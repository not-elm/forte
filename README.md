# forte

notelm's personal collection of Claude Code skills, packaged as a plugin.

## Installation

```sh
claude plugin marketplace add https://github.com/not-elm/forte.git
claude plugin install forte
```

## Skills

### forte:rust-diagnostics

Automatically use this skill before the assistant runs `cargo check` or
`cargo clippy`. A local Python runner executes the requested Cargo command once,
keeps complete output in temporary artifacts, and returns at most 4 KiB of JSON.
It uses compiler-provided suggestions directly when all are
`MachineApplicable`; other failures or warnings may receive one local Qwen
analysis with Japanese causes and possible fixes.

```text
/forte:rust-diagnostics check -- -p my-crate --all-targets
/forte:rust-diagnostics clippy -- --workspace -- -D warnings
```

The runner preserves the caller's package, feature, target, manifest, profile,
locking/offline, toolchain, and lint arguments. It owns Cargo's JSON/color flags
and rejects `--fix`. It does not edit source or apply suggestions. Cargo has an
1,800-second deadline; local analysis has a 120-second deadline, 24 KiB prompt
limit, and no retry or cloud fallback.

Requires Python 3.9+, Rust/Cargo, and optionally a running Ollama service with
`qwen3.8:27b-q8_0`. `QWEN_DIAGNOSTICS_MODEL` selects another installed model.
Full `stdout.log`, `stderr.log`, `diagnostics.json`, and `report.json` remain in
the mode-0700 temporary directory named by the compact result. The operating
system may eventually clear these temporary artifacts.

### forte:qwen-commit

Automatically use this skill when an authorized workflow is ready to create a
new commit after selecting and staging its files. With no supplied subject, the
runner creates an English Conventional Commit through local Qwen. Existing full
messages use `--message-file`; required trailers on a generated message use
repeatable `--trailer`. The calling assistant receives at most 1 KiB of JSON,
while staged diff and prompt data stay inside the runner.

```text
/forte:qwen-commit
```

Requires Python 3.9+ and Git; generated mode also needs a running Ollama service
with `qwen3.8:27b-q8_0`. `QWEN_COMMIT_MODEL` selects another installed compatible
model. The endpoint is fixed to `127.0.0.1:11434`; there is no proxy, retry,
remote fallback, or automatic model pull. Generation has a 24 KiB prompt limit
and 300-second deadline. Provided messages accept up to 64 KiB without loading
the diff or contacting Ollama.

The runner commits only already-staged changes. It preserves identity, signing,
and hooks, rechecks HEAD/index before committing, and verifies the resulting
tree and parent. It never stages, amends, pushes, bypasses a hook, or rolls back
an unexpected result.

Automatic selection applies to assistants that load this plugin. It does not
intercept commands typed directly in a terminal, CI, or unrelated agents.

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

### forte:codex-investigate

Run Codex CLI in read-only mode to investigate a bug's root cause from its symptoms. Describe the bug and Codex searches the codebase, identifies root causes with file paths and line numbers, assesses impact scope, and suggests fix approaches.

Arguments: free-form symptom description, plus optional additional context (OS, repro steps, error logs, file paths).

```
codex investigate the login page crashes after entering credentials on Safari
codex debug users report 500 errors on /api/orders since yesterday's deploy
```

### forte:discussion-board

Structured team debate with iterative synthesis using 4–10 role-based agents (scaled to topic complexity). Explores open-ended questions through rounds of hypothesize, critique, audit (via Codex), synthesize, and ratify phases. Produces a design doc when concluded.

Arguments: free-form proposition or question to explore.

```
discuss how should we handle rate limiting across our microservices
explore question what caching strategy best fits our read-heavy workload
```

## Prerequisites

[Codex CLI](https://github.com/openai/codex) is required for **codex-investigate**:

```
npm i -g @openai/codex
```

Local-runner development tests:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/local-implement/tests -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/rust-diagnostics/tests -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/qwen-commit/tests -v
```

## License

MIT
