---
name: frontend-design-board
description: >-
  Frontend design discussion via 2-phase structured team debate.
  Phase 1 builds design direction consensus (tone, purpose, target user),
  Phase 2 specifies design tokens, responsive strategy, and motion policy.
  Outputs a Design Spec mapped to frontend-design skill input format.
  Triggers: UIデザイン議論, デザイン方針を議論, UIの方向性, frontend design discussion, UI discussion, フロントエンドデザイン議論
---

# Frontend Design Board — 2-Phase Design Discussion via Team Debate

Produce a concrete Design Spec through structured 2-phase team debate: Phase 1 (Design Direction) builds consensus on aesthetic direction, tone, and target user; Phase 2 (Design Specification) defines tokens, responsive strategy, and motion policy. Outputs a Design Spec that maps directly to the frontend-design skill's Design Thinking input format. Uses TeamCreate + SendMessage + AskUserQuestion.

## When to Use

- The task requires discussing and deciding frontend design direction with multiple perspectives
- Keywords: "UIデザイン議論", "デザイン方針を議論", "UIの方向性", "frontend design discussion", "UI discussion", "フロントエンドデザイン議論"

## When NOT to Use

- Use `frontend-design` for immediate implementation without design discussion
- Use `design-board` for implementation design with technology selection (backend/architecture focus)
- Use `discussion-board` for open-ended exploration not specific to frontend design

## Core Principles

1. **Design-direction-centric** — All activity targets producing an actionable Design Spec for frontend implementation.
2. **2-phase model** — Phase 1 (Design Direction) builds aesthetic consensus; Phase 2 (Design Specification) produces concrete tokens and strategies. Each phase has its own WHITEBOARD.md + SYNTHESIS.md in separate subdirectories.
3. **2-file model per phase** — WHITEBOARD.md (framing + hypotheses + critiques) + SYNTHESIS.md (leader-managed state), in `docs/discussions/{discussion-id}/phase-{N}/`.
4. **Per-member write zones** — Each teammate writes only to their own `### {name}` subsection in WHITEBOARD.md.
5. **Leader-only SYNTHESIS.md** — Teammates read but never write to SYNTHESIS.md.
6. **Append-only** — Teammates add content, never delete or modify existing entries.
7. **Leader as synthesizer, not participant** — Leader does NOT write hypotheses or critiques. Leader MAY write process artifacts (audit results, evidence maps, conclusions). **Exception:** Leader acts as scribe/proxy for advisory members (e.g., Codex).
8. **Structured phase handoff** — Phase 1 SYNTHESIS.md is the mandatory context injection source for Phase 2. Leader pushes Phase 1 conclusions via broadcast at Phase 2 framing start.
9. **Advisory members** — Non-voting participants (e.g., Codex) contribute hypotheses and critiques but do not vote in ratification. Leader manages their participation directly.
10. **Principle-based critique** — Critiques must reference design principles (contrast, repetition, alignment, proximity, visual hierarchy, Gestalt), not subjective preferences. "I don't like it" is never valid; "this violates the alignment principle because..." is required.
11. **Staged concreteness** — Phase 1 uses linguistic descriptions (mood, direction, references); Phase 2 requires CSS Custom Properties token definitions. This prevents premature specificity from suppressing creative exploration.

## Phase Model

```
setup/explore → setup/confirm → [Phase 1: framing → hypothesize → critique → synthesize → ratify] → user-review → [Phase 2: framing → [Round N: hypothesize → critique → audit → revise (if needed) → synthesize → ratify] ] → concluded
```

### Phase 1 — Design Direction (5 steps)

| Step | Who | What |
|------|-----|------|
| framing | All members | Document design context: purpose, aesthetic instincts, target user, constraints, unknowns |
| hypothesize | All members + Codex (advisory) | Propose design directions: tone, mood, aesthetic stance, reference points |
| critique | All members + Codex (advisory) | Challenge/support/amend/question directions using design principles |
| synthesize | Leader only | Read all content, write Evidence Map + Direction Conclusion in SYNTHESIS.md |
| ratify | All voting members | Vote accept or push-back on design direction. Simple majority ratifies |

Phase 1 does NOT include audit or revise. Hypotheses are linguistic descriptions; code snippets are optional.

### User Review

Leader presents Phase 1 direction conclusion to the user via AskUserQuestion:
- Include: selected design direction (tone, mood, purpose), key trade-offs, rejected alternatives with reasons
- User choices: "Proceed to Phase 2" or "Provide feedback on the design direction"
- If user provides feedback: Leader records feedback in phase-1/SYNTHESIS.md `## User Review Outcome`, then incorporates it as additional constraints for Phase 2 framing. Phase 1 files are NOT re-executed.
- No skip option — user confirmation is mandatory

### Phase 2 — Design Specification (6 steps + conditional revise)

