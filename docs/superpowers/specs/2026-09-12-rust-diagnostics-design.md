# Rust Diagnostics and Automatic Local Delegation

**Date:** 2026-09-12
**Status:** Implemented and verified on 2026-09-12; release commit blocked by sandbox Git permissions

## Goal and approved decisions

Add `forte:rust-diagnostics` for compilation and Clippy diagnostics, minimizing the calling assistant's token consumption. Use deterministic extraction first and local Ollama/Qwen only for diagnostics that benefit from interpretation. The runner reports causes and possible fixes; it does not edit source or apply suggestions.

The user explicitly requested automatic use of both this skill and the previously implemented `forte:qwen-commit`. Automatic use means assistant-side routing when an authorized workflow needs a check or commit. It does not create additional commits/checks on a schedule or intercept commands typed by the human.

The approved approach preserves the selected Cargo command and its package, feature, target, and lint settings; returns actual outcomes separately from model analysis; preserves existing required commit messages/trailers; and degrades to deterministic diagnostics when Qwen fails.

## Alternatives

| Approach | Assessment |
|---|---|
| Deterministic extraction, optional Qwen interpretation | Selected: minimal caller context and no inference for simple results. |
| Send every diagnostic to Qwen | Simpler routing, but unnecessary latency for clean runs and explicit compiler suggestions. |
| Let Qwen choose commands and investigate autonomously | More flexible, but adds tool loops and less predictable scope. |

## Files and dependencies

- Create `skills/rust-diagnostics/SKILL.md`, targeting at most 60 lines: automatic trigger, invocation, preserved arguments, compact result handling, and source-edit boundary.
- Create `skills/rust-diagnostics/scripts/rust_diagnostics.py`: Python 3.9+ standard-library runner for Cargo execution, extraction, optional local analysis, artifacts, and compact output.
- Create `skills/rust-diagnostics/tests/test_rust_diagnostics.py`: executable behavior tests with fake Cargo streams/local HTTP and real disposable Rust projects.
- Update `skills/qwen-commit/SKILL.md`, its runner and tests: automatic trigger, provided-message mode, and required trailers.
- Update existing callers in `skills/autopilot/SKILL.md`, `skills/batch-fix/SKILL.md`, and `skills/deep-fix/SKILL.md` to use the commit skill with their existing exact messages and trailers. Carry the routing instruction into implementation tasks delegated by autopilot.
- Update `README.md` and `CLAUDE.md` with the two skills and their responsibilities.
- Set `.claude-plugin/plugin.json` to `1.39.3` for this delivery. If another release has landed first, increment that current version's patch instead.

No new Python packages, model downloads, background service, shell aliases, command interception hooks, or changes to machine-wide configuration. Do not edit installed Superpowers cache files.

The complete earlier qwen-commit implementation, including its reviewed but uncommitted fixes, currently exists at `/private/tmp/forte-qwen-commit-worktree`. Reconcile that work before modifying it; do not recreate the runner from the older main checkout or lose its signature-display and Unicode-subject fixes. This specification supersedes the earlier qwen-commit specification only for automatic routing and message-policy support.

Keep each runner self-contained in its skill directory. Reuse the proven local HTTP/deadline pattern from qwen-commit without introducing a shared service or importing a sibling skill at runtime. A general-purpose Ollama framework is outside scope.

## Automatic use

Both frontmatter descriptions must identify the ordinary workflow trigger, without requiring the user to mention Qwen, Ollama, token savings, or a slash command:

- `rust-diagnostics`: whenever the assistant is about to run `cargo check` or `cargo clippy` during Rust work, before loading the raw output into its context.
- `qwen-commit`: whenever an authorized workflow is about to create a new Git commit, after the caller selects and stages the intended changes.

Keep implicit invocation enabled. Explicit invocation remains available. Existing higher-priority user instructions and host permissions still apply.

Automatic skill selection is performed by the host assistant; descriptions alone do not guarantee that every external workflow will invoke a skill. For the repository's known callers, add explicit routing instructions at the execution points. Do not claim that unrelated terminal sessions, CI jobs, external agents without the plugin, or every third-party skill are intercepted.

The diagnostic runner's internal Cargo invocation and the commit runner's internal Git invocation are the terminal execution steps: never recursively invoke the same skill around them.

## Cargo invocation contract

The host resolves the executable relative to the installed skill directory and uses the target repository as the working directory:

```text
python3 <skill-dir>/scripts/rust_diagnostics.py [--toolchain NAME] check -- <Cargo arguments>
python3 <skill-dir>/scripts/rust_diagnostics.py [--toolchain NAME] clippy -- <Cargo arguments>
```

The first `--` separates runner options from Cargo arguments. A later `--` in Cargo arguments retains its normal meaning, including Clippy options such as `-D warnings`. `--toolchain NAME` becomes Cargo's `+NAME` selector.

