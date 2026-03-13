---
name: code-review-board
description: >-
  Multi-perspective code review via Agent Team.
  Use when performing comprehensive code review with parallel reviewer agents.
  Triggers: /code-review, review code, code review, コードレビュー, レビュー
---

# Code Review Board — Multi-Perspective Team Code Review

Perform comprehensive code review from 8 perspectives using parallel reviewer agents. Each agent writes findings to their own `findings/{perspective}.md` file, and the leader synthesizes results into a Markdown report with checklists for tracking fixes.

## When to Use

- The user requests a code review: `/code-review`, "review code", "code review", "コードレビュー", "レビュー"
- The user wants multi-perspective analysis of code quality

## When NOT to Use

- Quick, single-perspective feedback — use `requesting-code-review` instead
- The user only wants a diff review for a PR — use `requesting-code-review` instead

## Arguments

- `target` (required): File paths or directory paths to review (space-separated)
- `--spec <path>` (optional): Specification document file path for spec compliance checks
- `--perspectives <list>` (optional): Comma-separated list of perspectives to include or exclude. Prefix with `-` to exclude. Default: all applicable perspectives.

**Examples:**
```
/code-review src/api/
/code-review src/api/ --spec docs/plans/api-design.md
/code-review src/api/ --perspectives security,correctness,performance
/code-review src/api/ --perspectives -bevy-architect,-codex-reviewer
```

## Core Principles

1. **Review-centric** — The board revolves around a set of target files/directories. All findings reference specific file locations.
2. **Individual file model** — Each reviewer writes to their own `findings/{perspective}.md`. Leader reads all files during synthesize and generates a unified view. No shared WHITEBOARD.md.
3. **Leader-only SYNTHESIS.md** — Reviewers can read SYNTHESIS.md but never write to it.
4. **Append-only** — Reviewers add findings, never delete or modify existing entries.
5. **Two-pass workflow** — Reviewers analyze independently in parallel (pass 1), then respond to leader's cross-review summary (pass 2). Leader synthesizes all input.
6. **Conditional agents** — Bevy Architect agent is only spawned when `.rs` files are in the review target.
7. **Evidence-backed findings** — Critical and Major findings require concrete code evidence. Findings without evidence are downgraded.
8. **Explicit state management** — SYNTHESIS.md tracks `Status` and `Phase` for progress visibility, matching discussion-board patterns.

---

## Phase Model

```
setup → reviewing → cross-reviewing → synthesizing → reporting → completed
```

| Phase | Who Acts | What Happens |
|-------|----------|--------------|
| `setup` | Leader | Parse arguments, identify target files, create `docs/reviews/{review-id}/` directory with SYNTHESIS.md and `findings/` subdirectory, create team, spawn reviewers |
| `reviewing` | All reviewers | Each reviewer analyzes code from their perspective, writes findings to `findings/{perspective}.md`, sends structured completion report to leader. Leader displays progress to user after each report. |
| `cross-reviewing` | Leader + reviewers | Leader broadcasts findings summary. Each reviewer responds with duplicates found and missed issues from their perspective. |
| `synthesizing` | Leader only | Leader reads all `findings/*.md`, applies 3-stage deduplication, calibrates severity, computes scores, writes to SYNTHESIS.md |
| `reporting` | Leader only | Leader generates Markdown report to `docs/reviews/YYYY-MM-DD-{target}-review.md`, displays terminal summary, deletes `findings/` and SYNTHESIS.md |
| `completed` | Leader only | Sends shutdown requests to all reviewers, cleans up team |

### Transition Triggers

- `setup` → `reviewing`: All reviewers spawned and tasks assigned.
- `reviewing` → `cross-reviewing`: All reviewers have reported completion (or timed out after 5 minutes). Leader sends reminder after 4 minutes to unresponsive reviewers.
- `cross-reviewing` → `synthesizing`: All reviewers have responded to cross-review summary (or 2 minutes elapsed).
- `synthesizing` → `reporting`: SYNTHESIS.md is complete with scores and deduplicated findings.
- `reporting` → `completed`: Markdown report generated, intermediate files cleaned up.

---

## Team Composition

