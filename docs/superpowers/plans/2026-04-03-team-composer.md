# team-composer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract common team composition logic from 4 board skills into a shared `forte:team-composer` skill.

**Architecture:** New `skills/team-composer/SKILL.md` defines expertise map → role generation → user approval → TeamCreate workflow. Each board's setup section is replaced with a `team-composer` invocation, keeping only board-specific spawn prompts. All boards adopt the always-doubling model (normal + `-cx` members) and deprecate Codex advisory.

**Tech Stack:** Claude Code skills (SKILL.md markdown), TeamCreate/SendMessage tools, codex exec CLI

---

### Task 1: Create team-composer SKILL.md

**Files:**
- Create: `skills/team-composer/SKILL.md`

- [ ] **Step 1: Create the skill directory**

```bash
mkdir -p skills/team-composer
```

- [ ] **Step 2: Write the SKILL.md file**

Create `skills/team-composer/SKILL.md` with the following content:

```markdown
---
name: team-composer
description: >-
  Dynamic team composition for board-type skills.
  Analyzes a topic, generates an expertise map, creates discipline-focused roles
  with always-doubling (normal + codex-explore members), and executes TeamCreate.
  Triggers: team-composer, チーム編成
---

# Team Composer — Dynamic Team Composition for Board Skills

Compose a team for structured board discussions. Analyzes the topic, generates an expertise map, creates discipline-focused roles with always-doubling (normal + `-cx` members), obtains user approval, and executes TeamCreate. Returns control to the calling board skill for member spawning.

## When to Use

- Called internally by board skills (discussion-board, design-board, frontend-design-board, investigation-board) during their setup phase
- NOT intended for direct user invocation

## Input Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `topic` | Yes | — | Discussion theme / design challenge / bug description |
| `team_name` | Yes | — | kebab-case ID for TeamCreate |
| `role_count` | No | `"3-6"` | Role count range |
| `domain_hints` | No | — | Domains to include (e.g., `"security, performance"`) |
| `constraints` | No | — | Board-specific constraint list. Natural language; interpreted as domain inclusion/exclusion rules (e.g., `["a11y non-negotiable axis"]` → must include a11y domain) |

## Output (Handoff Contract)

When team-composer completes, the following information is explicitly output to the conversation:

```
## Team Composer — Handoff
- **Team name**: {team_name}
- **Roles**:
  1. {role-name}: {discipline description}
  ...
- **Members**:
  | Name | Role | Type | Initial |
  |------|------|------|---------|
  | {role-name} | {role} | normal | {X} |
  | {role-name}-cx | {role} | cx | {X}X |
  ...
- **Initial Map**: {name} → {initial}, ...
```

The calling board skill uses this to spawn members with board-specific prompts.

## Member Composition Rules

### Always-Doubling

Each role gets exactly 2 members:

- **Normal member** (`{role-name}`): Participates in discussion directly
- **-cx member** (`{role-name}-cx`): Runs `codex exec` to explore the topic from their role's perspective before participating, bringing Codex-informed insights

| Role Count | Total Members |
|------------|--------------|
| 3 | 6 |
| 4 | 8 |
| 5 | 10 |
| 6 | 12 |

### Entry ID Initial Rule

- Normal member: First letter of name (uppercase). Example: `backend` → `B`
- `-cx` member: Normal initial + `X`. Example: `backend-cx` → `BX`
- If normal members collide: fall back to first 2 letters. Example: `backend-api` → `BA`, `backend-api-cx` → `BAX`
- Examples:
  - `[H-B-001]` = backend (normal)
  - `[H-BX-001]` = backend-cx
  - `[H-BA-001]` = backend-api (2-letter fallback)
  - `[H-BAX-001]` = backend-api-cx (2-letter fallback + X)

### Voting

- All members (normal and -cx) have voting rights
- Majority threshold: ⌊N/2⌋ + 1 where N = total members

### No Audit Role

Do not include an "Audit" or "Auditor" role. Audit is handled by the board leader during round flow.

## Workflow

### Phase 1: Expertise Map Generation

1. Analyze `topic` and `domain_hints` to identify relevant knowledge domains.
2. If `constraints` are provided, interpret each constraint and ensure the expertise map reflects it:
   - Inclusion constraint (e.g., `"a11y non-negotiable axis"`): The specified domain MUST appear in the map.
   - Exclusion constraint (e.g., `"exclude DevOps"`): The specified domain MUST NOT appear.
3. Generate `role_count` domains (within the specified range). Each domain must be **directly relevant** to the topic; do not include "nice to have" domains.
4. Format the expertise map:
   ```
   Expertise Map — {topic}
   1. {domain}: {why this topic requires this expertise}
   2. {domain}: {why this topic requires this expertise}
   ...
   ```

### Phase 2: Role Generation

1. Generate one role per domain. Each role has:
   - **Role name**: kebab-case, 1-2 words (English). Must work as `### {name}` subsection header.
   - **Discipline**: The specific expertise this member brings.
   - **Expected contribution**: Concrete contribution to the discussion.
