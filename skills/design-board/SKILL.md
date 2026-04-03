---
name: design-board
description: >-
  Implementation design via 2-phase structured team debate.
  Phase 1 investigates technology choices, Phase 2 designs the implementation.
  Outputs a single Plan File with architecture background.
  Triggers: design board, implementation plan, 設計, 実装計画, 実装設計
---

# Design Board — 2-Phase Implementation Design via Team Debate

Produce a concrete implementation plan through structured 2-phase team debate: Phase 1 (Technical Investigation) explores technology choices, Phase 2 (Design) creates the implementation design. Uses TeamCreate + SendMessage + AskUserQuestion.

## When to Use

- The task requires designing an implementation plan with technology selection and architectural decisions
- Keywords: "design board", "implementation plan", "設計", "実装計画", "実装設計"

## When NOT to Use

- Use `discussion-board` for open-ended exploration without implementation focus
- Use `decision-board` when the user provides explicit candidate options

## Core Principles

1. **Design-centric** — All activity targets producing an actionable implementation plan.
2. **2-phase model** — Phase 1 (Technical Investigation) narrows technology choices; Phase 2 (Design) produces the implementation plan. Each phase has its own WHITEBOARD.md + SYNTHESIS.md in separate subdirectories.
3. **2-file model per phase** — WHITEBOARD.md (framing + hypotheses + critiques) + SYNTHESIS.md (leader-managed state), in `docs/discussions/{discussion-id}/phase-{N}/`.
4. **Per-member write zones** — Each teammate writes only to their own `### {name}` subsection in WHITEBOARD.md.
5. **Leader-only SYNTHESIS.md** — Teammates read but never write to SYNTHESIS.md.
6. **Append-only** — Teammates add content, never delete or modify existing entries.
7. **Leader as synthesizer, not participant** — Leader does NOT write hypotheses or critiques. Leader MAY write process artifacts (audit results, evidence maps, conclusions).
8. **Structured phase handoff** — Phase 1 SYNTHESIS.md is the mandatory context injection source for Phase 2. Leader pushes Phase 1 conclusions via broadcast at Phase 2 framing start.

## Phase Model

```
setup → [Phase 1: framing → hypothesize → critique → synthesize] → user-review → [Phase 2: framing → [Round N: hypothesize → critique → audit → revise (if needed) → synthesize → ratify] ] → concluded
```

### Phase 1 — Technical Investigation (4 steps)

| Step | Who | What |
|------|-----|------|
| framing | All members | Document problem interpretation, technology constraints, evaluation criteria, unknowns |
| hypothesize | All members | Propose concrete technology choices, library candidates, architecture patterns |
| critique | All members | Challenge/support/amend/question hypotheses with cross-references |
| synthesize | Leader only | Read all content, write Evidence Map + Technology Conclusion in SYNTHESIS.md |

Phase 1 does NOT include audit, revise, or ratify. The user-review step after Phase 1 serves as the ratification gate.

### User Review

Leader presents Phase 1 conclusions to the user via AskUserQuestion:
- Include: selected technologies, key trade-offs, rejected alternatives with reasons
- User choices: "Proceed to Phase 2" or "Provide feedback on the technology selections"
- If user provides feedback: Leader records feedback in phase-1/SYNTHESIS.md `## User Review Outcome`, then incorporates it as additional constraints for Phase 2 framing. Phase 1 files are NOT re-executed — feedback adjusts Phase 2's starting constraints only.
- No skip option — user confirmation is mandatory

### Phase 2 — Design (6 steps + conditional revise)

| Step | Who | What |
|------|-----|------|
| framing | All members | Document design constraints, scope, acceptance criteria (informed by Phase 1 conclusions) |
| hypothesize | All members | Propose concrete implementation designs: file structure, APIs, data models |
| critique | All members | Challenge/support/amend/question designs with cross-references |
| audit | Leader only | Run Codex CLI to fact-check claims from current round |
| revise | All members (conditional) | Append corrections if audit found inaccuracies (skipped if all clean) |
| synthesize | Leader only | Read all content, write Evidence Map + Draft Design in SYNTHESIS.md |
| ratify | All voting members | Vote accept or push-back via SendMessage. Simple majority ratifies |

## Entry Formats

### Framing

Structured fields in each member's `### {name}` Framing subsection (no entry IDs):

