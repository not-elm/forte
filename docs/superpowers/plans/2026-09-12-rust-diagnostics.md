# Rust Diagnostics and Automatic Local Delegation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a compact Rust `cargo check`/Clippy diagnostic runner that delegates only ambiguous diagnosis to local Qwen, and make both that runner and the existing local-Qwen commit runner the automatic routes for the repository's supported workflows.

**Architecture:** A self-contained Python runner executes exactly one requested Cargo command, streams complete evidence into private temporary artifacts, normalizes compiler diagnostics, and invokes local Ollama once only when deterministic compiler suggestions are insufficient. The existing qwen-commit runner gains explicit-message and trailer inputs without weakening its staged-tree checks; short skill contracts and known forte callers route ordinary checks and authorized commits through these runners.

**Tech Stack:** Python 3.9 standard library, `unittest`, Cargo/rustc JSON diagnostics, Git CLI, Ollama HTTP API, Claude Code skill Markdown.

**Spec:** `docs/superpowers/specs/2026-09-12-rust-diagnostics-design.md` (approved by the user on 2026-09-12).

## Global Constraints

- Preserve all reviewed qwen-commit work in `/private/tmp/forte-qwen-commit-worktree`, including the `--no-show-signature` verification fix and Unicode line-separator rejection. Use that worktree as the implementation base.
- Python 3.9+ standard library only. Do not add packages, shared runner services, sibling-skill runtime imports, model downloads, background processes, shell aliases, command interception hooks, or machine-wide configuration.
- Use fixed local Ollama endpoint `http://127.0.0.1:11434/api/generate`; no proxies, redirects, retry, cloud fallback, or automatic model pull.
- Diagnostic model is `QWEN_DIAGNOSTICS_MODEL`, default `qwen3.8:27b-q8_0`; request settings are `stream: false`, `think: false`, `num_ctx: 32768`, and `num_predict: 1024`.
- Diagnostic prompt limit is 24 KiB UTF-8, response limit is 64 KiB, total Ollama deadline is 120 seconds, and compact output limit is 4 KiB including its newline.
- Execute only the caller-selected `cargo check` or `cargo clippy` once, preserving package, feature, target, manifest, profile, locking/offline, toolchain, and lint arguments. Do not add workspace/features/lint policy or apply fixes.
- Cargo execution deadline is 1,800 seconds. On timeout or interruption, stop the runner-owned process group and retain partial artifacts.
- Diagnostics and logs are untrusted input. Qwen may return Japanese cause hypotheses and fix suggestions only; it cannot change authoritative status/count/path data, edit files, call tools, or propose commands for automatic execution.
- Keep both `SKILL.md` files at most 60 lines. Normal callers consume only compact JSON and load artifacts selectively.
- qwen-commit retains immutable staged-tree checks, hooks, signing, identity, outcome verification, 4 KiB generated-message limit, and 1 KiB compact-output limit.
- Version target is `1.39.2` from the pending `1.39.1` worktree. If the worktree version has advanced, increase its current patch component instead.
- The environment may deny `.git` writes. Complete and verify file changes even if a task's commit step fails; record the exact Git error and never claim an uncreated commit.

## File map

| File | Responsibility |
|---|---|
| `skills/rust-diagnostics/scripts/rust_diagnostics.py` | Cargo argument validation, process supervision, JSON extraction, deterministic routing, Ollama analysis, artifacts, and compact result. |
| `skills/rust-diagnostics/tests/test_rust_diagnostics.py` | Fake-Cargo, loopback-Ollama, process-tree, output-bound, and disposable real-Rust behavior tests. |
| `skills/rust-diagnostics/SKILL.md` | Automatic Rust check/Clippy trigger and compact caller contract. |
| `skills/qwen-commit/scripts/qwen_commit.py` | Existing commit runner plus supplied-message and generated-trailer modes. |
| `skills/qwen-commit/tests/test_qwen_commit.py` | Regression coverage for both message modes and all existing commit guarantees. |
| `skills/qwen-commit/SKILL.md` | Automatic authorized-commit trigger and message-policy routing. |
| `skills/autopilot/SKILL.md` | Carry Rust diagnostic routing into implementers and use provided messages for its two fixed commit steps. |
| `skills/batch-fix/SKILL.md` | Preserve its exact fixed message and Claude co-author trailer through a message file. |
| `skills/deep-fix/SKILL.md` | Preserve both conditional fixed messages and Claude co-author trailer through a message file. |
| `README.md` | Installation, automatic behavior, commands, limits, artifacts, and development validation. |
| `CLAUDE.md` | Repository structure and local-runner architecture entries. |
| `.claude-plugin/plugin.json` | Patch release metadata. |

Keep each runner cohesive in one script and each test suite in one companion module. The two runners may use equivalent private helper patterns, but neither imports the other at runtime.

---

### Task 1: Execute one Cargo command and retain complete private evidence

**Files:**
- Create: `skills/rust-diagnostics/scripts/rust_diagnostics.py`
- Create: `skills/rust-diagnostics/tests/test_rust_diagnostics.py`

