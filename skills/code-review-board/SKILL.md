---
name: code-review-board
description: >-
  Multi-perspective code review via Agent Team.
  Use when performing comprehensive code review with parallel reviewer agents.
  Triggers: /code-review, review code, code review, コードレビュー, レビュー
---

# Code Review Board — Multi-Perspective Team Code Review

Perform comprehensive code review from 7 perspectives using parallel reviewer agents. Each agent writes findings to their own `findings/{perspective}.md` file, and the leader synthesizes results into a Markdown report with checklists for tracking fixes.

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
- `--rounds <N>` (optional): Number of debate rounds. Default: 2. Set to 0 to skip debate phase entirely.

**Examples:**
```
/code-review src/api/
/code-review src/api/ --spec docs/plans/api-design.md
/code-review src/api/ --perspectives security,correctness,performance
/code-review src/api/ --perspectives -codex-reviewer
/code-review src/api/ --rounds 3
/code-review src/api/ --rounds 0
```

## Core Principles

1. **Review-centric** — The board revolves around a set of target files/directories. All findings reference specific file locations.
2. **Individual file model + WHITEBOARD.md** — Each reviewer writes findings to their own `findings/{perspective}.md`. For debate and solutions, reviewers write to per-member `### {perspective}` subsections in a shared WHITEBOARD.md. Leader reads all files during synthesize and generates a unified view.
3. **Leader-only SYNTHESIS.md** — Reviewers can read SYNTHESIS.md but never write to it.
4. **Append-only** — Reviewers add findings, never delete or modify existing entries.
5. **Multi-pass workflow** — Reviewers analyze independently in parallel (pass 1), debate findings validity across N rounds (pass 2), then propose solutions (pass 3). Leader synthesizes all input.
6. **Evidence-backed findings** — Critical and Major findings require concrete code evidence. Findings without evidence are downgraded.
7. **Explicit state management** — SYNTHESIS.md tracks `Status` and `Phase` for progress visibility, matching discussion-board patterns.

---

## Phase Model

```
setup → reviewing → debating (N rounds) → resolving → synthesizing → reporting → completed
```

| Phase | Who Acts | What Happens |
|-------|----------|--------------|
| `setup` | Leader | Parse arguments (including `--rounds`), identify target files, create `docs/reviews/{review-id}/` directory with SYNTHESIS.md, WHITEBOARD.md, and `findings/` subdirectory, create team, spawn reviewers |
| `reviewing` | All reviewers | Each reviewer analyzes code from their perspective, writes findings to `findings/{perspective}.md`, sends structured completion report to leader. Leader displays progress to user after each report. |
| `debating` | All reviewers | Reviewers write reactions to other perspectives' findings in WHITEBOARD.md per-member write zones. Multiple rounds (default 2, configurable via `--rounds`). Leader manages round transitions. |
| `resolving` | All reviewers | Each reviewer proposes solutions for confirmed findings in WHITEBOARD.md `## Solutions` section. Single pass. |
| `synthesizing` | Leader only | Leader reads all `findings/*.md` and WHITEBOARD.md, applies debate tally, calibrates severity, deduplicates, consolidates solutions, computes scores, writes to SYNTHESIS.md |
| `reporting` | Leader only | Leader generates Markdown report to `docs/reviews/YYYY-MM-DD-{target}-review.md` (with Solution lines and Debate Summary), displays terminal summary, deletes intermediate files |
| `completed` | Leader only | Sends shutdown requests to all reviewers, cleans up team |

### Transition Triggers

- `setup` → `reviewing`: All reviewers spawned and tasks assigned.
- `reviewing` → `debating`: All reviewers have reported completion (or timed out after 5 minutes). Leader sends reminder after 4 minutes to unresponsive reviewers.
- `debating` → next round or `resolving`: Each round completes when all reviewers report (or timeout at 3 min, reminder at 2 min). After final round (or early termination), proceed to `resolving`.
- `resolving` → `synthesizing`: All reviewers have reported solution proposals (or timeout at 3 min, reminder at 2 min).
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
| Reviewer 5 | `security` | general-purpose | Always |
| Reviewer 6 | `performance` | general-purpose | Always |
| Reviewer 7 | `codex-reviewer` | general-purpose | Always |

