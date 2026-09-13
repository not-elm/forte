#!/usr/bin/env python3
"""Implement one SDD task with a local model; this runner performs every side effect."""
from dataclasses import dataclass
import http.client
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import threading
import time
from typing import Optional, Sequence, Tuple


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
        entry = re.sub(r"^[-*]\s*", "", entry).strip().strip("`").strip()
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
