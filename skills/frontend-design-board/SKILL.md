---
name: frontend-design-board
description: >-
  Frontend design discussion via 2-phase structured team debate with visual mockup feedback loops.
  Phase 1 builds design direction consensus (tone, purpose, target user),
  Phase 2 specifies design tokens, responsive strategy, and motion policy.
  After each phase, presents visual mockups (moodboard / UI) via browser and loops on user feedback.
  Outputs a Design Spec mapped to frontend-design skill input format.
  Triggers: UIデザイン議論, デザイン方針を議論, UIの方向性, frontend design discussion, UI discussion, フロントエンドデザイン議論
---

# Frontend Design Board — 2-Phase Design Discussion via Team Debate

Produce a concrete Design Spec through structured 2-phase team debate with visual mockup feedback loops: Phase 1 (Design Direction) builds consensus on aesthetic direction, tone, and target user; Phase 2 (Design Specification) defines tokens, responsive strategy, and motion policy. After each phase, the leader presents visual mockups via the superpowers visual companion and collects user feedback — looping back to hypothesize until approved. Outputs a Design Spec that maps directly to the frontend-design skill's Design Thinking input format. Uses TeamCreate + SendMessage + AskUserQuestion + Visual Companion.

## When to Use

- The task requires discussing and deciding frontend design direction with multiple perspectives
- Keywords: "UIデザイン議論", "デザイン方針を議論", "UIの方向性", "frontend design discussion", "UI discussion", "フロントエンドデザイン議論"

## When NOT to Use

- Use `frontend-design` for immediate implementation without design discussion
- Use `design-board` for implementation design with technology selection (backend/architecture focus)
- Use `discussion-board` for open-ended exploration not specific to frontend design

## Scope Exclusions

The following are explicitly outside this skill's scope:

- **Component API design / Props design** — Use `frontend-design` skill after obtaining the Design Spec
- **State transition tables / copy CSV** — Responsibility of implementation skills
- **i18n / RTL locale support as mandatory gate** — May be mentioned in Phase 1 framing as context, but is NOT a required gate
- **Non-AI handoff pack** — Out of scope; the Design Spec is the sole output artifact

## Core Principles

1. **Design-direction-centric** — All activity targets producing an actionable Design Spec for frontend implementation.
2. **2-phase model** — Phase 1 (Design Direction) builds aesthetic consensus; Phase 2 (Design Specification) produces concrete tokens and strategies. Each phase has its own working directory with round-split WHITEBOARD files + SYNTHESIS.md in `docs/discussions/{discussion-id}/phase-{N}/`.
3. **Round-split WHITEBOARD model** — Base WHITEBOARD.md (topic + framing, read-only after framing) + per-round WHITEBOARD-R{N}.md + SYNTHESIS.md per phase. See board-engine REFERENCE.md for file model details.
4. **Principle-based critique** — Critiques must reference design principles (contrast, repetition, alignment, proximity, visual hierarchy, Gestalt), not subjective preferences. "I don't like it" is never valid; "this violates the alignment principle because..." is required.
5. **Staged concreteness** — Phase 1 uses linguistic descriptions (mood, direction, references); Phase 2 requires CSS Custom Properties token definitions. This prevents premature specificity from suppressing creative exploration.
6. **Axis tagging** — Every hypothesis and critique must include at least one `axis=` tag from: typography, color, layout, motion, accessibility, spatial-composition, spacing, elevation.

## Shared Debate Engine

**At setup, leader reads the lightweight setup reference:**
1. Use `Glob pattern="**/board-engine/SETUP.md"` to locate the file
2. Read the found file path (file model, round numbering, setup checklist)

**At framing kickoff, leader reads the full debate reference:**
1. Use `Glob pattern="**/board-engine/REFERENCE.md"` to locate the file
2. Read the found file path
3. If Glob returns no results, use fallback path: `../board-engine/REFERENCE.md` relative to this skill's base directory