---

## Review Directory Structure

Create at `docs/reviews/{review-id}/` where `{review-id}` is `YYYY-MM-DD-{target-name}`:

```
docs/reviews/{review-id}/
├── SYNTHESIS.md          (leader-only)
├── WHITEBOARD.md         (per-member write zones)
├── findings/
│   ├── readability.md
│   ├── correctness.md
│   ├── spec-compliance.md
│   ├── architecture.md
│   ├── security.md
│   ├── performance.md
│   └── codex-reviewer.md
└── (intermediate files, cleaned up after report generation)
```

Ensure `docs/reviews/` is in `.gitignore`. Add if missing:
```
docs/reviews/*/findings/
docs/reviews/*/SYNTHESIS.md
docs/reviews/*/WHITEBOARD.md
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

### WHITEBOARD.md Template

WHITEBOARD.md uses per-member write zones. Each reviewer writes only within their own `### {perspective}` subsection under `## Debate` and `## Solutions` sections. Reviewers add `#### Round 1`, `#### Round 2` headers within their own `### {perspective}` subsection. The leader creates this file during setup with sections for all active perspectives (after `--perspectives` filtering).

```markdown
# WHITEBOARD — {review-id}
> Target: {target paths}
> Rounds: {N}

## Findings Summary

> Leader populates this section with a summary of all findings after the reviewing phase.

## Debate

### readability

### correctness

### spec-compliance

### architecture

### security

### performance

### codex-reviewer

## Solutions

### readability

### correctness

### spec-compliance

### architecture

### security

### performance

### codex-reviewer
```

**Timeout differences:** Reviewing phase uses 5-minute timeout with 4-minute reminder. Debating and resolving phases use 3-minute timeout with 2-minute reminder (shorter because reviewers are reacting to known findings, not performing fresh analysis).

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

| Perspective | Score | Grade | Critical | Major | Minor |
|-------------|-------|-------|----------|-------|-------|

## Overall Score

| Field | Value |
|-------|-------|
| Score | — |
| Grade | — |
| Total Findings | — |
| Critical | — |
| Major | — |
| Minor | — |

## Deduplicated Findings

## Severity Calibration Log

## Debate Tally

| Finding | Agree | Disagree | Revise | Result |
|---------|-------|----------|--------|--------|

## Top Recommendations

## Review Notes
```

### Status Values

| Status | Meaning |
|--------|---------|
| `setup` | Initial state. Leader is creating files and spawning reviewers. |
| `reviewing` | Reviewers are analyzing code. Update with progress: `reviewing (3/7 completed)`. |
| `debating` | Reviewers are debating findings validity. Update with round: `debating (round 1/2, 4/7 completed)`. |
| `resolving` | Reviewers are proposing solutions for confirmed findings. |
| `synthesizing` | Leader is reading all findings, applying debate tally, deduplicating, and scoring. |
| `reporting` | Leader is generating the Markdown report and terminal summary. |
| `completed` | Review finished. Report generated, intermediate files cleaned up. |

Update `Status` and `Phase` at each transition. During `reviewing`, update with progress: `reviewing (3/7 completed)`. During `debating`, update with round and progress: `debating (round 1/2, 4/7 completed)`.

---

## Entry ID System

Format: `[R-{PERSPECTIVE}-{NNN}]`

| Code | Perspective |
|------|------------|
| RD | Readability |
| CR | Correctness & Reliability |
| SP | Spec Compliance & Testing |
| AR | Architecture |
| SC | Security |
| PF | Performance |
| CX | Codex Holistic Review |

### Severity Levels

| Level | Color | Description |
|-------|-------|------------|
| **Critical** | Red | Immediate fix required. Security vulnerabilities, data loss risk, crashes. |
| **Major** | Yellow | Fix before release. Performance issues, significant design problems. |
| **Minor** | Blue | Improvement recommended but not urgent. Naming, comments, minor redundancy. |

### Finding Format

For **Critical** and **Major** (Evidence required):
```markdown
- [R-XX-NNN] **Severity** | `file:line` | Description of the issue.
  > Impact: {affected scope}
  > Evidence: `relevant code snippet (max 3 lines)`