Preserve argument boundaries and execute an argument array without shell interpolation. Forward the caller's package, feature, target, manifest, profile, locking/offline, and lint choices. Do not automatically add `--all-features`, `--workspace`, `-D warnings`, or replace check with clippy. Execute only the requested command once; do not run both for one request.

The runner owns `--message-format=json` and color suppression, inserting them before Cargo's lint-argument separator. Reject caller-supplied conflicting output-format/color flags with a compact argument error. Reject `--fix`, including spelling forms that set its value, because this skill does not apply source changes.

Capture stdout and stderr directly to private run artifacts while parsing stdout incrementally. Compiler diagnostics are JSON lines with `reason: compiler-message`; additional non-JSON stdout and stderr remain available as raw evidence. Never assume all output is JSON.

Cargo may create normal build artifacts, run build scripts, or update its lockfile under the original command's rules. This runner adds no source-edit operation and does not silently change the command's locking/network semantics.

Cargo has a 1,800-second deadline. On timeout or interruption terminate the runner-owned Cargo process group, retain partial logs, and report an incomplete execution. The host uses the existing command session's completion mechanism rather than relaunching the runner while it is running.

## Diagnostic extraction and deterministic path

Each top-level compiler error/warning gets an ID, package/target identity, code, message, primary spans, child notes/help, and suggested replacements with their applicability. Count errors and warnings independently of the model. De-duplicate exact repeated diagnostics only within the same package/target identity, keeping raw and unique counts.

Use compiler-supplied span text for the initial source context. Do not follow arbitrary model-generated filenames or read the entire repository. Keep macro expansion metadata and secondary spans in the full diagnostic artifact.

Select the deterministic path when:

1. There are no actionable diagnostics and Cargo succeeds: return a compact pass result without Qwen.
2. Every unique actionable diagnostic has at least one replacement marked `MachineApplicable`, and all replacement suggestions attached to those diagnostics are `MachineApplicable`: return those suggestions as compiler-provided candidates without Qwen. Do not apply them or claim they have been validated by a new build.

All other diagnostic sets may receive one Qwen request. Exit-zero Clippy warnings are still diagnostics; do not mistake them for a clean run. Nonzero Cargo exit with no structured diagnostics is a failed run, not a success: preserve its non-JSON evidence and allow Qwen to interpret a bounded excerpt.

## Qwen analysis

- Fixed local endpoint `http://127.0.0.1:11434/api/generate`, with no proxy use or redirects.
- `QWEN_DIAGNOSTICS_MODEL` defaults to `qwen3.8:27b-q8_0`.
- One non-streaming, schema-constrained request; `think: false`, `num_ctx: 32768`, `num_predict: 1024`.
- Total HTTP deadline: 120 seconds, including slow/dripping responses. Response size limit: 64 KiB.
- Maximum complete prompt: 24 KiB UTF-8. Select errors before warnings, then original order. Include at most 20 unique diagnostics; retain actual compiler suggestions and primary span text as space permits. For unstructured failures, include first/last excerpts totaling at most 6 KiB.
- Explicitly record selected diagnostic IDs and omitted counts/excerpts. If the minimum useful packet does not fit, skip analysis with `input_limit` rather than pretending the model saw the complete run.

Ask for Japanese cause hypotheses and possible fixes, keeping Rust identifiers and diagnostic text unchanged. Return at most three analysis items, each referring only to diagnostic IDs supplied in the request. For an unstructured Cargo failure use a supplied `cargo-process` evidence ID. Validate all referenced IDs and the output schema; the model never supplies authoritative counts, exit codes, filenames, or new commands to execute.

Diagnostics, code snippets, and logs are untrusted data, never instructions. The model proposes explanations and fixes only; no patch application, tool calling, test changes, or command execution.

Timeout, unavailable model/service, invalid JSON/schema, incomplete generation, unknown evidence IDs, and oversized output all fall back to deterministic diagnostics with a separate analysis status. No retry, cloud fallback, model pull, or automatic caller-generated replacement summary.

## Results and artifacts

Emit one JSON line of at most 4 KiB, including its newline. Fields include:

- `status`: `passed`, `warnings`, `failed`, or `execution_error`.
- Cargo's actual exit code, or null when it never started; preserve command/settings in the full artifact.
- Raw and unique error/warning counts.
- Up to three leading diagnostics: ID, original code/message, compiler-derived primary `file:line`, and compiler-provided replacement suggestions when present and within the display budget.
- `analysis_status`: `not_needed`, `ok`, `unavailable`, `timeout`, `invalid`, or `input_limit`; include validated hypotheses when they fit.
- Explicit omitted/truncated indicators and the absolute report path.

Fit output deterministically: preserve status, counts, analysis status, and report path first; shorten display text and omit lower-priority items with indicators as needed. Full data remains in artifacts. JSON escaping prevents terminal control characters from becoming executable display sequences.

