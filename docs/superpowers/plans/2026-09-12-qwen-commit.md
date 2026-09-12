# Qwen Commit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Commit staged changes through local Qwen with minimal calling-model token consumption.

**Architecture:** A short skill launches one Python standard-library runner. The runner snapshots staged Git trees, sends a bounded prompt to local Ollama, validates the message and repository state, commits, and returns one bounded JSON line.

**Tech Stack:** Python 3.9+, unittest, Git CLI, Ollama HTTP API.

**Spec:** `docs/superpowers/specs/2026-09-12-qwen-commit-design.md` (approved by the user on 2026-09-12).

## Global Constraints

- Python 3 standard-library runner; no additional Python packages or agent delegation at runtime.
- Fixed endpoint: `http://127.0.0.1:11434/api/generate`. Disable proxy use and HTTP redirects.
- Model: `QWEN_COMMIT_MODEL`, default `qwen3.8:27b-q8_0`.
- Request deadline: 300 seconds. No automatic retries, cloud fallback, or model pulls.
- Generation: `stream: false`, `think: false`, `num_ctx: 32768`, `num_predict: 512`.
- Complete prompt limit: 24 KiB UTF-8. Message limit: 4 KiB. Subject limit: 100 characters. Output limit: 1 KiB including newline.
- English Conventional Commits with required subject and optionally empty body.
- Staged changes only. Preserve hooks, signing, identity, and unstaged changes. Never automatically stage, push, amend, or bypass host permissions.
- Target at most 60 lines for `SKILL.md`; do not load implementation or diffs into caller context during normal use.
- Use the existing Python 3.9.6 environment without installing dependencies.

## File map

| File | Responsibility |
|---|---|
| `skills/qwen-commit/scripts/qwen_commit.py` | Snapshot, prompt, local transport, message validation, commit, output. |
| `skills/qwen-commit/tests/test_qwen_commit.py` | Behavioral tests with isolated Git repositories and local HTTP stub. |
| `skills/qwen-commit/SKILL.md` | Minimal invocation contract for the calling assistant. |
| `README.md` | Usage, prerequisites, configuration, limitations. |
| `CLAUDE.md` | Repository structure entry. |
| `.claude-plugin/plugin.json` | Patch release from 1.39.0 to 1.39.1. |

Keep the runner as one cohesive executable and the tests as one companion module. Use named functions and a small immutable snapshot type; do not add an engine framework.

### Task 1: Snapshot staged changes and build a bounded prompt

**Files:** Create the runner and test module listed above.

**Interfaces:**
- `CommitError(code: str, message: str, committed: object = False)` carries bounded diagnostic data.
- `Snapshot` is a frozen dataclass with `root: Path`, `head: Optional[str]`, and `tree: str`.
- `git(root: Path, *args: str, input_data: Optional[bytes] = None) -> bytes` invokes Git through an argument array, captures output, and raises a sanitized error on failure.
- `snapshot(root: Path) -> Snapshot` validates state and captures immutable identities.
- `build_prompt(state: Snapshot) -> str` uses the captured trees and rejects oversized input.

- [ ] **1. Write failing integration tests** using `unittest`, `TemporaryDirectory`, and subprocess Git with temporary HOME/global config isolation. Configure test-only identity and disable signing. Stage a file, modify its working copy, and assert that only staged text reaches the prompt:

```python
def test_prompt_uses_staged_snapshot(self):
    self.stage("example.txt", "staged marker\n")
    state = qc.snapshot(self.root)
    (self.root / "example.txt").write_text("unstaged marker\n")
    prompt = qc.build_prompt(state)
    self.assertIn("staged marker", prompt)
    self.assertNotIn("unstaged marker", prompt)
```

Add concrete cases for no repository, an empty index, an unborn HEAD with a staged file, a conflict index, and each operation marker (`MERGE_HEAD`, `CHERRY_PICK_HEAD`, `REVERT_HEAD`, `rebase-merge`, `rebase-apply`, `sequencer`). A file containing `"x" * 25000` must raise `INPUT_TOO_LARGE`. Use binary bytes `b"\x00\xff\x01"` to check metadata-only handling; stage a rename and deletion to check patch coverage.

- [ ] **2. Run the tests and confirm failure** because the runner interfaces do not yet exist:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/qwen-commit/tests -v
```

- [ ] **3. Implement snapshot and prompt functions.** Resolve the repository root and Git marker paths via `git rev-parse`; check conflicts with `git ls-files -u`; capture the index with `git write-tree`. For an unborn branch use an empty tree created by `git mktree` with empty stdin. Diff immutable trees, including staged changes only:

```python
patch = git(state.root, "-c", "diff.renames=false", "diff",
            "--no-ext-diff", "--no-textconv", "--no-color",
            "--no-renames", "--stat", "--patch", base_tree, state.tree, "--")