```

For **Minor** (Evidence optional):
```markdown
- [R-XX-NNN] **Minor** | `file:line` | Description of the issue.
  > Impact: {affected scope}
```

**Evidence rule:** Critical/Major findings without an Evidence line are downgraded to Minor by the leader during severity calibration.

### Debate Entry Format

Format: `[D-{XX}-R{round}-{NNN}]`

- `{XX}` — Perspective code of the reviewer writing the debate entry (not the finding author)
- `R{round}` — Debate round number (R1, R2, etc.)
- `{NNN}` — Sequential number within the reviewer's debate entries for that round

Each debate entry must include a label: **agree**, **disagree**, or **revise**, followed by a reference to the finding being discussed.

```markdown
- [D-CR-R1-001] **agree** refs=[R-SC-001] | The null dereference is a genuine crash risk. Our correctness analysis confirms this path is reachable.
- [D-PF-R1-001] **disagree** refs=[R-CR-002] | The allocation is on a cold path called once at startup. Not a real performance concern.
- [D-AR-R1-001] **revise** refs=[R-RD-003] | Agree the function is too long, but the root cause is mixing validation and transformation — should be split by responsibility, not just length.
```

**Debate entry rules:**
- Reviewers may only react to findings from **other** perspectives (not their own).
- Each debate entry must reference exactly one finding ID.
- Debate entries are append-only within the reviewer's write zone.
- Reviewers should prioritize reacting to Critical and Major findings first.

### Debate Tally Rules

The leader tallies debate entries during synthesis to determine finding outcomes.

- **Tally scope:** Count agree, disagree, and revise entries across all rounds for each finding.
- **Minimum threshold:** A finding needs reactions from at least 2 different reviewers (not counting the author) for the tally to apply. Findings below threshold keep their original severity.
- **Finding author rule:** The finding author's perspective is excluded from the tally (they cannot vote on their own finding).
- **Revise handling:** `revise` counts as `disagree` for majority calculation (but the proposed revision is recorded separately for severity calibration).
- **Tally interpretation:**
  - **Agree majority** = agree count > (disagree + revise) count among responding reviewers → severity maintained
  - **Disagree majority** = (disagree + revise) count > agree count among responding reviewers → severity adjustment or exclusion considered during synthesizing
  - **Tie** = treated as "no consensus" → finding passes through unchanged
- **No consensus** (tie or fewer than 2 reactions): Finding passes through at original severity. No debate-based calibration applied.

### Debate Result Integration

After tallying, the leader applies results during synthesis:

- **Consensus (agree majority)** → Severity maintained
- **Dispute (disagree majority)** → Severity adjustment or finding exclusion considered during synthesizing
- **Revision proposed (revise entries)** → Severity change recorded in calibration log with the proposed revision as rationale
- **No consensus** → Finding passes through unchanged

### Early Termination

If all debate entries in a round are **agree** (no disagree or revise entries from any reviewer), the leader may skip remaining rounds and proceed directly to `resolving`. This avoids redundant rounds when reviewers are in full agreement.

### Solution Entry Format

Format: `[S-{XX}-{NNN}]`

- `{XX}` — Perspective code of the reviewer proposing the solution
- `{NNN}` — Sequential number within the reviewer's solution entries

Each solution entry must reference one or more finding IDs it addresses.

```markdown
- [S-CR-001] refs=[R-SC-001], [R-CR-002] | Add null check at `api.ts:45` before accessing `user.role`. Wrap in try-catch for the downstream call at `api.ts:52`.
  > Example: `if (!user?.role) throw new AuthError('missing role');`
