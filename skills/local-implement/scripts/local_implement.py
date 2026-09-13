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
