---
name: discussion-board
description: >-
  Team discussion via structured debate and iterative synthesis.
  Use when exploring an open-ended question through team collaboration
  where the answer must be discovered, not selected from pre-given options.
  Triggers: discuss, explore question, research question, how should we,
  what approach, open forum, 議論, 検討, どうすべき
---

# Discussion Board — Team Exploration via Hypotheses & Synthesis

Explore an open-ended proposition through structured team debate, iterative synthesis, and ratification using TeamCreate + SendMessage.

## When to Use

- The task requires exploring an open-ended question with no pre-defined options
- Keywords: "discuss", "explore question", "research question", "how should we", "議論", "検討", "どうすべき"

## When NOT to Use

- Use `decision-board` when the user provides explicit candidate options (candidate set is given)

## Core Principles

1. **Proposition-centric** — All activity addresses an open-ended proposition.
2. **2-file model** — WHITEBOARD.md (framing + hypotheses + critiques) + SYNTHESIS.md (leader-managed state), both in `docs/discussions/{discussion-id}/`. Concluded → Design Doc exported to `docs/plans/`, discussion directory deleted.
3. **Per-member write zones** — Each teammate writes only to their own `### {name}` subsection in WHITEBOARD.md.
4. **Leader-only SYNTHESIS.md** — Teammates read but never write to SYNTHESIS.md.
5. **Append-only** — Teammates add content, never delete or modify existing entries.
6. **Iterative synthesis** — Leader drafts conclusions; members ratify or push back across rounds.
7. **Leader as synthesizer, not participant** — Leader does NOT write hypotheses or critiques. Leader MAY write process artifacts (audit results, evidence maps, conclusions) to facilitate discussion quality.

## Phase Model

```
setup/explore → setup/confirm → framing → [Round N: hypothesize → critique → audit → revise (if needed) → synthesize → ratify] → concluded
```

| Phase | Who | What |
|-------|-----|------|
| setup/explore | Leader + User | Analyze proposition, ask user questions, generate expertise map of required domains |
| setup/confirm | Leader + User | Generate discipline-only roles from expertise map, present with expected contributions, user approves, create team + files |
| framing | All members | Document problem interpretation, constraints, criteria, unknowns |
| hypothesize | All members | Write concrete, testable candidate answers as hypotheses |
| critique | All members | Challenge/support/amend/question hypotheses with cross-references |
| audit | Leader only | Run Codex CLI to fact-check hypotheses and critiques from current round; write results to WHITEBOARD `## Audit` |
| revise | All members | Review audit findings and append corrections to own entries (skipped if no ⚠️/❌ found) |
| synthesize | Leader only | Read all content, write Evidence Map + Draft Conclusion in SYNTHESIS.md |
| ratify | All members | Vote accept or push-back via SendMessage. Simple majority ratifies |
| concluded | Leader only | Record final conclusion (and Minority Report if dissent exists) |

## Entry Formats

### Framing

Structured fields in each member's `### {name}` Framing subsection (no entry IDs):

```markdown
- **Problem**: {interpretation of the proposition}
- **Constraints**: {known limitations}
- **Criteria**: {what makes a good answer}
- **Unknowns**: {open questions}
```

### Hypothesis

**ID format:** `[H-{initial}-{seq}]` — `{initial}` = first letter of name (uppercase); `{seq}` = 001, 002, ...

```markdown
- [H-S-001] **hypothesis**: Use WebSocket-based real-time sync with CRDTs for offline mode.
  > Rationale: CRDTs allow concurrent edits without coordination.
  > Grounding: [general-knowledge] CRDTs are a well-established approach for distributed state (Shapiro et al., 2011). [code-verified] Current sync logic at src/sync/engine.ts:45 assumes single-writer.
```

Grounding labels:
- `[code-verified]` — Confirmed at a specific file:line in the codebase
- `[data-backed]` — Based on concrete data, measurements, or benchmarks
- `[general-knowledge]` — Based on widely recognized technical knowledge (always valid as escape valve)

### Critique

**ID format:** `[CR-{initial}-R{round}-{seq}]`

Common mistake: `[CR-P-1-001]` (missing R prefix) → Correct: `[CR-P-R1-001]`

Each critique must include: label (`**challenge**`/`**support**`/`**amend**`/`**question**`), `refs=[...]`, `@{member}`

Critiques making factual claims (challenge/amend) should include grounding for those claims. Questions and support labels may omit grounding. Example: `**challenge** ... [code-verified] The current implementation at file:line does X, contradicting this hypothesis.`

