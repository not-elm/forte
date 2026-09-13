"""Behavioral tests; all Git mutations stay in disposable repositories."""
import importlib.util
from contextlib import contextmanager
import io
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
        self.guard_git_subcommands()
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

    def guard_git_subcommands(self):
        """No runner path may invoke a Git verb that can mutate the repository."""
        original = self.li._git_result

        def guarded(root, *args):
            self.assertTrue(args, "the runner invoked git with no subcommand")
            self.assertIn(args[0], {"rev-parse", "status"},
                          "the runner invoked a git subcommand that is not read-only: "
                          + " ".join(args))
            return original(root, *args)

        patcher = patch.object(self.li, "_git_result", guarded)
        patcher.start()
        self.addCleanup(patcher.stop)

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

    def test_a_runner_flag_after_test_cmd_is_rejected(self):
        self.assert_code("BAD_ARGUMENTS", lambda: self.li.parse_argv([
            "--brief", str(self.brief), "--report", str(self.report),
            "--context", str(self.context), "--base", self.base,
            "--test-cmd", "cargo", "test", "--repair-rounds", "0"]))

    def test_test_cmd_keeps_its_own_dashed_options(self):
        options = self.li.parse_argv([
            "--brief", str(self.brief), "--report", str(self.report),
            "--context", str(self.context), "--base", self.base,
            "--test-cmd", "pytest", "-q", "--maxfail=1", "--tb=short"])
        self.assertEqual(options["test_cmd"],
                         ("pytest", "-q", "--maxfail=1", "--tb=short"))


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

    def test_rejects_a_prose_line(self):
        self.assert_code("ILLEGAL_PATH", lambda: self.li.parse_files_section(
            "## Files\nThe following files:\n- src/main.py\n"))

    def test_rejects_an_entry_containing_spaces(self):
        self.assert_code("ILLEGAL_PATH", lambda: self.li.parse_files_section(
            "## Files\n- spaces in path.py\n"))


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

    def test_rejects_symlink_component_resolving_inside_the_root(self):
        """The resolved path is inside the root, so only the per-component
        symlink scan can reject this."""
        (self.root / "real" / "sub").mkdir(parents=True)
        (self.root / "link_dir").symlink_to(self.root / "real")
        self.write_context(["link_dir/sub/new.py"])
        self.assert_code("ILLEGAL_PATH", lambda: self.li.load_dispatch(self.options()))

    def test_rejects_uppercase_git_declared_path(self):
        self.write_context([".GIT/config"])
        self.assert_code("ILLEGAL_PATH", lambda: self.li.load_dispatch(self.options()))

    def test_rejects_mixed_case_git_hook_declared_path(self):
        self.write_context([".Git/hooks/pre-commit"])
        self.assert_code("ILLEGAL_PATH", lambda: self.li.load_dispatch(self.options()))

    def test_rejects_nested_git_declared_path(self):
        self.write_context(["sub/.git/config"])
        self.assert_code("ILLEGAL_PATH", lambda: self.li.load_dispatch(self.options()))

    def test_rejects_declared_path_that_exists_as_a_directory(self):
        (self.root / "src" / "greet.py").mkdir(parents=True)
        self.assert_code("ILLEGAL_PATH", lambda: self.li.load_dispatch(self.options()))

    def test_rejects_declared_path_that_exists_as_a_fifo(self):
        (self.root / "src").mkdir()
        os.mkfifo(str(self.root / "src" / "greet.py"))
        self.assert_code("ILLEGAL_PATH", lambda: self.li.load_dispatch(self.options()))

    def test_rejects_declared_path_whose_parent_is_a_file(self):
        self.write_context(["seed.txt/inner.py"])
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

    def test_dirty_digests_consumes_a_worktree_side_rename_source(self):
        """A rename reported in the worktree column (status[1]) also carries a
        source path; missing it desynchronises the whole NUL walk."""
        payload = b" R new.txt\x00old.txt\x00 M seed.txt\x00"
        with patch.object(self.li, "git", lambda root, *args: payload):
            digests = self.li.dirty_digests(self.root)
        self.assertEqual(set(digests), {"new.txt", "seed.txt"})


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

    def test_a_blocked_repair_round_keeps_its_blocker(self):
        dispatch = self.dispatch(test_cmd=("python3", "-c", "raise SystemExit(1)"))
        bodies = [response_body(files=(("src/greet.py", "a\n"),)),
                  response_body(status="BLOCKED", files=(),
                                blocker="the brief omits the error type")]
        with ollama_stub(self.li, responses=bodies):
            proposal, _changed, run, used = self.li.implement(dispatch, self.artifacts())
        self.assertEqual(used, 1)
        self.assertEqual(run.result, "fail")
        self.assertIn("the brief omits the error type", proposal.blocker)


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

    def test_error_path_report_records_the_failed_first_round(self):
        bodies = [response_body(files=(("src/greet.py", "ok\n"),)),
                  response_body(files=(("src/undeclared.py", "x\n"),))]
        with ollama_stub(self.li, responses=bodies):
            result = self.li.run_skill([
                "--brief", str(self.brief), "--report", str(self.report),
                "--context", str(self.context), "--base", self.base,
                "--workdir", str(self.root),
                "--test-cmd", "python3", "-c", "raise SystemExit(1)"])
        self.addCleanup(lambda: subprocess.run(
            ["rm", "-rf", result["artifacts"]], check=False))
        self.assertEqual(result["status"], "VERIFY_FAILED")
        self.assertEqual(result["tests"]["result"], "fail")
        self.assertTrue(result["tests"]["command"])
        self.assertEqual(result["repair_rounds_used"], 1)
        text = Path(result["report"]).read_text()
        self.assertNotIn("No test command was supplied", text)
        self.assertIn("Result: **fail**", text)
        self.assertIn("Self-repair rounds used: 1", text)

    def test_report_labels_model_authored_sections_as_quoted_output(self):
        dispatch = self.dispatch()
        artifacts = self.li.create_artifacts()
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", str(artifacts.root)], check=False))
        body = response_body(files=(("src/greet.py", "ok\n"),), notes="added greet()",
                             concerns=("naming",), suggested_tests=("pytest -q",))
        with ollama_stub(self.li, responses=[body]):
            proposal, changed, run, used = self.li.implement(dispatch, artifacts)
        self.li.write_report(dispatch, proposal, changed, run, used, artifacts)
        text = self.report.read_text()
        self.assertIn("quoted model output", text)
        self.assertNotIn("raw model output", text)

    def test_report_names_the_test_log_when_no_run_survived(self):
        dispatch = self.dispatch(test_cmd=("python3", "-c", "pass"))
        artifacts = self.li.create_artifacts()
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", str(artifacts.root)], check=False))
        proposal = self.li.Proposal("BLOCKED", (), "stopped", (), (), "boom")
        self.li.write_report(dispatch, proposal, ("src/greet.py",), None, 0, artifacts)
        text = self.report.read_text()
        self.assertNotIn("No test command was supplied", text)
        self.assertIn(str(artifacts.root), text)