| Step | Who | What |
|------|-----|------|
| framing | All members | Document specification constraints, scope, acceptance criteria (informed by Phase 1 direction) |
| hypothesize | All members + Codex (advisory) | Propose concrete design specifications: token definitions (required), responsive strategy, motion policy |
| critique | All members + Codex (advisory) | Challenge/support/amend/question specifications with design principle references and axis tags |
| audit | Leader only | Run Codex CLI to fact-check: a11y (WCAG 2.1/2.2 AA), browser compat, performance (CLS/LCP). Aesthetic judgments excluded |
| revise | All members (conditional) | Append corrections if audit found inaccuracies (skipped if all clean) |
| synthesize | Leader only | Read all content, write Evidence Map + Draft Design Spec in SYNTHESIS.md |
| ratify | All voting members | Vote accept or push-back via SendMessage. Simple majority ratifies |

## Entry Formats

### Framing

Structured fields in each member's `### {name}` Framing subsection (no entry IDs):

**Phase 1 framing (Design Direction):**
```markdown
- **Purpose**: {what problem this interface solves and who uses it}
- **Aesthetic Instinct**: {initial gut feeling about tone/mood/direction — will be debated}
- **Target User**: {who the design serves — demographics, context, needs}
- **Constraints**: {technical requirements, brand guidelines, existing design system, accessibility needs}
- **Unknowns**: {open questions about design direction}
```

**Phase 2 framing (Design Specification):**
```markdown
- **Scope**: {what this specification covers — token categories, responsive targets, motion scope}
- **Direction Constraints**: {from Phase 1 conclusions + user feedback}
- **Acceptance Criteria**: {what makes a good design specification}
- **Unknowns**: {open questions about specification details}
```

### Hypothesis

**ID format:** `[H-{phase}-{initial}-{seq}]` — `{phase}` = 1 or 2; `{initial}` = first letter of name (uppercase); `{seq}` = 001, 002, ...

**Phase 1 example (design direction — linguistic, code snippet optional):**
```markdown
- [H-1-V-001] **hypothesis** axis=typography,color: エディトリアル/マガジン系のトーンで、Playfair Display + Source Serif Proのクラシカルなセリフペアリングと、深いグリーン (#1B4332) を基調としたアースカラーパレットを採用する。
  > Rationale: ターゲットユーザー（30代以上の読書家層）にとって、セリフ体の権威性と自然系カラーの落ち着きが長時間閲覧の快適性を高める。
```

**Phase 2 example (design specification — token definition required):**
```markdown
- [H-2-T-001] **hypothesis** axis=color: カラートークンをセマンティックレイヤーで定義し、ライト/ダーク/ハイコントラストの3テーマ行列とする。
  > Rationale: テーマ分離を仕様段階でトークン化することで、実装時のWCAG AA準拠を構造的に担保する。
  > Token definition:
  > ```css
  > /* Light theme */
  > --color-surface: #FAFAF5;
  > --color-on-surface: #1B4332;
  > --color-primary: #2D6A4F;
  > --color-accent: #D4A373;
  >
  > /* Dark theme */
  > --color-surface: #1A1A2E;
  > --color-on-surface: #E8E8D6;
  > --color-primary: #52B788;
  > --color-accent: #E9C46A;
  >
  > /* High contrast theme */
  > --color-surface: #000000;
  > --color-on-surface: #FFFFFF;
  > --color-primary: #00FF88;
  > --color-accent: #FFD700;
  > ```
```

### Critique

**ID format:** `[CR-{phase}-{initial}-R{round}-{seq}]`

Each critique must include: label (`**challenge**`/`**support**`/`**amend**`/`**question**`), `refs=[...]`, `@{member}`, and `axis={tag}` (one or more from: typography, color, layout, motion, accessibility, spatial-composition, spacing, elevation).

**Recommended critique body structure** (Feldman model — recommended, not required):
```markdown
#### Round 1
- [CR-1-A-R1-001] **challenge** @visual-designer refs=[H-1-V-001] axis=typography:
  記述: Playfair Display の x-height は低く、16px以下でのボディテキスト可読性が低下する
  分析: 長文閲覧用途ではx-height比0.48以上が推奨される（Playfair は約0.44）
  解釈: ターゲットユーザーの「長時間閲覧」要件と矛盾するリスク
  判断: ディスプレイ用途に限定し、ボディにはx-heightの高いセリフ体（Literata, Charter等）を提案
```

The Feldman structure (記述→分析→解釈→判断) is a **recommended template** to improve critique quality. It is NOT required — members may write free-form critiques with the standard label + refs + axis format. The 4-label system (challenge/support/amend/question) from discussion-board is the only **required** structure.

### Evidence Map (Leader only)