```markdown
#### Round 1
- [CR-P-R1-001] **challenge** @security-expert refs=[H-S-001]: CRDTs introduce unbounded state growth. How do we handle tombstone GC?
```

### Evidence Map (Leader only)

| # | Claim | Support | Counterpoint | Grounding | Confidence |
|---|-------|---------|--------------|-----------|------------|
| 1 | {claim} | refs=[H-X-001, CR-Y-R1-002] | refs=[CR-Z-R1-001] | code-verified/data-backed/general-knowledge/ungrounded | high/medium/low |

### Draft Conclusion (Leader only)

```markdown
## Draft Conclusion — Round {N}
{Synthesized conclusion citing entry IDs. Mark areas of uncertainty.}
**Key claims:** 1, 2, 3 (from Evidence Map)
**Unresolved:** {low-confidence or unaddressed claims}
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
**Dissenter(s):** {names}  **Position:** {view}  **Evidence:** refs=[...]
**Leader note:** {why majority view was adopted}
```

### Completion Report

Members send this via SendMessage after each sub-phase:

```
Entries added: {N}
Key insight: {most important finding}
Current position: {view in one sentence}
Evidence basis: {code-verified: N, data-backed: N, general-knowledge: N}
Remaining concerns: {description or "none"}
```

### Audit

Leader-only. Written per round after Codex CLI fact-check. Only factual claims are audited — opinions, value judgments, and forecasts are excluded.

| Entry | Claim Summary | Verdict | Notes |
|-------|--------------|---------|-------|
| [H-S-001] | {claim} | ✅/⚠️/❌/❓ | {evidence or reason} |

Verdict rubric:
- ✅ **Verified**: Claim is factually accurate based on established knowledge
- ⚠️ **Partially accurate**: Claim contains some truth but is misleading, incomplete, or outdated
- ❌ **Inaccurate**: Claim is factually wrong
- ❓ **Unverifiable**: Claim cannot be verified (insufficient context, or subjective/speculative)

Granularity: one row per hypothesis or critique entry (by entry ID), not per sentence.

### Revision

Members append corrections in their own subsection (append-only — original entry is never modified).

- [H-S-001] **revised**: Updated claim based on audit [Round {N}]. {corrected statement}
  > Original: {original claim}. Audit note: {audit note}.

### ID Summary

| Type | Format | Section | Phase |
|------|--------|---------|-------|
| Framing | (no ID — structured fields) | Framing | framing |
| Hypothesis | `[H-{initial}-{seq}]` | Hypotheses | hypothesize |
| Critique | `[CR-{initial}-R{round}-{seq}]` | Critique → Round N | critique |
| Audit | (no ID — table format) | Audit → Round N | audit |
| Revision | `[{original-ID}] **revised**` | Hypotheses or Critique | revise |

---

# Workflow Layer

## Workflow Overview

| Phase | Leader Action | Member Action | Output | Next Trigger |
|-------|---------------|---------------|--------|--------------|
| setup/explore | Analyze proposition, ask user questions, generate expertise map (6-10 required domains) | — | Expertise map + topic insights from user dialogue | Leader has expertise map with 6-10 domains |
| setup/confirm | Generate discipline-only roles from expertise map, present with expected contributions to user | — | Approved role list → team created, WHITEBOARD.md + SYNTHESIS.md | User approves roles |
| framing | Broadcast framing instructions | Document understanding in own section | Framing entries | All members report complete |
| hypothesize | Broadcast hypothesize kickoff | Write hypotheses in own section | Hypothesis entries | All members report complete |
| critique | Broadcast critique instructions | Write critiques with labels + refs | Critique entries | All members report complete |
| audit | Run Codex CLI on current round's claims, write Audit table | — | WHITEBOARD.md `## Audit → Round {N}` updated | Audit written |
| revise | Broadcast audit findings to affected members | Append corrections in own section (append-only) | Revised entries | All affected members report complete (or skipped if all ✅/❓) |
| synthesize | Read all WHITEBOARD, write Evidence Map + Draft | — | SYNTHESIS.md updated | Draft written |
| ratify | Broadcast ratify request | Send vote via SendMessage | Ratification History | Majority reached or next round |
| concluded | Write Final Conclusion (+ Minority Report) | — | Final SYNTHESIS.md | — |

## Phase Notes

### setup/explore

- Leader analyzes the proposition and assesses its clarity before asking questions.
- Ask the user one question at a time (never combine multiple questions in one message).
- Prefer multiple-choice questions where possible; open-ended questions are also acceptable.
- Question focus areas:
  - Background and motivation (why is this discussion needed?)
  - Goals (what outcome defines success?)
  - Known constraints and assumptions
  - Specific domains or expertise to emphasize or exclude
