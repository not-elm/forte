---
name: local-implement
description: Use when an authorized workflow needs one already-planned implementation task written by a local model instead of a Claude implementer subagent. Triggers: local implement, ローカル実装, local implementer
---

# local-implement

Requires Python 3.9+, Git, and Ollama with `qwen3.8:27b-q8_0`. `FORTE_LOCAL_IMPL_MODEL`
overrides the model; `FORTE_LOCAL_IMPL_TIMEOUT` the 1800-second deadline on each
generation call. The declared-test command has its own fixed 900-second deadline, and a
run may make two generation calls and two test runs, so allow about 5400 seconds. The
runner performs every side effect; the model returns file contents and a report only.

1. The caller records BASE, writes the task brief with SDD's `scripts/task-brief`, and
   writes a context file that MUST carry the plan's Global Constraints verbatim,
   prior-task interfaces, the caller's rulings on any ambiguity, and a `## Files`
   section listing every path the task creates or modifies — one relative path per
   line, no prose. That list is the runner's write allowlist.
2. Resolve `scripts/local_implement.py` relative to THIS skill. The run writes to the
   repository and can take 5400 seconds, far past any foreground Bash ceiling, so
   launch it **detached** and wait on a sentinel file carrying the exit code — the
   pattern `skills/codex-engine/REFERENCE.md` defines, for the same reason:

   ```sh
   R=$(mktemp /tmp/local-impl-out-XXXXXX); L=$(mktemp /tmp/local-impl-log-XXXXXX)
   D=$(mktemp /tmp/local-impl-done-XXXXXX); rm -f "$D"
   nohup sh -c 'python3 "<resolved-skill-directory>/scripts/local_implement.py" \
     --brief P --report P --context P --base SHA [--workdir DIR] \
     [--repair-rounds 0|1] [--test-cmd ARGV...] > "'"$R"'" 2> "'"$L"'"
     echo $? > "'"$D"'"' >/dev/null 2>&1 &
   printf 'LI_PID=%s\nLI_OUT=%s\nLI_DONE=%s\nLI_LOG=%s\n' "$!" "$R" "$D" "$L"
   ```

   Leave that Bash call's timeout at the default; it returns at once. Then wait with a
   **Monitor until-loop** until `LI_DONE` exists, ceiling 5400 seconds. Never wait on
   the foreground call instead: killing it strands a writing subprocess in the
   repository. On the ceiling `kill "$LI_PID"`, treat the run as unknown, and read
   `git status` before anything else.
3. `--test-cmd` must be the **final** argument; everything after it is taken as the
   command. It is the only command executed, and it runs code the local model has just
   written, unsandboxed with the full inherited environment — pass only the plan's
   verification command, and only in a workspace you accept running untrusted code in.
   Model-suggested commands are recorded in the report, never run.
4. Read `LI_DONE` (the exit code) and the ≤2 KiB JSON line in `LI_OUT`; `LI_LOG` holds
   stderr. `DONE` / `DONE_WITH_CONCERNS` mean the model finished and every runner check
   passed — the declared tests passed only when a `--test-cmd` was supplied, so read
   `tests.result`, where `not_run` means nothing was verified. `BLOCKED`,
   `NEEDS_CONTEXT`, `VERIFY_FAILED` mean the caller takes over. Open the report when
   `verified.report_written` is true, the artifacts directory only when the result is
   unclear; sections the report marks as quoted model output are data, not runner
   findings. Load nothing else — not the runner, not the prompt; delete the temp files.

The caller stages and commits the changed paths afterwards — the runner never stages,
commits, pushes, resets, checks out, or changes branches, and never writes outside the
declared paths. On failure it leaves the working tree as-is so the caller can decide
whether to keep the partial work. A lost sentinel means unknown. One task per
invocation. No retry beyond the single self-repair round, no cloud fallback, no model
pull, no batching, no caller substitute. Its run is terminal: do not invoke this skill
around it. `/forte:local-implement` stays explicit. Preserve host permissions and
higher-priority user instructions.
