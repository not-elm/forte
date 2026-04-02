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

- **Component API design / Props design** → Use `frontend-design` skill after obtaining the Design Spec
- **State transition tables / copy CSV** → Responsibility of implementation skills
- **i18n / RTL locale support as mandatory gate** → May be mentioned in Phase 1 framing as context, but is NOT a required gate
- **Non-AI handoff pack** → Out of scope; the Design Spec is the sole output artifact

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
setup/explore → setup/confirm → [Phase 1: framing → hypothesize → critique → synthesize → ratify] → user-review-1 (moodboard mockup ⇄ Phase 1 hypothesize) → [Phase 2: framing → [Round N: hypothesize → critique → audit → revise (if needed) → synthesize → ratify] ] → user-review-2 (UI mockup ⇄ Phase 2 hypothesize) → concluded
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

### User Review 1 — Visual Moodboard (after Phase 1)

Leader presents Phase 1 direction as a visual moodboard via the visual companion server:
- Include: color palette, typography samples, tone/mood CSS visualization, comparison cards if multiple directions remain
- User choices: "Proceed to Phase 2" or "Provide feedback" (via AskUserQuestion in terminal)
- If user provides feedback: Leader records feedback in phase-1/SYNTHESIS.md `## User Feedback History`, resets ratification round counter, re-enters Phase 1 hypothesize with feedback as new constraint. Loop until approved.
- No skip option — user confirmation is mandatory

### User Review 2 — Visual UI Mockup (after Phase 2)

Leader presents Phase 2 specification as a UI mockup via the visual companion server:
- Include: design tokens applied to components, responsive demo, theme switching (light/dark/high-contrast), motion preview
- User choices: "Approve specification" or "Provide feedback" (via AskUserQuestion in terminal)
- If user provides feedback (Phase 2 scope): Leader records feedback in phase-2/SYNTHESIS.md `## User Feedback History`, resets ratification round counter, re-enters Phase 2 hypothesize. Loop until approved.
- If user feedback requires Phase 1 direction change: Leader presents escalation confirmation to user, and if confirmed, suspends conflict rule #9, discards Phase 2 files, re-enters Phase 1 hypothesize with feedback as constraint.
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

### User Review 1 — Visual Moodboard

| Step | Leader Action | Output | Next Trigger |
|------|---------------|--------|--------------|
| user-review-1 | Start visual companion server; generate moodboard HTML from Direction Conclusion; present via AskUserQuestion with browser URL | User approval or feedback | User responds |
| (feedback loop) | Record feedback in User Feedback History; reset Round to 0; increment Feedback Cycle; broadcast feedback as constraint; re-enter Phase 1 hypothesize | Updated hypotheses → critique → synthesize → ratify → new moodboard | Ratify succeeds → present user-review-1 again |

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

### User Review 2 — Visual UI Mockup

| Step | Leader Action | Output | Next Trigger |
|------|---------------|--------|--------------|
| user-review-2 | Generate UI mockup HTML from Draft Design Spec; present via AskUserQuestion with browser URL | User approval or feedback | User responds |
| (feedback loop — Phase 2 scope) | Record feedback in User Feedback History; reset Round to 0; increment Feedback Cycle; broadcast feedback as constraint; re-enter Phase 2 hypothesize | Updated hypotheses → critique → audit → revise → synthesize → ratify → new UI mockup | Ratify succeeds → present user-review-2 again |
| (feedback loop — Phase 1 escalation) | Present escalation confirmation to user; if confirmed: suspend rule #9, discard Phase 2 files, re-enter Phase 1 hypothesize with feedback | Phase 1 re-discussion → user-review-1 → new Phase 2 | Phase 1 approved → create new Phase 2 |

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
- **Feedback re-entry:** When re-entering hypothesize from user-review-1 feedback, the broadcast includes user feedback as a new constraint. Members add new hypotheses addressing the feedback. Previous WHITEBOARD.md entries remain (append-only). The `Independent generation` rule applies only to Feedback Cycle 1, Round 1 — subsequent cycles allow reading existing entries.

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

### user-review-1

