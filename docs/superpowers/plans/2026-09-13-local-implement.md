# Local Implementer Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `forte:local-implement`, a skill that produces one SDD task's initial implementation with a local Ollama model while a deterministic Python runner performs every side effect, and wire it into autopilot behind an opt-in `--local-impl` flag.

**Architecture:** The model is asked for complete file contents as data through Ollama's native `/api/generate` with a JSON schema — there is no tool-calling layer, because measurement showed Codex's tool layer cannot drive local models on this host. The runner owns preflight, prompt construction, path-allowlisted application, test execution, one self-repair round, report writing, and a bounded result line. It never stages, commits, or mutates Git state; the Claude controller commits after verification.

**Tech Stack:** Python 3.9+ standard library only (`http.client`, `subprocess`, `tempfile`, `threading`, `signal`, `hashlib`, `unittest`), Git, Ollama with `qwen3.8:27b-q8_0`, Markdown skill files.

**Spec:** `docs/superpowers/specs/2026-09-13-local-implement-design.md`

## Global Constraints

- Python 3 standard library only; no third-party packages, no agent delegation from inside the runner.
- Model: `FORTE_LOCAL_IMPL_MODEL`, default `qwen3.8:27b-q8_0`. Never pull models automatically. No cloud fallback.
- Generation: non-streaming `/api/generate` at `http://127.0.0.1:11434`, direct `http.client.HTTPConnection` so no proxy or redirect is honoured, `think: false`, `options: {"num_ctx": 65536, "num_predict": 16384}`, `format` set to the response JSON schema.
- Size caps: total serialized prompt at most 48 KiB; any single declared file's current content at most 16 KiB; over either limit returns `INPUT_TOO_LARGE` with no truncation and no summarization. Ollama response body limit 1 MiB. Result line on stdout at most 2 KiB.
- Wall clock: `FORTE_LOCAL_IMPL_TIMEOUT`, default 1800 seconds, enforced as a hard expiry that a slow byte stream cannot extend. Declared-test timeout 900 seconds. On timeout terminate the whole process group and confirm termination before returning.
- The model returns **complete file contents, never diffs**. Model output is data: never a command, never an instruction to the runner.
- Write allowlist: exactly the paths in the context file's `## Files` section. A returned path outside it is refused with nothing written.
- Never stage, commit, push, amend, reset, checkout, stash, or change branches or `HEAD`. Never write under `.git/`.
- Never execute a model-proposed command. Only `--test-cmd`, supplied by the caller, is executed, and only as an argv array with no shell interpolation.
- Self-repair is capped at one round (`--repair-rounds`, values 0 or 1, default 1). No other retry.
- Status vocabulary: the **model** may return only `DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`. The **runner** passes those through when verification agrees, and otherwise substitutes `NEEDS_CONTEXT` (insufficient dispatch) or `VERIFY_FAILED` (output or repository state failed a check). A status the runner did not verify is never forwarded.
- `SKILL.md` is at most 60 lines and must not instruct the caller to read the runner, the prompt, or the raw model output during normal use.
- Test command for every task: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/local-implement/tests -v`
- `.claude-plugin/marketplace.json` has no version field; only `plugin.json` is bumped.

---

## File Structure

| File | Responsibility |
|---|---|
| `skills/local-implement/scripts/local_implement.py` | The whole runner: argument parsing, dispatch loading and preflight, prompt construction, generation, response validation, application, test execution, self-repair, report writing, bounded result. One file, mirroring `qwen_commit.py` and `rust_diagnostics.py`, which are single-file runners in this repository. |
| `skills/local-implement/tests/test_local_implement.py` | Behavioural tests against disposable Git repositories with an Ollama stub, mirroring `skills/qwen-commit/tests/test_qwen_commit.py`. |
| `skills/local-implement/SKILL.md` | Trigger, invocation, argument contract, result and error handling, scope limits. |
| `skills/autopilot/SKILL.md` | Modified: `--local-impl` input, Stage 5 standing answers, Stage 8 report line, ledger line, Quick Reference. |
| `CLAUDE.md`, `README.md`, `.claude-plugin/plugin.json` | Registration and version bump. |

Tasks 1–4 build the single runner file incrementally, each ending with its own passing test cycle. Tasks 5–7 are the skill document, the autopilot wiring, and registration.

---

### Task 1: Runner skeleton — arguments, dispatch loading, preflight

**Files:**
- Create: `skills/local-implement/scripts/local_implement.py`
- Test: `skills/local-implement/tests/test_local_implement.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: `LocalImplementError(code, message)` with attributes `.code` and `.message`; `Dispatch` frozen dataclass with fields `root: Path`, `brief: Path`, `report: Path`, `context: Path`, `base: str`, `files: Tuple[str, ...]`, `test_cmd: Tuple[str, ...]`, `repair_rounds: int`; `parse_argv(argv) -> dict`; `load_dispatch(options: dict) -> Dispatch`; `parse_files_section(text: str) -> Tuple[str, ...]`; `validate_declared_path(root: Path, raw: str) -> None`; `git(root, *args) -> bytes`; `check_model_available(model: str) -> None`; module constants `DEFAULT_MODEL`, `MODEL_ENV`, `OLLAMA_PORT`, `PROMPT_LIMIT`, `FILE_LIMIT`, `RESULT_LIMIT`, `REQUEST_TIMEOUT`, `TEST_TIMEOUT`, `TERMINATE_GRACE`, `NUM_CTX`, `NUM_PREDICT`, `RESPONSE_LIMIT`.

- [ ] **Step 1: Write the failing tests**

Create `skills/local-implement/tests/test_local_implement.py`:

```python
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
            if self.path == "/api/tags":
                data = json.dumps({"models": [{"name": n} for n in tags]}).encode()
                return FakeResponse(200, data)
            if delay:
                if self.sock.closed.wait(delay):
                    raise OSError("closed by deadline")
            if status == 0:
                raise ConnectionResetError("disconnected")
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/local-implement/tests -v`
Expected: FAIL — every test errors in `setUp` with "The local implementer runner is not implemented".

- [ ] **Step 3: Write the runner skeleton**

Create `skills/local-implement/scripts/local_implement.py`:

```python
#!/usr/bin/env python3
"""Implement one SDD task with a local model; this runner performs every side effect."""
from dataclasses import dataclass
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from typing import Dict, Optional, Sequence, Tuple


MODEL_ENV = "FORTE_LOCAL_IMPL_MODEL"
DEFAULT_MODEL = "qwen3.8:27b-q8_0"
TIMEOUT_ENV = "FORTE_LOCAL_IMPL_TIMEOUT"
OLLAMA_PORT = 11434
DEFAULT_TIMEOUT = 1800.0
TEST_TIMEOUT = 900.0
TERMINATE_GRACE = 1.0
RESPONSE_LIMIT = 1024 * 1024
PROMPT_LIMIT = 48 * 1024
FILE_LIMIT = 16 * 1024
RESULT_LIMIT = 2 * 1024
NUM_CTX = 65536
NUM_PREDICT = 16384
NEW_FILE_MARKER = "NEW FILE (does not exist yet)"


class LocalImplementError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def request_timeout() -> float:
    raw = os.environ.get(TIMEOUT_ENV)
    if raw is None:
        return DEFAULT_TIMEOUT
    try:
        value = float(raw)
    except ValueError:
        raise LocalImplementError("BAD_ARGUMENTS", f"{TIMEOUT_ENV} is not a number.") from None
    if value <= 0:
        raise LocalImplementError("BAD_ARGUMENTS", f"{TIMEOUT_ENV} must be positive.")
    return value


def model_name() -> str:
    return os.environ.get(MODEL_ENV) or DEFAULT_MODEL


@dataclass(frozen=True)
class Dispatch:
    root: Path
    brief: Path
    report: Path
    context: Path
    base: str
    files: Tuple[str, ...]
    test_cmd: Tuple[str, ...]
    repair_rounds: int


def _bad_arguments() -> LocalImplementError:
    return LocalImplementError(
        "BAD_ARGUMENTS",
        "usage: local_implement.py --brief P --report P --context P --base SHA "
        "[--workdir DIR] [--repair-rounds 0|1] [--test-cmd ARGV...]")


def parse_argv(argv: Sequence[str]) -> dict:
    options = {"brief": None, "report": None, "context": None, "base": None,
               "workdir": None, "repair_rounds": 1, "test_cmd": ()}
    single = {"--brief": "brief", "--report": "report", "--context": "context",
              "--base": "base", "--workdir": "workdir"}
    index = 0
    items = list(argv)
    while index < len(items):
        token = items[index]
        if token == "--test-cmd":
            rest = tuple(items[index + 1:])
            if not rest:
                raise _bad_arguments()
            options["test_cmd"] = rest
            index = len(items)
            continue
        if token == "--repair-rounds":
            if index + 1 >= len(items) or items[index + 1] not in ("0", "1"):
                raise _bad_arguments()
            options["repair_rounds"] = int(items[index + 1])
            index += 2
            continue
        key = single.get(token)
        if key is None or index + 1 >= len(items):
            raise _bad_arguments()
        options[key] = items[index + 1]
        index += 2
    if not all(options[name] for name in ("brief", "report", "context", "base")):
        raise _bad_arguments()
    return options


def _git_result(root: Path, *args: str):
    return subprocess.run(["git", "-C", str(root), *args], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=False)


def git(root: Path, *args: str) -> bytes:
    result = _git_result(root, *args)
    if result.returncode != 0:
        raise LocalImplementError("GIT_FAILED", "A read-only Git command failed.")
    return result.stdout


def read_text(path: Path, missing: str, empty: str) -> str:
    if not path.is_file():
        raise LocalImplementError(missing, f"Required file is missing: {path.name}")
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        raise LocalImplementError(empty, f"Required file is empty: {path.name}")
    return text


def parse_files_section(text: str) -> Tuple[str, ...]:
    paths = []
    inside = False
    for line in text.splitlines():
        if re.match(r"^#{1,6}\s", line):
            inside = bool(re.match(r"^#{1,6}\s+Files\s*$", line.strip()))
            continue
        if not inside:
            continue
        entry = line.strip()
        if not entry:
            continue
        entry = re.sub(r"^[-*]\s+", "", entry).strip().strip("`").strip()
        if entry:
            paths.append(entry)
    if not paths:
        raise LocalImplementError(
            "NO_FILES_SECTION",
            "The context file needs a non-empty '## Files' section listing every path "
            "the task creates or modifies.")
    unique = tuple(dict.fromkeys(paths))
    return unique


def validate_declared_path(root: Path, raw: str) -> None:
    illegal = LocalImplementError("ILLEGAL_PATH", f"Declared path is not allowed: {raw}")
    if not raw or raw.startswith(("/", "~")) or "\x00" in raw:
        raise illegal
    parts = Path(raw).parts
    if not parts or ".." in parts or parts[0] == ".git":
        raise illegal
    root_resolved = root.resolve()
    candidate = root_resolved / raw
    existing = candidate
    while not existing.exists():
        parent = existing.parent
        if parent == existing:
            break
        existing = parent
    if existing.is_symlink() or candidate.is_symlink():
        raise illegal
    try:
        resolved_existing = existing.resolve()
    except OSError:
        raise illegal from None
    if resolved_existing != root_resolved and root_resolved not in resolved_existing.parents:
        raise illegal
    suffix = candidate.relative_to(root_resolved)
    if os.path.normpath(str(suffix)) != str(suffix):
        raise illegal


def ollama_request(path: str, payload: Optional[dict], deadline_seconds: float) -> dict:
    # HTTPConnection connects directly: no proxies, redirects, or remote endpoint option.
    connection = http.client.HTTPConnection("127.0.0.1", OLLAMA_PORT,
                                            timeout=deadline_seconds)
    deadline = time.monotonic() + deadline_seconds
    timer = None
    expired = threading.Event()
    try:
        connection.connect()
        active_socket = connection.sock

        def expire():
            expired.set()
            try:
                active_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

        # A socket timeout alone can be extended forever by slowly arriving bytes.
        timer = threading.Timer(max(0, deadline - time.monotonic()), expire)
        timer.daemon = True
        timer.start()
        if payload is None:
            connection.request("GET", path)
        else:
            connection.request("POST", path, json.dumps(payload).encode("utf-8"),
                               {"Content-Type": "application/json"})
        response = connection.getresponse()
        if response.status != 200:
            code = "OLLAMA_UNAVAILABLE" if response.status == 404 else "GENERATION_FAILED"
            raise LocalImplementError(code, "Local Ollama request failed; check service and model.")
        data = response.read(RESPONSE_LIMIT + 1)
        if expired.is_set() or time.monotonic() >= deadline:
            raise TimeoutError
        if len(data) > RESPONSE_LIMIT:
            raise LocalImplementError("INVALID_RESPONSE", "Ollama response exceeds the size limit.")
        try:
            return json.loads(data)
        except (ValueError, UnicodeError):
            raise LocalImplementError("INVALID_RESPONSE", "Ollama returned invalid JSON.") from None
    except (OSError, http.client.HTTPException) as error:
        if expired.is_set() or isinstance(error, TimeoutError) or time.monotonic() >= deadline:
            raise LocalImplementError("GENERATION_TIMEOUT",
                                      "Local generation timed out; no retry performed.") from None
        raise LocalImplementError("OLLAMA_UNAVAILABLE",
                                  "Could not communicate with local Ollama.") from None
    finally:
        if timer:
            timer.cancel()
            timer.join()
        connection.close()