**Interfaces:**
- Produces `DiagnosticError(code: str, message: str, exit_code: int = 2)` for bounded setup/argument failures.
- Produces frozen `Invocation(tool: str, toolchain: Optional[str], cargo_args: Tuple[str, ...])`.
- Produces `RunArtifacts(root: Path, stdout_path: Path, stderr_path: Path, diagnostics_path: Path, report_path: Path)`.
- Produces `CargoRun(command: Tuple[str, ...], cwd: Path, exit_code: Optional[int], timed_out: bool, interrupted_signal: Optional[int], started_at: float, ended_at: float, stdout_non_json: Tuple[str, ...], raw_messages: Tuple[dict, ...], artifacts: RunArtifacts)`.
- Produces `parse_argv(argv: Sequence[str]) -> Invocation`, `build_cargo_command(invocation: Invocation) -> Tuple[str, ...]`, `create_artifacts() -> RunArtifacts`, and `run_cargo(invocation: Invocation, cwd: Path) -> CargoRun`.

- [ ] **Step 1: Write failing command-contract tests.** Build a fake `cargo` executable in a temporary `bin` directory that writes its argument vector to a JSON file and emits configurable stdout/stderr. Patch `PATH`, `CARGO_CAPTURE_PATH`, and the module deadline inside each test. Include these exact assertions:

```python
invocation = rd.parse_argv([
    "--toolchain", "stable", "clippy", "--",
    "-p", "core", "--features", "serde", "--manifest-path", "app/Cargo.toml",
    "--locked", "--", "-D", "warnings",
])
self.assertEqual(invocation.tool, "clippy")
self.assertEqual(invocation.toolchain, "stable")
self.assertEqual(invocation.cargo_args[-3:], ("--", "-D", "warnings"))
self.assertEqual(
    rd.build_cargo_command(invocation),
    ("cargo", "+stable", "clippy", "-p", "core", "--features", "serde",
     "--manifest-path", "app/Cargo.toml", "--locked",
     "--message-format=json", "--color=never", "--", "-D", "warnings"),
)
```

Test `check` and `clippy`; empty/missing `--`; unknown tools; missing toolchain values; `--message-format`, `--message-format=...`, `--color`, `--color=...`; and all Cargo/Clippy fix spellings (`--fix`, `--fix=true`, `--fix false`) as code `INVALID_ARGUMENTS`. Assert arguments containing spaces and shell metacharacters remain single literal array entries.

- [ ] **Step 2: Run the command tests and verify they fail because the module does not exist.**

```sh
PYTHONDONTWRITEBYTECODE=1 python3 \
  skills/rust-diagnostics/tests/test_rust_diagnostics.py ArgumentTests -v
```

Expected: import/module failure before any fake Cargo process starts.

- [ ] **Step 3: Implement strict parsing and argument insertion.** Use a small manual parser so the first wrapper delimiter and any later Cargo delimiter are distinguishable. Insert owned flags immediately before the first delimiter within `cargo_args`:

```python
def build_cargo_command(invocation: Invocation) -> Tuple[str, ...]:
    args = list(invocation.cargo_args)
    lint_at = args.index("--") if "--" in args else len(args)
    owned = ["--message-format=json", "--color=never"]
    selector = ["+" + invocation.toolchain] if invocation.toolchain else []
    return tuple(["cargo", *selector, invocation.tool, *args[:lint_at],
                  *owned, *args[lint_at:]])
```

Reject owned-output flags and any `--fix` value form before launching Cargo. Never pass a command string or `shell=True`.

- [ ] **Step 4: Write failing streaming/artifact tests.** The fake Cargo process must emit one JSON line in two writes, a non-JSON stdout line, stderr text, and then exit with a configured code. Assert the runner returns the real exit code, parses the split JSON line, and creates a unique absolute mode-0700 directory with byte-for-byte `stdout.log` and `stderr.log`. Add a fake Cargo mode that spawns a child, writes both PIDs, emits partial logs, and waits; set `CARGO_TIMEOUT` to `0.2` and assert exit 124, both processes stop, and partial logs remain.

```python
run = rd.run_cargo(rd.parse_argv(["check", "--", "-p", "demo"]), project)
self.assertEqual(run.exit_code, 101)
self.assertEqual(len(run.raw_messages), 1)
self.assertEqual(run.stdout_non_json, ("build-script marker",))
self.assertEqual(run.artifacts.root.stat().st_mode & 0o777, 0o700)
self.assertEqual(run.artifacts.stderr_path.read_text(), "linker detail\n")
```

- [ ] **Step 5: Run the new process tests and verify missing `run_cargo` behavior fails.**

```sh
PYTHONDONTWRITEBYTECODE=1 python3 \
  skills/rust-diagnostics/tests/test_rust_diagnostics.py CargoProcessTests -v
```

Expected: failures identify absent streaming, artifact, and timeout behavior.

- [ ] **Step 6: Implement streaming supervision and private artifacts.** Create the directory with `tempfile.mkdtemp(prefix="forte-rust-diagnostics-")`, immediately `chmod(0o700)`, open log files in binary mode, and launch `subprocess.Popen(command, cwd=str(cwd), stdout=PIPE, stderr=stderr_file, start_new_session=True)`. Use `selectors.DefaultSelector` plus `time.monotonic()` to copy stdout chunks to disk and assemble newline-delimited JSON incrementally. On timeout or `KeyboardInterrupt`, send `SIGTERM` to the process group, wait a bounded grace period, then `SIGKILL`; drain available pipe data and preserve artifacts. Decode non-JSON display evidence with UTF-8 replacement while retaining original log bytes.