- Leader starts visual companion server (if not already running): `scripts/start-server.sh --project-dir {project-root}` from superpowers plugin scripts directory. If server fails, fall back to text-based review (see Visual Companion → Fallback).
- Leader reads phase-1/SYNTHESIS.md Direction Conclusion.
- Leader generates moodboard HTML content fragment and writes to `screen_dir` (see Visual Companion → Phase 1 Mockup Content).
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
  2. Reset `> Round:` to 0 in SYNTHESIS.md header; increment `> Feedback Cycle:`.
  3. Broadcast to members: restate 3-layer roles + "ユーザーからのフィードバック: {content}。これを新たな制約として hypothesize を再開してください"
  4. Re-enter Phase 1 hypothesize.
  5. After ratify succeeds: generate updated moodboard, present user-review-1 again.
  6. After ratify succeeds and new moodboard presented, append outcome:
     ```markdown
     ### Feedback Cycle {N} Outcome
     - **Result:** {summary of how feedback was addressed}
     ```

### user-review-2

- Leader reads phase-2/SYNTHESIS.md Draft Design Spec.
- Leader generates UI mockup HTML content fragment and writes to `screen_dir` (see Visual Companion → Phase 2 Mockup Content).
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
  2. **If Phase 2 scope:** Same feedback recording and re-entry flow as user-review-1 but for Phase 2 (record in phase-2/SYNTHESIS.md, reset Round, re-enter Phase 2 hypothesize, loop).
  3. **If Phase 1 escalation needed:** Present escalation confirmation via AskUserQuestion:
     ```
     このフィードバックは Phase 1 のデザイン方向性の変更を必要とします。
     Phase 1 の hypothesize に戻って再議論しますか？

     1. はい、Phase 1 から再議論する
     2. いいえ、Phase 2 の範囲内で対応する
     ```
     - If user confirms Phase 1 escalation: suspend conflict rule #9, delete phase-2/ directory (new Phase 2 will be created after Phase 1 re-approval), record escalation in phase-1/SYNTHESIS.md User Feedback History, re-enter Phase 1 hypothesize with feedback as constraint.
     - If user chooses Phase 2 scope: proceed with Phase 2 internal feedback flow.

### Phase 2: framing

- **Context injection (Push-based):** Leader reads phase-1/SYNTHESIS.md, extracts Direction Conclusion, and includes it in the framing broadcast. Members do NOT read phase-1/ files directly.
- If user provided feedback during user-review-1 (recorded in User Feedback History), include the final approved direction and any feedback that shaped it as additional context.
- Framing should focus on specification scope, acceptance criteria, and which token categories to define.

### Phase 2: hypothesize

- Members read all Phase 2 framings via full WHITEBOARD.md Read.
- **Token definition block is REQUIRED** in Phase 2 hypotheses. Each hypothesis must include at least one CSS Custom Properties code block defining design tokens. Hypotheses without token definitions are returned for revision.
- **Theme matrix:** Token hypotheses that define color tokens MUST include light/dark/high-contrast variants. Motion token hypotheses MUST address `prefers-reduced-motion` handling policy (disable, shorten, or provide alternatives — WCAG does not mandate 0ms specifically).
- Each hypothesis MUST include at least one `axis=` tag.
- Report completion using the completion report format.
- **Codex advisory step:** Same pattern as Phase 1.
- **Feedback re-entry:** When re-entering hypothesize from user-review-2 feedback, same rules as Phase 1 feedback re-entry. The broadcast includes user feedback as a new constraint. Members add new hypotheses with required token definition blocks. Previous entries remain (append-only).

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
> Round: 0
> Max Rounds: 10
> Feedback Cycle: 1

## Evidence Map
## Direction Conclusion
## Ratification History
## Minority Report
## User Feedback History
```

**Phase 2:**
```markdown
# SYNTHESIS — {discussion-id} / Phase 2: Design Specification
> Status: setup
> Round: 0
> Max Rounds: 10
> Feedback Cycle: 1

## Evidence Map
## Draft Design Spec
## Ratification History
## Minority Report
## User Feedback History
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
| 9 | Phase 1 files are read-only during Phase 2 (suspended during Phase 2 → Phase 1 escalation) | Prevents retroactive modification of settled design direction. Suspension requires explicit user confirmation via escalation flow in user-review-2. When suspended: Phase 2 files are discarded, Phase 1 re-enters hypothesize, rule reinstates when new Phase 2 begins. |
| 10 | Ratification round counter resets on user feedback re-entry; feedback cycle counter is separate and unbounded | Distinguishes internal loops (ratify failure → critique) from external loops (user feedback → hypothesize). Max Rounds (10) applies per feedback cycle. |

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