def check_model_available(model: str) -> None:
    tags = ollama_request("/api/tags", None, min(30.0, request_timeout()))
    names = tags.get("models") if isinstance(tags, dict) else None
    if not isinstance(names, list):
        raise LocalImplementError("OLLAMA_UNAVAILABLE", "Ollama did not report its models.")
    available = {entry.get("name") for entry in names if isinstance(entry, dict)}
    if model not in available:
        raise LocalImplementError(
            "MODEL_MISSING",
            f"Model {model} is not installed; install it yourself (no automatic pull).")


def load_dispatch(options: dict) -> Dispatch:
    root = Path(options["workdir"] or os.getcwd()).resolve()
    if not root.is_dir() or _git_result(root, "rev-parse", "--is-inside-work-tree").returncode != 0:
        raise LocalImplementError("NOT_A_REPO", "The working directory is not a Git worktree.")
    if _git_result(root, "rev-parse", "--verify", "--quiet", options["base"] + "^{commit}").returncode != 0:
        raise LocalImplementError("BAD_BASE", "The supplied --base does not resolve in this repository.")
    brief = Path(options["brief"])
    context = Path(options["context"])
    read_text(brief, "MISSING_BRIEF", "EMPTY_BRIEF")
    context_text = read_text(context, "MISSING_CONTEXT", "EMPTY_CONTEXT")
    files = parse_files_section(context_text)
    for raw in files:
        validate_declared_path(root, raw)
        target = root / raw
        if target.is_file() and target.stat().st_size > FILE_LIMIT:
            raise LocalImplementError(
                "INPUT_TOO_LARGE",
                f"Declared file exceeds {FILE_LIMIT} bytes: {raw}; split the task.")
    check_model_available(model_name())
    return Dispatch(root=root, brief=brief, report=Path(options["report"]), context=context,
                    base=options["base"], files=files,
                    test_cmd=tuple(options["test_cmd"]),
                    repair_rounds=int(options["repair_rounds"]))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/local-implement/tests -v`
Expected: PASS for all `ArgumentTests`, `FilesSectionTests`, and `PreflightTests`.

- [ ] **Step 5: Commit**

```bash
git add skills/local-implement/scripts/local_implement.py skills/local-implement/tests/test_local_implement.py
git commit -m "feat(local-implement): add runner preflight and dispatch loading"
```

---

### Task 2: Prompt construction, generation, and response validation

**Files:**
- Modify: `skills/local-implement/scripts/local_implement.py` (append after `load_dispatch`)
- Test: `skills/local-implement/tests/test_local_implement.py` (append new test classes)

**Interfaces:**
- Consumes: `Dispatch`, `LocalImplementError`, `ollama_request`, `model_name`, `request_timeout`, `PROMPT_LIMIT`, `NUM_CTX`, `NUM_PREDICT`, `NEW_FILE_MARKER` from Task 1.
- Produces: `RULES` (str), `RESPONSE_SCHEMA` (dict), `Proposal` frozen dataclass with fields `status: str`, `files: Tuple[Tuple[str, str], ...]`, `notes: str`, `concerns: Tuple[str, ...]`, `suggested_tests: Tuple[str, ...]`, `blocker: str`; `build_prompt(dispatch: Dispatch, failure: Optional[str] = None, previous: Optional[Proposal] = None) -> str`; `validate_proposal(response: object, dispatch: Dispatch) -> Proposal`; `generate(dispatch: Dispatch, failure=None, previous=None) -> Proposal`.

- [ ] **Step 1: Write the failing tests**

Append to `skills/local-implement/tests/test_local_implement.py`, before the `if __name__` block:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/local-implement/tests -v`
Expected: FAIL with `AttributeError: module 'local_implement' has no attribute 'build_prompt'`.

- [ ] **Step 3: Implement prompt construction, generation, and validation**

Append to `skills/local-implement/scripts/local_implement.py`:

```python
RULES = """You implement exactly one task in a Git repository. Return only the JSON object
described by the schema.

Rules:
- TASK BRIEF is your requirements. Use its exact values, names, and strings verbatim.
- CONTEXT carries project-wide constraints and decisions from earlier tasks. Obey them.
- You may change only the files listed under DECLARED FILES. Touch nothing else.
- For every file you change, return its COMPLETE new content. Never return a diff, a patch,
  a fragment, or a placeholder comment standing in for code you did not write.
- Follow the style and patterns visible in the file contents you were given.
- Write the tests the brief asks for. Do not invent requirements it does not state.
- If the task cannot be implemented from what you were given, return status BLOCKED and put
  the specifics in blocker. Never guess.
- notes describes what you implemented; it becomes the report a reviewer reads.
- suggested_tests is advisory only and will not be executed.
"""

RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["status", "files", "notes", "concerns", "suggested_tests", "blocker"],
    "additionalProperties": False,
    "properties": {
        "status": {"type": "string", "enum": ["DONE", "DONE_WITH_CONCERNS", "BLOCKED"]},
        "files": {"type": "array", "items": {
            "type": "object", "required": ["path", "content"], "additionalProperties": False,
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}}}},
        "notes": {"type": "string"},
        "concerns": {"type": "array", "items": {"type": "string"}},
        "suggested_tests": {"type": "array", "items": {"type": "string"}},
        "blocker": {"type": "string"},
    },
}


@dataclass(frozen=True)
class Proposal:
    status: str
    files: Tuple[Tuple[str, str], ...]
    notes: str
    concerns: Tuple[str, ...]
    suggested_tests: Tuple[str, ...]
    blocker: str


def build_prompt(dispatch: Dispatch, failure: Optional[str] = None,
                 previous: Optional[Proposal] = None) -> str:
    sections = [RULES, "\n## TASK BRIEF\n", dispatch.brief.read_text(encoding="utf-8", errors="replace"),
                "\n## CONTEXT\n", dispatch.context.read_text(encoding="utf-8", errors="replace"),
                "\n## DECLARED FILES\n"]
    for raw in dispatch.files:
        target = dispatch.root / raw
        sections.append(f"\n### {raw}\n")
        if target.is_file():
            sections.append(target.read_text(encoding="utf-8", errors="replace"))
        else:
            sections.append(NEW_FILE_MARKER + "\n")
    if failure is not None:
        previous_notes = previous.notes if previous else ""
        sections.append(
            "\n## PREVIOUS ATTEMPT FAILED ITS TESTS\n"
            "Your previous attempt was applied and the declared test command failed. "
            "Return the complete corrected content of every file that needs changing.\n"
            f"\nYour previous notes:\n{previous_notes}\n"
            f"\nTest output:\n{failure}\n")
    prompt = "".join(sections)
    if len(prompt.encode("utf-8")) > PROMPT_LIMIT:
        raise LocalImplementError(
            "INPUT_TOO_LARGE",
            f"Prompt exceeds {PROMPT_LIMIT} bytes; split the task or shorten the context.")
    return prompt


def validate_proposal(response: object, dispatch: Dispatch) -> Proposal:
    invalid = LocalImplementError("INVALID_RESPONSE",
                                  "The local model did not return a valid proposal.")
    if (not isinstance(response, dict) or response.get("done") is not True
            or response.get("done_reason") != "stop"
            or not isinstance(response.get("response"), str)):
        raise invalid
    try:
        payload = json.loads(response["response"])
    except ValueError:
        raise invalid from None
    if not isinstance(payload, dict) or set(payload) != set(RESPONSE_SCHEMA["required"]):
        raise invalid
    status = payload["status"]
    if status not in ("DONE", "DONE_WITH_CONCERNS", "BLOCKED"):
        raise invalid
    for key in ("notes", "blocker"):
        if not isinstance(payload[key], str):
            raise invalid
    for key in ("concerns", "suggested_tests"):
        if not isinstance(payload[key], list) or any(
                not isinstance(item, str) for item in payload[key]):
            raise invalid
    if not isinstance(payload["files"], list):
        raise invalid
    files = []
    seen = set()
    for entry in payload["files"]:
        if (not isinstance(entry, dict) or set(entry) != {"path", "content"}
                or not isinstance(entry["path"], str) or not isinstance(entry["content"], str)):
            raise invalid
        path = entry["path"]
        if path not in dispatch.files:
            raise LocalImplementError(
                "UNDECLARED_PATH",
                f"The model returned a path that was not declared: {path}")
        if path in seen:
            raise invalid
        seen.add(path)
        files.append((path, entry["content"]))
    if status != "BLOCKED" and not files:
        raise invalid
    if status == "BLOCKED" and not payload["blocker"].strip():
        raise invalid
    return Proposal(status=status, files=tuple(files), notes=payload["notes"],
                    concerns=tuple(payload["concerns"]),
                    suggested_tests=tuple(payload["suggested_tests"]),
                    blocker=payload["blocker"])


def generate(dispatch: Dispatch, failure: Optional[str] = None,
             previous: Optional[Proposal] = None) -> Proposal:
    payload = {
        "model": model_name(),
        "prompt": build_prompt(dispatch, failure=failure, previous=previous),
        "stream": False, "think": False,
        "format": RESPONSE_SCHEMA,
        "options": {"num_ctx": NUM_CTX, "num_predict": NUM_PREDICT},
    }
    return validate_proposal(ollama_request("/api/generate", payload, request_timeout()),
                             dispatch)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/local-implement/tests -v`
Expected: PASS for `PromptTests` and `GenerationTests`, with Task 1's classes still passing.

- [ ] **Step 5: Commit**

```bash
git add skills/local-implement/scripts/local_implement.py skills/local-implement/tests/test_local_implement.py
git commit -m "feat(local-implement): generate and validate file proposals"
```

---

### Task 3: Application, declared tests, and one self-repair round

**Files:**
- Modify: `skills/local-implement/scripts/local_implement.py` (append after `generate`)
- Test: `skills/local-implement/tests/test_local_implement.py` (append new test classes)

**Interfaces:**
- Consumes: `Dispatch`, `Proposal`, `LocalImplementError`, `git`, `generate`, `TEST_TIMEOUT`, `TERMINATE_GRACE` from Tasks 1–2.
- Produces: `Artifacts` frozen dataclass with fields `root: Path`, `test_log: Path`, `raw_path: Path`; `create_artifacts() -> Artifacts`; `dirty_digests(root: Path) -> Dict[str, Optional[str]]`; `write_atomic(path: Path, content: str) -> None`; `apply_proposal(dispatch: Dispatch, proposal: Proposal, dirty: Dict[str, Optional[str]]) -> Tuple[str, ...]`; `TestRun` frozen dataclass with fields `command: Tuple[str, ...]`, `result: str`, `output: str`; `run_declared_tests(dispatch: Dispatch, artifacts: Artifacts, label: str) -> Optional[TestRun]`; `implement(dispatch: Dispatch, artifacts: Artifacts) -> Tuple[Proposal, Tuple[str, ...], Optional[TestRun], int]`.

- [ ] **Step 1: Write the failing tests**

Append to `skills/local-implement/tests/test_local_implement.py`, before the `if __name__` block:

```python
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
        target = self.root / "src" / "greet.py"
        target.parent.mkdir(parents=True)
        target.write_text("old\n")
        target.chmod(0o755)
        dispatch = self.dispatch()
        self.li.apply_proposal(dispatch, self.proposal([("src/greet.py", "new\n")]),
                               self.li.dirty_digests(self.root))
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/local-implement/tests -v`
Expected: FAIL with `AttributeError: module 'local_implement' has no attribute 'apply_proposal'`.

- [ ] **Step 3: Implement application, test execution, and self-repair**

Append to `skills/local-implement/scripts/local_implement.py`:

```python
@dataclass(frozen=True)
class Artifacts:
    root: Path
    test_log: Path
    raw_path: Path


def create_artifacts() -> Artifacts:
    root = Path(tempfile.mkdtemp(prefix="forte-local-implement-")).resolve()
    root.chmod(0o700)
    return Artifacts(root=root, test_log=root / "tests.log", raw_path=root / "raw.json")


def dirty_digests(root: Path) -> Dict[str, Optional[str]]:
    raw = git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    entries = raw.split(b"\x00")
    digests: Dict[str, Optional[str]] = {}
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if len(entry) < 4:
            continue
        status = entry[:2].decode("utf-8", errors="replace")
        path = entry[3:].decode("utf-8", errors="replace")
        if status[0] in ("R", "C") and index < len(entries):
            index += 1  # consume the rename/copy source path
        target = root / path
        if target.is_file() and not target.is_symlink():
            digests[path] = hashlib.sha256(target.read_bytes()).hexdigest()
        else:
            digests[path] = None
    return digests


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.is_file() else None
    descriptor, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as output:
            output.write(content)
        if mode is not None:
            os.chmod(temporary, mode)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def apply_proposal(dispatch: Dispatch, proposal: Proposal,
                   dirty: Dict[str, Optional[str]]) -> Tuple[str, ...]:
    for path, _content in proposal.files:
        if path not in dispatch.files:
            raise LocalImplementError(
                "UNDECLARED_PATH", f"Refusing to write an undeclared path: {path}")
        validate_declared_path(dispatch.root, path)
        if path in dirty:
            raise LocalImplementError(
                "DIRTY_PATH_CONFLICT",
                f"{path} already had uncommitted changes before the run; refusing to overwrite.")
    for path, content in proposal.files:
        write_atomic(dispatch.root / path, content)
    return tuple(path for path, _content in proposal.files)


@dataclass(frozen=True)
class TestRun:
    command: Tuple[str, ...]
    result: str
    output: str


def _terminate_process_group(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return
    grace_end = time.monotonic() + TERMINATE_GRACE
    while process.poll() is None and time.monotonic() < grace_end:
        time.sleep(min(0.02, max(0.0, grace_end - time.monotonic())))
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def run_declared_tests(dispatch: Dispatch, artifacts: Artifacts,
                       label: str) -> Optional[TestRun]:
    if not dispatch.test_cmd:
        return None
    process = subprocess.Popen(list(dispatch.test_cmd), cwd=str(dispatch.root),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               start_new_session=True)
    timed_out = False
    try:
        output, _ = process.communicate(timeout=TEST_TIMEOUT)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_process_group(process)
        output, _ = process.communicate()
    text = (output or b"").decode("utf-8", errors="replace")
    with artifacts.test_log.open("a", encoding="utf-8") as log:
        log.write(f"=== {label}: {' '.join(dispatch.test_cmd)} ===\n{text}\n")
    result = "timeout" if timed_out else ("pass" if process.returncode == 0 else "fail")
    return TestRun(command=dispatch.test_cmd, result=result, output=text)


def _failure_excerpt(run: TestRun, budget: int = 8 * 1024) -> str:
    encoded = run.output.encode("utf-8")
    if len(encoded) <= budget:
        return run.output
    return "…(earlier output omitted)…\n" + encoded[-budget:].decode("utf-8", errors="replace")


def implement(dispatch: Dispatch, artifacts: Artifacts):
    dirty = dirty_digests(dispatch.root)
    proposal = generate(dispatch)
    _write_raw(artifacts, "initial", proposal)
    if proposal.status == "BLOCKED":
        return proposal, (), None, 0
    changed = apply_proposal(dispatch, proposal, dirty)
    run = run_declared_tests(dispatch, artifacts, "initial")
    used = 0
    if (run is not None and run.result != "pass" and dispatch.repair_rounds > 0):
        repaired = generate(dispatch, failure=_failure_excerpt(run), previous=proposal)
        _write_raw(artifacts, "repair", repaired)
        used = 1
        if repaired.status != "BLOCKED" and repaired.files:
            changed = tuple(dict.fromkeys(
                changed + apply_proposal(dispatch, repaired, dirty)))
            proposal = Proposal(status=repaired.status, files=repaired.files,
                                notes=proposal.notes + "\n\nRepair round: " + repaired.notes,
                                concerns=proposal.concerns + repaired.concerns,
                                suggested_tests=repaired.suggested_tests,
                                blocker=repaired.blocker)
            run = run_declared_tests(dispatch, artifacts, "repair")
    return proposal, changed, run, used


def _write_raw(artifacts: Artifacts, label: str, proposal: Proposal) -> None:
    with artifacts.raw_path.open("a", encoding="utf-8") as raw:
        raw.write(json.dumps({"round": label, "status": proposal.status,
                              "paths": [path for path, _ in proposal.files],
                              "notes": proposal.notes,
                              "concerns": list(proposal.concerns),
                              "blocker": proposal.blocker},
                             ensure_ascii=False) + "\n")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/local-implement/tests -v`
Expected: PASS for `ApplicationTests`, `DeclaredTestTests`, `SelfRepairTests`, with Tasks 1–2 still passing.

- [ ] **Step 5: Commit**

```bash
git add skills/local-implement/scripts/local_implement.py skills/local-implement/tests/test_local_implement.py
git commit -m "feat(local-implement): apply proposals, run declared tests, allow one repair"
```

---

### Task 4: Report writing, status mapping, and bounded result

**Files:**
- Modify: `skills/local-implement/scripts/local_implement.py` (append after `_write_raw`)
- Test: `skills/local-implement/tests/test_local_implement.py` (append new test classes)

**Interfaces:**
- Consumes: everything from Tasks 1–3.
- Produces: `write_report(dispatch, proposal, changed, run, used, artifacts) -> None`; `resolve_status(proposal: Proposal, run: Optional[TestRun]) -> Tuple[str, str]` returning `(status, blocker)`; `build_result(...) -> dict`; `compact_result(result: dict) -> dict`; `emit_result(result: dict) -> None`; `run_skill(root_argv: Sequence[str]) -> dict`; `main(argv=None) -> int`. Exit code 0 only when the emitted status is `DONE` or `DONE_WITH_CONCERNS`.

- [ ] **Step 1: Write the failing tests**

Append to `skills/local-implement/tests/test_local_implement.py`, before the `if __name__` block:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/local-implement/tests -v`
Expected: FAIL with `AttributeError: module 'local_implement' has no attribute 'write_report'`.

- [ ] **Step 3: Implement report, status mapping, result, and entry point**

Append to `skills/local-implement/scripts/local_implement.py`:

```python
def write_report(dispatch: Dispatch, proposal: Proposal, changed: Tuple[str, ...],
                 run: Optional[TestRun], used: int, artifacts: Artifacts) -> None:
    lines = [f"# Local implementer report — base {dispatch.base}", "",
             "## What was implemented", "", proposal.notes.strip() or "(no notes returned)", "",
             "## Files changed", ""]
    lines += [f"- `{path}`" for path in changed] or ["- none"]
    lines += ["", "## Test evidence", ""]
    if run is None:
        lines += ["No test command was supplied by the caller (`--test-cmd` absent), so no "
                  "tests were executed by the runner."]
    else:
        lines += [f"Command: `{' '.join(run.command)}`", f"Result: **{run.result}**", "",
                  "```", _failure_excerpt(run, 16 * 1024).rstrip("\n") or "(no output)", "```"]
    lines += ["", f"Self-repair rounds used: {used}", "", "## Concerns", ""]
    lines += [f"- {item}" for item in proposal.concerns] or ["- none"]
    lines += ["", "## Model-suggested tests (not executed)", ""]
    lines += [f"- `{item}`" for item in proposal.suggested_tests] or ["- none"]
    if proposal.blocker.strip():
        lines += ["", "## Blocker", "", proposal.blocker.strip()]
    lines += ["", f"Full test log and raw model output: `{artifacts.root}`", ""]
    dispatch.report.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(dispatch.report, "\n".join(lines))