class StatusMappingTests(DispatchFixture):
    def test_passing_tests_keep_the_model_status(self):
        proposal = self.li.Proposal("DONE", (("a", "b"),), "n", (), (), "")
        run = self.li.TestRun(("python3",), "pass", "")
        self.assertEqual(self.li.resolve_status(proposal, run, used=0)[0], "DONE")

    def test_concerns_status_is_preserved(self):
        proposal = self.li.Proposal("DONE_WITH_CONCERNS", (("a", "b"),), "n", ("c",), (), "")
        run = self.li.TestRun(("python3",), "pass", "")
        self.assertEqual(self.li.resolve_status(proposal, run, used=0)[0], "DONE_WITH_CONCERNS")

    def test_failing_tests_become_blocked(self):
        proposal = self.li.Proposal("DONE", (("a", "b"),), "n", (), (), "")
        run = self.li.TestRun(("python3",), "fail", "boom")
        status, blocker = self.li.resolve_status(proposal, run, used=0)
        self.assertEqual(status, "BLOCKED")
        self.assertIn("still failing", blocker)

    def test_timed_out_tests_become_blocked(self):
        proposal = self.li.Proposal("DONE", (("a", "b"),), "n", (), (), "")
        run = self.li.TestRun(("python3",), "timeout", "")
        status, blocker = self.li.resolve_status(proposal, run, used=0)
        self.assertEqual(status, "BLOCKED")
        self.assertIn("timed out", blocker)

    def test_model_blocked_is_passed_through(self):
        proposal = self.li.Proposal("BLOCKED", (), "n", (), (), "no interface given")
        self.assertEqual(self.li.resolve_status(proposal, None, used=0),
                         ("BLOCKED", "no interface given"))

    def test_failure_message_mentions_repair_only_when_round_ran(self):
        proposal = self.li.Proposal("DONE", (("a", "b"),), "n", (), (), "")
        run = self.li.TestRun(("python3",), "fail", "boom")
        status, blocker = self.li.resolve_status(proposal, run, used=0)
        self.assertNotIn("self-repair round", blocker)
        status, blocker = self.li.resolve_status(proposal, run, used=1)
        self.assertIn("self-repair round", blocker)