2. Ensure normal member initials are unique within the team.
   - If collision is unavoidable with meaningful names, use first 2 letters as fallback.
3. Generate the member list (doubling applied):
   - `{role-name}` (normal, initial = first letter or 2-letter fallback)
   - `{role-name}-cx` (cx, initial = normal initial + `X`)

### Phase 3: User Approval

1. Present expertise map + role list + member table (with initials) to user.
   Format:
   ```
   Expertise Map — {topic}
   1. {domain}: {rationale}
   ...

   Proposed Roles:
   1. **{role-name}** — {discipline}
      > Expected contribution: {contribution}
      > Members: {role-name} ({initial}), {role-name}-cx ({initial}X)

   Total: {role_count} roles, {role_count * 2} members

   Add, remove, or modify roles as needed.
   ```
2. User may: approve, request modifications, or request more exploration (max 2 returns to Phase 1).
3. Max 3 re-presentations without convergence → ask user to specify roles in free text.

### Phase 4: TeamCreate

1. Execute TeamCreate with `team_name` and all member names (normal + -cx).
2. Output the Handoff Contract (see Output section above).
3. team-composer skill completes. Control returns to the calling board skill.

## -cx Member: codex exec Prompt Template

Board skills include this template in the spawn prompt for `-cx` members:

```
Before participating in the discussion, run a Codex exploration:

1. Write the following prompt to a temp file:
   "Analyze the codebase from a {role-description} perspective regarding: {topic}.
   Identify key considerations, potential issues, and insights that a {role-name}
   would find relevant. Cite specific file paths and line numbers as evidence."

2. Execute:
   cat <<'PROMPT_EOF' > /tmp/cx-explore-prompt.txt
   <constructed_prompt>
   PROMPT_EOF
   cat /tmp/cx-explore-prompt.txt | codex exec --ephemeral -m gpt-5.3-codex
   rm -f /tmp/cx-explore-prompt.txt

3. Use the findings as your unique perspective when writing hypotheses and critiques.
   Reference Codex findings with [codex-explored] label.

If codex CLI is not installed or fails, participate without Codex findings.
Note this in your first entry: (Codex exploration skipped: CLI not available)
```

Set Bash tool `timeout: 180000` (3 minutes) for the codex exec invocation.

## Error Handling

- If `constraints` reference a domain that conflicts with `domain_hints`, `constraints` take precedence.
- If user requests more roles than `role_count` max allows, inform user and suggest increasing the range or consolidating.
- If user requests fewer roles than `role_count` min, allow it (minimum 2 roles = 4 members).
```

- [ ] **Step 3: Verify the file exists and is well-formed**

```bash
head -5 skills/team-composer/SKILL.md
wc -l skills/team-composer/SKILL.md
```

Expected: First 5 lines show the YAML frontmatter (`---`, `name: team-composer`, etc.). Line count ~170.

- [ ] **Step 4: Commit**

```bash
git add skills/team-composer/SKILL.md
git commit -m "feat: add team-composer skill for shared team composition"
```

---

### Task 2: Update discussion-board to use team-composer

**Files:**
- Modify: `skills/discussion-board/SKILL.md`

- [ ] **Step 1: Replace setup/explore and setup/confirm sections**

In `skills/discussion-board/SKILL.md`, replace the `### setup/explore` section (lines ~215-238) and `### setup/confirm` section (lines ~240-268) with a single `### setup` section:

