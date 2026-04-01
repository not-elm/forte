# Discussion Board Role Selection Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace fault-line-based role selection with expertise-map-based role selection in discussion-board, simplify roles to discipline-only, and raise default team size to 6.

**Architecture:** Single-file change to `skills/discussion-board/SKILL.md`. Six edit regions: Phase Model table, Workflow Overview table, setup/explore section, setup/confirm section, hypothesize section, critique section, revise section.

**Tech Stack:** Markdown (skill spec)

**Spec:** `docs/superpowers/specs/2026-04-01-discussion-board-role-selection-redesign.md`

---

### Task 1: Update Phase Model table

**Files:**
- Modify: `skills/discussion-board/SKILL.md:42-43`

- [ ] **Step 1: Update setup/explore row**

Change line 42 from:
```markdown
| setup/explore | Leader + User | Analyze proposition, ask user questions, generate fault-line map of key disagreement axes |
```
To:
```markdown
| setup/explore | Leader + User | Analyze proposition, ask user questions, generate expertise map of required domains |
```

- [ ] **Step 2: Update setup/confirm row**

Change line 43 from:
```markdown
| setup/confirm | Leader + User | Construct 3-layer roles (discipline + stance + constraint) from fault-line map, present with expected arguments, user approves, create team + files |
```
To:
```markdown
| setup/confirm | Leader + User | Generate discipline-only roles from expertise map, present with expected contributions, user approves, create team + files |
```

- [ ] **Step 3: Commit**

```bash
git add skills/discussion-board/SKILL.md
git commit -m "refactor(discussion-board): update Phase Model table for expertise map"
```

### Task 2: Update Workflow Overview table

**Files:**
- Modify: `skills/discussion-board/SKILL.md:183-184`

- [ ] **Step 1: Update setup/explore row**

Change line 183 from:
```markdown
| setup/explore | Analyze proposition, ask user questions, generate fault-line map (3-5 axes of disagreement) | — | Fault-line map + perspective insights from user dialogue | Leader has fault-line map + enough info for roles |
```
To:
```markdown
| setup/explore | Analyze proposition, ask user questions, generate expertise map (6-10 required domains) | — | Expertise map + topic insights from user dialogue | Leader has expertise map + enough info for roles |
```

- [ ] **Step 2: Update setup/confirm row**

Change line 184 from:
```markdown
| setup/confirm | Construct 3-layer roles from fault-line map (discipline + stance + epistemic constraint), present with expected arguments to user | — | Approved role list → team created, WHITEBOARD.md + SYNTHESIS.md | User approves roles |
```
To:
```markdown
| setup/confirm | Generate discipline-only roles from expertise map, present with expected contributions to user | — | Approved role list → team created, WHITEBOARD.md + SYNTHESIS.md | User approves roles |
```

- [ ] **Step 3: Commit**

```bash
git add skills/discussion-board/SKILL.md
git commit -m "refactor(discussion-board): update Workflow Overview table for expertise map"
```

### Task 3: Rewrite setup/explore section

**Files:**
- Modify: `skills/discussion-board/SKILL.md:196-218`

- [ ] **Step 1: Replace entire setup/explore section**

Replace lines 196-218 with:

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add skills/discussion-board/SKILL.md
git commit -m "refactor(discussion-board): replace fault-line map with expertise map in setup/explore"
```

### Task 4: Rewrite setup/confirm section

**Files:**
- Modify: `skills/discussion-board/SKILL.md:220-250` (line numbers will have shifted after Task 3)

- [ ] **Step 1: Replace entire setup/confirm section**

Replace the current setup/confirm section (from `### setup/confirm` to just before `### framing`) with:

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add skills/discussion-board/SKILL.md
git commit -m "refactor(discussion-board): simplify setup/confirm to discipline-only roles"
```

### Task 5: Update role re-anchoring in hypothesize, critique, and revise

**Files:**
- Modify: `skills/discussion-board/SKILL.md` — hypothesize, critique, and revise sections (line numbers will have shifted)

- [ ] **Step 1: Update hypothesize section**

In the hypothesize section, replace:
```markdown
- **Independent generation (Round 1 only):** In the first round, members generate hypotheses WITHOUT reading other members' framing entries. Each member receives only the proposition and their own role briefing (3-layer description from setup/confirm). This eliminates first-mover anchoring where the first agent's conceptual vocabulary constrains all subsequent agents. All hypotheses are written to WHITEBOARD.md simultaneously.
```
With:
```markdown
- **Independent generation (Round 1 only):** In the first round, members generate hypotheses WITHOUT reading other members' framing entries. Each member receives only the proposition and their own role briefing (discipline + expected contribution from setup/confirm). This eliminates first-mover anchoring where the first agent's conceptual vocabulary constrains all subsequent agents. All hypotheses are written to WHITEBOARD.md simultaneously.
```

Replace:
```markdown
- **Per-round role re-anchoring:** Every broadcast that kicks off this phase must restate each member's core epistemic commitments (the epistemic stance + epistemic constraint from their 3-layer role description). This combats role collapse — the tendency of agents to drift toward consensus as the WHITEBOARD accumulates content.
```
With:
```markdown
- **Per-round role re-anchoring:** Every broadcast that kicks off this phase must restate each member's discipline and expected contribution (from setup/confirm). This combats role collapse — the tendency of agents to drift toward consensus as the WHITEBOARD accumulates content.
```

- [ ] **Step 2: Update critique section**

In the critique section, replace:
```markdown
- **Per-round role re-anchoring:** Every broadcast that kicks off this phase must restate each member's core epistemic commitments (the epistemic stance + epistemic constraint from their 3-layer role description).
```
With:
```markdown
- **Per-round role re-anchoring:** Every broadcast that kicks off this phase must restate each member's discipline and expected contribution (from setup/confirm).
```

- [ ] **Step 3: Update revise section**

In the revise section, replace:
```markdown
- **Per-round role re-anchoring:** The broadcast that kicks off this phase must restate each affected member's core epistemic commitments alongside the audit findings.
```
With:
```markdown
- **Per-round role re-anchoring:** The broadcast that kicks off this phase must restate each affected member's discipline and expected contribution alongside the audit findings.
```

- [ ] **Step 4: Commit**

```bash
git add skills/discussion-board/SKILL.md
git commit -m "refactor(discussion-board): simplify role re-anchoring to discipline + contribution"
```

### Task 6: Update plugin version

**Files:**
- Modify: `.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Check current version**

```bash
grep version .claude-plugin/plugin.json .claude-plugin/marketplace.json
```

- [ ] **Step 2: Bump patch version in both files**

Increment the patch version in both `plugin.json` and `marketplace.json`.

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore: bump version for discussion-board role selection redesign"
```

### Task 7: Verify final state

- [ ] **Step 1: Verify no remaining references to old concepts**

```bash
grep -n "fault-line\|fault line\|3-layer\|epistemic stance\|epistemic constraint\|Proposition Challenger" skills/discussion-board/SKILL.md
```

Expected: no matches.

- [ ] **Step 2: Verify expertise map references exist**

```bash
grep -n "expertise map\|Expertise Map\|Expertise mapping" skills/discussion-board/SKILL.md
```

Expected: matches in setup/explore, setup/confirm, and Workflow Overview.

- [ ] **Step 3: Verify team size minimum is 6**

```bash
grep -n "range\|fewer than\|minimum" skills/discussion-board/SKILL.md
```

Expected: "range 6-10" and "Fewer than 6 is not permitted."
