# qwen-commit Skill Design

**Date:** 2026-09-12
**Status:** Approved and implemented; automatic routing/message-policy extension verified on 2026-09-12, release commit blocked by sandbox Git permissions

## Goal and approved scope

Add `forte:qwen-commit` to generate a commit message with local Ollama/Qwen and commit already-staged changes. The primary objective is minimizing the calling Claude/Codex session's token consumption. Local inference still consumes tokens and time; this design moves commit-specific work out of the calling model's context.

The user approved a short skill plus a local script that obtains the staged diff, requests a message, validates it, executes the commit, and returns only its hash and subject. Staging, change selection, splitting commits, pushing, amending, and cloud fallback are outside this skill's scope.

## Alternatives considered

| Approach | Trade-off |
|---|---|
| Caller reads the diff and delegates wording | Simple, but the caller still pays for reading the diff and constructing the request. |
| Script collects the diff and returns the generated message | Avoids diff ingestion, but leaves a separate commit step with the caller. |
| Script collects the diff, generates the message, and commits | Selected: a single invocation and a bounded result minimize caller context and coordination. |

## Components and integration

- `skills/qwen-commit/SKILL.md`: concise trigger, prerequisites, command, scope, and result/error handling. Target at most 60 lines. It must not instruct the caller to read the script, diff, recent commits, or generation prompt during normal use.
- `skills/qwen-commit/scripts/qwen_commit.py`: Python 3 standard-library runner owning Git inspection, local HTTP, prompt construction, validation, commit execution, and bounded output. No additional Python packages or agent delegation.
- `skills/qwen-commit/tests/`: isolated Git-repository tests and an Ollama stub. Tests are not loaded by the skill at runtime.
- `README.md` and `CLAUDE.md`: register the new skill and its responsibility.
- `.claude-plugin/plugin.json`: bump the patch version when implementation is completed, following repository convention. No marketplace version field is added.

Resolve the runner relative to the installed skill directory, not relative to the target repository. Execute with the target repository as the working directory. Existing commit-producing skills remain unchanged in this first version; they can explicitly invoke this skill in future integrations.

## Invocation and configuration

The normal invocation runs the Python script without arguments in the target repository. Invoking the skill authorizes committing the already-staged changes; the skill adds no per-commit confirmation checkpoint beyond the host's applicable permissions.

- Fixed endpoint: `http://127.0.0.1:11434/api/generate`. Disable proxy use and HTTP redirects so the runner sends requests directly to the local service.
- Model: `QWEN_COMMIT_MODEL`, default `qwen3.8:27b-q8_0`, matching the model found on this machine. Do not pull models automatically.
- Request deadline: 300 seconds. A timeout produces a short error with no retry.
- Generation: non-streaming JSON-schema output with `subject` and `body` string fields; request `think: false`, a 32,768-token context, and at most 512 output tokens. Verify these settings against the installed model during implementation. Unsupported settings fail explicitly rather than silently changing models or invoking cloud generation.

Use English Conventional Commit messages, consistent with this repository's recent commits. The subject is required; the body may be empty. Explicit message rules already known to the caller, such as a required trailer or different language, take precedence: incompatible requests must stop with a short explanation instead of silently violating those rules. General repository-policy discovery is the host's responsibility; this runner is not an instruction-file interpreter.

## Data flow

