"""Behavioral tests; all Git mutations stay in disposable repositories."""
import importlib.util
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

RUNNER = Path(__file__).resolve().parents[1] / "scripts" / "local_implement.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("local_implement", RUNNER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def response_body(status="DONE", files=(), notes="implemented", concerns=(),
                  suggested_tests=(), blocker=""):
    payload = {"status": status,
               "files": [{"path": p, "content": c} for p, c in files],
               "notes": notes, "concerns": list(concerns),
               "suggested_tests": list(suggested_tests), "blocker": blocker}
    return {"done": True, "done_reason": "stop", "response": json.dumps(payload)}


@contextmanager
def ollama_stub(li, responses=None, status=200, tags=("qwen3.8:27b-q8_0",), delay=0):
    """Serve /api/tags then one body per /api/generate call, recording requests."""
    requests = []
    bodies = list(responses or [])

    class FakeSocket:
        def __init__(self):
            self.closed = threading.Event()

        def shutdown(self, _how):
            self.closed.set()

    class FakeResponse:
        def __init__(self, response_status, data):
            self.status = response_status
            self.data = data

        def read(self, _limit=None):
            return self.data

    class FakeConnection:
        def __init__(self, host, port, timeout):
            self.sock = None
            self.path = None

        def connect(self):
            self.sock = FakeSocket()

        def request(self, _method, path, body=None, _headers=None):
            self.path = path
            requests.append((path, json.loads(body) if body else None))

        def getresponse(self):
            if status == 0:
                raise ConnectionResetError("disconnected")
            if self.path == "/api/tags":
                data = json.dumps({"models": [{"name": n} for n in tags]}).encode()
                return FakeResponse(200, data)
            if delay:
                if self.sock.closed.wait(delay):
                    raise OSError("closed by deadline")
            body = bodies.pop(0) if bodies else response_body()
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            return FakeResponse(status, data)

        def close(self):
            if self.sock is not None:
                self.sock.closed.set()

    with patch.object(li.http.client, "HTTPConnection", FakeConnection):
        yield requests


