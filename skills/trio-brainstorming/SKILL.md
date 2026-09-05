---
name: trio-brainstorming
description: >
  Use when turning an idea into a design/spec through a three-party dialogue between Claude, Codex CLI, and the human. Runs superpowers:brainstorming as the base flow and adds Codex as an equal participant at two checkpoints: independent clarifying-question discovery (CP1) and remaining questions plus independent implementation approaches (CP2, architectural path only).
  Triggers: trio brainstorming, codex brainstorming, 3者ブレスト, Codexと一緒に設計, brainstorm with codex
---

# Trio Brainstorming

## Overview

Brainstorm with three participants at the table: **Claude** (this session, which talks to the human), **Codex** (OpenAI Codex CLI, invoked per checkpoint), and the **human**. Codex is an equal participant, not a reviewer — it originates clarifying questions, implementation approaches, and objections on the same footing as Claude.

This skill is an **overlay** on `superpowers:brainstorming`. The upstream skill remains authoritative for the dialogue flow; this skill adds exactly four things:

1. A **State file** that Claude maintains and embeds in every Codex prompt (Codex is stateless between calls).
2. **Checkpoint 1 (CP1)** — Claude and Codex independently enumerate the questions worth asking the human, before the first question is asked.
3. **Checkpoint 2 (CP2)** — after consequential answers arrive, Codex proposes remaining questions and independent approaches in a single call (architectural path only).
4. **Provenance and disagreement rules** for what the human sees.

