---
name: investigation-board
description: >-
  Evidence-based bug investigation via structured team debate.
  Use when investigating bugs that require root cause analysis through multi-perspective evidence gathering and hypothesis testing.
  Triggers: investigate bug, bug investigation, root cause analysis, バグ調査, 原因調査, 不具合調査
---

# Investigation Board — Evidence-Based Bug Investigation

Investigate bugs through structured evidence gathering, hypothesis testing, and iterative verification using TeamCreate + SendMessage. Extends discussion-board's base patterns with bug investigation-specific phases: evidence-gathering, structured hypothesis formats, dual-layer audit, and debate tally.

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
3. **2-file model** — WHITEBOARD.md (framing + evidence + hypotheses + critiques) + SYNTHESIS.md (leader-managed state), both in `docs/investigations/{investigation-id}/`. Concluded → Investigation Report exported to `docs/reports/`, investigation directory deleted.
4. **Per-member write zones** — Each teammate writes only to their own `### {name}` subsection in WHITEBOARD.md.
5. **Leader-only SYNTHESIS.md** — Teammates read but never write to SYNTHESIS.md.
6. **Append-only** — Teammates add content, never delete or modify existing entries.
7. **Structured hypotheses** — Every hypothesis MUST include three required fields: (a) Cause mechanism — the precise causal chain, (b) Predicted evidence — what evidence would exist at specific file:line locations if this hypothesis is correct, (c) Falsification condition — a concrete observation that would definitively disprove this hypothesis.
8. **Evidence chain** — Each hypothesis must maintain a living evidence chain with three categories: Supporting evidence (with strength: high/medium/low), Counter evidence (with strength), and Unverified leads (pending investigation). Quality gate: hypotheses without at least one Supporting [high] or two Supporting [medium] entries are automatically marked [low-confidence].
9. **Dual-layer audit** — Audit runs two layers: Layer 1 (code-specific) uses Read/Grep tools to verify code claims at specific file:line references; Layer 2 (general fact-checking) uses Codex CLI for broader factual verification, same as discussion-board.
10. **Debate tally** — Leader maintains a quantitative tally per hypothesis: challenge count, support count, amend count, question count, and Net score (support minus challenge). Hypotheses with net < 0 are marked [low-confidence]; hypotheses with net ≥ 0 remain [active].
11. **Leader as synthesizer, not participant** — Leader does NOT write evidence entries, hypotheses, or critiques. Leader MAY write process artifacts (audit results, evidence maps, debate tallies, conclusions) to facilitate investigation quality.
12. **Advisory members (Codex non-voting)** — A Codex advisory agent may participate using fixed initial `X`. Advisory entries carry the prefix `[advisory]` and are non-voting. Entry IDs follow the same format: `[E-X-NNN]`, `[H-X-NNN]`, `[CR-X-R{N}-NNN]`.
13. **Reproduction context required** — The Framing phase must capture a concrete reproduction context (steps, environment, observed vs. expected behavior) before evidence-gathering begins. Investigations without reproduction context are blocked from proceeding to evidence-gathering.

## Phase Model

```
setup → framing (with reproduction context) → evidence-gathering → [Round N: hypothesize → critique → audit (dual-layer) → revise (if needed) → synthesize → ratify] → concluded
```

| Phase | Who | What |
|-------|-----|------|
| setup | Leader + User | Analyze bug report, suggest 4-10 investigator roles, user approves, create team + files |
| framing | All members | Document bug interpretation, reproduction steps, environment, constraints, success criteria, unknowns |
| evidence-gathering | All members | Collect concrete evidence entries (code inspection, logs, test results, config review, git history) in own section |
| hypothesize | All members | Write structured hypotheses (cause mechanism + predicted evidence + falsification condition) citing gathered evidence |
| critique | All members | Challenge/support/amend/question hypotheses with labels, refs, and evidence citations |
| audit | Leader only | Layer 1: verify code claims via Read/Grep at cited file:line references; Layer 2: run Codex CLI for broader fact-checking; write results to WHITEBOARD `## Audit` |
| revise | All members | Review audit findings and append corrections to own entries (skipped if no ⚠️/❌ found) |
| synthesize | Leader only | Read all WHITEBOARD content, update debate tally, write Evidence Map + Draft Conclusion in SYNTHESIS.md |
| ratify | All members | Vote accept or push-back via SendMessage. Simple majority ratifies |
| concluded | Leader only | Record final conclusion (and Minority Report if dissent exists), export Investigation Report |

