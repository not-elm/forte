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

batch-fix is a **coordinator skill** — it uses Agent tool calls for dispatch but does not use the full Agent Team model (TeamCreate/SendMessage/WHITEBOARD.md). Phase 1 (single-site) uses parallel dispatch with one Agent per file group. Phase 2 (multi-site/cross-module) uses sequential dispatch with one Agent per finding, allowing multi-file edits.

---

## Flow

```
1. PARSE    — Read review Markdown, extract unchecked findings with > Solution: line
             → Classify by scope tag:
               - Phase 1: [single-site]
               - Phase 2: [multi-site], [cross-module], or missing/malformed scope tag
2. PRESENT  — AskUserQuestion multiSelect UI (findings grouped in batches of 4)
3. CONFIRM  — Deselected items are excluded; if none selected, exit
4. PHASE 1  — [single-site] grouped by file → parallel Agent dispatch
5. PHASE 2  — [multi-site] / [cross-module] → 1 finding per Agent, sequential dispatch
6. COLLECT  — Merge results from both phases
7. UPDATE   — Update review Markdown: [x] checkbox + <!-- fixed: memo --> comment
8. COMMIT   — Stage modified code files + updated review Markdown, single commit
9. REPORT   — Display summary: N fixed, N skipped
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
                        - Has `> Solution:` line (presence required — content is the solution text)
                     f. For each matching finding, extract:
                        - Finding ID (e.g., [R-RD-001])
                        - Severity (Critical, Major, Minor)
                        - Perspective name
                        - File path and line number
                        - Description
                        - Scope tag from `> Impact:` line ([single-site], [multi-site], or [cross-module])
                          If `> Impact:` line is missing or malformed, default to [multi-site]
                        - Impact text (after scope tag)
                        - Evidence snippet (if present)
                        - Solution text
                     g. Classify extracted findings by scope tag:
                        - Phase 1: [single-site]
                        - Phase 2: [multi-site], [cross-module]
                     h. If no unchecked findings exist at all (every finding is `- [x]`),
                        display and exit: "All findings already fixed in {file}."
                     i. If unchecked findings exist but none have a `> Solution:` line,
                        display and exit:
                        "No unchecked findings with Solution found in {file}."

 2. PRESENT       → Present findings via AskUserQuestion with `multiSelect: true`.

                     Each option represents one finding:
                       - label:       "[R-RD-001] Minor | utils.ts:12 | Variable name unclear"
                       - description: "Solution: Rename to `descriptiveName`"

                     AskUserQuestion constraints:
                       - Max 4 options per question, max 4 questions per call
                       - Options require minItems: 2
                       - No pre-selection API (user selects from scratch)

                     Grouping rules:
                       - Pack up to 4 findings per question, up to 4 questions
                         per AskUserQuestion call (max 16 findings per call).
                       - If the last group would have only 1 finding, merge it
                         into the previous group (minItems: 2 constraint).
                       - If total findings > 16, issue multiple sequential
                         AskUserQuestion calls.

                     Question text:
                       - Single question:  "Select findings to fix:"
                       - Multiple questions: "Select findings to fix (group {i}/{total}):"

                     The user selects the findings they WANT fixed.
                     Unselected findings are skipped.

                     IMPORTANT: Never fall back to a text-based numbered list
                     or number-input toggling. Always use AskUserQuestion
                     multiSelect.

 3. CONFIRM       → Collect responses from all AskUserQuestion calls.
                     Findings the user selected → proceed to fix.
                     Findings not selected → skip.
                     "Other" text responses → ignore (not applicable).
                     If no findings are selected across all calls:
                       display "No findings selected. Exiting." and exit.

 4. PHASE 1       → [single-site] findings — parallel dispatch.
                     a. Group Phase 1 findings by file path.
                     b. For each file group, launch an Agent tool call with:

                        Prompt template:
                        """
                        Fix the following code review findings in `{file_path}`.

                        INSTRUCTIONS:
                        1. Read the file first.
                        2. For each finding, if Evidence is provided, check if it
                           matches the current code at or near the specified line.
                           If the code has changed (Evidence does not match), SKIP
                           that finding. If Evidence is "none", skip this check.
                        3. Follow the Solution to apply the fix.
                        4. Do NOT make changes beyond what each finding describes.

                        FINDINGS:
                        {for each finding in this file group}
                        - {finding_id} | Line {line} | {severity} | {description}
                          Impact: {impact_text}
                          Evidence: {evidence_snippet or "none"}
                          Solution: {solution_text}
                        {end for}

                        RESPONSE FORMAT (one line per finding, no other output):
                        {finding_id}: {description of change made}
                        {finding_id}: SKIPPED — {reason}
                        """

                     c. Launch ALL file-group Agents in parallel (concurrent
                        Agent tool calls in a single message).
                     d. If no Phase 1 findings, skip this step entirely.

 5. PHASE 2       → [multi-site] / [cross-module] findings — sequential dispatch.
                     a. For each Phase 2 finding, launch a single Agent with:

                        Prompt template:
                        """
                        Fix the following code review finding.

                        INSTRUCTIONS:
                        1. Read all files mentioned in the finding and Solution.
                        2. If Evidence is provided, check if it matches the current
                           code at or near the specified line. If the code has
                           changed (Evidence does not match), SKIP.
                           If Evidence is "none", skip this check and proceed to
                           step 3.
                        3. Follow the Solution description to apply the fix across
                           all affected files.
                        4. Do NOT make changes beyond what the finding and Solution
                           describe.

                        FINDING:
                        - {finding_id} | {file}:{line} | {severity} | {description}
                          Impact: {impact_text}
                          Evidence: {evidence_snippet or "none"}
                          Solution: {solution_text}

                        RESPONSE FORMAT (one line, no other output):
                        {finding_id}: {description of changes made, including all files modified}
                        {finding_id}: SKIPPED — {reason}
                        """

                     b. Dispatch Agents one at a time, sequentially (wait for
                        each Agent to complete before launching the next).
                     c. If no Phase 2 findings, skip this step entirely.

 6. COLLECT       → a. Gather responses from all Phase 1 and Phase 2 Agents.
                     b. Parse each response line:
                        - Lines containing ": SKIPPED" → record as skipped with reason
                        - Other lines → record as fixed with memo
                     c. If an Agent fails entirely (error, no response), record all
                        findings for that Agent as skipped with reason "Agent error".

 7. UPDATE        → For each successfully fixed finding, edit the review Markdown:
                     a. Change `- [ ]` to `- [x]` on the finding's checkbox line
                        (match by finding ID, e.g., `[R-RD-001]`).
                     b. Find the last `>` blockquote line belonging to that finding
                        (Impact, Evidence, or Solution line).
                     c. Insert after it: `  <!-- fixed: {memo from Agent} -->`

                     Existing `> Solution:` lines are preserved as-is.
                     Skipped findings remain unchanged (`- [ ]`).

 8. COMMIT        → a. If no source files were modified (all findings skipped),
                        skip the commit entirely.
                     b. Stage all modified source files + the updated review Markdown.
                        Use specific file paths (not `git add -A`).
                     c. Commit with message:
                        `fix: batch-fix {N} findings from {review-file-name}`
                        Include `Co-Authored-By: Claude <noreply@anthropic.com>`.

 9. REPORT        → Display terminal summary:

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
| No unchecked findings with `> Solution:` (but other unchecked exist) | Display "No unchecked findings with Solution found in {file}." and exit |
| All findings deselected by user | Display message and exit |
| File referenced by finding does not exist | Agent skips finding, reports "file not found" |
| Evidence snippet does not match current code | Agent skips finding, reports "code changed since review" |
| Agent fails entirely | Skip all findings for that Agent, report "Agent error" |
| All findings skipped | Skip commit, display report only |
