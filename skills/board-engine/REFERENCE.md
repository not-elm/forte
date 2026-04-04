# Board Engine — Shared Debate Reference

Common rules for all board-type skills (discussion-board, design-board, investigation-board, frontend-design-board). Each board skill reads this file at setup and may override specific sections.

---

## Round-Split WHITEBOARD Architecture

### File Model

Each discussion uses two types of files in its working directory:

1. **Base WHITEBOARD.md** — Created at setup. Contains initial phases (proposition/topic, framing, and any pre-round content like evidence). Becomes **read-only** after its initial phases complete.

2. **Per-round WHITEBOARD-R{N}.md** — Created by leader at the start of each round's hypothesize phase. Contains only that round's hypotheses, critiques, audit results, and revisions. One file per round.

3. **SYNTHESIS.md** — Leader-only file for cumulative state (Evidence Map, Draft Conclusion, Round Context Packet, Ratification History, etc.).

### Round Numbering

- Round numbers are **monotonically increasing** across the entire discussion, never reset.
- For 2-phase boards: numbering continues across phases (e.g., Phase 1 R1, R2 → Phase 2 R3, R4).
- For feedback loops: numbering continues across feedback cycles (no reset on re-entry).

### Per-Round WHITEBOARD-R{N}.md Template

```markdown
# WHITEBOARD — {id} / Round {N}
> Round: {N}
> Created: {YYYY-MM-DD}

## Hypotheses
### {member-A}
### {member-B}
### {member-C}
### {member-D}
<!-- ... per team member -->

## Critique
### {member-A}
### {member-B}
### {member-C}
### {member-D}
<!-- ... per team member -->

## Audit
```

Sections start empty. Board skills may add additional sections (e.g., `## Evidence Addendum` for investigation-board).

---

## Standard Debate Cycle

The core round loop shared by all boards:

```
[Round N: hypothesize → critique → audit → revise (if needed) → synthesize → ratify]
```

Board skills define what happens before (setup, framing, evidence-gathering) and after (concluded, export) this cycle.

### hypothesize

- **Leader creates WHITEBOARD-R{N}.md** at the start of each round using the per-round template. Members write hypotheses into this file.
- **Independent generation (Round 1 only):** Members generate hypotheses WITHOUT reading other members' entries. Each member receives only the topic and their own role briefing. This eliminates first-mover anchoring. All hypotheses are written to WHITEBOARD-R1.md simultaneously.
- **Round 2+ context protocol (mandatory):**
  1. Read latest `## Round Context Packet` in SYNTHESIS.md first.
  2. Read current round's WHITEBOARD-R{N}.md (empty or near-empty at this point).
  3. If referencing specific entries from prior rounds, Grep by entry ID on WHITEBOARD-R{X}.md where X < N.
- Do NOT read older round WHITEBOARD files in full — use targeted Grep by entry ID only.
- **Per-round role re-anchoring:** Every broadcast that kicks off this phase must restate each member's discipline and expected contribution. This combats role collapse — the tendency of agents to drift toward consensus as rounds accumulate.
- Each member aims for 1-3 hypotheses, each concrete and testable.
- Report completion using the Completion Report format.

### critique

- **Per-round role re-anchoring:** Every broadcast that kicks off this phase must restate each member's discipline and expected contribution.
- **ID-index protocol (replaces full WHITEBOARD read):**
  1. Leader reads WHITEBOARD-R{N}.md `## Hypotheses`, builds an ID-index, and assigns 2-3 hypothesis IDs per member in the critique broadcast.
  2. ID-index format (per entry): `[H-X-001] axis={tags} — {1-line summary, max 20 words}`
  3. Normal members Grep only their assigned IDs on WHITEBOARD-R{N}.md to get original text. Members MUST NOT Read the full file.
  4. -cx members do NOT Grep. Instead, pass file path + assigned IDs to codex exec (see -cx Codex protocol in team-composer).
