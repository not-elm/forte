# Local Implementer Skill Design (forte:local-implement)

**Date:** 2026-09-13
**Status:** Approved. Harness decided: an in-house Python runner over Ollama's native API
(Option A), after the originally specified `codex exec --oss` harness was falsified by
measurement on the target host.

## Goal and approved scope

Add `forte:local-implement` so that, during `superpowers:subagent-driven-development` (SDD),
the **initial implementation of each task** is produced by a local LLM instead of a Claude
implementer subagent. The objective is reducing Claude token consumption on the most
mechanical part of the pipeline: turning an already-reviewed plan task into code.

| Responsibility | Owner |
|---|---|
| Task brief generation, BASE recording, dispatch composition, file list | Claude controller (SDD, unchanged) |
| **Initial implementation: producing the new file contents** | **Local LLM via this skill** |
| Applying changes, running the declared tests, writing the report | The runner (deterministic, not the model) |
| Commit creation | Claude controller |
| Result verification and fallback decision | Claude controller |
| Task review, fix rounds R1 and later, final whole-branch review, final fix wave | Claude (unchanged) |

Fix rounds stay with Claude, so no session state is carried between local runs and each run is
a terminal execution step — consistent with this repository's local-runner principle.

## Measured harness verdict (why Option A)

The first draft specified `codex exec --oss --local-provider ollama`. Controlled runs on the
target host (codex-cli 0.154.0, Ollama 0.34.0, `qwen3.8:27b-q8_0`, 48 GB Mac16,8) falsified it.
Each run used the production flag set in a throwaway Git repository with the trivial task
"create hello.txt, stage it, commit it".

| `shell_type` in the model catalog | exit | wall clock | commits | file created | failure |
|---|---|---|---|---|---|
| `default` | 1 | 185s | none | no | `codex_core::tools::router: error=unsupported call: shell` |
| `shell_command` | 1 | 129s | none | no | no shell tool registered at all; the model stated it could not create local files and called the user's MCP GitHub plugin instead |
| `unified_exec` | 1 | 18s | none | no | `unsupported call: local_shell` |
| `local` | 1 | 26s | none | no | `unsupported call: shell` |

Every failure also collapsed the stream (`Reconnecting… 1/5 … 5/5`, then
`stream disconnected before completion`).

- **`--output-schema` breaks the run on this provider.** A/B on an identical tool-free prompt:
  with the flag, exit 1 and the `-o` file was never written; without it, exit 0 and the file
  was correct. The mechanism the first draft relied on for a bounded typed result destroys the
  output it was meant to bound.
- **A model catalog entry is necessary but not sufficient.** `-c model_catalog_json=<file>`
  with a minimal entry removed the `Model metadata for qwen3.8:27b-q8_0 not found` warning, so
  the mechanism works, but every tool-routing failure above persisted. The
  `model_catalog_json` hypothesis is tested and rejected as a fix. For the record, a valid
  minimal entry requires: `slug`, `display_name`, `apply_patch_tool_type`, `shell_type`,
  `context_window`, `max_context_window`, `supported_reasoning_levels`, `visibility`
  (`list|hide|none`), `supported_in_api`, `priority`, `support_verbosity`, `truncation_policy`
  (`{mode, limit}`), `experimental_supported_tools`, and one of `base_instructions` or
  `model_messages.instructions_template`.

**Conclusion:** the blocker is Codex's tool layer, not the model's competence. Codex registers
its shell and patch tools as OpenAI Responses API special/custom types, which Ollama's
OpenAI-compatible endpoint cannot represent, so the model's calls arrive unroutable. This
matches upstream openai/codex#2064 and ollama/ollama#16209.

**Option A therefore removes the tool-calling layer entirely.** The model is asked for file
contents as data; the runner performs every side effect. Two alternatives were considered and
rejected: Aider with a text-diff edit format (sidesteps the same layer, but adds a host
dependency with no forte precedent, loses the OS sandbox, and its repo map consumes context),
and parking the feature (zero risk, zero savings).

### Corrections to the first draft's research basis