def resolve_status(proposal: Proposal, run: Optional[TestRun]) -> Tuple[str, str]:
    if proposal.status == "BLOCKED":
        return "BLOCKED", proposal.blocker
    if run is not None and run.result != "pass":
        return "BLOCKED", (f"The declared test command {run.result}ed after "
                           "the self-repair round; the declared tests are still failing.")
    return proposal.status, ""


def build_result(dispatch: Dispatch, proposal: Proposal, changed: Tuple[str, ...],
                 run: Optional[TestRun], used: int, artifacts: Artifacts) -> dict:
    status, blocker = resolve_status(proposal, run)
    return {
        "status": status,
        "changed": list(changed),
        "tests": {"command": " ".join(run.command) if run else "",
                  "result": run.result if run else "not_run"},
        "concerns": list(proposal.concerns),
        "blocker": blocker,
        "report": str(dispatch.report),
        "repair_rounds_used": used,
        "verified": {"base": dispatch.base, "paths_allowed": True,
                     "untouched_dirty": True,
                     "report_written": dispatch.report.is_file()
                     and dispatch.report.stat().st_size > 0},
        "artifacts": str(artifacts.root),
    }


def _truncate(value: str, limit: int) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) <= limit:
        return value
    return encoded[:limit].decode("utf-8", errors="ignore") + "…"


def compact_result(result: dict) -> dict:
    compact = dict(result)
    compact["blocker"] = _truncate(compact.get("blocker", ""), 400)
    compact["concerns"] = [_truncate(item, 160) for item in compact.get("concerns", [])]
    while len(json.dumps(compact, ensure_ascii=False).encode("utf-8")) > RESULT_LIMIT:
        if len(compact["concerns"]) > 1:
            dropped = len(compact["concerns"]) - 1
            compact["concerns"] = compact["concerns"][:1]
            compact["concerns_omitted"] = dropped
            continue
        if len(compact.get("changed", [])) > 1:
            compact["changed_count"] = len(compact["changed"])
            compact["changed"] = compact["changed"][:1]
            continue
        if compact["concerns"]:
            compact["concerns_omitted"] = compact.get("concerns_omitted", 0) + 1
            compact["concerns"] = []
            continue
        compact["blocker"] = _truncate(compact["blocker"], 120)
        break
    return compact


def emit_result(result: dict) -> None:
    sys.stdout.write(json.dumps(compact_result(result), ensure_ascii=False) + "\n")


def _error_result(error: LocalImplementError) -> dict:
    needs_context = {"NO_FILES_SECTION", "MISSING_BRIEF", "EMPTY_BRIEF",
                     "MISSING_CONTEXT", "EMPTY_CONTEXT"}
    verify_failed = {"INVALID_RESPONSE", "UNDECLARED_PATH", "DIRTY_PATH_CONFLICT"}
    if error.code in needs_context:
        status = "NEEDS_CONTEXT"
    elif error.code in verify_failed:
        status = "VERIFY_FAILED"
    else:
        status = "BLOCKED"
    return {"status": status, "code": error.code, "message": error.message,
            "changed": [], "tests": {"command": "", "result": "not_run"},
            "concerns": [], "blocker": error.message, "report": "",
            "repair_rounds_used": 0,
            "verified": {"base": "", "paths_allowed": error.code != "UNDECLARED_PATH",
                         "untouched_dirty": error.code != "DIRTY_PATH_CONFLICT",
                         "report_written": False},
            "artifacts": ""}


def run_skill(argv: Sequence[str]) -> dict:
    artifacts = None
    try:
        dispatch = load_dispatch(parse_argv(argv))
        artifacts = create_artifacts()
        proposal, changed, run, used = implement(dispatch, artifacts)
        write_report(dispatch, proposal, changed, run, used, artifacts)
        return build_result(dispatch, proposal, changed, run, used, artifacts)
    except LocalImplementError as error:
        result = _error_result(error)
        if artifacts is not None:
            result["artifacts"] = str(artifacts.root)
        return result


