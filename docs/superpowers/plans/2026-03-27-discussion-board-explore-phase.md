# Discussion Board setup/explore Phase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the discussion-board setup phase into setup/explore (interactive perspective discovery) and setup/confirm (perspective approval + team creation).

**Architecture:** Single-file change to `skills/discussion-board/SKILL.md`. Four edit locations: Phase Model, Workflow Overview table, Phase Notes, and a version bump. All content is English (translating from the Japanese design spec). No code, no tests — this is a skill specification document.

**Tech Stack:** Markdown (SKILL.md skill spec), plugin.json + marketplace.json (version bump)

**Spec:** `docs/superpowers/specs/2026-03-27-discussion-board-explore-phase-design.md`

---

### Task 1: Update Phase Model (text + table)

**Files:**
- Modify: `skills/discussion-board/SKILL.md:36-42`

- [ ] **Step 1: Replace Phase Model code block (line 37)**

Replace:
```
setup → framing → [Round N: hypothesize → critique → audit → revise (if needed) → synthesize → ratify] → concluded
```

With:
```
setup/explore → setup/confirm → framing → [Round N: hypothesize → critique → audit → revise (if needed) → synthesize → ratify] → concluded
```

- [ ] **Step 2: Replace Phase Model table setup row (line 42)**

Replace:
```markdown
| setup | Leader + User | Analyze proposition, suggest 4-10 roles, user approves, create team |
```

With:
```markdown
| setup/explore | Leader + User | Analyze proposition, ask user questions one at a time to discover perspectives |
| setup/confirm | Leader + User | Present perspective list (name + description + rationale), user approves, create team + files |
```

- [ ] **Step 3: Verify edit**

Read lines 34-52 of `skills/discussion-board/SKILL.md` and confirm the Phase Model section now shows `setup/explore → setup/confirm` in both the code block and the table, with framing through concluded unchanged.

---

### Task 2: Update Workflow Overview table

**Files:**
- Modify: `skills/discussion-board/SKILL.md:173`

- [ ] **Step 1: Replace Workflow Overview setup row (line 173)**

Replace:
```markdown
| setup | Suggest 4-10 roles, create team + files | — | WHITEBOARD.md + SYNTHESIS.md | Team spawned |
```

With:
```markdown
| setup/explore | Analyze proposition, ask user questions one at a time to explore perspectives | — | Perspective insights from user dialogue | Leader has enough info for perspectives |
| setup/confirm | Generate perspective list (name + description + rationale), present to user for approval | — | Approved perspective list → team created, WHITEBOARD.md + SYNTHESIS.md | User approves perspectives |
```

- [ ] **Step 2: Verify edit**

Read lines 169-183 of `skills/discussion-board/SKILL.md` and confirm the Workflow Overview table has two setup rows with correct content, and all other rows (framing through concluded) are unchanged.

---

### Task 3: Replace Phase Notes ### setup

**Files:**
- Modify: `skills/discussion-board/SKILL.md:185-191`

- [ ] **Step 1: Replace ### setup section**

Replace the entire `### setup` section (lines 185-191):
```markdown
### setup

- Leader suggests 4-10 roles with distinct perspectives. Choose member count based on topic complexity: simple topics → 4-5, moderate → 6-7, complex/multifaceted → 8-10.
- User approves or modifies roles before team creation.
- Generate a kebab-case `{discussion-id}` from the proposition (e.g., `context-optimization`).
- Create `docs/discussions/{discussion-id}/WHITEBOARD.md` + `SYNTHESIS.md` using templates (see Reference Layer).
- Ensure `docs/discussions/` is in `.gitignore` (add if missing).
```

With:
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

### setup/confirm

- Generate a perspective list from explore results. Each perspective is presented as:
  ```
  1. **{Name}** — {one-line description}
     > Why needed: {rationale for this perspective in this discussion}
  ```
- Perspective count = team size (range 4-10).
  - If fewer than 4: leader proposes supplementary perspectives with explicit rationale.
  - If more than 10: leader presents consolidation candidates for user to choose.
- **Name constraints** (perspectives become role names = subsection headers = ID initials):
  - Short English names (1-2 words, space-separated).
  - Must work as `### {name}` subsection headers.
  - First-letter initials (uppercase) must be unique within the team (prevents `[H-{initial}-{seq}]` ID collisions).
  - If initial collision is unavoidable with meaningful names, use first two letters as the initial fallback.
- User approval gate: "These are the perspectives for the team. Add, remove, or modify as needed."
  - User requests modification → leader revises and re-presents (loop within confirm).
  - User requests more questions → return to explore (max 2 returns; question count is cumulative).
  - Max 3 re-presentations without convergence → ask user to specify roles in free text.
- After user approves:
  - Each perspective name becomes a role name (= member name) for team creation.
  - Generate a kebab-case `{discussion-id}` from the proposition (e.g., `context-optimization`).
  - Create `docs/discussions/{discussion-id}/WHITEBOARD.md` + `SYNTHESIS.md` using templates (see Reference Layer).
  - Ensure `docs/discussions/` is in `.gitignore` (add if missing).
  - SYNTHESIS.md initializes with `> Status: setup` as before; leader transitions to framing immediately.
```

- [ ] **Step 2: Verify edit**

Read lines 183-230 of `skills/discussion-board/SKILL.md` and confirm:
- `### setup` is gone
- `### setup/explore` and `### setup/confirm` are present with full content
- `### framing` follows immediately after (unchanged)

---

### Task 4: Commit

**Files:**
- All changes in: `skills/discussion-board/SKILL.md`

- [ ] **Step 1: Review full diff**

Run: `git diff skills/discussion-board/SKILL.md`

Verify:
- Phase Model code block updated (1 line)
- Phase Model table: 1 row → 2 rows
- Workflow Overview table: 1 row → 2 rows
- Phase Notes: `### setup` (7 lines) → `### setup/explore` + `### setup/confirm` (~35 lines)
- No other sections modified

- [ ] **Step 2: Commit**

```bash
git add skills/discussion-board/SKILL.md
git commit -m "feat(discussion-board): split setup into explore/confirm sub-phases

Add interactive perspective discovery (setup/explore) before team creation
(setup/confirm). Leader asks user 2-6 questions to identify discussion
perspectives, which become team roles directly.

Spec: docs/superpowers/specs/2026-03-27-discussion-board-explore-phase-design.md"
```

---

### Task 5: Bump plugin version

**Files:**
- Modify: `.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Read current versions**

Read `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` to find current version.

- [ ] **Step 2: Bump minor version**

Increment the minor version (e.g., `1.7.0` → `1.8.0`) in both files.

- [ ] **Step 3: Commit version bump**

```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore: bump version to 1.8.0"
```