**If either Read fails:** Proceed without the reference, but log warning in SYNTHESIS.md status line:
`> Warning: board-engine reference not found. Using inline rules only.`

SETUP.md provides: file model and round numbering. REFERENCE.md provides: full debate cycle, entry formats, and shared rules. Board-specific overrides below take precedence.

## Phase Model

```
setup → [Phase 1: framing → [Round N: hypothesize → critique → synthesize → ratify]] → user-review-1 (moodboard ⇄ Phase 1 hypothesize) → [Phase 2: framing → [Round N: hypothesize → critique → audit → revise (if needed) → synthesize → ratify]] → user-review-2 (UI mockup ⇄ Phase 2 hypothesize) → concluded
```

**Round numbering:** Round numbers are **monotonically increasing** across the entire discussion, never reset. Phase 1 feedback cycle 1 = R1, feedback cycle 2 = R2, Phase 2 starts at R3, etc. This prevents file naming collisions across feedback cycles.

**Max Rounds scope:** The 10-round max applies per-phase, not globally. Since round numbers are monotonically increasing, track the count of rounds within each phase separately. Example: Phase 1 uses R1-R3 (3 rounds), Phase 2 can use R4-R13 (up to 10 rounds).

### Phase 1 — Design Direction (4 steps per round)

| Step | Who | What |
|------|-----|------|
| framing | All members | Document design context: purpose, aesthetic instincts, target user, constraints, unknowns |
| hypothesize | All members | Propose design directions: tone, mood, aesthetic stance, reference points |
| critique | All members | Challenge/support/amend/question directions using design principles |
| synthesize | Leader only | Read current round WHITEBOARD-R{N}.md + prior SYNTHESIS.md, write Evidence Map + Direction Conclusion |
| ratify | All voting members | Vote accept or push-back on design direction. Simple majority ratifies |

**Phase 1 has NO audit or revise.** Aesthetic hypotheses are not fact-checkable. The debate cycle for Phase 1 is: hypothesize → critique → synthesize → ratify.

### User Review 1 — Visual Moodboard (after Phase 1)

Leader presents Phase 1 direction as a visual moodboard via the visual companion server:
- Include: color palette, typography samples, tone/mood CSS visualization, comparison cards if multiple directions remain
- User choices: "Proceed to Phase 2" or "Provide feedback" (via AskUserQuestion in terminal)
- If user provides feedback: Leader records feedback in phase-1/SYNTHESIS.md `## User Feedback History`, increments Feedback Cycle, re-enters Phase 1 hypothesize with feedback as new constraint. Loop until approved.
- No skip option — user confirmation is mandatory

### Phase 2 — Design Specification (6 steps + conditional revise per round)

| Step | Who | What |
|------|-----|------|
| framing | All members | Document specification constraints, scope, acceptance criteria (informed by Phase 1 direction) |
| hypothesize | All members | Propose concrete design specifications: token definitions (required), responsive strategy, motion policy |
| critique | All members | Challenge/support/amend/question specifications with design principle references and axis tags |
| audit | Leader only | Run Codex CLI to fact-check: a11y (WCAG 2.1/2.2 AA), browser compat, performance (CLS/LCP). Aesthetic judgments excluded |
| revise | All members (conditional) | Append corrections if audit found inaccuracies (skipped if all clean) |
| synthesize | Leader only | Read current round WHITEBOARD-R{N}.md + prior SYNTHESIS.md, write Evidence Map + Draft Design Spec |
| ratify | All voting members | Vote accept or push-back via SendMessage. Simple majority ratifies |

### User Review 2 — Visual UI Mockup (after Phase 2)