```markdown
### setup

- Invoke `forte:team-composer` with:
  - `topic`: the proposition
  - `team_name`: generate a kebab-case `{discussion-id}` from the proposition (e.g., `context-optimization`)
  - `role_count`: `"3-6"`
  - `domain_hints`: extracted from setup/explore questions (if any pre-context was given by user)
- After team-composer completes (Handoff Contract received):
  - Create `docs/discussions/{discussion-id}/WHITEBOARD.md` + `SYNTHESIS.md` using templates (see Reference Layer).
  - Ensure `docs/discussions/` is in `.gitignore` (add if missing).
  - SYNTHESIS.md initializes with `> Status: setup`.
  - Spawn all members with discussion-board-specific prompts:
    - Normal members: standard discussion participation prompt (discipline + expected contribution as briefing context).
    - `-cx` members: same prompt + codex exec exploration template (see team-composer skill for template).
  - Leader transitions to framing immediately.
```

- [ ] **Step 2: Update the Phase Model table**

Replace the `setup/explore` and `setup/confirm` rows with a single `setup` row:

```markdown
| setup | Invoke team-composer, create discussion files, spawn members | — | WHITEBOARD.md + SYNTHESIS.md created, team spawned | Team ready |
```

- [ ] **Step 3: Update Entry ID format documentation**

Add `-cx` member initial rule after the existing ID format section (around line 68):

```markdown
**-cx member initials:** `-cx` members use their normal member's initial + `X`. Example: `[H-BX-001]` = backend-cx member's hypothesis. See team-composer skill for full initial rules.
```

- [ ] **Step 4: Update Conflict Prevention Rules**

Add a rule for `-cx` members:

```markdown
| 6 | `-cx` members follow identical write-zone rules as normal members (own `### {name}` subsection only) | Same isolation guarantees |
```

- [ ] **Step 5: Update Ratification Rules**

Replace the fixed voting member table with the dynamic formula:

```markdown
## Ratification Rules

- **Voting members**: All members (normal + -cx). Count = role count × 2.
- **Majority threshold**: ⌊N/2⌋ + 1 where N = total voting members.
- **No advisory members**: All team members have voting rights.

| Total Members | Majority Threshold |
|---------------|-------------------|
| 6 | 4 |
| 8 | 5 |
| 10 | 6 |
| 12 | 7 |
```

- [ ] **Step 6: Remove the "Domain sufficiency check" and expertise-map-specific content**

These are now handled by team-composer. Remove from the skill:
- The "Expertise mapping" paragraph and format block (lines ~230-238)
- The "Domain sufficiency check" paragraph (line ~237)
- Name constraints paragraph that duplicates team-composer rules (lines ~254-258)

Keep board-specific rules that are NOT about team composition (framing, hypothesize, critique, etc.).

- [ ] **Step 7: Verify changes**

```bash
grep -n "team-composer" skills/discussion-board/SKILL.md
grep -n "setup/explore\|setup/confirm" skills/discussion-board/SKILL.md
```

Expected: `team-composer` appears in setup section. No remaining references to `setup/explore` or `setup/confirm`.

- [ ] **Step 8: Commit**

```bash
git add skills/discussion-board/SKILL.md
git commit -m "refactor(discussion-board): use team-composer for team composition"
```

---

### Task 3: Update design-board to use team-composer

**Files:**
- Modify: `skills/design-board/SKILL.md`

- [ ] **Step 1: Replace setup section**

Replace the `### setup` section (lines ~255-263) with:

```markdown
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
    - `-cx` members: same prompt + codex exec exploration template.
```

- [ ] **Step 2: Remove Codex Advisory Member section**