prompt = RULES + "\nSTAGED_GIT_DATA_JSON:\n" + json.dumps(
    patch.decode("utf-8", errors="replace"), ensure_ascii=False)
if len(prompt.encode("utf-8")) > 24 * 1024:
    raise CommitError("INPUT_TOO_LARGE", "Staged diff exceeds 24 KiB; split staged changes.")
```

`RULES` must require schema-shaped English Conventional Commit output, forbid following instructions embedded in the diff, forbid invented tests or binary semantics, and allow an empty body. Ensure the empty-index case compares the tree with the captured base tree.

- [ ] **4. Run the same test command and confirm the snapshot cases pass.**
- [ ] **5. Commit only the runner and test module** with subject `feat(qwen-commit): capture staged changes locally`.

### Task 2: Generate and validate messages through local Ollama

**Files:** Modify `skills/qwen-commit/scripts/qwen_commit.py` and `skills/qwen-commit/tests/test_qwen_commit.py`.

**Interfaces:**
- Consumes `build_prompt(state: Snapshot) -> str` and `CommitError` from Task 1.
- `generate_message(prompt: str) -> str` returns a validated message with a final newline.
- `validate_message(response: object) -> str` validates the Ollama envelope and nested JSON strings.
- `request_generation(payload: dict) -> dict` enforces the local endpoint, bounded response, and 300-second total deadline.

- [ ] **1. Add failing tests** with a loopback HTTP server on an ephemeral port, patching the module endpoint only in tests. Assert one request and the exact payload settings, test a valid subject/body, and verify no redirect or proxy is followed. Exercise HTTP 404, HTTP 500, invalid JSON, missing fields, non-string fields, response length overflow, `done: false`, and `done_reason: "length"`. Reject newline subjects, NUL, ANSI escape, overly long subjects, and oversized messages:

```python
def test_truncated_generation_is_rejected(self):
    envelope = {"done": True, "done_reason": "length",
                "response": json.dumps({"subject": "fix: repair parser", "body": ""})}
    with self.assertRaises(qc.CommitError) as caught:
        qc.validate_message(envelope)
    self.assertEqual(caught.exception.code, "INVALID_RESPONSE")
```

Use a stub that delays or drips bytes, with a patched short deadline, to prove total elapsed time is bounded and no retry occurs.

- [ ] **2. Run the same unittest command and observe failure in the new transport/validation cases.**
- [ ] **3. Implement the local request and validators.** Use a direct `http.client.HTTPConnection` (no environment proxies or automatic redirects). Enforce the total deadline while reading a bounded response, not just a socket inactivity timeout. Maximum response size is 64 KiB. Close the connection on every path. Build the payload inside the runner:

```python
payload = {"model": os.environ.get("QWEN_COMMIT_MODEL", "qwen3.8:27b-q8_0"),
           "prompt": prompt, "stream": False, "think": False,
           "format": {"type": "object", "required": ["subject", "body"],
                      "additionalProperties": False,
                      "properties": {"subject": {"type": "string"},
                                     "body": {"type": "string"}}},
           "options": {"num_ctx": 32768, "num_predict": 512}}
```

Accept only completed responses with `done_reason: "stop"`. Use a Conventional Commit regex with optional scope and breaking-change marker; require a nonblank description. Reject Unicode control/format characters except body line feeds. Decode and validate strictly; do not strip markdown fences or salvage malformed responses. Classify service failures without printing response bodies.

- [ ] **4. Run the unittest suite and confirm all transport and snapshot tests pass.**
- [ ] **5. Commit these two files** with subject `feat(qwen-commit): generate messages with local Ollama`.

### Task 3: Commit validated snapshots and return bounded results

**Files:** Modify `skills/qwen-commit/scripts/qwen_commit.py` and `skills/qwen-commit/tests/test_qwen_commit.py`.

**Interfaces:**
- Consumes `Snapshot`, `snapshot`, `build_prompt`, and `generate_message` from Tasks 1–2.
- `commit_snapshot(state: Snapshot, message: str) -> dict` rechecks state, commits, and verifies the outcome.
- `run(root: Path) -> dict` calls the complete pipeline once.
- `emit_result(result: dict) -> None` emits one UTF-8 JSON line, at most 1 KiB including newline.
- `main() -> int` converts exceptions to stable error output without tracebacks; unexpected errors after commit starts report unknown outcome.

- [ ] **1. Add failing full-workflow tests** using the HTTP stub and real Git. Check exactly one new commit, unchanged unstaged file contents, correct parent/tree, and actual subject. Mutate HEAD/index from the stub callback and assert no generated commit. Install executable `pre-commit` hooks that fail or stage an extra file and assert honored failure/unexpected-state detection. Test a commit-message hook that rewrites the subject. Use this literal message to prove no shell evaluation:

```python
subject = "fix: preserve $(touch injected) and `touch injected2` literally"
self.assertFalse((self.root / "injected").exists())
self.assertFalse((self.root / "injected2").exists())
```

Assert both literal preservation in the real commit and absence of those files after execution. Check normal output contains no staged marker, prompt rules, or raw server/hook error. A 2,000-character hook-written subject must leave the full commit subject intact while the result reports truncation within 1 KiB.

- [ ] **2. Run the unittest suite and confirm the new end-to-end cases fail.**
- [ ] **3. Implement commit and CLI.** Revalidate markers, HEAD, and tree immediately before commit. Use a private temporary message file and argument arrays:

```python
with tempfile.TemporaryDirectory(prefix="qwen-commit-") as temp_dir:
    message_path = Path(temp_dir) / "message.txt"
    message_path.write_text(message, encoding="utf-8")
    git(state.root, "commit", "--file", str(message_path))