Leader presents Phase 2 specification as a UI mockup via the visual companion server:
- Include: design tokens applied to components, responsive demo, theme switching (light/dark/high-contrast), motion preview
- User choices: "Approve specification" or "Provide feedback" (via AskUserQuestion in terminal)
- If user provides feedback (Phase 2 scope): Leader records feedback in phase-2/SYNTHESIS.md `## User Feedback History`, increments Feedback Cycle, re-enters Phase 2 hypothesize. Loop until approved.
- If user feedback requires Phase 1 direction change: Leader presents escalation confirmation to user, and if confirmed, suspends conflict rule #12, discards Phase 2 files, re-enters Phase 1 hypothesize with feedback as constraint.
- No skip option — user confirmation is mandatory

## Board-Specific Entry Formats

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

`-cx` members use their normal member's initial + `X`. Example: backend → `B`, backend-cx → `BX`. Entry IDs: `[H-1-BX-001]`.

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

Each critique must include: label (`**challenge**`/`**support**`/`**amend**`/`**question**`), `refs=[...]`, `@{member}`, and `axis={tag}`.

**Recommended critique body structure** (Feldman model — recommended, not required):
```markdown
#### Round 1
- [CR-1-A-R1-001] **challenge** @visual-designer refs=[H-1-V-001] axis=typography:
  記述: Playfair Display の x-height は低く、16px以下でのボディテキスト可読性が低下する
  分析: 長文閲覧用途ではx-height比0.48以上が推奨される（Playfair は約0.44）
  解釈: ターゲットユーザーの「長時間閲覧」要件と矛盾するリスク
  判断: ディスプレイ用途に限定し、ボディにはx-heightの高いセリフ体（Literata, Charter等）を提案
```

The Feldman structure (記述→分析→解釈→判断) is a **recommended template** to improve critique quality. It is NOT required — members may write free-form critiques with the standard label + refs + axis format. The 4-label system (challenge/support/amend/question) is the only **required** structure.

### Phase 1 Direction Conclusion (Leader only)

```markdown
## Direction Conclusion
**Design Direction:** {selected tone/mood/aesthetic with rationale}
**Purpose:** {what problem this interface solves}
**Target User:** {who the design serves}
**Rejected Directions:** {alternatives with reasons}
**Trade-offs:** {key trade-offs accepted}
**Open questions for Phase 2:** {items to resolve during specification}
```

### Phase 2 Draft Design Spec (Leader only)

```markdown
## Draft Design Spec — Round {N}
{Synthesized specification citing entry IDs. Mark areas of uncertainty.}
**Key claims:** 1, 2, 3 (from Evidence Map)
**Unresolved:** {low-confidence or unaddressed claims}
```

### Phase 2 Audit (Leader only)

**Scope is strictly limited to 3 axes — aesthetic judgments are explicitly excluded:**

1. **Accessibility** — WCAG 2.1/2.2 AA compliance (contrast ratio 4.5:1, target size 24x24px minimum per SC 2.5.8)
2. **Browser compatibility** — CSS feature support status across major browsers
3. **Performance** — CLS ≤ 0.1, LCP ≤ 2.5s impact assessment

**Explicit exclusion instruction in Codex prompt:** "Do NOT evaluate aesthetic quality, visual appeal, or design taste. Only verify factual claims about accessibility standards, browser support, and performance metrics."

All other entry formats (Evidence Map, Round Context Packet, Ratification History, Minority Report, Completion Report, Audit Table + Verdict Rubric, Revision) — see board-engine REFERENCE.md.

### ID Summary

| Type | Format | Phase |
|------|--------|-------|
| Framing | (no ID — structured fields) | both phases |
| Hypothesis | `[H-{phase}-{initial}-{seq}]` | both phases |
| Critique | `[CR-{phase}-{initial}-R{round}-{seq}]` | both phases |
| Audit | (no ID — table format) | Phase 2 only |
| Revision | `[{original-ID}] **revised**` | Phase 2 only |

## Board-Specific Phase Notes

For the standard debate cycle phases (hypothesize, critique, audit, revise, synthesize, ratify), see board-engine REFERENCE.md. Board-specific additions only below.

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
  - `role_count`: `"3-4"`
  - `constraints`: `["a11y non-negotiable axis"]`
  - `domain_hints`: extracted from user answers + design-domain seed axes (美的方向性, ユーザビリティ vs 表現性, パフォーマンス vs リッチネス, ブランド一貫性 vs 革新性)