**Phase 1 framing:**
```markdown
- **Problem**: {interpretation of the design challenge}
- **Technology Constraints**: {known platform/stack/compatibility requirements}
- **Evaluation Criteria**: {what makes a good technology choice}
- **Unknowns**: {open questions about technology landscape}
```

**Phase 2 framing:**
```markdown
- **Scope**: {what this design covers}
- **Constraints**: {from Phase 1 conclusions + user feedback}
- **Acceptance Criteria**: {what makes a good implementation design}
- **Unknowns**: {open questions about implementation}
```

### Hypothesis

**ID format:** `[H-{phase}-{initial}-{seq}]` — `{phase}` = 1 or 2; `{initial}` = first letter of name (uppercase); `{seq}` = 001, 002, ...

**Phase 1 example (technology choice):**
```markdown
- [H-1-S-001] **hypothesis**: Use SQLite with WAL mode for local persistence over IndexedDB.
  > Rationale: SQLite offers ACID transactions and SQL query flexibility; WAL mode supports concurrent reads.
```

**Phase 2 example (implementation design):**
```markdown
- [H-2-A-001] **hypothesis**: Implement a repository pattern with SQLite adapter behind an interface for storage abstraction.
  > Rationale: Allows swapping storage backends without touching business logic. Interface: `StorageRepository { get, put, list, delete }`.
```

### Critique

**ID format:** `[CR-{phase}-{initial}-R{round}-{seq}]`

Common mistake: `[CR-2-P-1-001]` (missing R prefix) → Correct: `[CR-2-P-R1-001]`

Each critique must include: label (`**challenge**`/`**support**`/`**amend**`/`**question**`), `refs=[...]`, `@{member}`

```markdown
#### Round 1
- [CR-1-P-R1-001] **challenge** @storage-expert refs=[H-1-S-001]: SQLite binary size adds ~2MB to the bundle. For a browser extension use case, this exceeds the store limit.
```

### Evidence Map (Leader only)

| # | Claim | Support | Counterpoint | Confidence |
|---|-------|---------|--------------|------------|
| 1 | {claim} | refs=[H-2-X-001, CR-2-Y-R1-002] | refs=[CR-2-Z-R1-001] | high/medium/low |

### Draft Conclusion (Leader only)

**Phase 1 — Technology Conclusion:**
```markdown
## Technology Conclusion
**Selected:** {technology/pattern choices with rationale}
**Rejected:** {alternatives with reasons}
**Trade-offs:** {key trade-offs accepted}
**Open questions for Phase 2:** {items to resolve during design}
```

**Phase 2 — Draft Design:**
```markdown
## Draft Design — Round {N}
{Synthesized implementation design citing entry IDs. Mark areas of uncertainty.}
**Key claims:** 1, 2, 3 (from Evidence Map)
**Unresolved:** {low-confidence or unaddressed claims}
```