- Adapt depth to proposition clarity: 2-3 questions if clear, up to 4 if ambiguous or broad.
- **Transition to setup/confirm** when either condition is met:
  1. Leader can identify enough independent expertise domains to match topic complexity (focused: 6, moderate: 7-8, complex: 9-10).
  2. Maximum 4 questions reached — proceed with best available domains.
- Question count is **cumulative** across all explore visits (does not reset if returning from confirm).
- If user specifies roles upfront, skip explore and enter confirm directly (name constraint check only).
- **Expertise mapping:** Before generating roles, the leader produces an expertise map — 6-10 domains of expertise directly required to discuss the proposition in depth. Each domain must be **directly relevant** to the topic; do not include "nice to have" domains. The same domain with different focus areas may appear as separate entries (e.g., "Performance × Latency", "Performance × Throughput"). Format:
  ```
  Expertise Map — {topic}
  1. {domain}: {why this topic requires this expertise}
  2. {domain}: {why this topic requires this expertise}
  ...
  ```
- **Domain sufficiency check:** If the leader cannot identify 6 independent domains without inferring major unstated assumptions, ask the user one clarifying question before proceeding. This does not count toward the 4-question limit.
- The expertise map is presented to the user alongside the role list in setup/confirm (not separately approved).

### setup/confirm

- Generate roles from the expertise map produced in setup/explore. Each role has a **single layer**:
  - **Discipline** — the specific expertise domain this member brings (e.g., "Cluster Operations Specialist", "Cost Optimization Analyst")
- Each role is presented in the following format:
  ```
  1. **{Role Name}** — {discipline/expertise domain}
     > Expected contribution: {concrete contribution this member brings to the discussion}
  ```
- Multiple members may share the same domain if they cover different focus areas (e.g., two security experts with different specializations). Names must be distinct and meaningful (e.g., "Sentinel" and "Bastion" rather than "Security1" and "Security2").
- Role count = team size (range 6-10).
  - Default: 6. Leader adjusts based on topic complexity: focused → 6, moderate → 7-8, complex → 9-10.
  - Fewer than 6 is not permitted.
  - If more than 10: leader presents consolidation candidates for user to choose.
- **Name constraints** (role names = subsection headers = ID initials):
  - Short English names (1-2 words, space-separated).
  - Must work as `### {name}` subsection headers.
  - First-letter initials (uppercase) must be unique within the team (prevents `[H-{initial}-{seq}]` ID collisions).
  - If initial collision is unavoidable with meaningful names, use first two letters as the initial fallback.
- User approval gate: "These are the team members. Add, remove, or modify as needed."
  - User requests modification → leader revises and re-presents (loop within confirm).
  - User requests more questions → return to explore (max 2 returns; question count is cumulative).
  - Max 3 re-presentations without convergence → ask user to specify roles in free text.
- After user approves:
  - Each role name becomes a member name for team creation. The discipline + expected contribution is used as the member's briefing context in all subsequent broadcasts.
  - Generate a kebab-case `{discussion-id}` from the proposition (e.g., `context-optimization`).
  - Create `docs/discussions/{discussion-id}/WHITEBOARD.md` + `SYNTHESIS.md` using templates (see Reference Layer).
  - Ensure `docs/discussions/` is in `.gitignore` (add if missing).
  - SYNTHESIS.md initializes with `> Status: setup` as before; leader transitions to framing immediately.

### framing

- Members use full WHITEBOARD.md Read (file is small, ~100 lines at this stage).
- Leader combines completion confirmation + hypothesize kickoff in 1 broadcast to reduce round-trips.

### hypothesize

- **Independent generation (Round 1 only):** In the first round, members generate hypotheses WITHOUT reading other members' framing entries. Each member receives only the proposition and their own role briefing (discipline + expected contribution from setup/confirm). This eliminates first-mover anchoring where the first agent's conceptual vocabulary constrains all subsequent agents. All hypotheses are written to WHITEBOARD.md simultaneously.
- **Round 2+:** Members read all prior content via full WHITEBOARD.md Read.
- **Per-round role re-anchoring:** Every broadcast that kicks off this phase must restate each member's discipline and expected contribution (from setup/confirm). This combats role collapse — the tendency of agents to drift toward consensus as the WHITEBOARD accumulates content.
- Each member aims for 2-5 hypotheses, each concrete and testable.
- Each hypothesis should include a `Grounding:` line citing evidence basis. `[general-knowledge]` is always valid — the goal is transparency about evidence strength, not blocking non-code claims. Hypotheses without grounding will be flagged during audit.
- Report completion using the completion report format.

