---
name: local-implement
description: Use when an authorized workflow needs one already-planned implementation task written by a local model instead of a Claude implementer subagent. Triggers: local implement, ローカル実装, local implementer
---

# local-implement

Requires Python 3.9+, Git, and Ollama with `qwen3.8:27b-q8_0`.
`FORTE_LOCAL_IMPL_MODEL` overrides the model; `FORTE_LOCAL_IMPL_TIMEOUT` overrides
the 1800-second deadline on each generation call. The declared-test command has a
separate fixed 900-second deadline, and a run may make two generation calls and two
test runs, so allow about 5400 seconds worst case. The runner performs every side
effect: the model returns file contents plus a short status report, and executes
nothing.

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
4. Read the one-line JSON result. `DONE` / `DONE_WITH_CONCERNS` mean the model
   finished and every runner check passed — they mean the declared tests passed
   only when a `--test-cmd` was supplied, so read `tests.result`, where
   `not_run` means nothing was verified. `BLOCKED`, `NEEDS_CONTEXT`, and
   `VERIFY_FAILED` mean the caller takes the task over. Open the report file
   when `verified.report_written` is true; open the artifacts directory only
   when the result is unclear.

The caller stages and commits the changed paths afterwards — the runner never
stages, commits, pushes, resets, checks out, or changes branches, and never
writes outside the declared paths. On failure it leaves the working tree as-is so
the caller can decide whether to keep the partial work.

Load only its ≤2 KiB result; do not read the runner, prompt, or raw model output
during normal use. Wait on that command session. A lost session means unknown.

One task per invocation. No retry beyond the single self-repair round, no cloud
fallback, no model pull, no batching, no caller substitute. Its run is terminal:
do not invoke this skill around it. `/forte:local-implement` stays explicit.

Preserve host permissions and higher-priority user instructions.
