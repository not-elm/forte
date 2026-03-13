# batch-fix — Design Spec

## Overview

A skill that batch-fixes code-review-board findings with small impact scope (`[single-site]`). Parses the review Markdown, presents fixable findings for user selection, dispatches parallel Agents per file, updates the review Markdown, and commits.

## Scope

Two deliverables:

1. **New skill: `batch-fix`** — `skills/batch-fix/SKILL.md`
2. **code-review-board modification** — Add structured Impact scope tags to finding format

## code-review-board Changes

### Impact Scope Tags

Every `> Impact:` line must begin with a scope tag:

| Tag | Meaning | batch-fix target |
|-----|---------|-----------------|
| `[single-site]` | Fix is contained to the target line/function, no ripple effects | Yes |
| `[multi-site]` | Multiple locations within the same module need changes | No |
| `[cross-module]` | Changes span modules or affect external interfaces | No |

### Tag Assignment Rules (for reviewers)

Tags are assigned by **reviewers** during the reviewing phase (step 3 in the reviewer workflow). The scope tag is part of the required `> Impact:` line in every finding.

- `[single-site]`: The fix modifies only the reported location. No callers, exports, or shared state are affected.
- `[multi-site]`: The fix requires changes in multiple places within the same file or module (e.g., rename used in 3 functions in the same file).
- `[cross-module]`: The fix changes a public interface, shared type, or behavior depended on by other modules.

The leader preserves scope tags as-is during deduplication and severity calibration. When merging duplicate findings, adopt the **wider** scope (e.g., two `[single-site]` findings merged into one that affects multiple locations becomes `[multi-site]`).

### Finding Format Change

Applies to both reviewer finding format and report template in code-review-board's SKILL.md:

**Reviewer finding format:**
```markdown
# Critical / Major
- [R-XX-NNN] **Severity** | `file:line` | Description.
  > Impact: [scope-tag] affected scope description
  > Evidence: `code snippet`

# Minor
- [R-XX-NNN] **Minor** | `file:line` | Description.
  > Impact: [scope-tag] affected scope description
```

**Report template (with checkbox and perspective):**
```markdown
- [ ] [R-XX-NNN] **Severity** | `{perspective}` | `{file}:{line}` | {Description}
  > Impact: [scope-tag] affected scope description
  > Evidence: `{code snippet}`
  > Solution: {solution description — only if proposed}
```

## batch-fix Skill Design

### Trigger

`/batch-fix`, `batch fix`, `一括修正`

### Arguments

- `target` (optional): Path to a review Markdown file. If omitted, uses the most recent `*-review.md` in `docs/reviews/`.

### Examples

```
/batch-fix
/batch-fix docs/reviews/2026-03-13-api-review.md
```

### Architecture Note

batch-fix is a **coordinator skill** — it uses parallel Agent tool calls for dispatch but does not use the full Agent Team model (TeamCreate/SendMessage/WHITEBOARD.md). This is a lighter pattern appropriate for tasks where Agents work on independent files with no need for inter-Agent communication.

### Flow

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

### Step 1: PARSE

- If `target` argument provided, use that path
- Otherwise, glob `docs/reviews/*-review.md` and select the most recently modified file
- Parse the Markdown to extract findings matching ALL of:
  - Unchecked: line starts with `- [ ]` (skip already-fixed `- [x]` findings)
  - Impact tag: `> Impact:` line starts with `[single-site]`
- Extract per finding: ID, severity, perspective, file:line, description, Impact text, Evidence (if any), Solution (if any)

### Step 2-3: PRESENT and CONFIRM

Display extracted findings as a numbered list:

```
Found 8 single-site findings in docs/reviews/2026-03-13-api-review.md:

 1. [x] [R-RD-001] Minor | utils.ts:12 | Variable name unclear
 2. [x] [R-RD-005] Minor | utils.ts:34 | Redundant type assertion
 3. [x] [R-PF-003] Major | api.ts:89  | Array.find in hot loop
 ...

Enter numbers to deselect (e.g., "3,5"), or "ok" to proceed:
```

Default: all selected. User can deselect specific items by number.

### Step 4: DISPATCH

- Group selected findings by file path
- For each file group, launch an Agent with:
  - File path to modify
  - List of findings with full context per finding: ID, line number, description, Impact text, Evidence snippet (if any), Solution (if any)
  - Instruction: read the target file first, then apply fixes
  - Instruction: if Solution exists, follow it; otherwise, make the minimal fix implied by the description
  - Instruction: if the Evidence snippet does not match the current code at the specified line (indicating the code has changed since the review), SKIP that finding
  - Instruction: return a summary line per finding: `[R-XX-NNN]: description of change made` or `[R-XX-NNN]: SKIPPED — reason`
- All Agents launched in parallel via concurrent Agent tool calls

### Step 5: COLLECT

- Gather Agent responses
- Parse each response into per-finding results: success (with memo) or skipped (with reason)

### Step 6: UPDATE

For each successfully fixed finding, update the review Markdown:

```markdown
# Before
- [ ] [R-RD-001] **Minor** | `Readability` | `utils.ts:12` | Variable name unclear.
  > Impact: [single-site] この関数内でのみ使用される変数

# After
- [x] [R-RD-001] **Minor** | `Readability` | `utils.ts:12` | Variable name unclear.
  > Impact: [single-site] この関数内でのみ使用される変数
  <!-- fixed: renamed `x` to `userCount` -->
```

Skipped findings remain unchanged (`- [ ]`). Existing `> Solution:` lines are preserved as-is.

### Step 7: COMMIT

- If no source files were modified (all findings skipped), skip the commit entirely
- Stage all modified source files and the updated review Markdown
- Commit message format: `fix: batch-fix {N} single-site findings from {review-file-name}`
- Include `Co-Authored-By: Claude <noreply@anthropic.com>` line

### Step 8: REPORT

Display terminal summary:

```
## batch-fix Complete

Fixed: 6 | Skipped: 2
Review: docs/reviews/2026-03-13-api-review.md (updated)
Commit: abc1234

### Skipped
- [R-CR-002]: file not found (deleted since review)
- [R-AR-001]: line 45 already modified
```

If all findings were skipped, omit the Commit line.

### Error Handling

- **File not found**: Skip finding, report reason
- **Line already modified**: Agent compares Evidence snippet against current code; if mismatch, skip finding
- **Agent failure**: Skip all findings for that file, report the error
- **No `[single-site]` findings**: Display message and exit without changes
- **No unchecked findings**: Display message (all already fixed) and exit
- **Review file not found**: Display error and exit
- **All findings skipped**: Skip commit, report results only

## Known Constraints

- The default review file location (`docs/reviews/*-review.md`) is coupled to the code-review-board output path. If that changes, batch-fix's default must also be updated.
- Version bump in `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` is required when adding the new skill.
