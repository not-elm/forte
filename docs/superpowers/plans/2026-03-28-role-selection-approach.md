# Role Selection Approach Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a three-layer role selection improvement (fault-line mapping, constructed roles, two-stage confirmation) plus two complementary protocol changes (per-round re-anchoring, independent hypothesis generation) in the discussion-board skill spec.

**Architecture:** Single-file change to `skills/discussion-board/SKILL.md`. Five edit locations: setup/explore (add fault-line mapping), setup/confirm (3-layer role construction + new presentation format), Workflow Overview table, hypothesize (independent generation + re-anchoring), critique/revise (re-anchoring). All content is English.

**Tech Stack:** Markdown (SKILL.md skill spec), plugin.json (version bump)

**Design doc:** `docs/plans/2026-03-28-role-selection-approach-design.md`

---

### Task 1: Add fault-line mapping to setup/explore

**Files:**
- Modify: `skills/discussion-board/SKILL.md:187-202`

- [ ] **Step 1: Add fault-line mapping step to setup/explore**

After the current setup/explore content (line 202), insert a new section about fault-line mapping. The explore phase now has two purposes: (1) ask user questions to understand context, and (2) generate a fault-line map before proceeding to confirm.

Replace the entire `### setup/explore` section (lines 187-202):

```markdown
### setup/explore

- Leader analyzes the proposition and assesses its clarity before asking questions.
- Ask the user one question at a time (never combine multiple questions in one message).
- Prefer multiple-choice questions where possible; open-ended questions are also acceptable.
- Question focus areas:
  - Background and motivation (why is this discussion needed?)
  - Goals (what outcome defines success?)
  - Known constraints and assumptions
  - Perspectives to emphasize or exclude
- Adapt depth to proposition clarity: 2-3 questions if clear, 4-6 if ambiguous or broad.
- **Transition to setup/confirm** when either condition is met:
  1. Leader can articulate enough independent perspectives to match topic complexity (simple: 4-5, moderate: 6-7, complex: 8-10).
  2. Maximum 6 questions reached — proceed with best available perspectives.
- Question count is **cumulative** across all explore visits (does not reset if returning from confirm).
- If user specifies roles upfront, skip explore and enter confirm directly (name constraint check only).
- **Fault-line mapping:** Before generating roles, the leader produces a fault-line map — 3-5 axes of disagreement for the proposition. The fault-line prompt must explicitly target latent axes not visible in the proposition's surface framing:
  - Contested assumptions the proposition takes for granted
  - Second-order consequences not addressed in the proposition
  - Premise challenges that reframe the question itself
  - At least one fault line that complicates the proposition's implicit premise
- **Propositional entropy check:** If the leader cannot generate 3 distinct fault lines without inferring major unstated assumptions, ask the user one clarifying question before proceeding. This does not count toward the 6-question limit.
- The fault-line map is presented to the user alongside the role list in setup/confirm (not separately approved).
```

- [ ] **Step 2: Verify edit**

Read lines 187-220 of `skills/discussion-board/SKILL.md` and confirm the setup/explore section includes fault-line mapping instructions and propositional entropy check.

---

### Task 2: Update setup/confirm with 3-layer role construction + new presentation format

**Files:**
- Modify: `skills/discussion-board/SKILL.md:204-228`

- [ ] **Step 1: Replace setup/confirm section**

Replace the entire `### setup/confirm` section (lines 204-228) with the new 3-layer role construction and presentation format:

```markdown
### setup/confirm

- Generate roles from the fault-line map produced in setup/explore. Each role is **constructed with three layers**:
  1. **Discipline-grounded identity** — activates domain-specific knowledge (e.g., "Economist", "Systems Engineer")
  2. **Epistemic stance** — constrains the reasoning path (e.g., "argues from empirical precedent", "prioritizes second-order systemic effects")
  3. **Explicit epistemic constraint** — specifies what counts as evidence and what blind spots to guard against (e.g., "treats theoretical arguments as insufficient without empirical data")
- **Mandatory Proposition Challenger:** One role must be explicitly mandated to attack the proposition's framing, not just its conclusion. This role asks: Is this the right question? Are the implicit assumptions warranted? This is distinct from a generic Devil's Advocate.
- Each role is presented in the following format:
  ```
  1. **{Role Name}** — {discipline + stance}
     > Expected argument: {one-sentence description of what this role will argue}
     > Guards against: {blind spot this role covers}
  ```
- Role count = team size (range 4-10).
  - If fewer than 4: leader proposes supplementary roles with explicit rationale.
  - If more than 10: leader presents consolidation candidates for user to choose.
- **Name constraints** (role names = subsection headers = ID initials):
  - Short English names (1-2 words, space-separated).
  - Must work as `### {name}` subsection headers.
  - First-letter initials (uppercase) must be unique within the team (prevents `[H-{initial}-{seq}]` ID collisions).
  - If initial collision is unavoidable with meaningful names, use first two letters as the initial fallback.