- [S-AR-001] refs=[R-RD-003] | Extract validation logic into `validateRequest()` and transformation into `transformPayload()`. Reduces function from 80 lines to ~30 each.
```

**Solution entry rules:**
- Each solution must reference at least one finding ID.
- Solutions may reference findings from any perspective (including the reviewer's own).
- Multiple reviewers may propose different solutions for the same finding — the leader consolidates during synthesis.
- Solutions are append-only within the reviewer's write zone.

### Entry ID Summary

| Type | Format | File | Phase |
|------|--------|------|-------|
| Finding | `[R-{XX}-{NNN}]` | `findings/{perspective}.md` | reviewing |
| Debate | `[D-{XX}-R{round}-{NNN}]` | WHITEBOARD.md | debating |
| Solution | `[S-{XX}-{NNN}]` | WHITEBOARD.md | resolving |

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
                    - Apply --perspectives filter to Team Composition table
                    - Extract --rounds N (default: 2)
                    - Generate review-id: YYYY-MM-DD-{target-name}

 2. CREATE FILES  → Create docs/reviews/{review-id}/ directory.
                    Create docs/reviews/{review-id}/findings/ subdirectory.
                    Write SYNTHESIS.md using template above.
                    Create docs/reviews/{review-id}/WHITEBOARD.md using WHITEBOARD.md template.
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

 6. DEBATE        → Update SYNTHESIS.md: Phase → "debating"
                    a. Read all findings/*.md files.
                    b. Compose findings summary (finding ID, severity, file:line,
                       brief description — grouped by file).
                    c. Write findings summary to WHITEBOARD.md ## Findings Summary.
                    d. Broadcast to all reviewers:
                       "DEBATE ROUND 1/{max_rounds}: Review the Findings Summary in
                        WHITEBOARD.md. For each finding from other perspectives,
                        write your reaction in your ### {perspective} section under
                        ## Debate. Use format: [D-{XX}-R1-{NNN}] **agree|disagree|revise**
                        refs=[R-XX-NNN] | reason. Send completion report when done."
                    e. Wait for completion reports (reminder at 2 min, timeout at 3 min).
                    f. Update SYNTHESIS.md Status: "debating (round 1/{max_rounds})"

                    For round 2+:
                    g. Read all ## Debate sections from WHITEBOARD.md.
                    h. Compose debate summary for the previous round (per-finding
                       tally of agree/disagree/revise with key arguments).
                    i. Broadcast to all reviewers:
                       "DEBATE ROUND {N}/{max_rounds}: Previous round summary:
                        {debate_summary}. Continue debating in your ### {perspective}
                        section. Add #### Round {N} header, then your entries.
                        Send completion report when done."
                    j. Wait for completion reports (reminder at 2 min, timeout at 3 min).
                    k. Update SYNTHESIS.md Status: "debating (round {N}/{max_rounds})"

                    After all rounds (or early termination):
                    l. Tally debate results per finding using Debate Tally Rules.
                    m. Record tally results in SYNTHESIS.md ## Debate Tally.

 7. RESOLVE       → Update SYNTHESIS.md: Phase → "resolving"
                    a. Apply debate tally to findings: exclude findings with
                       disagree majority (record in calibration log), note severity
                       revision proposals.
                    b. Compose confirmed findings list (finding ID, adjusted severity,
                       file:line, brief description).
                    c. Broadcast to all reviewers:
                       "RESOLVE: Confirmed findings list below. Propose solutions
                        for findings relevant to your expertise. Write to your
                        ### {perspective} section under ## Solutions in WHITEBOARD.md.
                        Format: [S-{XX}-{NNN}] refs=[R-XX-NNN] | solution description.
                        Send completion report when done.
                        Confirmed findings: {confirmed_findings_list}"
                    d. Wait for completion reports (reminder at 2 min, timeout at 3 min).

 8. SYNTHESIZE    → Update SYNTHESIS.md: Phase → "synthesizing"
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
                                 cause (e.g., repeated missing-null-check pattern) → group as
                                 representative finding + "N similar occurrences" note
                       Apply debate tally duplicate notes from step 6.

                    c. SCORING: For each perspective:
                       - Count deduplicated findings by severity
                       - Score 0-100: Start at 100
                         Critical: -20 per finding
                         Major: -10 per finding
                         Minor: -3 per finding
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

                    Additional inputs: WHITEBOARD.md ## Debate and ## Solutions.
                    a. Severity calibration now includes debate evidence:
                       - Debate disagree majority → downgrade or exclude
                       - Debate revise proposals → severity change with rationale
                       - Existing Evidence-based downgrading still applies
                    b. Solution consolidation:
                       - For each finding, collect all [S-XX-NNN] entries that
                         reference it via refs=[]
                       - If multiple solutions exist, select the most actionable one
                       - Store selected solution text per finding for report generation

 9. REPORT        → Update SYNTHESIS.md: Phase → "reporting"
                    Generate Markdown report using Markdown Report Template.
                    Save directly to docs/reviews/{review-id}-review.md (not inside the subdirectory).
                    Delete docs/reviews/{review-id}/findings/ directory.
                    Delete docs/reviews/{review-id}/SYNTHESIS.md.
                    Delete docs/reviews/{review-id}/ directory.
                    Display terminal summary to user (see Terminal Output Format).
                    Report file path to user.

                    Additional content:
                    a. Add > Solution: line to findings that have a selected solution
                       (after Evidence line, or after description if no Evidence)
                    b. Add ## Debate Summary section before ## Calibration Log
                       with per-finding tally and outcome
                    c. Delete WHITEBOARD.md along with findings/ and SYNTHESIS.md

10. SHUTDOWN      → Send shutdown_request to all reviewers.
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
   - Every finding MUST include an `> Impact:` line describing the affected scope.
   - Critical/Major findings MUST include an Evidence line with a code snippet (max 3 lines).
   - Focus on your perspective's checklist items — do not duplicate other perspectives' work.
4. **Report** completion to the leader via SendMessage using the structured completion report format.
5. **Debate** (when prompted): Read the Findings Summary in WHITEBOARD.md. For each finding from other perspectives, write reactions in own `### {perspective}` section under `## Debate`. Use `[D-{XX}-R{round}-{NNN}]` format with `agree`/`disagree`/`revise` labels. Send completion report when done. Repeat for each debate round.
6. **Resolve** (when prompted): Read the confirmed findings list from leader's broadcast. Propose solutions for findings relevant to own expertise. Write to own `### {perspective}` section under `## Solutions`. Use `[S-{XX}-{NNN}]` format. Send completion report when done.