### Ratification History (Leader only, Phase 2 only)

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
**Dissenter(s):** {names}  **Position:** {view}  **Evidence:** refs=[...]
**Leader note:** {why majority view was adopted}
```

### Completion Report

Members send this via SendMessage after each sub-phase:

```
Entries added: {N}
Key insight: {most important finding}
Current position: {stance in one sentence}
Remaining concerns: {description or "none"}
```

### Audit (Phase 2 only)

Leader-only. Written per round after Codex CLI fact-check. Only factual claims are audited — opinions, value judgments, and forecasts are excluded.

| Entry | Claim Summary | Verdict | Notes |
|-------|--------------|---------|-------|
| [H-2-S-001] | {claim} | ✅/⚠️/❌/❓ | {evidence or reason} |

Verdict rubric:
- ✅ **Verified**: Claim is factually accurate based on established knowledge
- ⚠️ **Partially accurate**: Claim contains some truth but is misleading, incomplete, or outdated
- ❌ **Inaccurate**: Claim is factually wrong
- ❓ **Unverifiable**: Claim cannot be verified (insufficient context, or subjective/speculative)

Granularity: one row per hypothesis or critique entry (by entry ID), not per sentence.

### Revision (Phase 2 only)

Members append corrections in their own subsection (append-only — original entry is never modified).

- [H-2-S-001] **revised**: Updated claim based on audit [Round {N}]. {corrected statement}
  > Original: {original claim}. Audit note: {audit note}.

### ID Summary

| Type | Format | Section | Phase |
|------|--------|---------|-------|
| Framing | (no ID — structured fields) | Framing | framing (both phases) |
| Hypothesis | `[H-{phase}-{initial}-{seq}]` | Hypotheses | hypothesize (both phases) |
| Critique | `[CR-{phase}-{initial}-R{round}-{seq}]` | Critique → Round N | critique (both phases) |
| Audit | (no ID — table format) | Audit → Round N | audit (Phase 2 only) |
| Revision | `[{original-ID}] **revised**` | Hypotheses or Critique | revise (Phase 2 only) |

Note: `{phase}` = 1 or 2 to ensure IDs are globally unique across phases. `-cx` members use their normal member's initial + `X`. Example: backend → `B`, backend-cx → `BX`. Entry IDs: `[H-1-BX-001]`.

---

# Workflow Layer

## Workflow Overview

### Phase 1 — Technical Investigation

| Step | Leader Action | Member Action | Output | Next Trigger |
|------|---------------|---------------|--------|--------------|
| setup | Invoke team-composer, create phase files, spawn members | — | phase-1/ + phase-2/ WHITEBOARD.md + SYNTHESIS.md | Team spawned |
| framing | Broadcast framing instructions | Document understanding in own section | Framing entries | All members report complete |
| hypothesize | Broadcast kickoff | Write hypotheses in own section | Hypothesis entries | All members report complete |
| critique | Broadcast instructions | Write critiques with labels + refs | Critique entries | All members report complete |
| synthesize | Read all WHITEBOARD, write Evidence Map + Technology Conclusion | — | phase-1/SYNTHESIS.md updated | Conclusion written |

### User Review

| Step | Leader Action | Output | Next Trigger |
|------|---------------|--------|--------------|
| user-review | Present Phase 1 Technology Conclusion via AskUserQuestion | User approval or feedback | User responds |

### Phase 2 — Design

| Step | Leader Action | Member Action | Output | Next Trigger |
|------|---------------|---------------|--------|--------------|
| framing | Broadcast Phase 1 conclusions + framing instructions | Document design constraints in own section | Framing entries | All members report complete |
| hypothesize | Broadcast kickoff | Write design hypotheses in own section | Hypothesis entries | All members report complete |
| critique | Broadcast instructions | Write critiques with labels + refs | Critique entries | All members report complete |
| audit | Run Codex CLI on current round's claims, write Audit table | — | phase-2/WHITEBOARD.md `## Audit → Round {N}` updated | Audit written |
| revise | Broadcast audit findings to affected members | Append corrections (append-only) | Revised entries | All affected complete (or skipped if all clean) |
| synthesize | Read all WHITEBOARD, write Evidence Map + Draft Design | — | phase-2/SYNTHESIS.md updated | Draft written |
| ratify | Broadcast ratify request to voting members | Send vote via SendMessage | Ratification History | Majority reached or next round |

### Concluded

| Step | Leader Action | Output |
|------|---------------|--------|
| concluded | Generate Plan File, delete discussion directory | `docs/plans/YYYY-MM-DD-{topic}.md` |

## Phase Notes

### setup

- Invoke `forte:team-composer` with:
  - `topic`: the design topic
  - `team_name`: generate a kebab-case `{discussion-id}` from the design topic (e.g., `auth-system-design`)
  - `role_count`: `"3-6"`
- Roles should cover both technology evaluation AND implementation design perspectives (same team serves both phases).
- After team-composer completes (Handoff Contract received):
  - Create `docs/discussions/{discussion-id}/phase-1/WHITEBOARD.md` + `SYNTHESIS.md` using templates.
  - Create `docs/discussions/{discussion-id}/phase-2/WHITEBOARD.md` + `SYNTHESIS.md` using templates.
  - Ensure `docs/discussions/` is in `.gitignore` (add if missing).
  - Spawn all members with design-board-specific prompts:
    - Normal members: standard design discussion prompt.
    - `-cx` members: same prompt + codex exec exploration template (see team-composer skill for template).

### Phase 1: framing

- Members use full WHITEBOARD.md Read (file is small, ~100 lines at this stage).
- Leader combines completion confirmation + hypothesize kickoff in 1 broadcast to reduce round-trips.
- Framing should focus on technology landscape, constraints, and evaluation criteria.

### Phase 1: hypothesize