- User approval gate: "These are the roles for the team. Each role's expected argument and blind-spot coverage is shown. Add, remove, or modify as needed."
  - User requests modification → leader revises and re-presents (loop within confirm).
  - User requests more questions → return to explore (max 2 returns; question count is cumulative).
  - Max 3 re-presentations without convergence → ask user to specify roles in free text.
- After user approves:
  - Each role name becomes a member name for team creation. The full 3-layer role description is used as the member's briefing context in all subsequent broadcasts.
  - Generate a kebab-case `{discussion-id}` from the proposition (e.g., `context-optimization`).
  - Create `docs/discussions/{discussion-id}/WHITEBOARD.md` + `SYNTHESIS.md` using templates (see Reference Layer).
  - Ensure `docs/discussions/` is in `.gitignore` (add if missing).
  - SYNTHESIS.md initializes with `> Status: setup` as before; leader transitions to framing immediately.
```

- [ ] **Step 2: Verify edit**

Read lines 204-245 of `skills/discussion-board/SKILL.md` and confirm setup/confirm includes 3-layer construction, Proposition Challenger mandate, new presentation format, and the briefing context note.

---

### Task 3: Update Workflow Overview table

**Files:**
- Modify: `skills/discussion-board/SKILL.md:174-175`

- [ ] **Step 1: Update setup/explore row description**

Replace:
```markdown
| setup/explore | Analyze proposition, ask user questions one at a time to explore perspectives | — | Perspective insights from user dialogue | Leader has enough info for perspectives |
```

With:
```markdown
| setup/explore | Analyze proposition, ask user questions, generate fault-line map (3-5 axes of disagreement) | — | Fault-line map + perspective insights from user dialogue | Leader has fault-line map + enough info for roles |
```

- [ ] **Step 2: Update setup/confirm row description**

Replace:
```markdown
| setup/confirm | Generate perspective list (name + description + rationale), present to user for approval | — | Approved perspective list → team created, WHITEBOARD.md + SYNTHESIS.md | User approves perspectives |
```

With:
```markdown
| setup/confirm | Construct 3-layer roles from fault-line map (discipline + stance + epistemic constraint), present with expected arguments to user | — | Approved role list → team created, WHITEBOARD.md + SYNTHESIS.md | User approves roles |
```

- [ ] **Step 3: Verify edit**

Read lines 170-185 of `skills/discussion-board/SKILL.md` and confirm the Workflow Overview table reflects fault-line mapping and 3-layer role construction.

---

### Task 4: Add independent hypothesis generation + per-round re-anchoring

**Files:**
- Modify: `skills/discussion-board/SKILL.md` — hypothesize and critique sections

- [ ] **Step 1: Update hypothesize phase notes**

Replace the current `### hypothesize` section (lines 235-239):
```markdown
### hypothesize

- Members read all framings via full WHITEBOARD.md Read (~200 lines at this stage).
- Each member aims for 2-5 hypotheses, each concrete and testable.
- Report completion using the completion report format.
```

With:
```markdown
### hypothesize

- **Independent generation (Round 1 only):** In the first round, members generate hypotheses WITHOUT reading other members' framing entries. Each member receives only the proposition and their own role briefing (3-layer description from setup/confirm). This eliminates first-mover anchoring where the first agent's conceptual vocabulary constrains all subsequent agents. All hypotheses are written to WHITEBOARD.md simultaneously.
- **Round 2+:** Members read all prior content via full WHITEBOARD.md Read.
- **Per-round role re-anchoring:** Every broadcast that kicks off this phase must restate each member's core epistemic commitments (the epistemic stance + epistemic constraint from their 3-layer role description). This combats role collapse — the tendency of agents to drift toward consensus as the WHITEBOARD accumulates content.
- Each member aims for 2-5 hypotheses, each concrete and testable.
- Report completion using the completion report format.
```