### Codex Reviewer

1. **Read** the target files to understand the codebase.
2. **Build** a Code Review prompt following the `codex-review` skill pattern:
   ```
   Analyze the following code. Identify issues from these perspectives:
   - Bugs or logic errors
   - Unhandled edge cases
   - Security issues
   - Performance concerns
   Report each finding with: severity (Critical/Major/Minor), file:line, and description.
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
6. **Handle errors**: If `codex` CLI is not installed or fails, retry once. On second failure, write: `- [R-CX-001] **Minor** | N/A | Codex review unavailable — codex CLI execution failed.`
6. **Report** completion to the leader via SendMessage using the structured completion report format.
7. **Debate** (when prompted): Same as other reviewers.
8. **Resolve** (when prompted): Same as other reviewers.

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

- Crash / abort possibilities (unhandled null, unchecked access, out-of-bounds access)
- Integer overflow, division by zero
- Unhandled edge cases (empty collections, null/nil/None, error paths)
- Resource leaks (unclosed handles, missing cleanup/dispose)
- Logic errors (off-by-one, inverted conditions)
- Concurrency bugs (deadlocks, race conditions, lock ordering)
- Async correctness (cancellation, timeout, unawaited futures/promises)
- Unsafe / FFI boundary invariants
- Numeric conversion/precision issues (implicit casts, float edge cases)

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
- Module/layer boundary enforcement

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

- Unnecessary allocations (redundant copies, string duplication, boxing)
- N+1 problems (queries/file I/O in loops)
- Unnecessary copies (large object copy vs reference/pointer)
- Inefficient algorithms (O(n^2) that could be O(n log n))
- Underutilized caching
- Lock contention and sync bottlenecks
- Unnecessary re-renders / recomputations in UI frameworks
- Startup/load-time regressions

### Codex Holistic Review Agent Checklist

- Build a Code Review prompt with all target file contents following the `codex-review` skill pattern
- Run via temp file + stdin: write prompt to `/tmp/codex-review-prompt.txt`, pipe to `codex exec`, clean up temp file
- Prompt Codex: "Analyze the following code. Identify issues: bugs, logic errors, unhandled edge cases, security issues, performance concerns. Report each finding with: severity (Critical/Major/Minor), file:line, and description."
- Convert Codex response into `[R-CX-NNN]` finding format
- If `codex` CLI is not installed or fails, retry once. On second failure, write a single Minor finding: "Codex review unavailable — codex CLI execution failed."

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

## Perspective Scores

| Perspective | Grade | Score | Critical | Major | Minor |
|-------------|-------|-------|----------|-------|-------|
| {name} | {grade} | {score}/100 | {n} | {n} | {n} |

## File Summary

| File | Critical | Major | Minor |
|------|----------|-------|-------|
| `{file path}` | {n} | {n} | {n} |

## Findings

### Critical

- [ ] [R-XX-NNN] **Critical** | `{perspective}` | `{file}:{line}` | {Description}
  > Impact: {affected scope}
  > Evidence: `{code snippet}`
  > Solution: {solution description — only if proposed}

### Major

- [ ] [R-XX-NNN] **Major** | `{perspective}` | `{file}:{line}` | {Description}
  > Impact: {affected scope}
  > Evidence: `{code snippet}`
  > Solution: {solution description — only if proposed}

### Minor

- [ ] [R-XX-NNN] **Minor** | `{perspective}` | `{file}:{line}` | {Description}
  > Impact: {affected scope}

## Top Recommendations

1. **[R-XX-NNN]** — {action description}
2. ...

## Debate Summary

- [R-XX-NNN] **{Severity}** — {Consensus/Dispute/Excluded} ({N} agree, {N} disagree). {Outcome description}.

## Calibration Log

- [R-XX-NNN] calibrated: {Original}→{New} — {reason}

---
*Generated by Code Review Board | {YYYY-MM-DD}*
```

