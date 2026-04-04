---
name: investigation-board
description: >-
  Evidence-based bug investigation via structured team debate.
  Use when investigating bugs that require root cause analysis through multi-perspective evidence gathering and hypothesis testing.
  Triggers: investigate bug, bug investigation, root cause analysis, バグ調査, 原因調査, 不具合調査
---

# Investigation Board — Evidence-Based Bug Investigation

Investigate bugs through structured evidence gathering, hypothesis testing, and iterative verification using TeamCreate + SendMessage. Extends the shared board-engine debate cycle with evidence-gathering, structured hypothesis formats, dual-layer audit, and debate tally.

## When to Use

- A bug requires multi-perspective root cause analysis
- The bug is complex enough that single-agent investigation (codex-investigate) is insufficient
- Keywords: "investigate bug", "bug investigation", "root cause analysis", "バグ調査", "原因調査"

## When NOT to Use

- Use `codex-investigate` for quick single-agent bug investigation
- Use `discussion-board` for open-ended questions that aren't bug investigations
- Use `design-board` for implementation design decisions
- Use `code-review-board` for code review

## Core Principles

1. **Investigation-centric** — All activity is directed at identifying the root cause of a specific bug.
2. **Evidence-before-hypothesis** — Members must gather and cite concrete evidence before forming hypotheses. Hypotheses without supporting evidence are not permitted.
3. **Round-split WHITEBOARD model** — Base WHITEBOARD.md (bug report + framing + evidence, read-only after evidence-gathering) + per-round WHITEBOARD-R{N}.md (hypotheses + critiques + audit + evidence addendum) + SYNTHESIS.md (leader-managed incl. Debate Tally), all in `docs/investigations/{investigation-id}/`. Concluded → Investigation Report → `docs/reports/`, investigation directory deleted.
4. **Structured hypotheses** — Every hypothesis MUST include: (a) Cause mechanism, (b) Predicted evidence at specific file:line, (c) Falsification condition.
5. **Evidence chain** — Each hypothesis maintains: Supporting (high/medium/low), Counter (strength), Unverified. Quality gate: without at least one Supporting [high] or two Supporting [medium] → [low-confidence].
6. **Dual-layer audit** — Layer 1: Read/Grep at file:line. Layer 2: Codex CLI fact-checking.
7. **Debate tally** — Per hypothesis: challenge/support/amend/question counts + Net (S-C). Net < 0 → [low-confidence]; net >= 0 → [active].
8. **Reproduction context required** — Framing must capture concrete reproduction context before evidence-gathering.
9. **Evidence immutability** — Base `## Evidence` read-only after evidence-gathering. Round-level evidence → `## Evidence Addendum` in WHITEBOARD-R{N}.md.
10. **Read-only investigation** — Evidence gathering uses Read/Grep/Glob (read-only tools) — no file modifications during investigation.

Shared principles (per-member write zones, leader-only SYNTHESIS.md, append-only, leader as synthesizer) are in board-engine REFERENCE.md.

## Shared Debate Engine

**At setup, leader reads the lightweight setup reference:**
1. Use `Glob pattern="**/board-engine/SETUP.md"` to locate the file
2. Read the found file path (file model, round numbering, setup checklist)

**At framing kickoff, leader reads the full debate reference:**
1. Use `Glob pattern="**/board-engine/REFERENCE.md"` to locate the file
2. Read the found file path

**If either Read fails:** Proceed without the reference, but log warning in SYNTHESIS.md status line:
`> Warning: board-engine reference not found. Using inline rules only.`

SETUP.md provides: file model and round numbering. REFERENCE.md provides: full debate cycle, entry formats, and shared rules. Board-specific overrides below take precedence.

## Phase Model

```
setup → framing → evidence-gathering → [Round N: hypothesize → critique → audit (dual-layer) → revise → synthesize → ratify] → concluded
```

## Board-Specific Entry Formats

Shared formats (Hypothesis ID, Critique ID, Evidence Map, Round Context Packet, Ratification History, Minority Report, Completion Report, Audit Table, Revision) are in REFERENCE.md.

### Framing

```markdown
- **Problem**: {interpretation of the bug}
- **Reproduction**: {steps / environment / observed vs. expected}
- **Constraints**: {investigation boundaries}
- **Criteria**: {what constitutes confirmed root cause}
- **Unknowns**: {open questions}
```

### Evidence

**ID:** `[E-{initial}-{seq}]` — `-cx` members use initial + `X` (e.g., `[E-BX-001]`).

Each entry MUST include: **Source** (`file:line` or log ref), **Type** (`code-inspection | log-analysis | test-result | config-review | git-history`), **Snippet** (max 5 lines), **Relevance** (significance to bug).