| # | Claim | Support | Counterpoint | Confidence |
|---|-------|---------|--------------|------------|
| 1 | {claim} | refs=[H-1-X-001, CR-1-Y-R1-002] | refs=[CR-1-Z-R1-001] | high/medium/low |

### Draft Conclusion (Leader only)

**Phase 1 — Direction Conclusion:**
```markdown
## Direction Conclusion
**Design Direction:** {selected tone/mood/aesthetic with rationale}
**Purpose:** {what problem this interface solves}
**Target User:** {who the design serves}
**Rejected Directions:** {alternatives with reasons}
**Trade-offs:** {key trade-offs accepted}
**Open questions for Phase 2:** {items to resolve during specification}
```

**Phase 2 — Draft Design Spec:**
```markdown
## Draft Design Spec — Round {N}
{Synthesized specification citing entry IDs. Mark areas of uncertainty.}
**Key claims:** 1, 2, 3 (from Evidence Map)
**Unresolved:** {low-confidence or unaddressed claims}
```

### Ratification History (Leader only)

```markdown
### Round {N}
| Member | Vote | Reason |
|--------|------|--------|
| {name} | accept / push-back | {brief reason} |
**Result:** {count}/{total} — {ratified | not ratified}
```

### Minority Report (Leader only)

Written only when conclusion is ratified with dissent:

```markdown
**Dissenter(s):** {names}  **Position:** {view}  **Evidence:** refs=[...]
**Leader note:** {why majority view was adopted}
```

### Completion Report

Members send this via SendMessage after each sub-phase:

```
Entries added: {N}
Key insight: {most important finding}
Current position: {stance in one sentence}
Remaining concerns: {description or "none"}
```

### Audit (Phase 2 only)

Leader-only. Written per round after Codex CLI fact-check. **Scope is limited to 3 axes — aesthetic judgments are explicitly excluded:**

1. **Accessibility** — WCAG 2.1/2.2 AA compliance (contrast ratio 4.5:1, target size 24x24px minimum per SC 2.5.8)
2. **Browser compatibility** — CSS feature support status across major browsers
3. **Performance** — CLS ≤ 0.1, LCP ≤ 2.5s impact assessment

| Entry | Claim Summary | Verdict | Notes |
|-------|--------------|---------|-------|
| [H-2-T-001] | {claim} | ✅/⚠️/❌/❓ | {evidence or reason} |

Verdict rubric:
- ✅ **Verified**: Claim is factually accurate
- ⚠️ **Partially accurate**: Contains some truth but misleading, incomplete, or outdated
- ❌ **Inaccurate**: Factually wrong
- ❓ **Unverifiable**: Cannot be verified (subjective, speculative, or insufficient context)

Granularity: one row per hypothesis or critique entry (by entry ID), not per sentence.

### Revision (Phase 2 only)

Members append corrections in their own subsection (append-only — original entry is never modified).

```markdown
- [H-2-T-001] **revised**: Updated claim based on audit [Round {N}]. {corrected statement}
  > Original: {original claim}. Audit note: {audit note}.
```

### ID Summary

| Type | Format | Section | Phase |
|------|--------|---------|-------|
| Framing | (no ID — structured fields) | Framing | framing (both phases) |
| Hypothesis | `[H-{phase}-{initial}-{seq}]` | Hypotheses | hypothesize (both phases) |
| Critique | `[CR-{phase}-{initial}-R{round}-{seq}]` | Critique → Round N | critique (both phases) |
| Audit | (no ID — table format) | Audit → Round N | audit (Phase 2 only) |
| Revision | `[{original-ID}] **revised**` | Hypotheses or Critique | revise (Phase 2 only) |

Note: `{phase}` = 1 or 2 to ensure IDs are globally unique across phases. Codex (advisory) uses fixed initial `X` (eXternal). Entry IDs: `[H-1-X-NNN]`, `[CR-2-X-R{N}-NNN]`.

---

# Workflow Layer

## Workflow Overview

### Phase 1 — Design Direction

| Step | Leader Action | Member Action | Output | Next Trigger |
|------|---------------|---------------|--------|--------------|
| setup/explore | Analyze topic, ask user questions, generate fault-line map with design-domain seeds | — | Fault-line map + design context | Leader has map + enough info for roles |
| setup/confirm | Construct 3-layer roles from fault-line map, ensure a11y non-negotiable axis, present to user | — | Approved role list → team + phase files created | User approves roles |
| framing | Broadcast framing instructions | Document design context in own section | Framing entries | All members report complete |
| hypothesize | Broadcast kickoff; after members, invoke Codex → `### codex` | Write direction hypotheses (linguistic, code optional) | Hypothesis entries | All complete + Codex written |
| critique | Broadcast instructions; after members, invoke Codex → `### codex` | Write critiques with labels + axis tags + refs | Critique entries | All complete + Codex written |
| synthesize | Read all WHITEBOARD, write Evidence Map + Direction Conclusion | — | phase-1/SYNTHESIS.md updated | Conclusion written |
| ratify | Broadcast ratify request to voting members | Send vote via SendMessage | Ratification History | Majority reached or next round |