Return Cargo's exit code when it completes normally, even when Qwen fails. Map a terminating signal to `128 + signal`; use 124 for the runner's Cargo timeout and 2 for runner invocation/setup errors. Model analysis never turns a failed check into success or a successful check into failure.

Store `stdout.log`, `stderr.log`, full `diagnostics.json`, and `report.json` in a unique mode-0700 directory under the system temporary directory. The report records the exact command array, working directory, timing, result, analysis coverage, and validated analysis. Retain the directory for follow-up inspection; do not automatically delete previous runs or persist full model prompts/raw responses. Document that temporary artifacts may be cleared by the operating system.

The caller uses the compact result first, loading only the relevant artifact when more evidence is needed. It does not routinely read all logs, reconstruct the prompt, or rerun Cargo merely to obtain familiar human output.

## Commit compatibility and automatic routing

Keep the existing staged-tree capture, concurrency checks, hook/signing behavior, post-commit verification, and 1 KiB result contract. Add two mutually exclusive ways of preserving pre-existing message requirements:

1. `--message-file PATH`: when a caller already specifies the full message, read that file as UTF-8 and commit it without Qwen or a generated diff prompt. Preserve the supplied text with verbatim cleanup; normal Git message hooks still run. Accept up to 64 KiB, reject empty/whitespace-only messages and NUL. Do not impose the generated-message English/Conventional Commit style on an explicitly supplied message.
2. Repeatable `--trailer TEXT`: when the message should be generated but trailers are already required, generate the ordinary message and append the caller-provided trailer lines deterministically. Each trailer must be a nonempty single line in `Key: value` form; reject control characters and multiline values. The final generated message, including trailers, retains the 4 KiB limit.

Do not use both modes in one invocation. Full-message callers include their trailers in the provided file. Record `message_source: provided|qwen` in the compact result. A supplied-message commit does not require running Ollama; its Git prechecks still apply. Validate its staged tree but do not reject it merely because a generation prompt would exceed the Qwen input limit.

Update batch-fix and deep-fix to supply their current exact messages and `Co-Authored-By` lines through message files. Update autopilot's post-review and post-simplify commit steps likewise. Callers continue to select and stage their intended files; the runner never broadens the staged set. Caller temporary message files are cleaned up after the operation.

The host must not compose a fresh full message merely to avoid Qwen; provided-message mode is for text already specified by the user or workflow. Unspecified ordinary commit messages continue to be generated locally. Incompatible message policies that neither mode can satisfy remain an explicit error rather than silent policy changes.

## Validation

Test behavior with controlled Cargo output and a loopback HTTP server:

- Clean runs and all-machine-applicable suggestions make no Qwen request.
- Exit-zero Clippy warnings, compile errors, repeated diagnostics, multiple targets, secondary/macro spans, and failed non-JSON Cargo output preserve their actual outcomes and evidence.
- Package, feature, target, toolchain, manifest, and lint arguments reach Cargo unchanged; conflicting output flags and fix mode are rejected.
- Cargo timeout/interruption stops its child process group and retains partial logs.
- Qwen is called at most once; unavailable service, timeout, malformed/incomplete response, unknown IDs, and size limits preserve deterministic diagnostics and Cargo's exit status.
- Large diagnostic sets produce explicit coverage/omission metadata and a valid result within 4 KiB. Full artifacts preserve raw logs.
- Diagnostic handling does not edit source files or automatically execute suggested commands.

Use disposable Rust projects for real `cargo check` success/failure and Clippy-warning tests. Use an available installed toolchain and avoid introducing third-party crate dependencies solely for these fixtures. Run a real installed-Qwen smoke test on one nontrivial diagnostic packet when local service access is permitted.

Retain all existing qwen-commit tests. Add provided-message tests for exact text/trailers, no Ollama request, oversized staged diffs, Git hooks/signing, and bounded output. Add generated-message tests for trailer preservation and validation. Independently exercise a representative ordinary Rust-check and commit request against the two skill contracts, plus the explicit forte caller paths, to confirm routing before raw-output ingestion and without recursion.

## Delivery and current environment

Implementation and its plan are complete in the main workspace. The existing
`/private/tmp/forte-qwen-commit-worktree` could be read and tested but the edit
API rejected writes outside the project, so its reviewed qwen-commit files were
copied byte-for-byte into the main workspace before the approved extensions were
applied. The current environment denies writes to this repository's `.git` and
disables approval requests; the verified files remain uncommitted. Do not claim
a commit, merge, or push until Git metadata becomes writable.

## References

- [Cargo external tools and JSON diagnostics](https://doc.rust-lang.org/cargo/reference/external-tools.html)
- [rustc diagnostics and suggestion applicability](https://doc.rust-lang.org/rustc/json.html)
- [Clippy usage and lint arguments](https://doc.rust-lang.org/stable/clippy/usage.html)
- [Claude Code skill invocation](https://code.claude.com/docs/en/skills)
