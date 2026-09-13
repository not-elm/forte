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


class ApplicationTests(DispatchFixture):
    def dispatch(self, **overrides):
        with ollama_stub(self.li):
            return self.li.load_dispatch(self.options(**overrides))

    def proposal(self, files):
        return self.li.Proposal("DONE", tuple(files), "notes", (), (), "")

    def test_creates_a_new_file_with_parent_directories(self):
        dispatch = self.dispatch()
        changed = self.li.apply_proposal(
            dispatch, self.proposal([("src/greet.py", "def greet():\n    return 'HELLO'\n")]),
            self.li.dirty_digests(self.root))
        self.assertEqual(changed, ("src/greet.py",))
        self.assertEqual((self.root / "src" / "greet.py").read_text(),
                         "def greet():\n    return 'HELLO'\n")

    def test_preserves_the_mode_of_an_existing_file(self):
        dispatch = self.dispatch()
        dirty = self.li.dirty_digests(self.root)
        target = self.root / "src" / "greet.py"
        target.parent.mkdir(parents=True)
        target.write_text("old\n")
        target.chmod(0o755)
        self.li.apply_proposal(dispatch, self.proposal([("src/greet.py", "new\n")]), dirty)
        self.assertEqual(target.stat().st_mode & 0o777, 0o755)
        self.assertEqual(target.read_text(), "new\n")

    def test_refuses_a_path_that_was_already_dirty(self):
        target = self.root / "src" / "greet.py"
        target.parent.mkdir(parents=True)
        target.write_text("uncommitted work\n")
        dispatch = self.dispatch()
        dirty = self.li.dirty_digests(self.root)
        self.assert_code("DIRTY_PATH_CONFLICT", lambda: self.li.apply_proposal(
            dispatch, self.proposal([("src/greet.py", "overwritten\n")]), dirty))
        self.assertEqual(target.read_text(), "uncommitted work\n")

    def test_refuses_an_undeclared_path_and_writes_nothing(self):
        dispatch = self.dispatch()
        self.assert_code("UNDECLARED_PATH", lambda: self.li.apply_proposal(
            dispatch,
            self.proposal([("src/greet.py", "ok\n"), ("src/sneaky.py", "bad\n")]),
            self.li.dirty_digests(self.root)))
        self.assertFalse((self.root / "src" / "greet.py").exists())
        self.assertFalse((self.root / "src" / "sneaky.py").exists())

    def test_dirty_digests_reports_untracked_and_modified_paths(self):
        (self.root / "untracked.txt").write_text("u\n")
        (self.root / "seed.txt").write_text("changed\n")
        digests = self.li.dirty_digests(self.root)
        self.assertIn("untracked.txt", digests)
        self.assertIn("seed.txt", digests)


class DeclaredTestTests(DispatchFixture):
    def dispatch(self, **overrides):
        with ollama_stub(self.li):
            return self.li.load_dispatch(self.options(**overrides))

    def test_returns_none_without_a_test_command(self):
        dispatch = self.dispatch()
        artifacts = self.li.create_artifacts()
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", str(artifacts.root)], check=False))
        self.assertIsNone(self.li.run_declared_tests(dispatch, artifacts, "initial"))

    def test_records_a_passing_command(self):
        dispatch = self.dispatch(test_cmd=("python3", "-c", "print('all good')"))
        artifacts = self.li.create_artifacts()
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", str(artifacts.root)], check=False))
        run = self.li.run_declared_tests(dispatch, artifacts, "initial")
        self.assertEqual(run.result, "pass")
        self.assertIn("all good", artifacts.test_log.read_text())

    def test_records_a_failing_command(self):
        dispatch = self.dispatch(test_cmd=("python3", "-c", "raise SystemExit(3)"))
        artifacts = self.li.create_artifacts()
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", str(artifacts.root)], check=False))
        run = self.li.run_declared_tests(dispatch, artifacts, "initial")
        self.assertEqual(run.result, "fail")

    def test_timeout_terminates_the_process_group(self):
        dispatch = self.dispatch(test_cmd=("python3", "-c", "import time; time.sleep(30)"))
        artifacts = self.li.create_artifacts()
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", str(artifacts.root)], check=False))
        with patch.object(self.li, "TEST_TIMEOUT", 0.2):
            run = self.li.run_declared_tests(dispatch, artifacts, "initial")
        self.assertEqual(run.result, "timeout")

    def test_never_runs_model_suggested_commands(self):
        marker = self.root / "should-not-exist.txt"
        dispatch = self.dispatch()
        artifacts = self.li.create_artifacts()
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", str(artifacts.root)], check=False))
        proposal = self.li.Proposal("DONE", (("src/greet.py", "x\n"),), "n", (),
                                    (f"touch {marker}",), "")
        self.li.apply_proposal(dispatch, proposal, self.li.dirty_digests(self.root))
        self.li.run_declared_tests(dispatch, artifacts, "initial")
        self.assertFalse(marker.exists())


