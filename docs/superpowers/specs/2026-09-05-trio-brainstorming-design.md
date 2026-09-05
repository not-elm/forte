# trio-brainstorming Skill Design

**Date:** 2026-09-05
**Status:** Draft (pending user review)

## Goal

Add a new forte skill `trio-brainstorming` that runs the `superpowers:brainstorming` dialogue with three participants: Claude (the session, which talks to the human), Codex (invoked via `codex exec`), and the human.

Codex is an **equal participant**, not a reviewer. Its primary contribution is collaborating with Claude on **discovering which clarifying questions to ask the human**, and secondarily on originating implementation approaches independently of Claude.

## Positioning in the Workflow

Drop-in replacement for `superpowers:brainstorming` at the head of the pipeline:

```
trio-brainstorming → spec → (spec-review) → writing-plans → ...
```

The exit is identical to brainstorming: spec written to `docs/superpowers/specs/`, committed, reviewed by the human, then hand off to `superpowers:writing-plans`. Existing downstream skills (`spec-review`, `autopilot`) are unaffected.

## Design Decisions (from brainstorming)

| Decision | Choice | Rationale |
|---|---|---|
| Codex role | Equal participant | User requirement |
| Codex focus | Question discovery first, approaches second | User requirement: 「質問の洗い出しを両者で協力させる」 |
| Pacing | Hybrid: two checkpoints, extra rounds only for a named unresolved decision | Recommended by Codex during this brainstorm; balances latency (3–9 min/call) against the moment Codex adds most value (after answers invalidate the initial frame) |
| Path coverage | bounded: CP1 only. architectural: CP1 + CP2. spike: no Codex | Codex value is low on spikes; one call is worth it on bounded work |
| Relation to superpowers:brainstorming | Overlay, not reimplementation | CLAUDE.md: never duplicate stage logic. Upstream flow stays authoritative |
| Exit | Same as brainstorming | Keeps autopilot / spec-review compatible |

## Architecture

### Overlay Model

`trio-brainstorming/SKILL.md` first invokes `superpowers:brainstorming` via the Skill tool so the upstream flow (HARD-GATE, three-path classification, one-question-at-a-time, design sections, spec location, writing-plans hand-off) is loaded and remains authoritative. The overlay then adds exactly four things:

1. A **State file** that Claude maintains and embeds in every Codex prompt.
2. **Checkpoint 1 (CP1)** — independent question discovery, before the first question reaches the human.
3. **Checkpoint 2 (CP2)** — remaining questions + independent approaches, architectural path only.
4. **Provenance and disagreement rules** for what the human sees.

Insertion points are named by **action**, not by upstream checklist item name, so upstream renames do not break the overlay:

- CP1 fires "after context exploration completes, before the first clarifying question is asked."
- CP2 fires "before the 2–3 approaches are presented."

The overlay overrides only two upstream behaviors: how question candidates are produced, and how approach candidates are produced. Everything else follows brainstorming unchanged.

### Codex Invocation

All Codex calls follow `codex-engine/REFERENCE.md` (detached `codex exec`, read-only, sentinel file, 900 s Monitor ceiling, full-file read-back, cleanup on every path). The skill owns only its prompts and prefixes:

| Checkpoint | `{PREFIX}` |
|---|---|
| CP1 | `trio-cp1` |
| CP2 | `trio-cp2` |

No model, effort, or timeout overrides. While Codex runs, Claude displays one status line to the human — "Codex が考えています（3〜9 分）" — and uses the wait to do its own independent enumeration.

### Calls per Path

| Path | CP1 | CP2 |
|---|---|---|
| spike | — | — |
| bounded | yes | — |
| architectural | yes | yes, when a trigger fires |

## State File