## Entry Formats

### Framing

Structured fields in each member's `### {name}` Framing subsection (no entry IDs):

```markdown
- **Problem**: {interpretation of the bug}
- **Reproduction**: {steps to reproduce / environment / observed vs. expected behavior}
- **Constraints**: {known limitations or boundaries of the investigation}
- **Criteria**: {what constitutes a confirmed root cause}
- **Unknowns**: {open questions that need investigation}
```

### Evidence

**ID format:** `[E-{initial}-{seq}]` — `{initial}` = first letter of name (uppercase); `{seq}` = 001, 002, ...

Each evidence entry MUST include:
- **Source**: `file:line` reference (or log file / external source with timestamp)
- **Type**: one of `code-inspection | log-analysis | test-result | config-review | git-history`
- **Snippet**: at most 5 lines of the relevant content
- **Relevance**: explanation of why this evidence is significant to the bug

**Positive evidence example:**

```markdown
- [E-S-001] **evidence**
  - Source: `src/cache/lru.ts:142`
  - Type: code-inspection
  - Snippet:
    ```ts
    if (this.size > this.maxSize) {
      this.evict(); // evicts LRU entry
    }
    ```
  - Relevance: Eviction is triggered after insertion, not before. This means the cache can momentarily exceed maxSize, which may cause the observed memory spike.
```

**Negative evidence** (evidence that rules something out) uses the `**negative-evidence**` label:

```markdown
- [E-S-002] **negative-evidence**
  - Source: `src/cache/lru.ts:89`
  - Type: code-inspection
  - Snippet:
    ```ts
    constructor(maxSize: number) {
      this.maxSize = maxSize;
    }
    ```
  - Relevance: maxSize is set correctly at construction time. Rules out misconfiguration of the cache limit as a cause.
```

### Hypothesis

**ID format:** `[H-{initial}-{seq}]` — `{initial}` = first letter of name (uppercase); `{seq}` = 001, 002, ...

Every hypothesis MUST include all three required fields and an evidence chain:

```markdown
- [H-S-001] **hypothesis**: LRU cache eviction occurs after insertion rather than before, causing transient size exceedance and memory pressure.
  - **Cause mechanism**: `lru.ts:142` checks size and evicts only after the new entry is inserted. During the window between insertion and eviction, cache size is `maxSize + 1`, triggering the allocator's emergency GC path.
  - **Predicted evidence**: `src/allocator/gc.ts` should contain an emergency GC trigger condition referencing a threshold exceeded by `maxSize + 1`.
  - **Falsification condition**: If `gc.ts` emergency GC threshold is set higher than `maxSize + 1`, or if eviction is confirmed to occur before insertion in all code paths, this hypothesis is disproved.
  - **Evidence chain**:
    - Supporting [high]: refs=[E-S-001] — directly shows post-insertion eviction at lru.ts:142
    - Counter [medium]: refs=[E-P-003] — log shows GC triggered only every 30s, suggesting emergency path is not taken frequently
    - Unverified: Need to check `src/allocator/gc.ts` threshold value
```

**Quality gate**: Hypotheses without at least one Supporting [high] or two Supporting [medium] are automatically marked `[low-confidence]` and cannot be the sole basis for a Draft Conclusion.

### Critique

**ID format:** `[CR-{initial}-R{round}-{seq}]`

Common mistake: `[CR-P-1-001]` (missing R prefix) → Correct: `[CR-P-R1-001]`

Each critique must include: label (`**challenge**`/`**support**`/`**amend**`/`**question**`), `refs=[...]`, `@{member}`. Critiques targeting hypotheses should also reference relevant evidence entries.

```markdown
#### Round 1
- [CR-P-R1-001] **challenge** @security-expert refs=[H-S-001, E-S-001]: The post-insertion eviction window assumes single-threaded execution. If the cache uses a lock-free structure, multiple threads could insert concurrently, making the transient size much larger than maxSize + 1.
- [CR-A-R1-001] **support** @memory-analyst refs=[H-S-001, E-S-001, E-A-002]: Confirmed the allocator's emergency GC path threshold. refs=[E-A-002] shows it is set at exactly maxSize + 1, consistent with the predicted evidence in H-S-001.
```

