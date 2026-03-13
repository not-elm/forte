# Code Review Board — Debate & Resolution Enhancement Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-pass cross-review in code-review-board with round-based debate and add a solution resolution phase.

**Architecture:** Modify the single file `skills/code-review-board/SKILL.md`. All changes are to the prompt/spec content — no code files, no tests. The file is ~730 lines. Changes touch 13 distinct sections, applied in dependency order (foundations first, then sections that reference them).

**Tech Stack:** Markdown (SKILL.md prompt file)

**Spec:** `docs/superpowers/specs/2026-03-13-code-review-board-debate-design.md`

---

## Chunk 1: Foundation Sections

These sections establish the new concepts (phases, arguments, entry IDs, templates) that later sections reference.

### Task 1: Update Core Principles

**Files:**
- Modify: `skills/code-review-board/SKILL.md:37-46`

- [ ] **Step 1: Update Core Principle #2**

Replace line 40:
```markdown
2. **Individual file model** — Each reviewer writes to their own `findings/{perspective}.md`. Leader reads all files during synthesize and generates a unified view. No shared WHITEBOARD.md.
```
With:
```markdown
2. **Individual file model + WHITEBOARD.md** — Each reviewer writes findings to their own `findings/{perspective}.md`. For debate and solutions, reviewers write to per-member `### {perspective}` subsections in a shared WHITEBOARD.md. Leader reads all files during synthesize and generates a unified view.
```

- [ ] **Step 2: Update Core Principle #5**

Replace line 43:
```markdown
5. **Two-pass workflow** — Reviewers analyze independently in parallel (pass 1), then respond to leader's cross-review summary (pass 2). Leader synthesizes all input.
```
With:
```markdown
5. **Multi-pass workflow** — Reviewers analyze independently in parallel (pass 1), debate findings validity across N rounds (pass 2), then propose solutions (pass 3). Leader synthesizes all input.
```

- [ ] **Step 3: Verify** — Read lines 37-46 to confirm both principles updated correctly.

### Task 2: Update Phase Model and Transition Triggers

**Files:**
- Modify: `skills/code-review-board/SKILL.md:49-71`

- [ ] **Step 1: Replace phase diagram**

Replace line 52:
```
setup → reviewing → cross-reviewing → synthesizing → reporting → completed
```
With:
```
setup → reviewing → debating (N rounds) → resolving → synthesizing → reporting → completed
```

- [ ] **Step 2: Replace phase table**

Replace the phase table (lines 55-62) with:

```markdown
| Phase | Who Acts | What Happens |
|-------|----------|--------------|
| `setup` | Leader | Parse arguments (including `--rounds`), identify target files, create `docs/reviews/{review-id}/` directory with SYNTHESIS.md, WHITEBOARD.md, and `findings/` subdirectory, create team, spawn reviewers |
| `reviewing` | All reviewers | Each reviewer analyzes code from their perspective, writes findings to `findings/{perspective}.md`, sends structured completion report to leader. Leader displays progress to user after each report. |
| `debating` | All reviewers | Reviewers write reactions to other perspectives' findings in WHITEBOARD.md per-member write zones. Multiple rounds (default 2, configurable via `--rounds`). Leader manages round transitions. |
| `resolving` | All reviewers | Each reviewer proposes solutions for confirmed findings in WHITEBOARD.md `## Solutions` section. Single pass. |
| `synthesizing` | Leader only | Leader reads all `findings/*.md` and WHITEBOARD.md, applies debate tally, calibrates severity, deduplicates, consolidates solutions, computes scores, writes to SYNTHESIS.md |
| `reporting` | Leader only | Leader generates Markdown report to `docs/reviews/YYYY-MM-DD-{target}-review.md` (with Solution lines and Debate Summary), displays terminal summary, deletes intermediate files |
| `completed` | Leader only | Sends shutdown requests to all reviewers, cleans up team |
```

- [ ] **Step 3: Replace transition triggers**

Replace the transition triggers (lines 64-70) with:

```markdown
### Transition Triggers