- After team-composer completes (Handoff Contract received):
  - Create `docs/discussions/{discussion-id}/phase-1/` and `phase-2/` directories.
  - Read `skills/frontend-design-board/references/whiteboard-templates.md` and `skills/frontend-design-board/references/synthesis-templates.md`.
  - In each phase directory, create base WHITEBOARD.md + SYNTHESIS.md using template reference files (see Template References section).
  - Do NOT create per-round WHITEBOARD files yet — created at each round's hypothesize phase.
  - Ensure `docs/discussions/` is in `.gitignore`.
  - Spawn all members with frontend-design-board-specific prompts:
    - Normal members: discipline + expected contribution as briefing.
    - `-cx` members: same briefing + codex exec exploration template (see team-composer skill for template) + `model: "sonnet"`.
  - **Lean role briefing policy:** For recurring broadcasts (hypothesize/critique/revise/re-entry), restate only discipline + expected contribution. This minimizes token overhead while preserving role separation.

### Phase 1: framing

- **Leader reads board-engine REFERENCE.md** at framing kickoff (if not already read).
- Normal members use full base WHITEBOARD.md Read (file is small, ~100 lines at this stage).
- -cx members use Codex framing template:
  ```
  Read the base WHITEBOARD at {absolute-path}/phase-1/WHITEBOARD.md.

  From a {role-description} perspective, provide Phase 1 framing:
  - Purpose: what problem this interface solves and who uses it
  - Aesthetic Instinct: initial direction about tone/mood
  - Target User: who the design serves
  - Constraints: technical requirements relevant to your expertise
  - Unknowns: open questions from your discipline

  Analyze the codebase for relevant constraints. Cite file:line.
  Output: structured framing fields only, max 250 tokens.
  ```
- After framing completes, base WHITEBOARD.md becomes **read-only** for the remainder of Phase 1.
- Leader combines completion confirmation + hypothesize kickoff in 1 broadcast.
- Framing should focus on design context: purpose, aesthetic instincts, target user, constraints.

### Phase 1: hypothesize

- Leader creates WHITEBOARD-R{N}.md in phase-1/ at the start of each round.
- **Independent generation (Round 1, Feedback Cycle 1 only):** Members generate hypotheses WITHOUT reading other members' entries. Each member receives only the topic and their own role briefing (discipline + expected contribution). This eliminates first-mover anchoring. Subsequent feedback cycles allow reading existing entries.
- Each member aims for **1-2 hypotheses** about design direction. Hypotheses are linguistic (mood, tone, references). No code snippets in Phase 1.
- Each hypothesis MUST include at least one `axis=` tag.
- **Feedback re-entry:** When re-entering hypothesize from user-review-1 feedback, the broadcast includes user feedback as a new constraint. Members write new hypotheses in a new WHITEBOARD-R{N}.md file (round number continues monotonically). Previous round files remain read-only.

### Phase 1: critique

- ID-index protocol from board-engine REFERENCE.md applies. Leader builds ID-index and assigns hypotheses.
- Each member writes at most **1 critique per round**, prioritizing highest-risk disagreements.
- **Feldman template encouraged** (記述→分析→解釈→判断) but not enforced.

### Phase 1: synthesize

- Leader reads WHITEBOARD-R{N}.md in full (current round) + previous Evidence Map and Direction Conclusion from SYNTHESIS.md.
- Writes updated Evidence Map + Direction Conclusion in phase-1/SYNTHESIS.md.
- Direction Conclusion must clearly state: design direction (tone/mood/aesthetic), purpose, target user, rejected alternatives, key trade-offs, and open questions for Phase 2.

### Phase 1: ratify

- If not ratified: incorporate push-back, leader creates WHITEBOARD-R{N+1}.md, start next hypothesize round (within Phase 1).