class BudgetTests(DispatchFixture):
    def invoke(self, argv, responses):
        with ollama_stub(self.li, responses=responses):
            return self.li.run_skill(argv)

    def argv(self, *extra):
        return ["--brief", str(self.brief), "--report", str(self.report),
                "--context", str(self.context), "--base", self.base,
                "--workdir", str(self.root), *extra]

    def test_extreme_paths_still_fit_in_budget(self):
        long_report_path = str(self.report.parent / ("x" * 200 + ".md"))
        long_context_path = str(self.context.parent / ("y" * 200 + ".md"))
        Path(long_context_path).write_text(self.context.read_text())
        argv = ["--brief", str(self.brief), "--report", long_report_path,
                "--context", long_context_path, "--base", self.base,
                "--workdir", str(self.root)]
        long_concerns = tuple(f"concern {i} " + "z" * 200 for i in range(40))
        body = response_body(files=(("src/greet.py", "x" * 5000),),
                           concerns=long_concerns)
        result = self.invoke(argv, [body])
        encoded = json.dumps(result, ensure_ascii=False).encode("utf-8")
        self.assertLessEqual(len(encoded), self.li.RESULT_LIMIT)
        self.addCleanup(lambda: subprocess.run(
            ["rm", "-rf", result["artifacts"]], check=False))

    def _sweep_payload(self, report_extra_len):
        """The large-field shape used by the effectiveness sweeps: a long report
        path (the swept variable) alongside a long message, many long concerns,
        a long blocker, a long test command, several long changed paths, and a
        long artifacts path — big enough on every field to actually engage
        compact_result's reduction stages and the minimal-result fallback."""
        report = str(self.report.parent / ("r" * report_extra_len + ".md"))
        artifacts = "/tmp/" + "a" * 900
        changed = [f"src/module_{i}/" + "p" * 60 + f"file_{i}.py" for i in range(12)]
        concerns = [f"concern {i} " + "c" * 300 for i in range(40)]
        blocker = "blocker " + "b" * 2000
        command = "test-command " + "t" * 600
        message = "m" * 3000
        return {
            "status": "DONE_WITH_CONCERNS",
            "message": message,
            "changed": changed,
            "tests": {"command": command, "result": "fail"},
            "concerns": concerns,
            "blocker": blocker,
            "report": report,
            "repair_rounds_used": 1,
            "verified": {"base": "abc123def456", "paths_allowed": True,
                        "untouched_dirty": True, "report_written": True},
            "artifacts": artifacts,
        }

    def test_result_line_stays_within_budget_across_a_self_validating_sweep(self):
        """Replaces test_result_budget_across_boundary_region,
        test_paths_truncated_flag_set_on_report_only, and
        test_compact_result_is_idempotent: those swept input sizes too small to
        ever reach the minimal-result fallback, so their guarded assertions
        never ran and they pinned no defect. This sweep asserts the budget,
        fixed-point, and paths_truncated invariants on every case from 0 to
        3000, then asserts its own coverage so a range that stops engaging the
        machinery under test fails loudly instead of passing vacuously."""
        reached_minimal_fallback = False
        reached_paths_truncated = False
        reached_report_only_shortened = False

        for report_extra_len in range(0, 3001, 50):
            payload = self._sweep_payload(report_extra_len)
            compact_once = self.li.compact_result(payload)
            compact_twice = self.li.compact_result(compact_once)

            stdout_capture = io.StringIO()
            with patch.object(sys, "stdout", stdout_capture):
                self.li.emit_result(payload)
            emitted = stdout_capture.getvalue().encode("utf-8")

            report_shortened = compact_once.get("report") != payload["report"]
            artifacts_shortened = compact_once.get("artifacts") != payload["artifacts"]

            with self.subTest(report_extra_len=report_extra_len, check="budget"):
                self.assertLessEqual(
                    len(emitted), self.li.RESULT_LIMIT,
                    f"emitted line exceeds RESULT_LIMIT at report_extra_len="
                    f"{report_extra_len}: {len(emitted)} > {self.li.RESULT_LIMIT}")

            with self.subTest(report_extra_len=report_extra_len, check="fixed_point"):
                self.assertEqual(
                    json.dumps(compact_once, sort_keys=True),
                    json.dumps(compact_twice, sort_keys=True),
                    f"compact_result is not a fixed point at report_extra_len="
                    f"{report_extra_len}")

            if report_shortened or artifacts_shortened:
                with self.subTest(report_extra_len=report_extra_len, check="paths_truncated"):
                    self.assertTrue(
                        compact_once.get("paths_truncated", False),
                        f"paths_truncated not set despite shortening at "
                        f"report_extra_len={report_extra_len} "
                        f"(report_shortened={report_shortened}, "
                        f"artifacts_shortened={artifacts_shortened})")

            if "result_truncated" in compact_once:
                reached_minimal_fallback = True
            if compact_once.get("paths_truncated"):
                reached_paths_truncated = True
            if report_shortened and not artifacts_shortened:
                reached_report_only_shortened = True

        self.assertTrue(reached_minimal_fallback,
                       "sweep never reached the minimal-result fallback "
                       "(result_truncated); the swept range is ineffective")
        self.assertTrue(reached_paths_truncated,
                       "sweep never set paths_truncated; the swept range is "
                       "ineffective")
        self.assertTrue(reached_report_only_shortened,
                       "sweep never shortened report while leaving artifacts "
                       "intact; the swept range is ineffective")


