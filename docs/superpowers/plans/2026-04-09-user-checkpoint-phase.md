# User Checkpoint Phase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional `user-checkpoint` phase between `synthesize` and `ratify` in the board-engine standard debate cycle, allowing the leader to ask the user targeted questions when trigger conditions are met.

**Architecture:** The user-checkpoint phase is defined in `board-engine/REFERENCE.md` as a shared phase (like `revise`). Each board skill updates its phase model string and SYNTHESIS.md template. The phase is leader-only: evaluate triggers, call AskUserQuestion, record response, branch to ratify or hypothesize.

**Tech Stack:** Markdown skill files (SKILL.md, REFERENCE.md), AskUserQuestion tool, SYNTHESIS.md file format.

---

## File Tree

```
skills/
  board-engine/
    REFERENCE.md                          # Modify: add user-checkpoint phase + entry format
  discussion-board/
    SKILL.md                              # Modify: phase model string, phase table, SYNTHESIS template
  design-board/
    SKILL.md                              # Modify: Phase 2 cycle string, SYNTHESIS template
  investigation-board/
    SKILL.md                              # Modify: phase model string, SYNTHESIS template
  frontend-design-board/
    SKILL.md                              # Modify: Phase 1 + Phase 2 cycle strings, phase tables
    references/
      synthesis-templates.md              # Modify: add ## User Checkpoint to both phase templates
.claude-plugin/
  plugin.json                             # Modify: bump version
  marketplace.json                        # No change needed (no version field)
```

---

## Task 1: Add user-checkpoint to board-engine/REFERENCE.md

**Files:**
- Modify: `skills/board-engine/REFERENCE.md:53-59` (Standard Debate Cycle string)
- Modify: `skills/board-engine/REFERENCE.md:217-224` (insert new section between synthesize and ratify)
- Modify: `skills/board-engine/REFERENCE.md:228-322` (add entry format to Shared Entry Formats)

- [ ] **Step 1: Update the Standard Debate Cycle string**

In `skills/board-engine/REFERENCE.md`, find the cycle string at line 58 and change:

```markdown
[Round N: hypothesize → critique → audit → revise (if needed) → synthesize → ratify]
```

To:

```markdown
[Round N: hypothesize → critique → audit → revise (if needed) → synthesize → user-checkpoint (if needed) → ratify]
```

- [ ] **Step 2: Add the `### user-checkpoint` section between `### synthesize` and `### ratify`**

Insert the following new section after the `### synthesize` section (after line 217, before `### ratify`):

```markdown
### user-checkpoint

- **Optional phase** — only runs when trigger conditions match. Skipped otherwise.
- Leader evaluates the trigger condition checklist against SYNTHESIS.md artifacts (Draft Conclusion, Evidence Map, Round Context Packet) and WHITEBOARD-R{N}.md audit results immediately after synthesize completes.

- **Trigger Condition Checklist** — execute user-checkpoint if one or more match:

| # | Condition | Criteria | Example |
|---|-----------|----------|---------|
| 1 | **Domain requirement uncertainty** | The conclusion depends on user's business requirements or domain knowledge that the team cannot determine internally | "Is performance or UX the priority for this feature?" |
| 2 | **Business trade-off judgment** | Multiple technically valid options exist and a business judgment is needed | "Accept increased cost for high availability?" |
| 3 | **Unverified premise** | Facts underlying hypotheses cannot be verified by the team or audit, and only the user knows | "What is the actual concurrent connection count in production?" |
| 4 | **Scope boundary ambiguity** | The scope of the conclusion is unclear and user intent confirmation is needed | "Can this change break backward compatibility of the existing API?" |
| 5 | **Unresolvable member disagreement** | The same dispute persists in Round Context Packet's Open disputes for **2+ rounds** | "RDB vs NoSQL remains undecided for 2 consecutive rounds" |
| 6 | **Process confidence degradation** | Audit failed, unresolved inaccuracies (❌/⚠️) remain after revise, or Draft Conclusion confidence is **low** | "Codex timed out, audit was skipped" |

- Board skills may add board-specific conditions or disable specific conditions via override.

- **Execution flow:**
  1. Leader constructs questions from matched triggers and presents via AskUserQuestion (single call, all questions in numbered list).
  2. AskUserQuestion format:
     ```
     Round {N} の統合結果について、以下の点を確認させてください。

     1. {question}
        背景: {why this needs user input, citing entry IDs}

     2. {question}
        背景: {why this needs user input, citing entry IDs}

     回答後、チームの投票（ratify）に進みます。
     方向転換が必要な場合はその旨お伝えください。
     ```
  3. Record response in SYNTHESIS.md `## User Checkpoint` → `### Round {N}` (see User Checkpoint Record format in Shared Entry Formats).
  4. Branch on response:
     - **Confirmation only** (no direction change needed) → include user response in ratify broadcast, proceed to `ratify`
     - **Direction change needed** → skip `ratify`, create WHITEBOARD-R{N+1}.md, re-enter `hypothesize` with user response as new constraint in broadcast
     - **Direction change criteria:** The user explicitly states a direction change is needed, OR the user's answer invalidates a key claim in the Draft Conclusion (leader judgment). When ambiguous, leader asks a follow-up: "この回答を踏まえて、現在の結論の方向で投票に進んでよいですか？"