Delete the entire `## Codex Advisory Member` section (lines ~616-700), including:
- Prerequisites
- Workflow
- Hypothesize Prompt Template
- Critique Prompt Template
- Revise Prompt Template
- Invocation Pattern
- Verbatim Copy Rule
- Error Handling

- [ ] **Step 3: Remove Codex advisory steps from Phase Notes**

Remove these lines from Phase 1 and Phase 2 sections:
- "**Codex advisory step:** After all members report complete, leader reads WHITEBOARD.md, constructs Codex hypothesize prompt..." (line ~276)
- "**Codex advisory step:** After all members report complete, leader invokes Codex critique..." (line ~283)
- "**Codex advisory revise:** If any Codex entries were flagged..." (line ~381)

- [ ] **Step 4: Remove `### codex` subsections from WHITEBOARD templates**

In the WHITEBOARD.md template, remove all `### codex` subsection entries under Hypotheses, Critique, and any other phase sections.

- [ ] **Step 5: Update Conflict Prevention Rules**

Remove rule #8 (`### codex` subsection is leader-only). Add `-cx` member rule:

```markdown
| 8 | `-cx` members follow identical write-zone rules as normal members (own `### {name}` subsection only) | Same isolation guarantees |
```

- [ ] **Step 6: Update Ratification Rules**

Remove the `| codex | (advisory — no vote) |` row. Update the table to reflect always-doubling member counts:

```markdown
| Total Members | Majority Threshold |
|---------------|-------------------|
| 6 | 4 |
| 8 | 5 |
| 10 | 6 |
| 12 | 7 |

- All members (normal + -cx) have voting rights. No advisory members.
```

- [ ] **Step 7: Update Entry ID documentation**

Update the Note about Codex initials (line ~211) to reflect the new `-cx` initial rule:

```markdown
Note: `{phase}` = 1 or 2 to ensure IDs are globally unique across phases. `-cx` members use their normal member's initial + `X`. Example: backend → `B`, backend-cx → `BX`. Entry IDs: `[H-1-BX-001]`.
```

- [ ] **Step 8: Update Phase Model table**

Replace the setup row:

```markdown
| setup | Invoke team-composer, create phase files, spawn members | — | phase-1/ + phase-2/ WHITEBOARD.md + SYNTHESIS.md | Team spawned |
```

Remove Codex references from hypothesize and critique rows (remove "invoke Codex → `### codex`" from Leader Action column).

- [ ] **Step 9: Verify changes**

```bash
grep -n "team-composer" skills/design-board/SKILL.md
grep -n "Codex advisory\|codex advisory\|### codex" skills/design-board/SKILL.md
```

Expected: `team-composer` in setup. No remaining Codex advisory references.

- [ ] **Step 10: Commit**

```bash
git add skills/design-board/SKILL.md
git commit -m "refactor(design-board): use team-composer, remove Codex advisory"
```

---

### Task 4: Update frontend-design-board to use team-composer

**Files:**
- Modify: `skills/frontend-design-board/SKILL.md`

- [ ] **Step 1: Replace setup/explore and setup/confirm sections**

Replace `### setup/explore` (lines ~325-343) and `### setup/confirm` (lines ~345-354) with a single `### setup` section:

```markdown
### setup

- Leader analyzes the design topic and assesses clarity. Ask user 1 question at a time (max 4):
  1. このデザインの対象ユーザーは誰ですか？（年齢層、利用コンテキスト、技術リテラシー）
  2. 既存のブランドガイドラインやデザインシステムはありますか？
  3. 技術スタック上の制約はありますか？
  4. デザイン上の最大の懸念は何ですか？
- **Optional arguments:** If user provides `--design-system {path}` or `--brand-guide {path}`, read during setup.
- Invoke `forte:team-composer` with:
  - `topic`: the design topic
  - `team_name`: generate a kebab-case `{discussion-id}`
  - `role_count`: `"3-6"`
  - `constraints`: `["a11y non-negotiable axis"]`
  - `domain_hints`: extracted from user answers + design-domain seed axes (美的方向性, ユーザビリティ vs 表現性, パフォーマンス vs リッチネス, ブランド一貫性 vs 革新性)
- After team-composer completes (Handoff Contract received):
  - Create `docs/discussions/{discussion-id}/phase-1/` and `phase-2/` with WHITEBOARD.md + SYNTHESIS.md.
  - Ensure `docs/discussions/` is in `.gitignore`.
  - Spawn all members with frontend-design-board-specific prompts:
    - Normal members: 3-layer role description (discipline + epistemic stance + epistemic constraint) as briefing.
    - `-cx` members: same 3-layer prompt + codex exec exploration template.
  - **Important: 3-layer role enrichment** — team-composer provides role name + discipline only. The board adds epistemic stance (layer 2) and epistemic constraint (layer 3) at spawn time, using team-composer's role names and disciplines as the base. This moves 3-layer construction from setup/confirm to spawn, keeping team-composer domain-agnostic.
```

- [ ] **Step 2: Remove Codex Advisory sections**

Delete the Codex Advisory Member section (same pattern as design-board: prerequisites, workflow, prompt templates, invocation pattern, verbatim copy rule, error handling).

- [ ] **Step 3: Remove Codex advisory steps from Phase Notes**

Remove all "**Codex advisory step:**" lines from Phase 1 and Phase 2 hypothesize, critique, and revise sections.

- [ ] **Step 4: Remove `### codex` from WHITEBOARD templates**

Remove all `### codex` subsection entries from the template.

- [ ] **Step 5: Update member count and ratification rules**

Replace `Default 4 members, max 5. Codex is automatic and does not count toward this limit.` (line ~351) with:

```markdown
Member count is determined by team-composer (role_count × 2). All members (normal + -cx) have voting rights.
```

Update the ratification table to match the always-doubling model (same table as design-board Task 3 Step 6).

- [ ] **Step 6: Update Conflict Prevention Rules**

Remove `### codex` leader-only rule. Add `-cx` member write-zone rule.

- [ ] **Step 7: Update Entry ID documentation**

Same pattern as design-board: replace Codex initial `X` documentation with `-cx` initial rule (`{initial}X`).

- [ ] **Step 8: Update Phase Model table**

Replace setup/explore and setup/confirm rows with a single setup row:

```markdown
| setup | Analyze design topic, ask questions, invoke team-composer, create phase files, spawn members | — | phase-1/ + phase-2/ created, team spawned | Team ready |
```

Remove Codex references from hypothesize and critique rows.

- [ ] **Step 9: Verify changes**

```bash
grep -n "team-composer" skills/frontend-design-board/SKILL.md
grep -n "Codex advisory\|codex advisory\|### codex" skills/frontend-design-board/SKILL.md
grep -n "a11y non-negotiable" skills/frontend-design-board/SKILL.md
```

Expected: `team-composer` in setup with `a11y non-negotiable axis` constraint. No Codex advisory. `a11y non-negotiable` still referenced in constraints.

- [ ] **Step 10: Commit**

```bash
git add skills/frontend-design-board/SKILL.md
git commit -m "refactor(frontend-design-board): use team-composer, remove Codex advisory"
```

---

### Task 5: Update investigation-board to use team-composer

**Files:**
- Modify: `skills/investigation-board/SKILL.md`

- [ ] **Step 1: Replace setup section**

Replace `### setup` (lines ~290-298) with:

```markdown
### setup

- Invoke `forte:team-composer` with:
  - `topic`: the bug description / symptom
  - `team_name`: generate a kebab-case `{investigation-id}` from the bug description (e.g., `cache-memory-spike-on-login`)
  - `role_count`: `"3-6"`
- After team-composer completes (Handoff Contract received):
  - Create `docs/investigations/{investigation-id}/WHITEBOARD.md` + `SYNTHESIS.md` using templates.
  - Ensure `docs/investigations/` is in `.gitignore` (add if missing).
  - **Optional: codex-investigate pre-injection** — Before creating files, leader runs `codex-investigate` with the bug symptoms. If successful, output is included in Bug Report section as prior investigation context.
  - Spawn all members with investigation-board-specific prompts:
    - Normal members: standard investigation prompt + **role-specific investigation checklist** (3-5 focus items) + **few-shot example** (1 pair: good vs insufficient hypothesis, ~200-300 tokens).
    - `-cx` members: same prompt (including checklist + few-shot) + codex exec exploration template.
```