**Positive:** `**evidence**` label. **Negative** (rules something out): `**negative-evidence**` label. Same fields.

### Structured Hypothesis (Override)

Extends shared Hypothesis ID with three required fields + evidence chain:

```markdown
- [H-S-001] **hypothesis**: {concise statement}
  - **Cause mechanism**: {causal chain with file:line refs}
  - **Predicted evidence**: {what would exist if correct}
  - **Falsification condition**: {observation that disproves}
  - **Evidence chain**:
    - Supporting [high]: refs=[E-S-001] — {why}
    - Counter [medium]: refs=[E-P-003] — {why}
    - Unverified: {what needs checking}
```

Quality gate: Without Supporting [high] x1 or [medium] x2 → `[low-confidence]`, cannot be sole basis for Draft Conclusion.

### Debate Tally (Leader only)

| Hypothesis | Challenge | Support | Amend | Question | Net (S-C) | Status |
|-----------|-----------|---------|-------|----------|-----------|--------|
| [H-S-001] | 1 | 3 | 1 | 1 | +2 | active |

**active**: net >= 0. **low-confidence**: net < 0 or fails quality gate.

### Dual-Layer Audit (Override)

**Layer 1 — Code Verification** (Read/Grep): For every file:line citation, verify code at +/-10 lines.

| Entry | Code Claim | File:Line | Verification | Verdict |
|-------|-----------|-----------|--------------|---------|
| [H-S-001] | {claim} | `file:line` | {what Read showed} | ✅/⚠️/❌/❓ |

Verdicts: ✅ Match, ⚠️ Partial match, ❌ No match, ❓ Cannot verify.

**Layer 2 — Fact-Checking** (Codex CLI): Shared audit table from REFERENCE.md with prompt:
```
Fact-check claims from a bug investigation team. For each:
1. Verify factual accuracy re: technology/language/system behavior
2. Note inaccuracies or unsupported assertions
3. Skip opinions/forecasts — mark ❓
Rate: ✅ Verified / ⚠️ Partially accurate / ❌ Inaccurate / ❓ Unverifiable
Claims: {current round hypotheses and critiques}
```

### Evidence Addendum

Evidence discovered during rounds → `## Evidence Addendum` in WHITEBOARD-R{N}.md. Same format as base Evidence.

### Draft Conclusion (Override)

```markdown
## Draft Conclusion — Round {N}
**Root Cause**: {citing entry IDs and evidence}
**Confidence**: high / medium / low
**Suggested Fix**: {file:line level recommendation}
**Key claims**: 1, 2, 3 (from Evidence Map)
**Unresolved**: {low-confidence claims, open leads}
```

### ID Summary

| Type | Format | Location | Phase |
|------|--------|----------|-------|
| Framing | (no ID) | WHITEBOARD.md | framing |
| Evidence | `[E-{initial}-{seq}]` | WHITEBOARD.md `## Evidence` | evidence-gathering |
| Evidence Addendum | `[E-{initial}-{seq}]` | WHITEBOARD-R{N}.md | hypothesize+ |
| Hypothesis | `[H-{initial}-{seq}]` | WHITEBOARD-R{N}.md | hypothesize |
| Critique | `[CR-{initial}-R{round}-{seq}]` | WHITEBOARD-R{N}.md | critique |
| Audit L1/L2 | (table) | WHITEBOARD-R{N}.md | audit |
| Debate Tally | (table, leader) | SYNTHESIS.md | synthesize |

`-cx` members: initial + `X` (e.g., `[E-BX-001]`). All have voting rights.

---

# Workflow Layer

Standard debate cycle (hypothesize, critique, audit, revise, synthesize, ratify) follows REFERENCE.md. Below: overrides + additional phases.

### setup

- Load board-engine REFERENCE.md.
- Invoke `forte:team-composer`: `topic` = bug description, `team_name` = kebab-case `{investigation-id}`, `role_count` = `"3-4"`.
- After team-composer completes:
  - Create `docs/investigations/{investigation-id}/WHITEBOARD.md` + `SYNTHESIS.md` using templates.
  - Do NOT create per-round files yet.
  - Ensure `docs/investigations/` is in `.gitignore`.
  - **Optional: codex-investigate pre-injection** — run with bug symptoms; include output in Bug Report.
  - Spawn: normal members get investigation prompt + **role-specific checklist** (3-5 items) + **few-shot example** (~200-300 tokens). `-cx` members: same + codex exec template.

### framing

- **Leader reads board-engine REFERENCE.md** at framing kickoff (if not already read).
- Normal members: full WHITEBOARD.md Read (small at this stage).
- -cx members use Codex framing template (see team-composer Codex-Mediated Protocol).
- **Reproduction context gate**: Missing reproduction steps → request clarification before proceeding.
- Combine completion confirmation + evidence-gathering kickoff in 1 broadcast.