| Role | Agent Name | subagent_type | Condition |
|------|-----------|---------------|-----------|
| Leader | `review-lead` | (the invoking agent) | Always |
| Reviewer 1 | `readability` | general-purpose | Always |
| Reviewer 2 | `correctness` | general-purpose | Always |
| Reviewer 3 | `spec-compliance` | general-purpose | Always |
| Reviewer 4 | `architecture` | general-purpose | Always |
| Reviewer 5 | `bevy-architect` | general-purpose | Only when `.rs` files in target |
| Reviewer 6 | `security` | general-purpose | Always |
| Reviewer 7 | `performance` | general-purpose | Always |
| Reviewer 8 | `codex-reviewer` | general-purpose | Always |

---

## Review Directory Structure

Create at `docs/reviews/{review-id}/` where `{review-id}` is `YYYY-MM-DD-{target-name}`:

```
docs/reviews/{review-id}/
├── SYNTHESIS.md          (leader-only)
├── findings/
│   ├── readability.md
│   ├── correctness.md
│   ├── spec-compliance.md
│   ├── architecture.md
│   ├── bevy-architect.md  (only if .rs files)
│   ├── security.md
│   ├── performance.md
│   └── codex-reviewer.md
└── (intermediate files, cleaned up after report generation)
```

Ensure `docs/reviews/` is in `.gitignore`. Add if missing:
```
docs/reviews/*/findings/
docs/reviews/*/SYNTHESIS.md
```

### Individual Finding File Template

Each reviewer's `findings/{perspective}.md`:

```markdown
# {Perspective Name} Findings

> Reviewer: {agent-name}
> Target: {comma-separated file/directory paths}
> Spec: {spec file path, or "none"}

## Findings

```

Reviewers append findings using the Finding Format (see Entry ID System). No other structure needed — each reviewer owns their entire file.

**Note:** If Bevy Architect agent is not spawned (no `.rs` files), omit the `bevy-architect.md` file.

---

## SYNTHESIS.md Template

Create at `docs/reviews/{review-id}/SYNTHESIS.md`. This file is **leader-only**.

```markdown
# CODE REVIEW SYNTHESIS

> Status: setup
> Phase: setup
> Review ID: {review-id}
> Target: {comma-separated file/directory paths}
> Spec: {spec file path, or "none"}
> Active Perspectives: {comma-separated list of active perspectives}

---

## Perspective Scores

| Perspective | Score | Grade | Critical | Major | Minor | Info |
|-------------|-------|-------|----------|-------|-------|------|

## Overall Score

| Field | Value |
|-------|-------|
| Score | — |
| Grade | — |
| Total Findings | — |
| Critical | — |
| Major | — |
| Minor | — |
| Info | — |

## Deduplicated Findings

## Severity Calibration Log

## Cross-Review Notes

## Top Recommendations

## Review Notes
```

### Status Values

| Status | Meaning |
|--------|---------|
| `setup` | Initial state. Leader is creating files and spawning reviewers. |
| `reviewing` | Reviewers are analyzing code. Update with progress: `reviewing (3/8 completed)`. |
| `cross-reviewing` | Leader has broadcast findings summary. Reviewers responding with cross-review input. |
| `synthesizing` | Leader is reading all findings, deduplicating, and scoring. |
| `reporting` | Leader is generating the Markdown report and terminal summary. |
| `completed` | Review finished. Report generated, intermediate files cleaned up. |

Update `Status` and `Phase` at each transition. During `reviewing`, also update with progress: `reviewing (3/8 completed)`.

---

## Entry ID System

Format: `[R-{PERSPECTIVE}-{NNN}]`

| Code | Perspective |
|------|------------|
| RD | Readability |
| CR | Correctness & Reliability |
| SP | Spec Compliance & Testing |
| AR | Architecture |
| BV | Bevy Architecture |
| SC | Security |
| PF | Performance |
| CX | Codex Holistic Review |

### Severity Levels

| Level | Color | Description |
|-------|-------|------------|
| **Critical** | Red | Immediate fix required. Security vulnerabilities, data loss risk, panics. |
| **Major** | Yellow | Fix before release. Performance issues, significant design problems. |
| **Minor** | Blue | Improvement recommended but not urgent. Naming, comments, minor redundancy. |
| **Info** | Gray | Reference information, praise for good implementation. |

### Finding Format

For **Critical** and **Major** (Evidence required):
```markdown
- [R-XX-NNN] **Severity** | `file:line` | Description of the issue and its impact.
  > Evidence: `relevant code snippet (max 3 lines)`
```

