---
name: deep-fix
description: >-
  Deep-fix complex multi-site/cross-module code review findings one at a time.
  Use for findings requiring design planning before implementation.
  Triggers: /deep-fix, deep fix, 個別修正
---

# deep-fix — Deep Fix Complex Review Findings

Address code-review-board findings with `[multi-site]` or `[cross-module]` scope one at a time. Parses the review Markdown, validates findings against current code, ranks candidates by dependency analysis, and delegates to brainstorming or Plan mode for design and implementation.

## When to Use

- The user wants to fix a complex finding from a code review report: `/deep-fix`, "deep fix", "個別修正"
- The finding requires changes across multiple locations (`[multi-site]`) or modules (`[cross-module]`)
- The fix needs design discussion or planning before implementation

## When NOT to Use

- Findings are `[single-site]` — use `/batch-fix` instead
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
6. APPROACH — User chooses brainstorming or Plan mode
7. EXECUTE  — Delegate to chosen approach, collect fix summary
8. VERIFY   — Check if source files were modified (HEAD or working tree)
9. UPDATE   — Mark finding as [x], insert fixed comment
10. COMMIT  — Commit review update (and source files if uncommitted)
11. REPORT  — Display summary with remaining count
```