### evidence-gathering

- Full WHITEBOARD.md Read for all framings.
- 2-5 evidence entries per member with Source/Type/Snippet/Relevance.
- Both positive and negative evidence valuable.
- Priority: code-inspection → log-analysis → git-history → config-review → test-result.
- **Cross-boundary investigation permitted.**
- After all complete: base `## Evidence` becomes **read-only**.

### hypothesize (override)

- Shared rules from REFERENCE.md, plus:
- **MUST read all evidence first**: base WHITEBOARD.md `## Evidence` + any `## Evidence Addendum` in current round file.
- Every hypothesis MUST include cause mechanism + predicted evidence + falsification condition + evidence chain.
- 1-3 hypotheses per member — fewer, better-supported preferred.

### audit (override)

- **Layer 1** runs first: Read tool at +/-10 lines for every file:line citation. Record in Layer 1 table. May invalidate before Layer 2.
- **Layer 2**: Shared audit from REFERENCE.md with investigation-specific Codex prompt.
- Error: L1 file not found → ❓; L2 Codex error → skip L2, proceed with L1 only.
- All ✅/❓ both layers → skip revise; any ⚠️/❌ → revise.

### synthesize (override)

- **Incremental read:** (1) WHITEBOARD-R{N}.md in full, (2) Evidence Map + Draft Conclusion + Debate Tally from SYNTHESIS.md, (3) Grep older rounds by entry ID for cross-refs only.
- Updates **Debate Tally** + Evidence Map + Draft Conclusion (Root Cause, Confidence, Suggested Fix) + Round Context Packet in SYNTHESIS.md.
- **Information loss prevention**: list hypotheses NOT in conclusion with exclusion reasons.

### concluded

- Export Investigation Report to `docs/reports/YYYY-MM-DD-{investigation-id}-report.md`.
- Verify file created. Delete investigation directory.
- If interrupted: skip export, delete directory manually.

---

# Reference Layer

## WHITEBOARD.md Template (Base)

Path: `docs/investigations/{investigation-id}/WHITEBOARD.md` — **read-only after evidence-gathering**.

```markdown
# WHITEBOARD — {investigation-id}
> Bug: {bug description}
> Created: {YYYY-MM-DD}
> Team: {comma-separated names}

## Bug Report
{Symptoms, error messages, stack traces, affected components.}
### Reproduction Context
{Steps, environment, preconditions, expected, actual.}
### Prior Investigation (codex-investigate)
{Output or "(No prior investigation)".}

## How Our Work Connects
{Each member's role and perspective.}

## Framing
### {member-A}
### {member-B}
<!-- ... per team member -->

## Evidence
### {member-A}
### {member-B}
<!-- ... per team member -->
```

## WHITEBOARD-R{N}.md Template (Per-Round)

Shared template from REFERENCE.md + `## Evidence Addendum`:

```markdown
# WHITEBOARD — {investigation-id} / Round {N}
> Round: {N}
> Created: {YYYY-MM-DD}

## Hypotheses
### {member-A}
### {member-B}
## Critique
### {member-A}
### {member-B}
## Audit
## Evidence Addendum
### {member-A}
### {member-B}
```

## SYNTHESIS.md Template

```markdown
# SYNTHESIS — {investigation-id}
> Status: setup
> Round: 0
> Max Rounds: 10

## Debate Tally
## Evidence Map
## Draft Conclusion
## Round Context Packet
## Ratification History
## Minority Report
## Final Conclusion
```

Includes `## Debate Tally` (investigation-specific) + `## Round Context Packet` (shared engine).

## Investigation Report Template

Path: `docs/reports/YYYY-MM-DD-{investigation-id}-report.md`

```markdown
# {Bug Description} — Investigation Report
> Date: {YYYY-MM-DD}
> Status: Concluded ({accept_count}/{total} {unanimous/majority})
> Method: Investigation Board ({N}-member structured investigation)

## Summary
{Root cause — 2-3 sentences}
## Bug Report
{Description + reproduction context + impact}
## Root Cause
{Detailed statement citing key evidence IDs.}
## Confidence
{high / medium / low — with justification}
## Suggested Fix
{Concrete fix at file:line level}
## Key Evidence
{Top 3-5 decisive entries}
## Investigation Artifacts
- Team: {names} | Evidence: {N} | Hypotheses: {N} | Critiques: {N}
- Ratification: Round {N}, {accept}/{total} | Unresolved: {questions}
```

Note: This is an investigation report, not an implementation plan. Use `superpowers:writing-plans` with this report as input for executable fix plans.