For **Minor** and **Info** (Evidence optional):
```markdown
- [R-XX-NNN] **Severity** | `file:line` | Description of the issue and its impact.
```

**Evidence rule:** Critical/Major findings without an Evidence line are downgraded to Minor by the leader during severity calibration.

---

## Leader Workflow

```
 1. PARSE ARGS    → Parse the skill arguments:
                    - Extract target file/directory paths
                    - Extract --spec path (if provided)
                    - Extract --perspectives list (if provided)
                    - Resolve all paths to absolute paths
                    - Validate that target paths exist
                    - List all files in target directories (recursively)
                    - Determine if .rs files are present (for Bevy agent)
                    - Apply --perspectives filter to Team Composition table
                    - Generate review-id: YYYY-MM-DD-{target-name}

 2. CREATE FILES  → Create docs/reviews/{review-id}/ directory.
                    Create docs/reviews/{review-id}/findings/ subdirectory.
                    Write SYNTHESIS.md using template above.
                    Ensure docs/reviews/ entries are in .gitignore.

 3. CREATE TEAM   → TeamCreate with team_name "code-review".

 4. SPAWN         → Spawn reviewer agents using the Agent tool with team_name "code-review".
                    For each active reviewer (after --perspectives filtering), provide:
                    - Their perspective name and checklist (from Reviewer Responsibilities below)
                    - Their individual finding file path: docs/reviews/{review-id}/findings/{perspective}.md
                    - The list of target files to review
                    - The spec file path (for spec-compliance agent)
                    - Scope boundary rules
                    - Finding format instructions (including Evidence requirement for Critical/Major)
                    - Instruction: "Read the target files. Analyze from your perspective.
                      Write findings to your individual file at {finding-file-path}
                      using [R-XX-NNN] format. When done, send a structured completion
                      report to review-lead."

                    Skip bevy-architect if no .rs files in target.
                    Skip any perspectives excluded by --perspectives.

                    For codex-reviewer, additionally instruct:
                    - "Use the codex-review skill approach: build a Code Review prompt
                      with all target file contents, write it to a temp file, and run
                      `cat /tmp/codex-review-prompt.txt | codex exec`. Convert the Codex
                      response into [R-CX-NNN] finding format and write to your finding file."

                    Update SYNTHESIS.md: Status → "reviewing", Phase → "reviewing"

 5. WAIT + REPORT → Wait for completion reports from all reviewers.
                    After each completion report received:
                    a. Display progress to user: "{N}/{total} reviewers completed — {perspective}: {critical} Critical, {major} Major"
                    b. Update SYNTHESIS.md Status: "reviewing ({N}/{total} completed)"
                    After 4 minutes, send reminder to unresponsive reviewers.
                    After 5 minutes, skip remaining unresponsive reviewers.
                    For timed-out perspectives: send reminder at 4 min. If still
                    unresponsive at 5 min, leader writes a brief fallback review
                    (2-3 key concerns from the perspective's checklist) to the
                    timed-out perspective's finding file.

 6. CROSS-REVIEW  → Update SYNTHESIS.md: Phase → "cross-reviewing"
                    Read all findings/*.md files.
                    Compose a concise summary of all findings (grouped by file,
                    listing entry IDs and severity — no full descriptions).
                    Broadcast summary to all active reviewers with instruction:
                    "Review this summary. Reply with:
                     1. Duplicate findings you notice (cite both IDs)
                     2. Important issues from your perspective that were missed
                     Format: CROSS-REVIEW: duplicates=[ID1=ID2, ...], missed=[description, ...]"
                    Wait up to 2 minutes for responses.
                    Record cross-review notes in SYNTHESIS.md ## Cross-Review Notes.

 7. SYNTHESIZE    → Update SYNTHESIS.md: Phase → "synthesizing"
                    Read all findings/*.md files.

                    a. SEVERITY CALIBRATION:
                       - Check all Critical/Major findings for Evidence field
                       - Downgrade Critical/Major without Evidence to Minor
                       - Compare severity across perspectives for consistency
                       - Record adjustments in ## Severity Calibration Log:
                         "[R-XX-NNN] calibrated: Major→Minor, reason: no Evidence provided"

                    b. 3-STAGE DEDUPLICATION:
                       Stage 1 — Exact match: same file:line AND same severity → merge,
                                 keep the more detailed description
                       Stage 2 — Location overlap: file:line within ±5 lines AND same
                                 issue category → merge, adopt higher severity
                       Stage 3 — Semantic duplicate: different locations but same root
                                 cause (e.g., repeated unwrap() pattern) → group as
                                 representative finding + "N similar occurrences" note
                       Apply cross-review duplicate notes from step 6.

                    c. SCORING: For each perspective:
                       - Count deduplicated findings by severity
                       - Score 0-100: Start at 100
                         Critical: -20 per finding
                         Major: -10 per finding
                         Minor: -3 per finding
                         Info: 0 (no deduction)
                         Minimum score: 0
                       - Convert to letter grade:
                         97-100=A+, 93-96=A, 90-92=A-,
                         87-89=B+, 83-86=B, 80-82=B-,
                         77-79=C+, 73-76=C, 70-72=C-,
                         67-69=D+, 63-66=D, 60-62=D-,
                         0-59=F
                       Overall = simple average of active perspective scores
                       (exclude timed-out perspectives without fallback).

                    d. Write top 5 recommendations (highest severity first).
                    e. Populate SYNTHESIS.md tables.

 8. REPORT        → Update SYNTHESIS.md: Phase → "reporting"
                    Generate Markdown report using Markdown Report Template.
                    Save directly to docs/reviews/{review-id}-review.md (not inside the subdirectory).
                    Delete docs/reviews/{review-id}/findings/ directory.
                    Delete docs/reviews/{review-id}/SYNTHESIS.md.
                    Delete docs/reviews/{review-id}/ directory.
                    Display terminal summary to user (see Terminal Output Format).
                    Report file path to user.

 9. SHUTDOWN      → Send shutdown_request to all reviewers.
                    Delete team with TeamDelete.
                    Report completion to user with report file path.
```