### User Review

| Step | Leader Action | Output | Next Trigger |
|------|---------------|--------|--------------|
| user-review | Present Phase 1 Direction Conclusion via AskUserQuestion | User approval or feedback | User responds |

### Phase 2 — Design Specification

| Step | Leader Action | Member Action | Output | Next Trigger |
|------|---------------|---------------|--------|--------------|
| framing | Broadcast Phase 1 conclusions + framing instructions | Document specification constraints in own section | Framing entries | All members report complete |
| hypothesize | Broadcast kickoff; after members, invoke Codex → `### codex` | Write specification hypotheses (token definitions required) | Hypothesis entries | All complete + Codex written |
| critique | Broadcast instructions; after members, invoke Codex → `### codex` | Write critiques with labels + axis tags + refs | Critique entries | All complete + Codex written |
| audit | Run Codex CLI on current round (a11y/compat/perf only, NO aesthetic judgment) | — | phase-2/WHITEBOARD.md `## Audit → Round {N}` updated | Audit written |
| revise | Broadcast audit findings to affected members | Append corrections (append-only) | Revised entries | All affected complete (or skipped if all clean) |
| synthesize | Read all WHITEBOARD, write Evidence Map + Draft Design Spec | — | phase-2/SYNTHESIS.md updated | Draft written |
| ratify | Broadcast ratify request to voting members | Send vote via SendMessage | Ratification History | Majority reached or next round |

### Concluded

| Step | Leader Action | Output |
|------|---------------|--------|
| concluded | Generate Design Spec file, delete discussion directory | `docs/plans/YYYY-MM-DD-{topic}-design-spec.md` |

## Phase Notes

### setup/explore

- Leader analyzes the design topic and assesses its clarity before asking questions.
- Ask the user one question at a time (never combine multiple questions in one message).
- **Design-domain question templates** (use as starting points, adapt to topic):
  1. このデザインの対象ユーザーは誰ですか？（年齢層、利用コンテキスト、技術リテラシー）
  2. 既存のブランドガイドラインやデザインシステムはありますか？（パス指定 or なし）
  3. 技術スタック上の制約はありますか？（フレームワーク、CSS制限、パフォーマンス要件）
  4. デザイン上の最大の懸念は何ですか？（方向性の迷い、既存デザインとの整合性、a11y等）
- Maximum 4 questions (design domain is constrained enough to not need 6).
- Question count is cumulative across all explore visits (does not reset if returning from confirm).
- **Optional arguments:** If user provides `--design-system {path}` or `--brand-guide {path}`, read these files during explore and incorporate as constraints.
- **Fault-line mapping:** Before generating roles, produce a fault-line map — 3-5 axes of disagreement. Use **design-domain seed axes** to guide generation:
  - 美的方向性の対立（ミニマリズム vs マキシマリズム, ブルータリスト vs リファインド, etc.）
  - ユーザビリティ vs 表現性
  - パフォーマンス vs リッチネス
  - ブランド一貫性 vs 革新性
  - **Non-negotiable axis: アクセシビリティ** — At least one fault line MUST position accessibility as a tension against another value (e.g., "WCAG AAA compliance vs. aesthetic freedom"). This is NOT optional; it ensures a11y perspective is structurally guaranteed in the team.
- The fault-line map is presented to the user alongside the role list in setup/confirm (not separately approved).

### setup/confirm

- Generate roles from the fault-line map. Each role is **constructed with three layers**:
  1. **Discipline-grounded identity** — activates domain-specific design knowledge (e.g., "Typography Specialist", "Motion Designer", "UX Researcher")
  2. **Epistemic stance** — constrains reasoning toward a design perspective (e.g., "prioritizes readability metrics over aesthetic novelty", "argues from user research data")
  3. **Explicit epistemic constraint** — specifies evidence requirements and blind spots to guard (e.g., "rejects aesthetic arguments without WCAG compliance data", "requires user context before accepting layout changes")
- Default 4 members, max 5. Codex is automatic and does not count toward this limit.
- Due to the non-negotiable a11y fault line, at least one member WILL have accessibility as a primary concern in their 3-layer role — this is guaranteed by construction, not by a fixed role slot.
- Present the fault-line map + roles to user via AskUserQuestion. User may: approve, request modifications, or request more questions (return to explore, max 2 returns).
- After approval: create `docs/discussions/{discussion-id}/phase-1/` and `docs/discussions/{discussion-id}/phase-2/` with WHITEBOARD.md + SYNTHESIS.md using templates. Ensure `docs/discussions/` is in `.gitignore`.

