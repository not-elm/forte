# Code Review Board — Debate & Resolution Enhancement Design

> Date: 2026-03-13
> Status: Draft

## Summary

Enhance the code-review-board skill by replacing the single-pass cross-review phase with a round-based debate system (inspired by discussion-board) and adding a solution resolution phase. Reviewers validate each other's findings through structured multi-round debate, then propose solutions for confirmed findings. Both debate rationale and solutions are included in the final report.

## Background

The current code-review-board has a `cross-reviewing` phase where reviewers respond once to a findings summary with duplicate/missed issue notes. This is shallow — reviewers cannot challenge severity, dispute findings, or build on each other's observations. Additionally, the final report lists problems without suggesting solutions, leaving the user to figure out fixes independently.

### Goals

1. Replace the one-shot cross-review with multi-round debate where reviewers validate each other's findings
2. Add a solution proposal phase so the report includes actionable fix suggestions
3. Maintain the existing parallel review performance and conflict prevention guarantees

### Non-Goals

- Full discussion-board features (audit, ratify, hypotheses) — too heavyweight for code review
- Automated code fix generation — solutions are human-readable suggestions, not patches

## Design

### Core Principles Updates

The following existing core principles must be updated in the skill:

| # | Current | Updated |
|---|---------|---------|
| 2 | "No shared WHITEBOARD.md" | "WHITEBOARD.md with per-member write zones for debate and solutions. Each reviewer writes only to their own `### {perspective}` subsection." |
| 5 | "Two-pass workflow" | "Multi-pass workflow — Reviewers analyze independently (pass 1), debate findings validity across N rounds (pass 2), then propose solutions (pass 3). Leader synthesizes all input." |

All other core principles (1, 3, 4, 6, 7) remain unchanged.

### Phase Model

Current:
```
setup → reviewing → cross-reviewing → synthesizing → reporting → completed
```

Proposed:
```
setup → reviewing → debating (N rounds) → resolving → synthesizing → reporting → completed
```

| Phase | Who | What |
|-------|-----|------|
| `setup` | Leader | Existing behavior + WHITEBOARD.md creation, `--rounds` argument parsing |
| `reviewing` | All reviewers | Unchanged. Each reviewer writes to `findings/{perspective}.md` |
| `debating` | All reviewers | WHITEBOARD.md per-member write zones. Round-based debate on findings validity. Default 2 rounds |
| `resolving` | All reviewers | Each reviewer proposes solutions for confirmed findings in WHITEBOARD.md. Single pass |
| `synthesizing` | Leader only | Existing deduplication/scoring + debate result integration + solution consolidation |
| `reporting` | Leader only | Existing + `> Solution:` lines per finding + `## Debate Summary` section |
| `completed` | Leader only | Existing + WHITEBOARD.md cleanup |

### Status Values (Updated)

| Status | Meaning |
|--------|---------|
| `setup` | Initial state. Leader is creating files and spawning reviewers. |
| `reviewing` | Reviewers are analyzing code. Update with progress: `reviewing (3/7 completed)`. |
| `debating` | Reviewers are debating findings validity. Update with progress: `debating (round 1/2)`. |
| `resolving` | Reviewers are proposing solutions for confirmed findings. |
| `synthesizing` | Leader is reading all findings, deduplicating, and scoring. |
| `reporting` | Leader is generating the Markdown report and terminal summary. |
| `completed` | Review finished. Report generated, intermediate files cleaned up. |

### Arguments

New argument:
```
--rounds <N>    Debate round count (default: 2)
```

Examples:
```
/code-review src/api/ --rounds 3
/code-review src/api/ --spec docs/plans/api-design.md --rounds 1
```

### WHITEBOARD.md

New file in the review directory: `docs/reviews/{review-id}/WHITEBOARD.md`

Created during setup phase (step 2 of leader workflow), alongside SYNTHESIS.md and `findings/` directory.

Template:
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

Per-member write zones follow the same conflict prevention pattern as discussion-board: each reviewer writes only to their own `### {perspective}` subsection, append-only. `## Findings Summary` is leader-only. When `--perspectives` filtering excludes certain perspectives, omit their `### {perspective}` subsections from both `## Debate` and `## Solutions`.

**Note:** The reviewing phase retains its existing timeout of 5 min (reminder at 4 min). The debating and resolving phases use shorter timeouts of 3 min (reminder at 2 min) because their per-round scope is narrower than a full review pass.

### Debating Phase

#### Flow (per round)