- [ ] **Step 2: Update critique phase notes — add re-anchoring**

Replace:
```markdown
### critique

- **IMPORTANT**: Use 2-step Grep extraction when WHITEBOARD exceeds ~350 lines:
```

With:
```markdown
### critique

- **Per-round role re-anchoring:** Every broadcast that kicks off this phase must restate each member's core epistemic commitments (the epistemic stance + epistemic constraint from their 3-layer role description).
- **IMPORTANT**: Use 2-step Grep extraction when WHITEBOARD exceeds ~350 lines:
```

- [ ] **Step 3: Update revise phase notes — add re-anchoring**

Replace:
```markdown
### revise

- Only runs when audit found ⚠️ Partially accurate or ❌ Inaccurate entries.
- Leader broadcasts audit results and instructs affected members to review and correct their entries.
```

With:
```markdown
### revise

- Only runs when audit found ⚠️ Partially accurate or ❌ Inaccurate entries.
- **Per-round role re-anchoring:** The broadcast that kicks off this phase must restate each affected member's core epistemic commitments alongside the audit findings.
- Leader broadcasts audit results and instructs affected members to review and correct their entries.
```

- [ ] **Step 4: Verify edits**

Read the `### hypothesize`, `### critique`, and `### revise` sections in `skills/discussion-board/SKILL.md` (note: line numbers will have shifted due to earlier tasks expanding setup/explore and setup/confirm) and confirm:
- hypothesize has independent generation for Round 1 and re-anchoring
- critique has re-anchoring as first bullet
- revise has re-anchoring after the condition bullet

---

### Task 5: Update Phase Model table

**Files:**
- Modify: `skills/discussion-board/SKILL.md:42-43`

- [ ] **Step 1: Update setup/explore description in Phase Model table**

Replace:
```markdown
| setup/explore | Leader + User | Analyze proposition, ask user questions one at a time to discover perspectives |
```

With:
```markdown
| setup/explore | Leader + User | Analyze proposition, ask user questions, generate fault-line map of key disagreement axes |
```

- [ ] **Step 2: Update setup/confirm description in Phase Model table**

Replace:
```markdown
| setup/confirm | Leader + User | Present perspective list (name + description + rationale), user approves, create team + files |
```

With:
```markdown
| setup/confirm | Leader + User | Construct 3-layer roles (discipline + stance + constraint) from fault-line map, present with expected arguments, user approves, create team + files |
```

- [ ] **Step 3: Verify edit**

Read lines 40-52 of `skills/discussion-board/SKILL.md` and confirm both Phase Model table rows reflect the new descriptions.

---

### Task 6: Commit + version bump

**Files:**
- `skills/discussion-board/SKILL.md`
- `.claude-plugin/plugin.json`

- [ ] **Step 1: Review full diff**

Run: `git diff skills/discussion-board/SKILL.md`

Verify changes span:
- Phase Model table (2 rows updated)
- Workflow Overview table (2 rows updated)
- setup/explore (fault-line mapping + propositional entropy check added)
- setup/confirm (3-layer construction + new format + Proposition Challenger)
- hypothesize (independent generation + re-anchoring)
- critique (re-anchoring)

- [ ] **Step 2: Commit SKILL.md changes**

```bash
git add skills/discussion-board/SKILL.md
git commit -m "feat(discussion-board): implement 3-layer role selection approach

Add fault-line mapping before role selection, 3-layer role construction
(discipline + stance + epistemic constraint), mandatory Proposition Challenger,
two-stage user confirmation with expected arguments, per-round role re-anchoring,
and independent hypothesis generation in Round 1.

Design: docs/plans/2026-03-28-role-selection-approach-design.md"
```

- [ ] **Step 3: Bump version**

Read `.claude-plugin/plugin.json`, increment minor version (1.11.0 → 1.12.0), commit:

```bash
git add .claude-plugin/plugin.json
git commit -m "chore: bump version to 1.12.0"
```
