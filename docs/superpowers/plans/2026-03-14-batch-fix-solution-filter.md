# batch-fix Solution-Based Filter Redesign — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Change batch-fix extraction from scope-tag-based to Solution-based filtering, add two-phase dispatch for single-site (parallel) and multi-site/cross-module (sequential) findings.

**Architecture:** Modify two SKILL.md files (batch-fix and deep-fix) to realign their boundary. batch-fix now owns all findings with `> Solution:` lines; deep-fix owns findings without. batch-fix gains a Phase 2 sequential dispatch for non-single-site findings.

**Tech Stack:** Markdown skill definitions (no runtime code — these are Claude Code skill specs)

**Spec:** `docs/superpowers/specs/2026-03-14-batch-fix-solution-filter-design.md`

---

## Chunk 1: batch-fix SKILL.md Updates

### Task 1: Update frontmatter and header

**Files:**
- Modify: `skills/batch-fix/SKILL.md:1-11`

- [ ] **Step 1: Update frontmatter description**

Change lines 2-6:
```yaml
---
name: batch-fix
description: >-
  Batch-fix code review findings that have a clear Solution.
  Use when applying batch fixes for code-review-board findings.
  Triggers: /batch-fix, batch fix, 一括修正
---
```

- [ ] **Step 2: Update title and summary paragraph**

Change line 9:
```markdown
# batch-fix — Batch Fix Review Findings with Solution
```

Change line 11:
```markdown
Parse a code-review-board report, extract unchecked findings that have a `> Solution:` line, let the user select which to fix via checkbox UI, dispatch Agents to apply fixes (parallel for single-site, sequential for multi-site/cross-module), update the review Markdown, and commit.
```

- [ ] **Step 3: Update When to Use / When NOT to Use**

Replace lines 13-21:
```markdown
## When to Use

- The user wants to batch-fix findings from a code review report: `/batch-fix`, "batch fix", "一括修正"
- The user wants to auto-fix findings that have a clear Solution after running `/code-review`

## When NOT to Use

- The user wants to manually fix specific findings one by one
- Findings require design discussion or planning before implementation (use `/deep-fix`)
```

- [ ] **Step 4: Commit**

```bash
git add skills/batch-fix/SKILL.md
git commit -m "refactor(batch-fix): update frontmatter, header, and usage sections for Solution-based filter"
```

### Task 2: Update Architecture Note and Flow summary

**Files:**
- Modify: `skills/batch-fix/SKILL.md:35-52`

- [ ] **Step 1: Update Architecture Note**

Replace lines 35-37:
```markdown
## Architecture Note

batch-fix is a **coordinator skill** — it uses Agent tool calls for dispatch but does not use the full Agent Team model (TeamCreate/SendMessage/WHITEBOARD.md). Phase 1 (single-site) uses parallel dispatch with one Agent per file group. Phase 2 (multi-site/cross-module) uses sequential dispatch with one Agent per finding, allowing multi-file edits.
```

- [ ] **Step 2: Update Flow summary**

Replace lines 41-52:
```markdown
## Flow

` `` (triple backticks)
1. PARSE    — Read review Markdown, extract unchecked findings with > Solution: line
             → Classify by scope tag:
               - Phase 1: [single-site]
               - Phase 2: [multi-site], [cross-module], or missing/malformed scope tag
2. PRESENT  — Display finding list with checkbox UI (default: all selected)
3. CONFIRM  — User toggles selection, confirms with "ok"
4. PHASE 1  — [single-site] grouped by file → parallel Agent dispatch
5. PHASE 2  — [multi-site] / [cross-module] → 1 finding per Agent, sequential dispatch
6. COLLECT  — Merge results from both phases
7. UPDATE   — Update review Markdown: [x] checkbox + <!-- fixed: memo --> comment
8. COMMIT   — Stage modified code files + updated review Markdown, single commit
9. REPORT   — Display summary: N fixed, N skipped
` ``
```