### Phase 1: framing

- Members use full WHITEBOARD.md Read (file is small, ~100 lines at this stage).
- Leader combines completion confirmation + hypothesize kickoff in 1 broadcast.
- Framing should focus on design context: purpose, aesthetic instincts, target user, constraints.

### Phase 1: hypothesize

- **Independent generation (Round 1 only):** Members generate hypotheses WITHOUT reading other members' framing entries. Each member receives only the topic and their own role briefing (3-layer description). This eliminates first-mover anchoring.
- **Per-round role re-anchoring:** Every broadcast must restate each member's core epistemic commitments.
- Each member aims for 2-5 hypotheses about design direction. Hypotheses are primarily linguistic (mood, tone, references). Code snippets (CSS variables, font-family declarations) are permitted but NOT required.
- Each hypothesis MUST include at least one `axis=` tag.
- Report completion using the completion report format.
- **Codex advisory step:** After all members report complete, leader reads WHITEBOARD.md, constructs Codex hypothesize prompt, runs `codex exec`, writes results to `### codex`.

### Phase 1: critique

- **Per-round role re-anchoring:** Every broadcast must restate each member's core epistemic commitments.
- **IMPORTANT**: Use 2-step Grep extraction when WHITEBOARD exceeds ~350 lines.
- Members must label each critique: challenge/support/amend/question.
- Cite refs=[], @member, and axis= for every entry.
- **Feldman template encouraged** (記述→分析→解釈→判断) but not enforced.
- **Codex advisory step:** Same pattern as hypothesize.

### Phase 1: synthesize

- Leader reads ALL phase-1/WHITEBOARD.md content.
- Writes Evidence Map + Direction Conclusion in phase-1/SYNTHESIS.md.
- Direction Conclusion must clearly state: design direction (tone/mood/aesthetic), purpose, target user, rejected alternatives, key trade-offs, and open questions for Phase 2.

### Phase 1: ratify

- Votes via SendMessage: `RATIFY: accept — {reason}` or `RATIFY: push-back — {concerns}`
- Simple majority: ⌊N/2⌋ + 1 required.
- If not ratified: incorporate push-back, start next critique round (within Phase 1).
- Max 10 rounds. On exhaustion: leader writes "best available direction" with uncertainty markers.

### user-review

- Leader reads phase-1/SYNTHESIS.md Direction Conclusion.
- Presents to user via AskUserQuestion with structured summary:
  ```
  Phase 1 (Design Direction) is complete.

  **Design Direction:**
  {selected tone/mood/aesthetic with brief rationale}

  **Purpose:** {what this interface solves}
  **Target User:** {who it serves}

  **Key trade-offs:**
  {bullet list of accepted trade-offs}

  **Rejected alternatives:**
  {bullet list with reasons}

  Options:
  1. Proceed to Phase 2 (Design Specification) with this direction
  2. Provide feedback on the design direction (will be incorporated as Phase 2 constraints)
  ```
- If user provides feedback: record in `## User Review Outcome`, incorporate as Phase 2 constraints.

### Phase 2: framing

- **Context injection (Push-based):** Leader reads phase-1/SYNTHESIS.md, extracts Direction Conclusion, and includes it in the framing broadcast. Members do NOT read phase-1/ files directly.
- If user provided feedback during user-review, include it as additional constraints.
- Framing should focus on specification scope, acceptance criteria, and which token categories to define.

### Phase 2: hypothesize

- Members read all Phase 2 framings via full WHITEBOARD.md Read.
- **Token definition block is REQUIRED** in Phase 2 hypotheses. Each hypothesis must include at least one CSS Custom Properties code block defining design tokens. Hypotheses without token definitions are returned for revision.
- **Theme matrix:** Token hypotheses that define color tokens MUST include light/dark/high-contrast variants. Motion token hypotheses MUST address `prefers-reduced-motion` handling policy (disable, shorten, or provide alternatives — WCAG does not mandate 0ms specifically).
- Each hypothesis MUST include at least one `axis=` tag.
- Report completion using the completion report format.
- **Codex advisory step:** Same pattern as Phase 1.

### Phase 2: critique

- Same rules as Phase 1 critique, plus: critiques of token definitions SHOULD include quantitative checks (contrast ratio, spacing ratio, type scale ratio) when applicable.
- **Codex advisory step:** Same pattern as Phase 1.

### Phase 2: audit

- **Prerequisite:** `codex` CLI must be installed (`npm i -g @openai/codex`). If not available, skip audit, log warning in SYNTHESIS.md status, proceed to synthesize.
- **Scope is strictly limited to 3 axes. Aesthetic judgments are EXCLUDED:**
  1. **Accessibility**: WCAG 2.1/2.2 AA (contrast ratio ≥ 4.5:1 for normal text per SC 1.4.3, target size ≥ 24x24px per SC 2.5.8)
  2. **Browser compatibility**: CSS feature support (e.g., oklch() color space, container queries)
  3. **Performance**: CLS ≤ 0.1, LCP ≤ 2.5s impact
