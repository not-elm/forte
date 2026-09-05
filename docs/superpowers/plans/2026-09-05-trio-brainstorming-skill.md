# trio-brainstorming Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new forte skill `trio-brainstorming` that runs `superpowers:brainstorming` as a three-party dialogue (Claude, Codex, human), with Codex joining as an equal participant at two checkpoints: independent question discovery (CP1) and remaining questions + independent approaches (CP2).

**Architecture:** One new standalone `skills/trio-brainstorming/SKILL.md` — an overlay that first loads `superpowers:brainstorming` via the Skill tool and then adds exactly four things: a Claude-maintained State file that is embedded in every Codex prompt, checkpoint CP1, checkpoint CP2, and provenance/disagreement rules. Codex invocation mechanics are delegated entirely to `codex-engine/REFERENCE.md`. Plus registration edits to `CLAUDE.md` and a version bump in `.claude-plugin/plugin.json`.

**Tech Stack:** Markdown (SKILL.md skill spec), Skill tool chaining, Codex CLI via codex-engine contract (detached `codex exec`, sentinel file, Monitor wait), git.

**Spec:** `docs/superpowers/specs/2026-09-05-trio-brainstorming-design.md`

## Global Constraints

- The overlay never duplicates upstream stage logic: HARD-GATE, three-path classification, one-question-at-a-time, design sections, spec location `docs/superpowers/specs/`, and the writing-plans hand-off all come from `superpowers:brainstorming`. The overlay's authority is limited to its own footprint: question-candidate production, approach-candidate production, provenance tagging in what the human sees, the State file and its lifecycle, checkpoint sequencing relative to the interview and the approaches step, and the spec's "Alternatives considered" section.
- Insertion points are named by **action** ("before the first clarifying question", "before the 2–3 approaches are presented"), never by upstream checklist item names.
- Codex calls follow `codex-engine/REFERENCE.md` verbatim. `{PREFIX}` values: `trio-cp1`, `trio-cp2`. No `-m`, `--model`, `-c model_reasoning_effort`, or per-skill timeout.
- Calls per path: spike = none; bounded = CP1 only; architectural = CP1 + CP2 (CP2 only when a trigger fires).
- State file at `docs/brainstorms/{topic-id}/STATE.md`; Claude is the sole writer; ≤ 200 lines target; `docs/brainstorms/` ignored via `.git/info/exclude`, never via the tracked `.gitignore`; directory deleted after the human approves the in-chat design (bounded path) or after the spec is written and committed (architectural path).
- Every Codex failure mode degrades to plain brainstorming with a visible note; absence is never recorded as agreement.
- Frontmatter Triggers line includes these exact keywords: `trio brainstorming, codex brainstorming, 3者ブレスト, Codexと一緒に設計, brainstorm with codex`
- Version bump touches `.claude-plugin/plugin.json` only (`1.36.0` → `1.37.0`); `marketplace.json` has no version field.
- This repo has no test framework; every verification step is a shell command with its expected output stated.
- `docs/` is gitignored in this repo; spec and plan files are tracked via `git add -f`. Skill files under `skills/` are tracked normally.

---

### Task 1: Create skills/trio-brainstorming/SKILL.md

**Files:**
- Create: `skills/trio-brainstorming/SKILL.md`

**Interfaces:**
- Consumes: `codex-engine/REFERENCE.md` (canonical invocation, wait protocol, read-back, failure table) — referenced, not copied. `superpowers:brainstorming` — loaded via Skill tool at runtime.
- Produces: the complete skill file; Task 2 registers the name `trio-brainstorming` and the tree description "Three-party brainstorming (Claude + Codex + human) as an overlay on superpowers:brainstorming" in CLAUDE.md.

- [ ] **Step 1: Create the file with this exact content**

Create `skills/trio-brainstorming/SKILL.md` containing exactly:

`````markdown
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

If not found, tell the human in one line: `> Warning: codex-engine reference not found. Codex のチェックポイントをスキップし、通常の brainstorming で続行します。` Then skip every checkpoint and run the base flow unchanged. There is no inline fallback: without the reference no Codex call can be constructed.

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

When building brainstorming's task list, insert "CP1: independent question discovery" immediately before "Ask clarifying questions" and, on the architectural path, "CP2: remaining questions and approaches" immediately before "Propose 2–3 approaches" — otherwise the checkpoints have no anchor in the list the agent actually works from.

**Precedence:** where this skill and brainstorming both speak, this skill wins on the following and nothing else:

- how question candidates are produced;
- how approach candidates are produced;
- provenance tagging in what the human sees;
- the State file and its lifecycle;
- checkpoint sequencing relative to the interview and the approaches step;
- the "Alternatives considered" section of the written spec.

Everything else is brainstorming's.

**HARD-GATE carve-out:** writing STATE.md and launching a read-only Codex run are not implementation actions and do not trip brainstorming's HARD-GATE; on the bounded path the State file is scratch, not the spec or plan document that path forbids.

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
| architectural | yes | yes — before the approaches step, once the trigger is met |

Announce the path and the resulting Codex plan in the same breath as brainstorming's classification, e.g. "this looks architectural, so Codex will join at two checkpoints."

A mid-task path upgrade (brainstorming's one-way ratchet) re-arms CP1, which fires at the next question boundary rather than being skipped as past its moment; CP2 then applies normally if the new path is architectural.

### While Codex runs

Display exactly one status line to the human:

> "Codex が考えています（3〜9 分）。その間に私も候補を出します。"

Then do Claude's own independent enumeration (see each checkpoint). Do not ask the human anything while waiting, and do not read Codex output before Claude's own list is written.

## State File

**Location:** `docs/brainstorms/{topic-id}/STATE.md`, where `{topic-id}` is a kebab-case slug of the request (e.g. `parallel-research-codex-only-flag`).

**Ignore rule:** before the first write, run `git check-ignore -q docs/brainstorms`. If it exits non-zero, append `docs/brainstorms/` to `.git/info/exclude`. NEVER edit the tracked `.gitignore` — a brainstorm must not leave an unrequested diff in the user's repository.

**Lifecycle:** created when context exploration completes, at the moment User Brief and Evidence are written; CP1 launches immediately after that write. Deleted after the human approves the in-chat design (bounded path) or after the spec is written and committed (architectural path). Run the delete as `rm -rf docs/brainstorms/{topic-id}` only when `{topic-id}` resolves to a non-empty slug — an unresolved placeholder would remove the whole scratch root. On the spike path no State file is created.

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
- U1 (→Q1, rev 1): "{verbatim}"
<!-- Consequential answers verbatim. rev N = the State Revision current when the answer arrived -->
<!-- Never summarize an answer that backs a Decision -->

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

- **After each human answer:** append to Human Answers (verbatim, marked `rev N` with the Revision current at that moment), set the answered row's Status in Question Ledger, add/update Decisions, append a line to Changes Since Last Codex Call. If the answer contradicts an Assumptions row, note `invalidates A{n}` in Changes — this is a CP2 trigger.
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
6. Rank pending rows by the consequence of the decision each answer affects — not by origin. Then hand control back to brainstorming's one-question-at-a-time interview, prefixing each question with its origin tag: `[Codex]`, `[Claude]`, or `[Joint]`.
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

**Trigger:** "Changes Since Last Codex Call" is non-empty — at least one human answer has landed since the previous Codex call — **and** either:
- the Question Ledger has zero rows with `Status: pending`, or
- a human answer invalidated an Assumptions row (Changes contains `invalidates A{n}`).

The non-emptiness condition comes first and is not optional: with an empty Changes section Codex would reason over State it has already seen, which buys nothing and costs another 3–9 minutes.

Claude evaluates the trigger after every human answer. If it has not fired when brainstorming reaches the approaches step, keep asking pending questions first — the approaches step waits for CP2. If there is nothing left to ask and Changes is still empty (CP1 produced no questions and none were asked), CP2 does not fire at all: proceed to approaches with Claude's list and record `Codex (rev N): not called — no new information since CP1` in Positions & Dissent.

**Procedure:**

1. Save State as `Revision: {N+1}`, `Phase: approaches`, with Changes Since Last Codex Call populated.
2. Launch Codex — canonical invocation with:

   | Value | |
   |-------|---|
   | `{PREFIX}` | `trio-cp2` |
   | `{prompt}` | Full contents of STATE.md, followed by the CP2 request below |

3. Display the waiting status line. Then, **before reading any Codex output**, write Claude's own 2–3 approaches (name, one-line summary, pros, cons, recommendation) into Positions & Dissent under `Claude:`.
4. Wait and read back per the reference. Clean up temp files.
5. Merge approaches: identical approaches collapse to one entry tagged `joint`; distinct approaches are listed side by side with their origin. Record Codex's recommendation and any disagreement under `Codex (rev N):`. Add Codex's new questions to the Ledger with `Origin: codex`, collapsing any that are semantically identical to an existing row into one row with `Origin: joint`, exactly as CP1 step 5 does.
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

**Evaluation point:** after the questions merged at the previous CP2 have been asked and answered — never immediately after read-back, which would contradict step 6.

At that point, the CP2 procedure may run again **only if** an answer received since the last Codex call invalidated an Assumptions row or changed a Decisions row that is not `confirmed`. Pendingness on its own is not a reason, and "just in case" re-calls are forbidden. Each additional round increments Revision.

## Provenance and Disagreement

- **Merge wording, keep provenance.** Present one natural question; tag it `[Codex]`, `[Claude]`, or `[Joint]`. All three tags may be localized to the session language (e.g. `[共同]`), but never mix languages across the set. Do not prefix every line with "Codex asks:".
- **Factual disagreement** (how code behaves, what a file contains): Claude investigates with Read/Grep and settles it. Record the result in Evidence. Never ask the human to referee a factual dispute between models.
- **Preference or priority disagreement:** present both rationales and ask the human once, as a single question.
- **Unresolved dissent** stays in Positions & Dissent and is transcribed into the spec's "Alternatives considered" (or equivalent) section when brainstorming writes the spec.
- **Deferred or rejected Codex proposals** are recorded with a reason under "Codex proposals not adopted" so Codex sees the disposition on its next call.

## Failure Handling

| Situation | Action |
|---|---|
| `codex` not installed (the sentinel file contains `127`) | Show one line: `⚠ Codex 不在: 通常の brainstorming で続行`. Record `Codex (rev N): unavailable` in Positions & Dissent. Skip every remaining checkpoint. Keep the State file — the Ledger is still useful for Claude. |
| Codex non-zero exit (other) | Surface `CODEX_LOG` highlights, record `Codex (rev N): failed — {reason}` in Positions & Dissent, continue this checkpoint with Claude's list alone. Try Codex again at the next checkpoint. |
| 900 s ceiling exceeded | `kill "$CODEX_PID"`, continue alone. Record `Codex (rev N): timeout` in Positions & Dissent so absence is not mistaken for agreement. |
| Codex output malformed | Import what is readable; mark rows `Origin: codex (unstructured)`. |
| Human answered while Codex was running | After read-back, reconcile against Human Answers whose `rev` marker equals the Revision the call was launched at — those arrived while Codex was thinking. Mark already-answered Codex questions `superseded`; do not present them. |
| `superpowers:brainstorming` unavailable | Stop: "trio-brainstorming requires the superpowers plugin (superpowers:brainstorming)." |

Temp files are cleaned on every path per codex-engine.

## Common Mistakes

Invocation-level mistakes (subcommand, approval policy, CLI-argument prompts, truncation, model/effort flags, `run_in_background`) are covered in codex-engine REFERENCE.md. Skill-specific:

- **Reading Codex output before writing Claude's own list** — defeats independent discovery. Write first, read second, at both checkpoints.
- **Calling Codex on every human answer** — the dialogue stalls for minutes per turn. Two checkpoints, plus named-decision rounds only.
- **Sending the whole conversation to Codex** — send STATE.md, which excludes logs and private reasoning. If STATE.md exceeds 200 lines, summarize routine answers, not decisions.
- **Treating a timeout or failure as agreement** — always record `timeout`, `unavailable`, or `failed — {reason}` in Positions & Dissent. Every row of the failure table records something; silence there reads as consent Codex never gave.
- **Asking the human to settle a factual dispute** — investigate it instead.
- **Overriding upstream flow beyond the two insertion points** — the HARD-GATE, classification, one-question-per-message, spec location, and writing-plans hand-off are brainstorming's.
- **Forgetting cleanup** — delete `docs/brainstorms/{topic-id}` after the human approves the in-chat design (bounded) or after the spec is committed (architectural). Never run the delete with an empty or unresolved `{topic-id}`.
`````

