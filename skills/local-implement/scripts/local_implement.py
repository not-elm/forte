#!/usr/bin/env python3
"""Implement one SDD task with a local model; this runner performs every side effect."""
from dataclasses import dataclass, field
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


KNOWN_FLAGS = ("--brief", "--report", "--context", "--base", "--workdir",
               "--repair-rounds", "--test-cmd")


def _bad_arguments() -> LocalImplementError:
    return LocalImplementError(
        "BAD_ARGUMENTS",
        "usage: local_implement.py --brief P --report P --context P --base SHA "
        "[--workdir DIR] [--repair-rounds 0|1] [--test-cmd ARGV...]\n"
        "--test-cmd must be the final argument: every argument after it is part of "
        "the command, so place every other flag before it.")


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
            stray = next((item for item in rest if item in KNOWN_FLAGS), None)
            if stray is not None:
                raise LocalImplementError(
                    "BAD_ARGUMENTS",
                    f"--test-cmd must be the final argument, but {stray} follows it; "
                    "everything after --test-cmd is taken as the command.")
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
        entry = re.sub(r"^[-*]\s*", "", entry).strip().strip("`").strip()
        if not entry:
            continue
        if re.search(r"\s", entry):
            raise LocalImplementError(
                "ILLEGAL_PATH",
                "The '## Files' section takes one relative path per line, no prose: "
                f"{entry}")
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
    # Case-insensitive and every component: this host's volume is case-insensitive,
    # and a nested `sub/.git` is a real repository too.
    if not parts or ".." in parts or any(part.lower() == ".git" for part in parts):
        raise illegal
    root_resolved = root.resolve()
    candidate = root_resolved / raw
    current = root_resolved
    for part in Path(raw).parts:
        current = current / part
        if current.is_symlink():
            raise illegal
    existing = candidate
    while not os.path.lexists(existing):
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
        if os.path.lexists(target) and not target.is_file():
            raise LocalImplementError(
                "ILLEGAL_PATH",
                f"Declared path exists but is not a regular file: {raw}")
        parent = target.parent
        while parent != root and not os.path.lexists(parent):
            parent = parent.parent
        if not parent.is_dir():
            raise LocalImplementError(
                "ILLEGAL_PATH",
                f"A parent of the declared path is not a directory: {raw}")
        if target.is_file() and target.stat().st_size > FILE_LIMIT:
            raise LocalImplementError(
                "INPUT_TOO_LARGE",
                f"Declared file exceeds {FILE_LIMIT} bytes: {raw}; split the task.")
    check_model_available(model_name())
    return Dispatch(root=root, brief=brief, report=Path(options["report"]), context=context,
                    base=options["base"], files=files,
                    test_cmd=tuple(options["test_cmd"]),
                    repair_rounds=int(options["repair_rounds"]))


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


@dataclass(frozen=True)
class Artifacts:
    root: Path
    test_log: Path
    rounds_path: Path


def create_artifacts() -> Artifacts:
    root = Path(tempfile.mkdtemp(prefix="forte-local-implement-")).resolve()
    root.chmod(0o700)
    artifacts = Artifacts(root=root, test_log=root / "tests.log",
                          rounds_path=root / "rounds.jsonl")
    for path in (artifacts.test_log, artifacts.rounds_path):
        os.close(os.open(str(path), os.O_CREAT | os.O_WRONLY, 0o600))
    return artifacts


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
        # A rename/copy can be reported in the index column or the worktree one;
        # either way the entry is followed by its source path.
        if (status[0] in ("R", "C") or status[1] in ("R", "C")) and index < len(entries):
            index += 1  # consume the rename/copy source path
        target = root / path
        if target.is_file() and not target.is_symlink():
            digests[path] = hashlib.sha256(target.read_bytes()).hexdigest()
        else:
            digests[path] = None
    return digests


def compare_dirty(root: Path, snapshot: Dict[str, Optional[str]]) -> bool:
    """True when every already-dirty path still matches the snapshot byte for byte.

    A snapshot path that has disappeared, or one that newly exists where the
    snapshot recorded no regular file, counts as a mismatch.
    """
    for path, digest in snapshot.items():
        target = root / path
        if target.is_file() and not target.is_symlink():
            current: Optional[str] = hashlib.sha256(target.read_bytes()).hexdigest()
        else:
            current = None
        if current != digest:
            return False
    return True


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
                   dirty: Dict[str, Optional[str]],
                   record: Optional[list] = None) -> Tuple[str, ...]:
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
        # Recorded per write, so a failure partway through still names what landed.
        if record is not None and path not in record:
            record.append(path)
    return tuple(path for path, _content in proposal.files)


