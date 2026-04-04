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
2. **Round-split WHITEBOARD model** — Base WHITEBOARD.md (proposition + framing, read-only after framing) + per-round WHITEBOARD-R{N}.md + SYNTHESIS.md, all in `docs/discussions/{discussion-id}/`. Concluded → Design Doc exported to `docs/plans/`, discussion directory deleted. See board-engine REFERENCE.md for file model details.
3. **Append-only** — Teammates add content, never delete or modify existing entries.
4. **Iterative synthesis** — Leader drafts conclusions; members ratify or push back across rounds.
5. **Leader as synthesizer, not participant** — Leader does NOT write hypotheses or critiques. Leader MAY write process artifacts (audit results, evidence maps, conclusions) to facilitate discussion quality.

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
setup → framing → [Round N: hypothesize → critique → audit → revise (if needed) → synthesize → ratify] → concluded
```

| Phase | Who | What |
|-------|-----|------|
| setup | Leader | Invoke team-composer, create discussion files, spawn members |
| framing | All members | Document problem interpretation, constraints, criteria, unknowns |
| hypothesize | All members | Write concrete, testable candidate answers as hypotheses |
| critique | All members | Challenge/support/amend/question hypotheses with cross-references |
| audit | Leader only | Codex CLI fact-check of current round; results to WHITEBOARD-R{N}.md `## Audit` |
| revise | All members | Review audit findings, append corrections (skipped if no warnings/errors) |
| synthesize | Leader only | Update Evidence Map + Draft Conclusion + Round Context Packet in SYNTHESIS.md |
| ratify | All members | Vote accept or push-back via SendMessage. Simple majority ratifies |
| concluded | Leader only | Record final conclusion (and Minority Report if dissent exists) |

## Board-Specific Entry Formats

### Framing

Structured fields in each member's `### {name}` Framing subsection (no entry IDs):

```markdown
- **Problem**: {interpretation of the proposition}
- **Constraints**: {known limitations}
- **Criteria**: {what makes a good answer}
- **Unknowns**: {open questions}
```

### Grounding Requirement

Every hypothesis should include a `Grounding:` line citing evidence basis. Labels:

- `[code-verified]` — Confirmed at a specific file:line in the codebase
- `[data-backed]` — Based on concrete data, measurements, or benchmarks
- `[general-knowledge]` — Based on widely recognized technical knowledge (always valid as escape valve)

`[general-knowledge]` is always valid — the goal is transparency about evidence strength, not blocking non-code claims. Hypotheses without grounding will be flagged during audit.

Critiques making factual claims (`**challenge**`/`**amend**`) should also include grounding. Questions and support labels may omit grounding.

All other entry formats (Hypothesis ID, Critique ID, Evidence Map, Draft Conclusion, Round Context Packet, Ratification History, Minority Report, Completion Report, Audit Table, Revision) — see board-engine REFERENCE.md.

## Board-Specific Phase Notes

For the standard debate cycle phases (hypothesize, critique, audit, revise, synthesize, ratify), see board-engine REFERENCE.md. Board-specific additions only below.

### setup

- Invoke `forte:team-composer` with:
  - `topic`: the proposition
  - `team_name`: generate a kebab-case `{discussion-id}` from the proposition (e.g., `context-optimization`)
  - `role_count`: `"3-4"`
  - `domain_hints`: extracted from any pre-context given by user
- After team-composer completes (Handoff Contract received):
  - Create `docs/discussions/{discussion-id}/WHITEBOARD.md` (base file) + `SYNTHESIS.md` using templates below.
  - Do NOT create per-round WHITEBOARD files yet — created at each round's hypothesize phase.
  - Ensure `docs/discussions/` is in `.gitignore` (add if missing).
  - SYNTHESIS.md initializes with `> Status: setup`.
  - Spawn all members with discussion-board-specific prompts:
    - Normal members: standard discussion participation prompt (discipline + expected contribution as briefing context).
    - `-cx` members: same prompt + codex exec exploration template (see team-composer skill for template).
  - Leader transitions to framing immediately.

### framing

- **Leader reads board-engine REFERENCE.md** at framing kickoff (if not already read).
- Normal members read only `## Proposition`, `## How Our Work Connects`, and their own `## Framing` subsection from base WHITEBOARD.md.
- -cx members use Codex framing template (see team-composer Codex-Mediated Protocol).
- Base WHITEBOARD.md is small at this stage (~100 lines); full Read is acceptable for normal members.
- After framing completes, base WHITEBOARD.md becomes **read-only** for the remainder of the discussion.
- Leader combines completion confirmation + hypothesize kickoff in 1 broadcast to reduce round-trips.

### hypothesize (board-specific addition)

- Each hypothesis should include a `Grounding:` line per the Grounding Requirement above.

### concluded

- Leader exports Final Conclusion as a Design Doc to `docs/plans/YYYY-MM-DD-{topic}-design.md` (see Design Doc Template below).
- Verify the Design Doc file was created successfully.
- Delete `docs/discussions/{discussion-id}/` directory after successful export.
- If discussion was interrupted (no Final Conclusion): skip Design Doc export, delete discussion directory manually.

---

# Reference Layer

## WHITEBOARD.md Template (Base File)

Path: `docs/discussions/{discussion-id}/WHITEBOARD.md`

Created during setup. Becomes **read-only after framing phase** completes.

```markdown
# WHITEBOARD — {discussion-id}
> Proposition: {question}
> Created: {YYYY-MM-DD}
> Team: {comma-separated names}

## Proposition
{Clear statement of the question. Include context and motivation.}

## How Our Work Connects
{Each member's role and perspective.}

<!-- Repeat ### {member-name} subsections for each team member -->
## Framing
### {member-A}
### {member-B}
### {member-C}
### {member-D}
<!-- ... up to {member-J} depending on team size -->
```

## SYNTHESIS.md Template

Path: `docs/discussions/{discussion-id}/SYNTHESIS.md`

```markdown
# SYNTHESIS — {discussion-id}
> Status: setup
> Round: 0
> Max Rounds: 10

## Evidence Map
## Draft Conclusion
## Round Context Packet
## Ratification History
## Minority Report
## Final Conclusion
```

Leader-only file. See board-engine REFERENCE.md for section content structure.

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

### Completion Report Override

Discussion-board adds one field to the standard Completion Report (see board-engine REFERENCE.md):

```
Evidence basis: {code-verified: N, data-backed: N, general-knowledge: N}
```

This tracks the grounding quality of each member's contributions.