class SelfRepairTests(DispatchFixture):
    def dispatch(self, **overrides):
        with ollama_stub(self.li):
            return self.li.load_dispatch(self.options(**overrides))

    def artifacts(self):
        artifacts = self.li.create_artifacts()
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", str(artifacts.root)], check=False))
        return artifacts

    def test_no_repair_when_tests_pass(self):
        dispatch = self.dispatch(test_cmd=("python3", "-c", "pass"))
        body = response_body(files=(("src/greet.py", "ok\n"),))
        with ollama_stub(self.li, responses=[body]) as requests:
            proposal, changed, run, used = self.li.implement(dispatch, self.artifacts())
        self.assertEqual(used, 0)
        self.assertEqual(run.result, "pass")
        self.assertEqual(changed, ("src/greet.py",))
        self.assertEqual(len([r for r in requests if r[0] == "/api/generate"]), 1)

    def test_one_repair_round_when_tests_fail_then_pass(self):
        script = self.root / "check.py"
        script.write_text(
            "import pathlib, sys\n"
            "sys.exit(0 if pathlib.Path('src/greet.py').read_text() == 'fixed\\n' else 1)\n")
        self.git("add", "--", "check.py")
        self.git("commit", "-qm", "chore: add check")
        dispatch = self.dispatch(test_cmd=("python3", str(script)))
        bodies = [response_body(files=(("src/greet.py", "broken\n"),)),
                  response_body(files=(("src/greet.py", "fixed\n"),))]
        with ollama_stub(self.li, responses=bodies) as requests:
            _proposal, changed, run, used = self.li.implement(dispatch, self.artifacts())
        self.assertEqual(used, 1)
        self.assertEqual(run.result, "pass")
        self.assertEqual(changed, ("src/greet.py",))
        self.assertEqual(len([r for r in requests if r[0] == "/api/generate"]), 2)

    def test_stops_after_one_repair_round(self):
        dispatch = self.dispatch(test_cmd=("python3", "-c", "raise SystemExit(1)"))
        bodies = [response_body(files=(("src/greet.py", "a\n"),)),
                  response_body(files=(("src/greet.py", "b\n"),))]
        with ollama_stub(self.li, responses=bodies) as requests:
            _proposal, _changed, run, used = self.li.implement(dispatch, self.artifacts())
        self.assertEqual(used, 1)
        self.assertEqual(run.result, "fail")
        self.assertEqual(len([r for r in requests if r[0] == "/api/generate"]), 2)

    def test_repair_rounds_zero_disables_repair(self):
        dispatch = self.dispatch(test_cmd=("python3", "-c", "raise SystemExit(1)"),
                                 repair_rounds=0)
        with ollama_stub(self.li, responses=[response_body(
                files=(("src/greet.py", "a\n"),))]) as requests:
            _proposal, _changed, run, used = self.li.implement(dispatch, self.artifacts())
        self.assertEqual(used, 0)
        self.assertEqual(run.result, "fail")
        self.assertEqual(len([r for r in requests if r[0] == "/api/generate"]), 1)

    def test_blocked_proposal_writes_nothing_and_skips_tests(self):
        dispatch = self.dispatch(test_cmd=("python3", "-c", "raise SystemExit(1)"))
        with ollama_stub(self.li, responses=[response_body(
                status="BLOCKED", files=(), blocker="missing interface")]):
            proposal, changed, run, used = self.li.implement(dispatch, self.artifacts())
        self.assertEqual(proposal.status, "BLOCKED")
        self.assertEqual(changed, ())
        self.assertIsNone(run)
        self.assertEqual(used, 0)
        self.assertFalse((self.root / "src" / "greet.py").exists())


class ReportTests(DispatchFixture):
    def dispatch(self, **overrides):
        with ollama_stub(self.li):
            return self.li.load_dispatch(self.options(**overrides))

    def test_report_records_command_output_and_unexecuted_suggestions(self):
        dispatch = self.dispatch(test_cmd=("python3", "-c", "print('probe output')"))
        artifacts = self.li.create_artifacts()
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", str(artifacts.root)], check=False))
        body = response_body(files=(("src/greet.py", "ok\n"),), notes="added greet()",
                             concerns=("naming",), suggested_tests=("pytest -q",))
        with ollama_stub(self.li, responses=[body]):
            proposal, changed, run, used = self.li.implement(dispatch, artifacts)
        self.li.write_report(dispatch, proposal, changed, run, used, artifacts)
        text = self.report.read_text()
        self.assertIn("added greet()", text)
        self.assertIn("src/greet.py", text)
        self.assertIn("probe output", text)
        self.assertIn("pytest -q", text)
        self.assertIn("not executed", text)
        self.assertIn("naming", text)


