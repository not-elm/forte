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
2. **2-phase model** — Phase 1 (Technical Investigation) narrows technology choices; Phase 2 (Design) produces the implementation plan. Each phase has its own WHITEBOARD + SYNTHESIS files in separate subdirectories.
3. **Structured phase handoff** — Phase 1 SYNTHESIS.md is the mandatory context injection source for Phase 2. Leader pushes Phase 1 conclusions via broadcast at Phase 2 framing start.
4. All other principles (2-file model, per-member write zones, leader-only SYNTHESIS, append-only, leader as synthesizer) — see Shared Debate Engine.

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
setup → [Phase 1: framing → hypothesize → critique → synthesize] → user-review → [Phase 2: framing → [Round N: hypothesize → critique → audit → revise (if needed) → synthesize → ratify] ] → concluded
```

### Phase 1 — Technical Investigation (4 steps, NO audit/revise/ratify)

| Step | Who | What |
|------|-----|------|
| framing | All members | Document problem interpretation, technology constraints, evaluation criteria, unknowns |
| hypothesize | All members | Propose concrete technology choices, library candidates, architecture patterns |
| critique | All members | Challenge/support/amend/question hypotheses with cross-references |
| synthesize | Leader only | Read all content, write Evidence Map + Technology Conclusion in SYNTHESIS.md |

Phase 1 uses a **single WHITEBOARD.md** (no round-split). There is only one cycle with no ratification loop, so round-split overhead is unnecessary.

Phase 1 does NOT include audit, revise, or ratify. The user-review step after Phase 1 serves as the ratification gate.

### User Review

Leader presents Phase 1 conclusions to the user via AskUserQuestion:
- Include: selected technologies, key trade-offs, rejected alternatives with reasons
- User choices: "Proceed to Phase 2" or "Provide feedback on the technology selections"
- If user provides feedback: Leader records feedback in phase-1/SYNTHESIS.md `## User Review Outcome`, then incorporates it as additional constraints for Phase 2 framing. Phase 1 files are NOT re-executed — feedback adjusts Phase 2's starting constraints only.
- No skip option — user confirmation is mandatory

### Phase 2 — Design (standard debate cycle with round-split)

Uses the standard debate cycle from REFERENCE.md: `[Round N: hypothesize → critique → audit → revise (if needed) → synthesize → ratify]`

Phase 2 applies round-split WHITEBOARD:
- **Base:** `phase-2/WHITEBOARD.md` — Topic + Framing (read-only after framing completes)
- **Rounds:** `phase-2/WHITEBOARD-R{N}.md` — Hypotheses + Critique + Audit per round

## Board-Specific Entry Formats

Entry IDs use phase prefix to ensure global uniqueness across phases:

- **Hypothesis:** `[H-{phase}-{initial}-{seq}]` — e.g., `[H-1-S-001]`, `[H-2-A-001]`
- **Critique:** `[CR-{phase}-{initial}-R{round}-{seq}]` — e.g., `[CR-1-P-R1-001]`, `[CR-2-M-R2-003]`

Common mistake: `[CR-2-P-1-001]` (missing R prefix) — Correct: `[CR-2-P-R1-001]`

All other entry formats (Evidence Map, Completion Report, Audit Table, Revision, Ratification History, Minority Report) — see REFERENCE.md.

### Phase 1 Framing Fields

```markdown
- **Problem**: {interpretation of the design challenge}
- **Technology Constraints**: {known platform/stack/compatibility requirements}
- **Evaluation Criteria**: {what makes a good technology choice}
- **Unknowns**: {open questions about technology landscape}
```

### Phase 2 Framing Fields

```markdown
- **Scope**: {what this design covers}
- **Constraints**: {from Phase 1 conclusions + user feedback}
- **Acceptance Criteria**: {what makes a good implementation design}
- **Unknowns**: {open questions about implementation}
```

### Technology Conclusion (Phase 1, Leader only)

```markdown
## Technology Conclusion
**Selected:** {technology/pattern choices with rationale}
**Rejected:** {alternatives with reasons}
**Trade-offs:** {key trade-offs accepted}
**Open questions for Phase 2:** {items to resolve during design}
```

### Draft Design (Phase 2, Leader only)

