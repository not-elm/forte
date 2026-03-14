---
name: deep-fix
description: >-
  Deep-fix complex code review findings that require design planning.
  Use for findings without a clear Solution that need discussion before implementation.
  Triggers: /deep-fix, deep fix, 個別修正
---

# deep-fix — Deep Fix Complex Review Findings

Address code-review-board findings that lack a `> Solution:` line and require design discussion or planning before implementation. Parses the review Markdown, validates findings against current code, ranks candidates by dependency analysis, and delegates to brainstorming or Plan mode for design and implementation.

## When to Use

- The user wants to fix a complex finding from a code review report: `/deep-fix`, "deep fix", "個別修正"
- The finding lacks a `> Solution:` line and requires design discussion or planning
- The fix needs design discussion or planning before implementation

## When NOT to Use

- Findings have a `> Solution:` line — use `/batch-fix` instead
- The user wants to batch-fix multiple findings at once — use `/batch-fix` instead

## Arguments

- `target` (optional): Path to a review Markdown file. If omitted, lists `*-review.md` files in `docs/reviews/` for user selection.

**Examples:**
```
/deep-fix
/deep-fix docs/reviews/2026-03-13-api-review.md
```

---

## Architecture Note

deep-fix is a **lightweight orchestrator skill**. It handles review file parsing, stale-finding validation, dependency-aware candidate ranking, and post-fix review file updates. The actual design and implementation work is fully delegated to either the brainstorming skill or Plan mode. deep-fix does not contain implementation logic.

---

## Flow

```
1. LOCATE   — Identify review file (argument or user selection)
2. EXTRACT  — Parse unchecked [multi-site] / [cross-module] findings
3. VALIDATE — Verify Evidence snippets still match current code
4. RANK     — LLM analyzes dependencies, selects up to 4 candidates
5. SELECT   — User picks one finding (or browses all)
6. APPROACH — User chooses brainstorming, Plan mode, or discussion-board
7. EXECUTE  — Delegate to chosen approach, collect fix summary
8. VERIFY   — Check if source files were modified (HEAD or working tree)
9. UPDATE   — Mark finding as [x], insert fixed comment
10. COMMIT  — Commit review update (and source files if uncommitted)
11. REPORT  — Display summary with remaining count
```

---

## Workflow