### critique

- **Per-round role re-anchoring:** Every broadcast that kicks off this phase must restate each member's discipline and expected contribution (from setup/confirm).
- **IMPORTANT**: Use 2-step Grep extraction when WHITEBOARD exceeds ~350 lines:
  1. `Grep pattern="## Hypotheses"` to extract the H2 section
  2. `Grep pattern="### {member-name}"` to narrow to a specific member
- Members must label each critique: challenge/support/amend/question.
- Cite refs=[] and @member for every entry.
- Round 2+: also read Draft Conclusion in SYNTHESIS.md.

### audit

- **Prerequisite:** `codex` CLI must be installed (`npm i -g @openai/codex`). If not available, skip audit phase entirely, log warning in SYNTHESIS.md status, and proceed to synthesize.
- **Scope:** Audit only entries from the current round (new hypotheses + new critiques). Do NOT re-audit entries from prior rounds.
- **Exclusion:** Skip opinions, value judgments, and forecasts — only fact-check verifiable factual claims.
- Leader collects hypotheses and critiques from current round in WHITEBOARD.md.
- Leader builds a Codex prompt requesting fact-checking of each claim.
- Prompt template:

  ```
  Fact-check the following claims from a team discussion. For each claim:
  1. Verify if it is factually accurate
  2. Note any inaccuracies, outdated information, or unsupported assertions
  3. Provide brief evidence or references for your assessment
  4. Skip opinions, value judgments, and forecasts — mark them as ❓ Unverifiable
  5. If a hypothesis cites a specific file:line reference, verify that the cited code actually supports the claim

  Rate each claim: ✅ Verified / ⚠️ Partially accurate / ❌ Inaccurate / ❓ Unverifiable

  Claims:
  {hypotheses and critique claims from current round}
  ```

- Execute via temp file + stdin (same as codex-review skill):
  ```bash
  TMPFILE=$(mktemp)
  cat <<'PROMPT_EOF' > "$TMPFILE"
  <constructed_prompt>
  PROMPT_EOF
  cat "$TMPFILE" | codex exec --ephemeral
  rm -f "$TMPFILE"
  ```

- Write results to WHITEBOARD.md `## Audit` → `### Round {N}` subsection (append-only, each round gets its own subsection).

- **Error handling:**
  - Codex exits non-zero or times out → record "Audit failed (Codex error)" in `### Round {N}`, skip revise, proceed to synthesize with warning
  - Codex returns partial/malformed output → leader writes available results, marks incomplete entries as ❓

- Set Bash tool `timeout: 180000` (3 minutes) for the Codex invocation to prevent the default 120s timeout from killing longer runs.

- **Decision logic:**
  - All ✅ or ❓ only → skip `revise`, proceed to `synthesize`
  - Any ⚠️ or ❌ → proceed to `revise`

### revise

- Only runs when audit found ⚠️ Partially accurate or ❌ Inaccurate entries.
- **Per-round role re-anchoring:** The broadcast that kicks off this phase must restate each affected member's discipline and expected contribution alongside the audit findings.
- Leader broadcasts audit results and instructs affected members to review and correct their entries.
- Members **append** corrections in their own `### {name}` subsection under the relevant section (Hypotheses or Critique). Original entries are NEVER modified (append-only).
- Revision format:

  ```markdown
  - [H-S-001] **revised**: Updated claim based on audit [Round {N}]. {corrected statement}
    > Original: {original claim}. Audit note: {audit note}.
  ```

- Members report completion via SendMessage using the standard completion report format.
- After all affected members report: proceed to `synthesize`.
- **Max 1 revise round per audit** — no recursive auditing of revisions.
- **Unresolved ❌ after revise:** Leader notes unresolved inaccuracies in the Evidence Map (synthesize phase) with low confidence rating. These are visible during ratification for members to consider.

### synthesize

- Leader reads ALL WHITEBOARD.md content (framing, hypotheses, all critiques).
- Writes Evidence Map + Draft Conclusion in SYNTHESIS.md.
- Round 2+: add entry ID → summary mapping table in SYNTHESIS.md for members to reference efficiently.
- Guideline: "When in doubt about summary accuracy, members should Grep original text."

### ratify