**Why two checkpoints:** each Codex call costs 3–9 minutes of wall-clock (the user's reasoning-effort setting decides; see codex-engine). Calling Codex after every human answer would stall the dialogue; calling it only once would lose Codex exactly when answers invalidate the initial framing. Two checkpoints — one before the interview, one before approaches — capture most of the value.

**Prerequisites:**
- `superpowers:brainstorming` (superpowers plugin) — hard requirement; stop with an error if unavailable
- `codex` CLI (`npm i -g @openai/codex`) — optional; if unavailable the skill degrades to plain brainstorming (see Failure Handling)

**Shared contract:** Codex invocation mechanics live in codex-engine REFERENCE.md. Before the first checkpoint:

1. Use `Glob pattern="**/codex-engine/REFERENCE.md"` to locate the file
2. Read it

If not found, display: `> Warning: codex-engine reference not found. Using inline rules only.`

## When to Use

- You want a second, independent AI perspective on **which questions to ask** before a design solidifies
- You are about to run brainstorming on a task large enough that a 3–9 minute pause per checkpoint is worth it
- You want implementation approaches originated by two models independently, not one model's preferred option plus variations

**When NOT to use:**
- Spikes or trivial changes — plain `superpowers:brainstorming` is faster and this skill calls no Codex on the spike path anyway
- You want Codex to *review* a finished spec — use `forte:spec-review`
- Multi-round agent debate without a human in the loop — use `forte:discussion-board` or `forte:design-board`

## Overlay Model

### Step 0: Load the base flow

Invoke `superpowers:brainstorming` via the Skill tool, passing this skill's arguments through unchanged. Its instructions load into the current turn. Follow them exactly — classification, HARD-GATE, one question per message, design sections, spec self-review, spec location, the writing-plans hand-off — **except** at the two insertion points below.

**Precedence:** where this skill and brainstorming both speak, this skill wins only on (a) how question candidates are produced and (b) how approach candidates are produced. Everything else is brainstorming's.

### Insertion points (named by action, not by upstream checklist wording)

| Insertion point | Fires when | What happens |
|---|---|---|
| **CP1** | Context exploration is complete and the first clarifying question is about to be asked | Independent question discovery (see Checkpoint 1) |
| **CP2** | The 2–3 approaches are about to be presented, and a CP2 trigger has fired | Remaining questions + independent approaches (see Checkpoint 2) |

### Calls per path

Classification is brainstorming's (spike / bounded / architectural). Codex participation scales with it:

| Path | CP1 | CP2 |
|---|---|---|
| spike | — | — |
| bounded | yes | — |
| architectural | yes | yes, when a trigger fires |

Announce the path and the resulting Codex plan in the same breath as brainstorming's classification, e.g. "this looks architectural, so Codex will join at two checkpoints."

### While Codex runs

Display exactly one status line to the human:

> "Codex が考えています（3〜9 分）。その間に私も候補を出します。"

Then do Claude's own independent enumeration (see each checkpoint). Do not ask the human anything while waiting, and do not read Codex output before Claude's own list is written.

## State File

**Location:** `docs/brainstorms/{topic-id}/STATE.md`, where `{topic-id}` is a kebab-case slug of the request (e.g. `parallel-research-codex-only-flag`).

**Ignore rule:** before the first write, run `git check-ignore -q docs/brainstorms`. If it exits non-zero, append `docs/brainstorms/` to `.gitignore` (mirrors the board skills' `docs/discussions/` rule).

**Lifecycle:** created at CP1, deleted (`rm -rf docs/brainstorms/{topic-id}`) after the spec is written and committed. On the spike path no State file is created.

**Sole writer:** Claude. Codex reads it only as embedded prompt text.

### Template

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
|----|----------|--------|--------|
| D1 | ... | human U3 | confirmed |
<!-- Source: human / claude / codex. Human decisions and model recommendations must stay distinguishable -->

## Assumptions
| ID | Assumption | Owner | Impact if false |
|----|------------|-------|-----------------|
| A1 | ... | claude | ... |
<!-- Used to evaluate the CP2 trigger -->

## Human Answers
- U1 (→Q1): "{verbatim}"
<!-- Consequential answers verbatim. Never summarize an answer that backs a Decision -->

## Question Ledger
| ID | Question | Origin | Decision affected | Status |
|----|----------|--------|-------------------|--------|
| Q1 | ... | codex | D2 | answered U1 |
<!-- Origin: claude / codex / joint. Status: pending / answered U{n} / deferred ({reason}) / superseded -->

## Positions & Dissent
- Claude: ...
- Codex (rev N): ...
- Unresolved: ...
- Codex proposals not adopted: {proposal} — {reason}

## Changes Since Last Codex Call
- ...
<!-- Cleared immediately after a Codex result is read; accumulates until the next call -->
```

### Update rules

- **After each human answer:** append to Human Answers (verbatim), set the answered row's Status in Question Ledger, add/update Decisions, append a line to Changes Since Last Codex Call. If the answer contradicts an Assumptions row, note `invalidates A{n}` in Changes — this is a CP2 trigger.
- **After each Codex read-back:** merge Codex questions into Question Ledger, move Codex evidence into Evidence, record Codex's position in Positions & Dissent as `Codex (rev N)`, then **clear** Changes Since Last Codex Call.
- **Exclude:** tool logs, raw file contents, rejected wording, Claude's private reasoning. Evidence carries only the point and a `file:line`; Codex can read the file itself.
- **Size:** target ≤ 200 lines. If exceeded, summarize older routine Human Answers, but keep verbatim any answer cited in a Decisions row.
- **Bounded path:** Assumptions, Positions & Dissent, and Changes may stay empty. Do not fork the template.

## Checkpoint 1 — Independent Question Discovery

**Trigger:** brainstorming's context exploration is complete; User Brief and Evidence are written to State. The first clarifying question has not yet been asked. Bounded and architectural paths.

**Procedure:**

1. Save State as `Revision: 1`, `Phase: clarifying`.
2. Launch Codex — the canonical invocation from codex-engine REFERENCE.md with:

   | Value | |
   |-------|---|
   | `{PREFIX}` | `trio-cp1` |
   | `{prompt}` | Full contents of STATE.md, followed by the CP1 request below |

3. Display the waiting status line. Then, **before reading any Codex output**, write Claude's own question candidates into Question Ledger with `Origin: claude`, each with the Decision it affects. This ordering is mandatory: neither party's frame may contaminate the other's initial list.
4. Wait per the reference's wait protocol (Monitor until-loop on `CODEX_DONE_MARKER`, 900 s ceiling). Read `CODEX_FINAL_OUTPUT` from line 1 through EOF. Clean up temp files.
5. Merge: add Codex questions with `Origin: codex`. Collapse semantically identical questions into one row with `Origin: joint`, keeping the clearer wording. Move any "Additional Evidence" into Evidence.
6. Rank pending rows by the consequence of the decision each answer affects — not by origin. Then hand control back to brainstorming's one-question-at-a-time interview, prefixing each question with its origin tag: `[Codex]`, `[Claude]`, or `[共同]`.
7. Follow-up questions Claude thinks of between checkpoints are Claude's alone: add them to the Ledger with `Origin: claude` and ask them normally.

**CP1 request (appended verbatim after the State contents):**

```
---
## Request

You are an equal participant in a design brainstorm. Read the State above.
List up to 5 questions we should ask the human, in priority order.
Each question MUST include the decision its answer changes, in one line.
Anything you can verify by reading the repository is NOT a question — report it
as Evidence with file:line instead.

Output exactly:

### Questions
| Question | Decision affected | Why now |
|----------|-------------------|---------|

### Additional Evidence
- {file:line} — {finding}
```

## Checkpoint 2 — Remaining Questions + Independent Approaches

Architectural path only.

**Trigger (either condition):**
- Question Ledger has zero rows with `Status: pending`, or
- a human answer invalidated an Assumptions row (Changes contains `invalidates A{n}`).

Claude evaluates the trigger after every human answer. If neither condition holds when brainstorming reaches the approaches step, keep asking pending questions first — the approaches step waits for CP2.

**Procedure:**

1. Save State as `Revision: {N+1}`, `Phase: approaches`, with Changes Since Last Codex Call populated.
2. Launch Codex — canonical invocation with:

   | Value | |
   |-------|---|
   | `{PREFIX}` | `trio-cp2` |
   | `{prompt}` | Full contents of STATE.md, followed by the CP2 request below |

3. Display the waiting status line. Then, **before reading any Codex output**, write Claude's own 2–3 approaches (name, one-line summary, pros, cons, recommendation) into Positions & Dissent under `Claude:`.
4. Wait and read back per the reference. Clean up temp files.
5. Merge approaches: identical approaches collapse to one entry tagged `joint`; distinct approaches are listed side by side with their origin. Record Codex's recommendation and any disagreement under `Codex (rev N):`. Add Codex's new questions to the Ledger with `Origin: codex`.
6. If any Ledger row is now `pending`, ask those questions first (one at a time, origin-tagged). Then proceed to brainstorming's "propose 2–3 approaches" step with the merged list. Each approach carries its origin tag. If Claude and Codex recommend different approaches, present both rationales as-is — do not manufacture consensus.

**CP2 request (appended verbatim after the State contents):**

```
---
## Request

Read the State above, especially "Changes Since Last Codex Call".

(1) Up to 3 remaining questions that directly gate an undecided decision.
(2) 2–3 implementation approaches, each with pros, cons, and your recommendation.
(3) Any disagreement with Claude's positions in "Positions & Dissent", stated explicitly.

Output exactly:

### Questions
| Question | Decision affected | Why now |
|----------|-------------------|---------|

### Approaches
#### {Approach name}
- Summary:
- Pros:
- Cons:
- Recommendation: {recommended | acceptable | not recommended} — {reason}

### Disagreements
- {Claude position} — {your objection and reason}

### Confidence
{High | Medium | Low} — {reason}
```

### Additional rounds

After CP2, the CP2 procedure may run again **only if** the Question Ledger still has `pending` rows whose "Decision affected" names a Decisions row that is not `confirmed`. "Just in case" re-calls are forbidden. Each additional round increments Revision.

## Provenance and Disagreement

- **Merge wording, keep provenance.** Present one natural question; tag it `[Codex]`, `[Claude]`, or `[共同]`. Do not prefix every line with "Codex asks:".
- **Factual disagreement** (how code behaves, what a file contains): Claude investigates with Read/Grep and settles it. Record the result in Evidence. Never ask the human to referee a factual dispute between models.
- **Preference or priority disagreement:** present both rationales and ask the human once, as a single question.
- **Unresolved dissent** stays in Positions & Dissent and is transcribed into the spec's "Alternatives considered" (or equivalent) section when brainstorming writes the spec.
- **Deferred or rejected Codex proposals** are recorded with a reason under "Codex proposals not adopted" so Codex sees the disposition on its next call.

## Failure Handling

| Situation | Action |
|---|---|
| `codex` not installed (`CODEX_DONE_MARKER` = `127`) | Show one line: `⚠ Codex 不在: 通常の brainstorming で続行`. Skip every remaining checkpoint. Keep the State file — the Ledger is still useful for Claude. |
| Codex non-zero exit (other) | Surface `CODEX_LOG` highlights, continue this checkpoint with Claude's list alone. Try Codex again at the next checkpoint. |
| 900 s ceiling exceeded | `kill "$CODEX_PID"`, continue alone. Record `Codex (rev N): timeout` in Positions & Dissent so absence is not mistaken for agreement. |
| Codex output malformed | Import what is readable; mark rows `Origin: codex (unstructured)`. |
| Human answered while Codex was running | After read-back, reconcile against Human Answers added since the call's Revision. Mark already-answered Codex questions `superseded`; do not present them. |
| `superpowers:brainstorming` unavailable | Stop: "trio-brainstorming requires the superpowers plugin (superpowers:brainstorming)." |

Temp files are cleaned on every path per codex-engine.

## Common Mistakes

Invocation-level mistakes (subcommand, approval policy, CLI-argument prompts, truncation, model/effort flags, `run_in_background`) are covered in codex-engine REFERENCE.md. Skill-specific:

- **Reading Codex output before writing Claude's own list** — defeats independent discovery. Write first, read second, at both checkpoints.
- **Calling Codex on every human answer** — the dialogue stalls for minutes per turn. Two checkpoints, plus named-decision rounds only.
- **Sending the whole conversation to Codex** — send STATE.md, which excludes logs and private reasoning. If STATE.md exceeds 200 lines, summarize routine answers, not decisions.
- **Treating a timeout or failure as agreement** — always record `timeout` / `unavailable` in Positions & Dissent.
- **Asking the human to settle a factual dispute** — investigate it instead.
- **Overriding upstream flow beyond the two insertion points** — the HARD-GATE, classification, one-question-per-message, spec location, and writing-plans hand-off are brainstorming's.
- **Forgetting cleanup** — delete `docs/brainstorms/{topic-id}` after the spec is committed.