### Report Format Notes

- All findings use `- [ ]` checkboxes for fix tracking. Users mark fixes as complete by editing: `- [x] [R-CR-001] ...`
- Findings grouped by severity (Critical first), within each group sorted by perspective
- Evidence shown as blockquote (`>`)
- Calibrated findings show their **final** (post-calibration) severity in the findings section; calibration details appear only in the Calibration Log
- File Summary table provides per-file severity counts
- `> Solution:` line appears after Evidence (or after description if no Evidence). Only present when a solution was proposed — no forced fill. Code examples within Solution are optional.
- Debate Summary section shows per-finding tally and outcome, providing transparency on severity changes and finding exclusions

### Perspective Enrichment

Reviewer findings use the format `[R-XX-NNN] **Severity** | \`file:line\` | Description` (no perspective field). When generating the Markdown report, the leader adds the perspective name based on the entry ID prefix:

| Prefix | Perspective (full name) |
|--------|------------|
| RD | Readability |
| CR | Correctness & Reliability |
| SP | Spec Compliance & Testing |
| AR | Architecture |
| SC | Security |
| PF | Performance |
| CX | Codex Holistic Review |

The leader maps the prefix to add `` `{perspective}` `` to each finding line in the report.

---

## Terminal Output Format

After generating the Markdown report, the leader displays a summary to the terminal. Only Critical and Major findings are shown — Minor are in the file.

```
## Code Review Complete — {grade} ({score}/100)

Critical: {N} | Major: {N} | Minor: {N}

### Critical
- [R-XX-NNN] `{file}:{line}` — {Description}

### Major
- [R-XX-NNN] `{file}:{line}` — {Description}

Full report: docs/reviews/{review-id}-review.md
```

---

## Example: Reviewing an API Module