- [ ] **Step 7: Run Task 1 tests, then commit the executable and tests.**

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s skills/rust-diagnostics/tests -v
git add skills/rust-diagnostics/scripts/rust_diagnostics.py \
  skills/rust-diagnostics/tests/test_rust_diagnostics.py
git commit -m "feat(rust-diagnostics): capture cargo diagnostics"
```

Expected: command/process tests pass; the commit succeeds when `.git` is writable, otherwise record the denial and continue without changing the index by another mechanism.

### Task 2: Normalize diagnostics and choose the deterministic path

**Files:**
- Modify: `skills/rust-diagnostics/scripts/rust_diagnostics.py`
- Modify: `skills/rust-diagnostics/tests/test_rust_diagnostics.py`

**Interfaces:**
- Consumes `CargoRun.raw_messages` and its artifact paths from Task 1.
- Produces frozen `Replacement(file_name: str, byte_start: int, byte_end: int, replacement: str, applicability: str)`.
- Produces `NormalizedDiagnostic(id: str, level: str, package_id: str, target: str, code: Optional[str], message: str, primary_spans: Tuple[dict, ...], secondary_spans: Tuple[dict, ...], children: Tuple[dict, ...], replacements: Tuple[Replacement, ...], full_message: dict, occurrences: int)`.
- Produces `DiagnosticSet(raw_error_count: int, raw_warning_count: int, unique_error_count: int, unique_warning_count: int, diagnostics: Tuple[NormalizedDiagnostic, ...])`.
- Produces `normalize_diagnostics(run: CargoRun) -> DiagnosticSet`, `all_machine_applicable(items: DiagnosticSet) -> bool`, `execution_status(run: CargoRun, items: DiagnosticSet) -> str`, and `write_diagnostics_artifact(run: CargoRun, items: DiagnosticSet) -> None`.

- [ ] **Step 1: Add failing normalization fixtures.** Emit `compiler-message` objects for two packages with identical messages, an exact repeat within one package/target, one error with primary/secondary macro spans, child `note`/`help`, and suggestions of each rustc applicability. Assert only the same package/target duplicate collapses, occurrence counts remain visible, raw/unique levels are counted separately, and full macro/secondary data appears in `diagnostics.json`.

```python
items = rd.normalize_diagnostics(run)
self.assertEqual((items.raw_error_count, items.unique_error_count), (3, 2))
self.assertEqual(items.diagnostics[0].id, "D001")
self.assertEqual(items.diagnostics[0].occurrences, 2)
self.assertEqual(items.diagnostics[0].replacements[0].applicability,
                 "MachineApplicable")
```

Use exact canonical deduplication input `(package_id, target identity, level, code, message, spans, children)`; do not merge diagnostics merely because their display text matches.

- [ ] **Step 2: Add failing deterministic-routing tests.** Assert a successful run with no error/warning diagnostics selects `passed`; exit-zero Clippy warnings select `warnings`; normal nonzero Cargo selects `failed`; setup failure selects `execution_error`. Assert `all_machine_applicable` is true only when every actionable unique diagnostic has at least one replacement and every attached replacement is `MachineApplicable`.

```python
self.assertTrue(rd.all_machine_applicable(machine_only_set))
self.assertFalse(rd.all_machine_applicable(mixed_applicability_set))
self.assertEqual(rd.execution_status(clippy_warning_run, warning_set), "warnings")
self.assertEqual(rd.execution_status(non_json_failure_run, empty_set), "failed")
```

- [ ] **Step 3: Run normalization tests and observe the new interface failures.**

```sh
PYTHONDONTWRITEBYTECODE=1 python3 \
  skills/rust-diagnostics/tests/test_rust_diagnostics.py \
  NormalizationTests RoutingTests -v
```

- [ ] **Step 4: Implement lossless normalization and deterministic classification.** Read only Cargo-provided JSON already captured from stdout. Build source context from `span["text"]`; never open compiler paths. Collect suggestions from spans with non-null `suggested_replacement`, preserve applicability, and retain the original message object in `full_message`. Assign IDs after stable first-seen deduplication, errors before warnings only during later model selection, not during normalization.

```python
def all_machine_applicable(items: DiagnosticSet) -> bool:
    actionable = [d for d in items.diagnostics if d.level in ("error", "warning")]
    return bool(actionable) and all(
        d.replacements and all(r.applicability == "MachineApplicable"
                               for r in d.replacements)
        for d in actionable
    )
```

Write `diagnostics.json` atomically within the private artifact directory with raw/unique counts, normalized fields, occurrence counts, full spans/children/macro expansions, and no model content.

- [ ] **Step 5: Run all diagnostic tests, then commit normalization.**

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s skills/rust-diagnostics/tests -v
git add skills/rust-diagnostics/scripts/rust_diagnostics.py \
  skills/rust-diagnostics/tests/test_rust_diagnostics.py
git commit -m "feat(rust-diagnostics): normalize compiler evidence"
```

### Task 3: Analyze only ambiguous evidence with local Qwen