- `setup` → `reviewing`: All reviewers spawned and tasks assigned.
- `reviewing` → `debating`: All reviewers have reported completion (or timed out after 5 minutes). Leader sends reminder after 4 minutes to unresponsive reviewers.
- `debating` → next round or `resolving`: Each round completes when all reviewers report (or timeout at 3 min, reminder at 2 min). After final round (or early termination), proceed to `resolving`.
- `resolving` → `synthesizing`: All reviewers have reported solution proposals (or timeout at 3 min, reminder at 2 min).
- `synthesizing` → `reporting`: SYNTHESIS.md is complete with scores and deduplicated findings.
- `reporting` → `completed`: Markdown report generated, intermediate files cleaned up.
```

- [ ] **Step 4: Verify** — Read lines 49-75 to confirm phase model updated.

### Task 3: Add --rounds Argument

**Files:**
- Modify: `skills/code-review-board/SKILL.md:23-35`

- [ ] **Step 1: Add --rounds to argument list**

After line 27 (`--perspectives` line), add:
```markdown
- `--rounds <N>` (optional): Number of debate rounds. Default: 2. Set to 0 to skip debate phase entirely.
```

- [ ] **Step 2: Add --rounds examples**

After line 34 (`--perspectives -codex-reviewer` example), add:
```
/code-review src/api/ --rounds 3
/code-review src/api/ --rounds 0
```

- [ ] **Step 3: Verify** — Read lines 23-40 to confirm argument section.

### Task 4: Update Review Directory Structure

**Files:**
- Modify: `skills/code-review-board/SKILL.md:89-111`

- [ ] **Step 1: Add WHITEBOARD.md to directory tree**

Replace the directory tree (lines 93-104) with:
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

- [ ] **Step 2: Add WHITEBOARD.md to .gitignore entries**

Replace lines 109-111:
```
docs/reviews/*/findings/
docs/reviews/*/SYNTHESIS.md
```
With:
```
docs/reviews/*/findings/
docs/reviews/*/SYNTHESIS.md
docs/reviews/*/WHITEBOARD.md
```

- [ ] **Step 3: Verify** — Read lines 89-115 to confirm.

### Task 5: Add WHITEBOARD.md Template Section

**Files:**
- Modify: `skills/code-review-board/SKILL.md` — insert after the Individual Finding File Template section (after line 129)

- [ ] **Step 1: Insert WHITEBOARD.md template**

After line 129 (`Reviewers append findings...`), insert:

```markdown

### WHITEBOARD.md Template

Create at `docs/reviews/{review-id}/WHITEBOARD.md` during setup phase. This file uses per-member write zones — each reviewer writes only to their own `### {perspective}` subsection under `## Debate` and `## Solutions`. `## Findings Summary` is leader-only.

When `--perspectives` filtering excludes certain perspectives, omit their `### {perspective}` subsections from both `## Debate` and `## Solutions`.

```markdown
# WHITEBOARD — {review-id}
> Target: {target paths}
> Rounds: {N}

## Findings Summary
{Leader writes: finding ID, severity, file:line, brief description — grouped by file}

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

**Note:** The reviewing phase retains its existing timeout of 5 min (reminder at 4 min). The debating and resolving phases use shorter timeouts of 3 min (reminder at 2 min) because their per-round scope is narrower than a full review pass.
```

- [ ] **Step 2: Verify** — Read the inserted section to confirm template is correct.

- [ ] **Step 3: Commit**

```bash
git add skills/code-review-board/SKILL.md
git commit -m "feat(code-review-board): update foundation sections for debate enhancement

Update core principles, phase model, arguments, directory structure,
and add WHITEBOARD.md template."
```

### Task 6: Update SYNTHESIS.md Template and Status Values

**Files:**
- Modify: `skills/code-review-board/SKILL.md` — the SYNTHESIS.md Template section (around lines 132-188 after Task 5 insertions shift line numbers)

- [ ] **Step 1: Replace `## Cross-Review Notes` with `## Debate Tally` in SYNTHESIS.md template**

In the SYNTHESIS.md template markdown block, replace:
```markdown
## Cross-Review Notes
```
With:
```markdown
## Debate Tally

| Finding | Agree | Disagree | Revise | Result |
|---------|-------|----------|--------|--------|
```

- [ ] **Step 2: Replace Status Values table**

Replace the status values table with:

```markdown
| Status | Meaning |
|--------|---------|
| `setup` | Initial state. Leader is creating files and spawning reviewers. |
| `reviewing` | Reviewers are analyzing code. Update with progress: `reviewing (3/7 completed)`. |
| `debating` | Reviewers are debating findings validity. Update with progress: `debating (round 1/2)`. |
| `resolving` | Reviewers are proposing solutions for confirmed findings. |
| `synthesizing` | Leader is reading all findings, deduplicating, and scoring. |
| `reporting` | Leader is generating the Markdown report and terminal summary. |
| `completed` | Review finished. Report generated, intermediate files cleaned up. |

Update `Status` and `Phase` at each transition. During `reviewing`, update with progress: `reviewing (3/7 completed)`. During `debating`, update with progress: `debating (round 1/2)`.
```

- [ ] **Step 3: Verify** — Read the SYNTHESIS.md template section to confirm.

### Task 7: Update Entry ID System

**Files:**
- Modify: `skills/code-review-board/SKILL.md` — Entry ID System section (around line 191+)

- [ ] **Step 1: Add Debate and Solution entry types**

After the Finding Format section (after the Evidence rule line), add:

```markdown

### Debate Entry Format

Format: `[D-{XX}-R{round}-{NNN}]` where `{XX}` uses the same 2-letter perspective codes as finding IDs.

Labels: `**agree**` / `**disagree**` / `**revise**`

```markdown
#### Round {N}
- [D-{XX}-R{round}-{NNN}] **agree** refs=[R-CR-001] | Finding is valid. Edge case concern is correct.
- [D-{XX}-R{round}-{NNN}] **disagree** refs=[R-PF-001] | Not a hot path — call frequency is max 10/sec.
- [D-{XX}-R{round}-{NNN}] **revise** refs=[R-RD-002] | Should be Minor not Major. Function is long but has low branching.
```

- `refs=[]` references target finding IDs
- Reason is mandatory
- Each reviewer writes debate entries only in their own `### {perspective}` subsection under `## Debate` in WHITEBOARD.md

### Debate Tally Rules

After all debate rounds complete, the leader tallies reactions per finding:

- **Tally scope:** Count only explicit `agree`, `disagree`, and `revise` reactions. Reviewers who did not react to a finding are not counted (neither for nor against).
- **Minimum threshold:** A finding needs reactions from at least 2 reviewers (excluding the author) to have a meaningful tally. Findings with fewer than 2 reactions are treated as "no consensus" and pass through unchanged.
- **Finding author:** The reviewer who authored a finding does not vote on their own finding. Their implicit position is "agree."
- **Tally interpretation:**
  - `revise` counts as `disagree` for majority calculation (but the proposed revision is recorded separately for severity calibration)
  - **Agree majority** = agree count > (disagree + revise) count among responding reviewers → severity maintained
  - **Disagree majority** = (disagree + revise) count > agree count among responding reviewers → severity adjustment or exclusion considered during synthesizing
  - **Tie** = treated as "no consensus" → finding passes through unchanged
- **No consensus** (tie or fewer than 2 reactions): Finding passes through at original severity. No debate-based calibration applied.

### Debate Result Integration

After debating completes, the leader applies tally results:
- **Consensus (agree majority)** → Severity maintained
- **Dispute (disagree majority)** → Severity adjustment or finding exclusion considered during synthesizing
- **Revision proposed (revise entries)** → Severity change recorded in calibration log with the proposed revision as rationale
- **No consensus** → Finding passes through unchanged

### Early Termination

If all findings either receive agree majority or have no consensus (fewer than 2 reactions) — and no finding has any disagree or revise reactions — the leader may end debate early and skip remaining rounds.

### Solution Entry Format

Format: `[S-{XX}-{NNN}]`

```markdown
- [S-{XX}-{NNN}] refs=[R-CR-001] | Solution description
  > Example: `fix code example — optional, max 3 lines`
```

- `refs=[]` references target finding
- Code examples are optional (only when a concrete fix is clear)
- Multiple reviewers may propose different solutions for the same finding — leader selects the best during synthesizing
- Each reviewer writes solution entries only in their own `### {perspective}` subsection under `## Solutions` in WHITEBOARD.md

### Entry ID Summary

| Type | Format | File | Phase |
|------|--------|------|-------|
| Finding | `[R-{XX}-{NNN}]` | `findings/{perspective}.md` | reviewing |
| Debate | `[D-{XX}-R{round}-{NNN}]` | WHITEBOARD.md | debating |
| Solution | `[S-{XX}-{NNN}]` | WHITEBOARD.md | resolving |
```

- [ ] **Step 2: Verify** — Read the entry ID section to confirm all formats present.

- [ ] **Step 3: Commit**

```bash
git add skills/code-review-board/SKILL.md
git commit -m "feat(code-review-board): add debate/solution entry formats and tally rules"
```

---

## Chunk 2: Workflow Sections

These sections define the step-by-step instructions for leader and reviewers using the concepts from Chunk 1.

### Task 8: Replace Leader Workflow Steps 6-9

**Files:**
- Modify: `skills/code-review-board/SKILL.md` — Leader Workflow section

- [ ] **Step 1: Update step 1 (PARSE ARGS)**

Add to the end of step 1's bullet list:
```
                    - Extract --rounds N (default: 2)
```

- [ ] **Step 2: Update step 2 (CREATE FILES)**

Add after the `Write SYNTHESIS.md` line:
```
                    Create docs/reviews/{review-id}/WHITEBOARD.md using WHITEBOARD.md template.
```

- [ ] **Step 3: Replace step 6 (CROSS-REVIEW → DEBATE)**

Replace the entire step 6 block with:

```
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
```

- [ ] **Step 4: Insert new step 7 (RESOLVE)**

Insert after the new step 6:

```
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
```

- [ ] **Step 5: Update step 7→8 (SYNTHESIZE)**

Renumber old step 7 to step 8. Add after the existing content:

```
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
```

Also update the deduplication step to say "Apply debate tally duplicate notes" instead of "Apply cross-review duplicate notes from step 6."

- [ ] **Step 6: Update step 8→9 (REPORT)**

Renumber old step 8 to step 9. Add:

```
                    Additional content:
                    a. Add > Solution: line to findings that have a selected solution
                       (after Evidence line, or after description if no Evidence)
                    b. Add ## Debate Summary section before ## Calibration Log
                       with per-finding tally and outcome
                    c. Delete WHITEBOARD.md along with findings/ and SYNTHESIS.md
```

- [ ] **Step 7: Renumber step 9→10 (SHUTDOWN)**

Renumber old step 9 to step 10. Content unchanged.

- [ ] **Step 8: Verify** — Read the entire Leader Workflow section to confirm all 10 steps present and correctly numbered.

- [ ] **Step 9: Commit**

```bash
git add skills/code-review-board/SKILL.md
git commit -m "feat(code-review-board): replace leader workflow with debate/resolve steps"
```

### Task 9: Update Reviewer Workflow

**Files:**
- Modify: `skills/code-review-board/SKILL.md` — Reviewer Workflow section

- [ ] **Step 1: Replace step 5 in "All Reviewers (except Codex)"**

Replace:
```markdown
5. **Cross-review** (when prompted): Read the leader's findings summary broadcast. Reply with duplicate findings and missed issues from your perspective.
```
With:
```markdown
5. **Debate** (when prompted): Read the Findings Summary in WHITEBOARD.md. For each finding from other perspectives, write reactions in own `### {perspective}` section under `## Debate`. Use `[D-{XX}-R{round}-{NNN}]` format with `agree`/`disagree`/`revise` labels. Send completion report when done. Repeat for each debate round.
6. **Resolve** (when prompted): Read the confirmed findings list from leader's broadcast. Propose solutions for findings relevant to own expertise. Write to own `### {perspective}` section under `## Solutions`. Use `[S-{XX}-{NNN}]` format. Send completion report when done.
```

- [ ] **Step 2: Replace step 7 in "Codex Reviewer"**

Replace:
```markdown
7. **Cross-review** (when prompted): Same as other reviewers.
```
With:
```markdown
7. **Debate** (when prompted): Same as other reviewers.
8. **Resolve** (when prompted): Same as other reviewers.
```

- [ ] **Step 3: Verify** — Read the Reviewer Workflow section to confirm.

- [ ] **Step 4: Commit**

```bash
git add skills/code-review-board/SKILL.md
git commit -m "feat(code-review-board): update reviewer workflow with debate/resolve steps"
```

---

## Chunk 3: Report, Rules, and Example

Update the output format, rules tables, error handling, and the walkthrough example to reflect the new phases.

### Task 10: Update Markdown Report Template

**Files:**
- Modify: `skills/code-review-board/SKILL.md` — Markdown Report Template section

- [ ] **Step 1: Add Solution lines to finding examples in template**

In the `### Critical` section, change:
```markdown
- [ ] [R-XX-NNN] **Critical** | `{perspective}` | `{file}:{line}` | {Description}
  > Evidence: `{code snippet}`
```
To:
```markdown
- [ ] [R-XX-NNN] **Critical** | `{perspective}` | `{file}:{line}` | {Description}
  > Evidence: `{code snippet}`
  > Solution: {solution description — only if proposed}
```

Do the same for `### Major`.

- [ ] **Step 2: Add Debate Summary section to template**

Before `## Calibration Log` in the template, insert:

```markdown
## Debate Summary

- [R-XX-NNN] **{Severity}** — {Consensus/Dispute/Excluded} ({N} agree, {N} disagree). {Outcome description}.
```

- [ ] **Step 3: Update Report Format Notes**

Add after the existing notes:
```markdown
- `> Solution:` line appears after Evidence (or after description if no Evidence). Only present when a solution was proposed — no forced fill. Code examples within Solution are optional.
- Debate Summary section shows per-finding tally and outcome, providing transparency on severity changes and finding exclusions
```

- [ ] **Step 4: Verify** — Read the report template section to confirm.

### Task 11: Replace Conflict Prevention Rules

**Files:**
- Modify: `skills/code-review-board/SKILL.md` — Conflict Prevention Rules section

- [ ] **Step 1: Replace the entire rules table**

Replace the existing table (5 rules) with the updated table (6 rules) from the spec. Add the note: "The old rule #5 ('Cross-review responses via SendMessage, not file writes') is removed — debate reactions are now file writes to WHITEBOARD.md per-member write zones."

New table:

```markdown
| # | Rule | Rationale |
|---|------|-----------|
| 1 | Each reviewer writes only to their own `findings/{perspective}.md` file | Individual files eliminate concurrent write conflicts during reviewing |
| 2 | Each reviewer writes only to their own `### {perspective}` subsection in WHITEBOARD.md | Per-member write zones prevent conflicts during debating/resolving |
| 3 | SYNTHESIS.md is leader-only (reviewers read, never write) | Single writer eliminates conflicts |
| 4 | Append-only writes (no deletion/modification of existing entries) | Prevents overwrites from stale reads |
| 5 | Phase transitions are leader-controlled via broadcast | Clear boundaries prevent out-of-order writes |
| 6 | `## Findings Summary` in WHITEBOARD.md is leader-only | Single writer for summary section |
```

- [ ] **Step 2: Verify** — Read the conflict prevention section to confirm.

### Task 12: Update Error Handling

**Files:**
- Modify: `skills/code-review-board/SKILL.md` — Error Handling section

- [ ] **Step 1: Replace the error handling table**

Remove the `Cross-review responses not received after 2 minutes` row. Add new rows:

```markdown
| Debate reviewer not responding after 2 min | Leader sends reminder |
| Debate reviewer not responding after 3 min | Leader proceeds with available responses |
| Resolving reviewer not responding after 3 min | Leader proceeds — solutions are optional |
| `--rounds 0` specified | Skip debating phase entirely. All findings pass through at original severity (no debate-based calibration). In the resolving phase (step 7), skip step 7a (no tally to apply) and use the original findings list as the confirmed findings list for step 7b-c. |
| All reviewers agree on all findings in round 1 | Leader ends debate early (skip remaining rounds) |
```

- [ ] **Step 2: Verify** — Read the error handling section to confirm.

- [ ] **Step 3: Commit**

```bash
git add skills/code-review-board/SKILL.md
git commit -m "feat(code-review-board): update report template, rules, and error handling"
```

### Task 13: Update Example

**Files:**
- Modify: `skills/code-review-board/SKILL.md` — Example section

- [ ] **Step 1: Replace the entire example**

Replace the example (from `=== SETUP PHASE ===` to end of code block) with an updated version that shows:
- Setup creates WHITEBOARD.md
- Reviewing phase (unchanged)
- Debating phase with 2 rounds (showing debate entries, round summaries, tally)
- Resolving phase (showing solution proposals)
- Synthesizing phase (showing debate-informed calibration and solution consolidation)
- Reporting phase (showing Solution lines and Debate Summary in report)

The new example:

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
    types.ts: [R-SP-001] Minor, [R-SP-002] Info"

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
   - correctness: [D-CR-R2-001] **agree** refs=[R-PF-001] **revise** | Agree with Minor.

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

   | Perspective | Score | Grade | Critical | Major | Minor | Info |
   |-------------|-------|-------|----------|-------|-------|------|
   | Readability | 90 | A- | 0 | 1 | 0 | 0 |
   | Correctness | 70 | C- | 1 | 1 | 0 | 0 |
   | Spec Compliance | 94 | A | 0 | 0 | 2 | 1 |
   | Architecture | 90 | A- | 0 | 1 | 0 | 0 |
   | Security | 100 | A+ | 0 | 0 | 0 | 0 |
   | Performance | 94 | A | 0 | 0 | 2 | 0 |
   | Codex Holistic | 84 | B | 0 | 1 | 2 | 1 |

   Overall: 89 → B+

=== REPORTING PHASE ===

9. Leader generates docs/reviews/2026-03-01-api-review.md
   with severity-grouped checklists, Solution lines, Debate Summary, and file summary.
   Sample finding in report:
   - [ ] [R-CR-001] **Critical** | `Correctness` | `routes.ts:45` | Null check missing
     > Evidence: `const name = user.name.toLowerCase()`
     > Solution: Add null guard with early return. `if (!user?.name) return defaultResponse;`

   Deletes docs/reviews/2026-03-01-api/findings/, WHITEBOARD.md, and SYNTHESIS.md.
   Removes docs/reviews/2026-03-01-api/ directory.
   Displays terminal summary with Critical/Major findings.

=== COMPLETED ===

10. Leader sends shutdown requests, deletes team.
    Reports to user: "Code review complete. Report: docs/reviews/2026-03-01-api-review.md"
```

- [ ] **Step 2: Verify** — Read the example section to confirm it covers all new phases.

- [ ] **Step 3: Commit**

```bash
git add skills/code-review-board/SKILL.md
git commit -m "feat(code-review-board): update example to show debate and resolution phases"
```

### Task 14: Final Verification

- [ ] **Step 1: Read the entire SKILL.md** — Scan for any remaining references to "cross-review" or "cross-reviewing" that should have been updated. Check for consistency.

- [ ] **Step 2: Fix any remaining references** — Replace any leftover "cross-review" references with appropriate debate/resolve terminology.

- [ ] **Step 3: Final commit**

```bash
git add skills/code-review-board/SKILL.md
git commit -m "feat(code-review-board): final cleanup — remove remaining cross-review references"
```