- **"Ollama's default context window is 4096 tokens" is false on this host.** With no
  `OLLAMA_CONTEXT_LENGTH` set, a warm-up produced `ollama ps` → `CONTEXT 32768` on Ollama
  0.34.0. Under Option A this matters less, because the runner sets `num_ctx` per request the
  way `qwen_commit.py` already does — no host-level mutation and no `SETUP.md` required.
- **32768 would have been a knife-edge threshold** (exactly the observed default) and is in any
  case not a meaningful gate: Codex's base prompt plus tool and skill descriptions consumed
  **16,456 tokens** before any task content. Option A's prompt is built by the runner, so this
  overhead disappears.
- **The claimed `~/.codex/ollama-launch-models.json` oversized-window bug was not reproduced**;
  no such file exists on this host after repeated `--oss` runs, and the observed symptom is the
  inverse (metadata missing). The issue number cited in the first draft did not match; the
  warning corresponds to ollama/ollama#14752.
- **`skills/board-engine/SETUP.md` is not a host-setup precedent** — it is a whiteboard file
  model reference. This repository has no host-setup document, and Option A needs none.
- **The user's `~/.codex` configuration leaked into every Codex run**: shortened-skill warnings,
  and one run calling `codex_apps/github.search_installed_repositories_streaming` instead of
  touching local files. Option A never loads that configuration.
- **Reasoning effort was inherited from user config** (`medium` observed) on a model that
  advertises `thinking`. Option A pins generation parameters explicitly, including `think:
  false`.

## Interface

```
/forte:local-implement --brief <path> --report <path> --context <path> --base <sha> \
                       [--test-cmd <argv…>] [--workdir <dir>] [--repair-rounds 0|1]
```

| Argument | Meaning |
|---|---|
| `--brief` | The SDD task brief from `scripts/task-brief PLAN_FILE N` (default `<repo-root>/.superpowers/sdd/<plan-basename>/task-<N>-brief.md`). Required. Single source of requirements; passed verbatim, never paraphrased. |
| `--report` | The report file to produce, named by SDD convention (`task-<N>-report.md` beside the brief). Required. Written by the runner, not by the model, so it always exists and always contains real test evidence. |
| `--context` | **Required.** Written by the controller. MUST contain the plan's Global Constraints verbatim, where the task fits, interfaces and decisions from earlier tasks, the controller's resolution of any ambiguity in the brief, pointers to parked findings in the area, and a required `## Files` section. `task-brief` extracts only the task's own section, so plan-level constraints reach the implementer through this file or not at all. |
| `--base` | The BASE commit the controller recorded before dispatch, passed in rather than re-derived so controller and runner cannot disagree about the range. |
| `--test-cmd` | Optional. The command to verify the task, as an argv list taken from the plan. The runner executes only this. Model-proposed commands are recorded as suggestions and never executed. |
| `--workdir` | Repository root or worktree. Defaults to the current working directory. |
| `--repair-rounds` | 0 or 1, default 1. See *Self-repair*. |

### The `## Files` contract

The context file's `## Files` section lists, one relative path per line, every file the task
creates or modifies. It is the runner's write allowlist: a returned path that is not on the
list is refused. This replaces codebase exploration, which the model cannot do under Option A,
with an explicit controller-authored declaration — deterministic, reviewable, and path-safe.

A task whose brief does not permit such a list is not a fit for the local implementer: the
runner returns `NEEDS_CONTEXT` and the controller dispatches Claude.

### Returned result

SDD's report contract (at most 15 lines) plus a verification line:

```
Status: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT | VERIFY_FAILED
Changed: <file list, or none>
Tests: <command and pass/fail summary, or "not run (no --test-cmd)">
Concerns: <one line each, or none>
Report: <report file path>
Verified: base=<sha> paths-allowed=<yes|no> untouched-dirty=<yes|no> report-written=<yes|no>
```

`DONE`, `DONE_WITH_CONCERNS`, `BLOCKED` and `NEEDS_CONTEXT` keep their SDD meanings so the
controller's existing handling applies. `VERIFY_FAILED` is the single addition: the run claimed
success but the repository state or the model's output contradicts it.