(Note: The triple backticks above are escaped for plan readability. Use actual ` ``` ` in the file.)

- [ ] **Step 3: Commit**

```bash
git add skills/batch-fix/SKILL.md
git commit -m "refactor(batch-fix): update architecture note and flow summary for two-phase dispatch"
```

### Task 3: Update PARSE step in Workflow

**Files:**
- Modify: `skills/batch-fix/SKILL.md:58-81`

- [ ] **Step 1: Rewrite PARSE step**

Replace lines 59-81 with:
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
```

- [ ] **Step 2: Commit**

```bash
git add skills/batch-fix/SKILL.md
git commit -m "refactor(batch-fix): update PARSE step for Solution-based extraction and scope classification"
```

### Task 4: Update PRESENT and CONFIRM steps

**Files:**
- Modify: `skills/batch-fix/SKILL.md:83-105`

- [ ] **Step 1: Rewrite PRESENT step**

Replace PRESENT (lines 83-97) with:
```
 2. PRESENT       → Display extracted findings as a numbered checkbox list:

                     ```
                     Found {N} fixable findings (with Solution) in {review-file}:

                      1. [x] [R-RD-001] Minor | utils.ts:12 | Variable name unclear
                      2. [x] [R-RD-005] Minor | utils.ts:34 | Redundant type assertion
                      3. [x] [R-PF-003] Major | api.ts:89  | Array.find in hot loop
                      ...

                     Enter numbers to toggle (e.g., "3,5"), or "ok" to proceed:
                     ```

                     All findings are selected by default (shown with [x]).
                     Wait for user input.
```

- [ ] **Step 2: Rewrite CONFIRM step**

Replace CONFIRM (lines 99-105) with:
```
 3. CONFIRM       → a. Parse user input:
                        - "ok" or empty → proceed with all selected
                        - Comma-separated numbers → toggle those items
                          (selected → deselected, deselected → selected)
                     b. After each toggle input, redisplay the updated list
                        and prompt again with the same prompt text.
                     c. If all items deselected, display message and exit:
                        "No findings selected. Exiting."
```

- [ ] **Step 3: Commit**

```bash
git add skills/batch-fix/SKILL.md
git commit -m "refactor(batch-fix): update PRESENT/CONFIRM for toggle-based checkbox UI"
```

### Task 5: Replace DISPATCH with Phase 1 and Phase 2

**Files:**
- Modify: `skills/batch-fix/SKILL.md:107-137`

- [ ] **Step 1: Replace DISPATCH step with PHASE 1 and PHASE 2**

Replace DISPATCH (lines 107-137) with:
```
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
```

- [ ] **Step 2: Commit**

```bash
git add skills/batch-fix/SKILL.md
git commit -m "refactor(batch-fix): replace DISPATCH with two-phase dispatch (Phase 1 parallel, Phase 2 sequential)"
```

### Task 6: Update COLLECT, COMMIT, and Error Handling

**Files:**
- Modify: `skills/batch-fix/SKILL.md:139-196`

- [ ] **Step 1: Update COLLECT step**

Replace COLLECT (lines 139-144) with:
```
 6. COLLECT       → a. Gather responses from all Phase 1 and Phase 2 Agents.
                     b. Parse each response line:
                        - Lines containing ": SKIPPED" → record as skipped with reason
                        - Other lines → record as fixed with memo
                     c. If an Agent fails entirely (error, no response), record all
                        findings for that Agent as skipped with reason "Agent error".
```

- [ ] **Step 2: Update COMMIT step**

Replace the commit message in COMMIT (line 161):
```
                     c. Commit with message:
                        `fix: batch-fix {N} findings from {review-file-name}`
                        Include `Co-Authored-By: Claude <noreply@anthropic.com>`.
```

- [ ] **Step 3: Update Error Handling table**

Replace the error handling table (lines 184-195):
```markdown
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
```

- [ ] **Step 4: Commit**

```bash
git add skills/batch-fix/SKILL.md
git commit -m "refactor(batch-fix): update COLLECT, COMMIT, and error handling for new filter"
```

---

## Chunk 2: deep-fix SKILL.md Updates

### Task 7: Update deep-fix boundary with batch-fix

**Files:**
- Modify: `skills/deep-fix/SKILL.md:1-6,10-11,19-22,72-74,86-91,223`

- [ ] **Step 1: Update deep-fix description in frontmatter**

Change lines 3-6:
```yaml
description: >-
  Deep-fix complex code review findings that require design planning.
  Use for findings without a clear Solution that need discussion before implementation.
  Triggers: /deep-fix, deep fix, 個別修正
```

- [ ] **Step 2: Update summary paragraph**

Change lines 10-11:
```markdown
Address code-review-board findings that lack a `> Solution:` line and require design discussion or planning before implementation. Parses the review Markdown, validates findings against current code, ranks candidates by dependency analysis, and delegates to brainstorming or Plan mode for design and implementation.
```

- [ ] **Step 3: Update When to Use / When NOT to Use**

Replace lines 14-22:
```markdown
## When to Use

- The user wants to fix a complex finding from a code review report: `/deep-fix`, "deep fix", "個別修正"
- The finding lacks a `> Solution:` line and requires design discussion or planning
- The fix needs design discussion or planning before implementation

## When NOT to Use

- Findings have a `> Solution:` line — use `/batch-fix` instead
- The user wants to batch-fix multiple findings at once — use `/batch-fix` instead
```

- [ ] **Step 4: Update EXTRACT step filter**

Replace lines 72-74:
```
                    b. Extract findings matching ALL of:
                       - Line starts with `- [ ]` (unchecked only — skip `- [x]`)
                       - Has `> Impact:` line starting with `[multi-site]` or `[cross-module]`
                       - Does NOT have a `> Solution:` line (findings with Solution belong to batch-fix)
```

Note: `[single-site]` findings without a `> Solution:` line are intentionally not claimed by either skill. These are simple, localized issues that are best fixed manually by the developer.

- [ ] **Step 5: Update exit message**

Replace lines 88-91:
```
                    e. If unchecked findings exist but none match (all have Solution
                       lines or are [single-site] without Solution), display and exit:
                       "No unchecked findings without Solution found in {file}.
                        Findings with Solution lines can be fixed with /batch-fix."
```

- [ ] **Step 6: Update REPORT remaining count**

Replace line 223:
```
                    Remaining: {N} findings without Solution
```

- [ ] **Step 7: Update Error Handling table**

Replace the row at line 236:
```
| No unchecked findings without Solution (all have Solution or are already fixed) | Display message suggesting `/batch-fix` and exit |
```

- [ ] **Step 8: Commit**

```bash
git add skills/deep-fix/SKILL.md
git commit -m "refactor(deep-fix): update boundary — deep-fix now owns findings without Solution line"
```

---

## Chunk 3: Version Bump

### Task 8: Bump plugin version

**Files:**
- Modify: `.claude-plugin/plugin.json:3`
- Modify: `.claude-plugin/marketplace.json:11`

- [ ] **Step 1: Bump version in plugin.json**

Change `"version": "1.3.0"` to `"version": "1.4.0"` in `.claude-plugin/plugin.json`.

- [ ] **Step 2: Bump version in marketplace.json**

Change `"version": "1.3.0"` to `"version": "1.4.0"` in `.claude-plugin/marketplace.json`.

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore: bump plugin version to 1.4.0 for batch-fix Solution-based filter redesign"
```