- **No timeout** — user is human, not an agent. Leader waits for response.
- **No new conflict rules** — user-checkpoint is leader-only (AskUserQuestion + SYNTHESIS.md write), consistent with rule #2.
```

- [ ] **Step 3: Add User Checkpoint Record format to Shared Entry Formats**

Insert the following after the `### Completion Report` section (after line 309, before `### Audit Table + Verdict Rubric`):

```markdown
### User Checkpoint Record (Leader only)

Written per-round when user-checkpoint fires. Stored in SYNTHESIS.md `## User Checkpoint`.

```markdown
## User Checkpoint
### Round {N}
- **Trigger:** {matched condition number(s) and name(s)}
- **Questions:** {questions asked}
- **Response:** {user's response verbatim}
- **Action:** ratify / re-enter hypothesize with constraint: {constraint summary}
```
```

- [ ] **Step 4: Verify the changes**

Read the modified file and confirm:
1. The cycle string on line ~58 includes `user-checkpoint (if needed)`
2. The `### user-checkpoint` section appears between `### synthesize` and `### ratify`
3. The `### User Checkpoint Record` entry format appears in Shared Entry Formats
4. No existing content was accidentally deleted or corrupted

- [ ] **Step 5: Commit**

```bash
git add skills/board-engine/REFERENCE.md
git commit -m "feat(board-engine): add user-checkpoint phase to standard debate cycle"
```

---

## Task 2: Update discussion-board/SKILL.md

**Files:**
- Modify: `skills/discussion-board/SKILL.md:50` (phase model string)
- Modify: `skills/discussion-board/SKILL.md:53-63` (phase table)
- Modify: `skills/discussion-board/SKILL.md:166-178` (SYNTHESIS.md template)

- [ ] **Step 1: Update the phase model string**

In `skills/discussion-board/SKILL.md`, find the phase model string at line 50 and change:

```
setup → framing → [Round N: hypothesize → critique → audit → revise (if needed) → synthesize → ratify] → concluded
```

To:

```
setup → framing → [Round N: hypothesize → critique → audit → revise (if needed) → synthesize → user-checkpoint (if needed) → ratify] → concluded
```

- [ ] **Step 2: Add user-checkpoint row to the phase table**

Insert a new row between `synthesize` and `ratify` in the phase table (between lines 61 and 62):

```markdown
| user-checkpoint | Leader only | AskUserQuestion if trigger conditions match; record response (skipped if no triggers) |
```

The table should now read:

```markdown
| Phase | Who | What |
|-------|-----|------|
| setup | Leader | Invoke team-composer, create discussion files, spawn members |
| framing | All members | Document problem interpretation, constraints, criteria, unknowns |
| hypothesize | All members | Write concrete, testable candidate answers as hypotheses |
| critique | All members | Challenge/support/amend/question hypotheses with cross-references |
| audit | Leader only | Codex CLI fact-check of current round; results to WHITEBOARD-R{N}.md `## Audit` |
| revise | All members | Review audit findings, append corrections (skipped if no warnings/errors) |
| synthesize | Leader only | Update Evidence Map + Draft Conclusion + Round Context Packet in SYNTHESIS.md |
| user-checkpoint | Leader only | AskUserQuestion if trigger conditions match; record response (skipped if no triggers) |
| ratify | All members | Vote accept or push-back via SendMessage. Simple majority ratifies |
| concluded | Leader only | Record final conclusion (and Minority Report if dissent exists) |
```

- [ ] **Step 3: Add `## User Checkpoint` to SYNTHESIS.md template**

In the SYNTHESIS.md template (around line 172-177), add `## User Checkpoint` between `## Ratification History` and `## Minority Report`:

```markdown
# SYNTHESIS — {discussion-id}
> Status: setup
> Round: 0
> Max Rounds: 10

## Evidence Map
## Draft Conclusion
## Round Context Packet
## Ratification History
## User Checkpoint
## Minority Report
## Final Conclusion
```

- [ ] **Step 4: Verify the changes**

Read the modified file and confirm:
1. Phase model string includes `user-checkpoint (if needed)`
2. Phase table has user-checkpoint row between synthesize and ratify
3. SYNTHESIS.md template includes `## User Checkpoint`

- [ ] **Step 5: Commit**

```bash
git add skills/discussion-board/SKILL.md
git commit -m "feat(discussion-board): add user-checkpoint to phase model and SYNTHESIS template"
```

---

## Task 3: Update design-board/SKILL.md

**Files:**
- Modify: `skills/design-board/SKILL.md:49` (Phase Model string — Phase 2 portion)
- Modify: `skills/design-board/SKILL.md:75` (Phase 2 cycle reference)
- Modify: `skills/design-board/SKILL.md:204` (Phase 2 debate cycle heading)
- Modify: `skills/design-board/SKILL.md:313-325` (Phase 2 SYNTHESIS template)

- [ ] **Step 1: Update the Phase Model string**

In `skills/design-board/SKILL.md`, find the phase model string at line 49 and change:

```
setup → [Phase 1: framing → hypothesize → critique → synthesize] → user-review → [Phase 2: framing → [Round N: hypothesize → critique → audit → revise (if needed) → synthesize → ratify] ] → concluded
```

To:

```
setup → [Phase 1: framing → hypothesize → critique → synthesize] → user-review → [Phase 2: framing → [Round N: hypothesize → critique → audit → revise (if needed) → synthesize → user-checkpoint (if needed) → ratify] ] → concluded
```

- [ ] **Step 2: Update the Phase 2 cycle reference**

At line 75, change:

```markdown
Uses the standard debate cycle from REFERENCE.md: `[Round N: hypothesize → critique → audit → revise (if needed) → synthesize → ratify]`
```

To:

```markdown
Uses the standard debate cycle from REFERENCE.md: `[Round N: hypothesize → critique → audit → revise (if needed) → synthesize → user-checkpoint (if needed) → ratify]`
```

- [ ] **Step 3: Update the Phase 2 debate cycle heading**

At line 204, change:

```markdown
### Phase 2: debate cycle (hypothesize → critique → audit → revise → synthesize → ratify)
```

To:

```markdown
### Phase 2: debate cycle (hypothesize → critique → audit → revise → synthesize → user-checkpoint → ratify)
```

- [ ] **Step 4: Add board-specific user-checkpoint note**

After the existing Phase 2 debate cycle bullet points (after the `- **ratify:**` line at ~211), add:

```markdown
- **user-checkpoint:** Phase 1 is excluded (no ratify loop; user-review serves as gate). Phase 2 applies all 6 trigger conditions from REFERENCE.md.
```

- [ ] **Step 5: Add `## User Checkpoint` to Phase 2 SYNTHESIS template**

In the Phase 2 SYNTHESIS template (around lines 319-325), add `## User Checkpoint` between `## Ratification History` and `## Minority Report`:

```markdown
# SYNTHESIS — {discussion-id} / Phase 2: Design
> Status: setup
> Round: 0
> Max Rounds: 10

## Evidence Map
## Draft Design
## Round Context Packet
## Ratification History
## User Checkpoint
## Minority Report
## Final Design
```

- [ ] **Step 6: Verify the changes**

Read the modified file and confirm:
1. Phase Model string includes `user-checkpoint (if needed)` in Phase 2 portion only
2. Phase 2 cycle reference includes `user-checkpoint (if needed)`
3. Phase 2 debate cycle heading includes `user-checkpoint`
4. Board-specific note about Phase 1 exclusion is present
5. Phase 2 SYNTHESIS template includes `## User Checkpoint`

- [ ] **Step 7: Commit**

```bash
git add skills/design-board/SKILL.md
git commit -m "feat(design-board): add user-checkpoint to Phase 2 debate cycle"
```

---

## Task 4: Update investigation-board/SKILL.md

**Files:**
- Modify: `skills/investigation-board/SKILL.md:59` (Phase Model string)
- Modify: `skills/investigation-board/SKILL.md:276-289` (SYNTHESIS.md template)

- [ ] **Step 1: Update the phase model string**

In `skills/investigation-board/SKILL.md`, find the phase model string at line 59 and change:

```
setup → framing → evidence-gathering → [Round N: hypothesize → critique → audit (dual-layer) → revise → synthesize → ratify] → concluded
```