---

## Reviewer Workflow

### All Reviewers (except Codex)

1. **Read** SYNTHESIS.md header to get target files and spec path.
2. **Read** the target files using Read, Grep, and Glob tools. Investigate thoroughly from your assigned perspective.
3. **Write** findings to your individual file at `findings/{perspective}.md`:
   - Use `[R-XX-NNN]` format with severity label.
   - Each finding must reference a specific `file:line` location.
   - Critical/Major findings MUST include an Evidence line with a code snippet (max 3 lines).
   - Focus on your perspective's checklist items — do not duplicate other perspectives' work.
4. **Report** completion to the leader via SendMessage using the structured completion report format.
5. **Cross-review** (when prompted): Read the leader's findings summary broadcast. Reply with duplicate findings and missed issues from your perspective.

### Codex Reviewer

1. **Read** the target files to understand the codebase.
2. **Build** a Code Review prompt following the `codex-review` skill pattern:
   ```
   Analyze the following code. Identify issues from these perspectives:
   - Bugs or logic errors
   - Unhandled edge cases
   - Security issues
   - Performance concerns
   Report each finding with: severity (Critical/Major/Minor/Info), file:line, and description.
   Files: {target file contents inlined}
   ```
3. **Run** Codex CLI via temp file + stdin (not as CLI argument — avoids shell length limits):
   ```bash
   cat <<'PROMPT_EOF' > /tmp/codex-review-prompt.txt
   <constructed_prompt>
   PROMPT_EOF
   cat /tmp/codex-review-prompt.txt | codex exec
   rm -f /tmp/codex-review-prompt.txt
   ```
4. **Convert** Codex response into `[R-CX-NNN]` finding format with Evidence where applicable.
5. **Write** converted findings to `findings/codex-reviewer.md`.
6. **Handle errors**: If `codex` CLI is not installed or fails, retry once. On second failure, write: `- [R-CX-001] **Info** | N/A | Codex review unavailable — codex CLI execution failed.`
6. **Report** completion to the leader via SendMessage using the structured completion report format.
7. **Cross-review** (when prompted): Same as other reviewers.

---

## Reviewer Responsibilities

### Scope Boundary Rules (include in ALL reviewer prompts)

- **Correctness vs Security:** Correctness = correctness under normal/trusted inputs. Security = robustness under adversarial inputs.
- **Readability vs Architecture:** Readability = local code comprehension. Architecture = system-level structure, boundaries, dependencies.
- **Architecture vs Performance:** Architecture = structural performance risks. Performance = runtime cost with concrete evidence.

### Readability Agent Checklist