### user-review-1

- Leader starts visual companion server (if not already running): `scripts/start-server.sh --project-dir {project-root}` from superpowers plugin scripts directory. If server fails, fall back to text-based review (see Visual Companion section).
- Leader reads phase-1/SYNTHESIS.md Direction Conclusion.
- Leader generates moodboard HTML content fragment and writes to `screen_dir` (see Visual Companion section).
- Presents to user via AskUserQuestion:
  ```
  Phase 1 (Design Direction) の結果をモックアップにしました。
  ブラウザで確認してください: {url}

  **Design Direction:**
  {selected tone/mood/aesthetic with brief rationale}

  **Purpose:** {what this interface solves}
  **Target User:** {who it serves}

  **Key trade-offs:**
  {bullet list of accepted trade-offs}

  **Rejected alternatives:**
  {bullet list with reasons}

  Options:
  1. この方向で Phase 2 に進む
  2. フィードバックを伝える（Phase 1 を再議論します）
  ```
- On approval: push waiting screen to `screen_dir`, proceed to Phase 2 framing.
- On feedback:
  1. Record in phase-1/SYNTHESIS.md `## User Feedback History` → `### Feedback Cycle {N}`:
     ```markdown
     ### Feedback Cycle {N}
     - **Feedback:** {user's feedback content}
     - **Action:** Re-entered hypothesize with feedback as constraint
     ```
  2. Increment `> Feedback Cycle:` in SYNTHESIS.md header.
  3. Broadcast to members: restate discipline + expected contribution + "ユーザーからのフィードバック: {content}。これを新たな制約として hypothesize を再開してください"
  4. Re-enter Phase 1 hypothesize (new WHITEBOARD-R{N}.md, round number continues).
  5. After ratify succeeds: generate updated moodboard, present user-review-1 again.
  6. After approval, append outcome:
     ```markdown
     ### Feedback Cycle {N} Outcome
     - **Result:** {summary of how feedback was addressed}
     ```

### Phase 2: framing

- **Context injection (Push-based):** Leader reads phase-1/SYNTHESIS.md, extracts Direction Conclusion, and includes it in the framing broadcast. Members do NOT read phase-1/ files directly.
- If user provided feedback during user-review-1, include the final approved direction and any feedback that shaped it as additional context.
- Normal members use full base WHITEBOARD.md Read.
- -cx members use Codex framing template:
  ```
  Read the base WHITEBOARD at {absolute-path}/phase-2/WHITEBOARD.md.

  From a {role-description} perspective, provide Phase 2 framing:
  - Scope: what this specification covers
  - Direction Constraints: from Phase 1 conclusions (included in WHITEBOARD)
  - Acceptance Criteria: what makes a good specification
  - Unknowns: open questions about specification details

  Analyze the codebase for relevant constraints. Cite file:line.
  Output: structured framing fields only, max 250 tokens.
  ```
- Framing should focus on specification scope, acceptance criteria, and which token categories to define.
- After framing completes, base WHITEBOARD.md becomes **read-only** for the remainder of Phase 2.

### Phase 2: hypothesize

- Leader creates WHITEBOARD-R{N}.md in phase-2/ at the start of each round (round number continues from Phase 1).
- Each member aims for 1-2 hypotheses per round, prioritizing coverage over quantity.
- **Token definition block is REQUIRED** in Phase 2 hypotheses. Each hypothesis must include at least one CSS Custom Properties code block defining design tokens. Hypotheses without token definitions are returned for revision.
- **Theme matrix:** Token hypotheses that define color tokens MUST include light/dark/high-contrast variants. Motion token hypotheses MUST address `prefers-reduced-motion` handling policy (disable, shorten, or provide alternatives — WCAG does not mandate 0ms specifically).
- **Feedback re-entry:** When re-entering hypothesize from user-review-2 feedback, the broadcast includes user feedback as a new constraint. Members write new hypotheses in a new WHITEBOARD-R{N}.md file.