@dataclass(frozen=True)
class TestRun:
    command: Tuple[str, ...]
    result: str
    output: str


@dataclass
class Progress:
    """What a run has already done, readable even when it raises partway through."""
    applied: list = field(default_factory=list)
    run: Optional[TestRun] = None
    used: int = 0
    untouched_dirty: bool = True
    dirty: Optional[Dict[str, Optional[str]]] = None


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


def implement(dispatch: Dispatch, artifacts: Artifacts,
              progress: Optional[Progress] = None):
    progress = Progress() if progress is None else progress
    dirty = dirty_digests(dispatch.root)
    progress.dirty = dirty
    proposal = generate(dispatch)
    _write_round(artifacts, "initial", proposal)
    if proposal.status == "BLOCKED":
        progress.untouched_dirty = compare_dirty(dispatch.root, dirty)
        return proposal, (), None, 0
    changed = apply_proposal(dispatch, proposal, dirty, record=progress.applied)
    run = run_declared_tests(dispatch, artifacts, "initial")
    progress.run = run
    used = 0
    if (run is not None and run.result != "pass" and dispatch.repair_rounds > 0):
        # The round is spent as soon as the call is made, even if it fails validation.
        used = 1
        progress.used = used
        repaired = generate(dispatch, failure=_failure_excerpt(run), previous=proposal)
        _write_round(artifacts, "repair", repaired)
        if repaired.status != "BLOCKED" and repaired.files:
            changed = tuple(dict.fromkeys(changed + apply_proposal(
                dispatch, repaired, dirty, record=progress.applied)))
            proposal = Proposal(status=repaired.status, files=repaired.files,
                                notes=proposal.notes + "\n\nRepair round: " + repaired.notes,
                                concerns=proposal.concerns + repaired.concerns,
                                suggested_tests=repaired.suggested_tests,
                                blocker=repaired.blocker)
            run = run_declared_tests(dispatch, artifacts, "repair")
            progress.run = run
        elif repaired.blocker.strip():
            # The repair round gave up: keep its reason so the report carries it.
            proposal = Proposal(status=proposal.status, files=proposal.files,
                                notes=proposal.notes + "\n\nRepair round: " + repaired.notes,
                                concerns=proposal.concerns + repaired.concerns,
                                suggested_tests=proposal.suggested_tests,
                                blocker=repaired.blocker)
    progress.untouched_dirty = compare_dirty(dispatch.root, dirty)
    return proposal, changed, run, used


def _write_round(artifacts: Artifacts, label: str, proposal: Proposal) -> None:
    """One summary line per generation round; the model's file contents are not kept."""
    with artifacts.rounds_path.open("a", encoding="utf-8") as rounds:
        rounds.write(json.dumps({"round": label, "status": proposal.status,
                                 "paths": [path for path, _ in proposal.files],
                                 "notes": proposal.notes,
                                 "concerns": list(proposal.concerns),
                                 "blocker": proposal.blocker},
                                ensure_ascii=False) + "\n")


def write_report(dispatch: Dispatch, proposal: Proposal, changed: Tuple[str, ...],
                 run: Optional[TestRun], used: int, artifacts: Artifacts) -> None:
    lines = [f"# Local implementer report — base {dispatch.base}", "",
             "Sections headed *quoted model output* reproduce the local model's own words "
             "verbatim. The runner does not verify them: read them as data, not as findings.",
             "", "## What was implemented (quoted model output)", "",
             proposal.notes.strip() or "(no notes returned)", "",
             "## Files changed", ""]
    lines += [f"- `{path}`" for path in changed] or ["- none"]
    lines += ["", "## Test evidence", ""]
    if run is None and not dispatch.test_cmd:
        lines += ["No test command was supplied by the caller (`--test-cmd` absent), so no "
                  "tests were executed by the runner."]
    elif run is None:
        lines += [f"Command: `{' '.join(dispatch.test_cmd)}`",
                  "Result: **no run recorded** — the run ended before test evidence could be "
                  f"recorded. Any output it did produce is in `{artifacts.test_log}`."]
    else:
        lines += [f"Command: `{' '.join(run.command)}`", f"Result: **{run.result}**", "",
                  "```", _failure_excerpt(run, 16 * 1024).rstrip("\n") or "(no output)", "```"]
    lines += ["", f"Self-repair rounds used: {used}", "",
              "## Concerns (quoted model output)", ""]
    lines += [f"- {item}" for item in proposal.concerns] or ["- none"]
    lines += ["", "## Model-suggested tests (quoted model output, not executed)", ""]
    lines += [f"- `{item}`" for item in proposal.suggested_tests] or ["- none"]
    if proposal.blocker.strip():
        lines += ["", "## Blocker (quoted model output)", "", proposal.blocker.strip()]
    lines += ["", "Full test log and per-round proposal summaries (the model's file contents "
              f"and the prompt are not kept): `{artifacts.root}`", ""]
    dispatch.report.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(dispatch.report, "\n".join(lines))