Who emits which status: the **model** may return only `DONE`, `DONE_WITH_CONCERNS` or
`BLOCKED`. The **runner** passes those through when verification agrees, and otherwise
substitutes its own — `NEEDS_CONTEXT` when the dispatch itself was insufficient (no `## Files`
list, a task that cannot declare one), or `VERIFY_FAILED` when the model's output or the
resulting repository state failed a check. A status the runner did not verify is never
forwarded.

## Runner design

`skills/local-implement/scripts/local_implement.py`, Python 3 standard library only, resolved
relative to the installed skill directory and executed with the target repository as the
working directory — the same shape as `qwen_commit.py` and `rust_diagnostics.py`.

### Preflight

Each failure returns a distinct code and does **not** contact the model:

1. `--workdir` is a Git worktree; `--base` resolves in it.
2. `--brief` and `--context` exist and are non-empty; `## Files` is present and non-empty.
3. Every declared path is relative, contains no `..`, resolves inside `--workdir`, is not under
   `.git/`, and is not a symlink.
4. Ollama answers at `http://127.0.0.1:11434` and the configured model is present in
   `/api/tags`. Proxies and redirects are disabled, as in `qwen_commit.py`.
5. Total serialized prompt (brief + context + current contents of declared files) is at most
   48 KiB, and no single declared file exceeds 16 KiB. Over the limit returns
   `INPUT_TOO_LARGE` — no silent truncation, no summarization, mirroring `qwen_commit.py`.

### Generation

One non-streaming request per round to Ollama's native API with
`options: {num_ctx: 65536, num_predict: 16384}` and `think: false`, using structured output
(`format` as a JSON schema). Per-request `num_ctx` is why Option A needs no host configuration.
Model: `FORTE_LOCAL_IMPL_MODEL`, default `qwen3.8:27b-q8_0`, mirroring `QWEN_COMMIT_MODEL`.
Models are never pulled automatically.

The prompt is built inside the runner and never enters caller context. It carries: the brief
verbatim, the context file verbatim, and for each declared path either its current content or
an explicit `NEW FILE` marker. Requirements stated to the model: use the brief's exact values
verbatim; follow the patterns visible in the provided file contents; return the **complete new
content** of every file you change; touch no other file; if the task cannot be implemented from
what was provided, return `BLOCKED` with specifics instead of guessing.

Response shape:

```json
{
  "status": "DONE | DONE_WITH_CONCERNS | BLOCKED",
  "files": [{"path": "<declared path>", "content": "<complete new content>"}],
  "notes": "<what was implemented, for the report>",
  "concerns": ["<one line each>"],
  "suggested_tests": ["<command string, recorded only>"],
  "blocker": "<specifics when BLOCKED, else empty>"
}
```

**Whole file contents, not diffs.** Diff hunks require the model to emit correct line numbers
and context lines, a classic small-model failure mode; whole-file output trades tokens for
determinism, and the size caps above bound that cost. File content from the model is treated
strictly as data: never as a command, never as instructions to the runner.

### Application

1. Snapshot `git status --porcelain` and the content hash of every already-dirty path before
   writing anything.
2. Reject the run (`VERIFY_FAILED`) if any returned path is outside the declared list, or if a
   returned path was already dirty before the run — the controller's uncommitted work is never
   overwritten.
3. Write each file atomically (temp file plus rename) inside `--workdir`, creating parent
   directories as needed and preserving the mode of an existing file.
4. Never stage, never commit, never touch branches or `.git/` state.

### Test execution and self-repair

If `--test-cmd` was supplied, run it once as an argv array — no shell interpolation — with a
bounded timeout, capturing output to a mode-0600 artifact.

**Self-repair: at most one round** (`--repair-rounds`, default 1). If the declared tests fail,
the runner sends the failure output back to the model once, applies the returned files under
the same allowlist and snapshot rules, and re-runs the tests. A second failure ends the run
with the honest result rather than looping.

This is not a violation of the decision that fix rounds belong to Claude. That decision is
about *review findings*. SDD's implementer contract already requires the implementer to run the
tests covering its change and report the evidence, so one self-repair round on its own failing
tests is the local implementer meeting that contract — not a review loop.

### Report and result