class ErrorStatusTests(DispatchFixture):
    def error_result(self, action):
        """Fail loudly when the expected error is not raised at all."""
        with self.assertRaises(self.li.LocalImplementError) as caught:
            action()
        return self.li._error_result(caught.exception)

    def test_illegal_path_reports_paths_allowed_false(self):
        self.write_context(["../outside.py"])
        with ollama_stub(self.li):
            result = self.error_result(lambda: self.li.load_dispatch(self.options()))
        self.assertFalse(result["verified"]["paths_allowed"])

    def test_illegal_path_is_needs_context(self):
        self.write_context(["../outside.py"])
        with ollama_stub(self.li):
            result = self.error_result(lambda: self.li.load_dispatch(self.options()))
        self.assertEqual(result["status"], "NEEDS_CONTEXT")

    def test_input_too_large_is_needs_context(self):
        target = self.root / "src" / "greet.py"
        target.parent.mkdir(parents=True)
        target.write_text("x" * (self.li.FILE_LIMIT + 1))
        with ollama_stub(self.li):
            result = self.error_result(lambda: self.li.load_dispatch(self.options()))
        self.assertEqual(result["status"], "NEEDS_CONTEXT")


class ErrorDispatchPopulationTests(DispatchFixture):
    def invoke(self, argv, responses):
        with ollama_stub(self.li, responses=responses):
            return self.li.run_skill(argv)

    def argv(self, *extra):
        return ["--brief", str(self.brief), "--report", str(self.report),
                "--context", str(self.context), "--base", self.base,
                "--workdir", str(self.root), *extra]

    def test_dispatch_fields_populated_on_post_load_error(self):
        body = response_body(files=(("src/undeclared.py", "x\n"),))
        result = self.invoke(self.argv(), [body])
        self.assertEqual(result["status"], "VERIFY_FAILED")
        self.assertEqual(result["code"], "UNDECLARED_PATH")
        self.assertEqual(result["verified"]["base"], self.base)
        self.assertEqual(result["report"], str(self.report))
        self.addCleanup(lambda: subprocess.run(
            ["rm", "-rf", result["artifacts"]], check=False))