### Phase 2: critique

- Same rules as Phase 1 critique, plus: critiques of token definitions SHOULD include quantitative checks (contrast ratio, spacing ratio, type scale ratio) when applicable.
- Each member writes at most 2 critiques per round, prioritizing highest-risk disagreements.

### Phase 2: audit

- **Scope is strictly limited to 3 axes. Aesthetic judgments are EXCLUDED:**
  1. **Accessibility**: WCAG 2.1/2.2 AA (contrast ratio >= 4.5:1 for normal text per SC 1.4.3, target size >= 24x24px per SC 2.5.8)
  2. **Browser compatibility**: CSS feature support (e.g., oklch() color space, container queries)
  3. **Performance**: CLS <= 0.1, LCP <= 2.5s impact
- Audit results written to WHITEBOARD-R{N}.md `## Audit` section.

### Phase 2: synthesize

- Leader reads WHITEBOARD-R{N}.md in full (current round) + previous Evidence Map and Draft Design Spec from SYNTHESIS.md.
- Writes updated Evidence Map + Draft Design Spec in phase-2/SYNTHESIS.md.
- Draft Design Spec must include the Design Thinking Mapping (5-axis) and token definition tables.

### Phase 2: ratify

- If not ratified: next round starts at hypothesize (leader creates WHITEBOARD-R{N+1}.md, full cycle including audit).

### user-review-2

- Leader reads phase-2/SYNTHESIS.md Draft Design Spec.
- Leader generates UI mockup HTML content fragment and writes to `screen_dir` (see Visual Companion section).
- Presents to user via AskUserQuestion:
  ```
  Phase 2 (Design Specification) の結果をモックアップにしました。
  ブラウザで確認してください: {url}

  **Design Spec 概要:** {トークン定義・レスポンシブ戦略の要約}

  Options:
  1. この仕様で確定する
  2. フィードバックを伝える（Phase 2 を再議論します）
  ```
- On approval: stop visual companion server (`scripts/stop-server.sh $SESSION_DIR`), proceed to concluded.
- On feedback:
  1. Leader assesses scope: is this Phase 2 internal or does it require Phase 1 direction change?
  2. **If Phase 2 scope:** Same feedback recording and re-entry flow as user-review-1 but for Phase 2 (record in phase-2/SYNTHESIS.md, increment Feedback Cycle, re-enter Phase 2 hypothesize with new WHITEBOARD-R{N}.md, loop).
  3. **If Phase 1 escalation needed:** Present escalation confirmation via AskUserQuestion:
     ```
     このフィードバックは Phase 1 のデザイン方向性の変更を必要とします。
     Phase 1 の hypothesize に戻って再議論しますか？

     1. はい、Phase 1 から再議論する
     2. いいえ、Phase 2 の範囲内で対応する
     ```
     - If user confirms Phase 1 escalation: suspend conflict rule #12, delete phase-2/ directory (new Phase 2 will be created after Phase 1 re-approval), record escalation in phase-1/SYNTHESIS.md User Feedback History, re-enter Phase 1 hypothesize with feedback as constraint.
     - If user chooses Phase 2 scope: proceed with Phase 2 internal feedback flow.

### concluded

- Leader writes `## Final Design Spec` in phase-2/SYNTHESIS.md.
- Read `skills/frontend-design-board/references/design-spec-template.md`.
- Leader generates the Design Spec file at `docs/plans/YYYY-MM-DD-{topic}-design-spec.md` (see template reference files).
- Content is derived from both phase-1/SYNTHESIS.md (design direction) and phase-2/SYNTHESIS.md (specifications).
- Verify the file was created successfully.
- Delete `docs/discussions/{discussion-id}/` directory after successful export.

## Board-Specific Conflict Rules

Rules 1-10 from board-engine REFERENCE.md apply. Additional board-specific rules:

| # | Rule | Rationale |
|---|------|-----------|
| 12 | Phase 1 files are read-only during Phase 2 (suspended during Phase 2 → Phase 1 escalation) | Prevents retroactive modification of settled design direction. Suspension requires explicit user confirmation via escalation flow in user-review-2. When suspended: Phase 2 files are discarded, Phase 1 re-enters hypothesize, rule reinstates when new Phase 2 begins. |

## Visual Companion

### Overview

Uses the superpowers brainstorming visual companion to present mockups in the user's browser during user-review phases. The visual companion is an external dependency from the superpowers plugin — its `scripts/` directory must be resolved via the superpowers plugin installation path.

### Server Lifecycle

- **Start:** At user-review-1 start, leader runs `scripts/start-server.sh --project-dir {project-root}` from the superpowers plugin scripts directory. Save `screen_dir` and `state_dir` from the response.
- **Maintain:** During Phase 2 discussion, push a waiting screen to `screen_dir`:
  ```html
  <!-- filename: waiting.html -->
  <div style="display:flex;align-items:center;justify-content:center;min-height:60vh">
    <p class="subtitle">Phase 2 議論中...</p>
  </div>
  ```
- **Stop:** After user-review-2 approval, leader runs `scripts/stop-server.sh $SESSION_DIR`.

### Fallback

If the visual companion server fails to start (superpowers plugin not installed, port conflict, no browser available):
1. Log warning in SYNTHESIS.md: `(Visual companion unavailable: {reason}. Falling back to text-based review.)`
2. Proceed with text-based AskUserQuestion only (same content as mockup, but described in text)
3. All other feedback loop mechanics remain unchanged

### Mockup Generation Rules

- **Responsibility:** Leader-only. Members do not generate mockups.
- **Source:** SYNTHESIS.md content (Direction Conclusion for Phase 1, Draft Design Spec for Phase 2).
- **Format:** Content fragments only (no full HTML documents). The visual companion frame template provides CSS/JS infrastructure.
- **Google Fonts:** system-ui fallback is required for all font declarations.
- **Scope:** Leader uses discretion to produce minimum viable mockup that conveys the design. Phase 2 mockups need not demonstrate every token — focus on what helps the user evaluate the specification.

### Phase 1 Mockup Content (Moodboard)

- Color palette visualization (proposed color directions)
- Typography samples (Google Fonts loaded with system-ui fallback)
- Tone/mood CSS-based atmosphere
- Multiple directions shown as cards layout for comparison (if applicable)
- File naming: `moodboard.html`, `moodboard-v2.html`, ...

### Phase 2 Mockup Content (UI Mockup)

- Design tokens applied to component samples
- Responsive breakpoint switching demo
- Light/dark/high-contrast theme switching
- Motion token animation preview (with `prefers-reduced-motion` policy applied)
- File naming: `ui-mockup.html`, `ui-mockup-v2.html`, ...

### Approval Contract

- **Primary:** AskUserQuestion text response in terminal determines approval/feedback.
- **Secondary:** Browser click events (`state_dir/events`) are supplementary information for leader context only.
- Approval/feedback decision is always via terminal text, never via browser clicks alone.

---

# Template References

To reduce static token overhead in this SKILL.md, templates are externalized.

- `skills/frontend-design-board/references/whiteboard-templates.md`
  - Phase 1/2 base WHITEBOARD templates
  - Use during setup when creating `phase-1/WHITEBOARD.md` and `phase-2/WHITEBOARD.md`
- `skills/frontend-design-board/references/synthesis-templates.md`
  - Phase 1/2 SYNTHESIS templates
  - Use during setup when creating `phase-1/SYNTHESIS.md` and `phase-2/SYNTHESIS.md`
- `skills/frontend-design-board/references/design-spec-template.md`
  - Final Design Spec export template
  - Use during concluded when writing `docs/plans/YYYY-MM-DD-{topic}-design-spec.md`

Per-round WHITEBOARD-R{N}.md files continue to use the template from `board-engine/REFERENCE.md` (Phase 1 round files omit `## Audit`).