- Members read all framings via full WHITEBOARD.md Read (~200 lines at this stage).
- Each member aims for 2-5 hypotheses about technology choices, library candidates, or architecture patterns.
- Report completion using the completion report format.

### Phase 1: critique

- **IMPORTANT**: Use 2-step Grep extraction when WHITEBOARD exceeds ~350 lines.
- Members must label each critique: challenge/support/amend/question.
- Cite refs=[] and @member for every entry.

### Phase 1: synthesize

- Leader reads ALL phase-1/WHITEBOARD.md content.
- Writes Evidence Map + Technology Conclusion in phase-1/SYNTHESIS.md.
- Technology Conclusion must clearly state: selected technologies, rejected alternatives, key trade-offs, and open questions for Phase 2.

### user-review

- Leader reads phase-1/SYNTHESIS.md Technology Conclusion.
- Presents to user via AskUserQuestion with structured summary:
  ```
  Phase 1 (Technical Investigation) is complete.

  **Selected technologies:**
  {bullet list of selected technologies with brief rationale}

  **Key trade-offs:**
  {bullet list of accepted trade-offs}

  **Rejected alternatives:**
  {bullet list with reasons}

  Options:
  1. Proceed to Phase 2 (Design) with these technology choices
  2. Provide feedback on the technology selections (will be incorporated as Phase 2 constraints)
  ```
- Leader records the user's response in phase-1/SYNTHESIS.md `## User Review Outcome` (approved / feedback provided).
- If user provides feedback: record feedback verbatim in `## User Review Outcome`, then incorporate as additional constraints in Phase 2 framing broadcast. Phase 1 files are NOT re-executed.

### Phase 2: framing

- **Context injection (Push-based):** Leader reads phase-1/SYNTHESIS.md, extracts Technology Conclusion, and includes it in the framing broadcast to all members. Members do NOT need to read phase-1/ files directly.
- If user provided feedback during user-review, include it as additional constraints.
- Framing should focus on implementation scope, design constraints, and acceptance criteria.

### Phase 2: hypothesize

- Members read all Phase 2 framings via full WHITEBOARD.md Read.
- Hypotheses should propose concrete implementation designs: file structure, APIs, data models, component boundaries.
- Report completion using the completion report format.

### Phase 2: critique

- Same rules as Phase 1 critique.

### Phase 2: audit

- **Prerequisite:** `codex` CLI must be installed (`npm i -g @openai/codex`). If not available, skip audit phase entirely, log warning in SYNTHESIS.md status, and proceed to synthesize.
- **Scope:** Audit only entries from the current round. Do NOT re-audit entries from prior rounds.
- **Exclusion:** Skip opinions, value judgments, and forecasts — only fact-check verifiable factual claims.
- Leader collects hypotheses and critiques from current round in WHITEBOARD.md.
- Leader builds a Codex prompt requesting fact-checking of each claim.
- Prompt template:

  ```
  Fact-check the following claims from a team discussion about implementation design. For each claim:
  1. Verify if it is factually accurate
  2. Note any inaccuracies, outdated information, or unsupported assertions
  3. Provide brief evidence or references for your assessment
  4. Skip opinions, value judgments, and forecasts — mark them as Unverifiable

  Rate each claim: Verified / Partially accurate / Inaccurate / Unverifiable

  Claims:
  {hypotheses and critique claims from current round}
  ```

- Execute via temp file + stdin:
  ```bash
  TMPFILE=$(mktemp)
  cat <<'PROMPT_EOF' > "$TMPFILE"
  <constructed_prompt>
  PROMPT_EOF
  cat "$TMPFILE" | codex exec --ephemeral -m gpt-5.3-codex
  rm -f "$TMPFILE"
  ```

- Write results to phase-2/WHITEBOARD.md `## Audit` → `### Round {N}` subsection.

- **Error handling:**
  - Codex exits non-zero or times out → record "Audit failed (Codex error)" in `### Round {N}`, skip revise, proceed to synthesize with warning
  - Codex returns partial/malformed output → leader writes available results, marks incomplete entries as ❓

- **Decision logic:**
  - All ✅ or ❓ only → skip `revise`, proceed to `synthesize`
  - Any ⚠️ or ❌ → proceed to `revise`

### Phase 2: revise

