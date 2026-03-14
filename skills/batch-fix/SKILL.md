---
name: batch-fix
description: >-
  Batch-fix code review findings that have a clear Solution.
  Use when applying batch fixes for code-review-board findings.
  Triggers: /batch-fix, batch fix, 一括修正
---

# batch-fix — Batch Fix Review Findings with Solution

Parse a code-review-board report, extract unchecked findings that have a `> Solution:` line, let the user select which to fix via checkbox UI, dispatch Agents to apply fixes (parallel for single-site, sequential for multi-site/cross-module), update the review Markdown, and commit.

## When to Use

- The user wants to batch-fix findings from a code review report: `/batch-fix`, "batch fix", "一括修正"
- The user wants to auto-fix findings that have a clear Solution after running `/code-review`

## When NOT to Use

- The user wants to manually fix specific findings one by one
- Findings require design discussion or planning before implementation (use `/deep-fix`)

## Arguments

- `target` (optional): Path to a review Markdown file. If omitted, uses the most recent `*-review.md` in `docs/reviews/`.

**Examples:**
```
/batch-fix
/batch-fix docs/reviews/2026-03-13-api-review.md
```

---

## Architecture Note

batch-fix is a **coordinator skill** — it uses parallel Agent tool calls for dispatch but does not use the full Agent Team model (TeamCreate/SendMessage/WHITEBOARD.md). This is a lighter pattern appropriate for tasks where Agents work on independent files with no need for inter-Agent communication.

---

## Flow

```
1. PARSE    — Read review Markdown, extract unchecked [single-site] findings
2. PRESENT  — Display finding list with selection UI (default: all selected)
3. CONFIRM  — User selects/deselects findings, confirms
4. DISPATCH — Group findings by file path, spawn 1 Agent per file in parallel
5. COLLECT  — Gather results from Agents (success + fix memo, or skip reason)
6. UPDATE   — Update review Markdown: [x] checkbox + <!-- fixed: memo --> comment
7. COMMIT   — Stage modified code files + updated review Markdown, auto-commit (skip if 0 fixes)
8. REPORT   — Display summary: N fixed, N skipped
```

---

## Workflow

```
 1. PARSE         → a. If target argument provided, use that path.
                     b. Otherwise, glob `docs/reviews/*-review.md` and select the
                        most recently modified file.
                     c. If no review file found, display error and exit:
                        "No review file found. Run /code-review first or specify a path."
                     d. Read the review Markdown.
                     e. Extract findings matching ALL of:
                        - Line starts with `- [ ]` (unchecked only — skip `- [x]`)
                        - Has `> Impact:` line starting with `[single-site]`
                     f. For each matching finding, extract:
                        - Finding ID (e.g., [R-RD-001])
                        - Severity (Critical, Major, Minor)
                        - Perspective name
                        - File path and line number
                        - Description
                        - Impact text (after [single-site])
                        - Evidence snippet (if present)
                        - Solution text (if present)
                     g. If no unchecked findings exist at all (every finding is `- [x]`),
                        display and exit: "All findings already fixed in {file}."
                     h. If unchecked findings exist but none are `[single-site]`,
                        display and exit:
                        "No unchecked [single-site] findings found in {file}."

 2. PRESENT       → Display extracted findings as a numbered list:

                     ```
                     Found {N} single-site findings in {review-file}:

                      1. [x] [R-RD-001] Minor | utils.ts:12 | Variable name unclear
                      2. [x] [R-RD-005] Minor | utils.ts:34 | Redundant type assertion
                      3. [x] [R-PF-003] Major | api.ts:89  | Array.find in hot loop
                      ...

                     Enter numbers to deselect (e.g., "3,5"), or "ok" to proceed:
                     ```

                     All findings are selected by default (shown with [x]).
                     Wait for user input.

 3. CONFIRM       → a. Parse user input:
                        - "ok" or empty → proceed with all selected
                        - Comma-separated numbers → deselect those items
                     b. If user deselects items, redisplay the updated list and
                        ask for confirmation again.
                     c. If all items deselected, display message and exit:
                        "No findings selected. Exiting."

 4. DISPATCH      → a. Group selected findings by file path.
                     b. For each file group, launch an Agent tool call with:

                        Prompt template:
                        """
                        Fix the following code review findings in `{file_path}`.

                        INSTRUCTIONS:
                        1. Read the file first.
                        2. For each finding, check if the Evidence snippet matches the
                           current code at or near the specified line. If the code has
                           changed (Evidence does not match), SKIP that finding.
                        3. If a Solution is provided, follow it. Otherwise, make the
                           minimal fix implied by the description.
                        4. Do NOT make changes beyond what each finding describes.

                        FINDINGS:
                        {for each finding in this file group}
                        - {finding_id} | Line {line} | {severity} | {description}
                          Impact: {impact_text}
                          Evidence: {evidence_snippet or "none"}
                          Solution: {solution_text or "none"}
                        {end for}

                        RESPONSE FORMAT (one line per finding, no other output):
                        {finding_id}: {description of change made}
                        {finding_id}: SKIPPED — {reason}
                        """

                     c. Launch ALL file-group Agents in parallel (concurrent
                        Agent tool calls in a single message).

 5. COLLECT       → a. Gather responses from all Agents.
                     b. Parse each response line:
                        - Lines containing ": SKIPPED" → record as skipped with reason
                        - Other lines → record as fixed with memo
                     c. If an Agent fails entirely (error, no response), record all
                        findings for that file as skipped with reason "Agent error".

 6. UPDATE        → For each successfully fixed finding, edit the review Markdown:
                     a. Change `- [ ]` to `- [x]` on the finding's checkbox line
                        (match by finding ID, e.g., `[R-RD-001]`).
                     b. Find the last `>` blockquote line belonging to that finding
                        (Impact, Evidence, or Solution line).
                     c. Insert after it: `  <!-- fixed: {memo from Agent} -->`

                     Existing `> Solution:` lines are preserved as-is.
                     Skipped findings remain unchanged (`- [ ]`).

 7. COMMIT        → a. If no source files were modified (all findings skipped),
                        skip the commit entirely.
                     b. Stage all modified source files + the updated review Markdown.
                        Use specific file paths (not `git add -A`).
                     c. Commit with message:
                        `fix: batch-fix {N} single-site findings from {review-file-name}`
                        Include `Co-Authored-By: Claude <noreply@anthropic.com>`.

 8. REPORT        → Display terminal summary:

                     ```
                     ## batch-fix Complete

                     Fixed: {N} | Skipped: {N}
                     Review: {review-file-path} (updated)
                     Commit: {short-hash}

                     ### Skipped
                     - [R-CR-002]: file not found (deleted since review)
                     - [R-AR-001]: line 45 already modified
                     ```

                     If all findings were skipped, omit the Commit line.
                     If no findings were skipped, omit the ### Skipped section.
```

---

## Error Handling

| Situation | Action |
|-----------|--------|
| Review file not found (no argument, no files in docs/reviews/) | Display error message and exit |
| All findings already fixed (`- [x]`) | Display "All findings already fixed" and exit |
| No unchecked `[single-site]` findings (but other unchecked exist) | Display "No unchecked [single-site] findings" and exit |
| All findings deselected by user | Display message and exit |
| File referenced by finding does not exist | Agent skips finding, reports "file not found" |
| Evidence snippet does not match current code | Agent skips finding, reports "code changed since review" |
| Agent fails entirely | Skip all findings for that file, report "Agent error" |
| All findings skipped | Skip commit, display report only |