To:

```
setup → framing → evidence-gathering → [Round N: hypothesize → critique → audit (dual-layer) → revise → synthesize → user-checkpoint (if needed) → ratify] → concluded
```

- [ ] **Step 2: Add `## User Checkpoint` to SYNTHESIS.md template**

In the SYNTHESIS.md template (around lines 282-289), add `## User Checkpoint` between `## Ratification History` and `## Minority Report`:

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
## User Checkpoint
## Minority Report
## Final Conclusion
```

- [ ] **Step 3: Verify the changes**

Read the modified file and confirm:
1. Phase model string includes `user-checkpoint (if needed)`
2. SYNTHESIS.md template includes `## User Checkpoint`

- [ ] **Step 4: Commit**

```bash
git add skills/investigation-board/SKILL.md
git commit -m "feat(investigation-board): add user-checkpoint to phase model and SYNTHESIS template"
```

---

## Task 5: Update frontend-design-board/SKILL.md

**Files:**
- Modify: `skills/frontend-design-board/SKILL.md:64` (Phase Model string — both phases)
- Modify: `skills/frontend-design-board/SKILL.md:73-79` (Phase 1 step table)
- Modify: `skills/frontend-design-board/SKILL.md:81` (Phase 1 cycle note)
- Modify: `skills/frontend-design-board/SKILL.md:93-101` (Phase 2 step table)

- [ ] **Step 1: Update the Phase Model string**

In `skills/frontend-design-board/SKILL.md`, find the phase model string at line 64 and change:

```
setup → [Phase 1: framing → [Round N: hypothesize → critique → synthesize → ratify]] → user-review-1 (moodboard ⇄ Phase 1 hypothesize) → [Phase 2: framing → [Round N: hypothesize → critique → audit → revise (if needed) → synthesize → ratify]] → user-review-2 (UI mockup ⇄ Phase 2 hypothesize) → concluded
```

To:

```
setup → [Phase 1: framing → [Round N: hypothesize → critique → synthesize → user-checkpoint (if needed) → ratify]] → user-review-1 (moodboard ⇄ Phase 1 hypothesize) → [Phase 2: framing → [Round N: hypothesize → critique → audit → revise (if needed) → synthesize → user-checkpoint (if needed) → ratify]] → user-review-2 (UI mockup ⇄ Phase 2 hypothesize) → concluded
```

- [ ] **Step 2: Add user-checkpoint to Phase 1 step table**

Insert a new row between `synthesize` and `ratify` in the Phase 1 table (between lines 78 and 79):

```markdown
| user-checkpoint | Leader only | AskUserQuestion if trigger conditions match (condition 6 disabled — no audit in Phase 1); skipped if no triggers |
```

The table should now read:

```markdown
| Step | Who | What |
|------|-----|------|
| framing | All members | Document design context: purpose, aesthetic instincts, target user, constraints, unknowns |
| hypothesize | All members | Propose design directions: tone, mood, aesthetic stance, reference points |
| critique | All members | Challenge/support/amend/question directions using design principles |
| synthesize | Leader only | Read current round WHITEBOARD-R{N}.md + prior SYNTHESIS.md, write Evidence Map + Direction Conclusion |
| user-checkpoint | Leader only | AskUserQuestion if trigger conditions match (condition 6 disabled — no audit in Phase 1); skipped if no triggers |
| ratify | All voting members | Vote accept or push-back on design direction. Simple majority ratifies |
```

- [ ] **Step 3: Update Phase 1 cycle note**

At line 81, change:

```markdown
**Phase 1 has NO audit or revise.** Aesthetic hypotheses are not fact-checkable. The debate cycle for Phase 1 is: hypothesize → critique → synthesize → ratify.
```

To:

```markdown
**Phase 1 has NO audit or revise.** Aesthetic hypotheses are not fact-checkable. The debate cycle for Phase 1 is: hypothesize → critique → synthesize → user-checkpoint (if needed) → ratify. **user-checkpoint override:** Condition 6 (Process confidence degradation) is disabled in Phase 1 — no audit means no audit failure to detect.
```

- [ ] **Step 4: Add user-checkpoint to Phase 2 step table**

Insert a new row between `synthesize` and `ratify` in the Phase 2 table (between lines 100 and 101):

```markdown
| user-checkpoint | Leader only | AskUserQuestion if trigger conditions match; all 6 conditions apply (skipped if no triggers) |
```

The table should now read:

```markdown
| Step | Who | What |
|------|-----|------|
| framing | All members | Document specification constraints, scope, acceptance criteria (informed by Phase 1 direction) |
| hypothesize | All members | Propose concrete design specifications: token definitions (required), responsive strategy, motion policy |
| critique | All members | Challenge/support/amend/question specifications with design principle references and axis tags |
| audit | Leader only | Run Codex CLI to fact-check: a11y (WCAG 2.1/2.2 AA), browser compat, performance (CLS/LCP). Aesthetic judgments excluded |
| revise | All members (conditional) | Append corrections if audit found inaccuracies (skipped if all clean) |
| synthesize | Leader only | Read current round WHITEBOARD-R{N}.md + prior SYNTHESIS.md, write Evidence Map + Draft Design Spec |
| user-checkpoint | Leader only | AskUserQuestion if trigger conditions match; all 6 conditions apply (skipped if no triggers) |
| ratify | All voting members | Vote accept or push-back via SendMessage. Simple majority ratifies |
```

- [ ] **Step 5: Verify the changes**

Read the modified file and confirm:
1. Phase Model string includes `user-checkpoint (if needed)` in both Phase 1 and Phase 2
2. Phase 1 step table has user-checkpoint row (with condition 6 disabled note)
3. Phase 1 cycle note updated with user-checkpoint and override
4. Phase 2 step table has user-checkpoint row (all 6 conditions)

- [ ] **Step 6: Commit**

```bash
git add skills/frontend-design-board/SKILL.md
git commit -m "feat(frontend-design-board): add user-checkpoint to Phase 1 and Phase 2 cycles"
```

---

## Task 6: Update frontend-design-board synthesis templates

**Files:**
- Modify: `skills/frontend-design-board/references/synthesis-templates.md`

- [ ] **Step 1: Add `## User Checkpoint` to Phase 1 SYNTHESIS template**

In `skills/frontend-design-board/references/synthesis-templates.md`, add `## User Checkpoint` between `## Ratification History` and `## User Feedback History` in the Phase 1 template:

```markdown
# SYNTHESIS — {discussion-id} / Phase 1: Design Direction
> Status: setup
> Round: 0
> Max Rounds: 10
> Feedback Cycle: 1

## Evidence Map
## Direction Conclusion
## Round Context Packet
## Ratification History
## User Checkpoint
## User Feedback History
```

- [ ] **Step 2: Add `## User Checkpoint` to Phase 2 SYNTHESIS template**

Add `## User Checkpoint` between `## Ratification History` and `## Minority Report` in the Phase 2 template:

```markdown
# SYNTHESIS — {discussion-id} / Phase 2: Design Specification
> Status: setup
> Round: 0
> Max Rounds: 10
> Feedback Cycle: 1

## Evidence Map
## Draft Design Spec
## Round Context Packet
## Ratification History
## User Checkpoint
## Minority Report
## User Feedback History
## Final Design Spec
```

- [ ] **Step 3: Verify the changes**

Read the modified file and confirm both templates include `## User Checkpoint`.

- [ ] **Step 4: Commit**

```bash
git add skills/frontend-design-board/references/synthesis-templates.md
git commit -m "feat(frontend-design-board): add User Checkpoint to synthesis templates"
```

---

## Task 7: Version bump and final verification

**Files:**
- Modify: `.claude-plugin/plugin.json:4` (version)

- [ ] **Step 1: Bump version**

In `.claude-plugin/plugin.json`, change version from `"1.23.0"` to `"1.24.0"`:

```json
{
  "name": "forte",
  "description": "notelm's personal collection of Claude Code skills",
  "version": "1.24.0",
  "author": {
    "name": "notelm"
  },
  "repository": "https://github.com/not-elm/forte.git",
  "license": "MIT"
}
```

- [ ] **Step 2: Final cross-file verification**

Verify consistency across all modified files:

1. `board-engine/REFERENCE.md` — cycle string includes `user-checkpoint (if needed)`
2. `discussion-board/SKILL.md` — cycle string matches, phase table has row, SYNTHESIS template has section
3. `design-board/SKILL.md` — Phase 2 cycle string matches, board-specific note present, Phase 2 SYNTHESIS template has section
4. `investigation-board/SKILL.md` — cycle string matches, SYNTHESIS template has section
5. `frontend-design-board/SKILL.md` — both Phase 1 and Phase 2 cycle strings match, both phase tables have rows, condition 6 disabled note in Phase 1
6. `frontend-design-board/references/synthesis-templates.md` — both templates have `## User Checkpoint`
7. `.claude-plugin/plugin.json` — version is `1.24.0`

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "chore: bump version to 1.24.0"
```