1. **Leader kicks off debate** — Reads all `findings/*.md`, writes findings summary to WHITEBOARD.md `## Findings Summary` (round 1 only). Broadcasts debate start to reviewers.
2. **Reviewers write reactions** — Each reviewer writes to their own `### {perspective}` section under `## Debate`, append-only.
3. **Leader manages progress** — Waits for all completion reports (reminder at 2 min, timeout at 3 min).
4. **Round 2+:** Leader broadcasts previous round's debate summary, starts next round.

#### Debate Entry Format

```markdown
#### Round {N}
- [D-{XX}-R{round}-{NNN}] **agree** refs=[R-CR-001] | Finding is valid. Edge case concern is correct.
- [D-{XX}-R{round}-{NNN}] **disagree** refs=[R-PF-001] | Not a hot path — call frequency is max 10/sec.
- [D-{XX}-R{round}-{NNN}] **revise** refs=[R-RD-002] | Should be Minor not Major. Function is long but has low branching.
```

Labels: `**agree**` / `**disagree**` / `**revise**`
- `refs=[]` references target finding IDs
- `{XX}` uses the same 2-letter perspective codes as finding IDs (RD, CR, SP, AR, SC, PF, CX)
- Reason is mandatory

#### Debate Tally Rules

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

#### Debate Result Integration

After debating completes, the leader applies tally results:
- **Consensus (agree majority)** → Severity maintained
- **Dispute (disagree majority)** → Severity adjustment or finding exclusion considered during synthesizing
- **Revision proposed (revise entries)** → Severity change recorded in calibration log with the proposed revision as rationale
- **No consensus** → Finding passes through unchanged

#### Early Termination

If all findings either receive agree majority or have no consensus (fewer than 2 reactions) — and no finding has any disagree or revise reactions — the leader may end debate early and skip remaining rounds.

### Resolving Phase

#### Flow

1. **Leader broadcasts confirmed findings list** — Debate-adjusted findings (excluded findings removed, severity updated).
2. **Reviewers propose solutions** — Each writes to `## Solutions` > `### {perspective}` in WHITEBOARD.md. Only for findings relevant to their expertise.
3. **Leader collects** — Solutions are consolidated during synthesizing.

#### Solution Entry Format

```markdown
- [S-{XX}-{NNN}] refs=[R-CR-001] | Solution description
  > Example: `fix code example — optional, max 3 lines`
```

- `refs=[]` references target finding
- Code examples are optional (only when a concrete fix is clear)
- Multiple reviewers may propose different solutions for the same finding — leader selects the best during synthesizing

#### Timeout

- Reminder: 2 min
- Cutoff: 3 min (solutions are optional, so missing submissions do not block)

### Leader Workflow (Updated)

Steps 1-5 are unchanged from the existing skill. Steps 6-9 are replaced:

```
 1. PARSE ARGS    → (existing) + Extract --rounds N (default: 2)

 2. CREATE FILES  → (existing) + Create docs/reviews/{review-id}/WHITEBOARD.md
                    using the WHITEBOARD.md template above.

 3. CREATE TEAM   → (unchanged)

 4. SPAWN         → (unchanged)

 5. WAIT + REPORT → (unchanged)

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

 8. SYNTHESIZE    → (existing severity calibration + deduplication + scoring)
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
                    c. (existing deduplication and scoring — unchanged)

 9. REPORT        → (existing report generation)
                    Additional content:
                    a. Add > Solution: line to findings that have a selected solution
                       (after Evidence line, or after description if no Evidence)
                    b. Add ## Debate Summary section before ## Calibration Log
                       with per-finding tally and outcome
                    c. Delete WHITEBOARD.md along with findings/ and SYNTHESIS.md

10. SHUTDOWN      → (unchanged)
```

### Reviewer Workflow (Updated)

Steps 1-4 are unchanged. Step 5 (cross-review) is replaced:

1. **Read** SYNTHESIS.md header to get target files and spec path. (unchanged)
2. **Read** target files and investigate from assigned perspective. (unchanged)
3. **Write** findings to `findings/{perspective}.md`. (unchanged)
4. **Report** completion to leader via SendMessage. (unchanged)
5. **Debate** (when prompted): Read the Findings Summary in WHITEBOARD.md. For each finding from other perspectives, write reactions in own `### {perspective}` section under `## Debate`. Use `[D-{XX}-R{round}-{NNN}]` format with `agree`/`disagree`/`revise` labels. Send completion report when done. Repeat for each debate round.
6. **Resolve** (when prompted): Read the confirmed findings list from leader's broadcast. Propose solutions for findings relevant to own expertise. Write to own `### {perspective}` section under `## Solutions`. Use `[S-{XX}-{NNN}]` format. Send completion report when done.