### Debate Tally

Leader-only. Updated each synthesize phase. Tracks quantitative challenge/support/amend/question counts per hypothesis.

| Hypothesis | Challenge | Support | Amend | Question | Net (S−C) | Status |
|-----------|-----------|---------|-------|----------|-----------|--------|
| [H-S-001] | 1 | 3 | 1 | 1 | +2 | active |
| [H-P-001] | 3 | 1 | 0 | 2 | −2 | low-confidence |
| [H-A-001] | 0 | 2 | 1 | 1 | +2 | active |

Status rules:
- **active**: net ≥ 0
- **low-confidence**: net < 0, OR hypothesis fails evidence chain quality gate

### Evidence Map (Leader only)

| # | Claim | Support | Counterpoint | Confidence |
|---|-------|---------|--------------|------------|
| 1 | {claim about root cause} | refs=[H-S-001, E-S-001, E-A-002] | refs=[CR-P-R1-001] | high/medium/low |

### Draft Conclusion (Leader only)

```markdown
## Draft Conclusion — Round {N}
**Root Cause**: {Synthesized root cause statement citing entry IDs and evidence.}
**Confidence**: high / medium / low
**Suggested Fix**: {Concrete fix recommendation at file:line level, if determinable.}
**Key claims**: 1, 2, 3 (from Evidence Map)
**Unresolved**: {low-confidence or unaddressed claims, open unverified leads}
```

### Ratification History (Leader only)

```markdown
### Round {N}
| Member | Vote | Reason |
|--------|------|--------|
| {name} | accept / push-back | {brief reason} |
**Result:** {count}/{total} — {ratified | not ratified}
```

### Minority Report (Leader only)

Written only when conclusion is ratified with dissent:

```markdown
**Dissenter(s):** {names}  **Position:** {alternative root cause view}  **Evidence:** refs=[...]
**Leader note:** {why majority view was adopted}
```

### Audit Formats

Two layers of audit are run each round:

**Layer 1 — Code-Specific Verification** (Leader uses Read/Grep tools directly):

| Entry | Code Claim | File:Line | Verification | Verdict |
|-------|-----------|-----------|--------------|---------|
| [H-S-001] | Eviction occurs after insertion at lru.ts:142 | `src/cache/lru.ts:142` | Read file; line 142 confirms post-insertion eviction check | ✅ Match |
| [E-P-003] | Config sets maxSize=500 | `config/cache.json:12` | Read file; line 12 shows maxSize=200, not 500 | ❌ No match |

Verdict rubric:
- ✅ **Match**: Code at cited file:line confirms the claim exactly
- ⚠️ **Partial match**: Code is present but claim is imprecise, incomplete, or the logic is more nuanced
- ❌ **No match**: Code at cited location contradicts or does not support the claim
- ❓ **Cannot verify**: File/line does not exist, is unreadable, or claim is too vague to verify against code

**Layer 2 — General Fact-Checking** (Leader uses Codex CLI):

| Entry | Claim Summary | Verdict | Notes |
|-------|--------------|---------|-------|
| [H-S-001] | {claim} | ✅/⚠️/❌/❓ | {evidence or reason} |

Verdict rubric:
- ✅ **Verified**: Claim is factually accurate based on established knowledge
- ⚠️ **Partially accurate**: Claim contains some truth but is misleading, incomplete, or outdated
- ❌ **Inaccurate**: Claim is factually wrong
- ❓ **Unverifiable**: Claim cannot be verified (insufficient context, or subjective/speculative)

Granularity: one row per hypothesis or evidence entry (by entry ID), not per sentence. Skip opinions, value judgments, and forecasts.

### Completion Report

Members send this via SendMessage after each sub-phase:

```
Entries added: {N}
Key finding: {most important evidence or insight}
Current position: {hypothesis stance or suspicion in one sentence}
Remaining concerns: {description or "none"}
```

### Revision

Members append corrections in their own subsection (append-only — original entry is never modified).

```markdown
- [H-S-001] **revised**: Updated hypothesis based on audit [Round {N}]. {corrected statement}
  > Original: {original claim}. Audit note: {audit note}.
```

