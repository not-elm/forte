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

### Debating Phase

#### Flow (per round)

1. **Leader kicks off debate** — Reads all `findings/*.md`, writes findings summary to WHITEBOARD.md `## Findings Summary` (round 1 only). Broadcasts debate start to reviewers.
2. **Reviewers write reactions** — Each reviewer writes to their own `### {perspective}` section under `## Debate`, append-only.
3. **Leader manages progress** — Waits for all completion reports (reminder at 2 min, timeout at 3 min).
4. **Round 2+:** Leader broadcasts previous round's debate summary, starts next round.

#### Debate Entry Format

```markdown
#### Round {N}
- [D-{PERSPECTIVE_CODE}-R{round}-{seq}] **agree** refs=[R-CR-001] | Finding is valid. Edge case concern is correct.
- [D-{PERSPECTIVE_CODE}-R{round}-{seq}] **disagree** refs=[R-PF-001] | Not a hot path — call frequency is max 10/sec.
- [D-{PERSPECTIVE_CODE}-R{round}-{seq}] **revise** refs=[R-RD-002] | Should be Minor not Major. Function is long but has low branching.
```

Labels: `**agree**` / `**disagree**` / `**revise**`
- `refs=[]` references target finding IDs
- Reason is mandatory

#### Debate Result Integration

After debating completes, the leader tallies reactions:
- **Consensus (agree majority)** → Severity maintained
- **Dispute (disagree majority)** → Severity adjustment or finding exclusion considered during synthesizing
- **Revision proposed (revise)** → Severity change recorded in calibration log

### Resolving Phase

#### Flow

1. **Leader broadcasts confirmed findings list** — Debate-adjusted findings (excluded findings removed, severity updated).
2. **Reviewers propose solutions** — Each writes to `## Solutions` > `### {perspective}` in WHITEBOARD.md. Only for findings relevant to their expertise.
3. **Leader collects** — Solutions are consolidated during synthesizing.

#### Solution Entry Format

```markdown
- [S-{PERSPECTIVE_CODE}-{seq}] refs=[R-CR-001] | Solution description
  > Example: `fix code example — optional, max 3 lines`
```

- `refs=[]` references target finding
- Code examples are optional (only when a concrete fix is clear)
- Multiple reviewers may propose different solutions for the same finding — leader selects the best during synthesizing

#### Timeout

- Reminder: 2 min
- Cutoff: 3 min (solutions are optional, so missing submissions do not block)

### WHITEBOARD.md

New file in the review directory: `docs/reviews/{review-id}/WHITEBOARD.md`

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

Per-member write zones follow the same conflict prevention pattern as discussion-board: each reviewer writes only to their own `### {perspective}` subsection, append-only.

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

WHITEBOARD.md is deleted along with other intermediate files during reporting phase.

### Conflict Prevention Rules (Updated)

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
| `--rounds 0` specified | Skip debating phase entirely, proceed directly to resolving |
| All reviewers agree on all findings in round 1 | Leader may end debate early (skip remaining rounds) |

### Entry ID Summary

| Type | Format | File | Phase |
|------|--------|------|-------|
| Finding | `[R-{XX}-{NNN}]` | `findings/{perspective}.md` | reviewing |
| Debate | `[D-{XX}-R{round}-{NNN}]` | WHITEBOARD.md | debating |
| Solution | `[S-{XX}-{NNN}]` | WHITEBOARD.md | resolving |