```
Target: src/api/
Spec: docs/plans/api-design.md
Rounds: 2 (default)

=== SETUP PHASE ===

1. Leader parses arguments:
   - Target files: routes.ts, middleware.ts, types.ts
   - Spec: docs/plans/api-design.md
   - --perspectives: not specified (all active)
   - --rounds: 2 (default)
   - Review ID: 2026-03-01-api

2. Leader creates docs/reviews/2026-03-01-api/ directory:
   - docs/reviews/2026-03-01-api/SYNTHESIS.md
   - docs/reviews/2026-03-01-api/WHITEBOARD.md
   - docs/reviews/2026-03-01-api/findings/ (empty directory)

3. Leader creates team "code-review", spawns 7 reviewer agents.
   Each reviewer writes to their own findings/{perspective}.md file.
   SYNTHESIS.md updated: Status → "reviewing", Phase → "reviewing"

=== REVIEWING PHASE ===

4. Reviewers work in parallel, each writing to their own file:

   readability completes (1/7):
   → Leader displays: "1/7 reviewers completed — Readability: 0 Critical, 1 Major, 2 Minor"

   correctness completes (2/7):
   → Leader displays: "2/7 reviewers completed — Correctness: 1 Critical, 1 Major"

   (reviewers continue completing, leader displays progress for each...)

   After 4 minutes, leader sends reminder to any unresponsive reviewers.
   All 7 complete within 5 minutes.

=== DEBATING PHASE (Round 1/2) ===

5. Leader reads all findings/*.md, composes findings summary:
   "routes.ts: [R-CR-001] Critical, [R-RD-001] Major, [R-PF-001] Major
    middleware.ts: [R-CR-002] Major, [R-SC-001] Minor
    types.ts: [R-SP-001] Minor"

   Writes summary to WHITEBOARD.md ## Findings Summary.
   Broadcasts debate round 1 instructions to all reviewers.

   Reviewers write reactions in WHITEBOARD.md ## Debate > ### {perspective}:
   - performance: [D-PF-R1-001] **disagree** refs=[R-CR-001] | Not Critical — input is already validated upstream.
   - security: [D-SC-R1-001] **agree** refs=[R-CR-001] | Confirmed — validation gap exists.
   - architecture: [D-AR-R1-001] **revise** refs=[R-PF-001] | Should be Minor — not a hot path.
   - readability: [D-RD-R1-001] **agree** refs=[R-CR-002] | Confirmed — error handling is unclear.

=== DEBATING PHASE (Round 2/2) ===

6. Leader broadcasts round 1 summary:
   "[R-CR-001] 4 agree, 1 disagree, 0 revise — key argument: validation gap confirmed by security
    [R-PF-001] 1 agree, 0 disagree, 3 revise — key argument: not a hot path"

   Reviewers continue debate in round 2:
   - performance: [D-PF-R2-001] **agree** refs=[R-CR-001] | Reconsidered — security's point is valid.
   - correctness: [D-CR-R2-001] **revise** refs=[R-PF-001] | Agree with Minor.

   Leader tallies final results:
   - [R-CR-001] 6 agree, 0 disagree → maintained as Critical
   - [R-PF-001] 1 agree, 0 disagree, 4 revise → severity revision to Minor
   - [R-RD-003] 1 agree, 4 disagree → excluded (style preference)

   Records tally in SYNTHESIS.md ## Debate Tally.

=== RESOLVING PHASE ===

7. Leader broadcasts confirmed findings list (excluded findings removed, severity adjusted).
   Reviewers propose solutions in WHITEBOARD.md ## Solutions > ### {perspective}:

   - correctness: [S-CR-001] refs=[R-CR-001] | Add null guard with early return.
     > Example: `if (!user?.name) return defaultResponse;`
   - security: [S-SC-001] refs=[R-CR-001] | Validate input schema at API boundary.
   - performance: [S-PF-001] refs=[R-PF-001] | Cache the computed value outside the loop.

=== SYNTHESIZING PHASE ===

8. Leader reads all findings/*.md and WHITEBOARD.md.

   Severity calibration (with debate evidence):
   - [R-PF-001] Major → Minor (debate: 4 revise, not a hot path)
   - [R-PF-002] Critical "redundant copy in hot path" → no Evidence provided
     → calibrated: Critical→Minor (reason: no Evidence)
   - [R-RD-003] excluded (debate: 4 disagree, style preference)

   Solution consolidation:
   - [R-CR-001] has 2 solution proposals → selected: [S-CR-001] (most actionable)
   - [R-PF-001] has 1 solution proposal → selected: [S-PF-001]

   3-stage deduplication:
   - Stage 1: [R-CR-001] and [R-SC-001] same file:line → merged (keep R-CR-001, Critical)

   Scoring:

   | Perspective | Score | Grade | Critical | Major | Minor |
   |-------------|-------|-------|----------|-------|-------|
   | Readability | 90 | A- | 0 | 1 | 0 |
   | Correctness | 70 | C- | 1 | 1 | 0 |
   | Spec Compliance | 94 | A | 0 | 0 | 2 |
   | Architecture | 90 | A- | 0 | 1 | 0 |
   | Security | 100 | A+ | 0 | 0 | 0 |
   | Performance | 94 | A | 0 | 0 | 2 |
   | Codex Holistic | 84 | B | 0 | 1 | 2 |

   Overall: 89 → B+

=== REPORTING PHASE ===

9. Leader generates docs/reviews/2026-03-01-api-review.md
   with severity-grouped checklists, Solution lines, Debate Summary, and file summary.
   Sample finding in report:
   - [ ] [R-CR-001] **Critical** | `Correctness` | `routes.ts:45` | Null check missing
     > Impact: All API routes using user.name — runtime crash on anonymous requests
     > Evidence: `const name = user.name.toLowerCase()`
     > Solution: Add null guard with early return. `if (!user?.name) return defaultResponse;`

   Deletes docs/reviews/2026-03-01-api/findings/, WHITEBOARD.md, and SYNTHESIS.md.
   Removes docs/reviews/2026-03-01-api/ directory.
   Displays terminal summary with Critical/Major findings.

=== COMPLETED ===

10. Leader sends shutdown requests, deletes team.
    Reports to user: "Code review complete. Report: docs/reviews/2026-03-01-api-review.md"
```