### ID Summary

| Type | Format | Section | Phase |
|------|--------|---------|-------|
| Framing | (no ID — structured fields) | Framing | framing |
| Evidence (positive) | `[E-{initial}-{seq}]` | Evidence | evidence-gathering |
| Evidence (negative) | `[E-{initial}-{seq}]` with `**negative-evidence**` label | Evidence | evidence-gathering |
| Hypothesis | `[H-{initial}-{seq}]` | Hypotheses | hypothesize |
| Critique | `[CR-{initial}-R{round}-{seq}]` | Critique → Round N | critique |
| Audit Layer 1 | (no ID — table format) | Audit → Round N → Layer 1 | audit |
| Audit Layer 2 | (no ID — table format) | Audit → Round N → Layer 2 | audit |
| Revision | `[{original-ID}] **revised**` | Evidence, Hypotheses, or Critique | revise |
| Debate Tally | (no ID — table format, leader-only) | SYNTHESIS.md | synthesize |
| Evidence Map | (no ID — table format, leader-only) | SYNTHESIS.md | synthesize |
| Draft Conclusion | (no ID — leader-only) | SYNTHESIS.md | synthesize |
| Ratification History | (no ID — table format, leader-only) | SYNTHESIS.md | ratify |
| Minority Report | (no ID — leader-only) | SYNTHESIS.md | concluded |

Note on Codex advisory: uses fixed initial `X`. Entry IDs: `[E-X-NNN]`, `[H-X-NNN]`, `[CR-X-R{N}-NNN]`. All advisory entries are prefixed with `[advisory]` and are non-voting.

---

# Workflow Layer

## Workflow Overview

| Phase | Leader Action | Member Action | Output | Next Trigger |
|-------|---------------|---------------|--------|--------------|
| setup | Analyze bug report, suggest 4-10 roles, create team + files | — | WHITEBOARD.md + SYNTHESIS.md | Team spawned |
| framing | Broadcast framing instructions with reproduction context requirement | Document bug interpretation, reproduction, constraints in own section | Framing entries | All members report complete AND reproduction context present |
| evidence-gathering | Broadcast evidence-gathering kickoff | Collect evidence entries (E-NNN) in own section | Evidence entries | All members report complete |
| hypothesize | Broadcast hypothesize kickoff | Write structured hypotheses with evidence chain in own section | Hypothesis entries | All members report complete |
| critique | Broadcast critique instructions | Write critiques with labels, refs, and evidence citations | Critique entries | All members report complete |
| audit | Layer 1: verify code claims via Read/Grep; Layer 2: run Codex CLI; write Audit tables | — | WHITEBOARD.md `## Audit → Round {N}` updated | Audit written |
| revise | Broadcast audit findings to affected members | Append corrections in own section (append-only) | Revised entries | All affected members report complete (or skipped if all ✅/❓) |
| synthesize | Read all WHITEBOARD, update Debate Tally, write Evidence Map + Draft Conclusion | — | SYNTHESIS.md updated | Draft written |
| ratify | Broadcast ratify request | Send vote via SendMessage | Ratification History | Majority reached or next round |
| concluded | Write Final Conclusion (+ Minority Report), export Investigation Report | — | Final SYNTHESIS.md + Investigation Report | — |

## Phase Notes

### setup