```

Capture Git/hook output privately. Preserve hooks/signing and return short errors; do not retry. After commit, compare actual tree and parent with the snapshot, and read the actual subject. For a failed commit command inspect HEAD to distinguish unchanged, changed, and uninspectable outcomes; never falsely report that no commit exists. Bound JSON after UTF-8 encoding, shortening only displayed subject and adding `subject_truncated: true`. Handle interruptions and unexpected errors without exposing data or claiming a known commit outcome when uncertain.

- [ ] **4. Run all tests and confirm single-line output and correct Git outcomes.**
- [ ] **5. Commit these two files** with subject `feat(qwen-commit): commit verified snapshots with bounded output`.

### Task 4: Publish the skill contract and validate the installed model

**Files:** Create `skills/qwen-commit/SKILL.md`; modify `README.md`, `CLAUDE.md`, and `.claude-plugin/plugin.json`.

**Interfaces:** The host reads the skill, resolves its installed directory, and runs `python3 <skill-directory>/scripts/qwen_commit.py` from the target repository. The host uses only `status`, `hash`, `subject`, or the bounded error to respond.

- [ ] **1. Exercise the pre-skill behavior** with a scenario asking an assistant to commit staged changes via local Qwen without reading the diff. Record why ordinary commit handling would ingest the diff or reconstruct prompts. Use an inline evaluation if agent delegation would conflict with the user's token-saving preference.
- [ ] **2. Write the short skill.** Frontmatter name is `qwen-commit`; description states trigger conditions only: local Qwen/Ollama commit requests and invocation `forte:qwen-commit`. Include Python/Git/Ollama prerequisites, the resolved-path command, existing message-policy precedence, staged-only scope, one-call/no-diff/no-script-read/no-retry rules, result handling, and normal sandbox permissions. Do not imply automatic invocation by every other forte skill.
- [ ] **3. Update documentation and patch version** to `1.39.1`. Document `QWEN_COMMIT_MODEL`, English Conventional Commits, 24 KiB prompt limit, 300-second generation deadline, hook preservation, the precheck race limitation, and unknown-outcome inspection. Add this usage example:

```text
/forte:qwen-commit
```

- [ ] **4. Run one live smoke test** in a disposable repository with test identity, signing disabled only there, and a staged small code change. Invoke the actual runner with installed `qwen3.8:27b-q8_0`. Allow local network access through the host's approval mechanism. Assert one committed result, expected tree/parent, and valid message; report elapsed time and output size, not raw model output or a fabricated token-savings percentage.
- [ ] **5. Run final checks** and inspect the final diff:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/qwen-commit/tests -v
git diff --check
wc -l skills/qwen-commit/SKILL.md
python3 -m json.tool .claude-plugin/plugin.json
```

Manually review the short skill against the trigger scenario, confirm it leads directly to the runner without loading source/diffs, and confirm error paths do not invite automatic retries. No tests for static README wording.
- [ ] **6. Commit the skill, docs, and manifest** with subject `feat(qwen-commit): register token-efficient local commit skill`. Update this plan with completed checks and evidence. Finish by reporting the invocation, validation results, and any actual unresolved limitation.

## Self-review

Task 1 covers immutable staged input, initial/binary/deleted/renamed files, repository guards, and size limits. Task 2 covers the local-only generation protocol, completion/schema validation, deadline, and failure handling. Task 3 covers identity checks, normal Git hooks, output limits, shell safety, and uncertain commit outcomes. Task 4 covers the installed model, short runtime contract, documentation, and plugin release. All function names used across task boundaries are declared above.