**Files:**
- Modify: `skills/rust-diagnostics/scripts/rust_diagnostics.py`
- Modify: `skills/rust-diagnostics/tests/test_rust_diagnostics.py`

**Interfaces:**
- Consumes `CargoRun`, `DiagnosticSet`, normalized diagnostic IDs, and non-JSON evidence.
- Produces `AnalysisPacket(prompt: str, evidence_ids: Tuple[str, ...], selected_ids: Tuple[str, ...], omitted_diagnostics: int, stdout_excerpt_omitted: bool, stderr_excerpt_omitted: bool)`.
- Produces `AnalysisResult(status: str, items: Tuple[dict, ...], coverage: dict)` where status is `not_needed`, `ok`, `unavailable`, `timeout`, `invalid`, or `input_limit`.
- Produces `build_analysis_packet(run: CargoRun, items: DiagnosticSet) -> Optional[AnalysisPacket]`, `request_analysis(packet: AnalysisPacket) -> object`, `validate_analysis(response: object, packet: AnalysisPacket) -> AnalysisResult`, and `analyze(run: CargoRun, items: DiagnosticSet) -> AnalysisResult`.

- [ ] **Step 1: Add failing packet-selection tests.** Generate 25 diagnostics in mixed order and assert the packet includes no more than 20, prioritizes errors before warnings while preserving relative order within each level, includes selected IDs and omitted counts, and stays at or below 24 KiB encoded. Assert primary compiler span text and replacements survive before optional children are shortened. For a nonzero run with no compiler messages, assert `cargo-process` is the only evidence ID and first/last stdout/stderr excerpts total no more than 6 KiB.

```python
packet = rd.build_analysis_packet(run, items)
self.assertLessEqual(len(packet.prompt.encode("utf-8")), 24 * 1024)
self.assertEqual(packet.selected_ids[:2], ("D002", "D004"))
self.assertEqual(packet.evidence_ids, packet.selected_ids)
self.assertEqual(packet.omitted_diagnostics, 5)
```

Add a single diagnostic whose minimum ID/code/message/primary location packet exceeds 24 KiB and assert `analyze` returns `input_limit` without opening HTTP.

- [ ] **Step 2: Add failing loopback HTTP/schema tests.** Reuse the qwen-commit test-server pattern within this test module, bound to an ephemeral loopback port. Assert exactly one request with the configured model, schema, non-streaming/no-thinking settings, 32,768 context and 1,024 prediction limit. Accept at most three items shaped as `{"evidence_ids": ["D001"], "cause": "…", "fix": "…"}`. Reject unknown IDs, empty evidence arrays, non-string cause/fix, extra fields, more than three items, incomplete `done`, length completion, invalid JSON, HTTP errors, redirects, and bodies over 64 KiB.

```python
analysis = rd.validate_analysis({
    "done": True,
    "done_reason": "stop",
    "response": json.dumps({"items": [{
        "evidence_ids": ["D001"],
        "cause": "借用が同時に保持されています。",
        "fix": "可変借用のスコープを短くします。",
    }]}, ensure_ascii=False),
}, packet)
self.assertEqual(analysis.status, "ok")
self.assertEqual(analysis.items[0]["evidence_ids"], ["D001"])
```

- [ ] **Step 3: Run Qwen tests and confirm packet/transport functions are missing.**

```sh
PYTHONDONTWRITEBYTECODE=1 python3 \
  skills/rust-diagnostics/tests/test_rust_diagnostics.py \
  PacketTests AnalysisTests -v
```

- [ ] **Step 4: Implement bounded packet construction.** Serialize diagnostics as untrusted evidence inside a rules-first JSON prompt. Build each candidate packet completely and measure UTF-8 bytes before accepting it. Drop optional child/span text before excluding a diagnostic; never cut JSON bytes. If the minimum packet cannot fit, return `input_limit`. Record selected IDs, diagnostic omission counts, and excerpt omission flags independently of model output.

- [ ] **Step 5: Implement direct local HTTP and strict response validation.** Use `http.client.HTTPConnection("127.0.0.1", OLLAMA_PORT)` and a monotonic 120-second deadline that closes/shuts down the socket from a timer so delayed headers and dripping bodies cannot exceed the total. Read at most 64 KiB plus one byte, require HTTP 200, strict UTF-8/JSON, `done is True`, and `done_reason == "stop"`. Validate every evidence ID against `packet.evidence_ids`; keep authoritative coverage from the packet.

```python
payload = {
    "model": os.environ.get("QWEN_DIAGNOSTICS_MODEL", "qwen3.8:27b-q8_0"),
    "prompt": packet.prompt,
    "stream": False,
    "think": False,
    "format": ANALYSIS_SCHEMA,
    "options": {"num_ctx": 32768, "num_predict": 1024},
}
```

Map service/connect/read failures to `unavailable`, deadline expiry to `timeout`, and envelope/schema/ID failures to `invalid`. Call Qwen zero times for clean success and all-machine-applicable sets, once for other diagnostic sets and unstructured Cargo failures, and never more than once.

- [ ] **Step 6: Run all diagnostic tests, then commit analysis support.**

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s skills/rust-diagnostics/tests -v
git add skills/rust-diagnostics/scripts/rust_diagnostics.py \
  skills/rust-diagnostics/tests/test_rust_diagnostics.py