```
 1. LOCATE       → a. If target argument provided, use that path.
                    b. Otherwise, glob `docs/reviews/*-review.md` and list
                       matches sorted by modification time (newest first).
                    c. If no review file found, display error and exit:
                       "No review file found. Run /code-review first or specify a path."
                    d. If multiple files found, display numbered list and ask
                       user to select by number.

 2. EXTRACT      → a. Read the review Markdown.
                    b. Extract findings matching ALL of:
                       - Line starts with `- [ ]` (unchecked only — skip `- [x]`)
                       - Has `> Impact:` line starting with `[multi-site]` or `[cross-module]`
                       - Does NOT have a `> Solution:` line (findings with Solution belong to batch-fix)
                    c. Finding line format (from code-review-board report):
                       `- [ ] [R-XX-NNN] **Severity** | `perspective` | `file:line` | Description`
                       For each matching finding, extract:
                       - Finding ID (e.g., [R-AR-003])
                       - Severity (Critical, Major, Minor)
                       - File path and line number
                       - Description
                       - Scope tag ([multi-site] or [cross-module])
                       - Impact text (after scope tag)
                       - Evidence snippet (if present)
                       - Solution text (if present)
                    d. If no unchecked findings exist at all (every finding is `- [x]`),
                       display and exit: "All findings already fixed in {file}."
                    e. If unchecked findings exist but none match (all have Solution
                       lines or are [single-site] without Solution), display and exit:
                       "No unchecked findings without Solution found in {file}.
                        Findings with Solution lines can be fixed with /batch-fix."

 3. VALIDATE     → For each extracted finding:
                    a. Check if the file referenced in the finding exists.
                       If not, mark as stale with reason "file not found".
                    b. If Evidence snippet is present, read the file and check
                       if the snippet matches at or near the specified line (±10 lines).
                       If not, mark as stale with reason "code changed since review".
                    c. Stale findings are excluded from ranking but reported:
                       "Excluded {N} stale findings: {list of IDs and reasons}"
                    d. If all findings are stale, display and exit:
                       "All [multi-site]/[cross-module] findings are stale."

 4. RANK         → LLM analyzes all valid findings and selects up to 4 candidates.
                    Priority rules (in order of precedence):
                    a. Dependency prerequisites first — findings that are
                       prerequisites for other findings (e.g., interface changes
                       before consumers, shared utility before callers).
                    b. Higher severity — Critical > Major > Minor.
                    c. Smaller impact scope within same severity — [multi-site]
                       before [cross-module] when severity is equal.

 5. SELECT       → Display candidates as numbered list:

                    ```
                    ## Candidates ({N} of {total} findings)

                    1. [R-AR-003] Major | [cross-module] | `src/auth/session.ts:45`
                       Session token storage format inconsistent with new spec
                       → Reason: Prerequisite for R-SC-001 and R-CR-002 (interface change)

                    2. [R-CR-005] Major | [multi-site] | `src/api/handler.ts:120`
                       Error handling pattern inconsistent across 3 locations
                       → Reason: Contained within single module, lower risk

                    3. ...
                    4. ...

                    Enter a number to select, or "all" to see all findings:
                    ```

                    a. Number → select that finding, proceed to step 6.
                    b. "all" → display full list of valid findings with same
                       format (no ranking reasons), let user pick by number.

 6. APPROACH     → Present two options:

                    ```
                    How would you like to approach this fix?
                      A) brainstorming — Detailed design discussion before implementation
                      B) Plan mode — Quick design proposal and implementation
                      C) discussion-board — Team debate to explore the best approach
                    ```

                    Wait for user selection.

 7. EXECUTE      → a. Build context block from selected finding:
                       - Finding ID, severity, scope tag
                       - File path and line number
                       - Description
                       - Impact text
                       - Evidence snippet (if present)
                       - Solution text (if present)

                    b. If option A (brainstorming):
                       Invoke the brainstorming skill with the context block
                       as arguments. The brainstorming flow handles design
                       discussion, spec writing, and transitions to
                       implementation planning.

                    c. If option B (Plan mode):
                       Enter Plan mode (EnterPlanMode). Provide the context
                       block and ask for a fix proposal. After user approves
                       the plan, exit Plan mode and implement the fix.

                    d. If option C (discussion-board):
                       Invoke the discussion-board skill with the context block
                       as the proposition. The discussion-board produces a
                       Design Doc via structured team debate. After the
                       discussion concludes, use the Design Doc as context
                       to implement the fix.

                    e. Implementation is complete when the user confirms the
                       fix is done, or the delegated workflow completes.
                    f. After completion, ask the user for a one-line fix summary
                       (used as the `<!-- fixed: ... -->` memo). If the user
                       declines or gives no summary, generate one from the
                       git diff of modified files.

 8. VERIFY       → a. Record the HEAD commit hash before EXECUTE (step 7).
                       After EXECUTE completes, check for changes:
                       - If HEAD has advanced (delegated workflow committed),
                         extract modified file list from the new commit(s).
                       - If HEAD is unchanged, check for uncommitted modifications
                         in the working tree.
                       - If neither, no source files were modified.
                    b. If no source files were modified, display:
                       "No code changes made. Review file not updated."
                       Skip UPDATE, COMMIT, and proceed to REPORT.

 9. UPDATE       → Edit the review Markdown for the fixed finding:
                    a. Change `- [ ]` to `- [x]` on the finding's checkbox line
                       (match by finding ID, e.g., `[R-AR-003]`).
                    b. Find the last `>` blockquote line belonging to that finding
                       (Impact, Evidence, or Solution line).
                    c. Insert a new line after it:
                       `  <!-- fixed: {fix summary from step 7e} -->`

                    This matches the batch-fix update format exactly.

10. COMMIT       → a. If the delegated workflow already committed the fix
                       (HEAD advanced during EXECUTE), commit only the review
                       Markdown update with message:
                       `docs: mark [R-XX-NNN] fixed in {review-file-name}`
                    b. If the fix is uncommitted, stage all modified source files
                       + the updated review Markdown.
                       Use specific file paths (not `git add -A`).
                       Commit with message:
                       `fix: deep-fix [R-XX-NNN] from {review-file-name}`
                    c. Include `Co-Authored-By: Claude <noreply@anthropic.com>`
                       in all commit messages.

11. REPORT       → Display terminal summary:

                    ```
                    ## deep-fix Complete

                    Fixed: [R-AR-003] Major | src/auth/session.ts:45
                    Memo: {short description of the fix}
                    Review: {review-file-path} (updated)
                    Commit: {short-hash}

                    Remaining: {N} findings without Solution
                    ```
```

---

## Error Handling

| Situation | Action |
|-----------|--------|
| Review file not found (no argument, no files in docs/reviews/) | Display error message and exit |
| Review file argument points to nonexistent file | Display error message and exit |
| All findings already fixed (`- [x]`) | Display "All findings already fixed" and exit |
| No unchecked findings without Solution (all have Solution or are already fixed) | Display message suggesting `/batch-fix` and exit |
| All findings stale (Evidence mismatch or file missing) | Display "All findings are stale" and exit |
| User enters invalid selection number | Re-prompt with valid range |
| User cancels during finding selection | Display "Cancelled" and exit |
| User cancels during approach selection | Display "Cancelled" and exit |
| brainstorming/Plan mode/discussion-board abandoned by user | Do not update review file, do not commit, exit gracefully |
| No source files modified after implementation | Skip commit, do not update review checkbox |
| Commit failure (e.g., pre-commit hook) | Display error, leave review file unchanged |