def main(argv: Optional[Sequence[str]] = None) -> int:
    result = run_skill(list(sys.argv[1:] if argv is None else argv))
    emit_result(result)
    return 0 if result["status"] in ("DONE", "DONE_WITH_CONCERNS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/local-implement/tests -v`
Expected: PASS — the whole suite, Tasks 1–4.

- [ ] **Step 5: Commit**

```bash
git add skills/local-implement/scripts/local_implement.py skills/local-implement/tests/test_local_implement.py
git commit -m "feat(local-implement): write the SDD report and emit a bounded result"
```

---

### Task 5: SKILL.md

**Files:**
- Create: `skills/local-implement/SKILL.md`

**Interfaces:**
- Consumes: the runner's CLI contract from Tasks 1–4 (`--brief`, `--report`, `--context`, `--base`, `--workdir`, `--repair-rounds`, `--test-cmd`) and its result keys.
- Produces: the caller-facing contract; no code.

- [ ] **Step 1: Write the skill file**

Create `skills/local-implement/SKILL.md` with exactly this content:

```markdown
---
name: local-implement
description: Use when an authorized workflow needs one already-planned implementation task written by a local model instead of a Claude implementer subagent. Triggers: local implement, ローカル実装, local implementer
---

# local-implement

Requires Python 3.9+, Git, and Ollama with `qwen3.8:27b-q8_0`.
`FORTE_LOCAL_IMPL_MODEL` overrides the model; `FORTE_LOCAL_IMPL_TIMEOUT` overrides
the 1800-second deadline. The runner performs every side effect: the model only
returns file contents as data.

1. The caller records BASE, writes the task brief with SDD's `scripts/task-brief`,
   and writes a context file that MUST carry the plan's Global Constraints
   verbatim, prior-task interfaces, the caller's rulings on any ambiguity, and a
   `## Files` section listing every path the task creates or modifies. That list
   is the runner's write allowlist.
2. Resolve `scripts/local_implement.py` relative to THIS skill and run once, with
   the target repository as cwd:

   ```sh
   python3 "<resolved-skill-directory>/scripts/local_implement.py" \
     --brief PATH --report PATH --context PATH --base SHA \
     [--workdir DIR] [--repair-rounds 0|1] [--test-cmd ARGV...]
   ```

3. `--test-cmd` is the plan's verification command and is the only command
   executed. Model-suggested commands are recorded in the report, never run.
4. Read the one-line JSON result. `DONE` / `DONE_WITH_CONCERNS` mean the declared
   tests passed; `BLOCKED`, `NEEDS_CONTEXT`, and `VERIFY_FAILED` mean the caller
   takes the task over. Open the report file when reviewing; open the artifacts
   directory only when the result is unclear.

The caller stages and commits the changed paths afterwards — the runner never
stages, commits, pushes, resets, checks out, or changes branches, and never
writes outside the declared paths. On failure it leaves the working tree as-is so
the caller can decide whether to keep the partial work.

Load only its ≤2 KiB result; do not read the runner, prompt, or raw model output
during normal use. Wait on that command session. A lost session means unknown.

One task per invocation. No retry beyond the single self-repair round, no cloud
fallback, no model pull, no batching, no caller substitute. Its run is terminal:
do not invoke this skill around it. `/forte:local-implement` stays explicit.
```

- [ ] **Step 2: Verify the line budget and frontmatter**

Run: `wc -l skills/local-implement/SKILL.md && head -5 skills/local-implement/SKILL.md`
Expected: at most 60 lines, and the frontmatter shows `name: local-implement`.

- [ ] **Step 3: Verify the documented invocation matches the runner**

Run: `python3 skills/local-implement/scripts/local_implement.py --brief x 2>&1 | head -2`
Expected: a single JSON line with `"code":"BAD_ARGUMENTS"` whose message lists exactly the flags documented in the skill file.

- [ ] **Step 4: Commit**

```bash
git add skills/local-implement/SKILL.md
git commit -m "docs(local-implement): add the skill contract"
```

---

### Task 6: autopilot integration

**Files:**
- Modify: `skills/autopilot/SKILL.md` (Inputs section, Stage 5, Stage 8 table, Quick Reference, Common Mistakes)

**Interfaces:**
- Consumes: `forte:local-implement`'s CLI contract and result statuses from Tasks 4–5.
- Produces: the `--local-impl` pipeline flag and its standing answers; no code.

- [ ] **Step 1: Add the flag to the Inputs section**

In `skills/autopilot/SKILL.md`, immediately after the `--branch <name>` bullet in `## Inputs`, insert:

```markdown
- **`--local-impl`** (optional) — run each task's **initial implementation** on the local model
  via `forte:local-implement` instead of a Claude implementer subagent. Opt-in: the default is
  off, because the local model's per-task success rate and wall clock are not yet measured.
  Review, fix rounds, and commits stay on Claude either way.
```

- [ ] **Step 2: Add the Stage 5 standing answers**

In `### Stage 5: Implementation`, immediately before the `- **Rust diagnostics:**` bullet, insert:

```markdown
- **Local initial implementation (only when `--local-impl` was passed):**
  - Dispatch each task's initial implementation to `forte:local-implement` instead of the Agent
    tool. Record BASE, run SDD's `scripts/task-brief`, then write a context file beside the
    brief (`task-<N>-context.md`) carrying the plan's Global Constraints verbatim, prior-task
    interfaces, your rulings on any ambiguity in the brief, pointers to parked findings in the
    area, and a `## Files` section listing every path the task creates or modifies. Pass
    `--brief`, `--report`, `--context`, `--base`, and `--test-cmd` (the plan's verification
    command) — the `## Files` list is the runner's write allowlist.
  - A task whose files cannot be declared up front is not a fit: dispatch a Claude implementer
    for it and note why in the ledger.
  - **Batching is disabled under `--local-impl`** — one local run per task, even for small
    same-shape tasks SDD would otherwise combine.
  - On `DONE` / `DONE_WITH_CONCERNS`: verify the result yourself before reviewing — every
    changed path was declared, no path that was already dirty changed, the report file is
    non-empty, and the declared test command actually ran with its output in the report. Then
    stage exactly the changed paths and commit via `forte:qwen-commit` — the runner never
    commits. Only then generate the review package from the recorded BASE.
  - On `BLOCKED` / `NEEDS_CONTEXT` / `VERIFY_FAILED`, or any runner failure: fall back to a
    Claude implementer for that task, carrying the brief path, the same report path, and the
    working-tree state (`git status --porcelain`, `git diff --stat`). **Never** reset, check
    out, stash, or otherwise discard the partial work — the Claude implementer decides whether
    to build on it.
  - **Fix rounds always use a fresh Claude implementer.** SDD normally resumes the original
    implementer for rounds 1–3; a local run leaves no resumable agent, so take SDD's documented
    fallback for harnesses that cannot resume a live session: a fresh implementer with the
    brief path, the same report file path, and the findings.
  - Append one ledger line per task: `LOCAL-IMPL: task <N> → <ok|fallback> (<reason>)`.
```

- [ ] **Step 3: Add the Stage 8 report line**

In the Stage 8 report template, immediately after the `| 5 Implementation | ... |` row, insert:

```markdown
| 5a ローカル実装 | {N件成功 / M件フォールバック / 未使用} | {LOCAL-IMPL ledger lines} |
```

- [ ] **Step 4: Extend Quick Reference and Common Mistakes**

In `## Quick Reference`, replace the `| Input |` row's value with:

```markdown
| Input | feature description and/or spec path (+ optional `--branch <name>`, `--local-impl`) |
```

Append to `## Common Mistakes`:

```markdown
- **Letting the local implementer commit, or committing for it with `git add -A`** — the runner
  never commits; the pipeline stages exactly the paths it reported as changed.
- **Discarding a failed local run's partial work** — fall back with the working-tree state
  attached; resetting or checking out is a destructive operation reserved for the human.
- **Resuming an implementer that does not exist** — after a local run, fix round R1 is a fresh
  Claude implementer, not a resume.
- **Batching tasks under `--local-impl`** — one local run per task.
```

- [ ] **Step 5: Verify the edits are consistent**

Run: `grep -n "local-impl\|LOCAL-IMPL\|local-implement" skills/autopilot/SKILL.md`
Expected: matches in Inputs, Stage 5 (multiple), Stage 8, Quick Reference, and Common Mistakes — and no occurrence describing the runner as committing.

- [ ] **Step 6: Commit**

```bash
git add skills/autopilot/SKILL.md
git commit -m "feat(autopilot): add opt-in --local-impl initial implementation"
```

---

### Task 7: Registration and version bump

**Files:**
- Modify: `CLAUDE.md` (repository structure list and the Key Patterns section)
- Modify: `README.md` (Skills section and the test-command list)
- Modify: `.claude-plugin/plugin.json` (version)

**Interfaces:**
- Consumes: the skill name and behaviour from Tasks 4–6.
- Produces: nothing consumed by later tasks (final task).

- [ ] **Step 1: Register the skill in CLAUDE.md**

In `CLAUDE.md`, inside the repository-structure code block, insert this line in alphabetical
order between the `investigation-board/` and `parallel-research/` lines:

```text
  local-implement/      # Local-model initial implementation for one SDD task (runner owns all side effects)
```

Then, in the **Automatic local-runner skills** bullet of `### Key Patterns Across Skills`,
replace that bullet with:

```markdown
- **Automatic local-runner skills** (rust-diagnostics, qwen-commit, local-implement): Route ordinary Cargo diagnostics, authorized commits, and opt-in local implementation of one planned task through short skills whose standard-library runners keep raw inputs outside caller context. The runners are terminal execution steps and are never wrapped recursively. `local-implement` additionally owns every side effect of an implementation attempt — the model only returns file contents as data — and never creates commits.
```

- [ ] **Step 2: Document the skill in README.md**

In `README.md`, after the `### forte:qwen-commit` section and before the section that follows
it, insert:

```markdown
### forte:local-implement

Produce one already-planned implementation task with a local model instead of a
Claude implementer subagent. A local Python runner builds the prompt from the SDD
task brief and a caller-written context file, asks Ollama for the complete new
content of each declared file, applies only the declared paths, runs the caller's
test command, allows one self-repair round if those tests fail, writes the SDD
report file, and returns at most 2 KiB of JSON.

```text
/forte:local-implement --brief .superpowers/sdd/plan/task-1-brief.md \
  --report .superpowers/sdd/plan/task-1-report.md \
  --context .superpowers/sdd/plan/task-1-context.md \
  --base $(git rev-parse HEAD) --test-cmd python3 -m unittest -q
```

The context file's `## Files` section is the write allowlist: the runner refuses
any other path, refuses a path that already had uncommitted changes, and never
stages, commits, or changes Git state — the caller commits after verifying. Model
suggested commands are recorded in the report and never executed. Generation has
a 1,800-second deadline, a 48 KiB prompt limit, a 16 KiB per-file limit, and no
retry or cloud fallback beyond the single self-repair round.

Requires Python 3.9+, Git, and a running Ollama service with `qwen3.8:27b-q8_0`.
`FORTE_LOCAL_IMPL_MODEL` selects another installed model and
`FORTE_LOCAL_IMPL_TIMEOUT` changes the deadline. The full test log and raw model
output stay in the mode-0700 temporary directory named by the result.

`autopilot --local-impl` opts the pipeline into using this skill for Stage 5's
initial implementation; review and fix rounds stay on Claude.
```

Then add this line to the test-command list next to the two existing ones:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/local-implement/tests -v
```

- [ ] **Step 3: Bump the plugin version**

In `.claude-plugin/plugin.json`, change the version line to:

```json
  "version": "1.41.0",
```

- [ ] **Step 4: Verify registration and the full suite**

Run:
```bash
grep -n "local-implement" CLAUDE.md README.md .claude-plugin/plugin.json
python3 -c "import json;print(json.load(open('.claude-plugin/plugin.json'))['version'])"
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/local-implement/tests -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/qwen-commit/tests -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/rust-diagnostics/tests -v
```
Expected: `local-implement` appears in `CLAUDE.md` and `README.md` (no match needed in
`plugin.json`), the version prints `1.41.0`, and all three suites pass.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md README.md .claude-plugin/plugin.json
git commit -m "chore: register local-implement and bump version to 1.41.0"
```

---

## Self-Review

**1. Spec coverage**

| Spec requirement | Task |
|---|---|
| Interface: `--brief`, `--report`, `--context`, `--base`, `--test-cmd`, `--workdir`, `--repair-rounds` | 1 |
| `## Files` contract as write allowlist; `NEEDS_CONTEXT` when undeclarable | 1, 4, 6 |
| Preflight: worktree, base, brief/context, path legality, Ollama, model, `INPUT_TOO_LARGE` | 1 |
| Generation: native API, `num_ctx` 65536, `num_predict` 16384, `think: false`, schema, model env | 2 |
| Whole file contents, never diffs; model output is data | 2 |
| Prompt built in the runner from brief + context + current contents / `NEW FILE` marker | 2 |
| Application: allowlist, dirty-path protection, atomic write, mode preserved, never `.git/` | 3 |
| Declared tests only; model-proposed commands never executed | 3 |
| One self-repair round, `--repair-rounds` 0/1 | 3 |
| Process-group termination on timeout, confirmed | 3 |
| Report written by the runner with real test evidence and unexecuted suggestions | 4 |
| Status ownership: model statuses vs runner-substituted `NEEDS_CONTEXT` / `VERIFY_FAILED` | 4 |
| Bounded ≤2 KiB result; prompt and raw output kept in mode-0700 artifacts | 3, 4 |
| No staging, commit, push, reset, checkout, stash, branch change | 3, 4, verified in 4 |
| autopilot `--local-impl`, Stage 5 standing answers, batching disabled, fresh-Claude fix rounds, controller commit, ledger line, Stage 8 line | 6 |
| Deliverables: SKILL.md, runner, tests, autopilot revision, registration, 1.41.0 | 5, 1–4, 6, 7 |
| No `SETUP.md`, no `schema/result.schema.json` | not created anywhere |

Spec validation items 1–9 are covered by Tasks 1–4's tests. Validation item 10 (end-to-end
through `autopilot --local-impl` on a real plan task, with wall-clock measurement) is
deliberately **not** a task in this plan: it requires a separate real pipeline run after this
plan lands, and the spec keeps `--local-impl` off by default until it exists.

**2. Placeholder scan**

No `TBD`/`TODO` markers; every code step carries its actual content; the SKILL.md, autopilot
inserts, CLAUDE.md, and README text are given verbatim rather than described.

**3. Type consistency**

`Dispatch`, `Proposal`, `TestRun`, `Artifacts` field names are used identically in Tasks 1–4 and
in the tests. `parse_argv` returns the same key set (`brief`, `report`, `context`, `base`,
`workdir`, `repair_rounds`, `test_cmd`) that `load_dispatch` reads and that `DispatchFixture.options`
builds. `validate_declared_path`, `dirty_digests`, `write_atomic`, `_failure_excerpt`, and
`_terminate_process_group` are each defined once and called with the signatures declared in the
Interfaces blocks. `implement` returns the 4-tuple `(proposal, changed, run, used)` that
`write_report`, `build_result`, and the tests all unpack in that order.