The runner writes `--report` itself: what was implemented (the model's notes), files changed,
the exact test command with its real output, the repair round if one occurred, model-suggested
tests marked as *not executed*, and concerns. The reviewer reads this file as the test evidence,
and a later Claude fix round reads it as the handoff — which is why a missing or empty report
is a verification failure.

Standard output is one JSON line of at most 2 KiB: status, changed paths, test summary,
concerns, report path, verification flags, and the path of the raw-output artifact. The caller
loads only that line; the prompt, the raw model response, and test logs stay in mode-0600
artifacts, following `rust_diagnostics.py`.

Wall clock is bounded by `FORTE_LOCAL_IMPL_TIMEOUT`, default 1800 seconds, as a hard expiry a
slow byte stream cannot extend (the `qwen_commit.py` precedent). On timeout the runner
terminates its whole process group and confirms termination before returning, so no writer
survives into the Claude fallback.

No retry beyond the single repair round, no cloud fallback, no model pull, no staging, no
commit, no push.

## Verification and fallback

The model's self-report is never authoritative. The controller accepts a run only when:

- every changed path was on the declared list,
- no already-dirty path was modified (byte-for-byte against the snapshot),
- the report file exists and is non-empty,
- the declared test command, if any, actually ran with its output in the report.

**A clean working tree is not required.** Autopilot creates and revises the spec and plan in
Stages 1–4 without committing them, so requiring a clean tree would fail correct local runs
purely because of pipeline artifacts, and would risk sweeping unrelated user changes into the
commit.

Fallback triggers: non-zero exit, timeout, unparsable or schema-violating output, `BLOCKED` /
`NEEDS_CONTEXT`, or any failed verification check.

Fallback performs **no destructive operation** — no reset, checkout, stash, or branch change.
The skill reports the failure reason with `git status --porcelain` and `git diff --stat`, and
the Claude implementer that takes over decides whether to build on the partial work or replace
it. Discarding a user-visible working tree without a human decision is what autopilot's stop
conditions reserve for the human.

## Commit ownership

**The local model does not commit, and neither does the runner.** After verification the Claude
controller stages only the paths the run changed and commits through `forte:qwen-commit`.
Rationale: Codex's `workspace-write` has documented `.git` metadata failures
(openai/codex#19315, #5034); a model-authored commit can sweep in pre-existing uncommitted
work; and this repository already centralises authorized commit creation. SDD's review package
is unaffected, since it is built from `BASE..HEAD` once the controller's commit exists.

## `codex-engine` relationship

Option A does not run `codex exec`, so `skills/codex-engine/REFERENCE.md` and its read-only
invariant are untouched and the contract conflict the first draft would have created does not
arise. No change to that reference or to `CLAUDE.md`'s description of it is needed.

## autopilot integration

A new flag, **`--local-impl`**, opts the pipeline in. Default off until the end-to-end
measurement in *Validation* exists.

Stage 5 standing answers when `--local-impl` is set:

- The initial implementation dispatch for each task goes to `forte:local-implement` with the
  brief, report, context, base and (when the plan states one) test-command arguments, instead
  of an Agent-tool implementer dispatch. The controller writes the context file, including the
  `## Files` list, from the plan.
- **Fix round R1 and later use a fresh Claude implementer.** SDD normally resumes the original
  implementer for rounds 1–3 because its context is intact. A local run leaves no resumable
  Claude agent, so the pipeline takes SDD's own documented fallback for harnesses that cannot
  resume a live session: a fresh implementer with the brief path, the same report file path,
  and the findings.
- The controller creates each task's commit after verification.
- **Batching is disabled.** SDD may combine several small same-shape tasks into one dispatch;
  this skill takes exactly one brief, so each task gets its own local run.
- Task review, the final whole-branch review and the final fix wave are unchanged, including
  their model selection.
- Ledger line per task: `LOCAL-IMPL: task <N> → <ok|fallback> (<reason>)`.
- Stage 8 report gains: `ローカル実装: N件成功 / M件フォールバック`.

Without `--local-impl`, autopilot behaves exactly as today and this skill is never invoked.

## Validation

1. **Capability test in `tests/`**: in a throwaway Git repository, a stubbed Ollama response
   drives the runner end to end and must produce the declared file, run the declared test
   command, and write the report. Under Option A there is no tool-calling layer to smoke-test at
   runtime, so this lives in the test suite rather than as a per-session gate.
2. Preflight distinguishes: non-Git workdir, unresolvable base, missing or empty brief or
   context, missing `## Files`, an illegal declared path, Ollama unreachable, model absent, and
   `INPUT_TOO_LARGE`.
3. Path containment: a response naming an undeclared path, an absolute path, a `..` path, a
   symlink, or anything under `.git/` is refused with nothing written.
4. Dirty-path protection: a response touching a path that was already dirty is refused, and the
   pre-existing content is unchanged afterwards.
5. Malformed model output (invalid JSON, missing field, wrong type) is refused rather than
   leniently parsed.
6. Self-repair: a first-round test failure triggers exactly one repair round; a second failure
   reports honestly and does not loop.
7. Non-destructiveness: after every failure path, HEAD and the working tree are exactly as the
   run left them and no Git state-changing command was issued.
8. Timeout terminates the process group, with termination confirmed before returning.
9. Output budget: the stdout JSON line stays within 2 KiB, and no prompt, raw model response,
   or test log appears in it.
10. End-to-end: one real plan task through `autopilot --local-impl`, measuring wall clock per
    task and confirming the brief-to-report handoff, the controller commit, the review package
    from BASE, and a fix round dispatched to a fresh Claude implementer.

Wall-clock expectations come from measurement, not assumption: on this host a single model turn
was observed at roughly 200 seconds. The default ceiling is revisited after item 10.

## Deliverables

1. `skills/local-implement/SKILL.md` — trigger, invocation, argument contract, result and error
   handling, scope limits. At most 60 lines, and it must not instruct the caller to read the
   runner, the prompt, or the raw model output during normal use.
2. `skills/local-implement/scripts/local_implement.py` — preflight, prompt construction,
   generation, application, test execution, one repair round, report writing, bounded result.
   Standard library only.
3. `skills/local-implement/tests/test_local_implement.py` — isolated Git repositories and an
   Ollama stub, matching `skills/qwen-commit/tests/` and `skills/rust-diagnostics/tests/`.
4. `skills/autopilot/SKILL.md` revision: `--local-impl`, Stage 5 standing answers, Stage 8 line.
5. `CLAUDE.md` and `README.md` registration; `.claude-plugin/plugin.json` bump to 1.41.0
   (`marketplace.json` has no version field).

No `SETUP.md` and no `schema/result.schema.json`: Option A needs no host configuration, and
`--output-schema` is neither used nor usable here.

## Out of scope

- Delegating fix rounds, task review, the final review, or the final fix wave to a local model
- Codebase exploration by the local model; the `## Files` declaration replaces it
- Diff- or patch-format output from the model
- Executing model-proposed commands
- Session continuation or state carried between local runs
- Task-level routing that decides which tasks are "mechanical enough"; every task with a
  declarable file list goes local first, and failures fall back
- Multiple local models, model selection heuristics, LM Studio / MLX providers
- Any change to `codex-engine`'s read-only invariant
- Automatic model pulling, implementer network access, cloud fallback, staging, or committing
- A Responses-API shim between Codex and Ollama, and any revisit of the Codex `--oss` harness

## References

- `skills/autopilot/SKILL.md` — Stage 5 standing answers, stop conditions, ledger format
- `skills/qwen-commit/` — `QWEN_COMMIT_MODEL`, per-request `num_ctx`, hard wall-clock expiry, Git snapshot guard, `INPUT_TOO_LARGE`, bounded output
- `skills/rust-diagnostics/` — bounded result plus mode-0600 artifact-on-demand pattern
- `skills/codex-engine/REFERENCE.md` — untouched by Option A; its read-only contract still governs Codex-based skills
- `superpowers/skills/subagent-driven-development/` — `SKILL.md`, `implementer-prompt.md`, `scripts/task-brief`, `scripts/review-package`: the dispatch, report, batching and review-package contracts
- openai/codex#2064, ollama/ollama#16209 — local-provider tool-call failures matching the measured verdict
- openai/codex#19315, #5034 — `workspace-write` `.git` metadata failures behind *Commit ownership*
- ollama/ollama#14752 — the `Model metadata … not found` warning