- **Assignment rules:**
  - Each member receives 2-3 IDs, prioritizing **cross-discipline** hypotheses (axis different from member's own).
  - Members choose which assigned IDs to critique (up to their critique cap per round).
  - All hypotheses covered by at least 1 member.
  - Members are never assigned their own hypotheses.
- **Critique broadcast format:**
  ```
  Phase {P} / Round {N} / Critique / WHITEBOARD-R{N}.md

  ID-index:
    [H-{P}-{I}-001] axis={tags} — {summary}
    ...

  Assignments:
    {member-name}: critique {ID-1}, {ID-2}
    {member-name}-cx: codex critique {ID-1}, {ID-2}
    ...

  Discipline: {discipline}. Expected contribution: {contribution}.
  Max {critique-cap} critiques this round. Choose which assigned IDs to critique.
  ```
- To reference entries from prior rounds, Grep by entry ID on WHITEBOARD-R{X}.md where X < N. Do NOT read older round files in full.
- Members must label each critique: `**challenge**` / `**support**` / `**amend**` / `**question**`.
- Cite `refs=[...]` and `@{member}` for every entry.
- Each member writes at most **2 critiques per round** (default; board skills may override).
- Round 2+: read both `## Draft Conclusion` and latest `## Round Context Packet` in SYNTHESIS.md before writing.
- Report completion using the Completion Report format.

### audit

- **Prerequisite:** `codex` CLI must be installed (`npm i -g @openai/codex`). If not available, skip audit phase entirely, log warning in SYNTHESIS.md status, and proceed to synthesize.
- **Scope:** Audit only entries from the current round (new hypotheses + new critiques). Do NOT re-audit entries from prior rounds.
- **Exclusion:** Skip opinions, value judgments, and forecasts — only fact-check verifiable factual claims.
- Leader collects hypotheses and critiques from current round in WHITEBOARD-R{N}.md.
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

- Execute via temp file + stdin:
  ```bash
  TMPFILE=$(mktemp)
  cat <<'PROMPT_EOF' > "$TMPFILE"
  <constructed_prompt>
  PROMPT_EOF
  cat "$TMPFILE" | codex exec --ephemeral -m gpt-5.3-codex
  rm -f "$TMPFILE"
  ```

- Write results to WHITEBOARD-R{N}.md `## Audit` section.
- Set Bash tool `timeout: 180000` (3 minutes) for the Codex invocation.

- **Error handling:**
  - Codex exits non-zero or times out → record "Audit failed (Codex error)" in WHITEBOARD-R{N}.md `## Audit`, skip revise, proceed to synthesize with warning
  - Codex returns partial/malformed output → leader writes available results, marks incomplete entries as ❓

- **Decision logic:**
  - All ✅ or ❓ only → skip `revise`, proceed to `synthesize`
  - Any ⚠️ or ❌ → proceed to `revise`

### revise

- Only runs when audit found ⚠️ Partially accurate or ❌ Inaccurate entries.
- **Per-round role re-anchoring:** The broadcast must restate each affected member's discipline and expected contribution alongside the audit findings.
- Leader broadcasts audit results and instructs affected members to review and correct their entries.
- Affected members read only from WHITEBOARD-R{N}.md:
  1. `## Audit` section
  2. Referenced entries (by ID) in Hypotheses/Critique
  3. Latest `## Round Context Packet` from SYNTHESIS.md
- Members **append** corrections in their own `### {name}` subsection in WHITEBOARD-R{N}.md. Original entries are NEVER modified (append-only).
- Revision format:

  ```markdown
  - [{original-ID}] **revised**: Updated claim based on audit [Round {N}]. {corrected statement}
    > Original: {original claim}. Audit note: {audit note}.
  ```

- Members report completion via SendMessage using the Completion Report format.
- After all affected members report: proceed to `synthesize`.
- **Max 1 revise round per audit** — no recursive auditing of revisions.
- **Unresolved ❌ after revise:** Leader notes unresolved inaccuracies in the Evidence Map (synthesize phase) with low confidence rating.

### synthesize

- **Incremental read protocol (replaces full WHITEBOARD read):**
  1. Read WHITEBOARD-R{N}.md in full (current round's entries only — bounded size).
  2. Read previous `## Evidence Map` and `## Draft Conclusion` from SYNTHESIS.md (cumulative summary of all prior rounds).
  3. For any `refs=[]` in current round entries that reference older rounds, Grep by entry ID on the specific WHITEBOARD-R{X}.md. Do NOT read older round files in full.
- Writes updated Evidence Map + Draft Conclusion in SYNTHESIS.md (cumulative — incorporates both prior synthesis and current round findings).
- Writes `## Round Context Packet` → `### Round {N}` as a compact handoff for next-round members.
- Round 2+: add entry ID → summary mapping table in SYNTHESIS.md for members to reference efficiently.
- Guideline: "When in doubt about summary accuracy, members should Grep original text in the relevant WHITEBOARD-R{X}.md."

### ratify

- Votes via SendMessage (NOT file writes): `RATIFY: accept — {reason}` or `RATIFY: push-back — {concerns}`
- **Ratify broadcast MUST include conclusion summary** (~100-150 tokens): the current Draft Conclusion or equivalent from SYNTHESIS.md, so -cx members (who cannot read SYNTHESIS.md directly) can vote meaningfully.
- Simple majority: ⌊N/2⌋ + 1 required to ratify.
- If not ratified and rounds remain: incorporate push-back, leader creates WHITEBOARD-R{N+1}.md, start next hypothesize phase.

---

## Shared Entry Formats

### Hypothesis ID

**Format:** `[H-{initial}-{seq}]` — `{initial}` = first letter of name (uppercase); `{seq}` = 001, 002, ...

For 2-phase boards, add phase prefix: `[H-{phase}-{initial}-{seq}]`

**-cx member initials:** `-cx` members use their normal member's initial + `X`. Example: `[H-BX-001]` = backend-cx. If normal members collide: fall back to first 2 letters.

### Critique ID

**Format:** `[CR-{initial}-R{round}-{seq}]`

For 2-phase boards: `[CR-{phase}-{initial}-R{round}-{seq}]`

Common mistake: `[CR-P-1-001]` (missing R prefix) → Correct: `[CR-P-R1-001]`

Each critique must include: label (`**challenge**`/`**support**`/`**amend**`/`**question**`), `refs=[...]`, `@{member}`

### Evidence Map (Leader only)

| # | Claim | Support | Counterpoint | Confidence |
|---|-------|---------|--------------|------------|
| 1 | {claim} | refs=[H-X-001, CR-Y-R1-002] | refs=[CR-Z-R1-001] | high/medium/low |

### Draft Conclusion (Leader only)

```markdown
## Draft Conclusion — Round {N}
{Synthesized conclusion citing entry IDs. Mark areas of uncertainty.}
**Key claims:** 1, 2, 3 (from Evidence Map)
**Unresolved:** {low-confidence or unaddressed claims}
```

### Round Context Packet (Leader only)

Compact handoff context for the next round. Default read target for members and leader in Round 2+.

```markdown
## Round Context Packet
### Round {N}
- Key points (with entry IDs): {5-10 bullets}
- Open disputes: refs=[...]
- Next-round focus: {what members should challenge or extend}
```

Rules:
- Keep concise: target 150-250 tokens, hard cap 350 tokens
- Reference entry IDs instead of pasting long excerpts
- Members read this first in Round 2+, then pull original text via Grep on WHITEBOARD-R{X}.md only when needed
- Leader also uses this as cumulative context during synthesize, avoiding full re-read of older round files

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
Remaining concerns: {description or "none"}
```

### Audit Table + Verdict Rubric

| Entry | Claim Summary | Verdict | Notes |
|-------|--------------|---------|-------|
| [H-S-001] | {claim} | ✅/⚠️/❌/❓ | {evidence or reason} |

- ✅ **Verified**: Claim is factually accurate based on established knowledge
- ⚠️ **Partially accurate**: Contains some truth but misleading, incomplete, or outdated
- ❌ **Inaccurate**: Factually wrong
- ❓ **Unverifiable**: Cannot be verified (insufficient context, or subjective/speculative)

Granularity: one row per hypothesis or critique entry (by entry ID), not per sentence.

---

## Standard Rules

### Conflict Prevention Rules

| # | Rule | Rationale |
|---|------|-----------|
| 1 | Each teammate edits only their own `### {name}` subsection in the current round's WHITEBOARD-R{N}.md | Prevents Edit tool match failures from concurrent writes |
| 2 | SYNTHESIS.md is leader-only (teammates read, never write) | Single writer eliminates conflicts |
| 3 | Append-only writes (no deletion/modification of existing entries) | Prevents overwrites from stale reads |
| 4 | Ratification votes via SendMessage, not file writes | Eliminates race conditions on vote tallying |
| 5 | Phase transitions are leader-controlled via broadcast | Clear boundaries prevent out-of-order writes |
| 6 | `## Audit` section is leader-only (structural exception to per-member rule) | Single writer; Codex results managed by leader |
| 7 | Revisions are append-only in member's own subsection; original entries are never modified | Maintains append-only invariant |
| 8 | `-cx` members follow identical write-zone rules as normal members (own `### {name}` subsection only) | Same isolation guarantees |
| 9 | Base WHITEBOARD.md is read-only after its initial phases complete | Prevents retroactive modification; keeps base file small |
| 10 | Older round files (WHITEBOARD-R{X}.md where X < current) are read-only; only current round file is writable | Prevents cross-round write conflicts; enforces incremental synthesis |
| 11 | `-cx` members MUST NOT directly Read or Grep any discussion files (base WHITEBOARD.md, WHITEBOARD-R{N}.md, SYNTHESIS.md) during any phase. They interact with these files exclusively through codex exec. Exception: hypothesize Round 1 (independent generation, no files to read). Fallback: if codex CLI is unavailable, -cx members use normal member protocol (full Read for framing, Grep for critique/revise). | Shifts token consumption from Claude to Codex (separate billing) |

Board skills may add additional rules (e.g., phase-specific read-only rules, escalation rules).

### Ratification Rules

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
- **Exhaustion**: If max rounds reached with no majority, leader writes "best available conclusion" with explicit uncertainty markers
- **Abstention**: Not permitted. Every member must vote each round.
- **Vote supersession**: A member's vote in round N supersedes prior rounds.

### Communication Rules

- All leader → member instructions via **broadcast** (NOT individual SendMessage).
- Use structured short format: Phase / Round / Action / Format-ref (~80-120 tokens).
- Combine phase transitions: completion confirmation + next phase instruction in 1 broadcast.
- Round 2+ broadcasts should reference `Round Context Packet` and entry IDs instead of pasting long excerpts. Include the current round file name (WHITEBOARD-R{N}.md) so members know which file to write to.

### Timeout Policy

| Situation | Action |
|-----------|--------|
| Member has not reported completion | Leader sends one reminder via SendMessage |
| After reminder, still no response | Leader proceeds with available results (partial round) |
| Missing ratification vote | Recorded as "not submitted"; threshold recalculated as ⌊voting_count/2⌋ + 1 |

### Audit Notes

- **Prerequisite:** `codex` CLI must be installed (`npm i -g @openai/codex`). If unavailable, skip audit, record warning in SYNTHESIS.md status line, and proceed to synthesize.
- **Do NOT audit opinions or forecasts** — only verifiable factual claims
- **Audit is incremental** — each round audits only new entries, not the full history
- **Revisions are append-only** — never edit the original hypothesis or critique text