- Votes via SendMessage (NOT file writes): `RATIFY: accept — {reason}` or `RATIFY: push-back — {concerns}`
- Simple majority: ⌊N/2⌋ + 1 required to ratify.
- If not ratified and rounds remain: incorporate push-back, start next critique round.

### concluded

- Leader exports Final Conclusion as a Design Doc to `docs/plans/YYYY-MM-DD-{topic}-design.md` (see Design Doc Template in Reference Layer).
- Verify the Design Doc file was created successfully.
- Delete `docs/discussions/{discussion-id}/` directory after successful export.
- If discussion was interrupted (no Final Conclusion): skip Design Doc export, delete discussion directory manually.

## Communication Rules

- All leader → member instructions via **broadcast** (NOT individual SendMessage).
- Use structured short format: Phase / Round / Action / Format-ref (~80-120 tokens).
- Combine phase transitions: completion confirmation + next phase instruction in 1 broadcast.

---

# Reference Layer

## WHITEBOARD.md Template

Path: `docs/discussions/{discussion-id}/WHITEBOARD.md`

```markdown
# WHITEBOARD — {discussion-id}
> Proposition: {question}
> Created: {YYYY-MM-DD}
> Team: {comma-separated names}

## Proposition
{Clear statement of the question. Include context and motivation.}

## How Our Work Connects
{Each member's role and perspective.}

<!-- Repeat ### {member-name} subsections for each team member (6-10 members) -->
## Framing
### {member-A}
### {member-B}
### {member-C}
### {member-D}
<!-- ... up to {member-J} depending on team size -->

## Hypotheses
### {member-A}
### {member-B}
### {member-C}
### {member-D}
<!-- ... up to {member-J} depending on team size -->

## Critique
### {member-A}
### {member-B}
### {member-C}
### {member-D}
<!-- ... up to {member-J} depending on team size -->

## Audit
```

No Status/Round header in WHITEBOARD — managed in SYNTHESIS.md. Sections start empty. See Entry Formats above for content structure.

## SYNTHESIS.md Template

Path: `docs/discussions/{discussion-id}/SYNTHESIS.md`

```markdown
# SYNTHESIS — {discussion-id}
> Status: setup
> Round: 0
> Max Rounds: 10

## Evidence Map
## Draft Conclusion
## Ratification History
## Minority Report
## Final Conclusion
```

Leader-only file. See Entry Formats above for section content structure.

## Design Doc Template

Path: `docs/plans/YYYY-MM-DD-{topic}-design.md`

Exported by leader during `concluded` phase. This is the permanent record of the discussion outcome.

```markdown
# {Topic} Design

> Date: {YYYY-MM-DD}
> Status: Approved ({accept_count}/{total} {unanimous/majority})
> Method: Discussion Board ({N}-member structured debate)

## Summary
{Final Conclusion summary — 2-3 sentences}

## Background
{Proposition + problem context + motivation}

## Approved Design
{Detailed conclusion citing key evidence. Structure with subsections as needed.}

## Expected Impact
{Expected effects of adopting this design}

## Discussion Artifacts
- Team: {comma-separated member names}
- Hypotheses: {count}, Critiques: {count}
- Ratification: Round {N}, {accept_count}/{total}
```

Note: This is a design document, not an implementation plan. To create an executable plan, use `superpowers:writing-plans` with this design doc as input.

## Ratification Rules

| Members | Majority Threshold |
|---------|-------------------|
| 6 | 4 |
| 7 | 4 |
| 8 | 5 |
| 9 | 5 |
| 10 | 6 |

- **Max rounds**: 10 (configurable at board creation)
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
| 6 | `## Audit` section is leader-only (structural exception to per-member rule, same pattern as SYNTHESIS.md) | Single writer; Codex results managed by leader |
| 7 | Revisions are append-only in member's own subsection; original entries are never modified | Maintains append-only invariant from Core Principle #5 |

## Audit Notes

- **Prerequisite:** `codex` CLI must be installed (`npm i -g @openai/codex`). If unavailable, skip audit, record warning in SYNTHESIS.md status line, and proceed to synthesize.
- **Do NOT audit opinions or forecasts** — only verifiable factual claims
- **Audit is incremental** — each round audits only new entries, not the full history
- **Revisions are append-only** — never edit the original hypothesis or critique text

## Timeout Policy

| Situation | Action |
|-----------|--------|
| Member has not reported completion | Leader sends one reminder via SendMessage |
| After reminder, still no response | Leader proceeds with available results (partial round) |
| Missing ratification vote | Recorded as "not submitted"; threshold recalculated as ⌊voting_count/2⌋ + 1 |