- **Explicit exclusion instruction in Codex prompt:** "Do NOT evaluate aesthetic quality, visual appeal, or design taste. Only verify factual claims about accessibility standards, browser support, and performance metrics."
- Audit only entries from the current round (incremental).
- Execute via temp file + stdin:
  ```bash
  TMPFILE=$(mktemp)
  cat <<'PROMPT_EOF' > "$TMPFILE"
  <constructed_prompt>
  PROMPT_EOF
  cat "$TMPFILE" | codex exec
  rm -f "$TMPFILE"
  ```
- Write results to phase-2/WHITEBOARD.md `## Audit` → `### Round {N}`.
- **Decision logic:** All ✅ or ❓ → skip revise; Any ⚠️ or ❌ → proceed to revise.

### Phase 2: revise

- Only runs when audit found ⚠️ or ❌.
- Members append corrections (append-only). Max 1 revise round per audit.
- **Codex advisory revise:** If Codex entries flagged, leader re-invokes Codex with flagged entries.

### Phase 2: synthesize

- Leader reads ALL phase-2/WHITEBOARD.md content.
- Writes Evidence Map + Draft Design Spec in phase-2/SYNTHESIS.md.
- Draft Design Spec must include the Design Thinking Mapping (5-axis) and token definition tables.

### Phase 2: ratify

- Same rules as Phase 1 ratify.
- If not ratified: next round starts at `critique` (members write new critiques, then audit → revise → synthesize → ratify).

### concluded

- Leader writes `## Final Design Spec` in phase-2/SYNTHESIS.md.
- Leader generates the Design Spec file at `docs/plans/YYYY-MM-DD-{topic}-design-spec.md` (see Design Spec Template in Reference Layer).
- Content is derived from both phase-1/SYNTHESIS.md (design direction) and phase-2/SYNTHESIS.md (specifications).
- Verify the file was created successfully.
- Delete `docs/discussions/{discussion-id}/` directory after successful export.

## Communication Rules

- All leader → member instructions via **broadcast** (NOT individual SendMessage).
- Use structured short format: Phase / Step / Action / Format-ref (~80-120 tokens).
- Combine phase transitions: completion confirmation + next phase instruction in 1 broadcast.
- Phase 2 framing broadcast MUST include Phase 1 Direction Conclusion summary (Push-based context injection).

---

# Reference Layer

## WHITEBOARD.md Templates

### Phase 1 WHITEBOARD

Path: `docs/discussions/{discussion-id}/phase-1/WHITEBOARD.md`

```markdown
# WHITEBOARD — {discussion-id} / Phase 1: Design Direction
> Topic: {design topic}
> Created: {YYYY-MM-DD}
> Team: {comma-separated names}

## Topic
{Clear statement of the design challenge. Include context, target user, and motivation.}

## How Our Work Connects
{Each member's role and perspective — full 3-layer description.}

- **codex** (advisory, non-voting): Cross-model perspective via Codex CLI. Contributes hypotheses and critiques but does not vote.

## Framing
### {member-A}
### {member-B}
### {member-C}
### {member-D}

## Hypotheses
### {member-A}
### {member-B}
### {member-C}
### {member-D}
### codex

## Critique
### {member-A}
### {member-B}
### {member-C}
### {member-D}
### codex
```

### Phase 2 WHITEBOARD

Path: `docs/discussions/{discussion-id}/phase-2/WHITEBOARD.md`

```markdown
# WHITEBOARD — {discussion-id} / Phase 2: Design Specification
> Topic: {design topic}
> Created: {YYYY-MM-DD}
> Team: {comma-separated names}

## Topic
{Clear statement of the design challenge. Include context, target user, and motivation.}

## How Our Work Connects
{Each member's role and perspective — full 3-layer description.}

- **codex** (advisory, non-voting): Cross-model perspective via Codex CLI. Contributes hypotheses and critiques but does not vote.

## Framing
### {member-A}
### {member-B}
### {member-C}
### {member-D}

## Hypotheses
### {member-A}
### {member-B}
### {member-C}
### {member-D}
### codex

## Critique
### {member-A}
### {member-B}
### {member-C}
### {member-D}
### codex

## Audit
```

No Status/Round header in WHITEBOARD — managed in SYNTHESIS.md. Sections start empty. Phase 1 has no `## Audit` section (audit is Phase 2 only).

## SYNTHESIS.md Templates

Path: `docs/discussions/{discussion-id}/phase-{N}/SYNTHESIS.md`