class StatusMappingTests(DispatchFixture):
    def test_passing_tests_keep_the_model_status(self):
        proposal = self.li.Proposal("DONE", (("a", "b"),), "n", (), (), "")
        run = self.li.TestRun(("python3",), "pass", "")
        self.assertEqual(self.li.resolve_status(proposal, run)[0], "DONE")

    def test_concerns_status_is_preserved(self):
        proposal = self.li.Proposal("DONE_WITH_CONCERNS", (("a", "b"),), "n", ("c",), (), "")
        run = self.li.TestRun(("python3",), "pass", "")
        self.assertEqual(self.li.resolve_status(proposal, run)[0], "DONE_WITH_CONCERNS")

    def test_failing_tests_become_blocked(self):
        proposal = self.li.Proposal("DONE", (("a", "b"),), "n", (), (), "")
        run = self.li.TestRun(("python3",), "fail", "boom")
        status, blocker = self.li.resolve_status(proposal, run)
        self.assertEqual(status, "BLOCKED")
        self.assertIn("still failing", blocker)

    def test_timed_out_tests_become_blocked(self):
        proposal = self.li.Proposal("DONE", (("a", "b"),), "n", (), (), "")
        run = self.li.TestRun(("python3",), "timeout", "")
        self.assertEqual(self.li.resolve_status(proposal, run)[0], "BLOCKED")

    def test_model_blocked_is_passed_through(self):
        proposal = self.li.Proposal("BLOCKED", (), "n", (), (), "no interface given")
        self.assertEqual(self.li.resolve_status(proposal, None),
                         ("BLOCKED", "no interface given"))


class ResultTests(DispatchFixture):
    def invoke(self, argv, responses):
        with ollama_stub(self.li, responses=responses):
            return self.li.run_skill(argv)

    def argv(self, *extra):
        return ["--brief", str(self.brief), "--report", str(self.report),
                "--context", str(self.context), "--base", self.base,
                "--workdir", str(self.root), *extra]

    def test_successful_run_emits_a_verified_result(self):
        result = self.invoke(self.argv(),
                             [response_body(files=(("src/greet.py", "ok\n"),))])
        self.assertEqual(result["status"], "DONE")
        self.assertEqual(result["changed"], ["src/greet.py"])
        self.assertTrue(result["verified"]["report_written"])
        self.assertTrue(result["verified"]["paths_allowed"])
        self.assertTrue(result["verified"]["untouched_dirty"])
        self.assertEqual(result["verified"]["base"], self.base)
        self.assertTrue(self.report.is_file())
        self.addCleanup(lambda: subprocess.run(
            ["rm", "-rf", result["artifacts"]], check=False))

    def test_result_line_stays_within_the_budget_and_hides_raw_output(self):
        long_notes = "n" * 20000
        body = response_body(files=(("src/greet.py", "x" * 5000),), notes=long_notes,
                             concerns=tuple(f"concern {i} " + "c" * 200 for i in range(40)))
        result = self.invoke(self.argv(), [body])
        encoded = json.dumps(result, ensure_ascii=False).encode("utf-8")
        self.assertLessEqual(len(encoded), self.li.RESULT_LIMIT)
        self.assertNotIn(long_notes, json.dumps(result))
        self.assertNotIn("x" * 100, json.dumps(result))
        self.addCleanup(lambda: subprocess.run(
            ["rm", "-rf", result["artifacts"]], check=False))

    def test_undeclared_path_reports_verify_failed_without_writing(self):
        result = self.invoke(self.argv(),
                             [response_body(files=(("src/other.py", "x\n"),))])
        self.assertEqual(result["status"], "VERIFY_FAILED")
        self.assertEqual(result["code"], "UNDECLARED_PATH")
        self.assertFalse((self.root / "src" / "other.py").exists())

    def test_missing_files_section_reports_needs_context(self):
        self.context.write_text("## Notes\n- nothing here\n")
        result = self.invoke(self.argv(), [])
        self.assertEqual(result["status"], "NEEDS_CONTEXT")
        self.assertEqual(result["code"], "NO_FILES_SECTION")

    def test_git_state_is_untouched_on_every_path(self):
        head_before = self.git("rev-parse", "HEAD").decode().strip()
        result = self.invoke(self.argv(),
                             [response_body(files=(("src/greet.py", "ok\n"),))])
        self.assertEqual(self.git("rev-parse", "HEAD").decode().strip(), head_before)
        staged = self.git("diff", "--cached", "--name-only").decode().strip()
        self.assertEqual(staged, "")
        self.addCleanup(lambda: subprocess.run(
            ["rm", "-rf", result["artifacts"]], check=False))

    def test_main_exit_codes_follow_the_status(self):
        with ollama_stub(self.li, responses=[response_body(
                files=(("src/greet.py", "ok\n"),))]):
            self.assertEqual(self.li.main(self.argv()), 0)
        with ollama_stub(self.li, responses=[response_body(
                status="BLOCKED", files=(), blocker="no interface")]):
            self.assertEqual(self.li.main(self.argv()), 1)


if __name__ == "__main__":
    unittest.main()