---

## Conflict Prevention Rules

The old rule #5 ('Cross-review responses via SendMessage, not file writes') is removed — debate reactions are now file writes to WHITEBOARD.md per-member write zones.

| # | Rule | Rationale |
|---|------|-----------|
| 1 | Each reviewer writes only to their own `findings/{perspective}.md` file | Individual files eliminate concurrent write conflicts during reviewing |
| 2 | Each reviewer writes only to their own `### {perspective}` subsection in WHITEBOARD.md | Per-member write zones prevent conflicts during debating/resolving |
| 3 | SYNTHESIS.md is leader-only (reviewers read, never write) | Single writer eliminates conflicts |
| 4 | Append-only writes (no deletion/modification of existing entries) | Prevents overwrites from stale reads |
| 5 | Phase transitions are leader-controlled via broadcast | Clear boundaries prevent out-of-order writes |
| 6 | `## Findings Summary` in WHITEBOARD.md is leader-only | Single writer for summary section |

---

## Error Handling

| Situation | Action |
|-----------|--------|
| Reviewer has not reported completion after 4 minutes | Leader sends one reminder via SendMessage |
| Reviewer has not reported completion after 5 minutes | Leader writes brief fallback review (2-3 key concerns from checklist) to the perspective's finding file, marks as "Leader fallback" in report |
| Codex CLI not installed or execution failure | Codex agent retries once. On second failure, writes Minor finding "Codex unavailable" |
| Target file/directory does not exist | Validated during setup. Non-existent paths skipped with warning message to user |
| No spec file provided | Spec cross-reference portion skipped; test quality checks still run |
| docs/reviews/ directory does not exist | Created automatically during setup phase |
| Debate reviewer not responding after 2 min | Leader sends reminder |
| Debate reviewer not responding after 3 min | Leader proceeds with available responses |
| Resolving reviewer not responding after 3 min | Leader proceeds — solutions are optional |
| `--rounds 0` specified | Skip debating phase entirely. All findings pass through at original severity (no debate-based calibration). In the resolving phase (step 7), skip step 7a (no tally to apply) and use the original findings list as the confirmed findings list for step 7b-c. |
| All reviewers agree on all findings in round 1 | Leader ends debate early (skip remaining rounds) |
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