**Phase 1:**
```markdown
# SYNTHESIS — {discussion-id} / Phase 1: Design Direction
> Status: setup

## Evidence Map
## Direction Conclusion
## Ratification History
## Minority Report
## User Review Outcome
```

**Phase 2:**
```markdown
# SYNTHESIS — {discussion-id} / Phase 2: Design Specification
> Status: setup
> Round: 0
> Max Rounds: 10

## Evidence Map
## Draft Design Spec
## Ratification History
## Minority Report
## Final Design Spec
```

Leader-only files. See Entry Formats above for section content structure.

## Design Spec Template

Path: `docs/plans/YYYY-MM-DD-{topic}-design-spec.md`

Exported by leader during `concluded` phase. This is the permanent record of the frontend design board outcome.

```markdown
# {Topic} Design Spec

> Date: {YYYY-MM-DD}
> Status: Approved ({accept_count}/{total} {unanimous/majority})
> Method: Frontend Design Board ({N}-member 2-phase structured debate)

## Summary
{2-3 sentence summary of the design direction and key specifications}

## Design Thinking Mapping

> This section maps directly to the frontend-design skill's Design Thinking input format.

- **Purpose**: {what problem this interface solves and who uses it}
- **Tone**: {selected aesthetic direction — e.g., "editorial minimalism with warm earth tones"}
- **Target User**: {who the design serves — demographics, context, needs}
- **Constraints**: {technical requirements, brand guidelines, accessibility requirements}
- **Differentiation**: {what makes this design unforgettable — the one thing someone will remember}

## Design Token Definition

### Color Tokens

| Token | Light | Dark | High Contrast |
|-------|-------|------|---------------|
| --color-surface | {value} | {value} | {value} |
| --color-on-surface | {value} | {value} | {value} |
| --color-primary | {value} | {value} | {value} |
| --color-accent | {value} | {value} | {value} |

### Typography Tokens

```css
--font-display: '{display font}', {fallback};
--font-body: '{body font}', {fallback};
--font-size-base: {value};
--line-height-base: {value};
--type-scale-ratio: {value};
```

### Spacing Tokens

```css
--space-unit: {base unit, e.g., 8px};
--space-xs: {value};
--space-sm: {value};
--space-md: {value};
--space-lg: {value};
--space-xl: {value};
```

### Motion Tokens

```css
--duration-fast: {value};
--duration-normal: {value};
--duration-slow: {value};
--easing-default: {value};
/* prefers-reduced-motion policy: {disable | shorten | alternative} */
```

### Elevation Tokens

```css
--shadow-sm: {value};
--shadow-md: {value};
--shadow-lg: {value};
```

## Responsive Strategy

- **Approach**: {mobile-first | desktop-first} — {rationale}
- **Breakpoints**:
  - sm: {value}
  - md: {value}
  - lg: {value}
  - xl: {value}

## Design Decisions
{Key design decisions from Phase 1 direction + Phase 2 specification with rationale}

## Unresolved Items
{Low-confidence claims, open questions, or items deferred for implementation. Omit section if none.}

## Minority Report
{Dissenting views from ratification, if any. Omit section if unanimous.}

## Discussion Artifacts
- Team: {comma-separated member names} (+ codex advisory)
- Phase 1: {hypothesis_count} hypotheses, {critique_count} critiques
- Phase 2: {hypothesis_count} hypotheses, {critique_count} critiques
- Ratification: Phase 1 Round {N} ({count}/{total}), Phase 2 Round {N} ({count}/{total})
```

Note: This is a design specification, not an implementation plan. To create executable code, use the `frontend-design` skill with this Design Spec as input context.

## Ratification Rules

| Voting Members | Majority Threshold |
|----------------|-------------------|
| 4 | 3 |
| 5 | 3 |
| codex | (advisory — no vote) |

- **Advisory members** (e.g., Codex) do NOT count toward majority threshold and cannot vote.
- **Max rounds**: 10 (configurable at board creation)
- **Vote format**: `RATIFY: accept — {reason}` or `RATIFY: push-back — {concerns}` via SendMessage
- **Exhaustion**: If max rounds reached with no majority, leader writes "best available conclusion" with explicit uncertainty markers
- **Abstention**: Not permitted. Every voting member must vote each round.
- **Vote supersession**: A member's vote in round N supersedes prior rounds.
- **Both phases use ratification.** Phase 1 ratifies the design direction; Phase 2 ratifies the design specification.

## Conflict Prevention Rules