- [ ] **Step 2: Verify the file's structure**

Run:
```bash
f=skills/trio-brainstorming/SKILL.md
head -1 "$f"
grep -c '^## \(Overview\|When to Use\|Overlay Model\|State File\|Checkpoint 1\|Checkpoint 2\|Provenance and Disagreement\|Failure Handling\|Common Mistakes\)' "$f"
grep -n 'name: trio-brainstorming' "$f"
grep -n 'Triggers: trio brainstorming, codex brainstorming, 3者ブレスト, Codexと一緒に設計, brainstorm with codex' "$f"
grep -n '`trio-cp1`\|`trio-cp2`' "$f" | wc -l
grep -c 'codex-engine.*REFERENCE.md' "$f"
grep -n -- ' -m \|--model\|model_reasoning_effort' "$f"
```
Expected:
- line 1 is `---`
- top-level section count is `9` (the grep names all nine `## ` headers; State-template and Request headers inside code fences are excluded by name)
- `name:` line found
- Triggers line found
- prefix matches is exactly `2` (one `trio-cp1` table row, one `trio-cp2` table row)
- codex-engine REFERENCE.md references ≥ 2 (both "codex-engine REFERENCE.md" and the Glob path "codex-engine/REFERENCE.md" count)
- the last grep prints nothing — the skill never uses `-m`, `--model`, or `model_reasoning_effort`