1. Confirm a Git worktree, a nonempty staged change, and no unresolved conflicts or merge/rebase/cherry-pick/revert operation. Support an initial commit with no existing HEAD.
2. Capture the current HEAD (or unborn state) and staged tree identity. Obtain the patch and change statistics from these captured immutable trees (use an empty base tree for an initial commit), not from a later read of the live index. Disable external diff tools, text conversion, color, and binary patch payloads. Read only staged content; unstaged content is not part of the request.
3. Build the prompt inside the runner. Include the staged patch and statistics, the required output schema, and concise message-writing rules. Diff text is untrusted data, never instructions. Binary changes are described only by Git's metadata; do not invent their internal semantics.
4. Reject a complete serialized prompt larger than 24 KiB in UTF-8. Do not silently truncate files or diffs. The caller receives `INPUT_TOO_LARGE` and can ask the user to split the staged changes. No automatic summarization or retry loop is introduced.
5. Send the request directly to Ollama. The caller sees neither the prompt nor the diff, generated thinking, raw response, or HTTP logs.
6. Validate successful completion and parse the structured response. Reject empty, malformed, truncated, or multiline-subject output. Reject control characters except line feeds within the body. Require a Conventional Commit subject of at most 100 characters and a complete message of at most 4 KiB. Treat the generated message exclusively as text, never a shell command.
7. Immediately before committing, check that HEAD and the staged tree still match the captured values and that the repository is still in an allowed state. A mismatch stops without committing or regenerating.
8. Write the message to a private temporary file and execute ordinary `git commit --file` through an argument array. Preserve normal Git hooks, signing, and identity settings. No `--no-verify`, shell interpolation, automatic staging, or configuration changes.
9. Verify the resulting commit before reporting success: it must have the captured parent (or no parent for an initial commit) and captured tree. Read the actual commit subject for the success output, accounting for message hooks.
10. Clean up temporary files on both success and failure. Do not persist prompts or model responses.

The pre-commit identity check detects changes during inference, but does not provide an atomic lock against unrelated Git processes or hooks changing state afterward. Post-commit verification detects a differing result; it never rewrites or rolls back a commit. This limitation must remain explicit in implementation documentation.

## Output and failure behavior

Success: one JSON line containing `status: "committed"`, the commit hash, and the actual subject, with exit code zero. The caller relays a short success statement without reviewing or regenerating the message. If a message hook produces a subject too long for the output budget, shorten only its display and include `subject_truncated: true`; do not modify the committed message.

Failure: one JSON line containing `status: "error"`, a stable error code, a short explanation, and whether a commit is known to have been created, with nonzero exit status. Bound the complete output to 1 KiB. Suppress raw Git/hook/HTTP output; report a concise category instead. Never include a raw diff, model response, or traceback in normal output.

Error categories cover an invalid repository, empty index, unsupported repository state, input too large, unavailable Ollama/model, generation timeout/failure, invalid response, changed index/HEAD, Git failure, and unexpected post-commit state. Where commit outcome is uncertain, report it as unknown and instruct the caller to inspect Git state before any retry.

No automatic retry, cloud fallback, model installation, hook bypass, or message rewriting by the caller. These would add cost or alter the requested workflow. Host approval prompts remain effective; this skill does not bypass sandbox permissions.

## Validation and acceptance criteria

Use meaningful integration tests with temporary repositories and a local HTTP stub:

- A valid generated message creates exactly one commit containing the staged tree; unstaged edits remain outside the commit.
- Initial commits, file deletion/renaming, and binary changes work within the input limit.
- Empty index, unresolved/in-progress operations, oversized prompts, unavailable service, timeouts, and malformed/truncated output create no commit.
- Changing HEAD or the staged tree during inference prevents the commit.
- Shell-looking generated text is treated as message data, never executed.
- A failing Git hook is honored; a hook that changes committed content yields an unexpected-state error rather than false success. No automatic second commit is attempted.
- Success and error output stay bounded and do not expose the patch, full prompt, thinking, or raw logs.

Run one real smoke test against the installed Qwen model in a disposable repository, confirming JSON output, generation settings, and the resulting commit. Do not use the user's existing staged work as test data.

Token savings are demonstrated structurally: normal skill execution requires a short skill, one runner invocation, and at most 1 KiB of tool output. The caller does not ingest a diff or build a generation prompt. Do not claim a measured percentage reduction without a comparable baseline.

## Next step

After the user reviews this written specification, use `superpowers:writing-plans` to produce the implementation plan. No runner or skill implementation is included in this design step.