class DispatchFixture(unittest.TestCase):
    def setUp(self):
        self.assertTrue(RUNNER.exists(), "The local implementer runner is not implemented")
        self.li = load_runner()
        self.temp = tempfile.TemporaryDirectory(prefix="test-local-implement-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_TERMINAL_PROMPT="0")
        self.env = patch.dict(os.environ, env, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.git("init", "-q")
        self.git("config", "user.name", "Local Implement Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        (self.root / "seed.txt").write_text("seed\n")
        self.git("add", "--", "seed.txt")
        self.git("commit", "-qm", "chore: seed")
        self.base = self.git("rev-parse", "HEAD").decode().strip()
        self.work = self.root / ".superpowers" / "sdd" / "plan"
        self.work.mkdir(parents=True)
        self.brief = self.work / "task-1-brief.md"
        self.report = self.work / "task-1-report.md"
        self.context = self.work / "task-1-context.md"
        self.brief.write_text("### Task 1: Add greeter\nCreate greet() returning HELLO.\n")
        self.write_context(["src/greet.py"])

    def write_context(self, files, extra=""):
        lines = ["## Global Constraints", "- stdlib only", "", "## Files"]
        lines += [f"- {path}" for path in files]
        if extra:
            lines += ["", extra]
        self.context.write_text("\n".join(lines) + "\n")

    def git(self, *args, input_data=None):
        return subprocess.run(["git", "-C", str(self.root), *args],
                              input=input_data, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, check=True).stdout

    def options(self, **overrides):
        values = {"brief": str(self.brief), "report": str(self.report),
                  "context": str(self.context), "base": self.base,
                  "workdir": str(self.root), "test_cmd": (), "repair_rounds": 1}
        values.update(overrides)
        return values

    def assert_code(self, code, action):
        with self.assertRaises(self.li.LocalImplementError) as caught:
            action()
        self.assertEqual(caught.exception.code, code)


class ArgumentTests(DispatchFixture):
    def test_parses_required_arguments(self):
        options = self.li.parse_argv([
            "--brief", str(self.brief), "--report", str(self.report),
            "--context", str(self.context), "--base", self.base,
            "--workdir", str(self.root)])
        self.assertEqual(options["base"], self.base)
        self.assertEqual(options["repair_rounds"], 1)
        self.assertEqual(options["test_cmd"], ())

    def test_test_cmd_collects_remaining_argv(self):
        options = self.li.parse_argv([
            "--brief", str(self.brief), "--report", str(self.report),
            "--context", str(self.context), "--base", self.base,
            "--test-cmd", "python3", "-m", "unittest", "-q"])
        self.assertEqual(options["test_cmd"], ("python3", "-m", "unittest", "-q"))

    def test_missing_required_argument_is_rejected(self):
        self.assert_code("BAD_ARGUMENTS", lambda: self.li.parse_argv(["--brief", "x"]))

    def test_repair_rounds_outside_range_is_rejected(self):
        self.assert_code("BAD_ARGUMENTS", lambda: self.li.parse_argv([
            "--brief", str(self.brief), "--report", str(self.report),
            "--context", str(self.context), "--base", self.base,
            "--repair-rounds", "2"]))


class FilesSectionTests(DispatchFixture):
    def test_parses_bulleted_and_bare_paths(self):
        text = "## Files\n- a/one.py\n`b/two.py`\n\n## Notes\n- c/three.py\n"
        self.assertEqual(self.li.parse_files_section(text), ("a/one.py", "b/two.py"))

    def test_missing_section_raises(self):
        self.assert_code("NO_FILES_SECTION",
                         lambda: self.li.parse_files_section("## Notes\n- a.py\n"))

    def test_empty_section_raises(self):
        self.assert_code("NO_FILES_SECTION",
                         lambda: self.li.parse_files_section("## Files\n\n## Notes\n"))

    def test_bare_bullet_is_skipped(self):
        text = "## Files\n-\n- src/main.py\n\n## Notes\n"
        self.assertEqual(self.li.parse_files_section(text), ("src/main.py",))


class PreflightTests(DispatchFixture):
    def test_accepts_a_valid_dispatch(self):
        with ollama_stub(self.li):
            dispatch = self.li.load_dispatch(self.options())
        self.assertEqual(dispatch.files, ("src/greet.py",))
        self.assertEqual(dispatch.base, self.base)

    def test_rejects_non_repository_workdir(self):
        outside = Path(tempfile.mkdtemp(prefix="test-local-implement-bare-"))
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", str(outside)], check=False))
        self.assert_code("NOT_A_REPO",
                         lambda: self.li.load_dispatch(self.options(workdir=str(outside))))

    def test_rejects_unknown_base(self):
        self.assert_code("BAD_BASE",
                         lambda: self.li.load_dispatch(self.options(base="0" * 40)))

    def test_rejects_empty_brief(self):
        self.brief.write_text("")
        self.assert_code("EMPTY_BRIEF", lambda: self.li.load_dispatch(self.options()))

    def test_rejects_missing_context(self):
        self.context.unlink()
        self.assert_code("MISSING_CONTEXT", lambda: self.li.load_dispatch(self.options()))

    def test_rejects_absolute_declared_path(self):
        self.write_context(["/etc/passwd"])
        self.assert_code("ILLEGAL_PATH", lambda: self.li.load_dispatch(self.options()))

    def test_rejects_parent_escape_declared_path(self):
        self.write_context(["../outside.py"])
        self.assert_code("ILLEGAL_PATH", lambda: self.li.load_dispatch(self.options()))

    def test_rejects_git_internal_declared_path(self):
        self.write_context([".git/config"])
        self.assert_code("ILLEGAL_PATH", lambda: self.li.load_dispatch(self.options()))

    def test_rejects_symlink_declared_path(self):
        (self.root / "link.py").symlink_to(self.root / "seed.txt")
        self.write_context(["link.py"])
        self.assert_code("ILLEGAL_PATH", lambda: self.li.load_dispatch(self.options()))

    def test_rejects_oversized_declared_file(self):
        target = self.root / "src" / "greet.py"
        target.parent.mkdir(parents=True)
        target.write_text("x" * (self.li.FILE_LIMIT + 1))
        self.assert_code("INPUT_TOO_LARGE", lambda: self.li.load_dispatch(self.options()))

    def test_rejects_missing_model(self):
        with ollama_stub(self.li, tags=("other-model",)):
            self.assert_code("MODEL_MISSING", lambda: self.li.load_dispatch(self.options()))

    def test_rejects_unreachable_ollama(self):
        with ollama_stub(self.li, status=0):
            self.assert_code("OLLAMA_UNAVAILABLE",
                            lambda: self.li.load_dispatch(self.options()))

    def test_rejects_dangling_symlink_ancestor(self):
        (self.root / "link_dir").symlink_to(self.root.parent / "outside_target")
        self.write_context(["link_dir/new.py"])
        self.assert_code("ILLEGAL_PATH", lambda: self.li.load_dispatch(self.options()))

    def test_rejects_symlink_ancestor_targeting_outside(self):
        outside = Path(tempfile.mkdtemp(prefix="test-local-implement-target-"))
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", str(outside)], check=False))
        (self.root / "link_dir").symlink_to(outside)
        self.write_context(["link_dir/new.py"])
        self.assert_code("ILLEGAL_PATH", lambda: self.li.load_dispatch(self.options()))


class PromptTests(DispatchFixture):
    def test_prompt_contains_brief_context_and_new_file_marker(self):
        with ollama_stub(self.li):
            dispatch = self.li.load_dispatch(self.options())
        prompt = self.li.build_prompt(dispatch)
        self.assertIn("Create greet() returning HELLO.", prompt)
        self.assertIn("stdlib only", prompt)
        self.assertIn("src/greet.py", prompt)
        self.assertIn(self.li.NEW_FILE_MARKER, prompt)

    def test_prompt_contains_existing_file_content(self):
        target = self.root / "src" / "greet.py"
        target.parent.mkdir(parents=True)
        target.write_text("def greet():\n    return 'OLD'\n")
        with ollama_stub(self.li):
            dispatch = self.li.load_dispatch(self.options())
        self.assertIn("return 'OLD'", self.li.build_prompt(dispatch))

    def test_repair_prompt_carries_the_test_failure(self):
        with ollama_stub(self.li):
            dispatch = self.li.load_dispatch(self.options())
        previous = self.li.Proposal("DONE", (("src/greet.py", "x"),), "n", (), (), "")
        prompt = self.li.build_prompt(dispatch, failure="AssertionError: HELLO != HI",
                                      previous=previous)
        self.assertIn("AssertionError: HELLO != HI", prompt)

    def test_oversized_prompt_is_rejected(self):
        self.brief.write_text("z" * (self.li.PROMPT_LIMIT + 1))
        with ollama_stub(self.li):
            dispatch = self.li.load_dispatch(self.options())
        self.assert_code("INPUT_TOO_LARGE", lambda: self.li.build_prompt(dispatch))


class GenerationTests(DispatchFixture):
    def dispatch(self):
        with ollama_stub(self.li):
            return self.li.load_dispatch(self.options())

    def test_accepts_a_well_formed_proposal(self):
        dispatch = self.dispatch()
        body = response_body(files=(("src/greet.py", "def greet():\n    return 'HELLO'\n"),),
                             concerns=("naming is provisional",))
        with ollama_stub(self.li, responses=[body]) as requests:
            proposal = self.li.generate(dispatch)
        self.assertEqual(proposal.status, "DONE")
        self.assertEqual(proposal.files[0][0], "src/greet.py")
        self.assertEqual(proposal.concerns, ("naming is provisional",))
        generate_calls = [r for r in requests if r[0] == "/api/generate"]
        self.assertEqual(len(generate_calls), 1)
        payload = generate_calls[0][1]
        self.assertIs(payload["stream"], False)
        self.assertIs(payload["think"], False)
        self.assertEqual(payload["options"]["num_ctx"], self.li.NUM_CTX)
        self.assertEqual(payload["options"]["num_predict"], self.li.NUM_PREDICT)
        self.assertEqual(payload["format"], self.li.RESPONSE_SCHEMA)
        self.assertEqual(payload["model"], self.li.DEFAULT_MODEL)

    def test_model_override_is_honoured(self):
        dispatch = self.dispatch()
        with patch.dict(os.environ, {self.li.MODEL_ENV: "other-model"}):
            with ollama_stub(self.li, responses=[response_body(
                    files=(("src/greet.py", "x\n"),))]) as requests:
                self.li.generate(dispatch)
        payload = [r for r in requests if r[0] == "/api/generate"][0][1]
        self.assertEqual(payload["model"], "other-model")

    def test_rejects_unfinished_response(self):
        dispatch = self.dispatch()
        body = {"done": False, "done_reason": "length", "response": "{}"}
        with ollama_stub(self.li, responses=[body]):
            self.assert_code("INVALID_RESPONSE", lambda: self.li.generate(dispatch))

    def test_rejects_non_json_inner_payload(self):
        dispatch = self.dispatch()
        body = {"done": True, "done_reason": "stop", "response": "not json"}
        with ollama_stub(self.li, responses=[body]):
            self.assert_code("INVALID_RESPONSE", lambda: self.li.generate(dispatch))

    def test_rejects_missing_field(self):
        dispatch = self.dispatch()
        body = {"done": True, "done_reason": "stop",
                "response": json.dumps({"status": "DONE", "files": []})}
        with ollama_stub(self.li, responses=[body]):
            self.assert_code("INVALID_RESPONSE", lambda: self.li.generate(dispatch))

    def test_rejects_wrong_type(self):
        dispatch = self.dispatch()
        body = response_body(files=(("src/greet.py", "x"),))
        inner = json.loads(body["response"])
        inner["concerns"] = "not a list"
        body["response"] = json.dumps(inner)
        with ollama_stub(self.li, responses=[body]):
            self.assert_code("INVALID_RESPONSE", lambda: self.li.generate(dispatch))

    def test_rejects_unknown_status(self):
        dispatch = self.dispatch()
        with ollama_stub(self.li, responses=[response_body(status="VERIFY_FAILED")]):
            self.assert_code("INVALID_RESPONSE", lambda: self.li.generate(dispatch))

    def test_rejects_undeclared_path(self):
        dispatch = self.dispatch()
        with ollama_stub(self.li, responses=[response_body(
                files=(("src/other.py", "x\n"),))]):
            self.assert_code("UNDECLARED_PATH", lambda: self.li.generate(dispatch))

    def test_rejects_done_without_files(self):
        dispatch = self.dispatch()
        with ollama_stub(self.li, responses=[response_body(files=())]):
            self.assert_code("INVALID_RESPONSE", lambda: self.li.generate(dispatch))

    def test_blocked_without_files_is_accepted(self):
        dispatch = self.dispatch()
        with ollama_stub(self.li, responses=[response_body(
                status="BLOCKED", files=(), blocker="brief omits the return type")]):
            proposal = self.li.generate(dispatch)
        self.assertEqual(proposal.status, "BLOCKED")
        self.assertEqual(proposal.blocker, "brief omits the return type")

    def test_timeout_is_reported_without_retry(self):
        dispatch = self.dispatch()
        with patch.dict(os.environ, {self.li.TIMEOUT_ENV: "0.05"}):
            with ollama_stub(self.li, delay=5) as requests:
                self.assert_code("GENERATION_TIMEOUT", lambda: self.li.generate(dispatch))
        self.assertEqual(len([r for r in requests if r[0] == "/api/generate"]), 1)


if __name__ == "__main__":
    unittest.main()