git commit -m "feat(rust-diagnostics): explain ambiguous failures locally"
```

### Task 4: Emit bounded results and verify real Rust behavior

**Files:**
- Modify: `skills/rust-diagnostics/scripts/rust_diagnostics.py`
- Modify: `skills/rust-diagnostics/tests/test_rust_diagnostics.py`

**Interfaces:**
- Consumes all Task 1–3 data.
- Produces `build_report(run: CargoRun, items: DiagnosticSet, analysis: AnalysisResult) -> dict` with exact command array, cwd, timing, authoritative outcome/counts, analysis coverage, validated analysis, and artifact paths.
- Produces `compact_result(report: dict) -> dict`, `emit_result(result: dict) -> None`, `run(root: Path, argv: Sequence[str]) -> dict`, and `main(argv: Optional[Sequence[str]] = None) -> int`.
- Compact results always retain `status`, `cargo_exit_code`, four raw/unique counts, `analysis_status`, `report_path`, and explicit omission/truncation indicators.

- [ ] **Step 1: Add failing end-to-end output tests.** Capture `main([...])` stdout and assert exactly one JSON line no larger than 4,096 bytes. Include control characters and 20 KiB messages in fake diagnostics; assert terminal output remains valid escaped JSON and full messages remain in artifacts. Verify up to three displayed diagnostics retain ID, compiler code/message, primary `file:line`, and compiler replacement when it fits.

```python
code, result, raw = self.main_output(["check", "--", "-p", "demo"])
self.assertLessEqual(len(raw.encode("utf-8")), 4096)
self.assertEqual(len(raw.splitlines()), 1)
self.assertEqual(result["status"], "failed")
self.assertEqual(result["cargo_exit_code"], 101)
self.assertTrue(Path(result["report_path"]).is_absolute())
self.assertIn("diagnostics_omitted", result)
```

Assert normal Cargo completion returns its actual code even when analysis is unavailable/invalid/timed out; signal termination returns `128 + signal`; Cargo timeout returns 124; argument/setup errors return 2. Verify Qwen cannot alter status, exit code, counts, paths, commands, or suggested replacements.

- [ ] **Step 2: Run end-to-end tests and observe missing report/CLI failures.**

```sh
PYTHONDONTWRITEBYTECODE=1 python3 \
  skills/rust-diagnostics/tests/test_rust_diagnostics.py OutputTests -v