class PartialWorkTests(DispatchFixture):
    def invoke(self, argv, responses):
        with ollama_stub(self.li, responses=responses):
            return self.li.run_skill(argv)

    def argv(self, *extra):
        return ["--brief", str(self.brief), "--report", str(self.report),
                "--context", str(self.context), "--base", self.base,
                "--workdir", str(self.root), *extra]

    def test_partial_work_reported_when_repair_fails(self):
        body_initial = response_body(files=(("src/greet.py", "ok\n"),))
        body_repair = response_body(files=(("src/bad.py", "x\n"),))
        result = self.invoke(
            self.argv("--test-cmd", "python3", "-c", "raise SystemExit(1)"),
            [body_initial, body_repair])
        self.assertEqual(result["status"], "VERIFY_FAILED")
        self.assertEqual(result["code"], "UNDECLARED_PATH")
        self.assertEqual(result["changed"], ["src/greet.py"])
        self.assertTrue(result["verified"]["report_written"])
        self.assertTrue((self.root / "src" / "greet.py").is_file())
        report_text = Path(result["report"]).read_text()
        self.assertIn("Run stopped partway", report_text)
        self.addCleanup(lambda: subprocess.run(
            ["rm", "-rf", result["artifacts"]], check=False))


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
        self.addCleanup(lambda: subprocess.run(
            ["rm", "-rf", result["artifacts"]], check=False))

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

    def test_unexpected_os_error_reports_applied_paths_and_writes_a_report(self):
        self.write_context(["src/greet.py", "src/other.py"])
        original = self.li.write_atomic
        seen = []

        def flaky(path, content):
            seen.append(str(path))
            if len(seen) == 2:
                raise OSError(28, "No space left on device")
            return original(path, content)

        body = response_body(files=(("src/greet.py", "a\n"), ("src/other.py", "b\n")))
        with patch.object(self.li, "write_atomic", flaky):
            result = self.invoke(self.argv(), [body])
        self.addCleanup(lambda: subprocess.run(
            ["rm", "-rf", result["artifacts"]], check=False))
        self.assertEqual(result["status"], "VERIFY_FAILED")
        self.assertEqual(result["code"], "IO_FAILED")
        self.assertEqual(result["changed"], ["src/greet.py"])
        self.assertTrue(result["verified"]["report_written"])
        self.assertIn("src/greet.py", Path(result["report"]).read_text())
        self.assertLessEqual(
            len(json.dumps(result, ensure_ascii=False).encode("utf-8")),
            self.li.RESULT_LIMIT)

    def test_a_test_command_that_rewrites_a_dirty_path_fails_verification(self):
        (self.root / "seed.txt").write_text("uncommitted edit\n")
        script = self.root / "rewrite.py"
        script.write_text("import pathlib\n"
                          "pathlib.Path('seed.txt').write_text('clobbered\\n')\n")
        self.git("add", "--", "rewrite.py")
        self.git("commit", "-qm", "chore: add rewriter")
        result = self.invoke(self.argv("--test-cmd", "python3", str(script)),
                             [response_body(files=(("src/greet.py", "ok\n"),))])
        self.addCleanup(lambda: subprocess.run(
            ["rm", "-rf", result["artifacts"]], check=False))
        self.assertFalse(result["verified"]["untouched_dirty"])
        self.assertEqual(result["status"], "VERIFY_FAILED")

    def test_error_path_also_reports_a_clobbered_dirty_path(self):
        (self.root / "seed.txt").write_text("uncommitted edit\n")
        script = self.root / "rewrite.py"
        script.write_text("import pathlib, sys\n"
                          "pathlib.Path('seed.txt').write_text('clobbered\\n')\n"
                          "sys.exit(1)\n")
        self.git("add", "--", "rewrite.py")
        self.git("commit", "-qm", "chore: add rewriter")
        bodies = [response_body(files=(("src/greet.py", "ok\n"),)),
                  response_body(files=(("src/undeclared.py", "x\n"),))]
        result = self.invoke(self.argv("--test-cmd", "python3", str(script)), bodies)
        self.addCleanup(lambda: subprocess.run(
            ["rm", "-rf", result["artifacts"]], check=False))
        self.assertEqual(result["code"], "UNDECLARED_PATH")
        self.assertFalse(result["verified"]["untouched_dirty"])
        self.assertEqual(result["status"], "VERIFY_FAILED")

    def test_untouched_dirty_stays_true_when_dirty_paths_are_left_alone(self):
        (self.root / "seed.txt").write_text("uncommitted edit\n")
        result = self.invoke(self.argv("--test-cmd", "python3", "-c", "print('ok')"),
                             [response_body(files=(("src/greet.py", "ok\n"),))])
        self.addCleanup(lambda: subprocess.run(
            ["rm", "-rf", result["artifacts"]], check=False))
        self.assertTrue(result["verified"]["untouched_dirty"])
        self.assertEqual(result["status"], "DONE")
        self.assertEqual((self.root / "seed.txt").read_text(), "uncommitted edit\n")

    def test_main_exit_codes_follow_the_status(self):
        import io
        stdout_capture = io.StringIO()
        with patch.object(sys, 'stdout', stdout_capture):
            with ollama_stub(self.li, responses=[response_body(
                    files=(("src/greet.py", "ok\n"),))]):
                self.assertEqual(self.li.main(self.argv()), 0)
        result = json.loads(stdout_capture.getvalue().strip())
        artifacts_path1 = result.get("artifacts", "")
        self.addCleanup(lambda path=artifacts_path1: subprocess.run(
            ["rm", "-rf", path], check=False))

        stdout_capture = io.StringIO()
        with patch.object(sys, 'stdout', stdout_capture):
            with ollama_stub(self.li, responses=[response_body(
                    status="BLOCKED", files=(), blocker="no interface")]):
                self.assertEqual(self.li.main(self.argv()), 1)
        result = json.loads(stdout_capture.getvalue().strip())
        artifacts_path2 = result.get("artifacts", "")
        self.addCleanup(lambda path=artifacts_path2: subprocess.run(
            ["rm", "-rf", path], check=False))


class ArtifactPermissionTests(DispatchFixture):
    def test_artifact_directory_and_files_are_owner_only(self):
        artifacts = self.li.create_artifacts()
        self.addCleanup(lambda: subprocess.run(["rm", "-rf", str(artifacts.root)], check=False))
        self.assertEqual(artifacts.root.stat().st_mode & 0o777, 0o700)
        for path in (artifacts.test_log, artifacts.rounds_path):
            self.assertTrue(path.is_file(), f"{path.name} was not created")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600, path.name)


class GitVerbGuardTests(DispatchFixture):
    """Proves the suite-wide guard installed by DispatchFixture actually fires."""

    def test_the_guard_rejects_a_mutating_subcommand(self):
        with self.assertRaises(AssertionError):
            self.li.git(self.root, "commit", "-m", "nope")

    def test_the_guard_allows_the_read_only_subcommands(self):
        self.assertIn(self.base.encode(), self.li.git(self.root, "rev-parse", "HEAD"))


if __name__ == "__main__":
    unittest.main()