| # | Rule | Rationale |
|---|------|-----------|
| 1 | Each teammate edits only their own `### {name}` subsection in WHITEBOARD.md | Prevents Edit tool match failures from concurrent writes |
| 2 | SYNTHESIS.md is leader-only (teammates read, never write) | Single writer eliminates conflicts |
| 3 | Append-only writes (no deletion/modification of existing entries) | Prevents overwrites from stale reads |
| 4 | Ratification votes via SendMessage, not file writes | Eliminates race conditions on vote tallying |
| 5 | Phase transitions are leader-controlled via broadcast | Clear boundaries prevent out-of-order writes |
| 6 | `## Audit` section is leader-only | Single writer; Codex results managed by leader |
| 7 | Revisions are append-only in member's own subsection | Maintains append-only invariant |
| 8 | `### codex` subsection is leader-only (leader writes on Codex's behalf) | Same pattern as Rule #6 |
| 9 | Phase 1 files are read-only during Phase 2 | Prevents retroactive modification of settled design direction |

## Codex Advisory Member

### Prerequisites

- `codex` CLI must be installed (`npm i -g @openai/codex`).
- If unavailable, skip all Codex advisory steps with `(Codex advisory skipped: CLI not found)` in `### codex` subsections.

### Workflow

1. Leader waits for all voting members to report completion.
2. Leader reads WHITEBOARD.md to gather context.
3. Leader constructs the appropriate Codex prompt (see templates below).
4. Leader runs `codex exec` via temp file + stdin.
5. Leader writes Codex output **verbatim** to `### codex` subsection.

### Hypothesize Prompt Template

```
You are an advisory member in a structured frontend design discussion.
The team is working on: {design topic}
Current phase: {Phase 1: Design Direction | Phase 2: Design Specification}

The team's framing and existing hypotheses are below. Generate 2-3 novel hypotheses that the team has NOT already proposed. Each hypothesis must be concrete and include axis= tags.

{Phase 2 addition: Each hypothesis MUST include CSS Custom Properties token definitions in a code block.}

Use this exact ID format: [H-{phase}-X-001], [H-{phase}-X-002], etc.

Format each hypothesis as:
- [H-{phase}-X-NNN] **hypothesis** axis={tag}: {concrete claim}
  > Rationale: {why this is worth considering}

Existing content:
{framing + hypotheses from WHITEBOARD.md}
```

### Critique Prompt Template

```
You are an advisory member in a structured frontend design discussion.
The team is working on: {design topic}
Current phase: {Phase 1: Design Direction | Phase 2: Design Specification}

Review the hypotheses and existing critiques below. Write 2-4 critiques that fill gaps in the existing critique coverage. Reference design principles where applicable.

Use this exact ID format: [CR-{phase}-X-R{round}-001], etc.

Label each critique: **challenge**, **support**, **amend**, or **question**.

Format each critique as:
- [CR-{phase}-X-R{N}-NNN] **{label}** @codex refs=[{target ID}] axis={tag}: {critique text}

Existing content:
{hypotheses + critiques from WHITEBOARD.md}
```

### Audit Prompt Template (Phase 2 only)

```
Fact-check the following claims from a frontend design specification discussion. For each claim:
1. Verify accessibility claims against WCAG 2.1/2.2 AA standards
2. Check browser compatibility claims for CSS features
3. Verify performance impact claims (CLS, LCP)
4. Do NOT evaluate aesthetic quality, visual appeal, or design taste — mark these as Unverifiable
5. Skip opinions, value judgments, and forecasts — mark them as Unverifiable

Rate each claim: Verified / Partially accurate / Inaccurate / Unverifiable

Claims:
{hypotheses and critique claims from current round}
```

### Invocation Pattern

```bash
TMPFILE=$(mktemp)
cat <<'PROMPT_EOF' > "$TMPFILE"
<constructed_prompt>
PROMPT_EOF
cat "$TMPFILE" | codex exec
rm -f "$TMPFILE"
```

### Verbatim Copy Rule

Leader MUST copy Codex output verbatim into `### codex` subsection. Formatting adjustments (ID prefix corrections) are permitted; content changes are not.

### Error Handling

| Situation | Action |
|-----------|--------|
| `codex` CLI not found | Skip advisory step; write `(Codex advisory skipped: CLI not found)` |
| Empty output | Write `(Codex provided no additional content)` |
| Malformed IDs in output | Leader prepends correct ID prefix + quotes raw text in blockquote |
| Non-zero exit code | Write `(Codex advisory skipped: exit code {N})` and proceed |
| Timeout (>2 min) | Write `(Codex advisory skipped: timeout)` and proceed |

### Budget

Max 3 Codex CLI calls per round (hypothesize + critique + audit), 2-minute timeout per call. Set Bash tool `timeout: 180000` (3 minutes).

## Timeout Policy

| Situation | Action |
|-----------|--------|
| Member has not reported completion | Leader sends one reminder via SendMessage |
| After reminder, still no response | Leader proceeds with available results (partial round) |
| Missing ratification vote | Recorded as "not submitted"; threshold recalculated as ⌊voting_count/2⌋ + 1 |
