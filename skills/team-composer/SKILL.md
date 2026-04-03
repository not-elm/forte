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