- [ ] **Step 3: Verify the checkpoint section headers and request templates exist**

Run:
```bash
f=skills/trio-brainstorming/SKILL.md
grep -n '^## Checkpoint 1\|^## Checkpoint 2\|^### Additional rounds\|^### Template\|^### Update rules' "$f"
grep -c '^## Request' "$f"
```
Expected: five header lines printed; `## Request` count is `2`.

- [ ] **Step 4: Commit**

```bash
git add skills/trio-brainstorming/SKILL.md
git commit -m "feat(trio-brainstorming): add three-party brainstorming overlay skill

Runs superpowers:brainstorming with Codex as an equal participant at two
checkpoints: independent question discovery (CP1) and remaining questions
plus independent approaches (CP2, architectural only). Codex invocation
follows the codex-engine contract."
```

---

### Task 2: Register the skill and bump the plugin version

**Files:**
- Modify: `CLAUDE.md` (Repository Structure tree, ~lines 12-27; Key Patterns "Codex-based skills" bullet, ~line 35)
- Modify: `.claude-plugin/plugin.json:4` (`"version": "1.36.0"`)

**Interfaces:**
- Consumes: skill name `trio-brainstorming` from Task 1
- Produces: nothing downstream

- [ ] **Step 1: Add the skill to the Repository Structure tree in CLAUDE.md**

In `CLAUDE.md`, inside the fenced tree under `## Repository Structure`, insert a new line after the `team-composer/` line so the tree ends:

```
  team-composer/       # Shared team composition for board skills (expertise map + always-doubling)
  trio-brainstorming/  # Three-party brainstorming (Claude + Codex + human) as an overlay on superpowers:brainstorming
```

- [ ] **Step 2: Add the skill to the Codex-based skills pattern in CLAUDE.md**

In `CLAUDE.md`, under `### Key Patterns Across Skills`, change the beginning of the **Codex-based skills** bullet from:

```
- **Codex-based skills** (codex-investigate, parallel-research, plan-review, spec-review, plus board `-cx` members):
```

to:

```
- **Codex-based skills** (codex-investigate, parallel-research, plan-review, spec-review, trio-brainstorming, plus board `-cx` members):
```

Then append a new bullet after the **Orchestrator skills** bullet:

```
- **Overlay skills** (trio-brainstorming): Load an upstream skill via the Skill tool and override a small, named set of its behaviors at insertion points named by action. Own only the overlay's added state and prompts — never restate the upstream flow.
```

- [ ] **Step 3: Bump the version**

In `.claude-plugin/plugin.json`, change:

```json
  "version": "1.36.0",
```

to:

```json
  "version": "1.37.0",
```

- [ ] **Step 4: Verify**