- [ ] **Step 2: Remove Codex Advisory sections**

Delete the Codex Advisory Member section (prerequisites, workflow, prompt templates, invocation pattern, verbatim copy rule, error handling).

- [ ] **Step 3: Remove Codex advisory steps from Phase Notes**

Remove all "**Codex advisory step:**" references from hypothesize, critique, and revise sections.

- [ ] **Step 4: Remove `### codex` from WHITEBOARD template**

Remove all `### codex` subsection entries. Remove the advisory member documentation from Core Principles section (line ~39: principle #12 about advisory members).

- [ ] **Step 5: Update Entry ID documentation**

Replace the advisory member ID documentation (line ~267) with the `-cx` initial rule:

```markdown
Note on -cx members: `-cx` members use their normal member's initial + `X`. Entry IDs: `[E-BX-001]`, `[H-BX-001]`, `[CR-BX-R1-001]`. All `-cx` members have voting rights (no advisory designation).
```

- [ ] **Step 6: Update Conflict Prevention and Ratification Rules**

Same pattern as other boards: remove codex-specific rules, add `-cx` write-zone rule, update ratification table.

- [ ] **Step 7: Update Phase Model table**

Replace the setup row:

```markdown
| setup | Invoke team-composer, create investigation files, spawn members | — | WHITEBOARD.md + SYNTHESIS.md | Team spawned |
```

Remove Codex references from other rows.

- [ ] **Step 8: Verify changes**

```bash
grep -n "team-composer" skills/investigation-board/SKILL.md
grep -n "Codex advisory\|codex advisory\|### codex\|\[advisory\]" skills/investigation-board/SKILL.md
grep -n "codex-investigate" skills/investigation-board/SKILL.md
```

Expected: `team-composer` in setup. No Codex advisory. `codex-investigate` still referenced (pre-injection is kept).

- [ ] **Step 9: Commit**

```bash
git add skills/investigation-board/SKILL.md
git commit -m "refactor(investigation-board): use team-composer, remove Codex advisory"
```

---

### Task 6: Version bump and CLAUDE.md update

**Files:**
- Modify: `.claude-plugin/plugin.json`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Bump version in plugin.json**

In `.claude-plugin/plugin.json`, change:

```json
"version": "1.16.0"
```

to:

```json
"version": "1.17.0"
```

- [ ] **Step 2: Update CLAUDE.md repository structure**

Add team-composer to the skills listing in `CLAUDE.md`:

```markdown
skills/
  batch-fix/           # Batch-fix code review findings with clear solutions
  code-review-board/   # Multi-perspective parallel code review (8 reviewer agents)
  codex-investigate/   # Bug root-cause investigation via Codex CLI
  codex-review/        # Design/code/hypothesis review via Codex CLI
  deep-fix/            # Deep-fix complex code review findings requiring design
  design-board/        # Implementation design via 2-phase structured team debate
  discussion-board/    # Structured team debate with iterative synthesis
  frontend-design-board/ # Frontend design discussion via 2-phase team debate
  investigation-board/ # Evidence-based bug investigation via structured team debate
  team-composer/       # Shared team composition for board skills (expertise map + always-doubling)
```

- [ ] **Step 3: Verify**

```bash
cat .claude-plugin/plugin.json | grep version
grep "team-composer" CLAUDE.md
```

Expected: Version shows `1.17.0`. CLAUDE.md lists team-composer.

- [ ] **Step 4: Commit**

```bash
git add .claude-plugin/plugin.json CLAUDE.md
git commit -m "chore: bump version to 1.17.0, add team-composer to docs"
```