Location: `docs/brainstorms/{topic-id}/STATE.md`, where `{topic-id}` is a kebab-case slug of the request. `docs/brainstorms/` must be gitignored (the repo already ignores `docs/`; the skill checks and adds the line if missing, mirroring the board skills' `docs/discussions/` rule). The directory is deleted after the spec is written, matching the board skills' lifecycle.

Codex is stateless, so this file is its only memory. **Claude is the sole writer.**

```markdown
# Brainstorm State — {topic-id}
> Revision: {N}        <!-- +1 per Codex call -->
> Path: {bounded|architectural}
> Phase: {clarifying|approaches|design}

## User Brief
- Original request: {verbatim}
- Goal / success criteria:
- Hard constraints / non-goals:

## Evidence
- {file:line} — {finding and implication}

## Decisions
| ID | Decision | Source | Status |
| D1 | ... | human U3 | confirmed |
<!-- Source: human / claude / codex. Human decisions and model recommendations must stay distinguishable -->

## Assumptions
| ID | Assumption | Owner | Impact if false |
| A1 | ... | claude | ... |
<!-- Used to evaluate the CP2 trigger -->

## Human Answers
- U1 (→Q1): "{verbatim}"
<!-- Consequential answers verbatim. Never summarize an answer that backs a Decision -->

## Question Ledger
| ID | Question | Origin | Decision affected | Status |
| Q1 | ... | codex | D2 | answered U1 |
<!-- Origin: claude / codex / joint. Status: pending / answered / deferred (reason) / superseded -->

## Positions & Dissent
- Claude: ...
- Codex (rev N): ...
- Unresolved: ...
- Codex proposals not adopted: {proposal} — {reason}

## Changes Since Last Codex Call
- ...
<!-- Cleared immediately after a Codex result is read; accumulates until the next call -->
```

**Update rules**
- After each human answer: update Human Answers, Question Ledger, Decisions, Changes.
- After each Codex read-back: update Question Ledger and Positions, then clear Changes.
- Exclude tool logs, raw file contents, rejected wording, and Claude's private reasoning. Evidence carries only the point and a `file:line`; Codex reads the file itself if it needs more.
- Target ≤ 200 lines. If exceeded, summarize older routine Human Answers, but keep verbatim any answer cited by a Decision.
- On the bounded path, Assumptions / Positions / Changes may stay empty. The template is not forked.

## Checkpoint 1 — Independent Question Discovery

**Trigger:** context exploration is complete and User Brief + Evidence are written. Before the first clarifying question.

**Procedure**
1. Save State as Revision 1.
2. Launch Codex with `{PREFIX}` = `trio-cp1`. Prompt = full State + the CP1 request below.
3. While Codex runs, and **before reading its output**, Claude writes its own question candidates to the Question Ledger with `origin: claude`. Ordering is mandatory: neither party's frame may contaminate the other's initial list.
4. Read Codex output; add its questions with `origin: codex`. Merge semantically identical questions into one row with `origin: joint`. Move any Codex evidence into Evidence.
5. Rank by the consequence of the decision each answer affects (not by origin). Ask the human one question at a time per brainstorming rules, each tagged `[Codex]`, `[Claude]`, or `[共同]`.
6. Follow-up questions between checkpoints are Claude's alone; add them to the Ledger with `origin: claude`.

**CP1 request (appended to State)**
```
You are an equal participant in a design brainstorm. Read the State above.
List up to 5 questions we should ask the human, in priority order.
Each question MUST include the decision its answer changes, in one line.
Anything you can verify by reading the repository is NOT a question — report it
as Evidence with file:line instead.
Output:
| Question | Decision affected | Why now |
followed by an "Additional Evidence" list (file:line — finding).
```

## Checkpoint 2 — Remaining Questions + Independent Approaches

Architectural path only.

**Trigger (either):**
- Question Ledger has zero `pending` rows, or
- a human answer invalidates a row in Assumptions. Claude makes this call and records the Assumption ID in Changes.

**Procedure**
1. Save State as Revision +1, with Changes Since Last Codex Call populated.
2. Launch Codex with `{PREFIX}` = `trio-cp2`.
3. While Codex runs, and **before reading its output**, Claude writes its own 2–3 approaches to Positions.
4. Read Codex output. Merge approaches: identical ones collapse to one entry with `origin: joint`; distinct ones are listed side by side. New Codex questions go to the Ledger; if any are `pending`, ask them before presenting approaches.
5. Proceed to brainstorming's "propose 2–3 approaches" step. Each approach carries its origin tag. If Claude and Codex recommend different approaches, both rationales are shown as-is.

**CP2 request (appended to State)**
```
Read the State above, especially "Changes Since Last Codex Call".
(1) Up to 3 remaining questions that directly gate an undecided decision.
(2) 2–3 implementation approaches, each with pros, cons, and your recommendation.
(3) Any disagreement with Claude's positions in "Positions & Dissent", stated explicitly.
Output: question table (same columns as before) + approaches + disagreements + Confidence (High/Medium/Low, with reason).
```

### Additional Rounds

After CP2, the CP2 procedure may run again **only if** the Ledger still has `pending` rows tied to a named undecided Decision. "Just in case" re-calls are forbidden.

## Provenance and Disagreement

- Merge wording into one natural question; keep provenance via a light tag. Do not repeat "Codex asks:" on every line.
- **Factual disagreement** (how code behaves, what a file contains): Claude investigates and settles it; result recorded in Evidence. The human is not asked to referee.
- **Preference / priority disagreement**: present both rationales and ask the human once.
- Unresolved dissent stays in Positions & Dissent and is transcribed into the spec's "Alternatives considered" section.

## Failure Handling

| Situation | Action |
|---|---|
| `codex` not installed (exit 127) | Show one line: `⚠ Codex 不在: 通常の brainstorming で続行`. Skip every remaining checkpoint. Keep the State file (the Ledger is still useful). |
| Codex non-zero exit | Surface `CODEX_LOG` highlights, continue this checkpoint with Claude alone. Retry Codex at the next checkpoint. |
| 900 s ceiling exceeded | Kill `CODEX_PID`, continue alone. Record `Codex (rev N): timeout` in Positions so absence is not mistaken for agreement. |
| Codex output malformed | Import what is readable; mark rows `origin: codex (unstructured)`. |
| Human answered while Codex was running | After read-back, reconcile against answers received since the call's Revision. Mark already-answered Codex questions `superseded`; do not present them. |

Temp files are cleaned on every path per codex-engine.

## Deliverables

| File | Change |
|---|---|
| `skills/trio-brainstorming/SKILL.md` | New. Frontmatter (name, description with triggers: trio brainstorming, codex brainstorming, 3者ブレスト, Codexと一緒に設計, brainstorm with codex) + the rules above, including the State template and both Codex request templates. |
| `.claude-plugin/plugin.json` | Bump version to 1.37.0. |
| `CLAUDE.md` | Add one line to Repository Structure; add `trio-brainstorming` to the Codex-based skills list in Key Patterns. |

## Verification

The skill is a natural-language spec, so verification is by running it:

1. **Bounded path** — run on forte itself with a small topic (e.g. "add a `--codex-only` flag to parallel-research"). Expect exactly one Codex call (CP1), a Ledger mixing claude/codex/joint origins, origin tags on questions shown to the human, and no CP2.
2. **Architectural path** — run on a medium topic. Expect CP1 → questions consumed → CP2 fires → approaches include at least one Codex-originated option → spec saved → writing-plans hand-off. Observe whether State stays ≤ 200 lines.
3. **Codex unavailable** — remove `codex` from `PATH`; expect the one-line warning and a normal brainstorming run to completion.
4. **Cleanup** — after the spec is written, `docs/brainstorms/{topic-id}/` no longer exists.

## Out of Scope

- Sharing the State format with design-board or other board skills.
- Per-skill model / reasoning-effort overrides (forbidden by codex-engine).
- Automatic chaining into spec-review (autopilot's responsibility).
- Modifying `superpowers:brainstorming` itself (external plugin).