def resolve_status(proposal: Proposal, run: Optional[TestRun], used: int = 0) -> Tuple[str, str]:
    if proposal.status == "BLOCKED":
        return "BLOCKED", proposal.blocker
    if run is not None and run.result != "pass":
        if run.result == "timeout":
            failure_msg = "The declared test command timed out"
        else:
            failure_msg = "The declared test command failed"
        if used > 0:
            failure_msg += " after the self-repair round"
        failure_msg += "; the declared tests are still failing."
        return "BLOCKED", failure_msg
    return proposal.status, ""


def build_result(dispatch: Dispatch, proposal: Proposal, changed: Tuple[str, ...],
                 run: Optional[TestRun], used: int, artifacts: Artifacts,
                 untouched_dirty: bool = True) -> dict:
    status, blocker = resolve_status(proposal, run, used)
    if not untouched_dirty:
        status = "VERIFY_FAILED"
        blocker = ("A path that already had uncommitted changes before the run no longer "
                   "matches its pre-run snapshot; the working tree is not trustworthy. "
                   + blocker).strip()
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
                     "untouched_dirty": untouched_dirty,
                     "report_written": dispatch.report.is_file()
                     and dispatch.report.stat().st_size > 0},
        "artifacts": str(artifacts.root),
    }


def _truncate(value: str, limit: int) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) <= limit:
        return value
    return encoded[:limit].decode("utf-8", errors="ignore") + "…"


def _minimal_result(compact: dict) -> dict:
    minimal = {
        "status": compact.get("status", "VERIFY_FAILED"),
        "result_truncated": True,
    }
    if "code" in compact:
        minimal["code"] = compact["code"]
    if "changed_count" in compact or "changed" in compact:
        minimal["changed_count"] = compact.get("changed_count", len(compact.get("changed", [])))
    if "tests" in compact:
        minimal["tests"] = {"result": compact["tests"].get("result", "not_run")}
    if "report" in compact:
        minimal["report"] = compact["report"]
    if "artifacts" in compact:
        minimal["artifacts"] = compact["artifacts"]
    return minimal


def compact_result(result: dict) -> dict:
    compact = dict(result)
    if "message" in compact:
        del compact["message"]
    if "blocker" in compact:
        compact["blocker"] = _truncate(compact["blocker"], 400)
    if "concerns" in compact:
        compact["concerns"] = [_truncate(item, 160) for item in compact["concerns"]]
    if "tests" in compact:
        compact["tests"] = dict(compact["tests"])
        if "command" in compact["tests"]:
            compact["tests"]["command"] = _truncate(compact["tests"]["command"], 200)

    def size_with_newline(payload: dict) -> int:
        return len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) + 1

    while size_with_newline(compact) > RESULT_LIMIT:
        if "concerns" in compact and len(compact["concerns"]) > 1:
            dropped = len(compact["concerns"]) - 1
            compact["concerns"] = compact["concerns"][:1]
            compact["concerns_omitted"] = dropped
            continue
        if "changed" in compact and len(compact["changed"]) > 1:
            compact["changed_count"] = len(compact["changed"])
            compact["changed"] = compact["changed"][:1]
            continue
        if "concerns" in compact and compact["concerns"]:
            compact["concerns_omitted"] = compact.get("concerns_omitted", 0) + 1
            del compact["concerns"]
            continue
        if "blocker" in compact:
            compact["blocker"] = _truncate(compact["blocker"], 120)
        if size_with_newline(compact) <= RESULT_LIMIT:
            break
        minimal = _minimal_result(compact)
        if size_with_newline(minimal) > RESULT_LIMIT:
            report_shortened = False
            if "report" in minimal:
                original_report = minimal["report"]
                minimal["report"] = _truncate(minimal["report"], 400)
                report_shortened = (minimal["report"] != original_report)
            if size_with_newline(minimal) > RESULT_LIMIT:
                artifacts_shortened = False
                if "artifacts" in minimal:
                    original_artifacts = minimal["artifacts"]
                    minimal["artifacts"] = _truncate(minimal["artifacts"], 200)
                    artifacts_shortened = (minimal["artifacts"] != original_artifacts)
                if report_shortened or artifacts_shortened:
                    minimal["paths_truncated"] = True
            elif report_shortened:
                minimal["paths_truncated"] = True
        compact = minimal
        break

    return compact