- Function/variable names clearly express intent
- Code reads like natural language (method chains, clear conditionals)
- Function length (warn if >50 lines)
- Cognitive complexity / nesting depth
- Comment quality (redundant vs missing)
- Error message clarity and debuggability
- Magic numbers
- Dead code / confusing indirection
- TODO/FIXME quality and staleness

### Correctness & Reliability Agent Checklist

- Panic possibilities (`.unwrap()`, `.expect()`, array index access)
- Integer overflow, division by zero
- Unhandled edge cases (empty collections, None, error paths)
- Resource leaks (missing Drop impl, unclosed file handles)
- Logic errors (off-by-one, inverted conditions)
- Concurrency bugs (deadlocks, race conditions, lock ordering)
- Async correctness (cancellation, timeout, unawaited futures)
- `unsafe` block invariants
- Numeric conversion/precision issues (`as` casts, float edge cases)
- React hook pitfalls (stale closures, dependency array mistakes) — TS targets only

### Spec Compliance & Testing Agent Checklist

- Cross-reference spec requirements with code implementation
- Detect unimplemented spec items
- Detect implementations not in spec (scope creep)
- Terminology mismatches between spec and code
- Backward-compatibility checks (API behavior changes)
- Test coverage for behavior changes (added/updated?)
- Edge/error/concurrency case coverage in tests
- Test determinism and non-flakiness
- If no spec file provided, skip spec cross-reference (still check test quality)

### Architecture Agent Checklist

- Single Responsibility Principle violations
- Abstraction level consistency
- Dependency direction (upper layers depending on lower)
- Cyclic dependency detection
- Module cohesion and coupling
- DRY principle — but tolerate intentional duplication for clarity
- Testability seams (DI, trait boundaries, mockability)
- Unnecessary abstraction / premature generalization
- engine/core/ui/sdk boundary enforcement

### Bevy Architect Agent Checklist (only when .rs files in target)

- Bevy 0.18 API compliance
- Project's bevy-patterns.md rules compliance
- `try_insert` vs `insert` usage
- ApiReactor pattern correct usage
- SystemParam utilization
- System ordering / run conditions correctness
- Event lifecycle correctness (reader/writer usage)
- Query filter correctness (`Changed`, `Added`, etc.)
- Archetype churn risks from add/remove patterns

### Security Agent Checklist

- Injection vulnerabilities (SQL, command, path traversal)
- Hardcoded secrets (API keys, passwords)
- Input validation against adversarial inputs
- Unsafe deserialization
- Missing access controls
- Secret leakage in logs/error messages
- SSRF / path canonicalization checks
- Authentication vs authorization separation

### Performance Agent Checklist

- Unnecessary allocations (`.clone()` overuse, String vs &str)
- N+1 problems (queries/file I/O in loops)
- Unnecessary copies (large struct move vs reference)
- Inefficient algorithms (O(n^2) that could be O(n log n))
- Underutilized caching
- Lock contention and sync bottlenecks
- Bevy system frame-budget regression risks
- React re-render churn and memoization opportunities — TS targets only
- Startup/load-time regressions

### Codex Holistic Review Agent Checklist

- Build a Code Review prompt with all target file contents following the `codex-review` skill pattern
- Run via temp file + stdin: write prompt to `/tmp/codex-review-prompt.txt`, pipe to `codex exec`, clean up temp file
- Prompt Codex: "Analyze the following code. Identify issues: bugs, logic errors, unhandled edge cases, security issues, performance concerns. Report each finding with: severity (Critical/Major/Minor/Info), file:line, and description."
- Convert Codex response into `[R-CX-NNN]` finding format
- If `codex` CLI is not installed or fails, retry once. On second failure, write a single Info finding: "Codex review unavailable — codex CLI execution failed."

---

## Markdown Report Template

The leader generates a Markdown report file. The report structure:

```markdown
# Code Review Report

> Date: {YYYY-MM-DD}
> Target: `{target paths}`
> Spec: `{spec path or "none"}`

## Overall Score

**{letter grade}** ({score}/100)

| Metric | Count |
|--------|-------|
| Critical | {N} |
| Major | {N} |
| Minor | {N} |
| Info | {N} |

## Perspective Scores

| Perspective | Grade | Score | Critical | Major | Minor | Info |
|-------------|-------|-------|----------|-------|-------|------|
| {name} | {grade} | {score}/100 | {n} | {n} | {n} | {n} |

## File Summary

| File | Critical | Major | Minor | Info |
|------|----------|-------|-------|------|
| `{file path}` | {n} | {n} | {n} | {n} |

## Findings

### Critical

- [ ] [R-XX-NNN] **Critical** | `{perspective}` | `{file}:{line}` | {Description}
  > Evidence: `{code snippet}`

### Major

- [ ] [R-XX-NNN] **Major** | `{perspective}` | `{file}:{line}` | {Description}
  > Evidence: `{code snippet}`

### Minor

- [ ] [R-XX-NNN] **Minor** | `{perspective}` | `{file}:{line}` | {Description}

### Info

- [R-XX-NNN] **Info** | `{perspective}` | `{file}:{line}` | {Description}

## Top Recommendations

1. **[R-XX-NNN]** — {action description}
2. ...

## Calibration Log

- [R-XX-NNN] calibrated: {Original}→{New} — {reason}

---
*Generated by Code Review Board | {YYYY-MM-DD}*
```

### Report Format Notes

- Critical/Major/Minor findings use `- [ ]` checkboxes for fix tracking. Users mark fixes as complete by editing: `- [x] [R-CR-001] ...`
- Info findings use `- ` without checkbox (reference only, no fix needed)
- Findings grouped by severity (Critical first), within each group sorted by perspective
- Evidence shown as blockquote (`>`)
- Calibrated findings show their **final** (post-calibration) severity in the findings section; calibration details appear only in the Calibration Log
- File Summary table provides per-file severity counts

### Perspective Enrichment

Reviewer findings use the format `[R-XX-NNN] **Severity** | \`file:line\` | Description` (no perspective field). When generating the Markdown report, the leader adds the perspective name based on the entry ID prefix:

| Prefix | Perspective (full name) |
|--------|------------|
| RD | Readability |
| CR | Correctness & Reliability |
| SP | Spec Compliance & Testing |
| AR | Architecture |
| BV | Bevy Architecture |
| SC | Security |
| PF | Performance |
| CX | Codex Holistic Review |

The leader maps the prefix to add `` `{perspective}` `` to each finding line in the report.

---

## Terminal Output Format

After generating the Markdown report, the leader displays a summary to the terminal. Only Critical and Major findings are shown — Minor/Info are in the file.

```
## Code Review Complete — {grade} ({score}/100)

Critical: {N} | Major: {N} | Minor: {N} | Info: {N}

### Critical
- [R-XX-NNN] `{file}:{line}` — {Description}

### Major
- [R-XX-NNN] `{file}:{line}` — {Description}

Full report: docs/reviews/{review-id}-review.md
```

---

## Example: Reviewing a Speech Module