### SYNTHESIS.md Template Updates

Replace `## Cross-Review Notes` with `## Debate Tally` in the SYNTHESIS.md template. Also remove the `cross-reviewing` status value from any status documentation and replace with the updated status values table above:

```markdown
## Debate Tally

| Finding | Agree | Disagree | Revise | Result |
|---------|-------|----------|--------|--------|
| [R-XX-NNN] | {N} | {N} | {N} | maintained / adjusted / excluded |
```

### Synthesizing Phase Changes

Inputs expand from `findings/*.md` only to `findings/*.md` + WHITEBOARD.md (`## Debate` + `## Solutions`).

1. **Severity calibration with debate evidence** — In addition to mechanical Evidence-based downgrading, debate consensus/disputes inform calibration decisions.
2. **Finding exclusion** — Findings with disagree majority may be excluded by leader judgment. Exclusion reason recorded in calibration log.
3. **Solution consolidation** — When multiple solutions exist for one finding, leader selects the best. No selection rationale recorded (only the Solution line in the report).

Scoring formula unchanged. Debate results affect scores indirectly through severity calibration and finding exclusion.

### Report Format Changes

#### Solution Lines on Findings

```markdown
- [ ] [R-CR-001] **Critical** | `Correctness` | `routes.ts:45` | Null check missing on user input
  > Evidence: `const name = user.name.toLowerCase()`
  > Solution: Add null guard before access. `const name = user?.name?.toLowerCase() ?? ''`
```

- `> Solution:` line added after Evidence (or after description if no Evidence)
- Only present when a solution was proposed. No forced fill.
- Code examples are optional within the Solution line.

#### Debate Summary Section

New section in report, placed before `## Calibration Log`:

```markdown
## Debate Summary

- [R-CR-001] **Critical** — Consensus (5 agree, 0 disagree). Severity maintained.
- [R-PF-001] **Major→Minor** — Dispute (2 agree, 3 disagree). Not a hot path, adjusted to Minor.
- [R-RD-003] **Excluded** — Dispute (1 agree, 4 disagree). Style preference, not a defect.
```

Provides transparency on why severities changed or findings were excluded.

### Review Directory Structure (Updated)

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

WHITEBOARD.md is deleted along with other intermediate files during the reporting phase (step 9).

### Conflict Prevention Rules (Updated)

This table **fully replaces** the existing conflict prevention rules table in the skill. The old rule #5 ("Cross-review responses via SendMessage, not file writes") is removed — debate reactions are now file writes to WHITEBOARD.md per-member write zones.

| # | Rule | Rationale |
|---|------|-----------|
| 1 | Each reviewer writes only to their own `findings/{perspective}.md` file | Individual files eliminate concurrent write conflicts during reviewing |
| 2 | Each reviewer writes only to their own `### {perspective}` subsection in WHITEBOARD.md | Per-member write zones prevent conflicts during debating/resolving |
| 3 | SYNTHESIS.md is leader-only (reviewers read, never write) | Single writer eliminates conflicts |
| 4 | Append-only writes (no deletion/modification of existing entries) | Prevents overwrites from stale reads |
| 5 | Phase transitions are leader-controlled via broadcast | Clear boundaries prevent out-of-order writes |
| 6 | `## Findings Summary` in WHITEBOARD.md is leader-only | Single writer for summary section |

### Error Handling (Updated)

| Situation | Action |
|-----------|--------|
| Debate reviewer not responding after 2 min | Leader sends reminder |
| Debate reviewer not responding after 3 min | Leader proceeds with available responses |
| Resolving reviewer not responding after 3 min | Leader proceeds — solutions are optional |
| `--rounds 0` specified | Skip debating phase entirely. All findings pass through at original severity (no debate-based calibration). In the resolving phase (step 7), skip step 7a (no tally to apply) and use the original findings list as the confirmed findings list for step 7b-c. |
| All reviewers agree on all findings in round 1 | Leader ends debate early (skip remaining rounds) |

### Entry ID Summary

| Type | Format | File | Phase |
|------|--------|------|-------|
| Finding | `[R-{XX}-{NNN}]` | `findings/{perspective}.md` | reviewing |
| Debate | `[D-{XX}-R{round}-{NNN}]` | WHITEBOARD.md | debating |
| Solution | `[S-{XX}-{NNN}]` | WHITEBOARD.md | resolving |