- Only runs when audit found ⚠️ or ❌ entries.
- Leader broadcasts audit results and instructs affected members to review and correct their entries.
- Members **append** corrections in their own `### {name}` subsection (append-only).
- **Max 1 revise round per audit** — no recursive auditing of revisions.
- **Unresolved ❌ after revise:** Leader notes unresolved inaccuracies in the Evidence Map with low confidence rating.

### Phase 2: synthesize

- Leader reads ALL phase-2/WHITEBOARD.md content.
- Writes Evidence Map + Draft Design in phase-2/SYNTHESIS.md.
- Round 2+: add entry ID → summary mapping table for members to reference efficiently.

### Phase 2: ratify

- Votes via SendMessage (NOT file writes): `RATIFY: accept — {reason}` or `RATIFY: push-back — {concerns}`
- Simple majority: ⌊N/2⌋ + 1 required to ratify.
- If not ratified and rounds remain: incorporate push-back concerns into next round. Next round starts at `critique` (members write new critiques addressing push-back concerns, then audit → revise → synthesize → ratify).
- If not ratified and max rounds exhausted: leader writes "best available design" in `## Final Design` with explicit uncertainty markers.

### concluded

- Leader writes `## Final Design` in phase-2/SYNTHESIS.md by promoting the ratified Draft Design (or best available design on exhaustion).
- Leader generates the Plan File at `docs/plans/YYYY-MM-DD-{topic}.md` (see Plan File Template in Reference Layer).
- Content is derived from both phase-1/SYNTHESIS.md (technology background) and phase-2/SYNTHESIS.md (implementation design).
- Verify the Plan File was created successfully.
- Delete `docs/discussions/{discussion-id}/` directory after successful export.
- If discussion was interrupted (no Final Design): skip Plan File export, delete discussion directory manually.

## Communication Rules

- All leader → member instructions via **broadcast** (NOT individual SendMessage).
- Use structured short format: Phase / Step / Action / Format-ref (~80-120 tokens).
- Combine phase transitions: completion confirmation + next phase instruction in 1 broadcast.
- Phase 2 framing broadcast MUST include Phase 1 Technology Conclusion summary (Push-based context injection).

---

# Reference Layer

## WHITEBOARD.md Templates

### Phase 1 WHITEBOARD

Path: `docs/discussions/{discussion-id}/phase-1/WHITEBOARD.md`

```markdown
# WHITEBOARD — {discussion-id} / Phase 1: Technical Investigation
> Topic: {design topic}
> Created: {YYYY-MM-DD}
> Team: {comma-separated names}

## Topic
{Clear statement of the design challenge. Include context and motivation.}

## How Our Work Connects
{Each member's role and perspective.}

## Framing
<!-- Repeat ### {member-name} subsections for each team member -->
### {member-A}
### {member-B}
...

## Hypotheses
<!-- Repeat ### {member-name} subsections for each team member -->
### {member-A}
### {member-B}
...

## Critique
<!-- Repeat ### {member-name} subsections for each team member -->
### {member-A}
### {member-B}
...
```

### Phase 2 WHITEBOARD

Path: `docs/discussions/{discussion-id}/phase-2/WHITEBOARD.md`

```markdown
# WHITEBOARD — {discussion-id} / Phase 2: Design
> Topic: {design topic}
> Created: {YYYY-MM-DD}
> Team: {comma-separated names}

## Topic
{Clear statement of the design challenge. Include context and motivation.}

## How Our Work Connects
{Each member's role and perspective.}

## Framing
<!-- Repeat ### {member-name} subsections for each team member -->
### {member-A}
### {member-B}
...

## Hypotheses
<!-- Repeat ### {member-name} subsections for each team member -->
### {member-A}
### {member-B}
...

## Critique
<!-- Repeat ### {member-name} subsections for each team member -->
### {member-A}
### {member-B}
...

## Audit
```

No Status/Round header in WHITEBOARD — managed in SYNTHESIS.md. Sections start empty. Phase 1 has no `## Audit` section (audit is Phase 2 only).

## SYNTHESIS.md Template

Path: `docs/discussions/{discussion-id}/phase-{N}/SYNTHESIS.md`

**Phase 1:**
```markdown
# SYNTHESIS — {discussion-id} / Phase 1: Technical Investigation
> Status: setup

## Evidence Map
## Technology Conclusion
## User Review Outcome
```