def emit_result(result: dict) -> None:
    sys.stdout.write(json.dumps(compact_result(result), ensure_ascii=False) + "\n")


def _error_result(error: LocalImplementError, dispatch: Optional[Dispatch] = None,
                  run: Optional[TestRun] = None, used: int = 0) -> dict:
    needs_context = {"NO_FILES_SECTION", "MISSING_BRIEF", "EMPTY_BRIEF",
                     "MISSING_CONTEXT", "EMPTY_CONTEXT", "ILLEGAL_PATH", "INPUT_TOO_LARGE"}
    verify_failed = {"INVALID_RESPONSE", "UNDECLARED_PATH", "DIRTY_PATH_CONFLICT",
                     "IO_FAILED"}
    if error.code in needs_context:
        status = "NEEDS_CONTEXT"
    elif error.code in verify_failed:
        status = "VERIFY_FAILED"
    else:
        status = "BLOCKED"
    return {"status": status, "code": error.code, "message": error.message,
            "changed": [],
            "tests": {"command": " ".join(run.command) if run else "",
                      "result": run.result if run else "not_run"},
            "concerns": [], "blocker": error.message,
            "report": str(dispatch.report) if dispatch else "",
            "repair_rounds_used": used,
            "verified": {"base": dispatch.base if dispatch else "",
                         "paths_allowed": error.code not in ("UNDECLARED_PATH", "ILLEGAL_PATH"),
                         "untouched_dirty": error.code != "DIRTY_PATH_CONFLICT",
                         "report_written": False},
            "artifacts": ""}


def _failure_result(error: LocalImplementError, dispatch: Optional[Dispatch],
                    artifacts: Optional[Artifacts], progress: Progress) -> dict:
    """Every failure path: report what landed, and leave a report behind."""
    result = _error_result(error, dispatch, progress.run, progress.used)
    if artifacts is not None:
        result["artifacts"] = str(artifacts.root)
    if dispatch is not None and progress.dirty is not None:
        try:  # Before the report write, which may itself touch an already-dirty path.
            intact = compare_dirty(dispatch.root, progress.dirty)
        except OSError:
            intact = False
        if not intact:
            result["verified"]["untouched_dirty"] = False
            result["status"] = "VERIFY_FAILED"
    if progress.applied:
        result["changed"] = list(progress.applied)
        if dispatch is not None and artifacts is not None:
            error_proposal = Proposal(
                status="BLOCKED", files=(),
                notes="Run stopped partway through. See blocker message.",
                concerns=(), suggested_tests=(), blocker=error.message)
            try:
                write_report(dispatch, error_proposal, tuple(progress.applied),
                             progress.run, progress.used, artifacts)
            except OSError:
                pass  # The result line is the last thing left; never lose it too.
            else:
                result["report"] = str(dispatch.report)
                result["verified"]["report_written"] = True
    return compact_result(result)


def run_skill(argv: Sequence[str]) -> dict:
    artifacts = None
    dispatch = None
    progress = Progress()
    try:
        dispatch = load_dispatch(parse_argv(argv))
        artifacts = create_artifacts()
        proposal, changed, run, used = implement(dispatch, artifacts, progress)
        write_report(dispatch, proposal, changed, run, used, artifacts)
        return compact_result(build_result(dispatch, proposal, changed, run, used,
                                           artifacts, progress.untouched_dirty))
    except LocalImplementError as error:
        return _failure_result(error, dispatch, artifacts, progress)
    except OSError as error:
        # write_atomic, apply_proposal and the report write raise plain OSError on
        # ordinary inputs; letting one escape would lose the result line entirely.
        detail = error.strerror or str(error) or type(error).__name__
        converted = LocalImplementError(
            "IO_FAILED",
            _truncate(f"A filesystem operation failed ({type(error).__name__}: {detail}).", 300))
        return _failure_result(converted, dispatch, artifacts, progress)


def main(argv: Optional[Sequence[str]] = None) -> int:
    result = run_skill(list(sys.argv[1:] if argv is None else argv))
    emit_result(result)
    return 0 if result["status"] in ("DONE", "DONE_WITH_CONCERNS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