Run:
```bash
grep -n 'trio-brainstorming' CLAUDE.md
grep -n '"version"' .claude-plugin/plugin.json
python3 -c 'import json;json.load(open(".claude-plugin/plugin.json"))' && echo JSON_OK
```
Expected:
- three `trio-brainstorming` matches in CLAUDE.md (tree line, Codex-based bullet, Overlay bullet)
- `"version": "1.37.0",`
- `JSON_OK`

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md .claude-plugin/plugin.json
git commit -m "chore: register trio-brainstorming skill and bump version to 1.37.0"
```

---

### Task 3: Runtime verification of the skill

This repo has no test harness for skills; verification is by running the skill. These runs are interactive and require a human at the keyboard. Record observations in the plan file's checkboxes; do not commit any State or spec files produced by trial runs unless the human asks.

**Files:**
- None created or modified. Trial artifacts under `docs/brainstorms/` are deleted by the skill at the end of each run — after the design is approved on the bounded path, after the spec is committed on the architectural path — and Steps 2 and 3 both assert that. Any trial spec under `docs/superpowers/specs/` is gitignored and may be removed by hand.

**Interfaces:**
- Consumes: `skills/trio-brainstorming/SKILL.md` from Task 1; registration from Task 2

- [ ] **Step 1: Confirm prerequisites**

Run:
```bash
command -v codex && codex --version
ls /Users/taiga/.claude/plugins/cache/claude-plugins-official/superpowers/*/skills/brainstorming/SKILL.md
```
Expected: a codex version string; at least one brainstorming SKILL.md path.

- [ ] **Step 2: Bounded path — one Codex call**

In a Claude Code session in this repo, invoke:

```
/forte:trio-brainstorming parallel-research に --codex-only フラグを追加したい（Agent を起動せず Codex だけで調査する）
```

Observe and check:
- Claude announces the path as bounded and says Codex joins once.
- Exactly one Codex launch is printed (`CODEX_PID=...`) with a `/tmp/trio-cp1-*` prefix.
- `docs/brainstorms/parallel-research-codex-only-flag/STATE.md` (or similar slug) exists during the run; its Question Ledger contains rows with at least two distinct Origin values among `claude` / `codex` / `joint`.
- Every question shown to you carries `[Codex]`, `[Claude]`, or `[Joint]` (or the same set localized to the session language).
- No `trio-cp2` launch appears before the short in-chat design.
- After you approve the design, the skill stops (bounded path: no spec file, no writing-plans).
- After you approve the design, the State directory is cleaned: `ls docs/brainstorms/` no longer lists the topic directory. This is the bounded-path half of the lifecycle rule and the only step that checks it.

Stop the run after the design is presented; no implementation is needed.

- [ ] **Step 3: Architectural path — two Codex calls**

Invoke with a medium-sized topic, for example:

```
/forte:trio-brainstorming board 系スキルの WHITEBOARD を SQLite に置き換えたい
```

Observe and check:
- Path announced as architectural with two checkpoints.
- `trio-cp1` launch, then the interview; `trio-cp2` launch appears only once at least one answer has landed since CP1 (State's "Changes Since Last Codex Call" is non-empty) *and* pending questions have reached zero or an Assumption is invalidated (Changes shows `invalidates A{n}`). CP2 never fires back-to-back with CP1 over an empty Changes section.
- The approaches presented include at least one tagged `[Codex]` or `[Joint]` (or the localized equivalent).
- STATE.md line count stays ≤ 200: `wc -l docs/brainstorms/*/STATE.md`.
- After the spec is written and committed, `ls docs/brainstorms/` no longer lists the topic directory.
- The skill offers the writing-plans hand-off exactly as brainstorming does.

You may decline the writing-plans hand-off and delete the trial spec afterwards.

- [ ] **Step 4: Codex unavailable — graceful degradation**

Shadow `codex` with a shim that exits 127, rather than stripping entries out of PATH (an unanchored `grep -v` both over-removes and under-removes). Create the shim, then start a session with its directory first on PATH:

```bash
shim=$(mktemp -d)
printf '#!/bin/sh\nexit 127\n' > "$shim/codex"
chmod +x "$shim/codex"
PATH="$shim:$PATH" claude
```

The shim wins over any real `codex` earlier or later on PATH, and the run's sentinel file receives `127` — exactly the signal the skill's "not installed" row keys on. Remove it when done: `rm -rf "$shim"`.

Invoke the skill with the bounded topic from Step 2. Observe and check:
- Exactly one line `⚠ Codex 不在: 通常の brainstorming で続行` appears after the CP1 attempt.
- No further Codex launches.
- The dialogue proceeds as normal brainstorming to the design gate.
- No temp files remain: `ls /tmp/trio-cp1-* 2>/dev/null` prints nothing.

- [ ] **Step 5: Record results**

Note any deviation from the expected observations above as a follow-up item in this plan file (append a `## Follow-ups` section) rather than editing SKILL.md ad hoc; fixes go through their own brainstorm → spec → plan cycle if non-trivial, or a direct edit + commit if a one-line wording fix.