```

- [ ] **Step 3: Implement report persistence and deterministic compaction.** Write `report.json` atomically after diagnostics and analysis are complete. Build the compact object from authoritative fields, then fit it by shortening diagnostic/analysis display strings on Unicode boundaries, dropping lower-priority analysis items, and dropping lower-priority diagnostics. Measure the final serialized line after `ensure_ascii=False`; never trim the report path or status/count fields. Mark every shortened/dropped category explicitly.

```python
encoded = (json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
if len(encoded.encode("utf-8")) > RESULT_LIMIT:
    raise DiagnosticError("RESULT_TOO_LARGE",
                          "Required result fields exceed the output limit.")
sys.stdout.write(encoded)
```

`run` creates artifacts before Cargo launch, writes a final report even for timeout/setup errors when possible, and never persists the complete model prompt or raw response. `main` catches expected errors and interruptions without a traceback or raw-log leakage.

- [ ] **Step 4: Add disposable real-Rust tests.** Detect the already installed toolchain with `rustc --version` and `cargo clippy --version`; skip with a precise reason if unavailable, without invoking rustup or the network. Create dependency-free temporary crates for: clean `cargo check`; compile failure from `let value: u32 = "bad";`; and Clippy warning from `let _ = 1 == 1;` with a lint explicitly enabled in source. Assert actual exit/status/count behavior and confirm source bytes are unchanged before/after each run.

- [ ] **Step 5: Run fake and real tests, inspect artifacts, then commit the complete runner.**

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s skills/rust-diagnostics/tests -v
python3 -m py_compile skills/rust-diagnostics/scripts/rust_diagnostics.py
git diff --check -- skills/rust-diagnostics
git add skills/rust-diagnostics/scripts/rust_diagnostics.py \
  skills/rust-diagnostics/tests/test_rust_diagnostics.py
git commit -m "feat(rust-diagnostics): report bounded rust results"
```

Expected: fake and available real-Rust tests pass, sources stay unchanged, every reported artifact path exists, and compact output remains within 4 KiB.

### Task 5: Preserve fixed commit messages and generated trailers

**Files:**
- Modify: `skills/qwen-commit/scripts/qwen_commit.py`
- Modify: `skills/qwen-commit/tests/test_qwen_commit.py`

**Interfaces:**
- Preserve all existing public calls by default: `build_prompt(state)`, `generate_message(prompt)`, `commit_snapshot(state, message)`, and `run(root)` remain valid.
- Add `parse_cli(argv: Sequence[str]) -> Tuple[Optional[Path], Tuple[str, ...]]`.
- Add `read_provided_message(path: Path) -> str`, `validate_trailer(text: str) -> str`, and `append_trailers(message: str, trailers: Sequence[str]) -> str`.
- Extend `commit_snapshot(state: Snapshot, message: str, cleanup: str = "strip") -> dict`.
- Extend `run(root: Path, message_file: Optional[Path] = None, trailers: Sequence[str] = ()) -> dict` and return `message_source: provided|qwen`.
- Change CLI entry to `main(argv: Optional[Sequence[str]] = None) -> int`; tests call `main([])` so unittest arguments never leak into parsing.

- [ ] **Step 1: Add failing provided-message tests without changing the 25 existing assertions.** Stage a diff larger than the generation prompt limit, pass a UTF-8 message file, and assert no HTTP request, one commit, exact multiline message bytes under `git cat-file commit`, and `message_source == "provided"`. Cover 64 KiB acceptance, greater-than-64 KiB rejection, empty/whitespace/NUL rejection, missing/unreadable/non-UTF-8 files, mutual exclusion with trailers, literal shell strings, failing hooks, commit-msg rewrites, signing, repository races, and bounded 1 KiB output.

```python
message_path.write_text(
    "fix: batch-fix 2 findings from api-review.md\n\n"
    "Co-Authored-By: Claude <noreply@anthropic.com>\n",
    encoding="utf-8",
)
with ollama_stub(self.qc) as requests:
    result = self.qc.run(self.root, message_file=message_path)
self.assertEqual(requests, [])
self.assertEqual(result["message_source"], "provided")
self.assertIn(b"Co-Authored-By: Claude <noreply@anthropic.com>",
              self.git("cat-file", "commit", "HEAD"))
```

- [ ] **Step 2: Add failing generated-trailer tests.** Validate repeatable `Key: value` trailers and reject empty, missing-colon, empty-key/value, multiline, NUL/control-character, and over-limit combinations. Assert the generated body receives one blank separator and trailers in caller order, with the combined message still capped at 4 KiB.

```python
message = self.qc.append_trailers(
    "fix: repair parser\n",
    ["Co-Authored-By: Claude <noreply@anthropic.com>", "Issue: R-RD-001"],
)
self.assertEqual(
    message,
    "fix: repair parser\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n"
    "Issue: R-RD-001\n",
)
```

- [ ] **Step 3: Run qwen-commit tests and confirm only new mode tests fail.**

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s skills/qwen-commit/tests -v
```

Expected: the original 25 tests stay green or fail only where their `main()` helper must pass `[]`; new parsing/message-policy tests fail before implementation.

- [ ] **Step 4: Implement validation before prompt construction.** Parse only `--message-file PATH` and repeatable `--trailer TEXT`. Reject their combination. In provided mode, read at most 64 KiB plus one byte as strict UTF-8, reject NUL/blank content, call `snapshot`, skip `build_prompt` and Ollama entirely, and commit with `cleanup="verbatim"`. Preserve supplied line endings/content as Git permits while allowing normal message hooks.

```python
if message_file is not None:
    message = read_provided_message(message_file)
    state = snapshot(root)
    result = commit_snapshot(state, message, cleanup="verbatim")
    return {**result, "message_source": "provided"}
state = snapshot(root)
message = append_trailers(generate_message(build_prompt(state)), trailers)
result = commit_snapshot(state, message)
return {**result, "message_source": "qwen"}
```

Pass `--cleanup=<mode>` to `git commit` through the existing argument array. Keep generated behavior at Git's current cleanup mode, and preserve the existing `--no-show-signature` machine-readable verification.

- [ ] **Step 5: Implement trailer validation and CLI output.** Require a printable, nonempty single line matching a nonempty key and value around the first colon; reject Unicode control/format characters. Append trailers deterministically after trimming only generated-message terminal newlines. Validate the final generated message against 4 KiB and existing content controls without reclassifying provided messages as Conventional Commits.

- [ ] **Step 6: Run the enlarged suite and commit compatibility support.**

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s skills/qwen-commit/tests -v
git diff --check -- skills/qwen-commit
git add skills/qwen-commit/scripts/qwen_commit.py \
  skills/qwen-commit/tests/test_qwen_commit.py
git commit -m "feat(qwen-commit): preserve caller message policies"
```

Expected: all original and new tests pass, including SSH signing, hooks, race checks, Unicode line separators, supplied large-diff messages, and generated trailers.

### Task 6: Register automatic routes, update known callers, and validate the release

**Files:**
- Create: `skills/rust-diagnostics/SKILL.md`
- Modify: `skills/qwen-commit/SKILL.md`
- Modify: `skills/autopilot/SKILL.md`
- Modify: `skills/batch-fix/SKILL.md`
- Modify: `skills/deep-fix/SKILL.md`
- Modify: `README.md`
- Modify: `CLAUDE.md`
- Modify: `.claude-plugin/plugin.json`
- Modify: `docs/superpowers/specs/2026-09-12-rust-diagnostics-design.md`
- Modify: `docs/superpowers/plans/2026-09-12-rust-diagnostics.md`

**Interfaces:**
- `forte:rust-diagnostics` directs any assistant about to run `cargo check` or `cargo clippy` to one resolved-path runner invocation before raw output enters model context.
- `forte:qwen-commit` directs any authorized new commit through the resolved runner after the caller has selected/staged changes; it selects `--message-file` only for already-specified full messages and `--trailer` only for required trailers on otherwise generated messages.
- Known callers create private temporary message files, invoke qwen-commit once, remove only their own file afterward, and preserve their existing staging scope and exact messages.

- [ ] **Step 1: Write the Rust skill contract at 60 lines or fewer.** Use frontmatter that names the ordinary automatic trigger, not only explicit Qwen wording:

```yaml
---
name: rust-diagnostics
description: Use whenever the assistant is about to run cargo check or cargo clippy in a Rust project, so compilation and Clippy evidence is reduced locally before entering caller context.
---
```

The body must tell the host to resolve the installed script, run exactly one of the two documented array-safe commands from the target repository, forward the user's existing Cargo/toolchain/lint arguments after `--`, wait on the same command session, read the one-line result first, and open only a relevant artifact when necessary. State that the runner does not edit source/apply suggestions, does not recursively invoke itself, and gets no automatic retry or cloud summary fallback.

- [ ] **Step 2: Rewrite qwen-commit's trigger and message-policy branch.** Its description must cover every authorized workflow about to create a new Git commit after staging. The body distinguishes: already-specified full text → private `--message-file`; unspecified subject → Qwen; unspecified subject plus required trailers → repeatable `--trailer`. Keep one runner call, no caller diff/script read, no caller-written substitute message, no recursive invocation, and unknown-outcome Git inspection.

- [ ] **Step 3: Replace the four known direct commit instructions.** In autopilot Stage 5, add a standing instruction that Rust implementers route any `cargo check`/`cargo clippy` call through `forte:rust-diagnostics` and consume compact output before artifacts. In autopilot Stages 6 and 7, retain the current `git add -A`, then write the exact existing subject to a mode-0600 temporary file, invoke `forte:qwen-commit --message-file`, and delete that file in cleanup. In batch-fix and both deep-fix branches, retain specific-path staging and use their exact subject plus:

```text
Co-Authored-By: Claude <noreply@anthropic.com>
```

inside the private message file. Do not replace fixed subjects with generated ones and do not broaden staging.

- [ ] **Step 4: Re-run the pre-skill routing scenarios against the completed contracts.** Use two fixed scenarios: “run `cargo clippy -p core -- -D warnings` and diagnose it” and “commit these already-staged changes” with no message. Inspect the selected execution contract and confirm the first routes through `forte:rust-diagnostics` with the original arguments, while the second routes through `forte:qwen-commit` without reading the diff. Exercise batch-fix, both deep-fix branches, and autopilot's two fixed-message steps by tracing their documented command sequence: each must stage the same files as before, invoke qwen-commit with `--message-file`, and clean up only its own temporary file. Record observed failures and tighten only the instruction that allowed them; do not add source-text assertions to `unittest`.

- [ ] **Step 5: Update user and maintainer documentation.** Add `forte:rust-diagnostics` before qwen-commit in README with automatic/explicit behavior, command examples, `QWEN_DIAGNOSTICS_MODEL`, 1,800/120-second deadlines, 24 KiB prompt, 4 KiB output, artifact contents/lifetime, deterministic no-Qwen paths, and no source edits. Update qwen-commit docs for automatic routing, supplied messages, trailers, and the continued 1 KiB result. Add the new directory and automatic local-runner pattern to CLAUDE.md. Set plugin version to `1.39.3` unless the current worktree version is newer, in which case increment that patch once.

- [ ] **Step 6: Validate skill structure and all automated behavior.** Use the repository's available skill validator from the installed skill-creator tooling, then run both suites and static checks:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s skills/rust-diagnostics/tests -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s skills/qwen-commit/tests -v
python3 -m json.tool .claude-plugin/plugin.json
wc -l skills/rust-diagnostics/SKILL.md skills/qwen-commit/SKILL.md
git diff --check
```

Expected: all tests pass, both skills are at most 60 lines, manifest JSON is valid, and whitespace validation is clean.

- [ ] **Step 7: Run two disposable end-to-end routing exercises.** For Rust, request an ordinary check on a disposable failing crate and confirm the skill invokes its runner once, returns compact JSON before any artifact is opened, and does not edit source. For Git, stage a small disposable change with no supplied message and confirm qwen-commit invokes installed Qwen once; then stage another change under a fixed-message caller contract and confirm provided mode makes no Qwen request. Use the installed model only when local service access is permitted; retain deterministic/test-server evidence otherwise and label the skipped live model check accurately.

- [ ] **Step 8: Run independent whole-change review and apply only in-scope correctness fixes.** Review the final diff against the approved spec, with special attention to process-group termination, byte limits, untrusted diagnostic boundaries, model-ID validation, Git supplied-message exactness, hook/signing preservation, and automatic-trigger wording. Re-run the affected suite after every correction.

- [ ] **Step 9: Mark the spec implemented, record evidence in this plan, and create the release commit.** Add an execution-evidence section containing test totals, real Cargo/Qwen smoke outcomes, skill line counts, manifest version, review findings/fixes, and any `.git` write limitation. Then stage only the files in this plan and run:

```sh
git add .claude-plugin/plugin.json CLAUDE.md README.md \
  skills/rust-diagnostics skills/qwen-commit \
  skills/autopilot/SKILL.md skills/batch-fix/SKILL.md skills/deep-fix/SKILL.md
git add -f \
  docs/superpowers/specs/2026-09-12-rust-diagnostics-design.md \
  docs/superpowers/plans/2026-09-12-rust-diagnostics.md
git commit -m "feat: delegate rust diagnostics and commits locally"
```

Expected: commit succeeds only if `.git` is writable. If denied, leave verified working-tree files intact and report their exact location, status, branch HEAD, and the denied operation; do not attempt reset, alternate Git metadata, merge, or push.

## Execution evidence (2026-09-12)

- The existing linked worktree at `/private/tmp/forte-qwen-commit-worktree` was
  verified on `feat/qwen-commit` with its 25-test baseline. Both the project
  edit API and its command-line `apply_patch` rejected writes there, so the
  reviewed runner/test/skill were copied into the main workspace with matching
  SHA-1 values before extension. The earlier signature-display and Unicode
  subject fixes were preserved.
- TDD progression: Cargo argument/process behavior failed with the runner
  absent, then 6 tests passed; normalization/routing interfaces failed absent,
  then 10 total passed; packet/analysis interfaces failed absent, then 18 total
  passed; output interfaces failed absent, then 23 total passed; qwen-commit's
  original 25 tests stayed green while 10 new message-policy tests failed absent,
  then the enlarged suite passed.
- Final Rust diagnostics suite: 28 tests passed. It includes fake Cargo streams,
  exact argument arrays, process-group and closed-stdout deadlines, structured
  counts/deduplication, malformed spans, MachineApplicable routing, 24 KiB/20-ID
  coverage, non-UTF-8 excerpts, HTTP fallback/schema/deadline behavior, 4 KiB
  output, real `cargo check` success/failure, and real exit-zero Clippy warnings.
- Final qwen-commit suite: 35 tests passed. It retains staged-tree, hook,
  signing, race, bounded-output, deadline, signature-display, and Unicode
  regression coverage and adds exact supplied messages, large-diff/no-Ollama,
  non-Conventional UTF-8, SSH signing, generated trailers, and CLI validation.
  Its HTTP boundary now uses an in-memory `HTTPConnection` fake because this
  sandbox rejects test-server loopback binds; request payload, status, body,
  disconnect, and total-deadline behavior remain covered without a socket.
- Review fixes added regression tests for Cargo closing stdout before exit,
  malformed span numbers, encoded excerpt budgets, optional-context compaction,
  unexpected CLI failures, and U+2028/U+2029 trailer separators.
- Both skill frontmatters passed `quick_validate.py`; rust-diagnostics is 33
  lines/197 words and qwen-commit is 31 lines/200 words. Plugin version is
  `1.39.3`; all runners and tests compile with Python 3.9 using a writable
  bytecode cache. Manifest parsing, `git diff --check`, trailing whitespace,
  and conflict-marker checks also passed.
- Real diagnostic smoke: disposable borrow-check failure, Cargo exit 101,
  `failed`, one unique error, 495-byte compact result, report retained, source
  unchanged. New loopback access was denied by the sandbox, so analysis fell
  back accurately as `unavailable`.
- Real installed-model commit smoke through the previously approved runner:
  `qwen3.8:27b-q8_0`, 21.42 seconds, 133-byte result, one verified commit with
  expected parent/tree. The current runner's generation transport is unchanged;
  its new message modes are covered with real disposable Git repositories.
- `git add` remains blocked by
  `fatal: Unable to create '/Users/taiga/workspace/forte/.git/index.lock':
  Operation not permitted`. No commit, merge, push, reset, or alternate Git
  metadata was attempted.

## Self-review

- Spec coverage: Tasks 1 and 4 cover exact Cargo forwarding, owned output flags, streaming, timeouts/signals, artifacts, actual exit semantics, compact output, and disposable Rust checks. Task 2 covers Cargo JSON extraction, package/target-scoped deduplication, spans/children/replacements, counts, and deterministic no-Qwen decisions. Task 3 covers bounded evidence selection, unstructured failure excerpts, one local Qwen call, strict schema/ID validation, total deadline, and every fallback status. Task 5 covers mutually exclusive supplied-message/trailer modes while preserving every qwen-commit guarantee. Task 6 covers automatic descriptions, known caller routes, documentation, release metadata, behavior exercises, review, and environment limitations.
- Scope: The diagnostic runner and commit extension remain in one plan because the approved deliverable is automatic local delegation and the same caller/release changes bind both contracts. Each runner remains independently testable.
- Placeholder scan: The plan contains no deferred implementation markers or unnamed error-handling steps. Every task supplies exact files, interfaces, failing behavior, implementation rules, commands, expected outcomes, and a commit boundary.
- Type consistency: `Invocation` flows into `build_cargo_command`/`run_cargo`; `CargoRun` flows through normalization, packet construction, report building, and CLI output; `DiagnosticSet` and `AnalysisResult` retain the same names and roles across Tasks 2–4. qwen-commit keeps backward-compatible default signatures while exposing explicit CLI/message helpers only in Task 5.

## Execution choice

Use one of the required implementation workflows from the header. Subagent-driven development gives a fresh implementation/review context per task. Inline execution keeps the complete design and the pending qwen-commit work in one session, which minimizes orchestration overhead and is the preferred choice for this token-saving project unless the user requests task delegation.
