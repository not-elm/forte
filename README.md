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

The context file's `## Files` section is the write allowlist — one relative path
per line, no prose. The runner refuses any other path, refuses a path that already
had uncommitted changes, verifies that no already-dirty path changed during the
run, and never stages, commits, or changes Git state; the caller commits after
verifying. Model-suggested commands are recorded in the report and never executed.
`--test-cmd` must be the last argument (everything after it is the command) and is
optional: without it nothing is verified and the result reports `tests.result` as
`not_run`. When it is supplied it runs code the local model just wrote, unsandboxed
with the inherited environment, so pass only the plan's verification command and
only in a workspace you accept running untrusted code in. Each generation call has
a 1,800-second deadline and the declared test command a separate fixed 900-second
one, so a run with a repair round can take about 5,400 seconds. The prompt limit is
48 KiB, the per-file limit 16 KiB, and there is no retry or cloud fallback beyond
the single self-repair round.

Because a run can outlast any foreground call, the skill launches the runner
detached and waits on a sentinel file carrying its exit code.

Requires Python 3.9+, Git, and a running Ollama service with `qwen3.8:27b-q8_0`.
`FORTE_LOCAL_IMPL_MODEL` selects another installed model and
`FORTE_LOCAL_IMPL_TIMEOUT` changes the per-generation deadline. The full test log
and a one-line-per-round proposal summary stay in owner-only files inside the
mode-0700 temporary directory named by the result; the prompt and the model's file
contents are not kept.

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
```

## License

MIT