```
Target: crates/homunculus_api/src/speech/
Spec: docs/plans/2026-03-01-speech-design.md

=== SETUP PHASE ===

1. Leader parses arguments:
   - Target files: timeline.rs, mod.rs, types.rs (3 .rs files → spawn Bevy agent)
   - Spec: docs/plans/2026-03-01-speech-design.md
   - --perspectives: not specified (all active)
   - Review ID: 2026-03-01-speech

2. Leader creates docs/reviews/2026-03-01-speech/ directory:
   - docs/reviews/2026-03-01-speech/SYNTHESIS.md
   - docs/reviews/2026-03-01-speech/findings/ (empty directory)

3. Leader creates team "code-review", spawns 8 reviewer agents.
   Each reviewer writes to their own findings/{perspective}.md file.
   SYNTHESIS.md updated: Status → "reviewing", Phase → "reviewing"

=== REVIEWING PHASE ===

4. Reviewers work in parallel, each writing to their own file:

   readability completes (1/8):
   → Leader displays: "1/8 reviewers completed — Readability: 0 Critical, 1 Major, 2 Minor"

   correctness completes (2/8):
   → Leader displays: "2/8 reviewers completed — Correctness: 1 Critical, 1 Major"

   (reviewers continue completing, leader displays progress for each...)

   After 4 minutes, leader sends reminder to any unresponsive reviewers.
   All 8 complete within 5 minutes.

=== CROSS-REVIEW PHASE ===

5. Leader reads all findings/*.md, composes summary:
   "timeline.rs: [R-CR-001] Critical, [R-RD-001] Major, [R-PF-001] Major, [R-BV-001] Minor
    mod.rs: [R-CR-002] Major, [R-SC-001] Minor
    types.rs: [R-SP-001] Minor, [R-SP-002] Info"

   Broadcasts to all reviewers. Responses within 2 minutes:
   - correctness: "CROSS-REVIEW: duplicates=[R-CR-001=R-SC-001], missed=[]"
   - performance: "CROSS-REVIEW: duplicates=[], missed=[timeline.rs:45 allocates Vec in loop]"

=== SYNTHESIZING PHASE ===

6. Leader reads all findings/*.md files.

   Severity calibration:
   - [R-RD-002] Major "function length 60 lines" → calibrated: Major→Minor
     (reason: architecture rated 80-line function as Minor; applying consistent threshold)
   - [R-PF-002] Critical "clone in hot path" → no Evidence provided
     → calibrated: Critical→Minor (reason: no Evidence)

   3-stage deduplication:
   - Stage 1: [R-CR-001] and [R-SC-001] same file:line → merged (keep R-CR-001, Critical)
   - Stage 3: [R-CR-002] and cross-review missed finding → grouped as pattern

   Scoring:

   | Perspective | Score | Grade | Critical | Major | Minor | Info |
   |-------------|-------|-------|----------|-------|-------|------|
   | Readability | 87 | B+ | 0 | 1 | 1 | 0 |
   | Correctness | 70 | C- | 1 | 1 | 0 | 0 |
   | Spec Compliance | 94 | A | 0 | 0 | 2 | 1 |
   | Architecture | 90 | A- | 0 | 1 | 0 | 0 |
   | Bevy Architecture | 97 | A+ | 0 | 0 | 1 | 0 |
   | Security | 100 | A+ | 0 | 0 | 0 | 0 |
   | Performance | 87 | B+ | 0 | 1 | 1 | 0 |
   | Codex Holistic | 84 | B | 0 | 1 | 2 | 1 |

   Overall: 89 → B+

=== REPORTING PHASE ===

7. Leader generates docs/reviews/2026-03-01-speech-review.md
   with severity-grouped checklists and file summary.
   Deletes docs/reviews/2026-03-01-speech/findings/ and SYNTHESIS.md.
   Removes docs/reviews/2026-03-01-speech/ directory.
   Displays terminal summary with Critical/Major findings.

=== COMPLETED ===

8. Leader sends shutdown requests, deletes team.
   Reports to user: "Code review complete. Report: docs/reviews/2026-03-01-speech-review.md"
```

---

## Conflict Prevention Rules

| # | Rule | Rationale |
|---|------|-----------|
| 1 | Each reviewer writes only to their own `findings/{perspective}.md` file | Individual files eliminate all concurrent write conflicts — no shared file contention |
| 2 | SYNTHESIS.md is leader-only (reviewers read, never write) | Single writer eliminates shared-section conflicts |
| 3 | Append-only writes (no deletion/modification of existing entries) | Prevents overwrites when another agent has read stale content |
| 4 | Phase transitions are leader-controlled via broadcast/SendMessage | Clear phase boundaries prevent out-of-order writes |
| 5 | Cross-review responses via SendMessage, not file writes | Eliminates race conditions on cross-review notes |

---

## Error Handling

| Situation | Action |
|-----------|--------|
| Reviewer has not reported completion after 4 minutes | Leader sends one reminder via SendMessage |
| Reviewer has not reported completion after 5 minutes | Leader writes brief fallback review (2-3 key concerns from checklist) to the perspective's finding file, marks as "Leader fallback" in report |
| Codex CLI not installed or execution failure | Codex agent retries once. On second failure, writes Info finding "Codex unavailable" |
| Target file/directory does not exist | Validated during setup. Non-existent paths skipped with warning message to user |
| No spec file provided | Spec cross-reference portion skipped; test quality checks still run |
| docs/reviews/ directory does not exist | Created automatically during setup phase |
| Cross-review responses not received after 2 minutes | Leader proceeds with available responses |
| --perspectives specifies non-existent perspective | Warning to user, ignored. Valid perspectives proceed. |

---

## Reviewer Completion Report Format

Each reviewer sends this to the leader via SendMessage when done:

```
Findings: {N} total ({critical} critical, {major} major, {minor} minor, {info} info)
Most critical: [R-XX-NNN] — {brief description}
Assessment: {one-sentence overall assessment from this perspective}
Files reviewed: {N}
Processing time: {approximate duration}
```

**Note:** Severity counts in completion reports are self-reported and used for progress display only. Official scoring uses the leader's calibrated severity during synthesize.
