# batch-fix: Solution-Based Filter Redesign

## Summary

Change the batch-fix skill's extraction criteria from scope-tag-based (`[single-site]`) to Solution-based (`> Solution:` line exists). Add two-phase internal dispatch to handle both single-site and multi-site/cross-module findings selected by the user.

## Motivation

The current batch-fix skill filters findings by Impact scope tag (`[single-site]`), which uses the *scope of change* as a proxy for automation safety. The actual signal for "safe to automate" is whether the fix approach is explicitly described — i.e., whether a `> Solution:` line exists. This redesign aligns the filter with the true intent: only fix findings where the solution is clear and requires no user judgment.

## Design

### Extraction Criteria

**Current:** `- [ ]` (unchecked) AND `> Impact:` line starts with `[single-site]`

**New:** `- [ ]` (unchecked) AND `> Solution:` line exists

Scope tags (`[single-site]`, `[multi-site]`, `[cross-module]`) are not used as extraction filters. They are used only for internal dispatch routing after extraction.

### Selection Flow (Checkbox UI)

Display all extracted findings with checkboxes, all selected by default:

```
Found {N} fixable findings (with Solution) in {review-file}:

 1. [x] [R-RD-001] Minor | utils.ts:12 | Variable name unclear
 2. [x] [R-RD-005] Minor | utils.ts:34 | Redundant type assertion
 3. [x] [R-PF-003] Major | api.ts:89  | Array.find in hot loop

Enter numbers to toggle (e.g., "3,5"), or "ok" to proceed:
```

- Default: all selected
- User enters numbers to toggle selection (entering a number again re-selects it)
- After each toggle input, redisplay the updated list and prompt again
- "ok" or empty input to confirm and proceed
- If all items deselected: display message and exit

### Internal Dispatch (Two-Phase)

After user confirmation, classify selected findings by scope tag and dispatch in two phases:

**Phase 1 — `[single-site]` findings (parallel)**
- Group by file path
- Launch 1 Agent per file group in parallel (concurrent Agent tool calls)
- Same prompt template and response format as current batch-fix

**Phase 2 — `[multi-site]` / `[cross-module]` findings (sequential)**
- Dispatch 1 Agent per finding, sequentially
- Each Agent can read and edit multiple files as needed
- Prompt template adapted for multi-file context (see Phase 2 Agent Prompt below)
- Same response format as Phase 1 (per-finding: description of change or SKIPPED with reason)

**Scope tag fallback:** If a finding has `> Solution:` but a malformed or missing `> Impact:` line, treat it as Phase 2 (`[multi-site]`) for safety — the sequential, multi-file-capable dispatch is the safer default for findings with unknown scope.

**Phase skipping:** If either phase has zero findings after classification, skip it entirely.

### Description Change

**Current:**
```
Batch-fix single-site code review findings.
Use when applying fixes for low-impact findings from code-review-board reports.
Triggers: /batch-fix, batch fix, 一括修正
```

**New:**
```
Batch-fix code review findings that have a clear Solution.
Use when applying batch fixes for code-review-board findings.
Triggers: /batch-fix, batch fix, 一括修正
```

### Title and Header Changes

**Current:** `# batch-fix — Batch Fix Single-Site Review Findings`

**New:** `# batch-fix — Batch Fix Review Findings with Solution`

### When to Use / When NOT to Use

**When to Use:**
- The user wants to batch-fix findings from a code review report
- The user wants to auto-fix findings that have a clear Solution after running `/code-review`

**When NOT to Use:**
- The user wants to manually fix specific findings one by one
- Findings require design discussion or planning before implementation (use `/deep-fix`)

### Error Handling Changes

| Situation | Current Message | New Message |
|-----------|----------------|-------------|
| No unchecked findings with `> Solution:` (but other unchecked exist) | "No unchecked [single-site] findings found in {file}." | "No unchecked findings with Solution found in {file}." |
| All findings already fixed | "All findings already fixed in {file}." | Unchanged |
| All findings deselected by user | "No findings selected. Exiting." | Unchanged |

All other error handling remains unchanged.

### Commit Message Change

**Current:** `fix: batch-fix {N} single-site findings from {review-file-name}`

**New:** `fix: batch-fix {N} findings from {review-file-name}`

### Boundary with deep-fix

- **batch-fix**: Findings with `> Solution:` line — automated fix following the described solution
- **deep-fix**: Findings without `> Solution:` line, or findings requiring design/planning before implementation

**Required changes to deep-fix SKILL.md:**
- Update extraction filter to exclude findings that have a `> Solution:` line (those belong to batch-fix)
- Update "When NOT to Use" to reflect the new boundary: "`[single-site]` findings → use `/batch-fix`" becomes "Findings with `> Solution:` → use `/batch-fix`"
- Update the exit message (line 91) from "Remaining unchecked findings are [single-site] — use /batch-fix." to "Remaining unchecked findings have Solution lines — use /batch-fix."

### Phase 2 Agent Prompt

Phase 2 findings may span multiple files. The prompt template is adapted from Phase 1:

```
Fix the following code review finding.

INSTRUCTIONS:
1. Read all files mentioned in the finding and Solution.
2. If Evidence is provided, check if it matches the current code at or near
   the specified line. If the code has changed (Evidence does not match), SKIP.
   If Evidence is "none", skip this check and proceed to step 3.
3. Follow the Solution description to apply the fix across all affected files.
4. Do NOT make changes beyond what the finding and Solution describe.

FINDING:
- {finding_id} | {file}:{line} | {severity} | {description}
  Impact: {impact_text}
  Evidence: {evidence_snippet or "none"}
  Solution: {solution_text}

RESPONSE FORMAT (one line, no other output):
{finding_id}: {description of changes made, including all files modified}
{finding_id}: SKIPPED — {reason}
```

Key difference from Phase 1: no `file_path` scope restriction — the Agent reads and edits whatever files the Solution requires.

## Flow (Updated)

```
1. PARSE    — Read review Markdown, extract unchecked findings with > Solution: line
             → Classify by scope tag into two groups:
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
```

## Changes NOT in Scope

- No changes to the Phase 1 Agent prompt template (reuses current batch-fix template), except: update the Evidence check instruction to match Phase 2 ("If Evidence is 'none', skip this check")
- No changes to the UPDATE logic (checkbox + fixed comment)
- No changes to the REPORT format (other than removing "single-site" wording)
- No changes to the code-review-board finding format or Solution line generation