**Phase 2:**
```markdown
# SYNTHESIS — {discussion-id} / Phase 2: Design
> Status: setup
> Round: 0
> Max Rounds: 10

## Evidence Map
## Draft Design
## Ratification History
## Minority Report
## Final Design
```

Leader-only files. See Entry Formats above for section content structure.

## Plan File Template

Path: `docs/plans/YYYY-MM-DD-{topic}.md`

Exported by leader during `concluded` phase. This is the permanent record of the design board outcome.

```markdown
# {Topic}

> Date: {YYYY-MM-DD}
> Status: Approved ({accept_count}/{total} {unanimous/majority})
> Method: Design Board ({N}-member 2-phase structured debate)

## Goal
{1-2 sentence summary of what this plan achieves}

## Architecture Background
{Technology selections from Phase 1 with rationale. Key trade-offs. Rejected alternatives.}

## Tech Stack
{Bullet list of selected technologies/libraries/patterns}

## File Tree
{Tree view of files to be created or modified}

## Files
{For each file: path, description of changes, and relevant code snippets}

## Chunk 1: {chunk-title}
- [ ] Step description
- [ ] Step description

## Chunk 2: {chunk-title}
- [ ] Step description
- [ ] Step description

## Design Decisions
{Key design decisions from Phase 2 with rationale. Include acceptance criteria and constraints.}

## Unresolved Items
{Low-confidence claims, open questions, or items deferred for implementation. Omit section if none.}

## Minority Report
{Dissenting views from ratification, if any. Omit section if unanimous.}

## Discussion Artifacts
- Team: {comma-separated member names}
- Phase 1: {hypothesis_count} hypotheses, {critique_count} critiques
- Phase 2: {hypothesis_count} hypotheses, {critique_count} critiques
- Ratification: Round {N}, {accept_count}/{total} (voting members only)
```

## Ratification Rules (Phase 2 only)

- **Voting members**: All members (normal + -cx). Count = role count × 2.
- **Majority threshold**: ⌊N/2⌋ + 1 where N = total voting members.
- **No advisory members**: All team members have voting rights.

| Total Members | Majority Threshold |
|---------------|-------------------|
| 6 | 4 |
| 8 | 5 |
| 10 | 6 |
| 12 | 7 |

- **Max rounds**: 10 (configurable at board creation)
- **Vote format**: `RATIFY: accept — {reason}` or `RATIFY: push-back — {concerns}` via SendMessage
- **Exhaustion**: If max rounds reached with no majority, leader writes "best available design" with explicit uncertainty markers
- **Abstention**: Not permitted. Every voting member must vote each round.
- **Vote supersession**: A member's vote in round N supersedes prior rounds.

## Conflict Prevention Rules

| # | Rule | Rationale |
|---|------|-----------|
| 1 | Each teammate edits only their own `### {name}` subsection in WHITEBOARD.md | Prevents Edit tool match failures from concurrent writes |
| 2 | SYNTHESIS.md is leader-only (teammates read, never write) | Single writer eliminates conflicts |
| 3 | Append-only writes (no deletion/modification of existing entries) | Prevents overwrites from stale reads |
| 4 | Ratification votes via SendMessage, not file writes | Eliminates race conditions on vote tallying |
| 5 | Phase transitions are leader-controlled via broadcast | Clear boundaries prevent out-of-order writes |
| 6 | `## Audit` section is leader-only | Single writer; Codex results managed by leader |
| 7 | Revisions are append-only in member's own subsection | Maintains append-only invariant |
| 8 | `-cx` members follow identical write-zone rules as normal members (own `### {name}` subsection only) | Same isolation guarantees |
| 9 | Phase 1 files are read-only during Phase 2 | Prevents retroactive modification of settled technology decisions |

## Audit Notes (Phase 2 only)

- **Prerequisite:** `codex` CLI must be installed. If unavailable, skip audit, record warning in SYNTHESIS.md status line, and proceed to synthesize.
- **Do NOT audit opinions or forecasts** — only verifiable factual claims
- **Audit is incremental** — each round audits only new entries, not the full history
- **Revisions are append-only** — never edit the original hypothesis or critique text

## Timeout Policy

| Situation | Action |
|-----------|--------|
| Member has not reported completion | Leader sends one reminder via SendMessage |
| After reminder, still no response | Leader proceeds with available results (partial round) |
| Missing ratification vote | Recorded as "not submitted"; threshold recalculated as ⌊voting_count/2⌋ + 1 |