```markdown
## Draft Design — Round {N}
{Synthesized implementation design citing entry IDs. Mark areas of uncertainty.}
**Key claims:** 1, 2, 3 (from Evidence Map)
**Unresolved:** {low-confidence or unaddressed claims}
```

---

# Workflow Layer

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

- **Leader reads board-engine REFERENCE.md** at framing kickoff (if not already read).
- Normal members use full WHITEBOARD.md Read (file is small, ~100 lines at this stage).
- -cx members use Codex framing template (see team-composer Codex-Mediated Protocol).
- Leader combines completion confirmation + hypothesize kickoff in 1 broadcast to reduce round-trips.
- Framing should focus on technology landscape, constraints, and evaluation criteria.

### Phase 1: hypothesize

- Members read all framings via full WHITEBOARD.md Read (~200 lines at this stage).
- Each member aims for **1-3 hypotheses** about technology choices, library candidates, or architecture patterns.
- Report completion using the Completion Report format.

### Phase 1: critique

- ID-index protocol from board-engine REFERENCE.md applies. Leader builds ID-index and assigns hypotheses.
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

### Phase 2: debate cycle (hypothesize → critique → audit → revise → synthesize → ratify)

Uses standard debate cycle from REFERENCE.md with these design-board specifics:

- **hypothesize:** Members propose concrete implementation designs: file structure, APIs, data models, component boundaries.
- **audit:** Writes to `phase-2/WHITEBOARD-R{N}.md` `## Audit` section.
- **synthesize:** Uses incremental read protocol from REFERENCE.md. Writes Evidence Map + Draft Design in phase-2/SYNTHESIS.md. Round 2+: add entry ID → summary mapping table.
- **ratify:** If not ratified and rounds remain, incorporate push-back concerns into next round. Next round starts at `hypothesize` (leader creates WHITEBOARD-R{N+1}.md). If not ratified and max rounds exhausted: leader writes "best available design" in `## Final Design` with explicit uncertainty markers.

### concluded

- Leader writes `## Final Design` in phase-2/SYNTHESIS.md by promoting the ratified Draft Design (or best available design on exhaustion).
- Leader generates the Plan File at `docs/plans/YYYY-MM-DD-{topic}.md` (see Plan File Template below).
- Content is derived from both phase-1/SYNTHESIS.md (technology background) and phase-2/SYNTHESIS.md (implementation design).
- Verify the Plan File was created successfully.
- Delete `docs/discussions/{discussion-id}/` directory after successful export.
- If discussion was interrupted (no Final Design): skip Plan File export, delete discussion directory manually.

### Board-Specific Communication Note

- Phase 2 framing broadcast MUST include Phase 1 Technology Conclusion summary (Push-based context injection).

---

# Reference Layer

## WHITEBOARD.md Templates

### Phase 1 WHITEBOARD (single file, no round-split)

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

No Audit section in Phase 1 (audit is Phase 2 only). No round-split — all content in a single file.

### Phase 2 Base WHITEBOARD (Topic + Framing only)

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
```

This base file becomes **read-only** after framing completes. Per-round content goes into WHITEBOARD-R{N}.md files (see REFERENCE.md for per-round template).

## SYNTHESIS.md Templates

### Phase 1 SYNTHESIS

Path: `docs/discussions/{discussion-id}/phase-1/SYNTHESIS.md`

```markdown
# SYNTHESIS — {discussion-id} / Phase 1: Technical Investigation
> Status: setup

## Evidence Map
## Technology Conclusion
## User Review Outcome
```

### Phase 2 SYNTHESIS

Path: `docs/discussions/{discussion-id}/phase-2/SYNTHESIS.md`

```markdown
# SYNTHESIS — {discussion-id} / Phase 2: Design
> Status: setup
> Round: 0
> Max Rounds: 10

## Evidence Map
## Draft Design
## Round Context Packet
## Ratification History
## Minority Report
## Final Design
```

Leader-only files. See Entry Formats above and REFERENCE.md for section content structure.

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

## Board-Specific Conflict Rule

| # | Rule | Rationale |
|---|------|-----------|
| 11 | Phase 1 files are read-only during Phase 2 | Prevents retroactive modification of settled technology decisions |

This extends the base conflict prevention rules (1-10) in REFERENCE.md.