- Leader suggests 4-10 roles with distinct investigative perspectives (e.g., frontend-engineer, backend-engineer, database-specialist, security-analyst, performance-engineer, qa-engineer, devops-engineer, architect). Choose count based on bug complexity: simple/localized → 4-5, moderate/cross-system → 6-7, complex/systemic → 8-10.
- User approves or modifies roles before team creation.
- Generate a kebab-case `{investigation-id}` from the bug description (e.g., `cache-memory-spike-on-login`).
- Create `docs/investigations/{investigation-id}/WHITEBOARD.md` + `SYNTHESIS.md` using templates (see Reference Layer).
- Ensure `docs/investigations/` is in `.gitignore` (add if missing).
- Each role should have a **Role-specific investigation checklist** — a list of 3-5 items the member should focus on during evidence-gathering and hypothesize phases (modeled after code-review-board's reviewer checklists and scope boundary rules).
- **Optional: codex-investigate pre-injection** — Before creating files, leader runs `codex-investigate` with the bug symptoms. If successful, the output (Root Cause / Impact Scope / Suggested Fix / Confidence) is included in the Bug Report section as prior investigation context.

### framing

- Members use full WHITEBOARD.md Read (file is small at this stage).
- **Reproduction context gate**: Leader reviews framing entries before allowing evidence-gathering to begin. If any member has not provided concrete reproduction steps, leader requests clarification via SendMessage before proceeding.
- Spawn-time prompt must include: (a) the member's **role-specific investigation checklist** (3-5 focus items), and (b) a **few-shot example** (1 pair: good hypothesis vs insufficient hypothesis, ~200-300 tokens) to calibrate output quality.
- Leader combines completion confirmation + evidence-gathering kickoff in 1 broadcast to reduce round-trips.

### evidence-gathering

- Members read all framings via full WHITEBOARD.md Read.
- Each member aims for 2-5 evidence entries, each with full Source/Type/Snippet/Relevance fields.
- Both positive evidence and negative evidence (ruling out causes) are valuable.
- Members should prioritize: code-inspection of cited stack traces → log-analysis of error logs → git-history for recent changes → config-review for misconfiguration → test-result for reproduction attempts.
- Report completion using the completion report format.
- **Cross-boundary investigation permitted**: Members may investigate outside their primary area if they discover relevant leads.

### hypothesize

- **IMPORTANT**: Use 2-step Grep extraction when WHITEBOARD exceeds ~350 lines:
  1. `Grep pattern="## Evidence"` to extract the evidence section
  2. `Grep pattern="### {member-name}"` to narrow to a specific member
- Members read all evidence entries before writing hypotheses.
- Each member aims for 1-3 hypotheses — fewer, better-supported hypotheses are preferred over many speculative ones.
- Every hypothesis MUST include all three required fields (cause mechanism, predicted evidence, falsification condition) and a complete evidence chain. Incomplete hypotheses will be flagged during audit.
- Report completion using the completion report format.

### critique

- **IMPORTANT**: Use 2-step Grep extraction when WHITEBOARD exceeds ~350 lines.
- Members must label each critique: challenge/support/amend/question.
- Cite refs=[] (including evidence IDs) and @member for every entry.
- Round 2+: also read Draft Conclusion in SYNTHESIS.md and Debate Tally.
- Strong critiques should either: (a) cite counter-evidence refs=[E-X-NNN] to challenge a hypothesis, or (b) cite supporting evidence refs=[E-X-NNN] to reinforce a hypothesis.

### audit

- **Layer 1 — Code-Specific Verification**:
  - For every hypothesis and evidence entry that cites a specific `file:line`, leader uses Read tool to retrieve that file section and checks the actual code at the referenced location **±10 lines** (following deep-fix's VALIDATE pattern) to verify the claim.
  - Record results in the Layer 1 table: Entry / Code Claim / File:Line / Verification / Verdict.
  - This layer runs first and may invalidate hypotheses before Layer 2.

- **Layer 2 — General Fact-Checking** (Codex CLI):
  - **Prerequisite:** `codex` CLI must be installed (`npm i -g @openai/codex`). If not available, skip Layer 2, log warning in SYNTHESIS.md status, and proceed to synthesize.
  - **Scope:** Audit only entries from the current round (new hypotheses + new critiques). Do NOT re-audit entries from prior rounds.
  - **Exclusion:** Skip opinions, value judgments, and forecasts — only fact-check verifiable factual claims.
  - Leader collects hypotheses and critiques from current round in WHITEBOARD.md.
  - Leader builds a Codex prompt requesting fact-checking of each claim.
  - Prompt template:

    ```
    Fact-check the following claims from a bug investigation team. For each claim:
    1. Verify if it is factually accurate regarding the technology, language, or system behavior described
    2. Note any inaccuracies, outdated information, or unsupported assertions
    3. Provide brief evidence or references for your assessment
    4. Skip opinions, value judgments, and forecasts — mark them as ❓ Unverifiable

    Rate each claim: ✅ Verified / ⚠️ Partially accurate / ❌ Inaccurate / ❓ Unverifiable

    Claims:
    {hypotheses and critique claims from current round}
    ```

  - Execute via temp file + stdin:
    ```bash
    TMPFILE=$(mktemp)
    cat <<'PROMPT_EOF' > "$TMPFILE"
    <constructed_prompt>
    PROMPT_EOF
    cat "$TMPFILE" | codex exec
    rm -f "$TMPFILE"
    ```

  - Write results to WHITEBOARD.md `## Audit` → `### Round {N}` subsection (append-only, each round gets its own subsection with Layer 1 and Layer 2 sub-subsections).

- **Error handling:**
  - Layer 1: File not found or unreadable → record "Cannot verify (file not found)" with ❓ verdict
  - Layer 2: Codex exits non-zero or times out → record "Audit failed (Codex error)" in `### Round {N} → Layer 2`, skip Layer 2 revise, proceed with Layer 1 results only
  - Layer 2: Codex returns partial/malformed output → leader writes available results, marks incomplete entries as ❓

- **Decision logic:**
  - All ✅ or ❓ across both layers → skip `revise`, proceed to `synthesize`
  - Any ⚠️ or ❌ in either layer → proceed to `revise`

### revise

- Only runs when audit found ⚠️ Partially accurate or ❌ Inaccurate / No match entries in either layer.
- Leader broadcasts audit results and instructs affected members to review and correct their entries.
- Members **append** corrections in their own `### {name}` subsection under the relevant section. Original entries are NEVER modified (append-only).
- Revision format:

  ```markdown
  - [H-S-001] **revised**: Updated hypothesis based on audit [Round {N}]. {corrected statement}
    > Original: {original claim}. Audit note: {audit note}.
  ```

- Members report completion via SendMessage using the standard completion report format.
- After all affected members report: proceed to `synthesize`.
- **Max 1 revise round per audit** — no recursive auditing of revisions.
- **Unresolved ❌ after revise:** Leader notes unresolved inaccuracies in the Evidence Map (synthesize phase) with low confidence rating. These are visible during ratification.

### synthesize

- Leader reads ALL WHITEBOARD.md content (framing, evidence, hypotheses, all critiques, audit results).
- Updates Debate Tally (challenge/support/amend/question counts, net score, status) in SYNTHESIS.md.
- Writes Evidence Map + Draft Conclusion in SYNTHESIS.md.
- Draft Conclusion must include Root Cause, Confidence, Suggested Fix, Key claims, and Unresolved items.
- Round 2+: add entry ID → summary mapping table in SYNTHESIS.md for members to reference efficiently.
- Guideline: "When in doubt about summary accuracy, members should Grep original text."
- **Information loss prevention**: Leader must list hypotheses NOT reflected in conclusion with exclusion reasons.

### ratify

- Votes via SendMessage (NOT file writes): `RATIFY: accept — {reason}` or `RATIFY: push-back — {concerns}`
- Simple majority: ⌊N/2⌋ + 1 required to ratify.
- If not ratified and rounds remain: incorporate push-back, start next critique round.

### concluded

- Leader exports Final Conclusion as an Investigation Report to `docs/reports/YYYY-MM-DD-{investigation-id}-report.md` (see Investigation Report Template in Reference Layer).
- Verify the Investigation Report file was created successfully.
- Delete `docs/investigations/{investigation-id}/` directory after successful export.
- If investigation was interrupted (no Final Conclusion): skip Investigation Report export, delete investigation directory manually.

## Communication Rules

- All leader → member instructions via **broadcast** (NOT individual SendMessage).
- Use structured short format: Phase / Round / Action / Format-ref (~80-120 tokens).
- Combine phase transitions: completion confirmation + next phase instruction in 1 broadcast.

---

# Reference Layer

## WHITEBOARD.md Template

Path: `docs/investigations/{investigation-id}/WHITEBOARD.md`

```markdown
# WHITEBOARD — {investigation-id}
> Bug: {bug description}
> Created: {YYYY-MM-DD}
> Team: {comma-separated names}

## Bug Report

{Clear description of the bug. Include symptoms, error messages, stack traces, affected components.}

### Reproduction Context

{Minimal reproduction steps. Environment, preconditions, input, expected behavior, actual behavior.}

### Prior Investigation (codex-investigate)

{Output from codex-investigate if available, or "(No prior investigation)" if not run.}

## How Our Work Connects
{Each member's role and investigative perspective.}

<!-- Repeat ### {member-name} subsections for each team member (4-10 members) -->
## Framing
### {member-A}
### {member-B}
### {member-C}
### {member-D}
<!-- ... up to {member-J} depending on team size -->

## Evidence
### {member-A}
### {member-B}
### {member-C}
### {member-D}
<!-- ... up to {member-J} depending on team size -->
### codex

## Hypotheses
### {member-A}
### {member-B}
### {member-C}
### {member-D}
<!-- ... up to {member-J} depending on team size -->
### codex

## Critique
### {member-A}
### {member-B}
### {member-C}
### {member-D}
<!-- ... up to {member-J} depending on team size -->
### codex

## Audit
```

No Status/Round header in WHITEBOARD — managed in SYNTHESIS.md. Sections start empty. See Entry Formats above for content structure.

## SYNTHESIS.md Template

Path: `docs/investigations/{investigation-id}/SYNTHESIS.md`

```markdown
# SYNTHESIS — {investigation-id}
> Status: setup
> Round: 0
> Max Rounds: 10

## Debate Tally
## Evidence Map
## Draft Conclusion
## Ratification History
## Minority Report
## Final Conclusion
```

Leader-only file. See Entry Formats above for section content structure.

## Investigation Report Template

Path: `docs/reports/YYYY-MM-DD-{investigation-id}-report.md`

Exported by leader during `concluded` phase. This is the permanent record of the investigation outcome.

```markdown
# {Bug Description} — Investigation Report

> Date: {YYYY-MM-DD}
> Status: Concluded ({accept_count}/{total} {unanimous/majority})
> Method: Investigation Board ({N}-member structured investigation)

## Summary
{Root cause summary — 2-3 sentences}

## Bug Report
{Bug description + reproduction context + impact}

## Root Cause
{Detailed root cause statement citing key evidence IDs. Structure with subsections as needed.}

## Confidence
{high / medium / low — with justification}

## Suggested Fix
{Concrete fix recommendation at file:line level}

## Key Evidence
{Top 3-5 evidence entries that were decisive}

## Investigation Artifacts
- Team: {comma-separated member names}
- Evidence entries: {count}, Hypotheses: {count}, Critiques: {count}
- Ratification: Round {N}, {accept_count}/{total}
- Unresolved: {any remaining open questions}
```

Note: This is an investigation report, not an implementation plan. To create an executable fix plan, use `superpowers:writing-plans` with this report as input.

## Ratification Rules

| Members | Majority Threshold |
|---------|-------------------|
| 4 | 3 |
| 5 | 3 |
| 6 | 4 |
| 7 | 4 |
| 8 | 5 |
| 9 | 5 |
| 10 | 6 |

- **Max rounds**: 10 (configurable at investigation creation)
- **Vote format**: `RATIFY: accept — {reason}` or `RATIFY: push-back — {concerns}` via SendMessage
- **Exhaustion**: If max rounds reached with no majority, leader writes "best available conclusion" with explicit uncertainty markers
- **Abstention**: Not permitted. Every member must vote each round.
- **Vote supersession**: A member's vote in round N supersedes prior rounds.

## Conflict Prevention Rules

| # | Rule | Rationale |
|---|------|-----------|
| 1 | Each teammate edits only their own `### {name}` subsection in WHITEBOARD.md | Prevents Edit tool match failures from concurrent writes |
| 2 | SYNTHESIS.md is leader-only (teammates read, never write) | Single writer eliminates conflicts |
| 3 | Append-only writes (no deletion/modification of existing entries) | Prevents overwrites from stale reads |
| 4 | Ratification votes via SendMessage, not file writes | Eliminates race conditions on vote tallying |
| 5 | Phase transitions are leader-controlled via broadcast | Clear boundaries prevent out-of-order writes |
| 6 | `## Audit` section is leader-only (structural exception to per-member rule, same pattern as SYNTHESIS.md) | Single writer; audit results managed by leader |
| 7 | Revisions are append-only in member's own subsection; original entries are never modified | Maintains append-only invariant from Core Principle #6 |
| 8 | Debate Tally is leader-only in SYNTHESIS.md | Single writer; quantitative tally requires consistent state |
| 9 | `### codex` subsection is leader-only (leader writes on Codex's behalf) | Same pattern as Audit rule |
| 10 | Evidence gathering uses Read/Grep/Glob (read-only tools) — no file modifications during investigation | Read-only tools cannot conflict with write zones |

## Audit Notes

- **Layer 1 prerequisite:** Read/Grep tools available in all Claude Code environments. Always runs.
- **Layer 2 prerequisite:** `codex` CLI must be installed (`npm i -g @openai/codex`). If unavailable, skip Layer 2, record warning in SYNTHESIS.md status line, and proceed to synthesize with Layer 1 results only.
- **Do NOT audit opinions or forecasts** — only verifiable factual claims and code references
- **Audit is incremental** — each round audits only new entries, not the full history
- **Revisions are append-only** — never edit the original hypothesis, evidence, or critique text
- **Layer 1 takes precedence** — if a code claim fails Layer 1 verification, it is flagged regardless of Layer 2 outcome

## Codex Advisory Member

### Prerequisites

`codex` CLI must be installed (`npm i -g @openai/codex`). If unavailable, skip all Codex advisory steps with "(Codex advisory skipped: CLI not found)".

### Workflow

Leader waits for all voting members to complete their phase entries → reads WHITEBOARD.md → constructs prompt from template → runs `codex exec` → writes verbatim output to the `### codex` subsection in the relevant WHITEBOARD section.

### Hypothesize Prompt Template

```
You are an advisory member in a structured bug investigation. The team is investigating the following bug:

{bug description and reproduction context}

The team's evidence and existing hypotheses are below. Generate 2-3 novel hypotheses that the team has NOT already proposed. Each hypothesis must be concrete, testable, and grounded in the evidence collected.

Use this exact ID format: [H-X-001], [H-X-002], etc.

Format each hypothesis as:
- [H-X-NNN] **hypothesis**: {concrete claim about root cause}
  > **Cause mechanism**: {causal chain}
  > **Predicted evidence**: {what to look for in the codebase}
  > **Falsification condition**: {what would disprove this}
  > **Evidence chain**:
  >   - Supporting [{strength}]: {evidence reference or description}
  >   - Counter [{strength}]: {counter-evidence or "none found"}
  >   - Unverified: {unverified assumptions}

Existing content:
{evidence + hypotheses from WHITEBOARD.md}
```

### Critique Prompt Template

```
You are an advisory member in a structured bug investigation. The team is investigating the following bug:

{bug description and reproduction context}

Review the hypotheses and existing critiques below. Write 2-4 critiques that fill gaps. Each critique must target a specific hypothesis using refs=[] and @codex.

Use this exact ID format: [CR-X-R{round}-001], [CR-X-R{round}-002], etc.
Label: **challenge**, **support**, **amend**, or **question**.
Reference evidence entries [E-X-NNN] where possible.

Existing content:
{evidence + hypotheses + critiques from WHITEBOARD.md}
```

### Revise Prompt Template

Same as discussion-board's revise prompt template.

### Invocation Pattern

Temp file + stdin:

```bash
TMPFILE=$(mktemp)
cat <<'PROMPT_EOF' > "$TMPFILE"
<constructed_prompt>
PROMPT_EOF
cat "$TMPFILE" | codex exec
rm -f "$TMPFILE"
```

### Verbatim Copy Rule

Leader MUST copy Codex output verbatim to the `### codex` subsection. Only ID prefix corrections are allowed (e.g., fixing `[H-1-001]` to `[H-X-001]`).

### Error Handling

| Situation | Action |
|-----------|--------|
| CLI not found | Skip Codex advisory with "(Codex advisory skipped: CLI not found)" |
| Empty output | Note "(Codex returned empty output)" in `### codex` subsection |
| Malformed IDs | Prepend correct ID format (e.g., `[H-X-NNN]`) before writing |
| Non-zero exit | Skip with "(Codex advisory skipped: exit code {N})" |
| Timeout (>2min) | Skip with "(Codex advisory skipped: timeout exceeded)" |

### Budget

Max 3 Codex CLI calls per round, 2-minute timeout per call.

## Timeout Policy

| Situation | Action |
|-----------|--------|
| Member has not reported completion | Leader sends one reminder via SendMessage |
| After reminder, still no response | Leader proceeds with available results (partial round) |
| Missing ratification vote | Recorded as "not submitted"; threshold recalculated as ⌊voting_count/2⌋ + 1 |
