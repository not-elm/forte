# team-composer Skill Design Spec

## Overview

`forte:team-composer` は、board系スキル（discussion-board, design-board, frontend-design-board, investigation-board）で重複しているチーム編成ロジックを共通化するスキル。トピック分析 → expertise map → ロール生成 → ユーザー承認 → TeamCreate を一貫して担当し、各boardはspawn promptのみを提供する。

## Motivation

4つのboard系スキルが独立してロール生成・ユーザー承認・TeamCreateを実装しており、ロジックの重複とドリフト（差分の蓄積）が発生している。共通スキルとして切り出すことで、メンテナンスコストを削減し、チーム編成の品質を統一する。

## Scope

### In Scope

- トピック分析とexpertise map生成
- ドメインからのロール生成（3-6ロール）
- 常時ダブリング: 各ロールに通常メンバー + `-cx`メンバー（codex execで別視点獲得）
- ユーザー承認フロー
- TeamCreate実行
- ハンドオフ契約（boardに返す情報の定義）

### Out of Scope

- メンバーのspawn（board固有のpromptが必要なためboardが担当）
- ラウンドフロー制御（将来の共通化候補だが本スキルの対象外）
- code-review-board（固定パースペクティブのため対象外）

## Skill Interface

### Input

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `topic` | Yes | — | 議論テーマ / 設計課題 / バグ説明 |
| `team_name` | Yes | — | TeamCreateに渡すkebab-case ID |
| `role_count` | No | `"3-6"` | ロール数の範囲 |
| `domain_hints` | No | — | 含めたいドメインのヒント (e.g., `"security, performance"`) |
| `constraints` | No | — | board固有の制約リスト。自然言語で記述し、ドメイン包含/除外ルールとして解釈される (e.g., `["a11y non-negotiable axis"]` → a11yドメインを必ず含める) |

### Output (Handoff Contract)

team-composer完了時、以下の情報が会話コンテキストに存在する:

| Field | Description |
|-------|-------------|
| `team_name` | TeamCreateに使用したチーム名 |
| `roles` | ロール一覧（名前 + discipline説明） |
| `members` | メンバー一覧（名前、ロール、タイプ: normal/cx） |
| `initial_map` | メンバー名 → エントリID initial のマッピング |

boardスキルはこの情報を使ってメンバーをspawnする。

## Member Composition Rules

### Doubling Rule

各ロールに常に2名をアサインする:

- **通常メンバー** (`{role-name}`): 標準の議論参加
- **-cxメンバー** (`{role-name}-cx`): `codex exec`でトピックを事前調査し、その結果を踏まえて別視点から議論に参加

| Role Count | Total Members | Example |
|------------|--------------|---------|
| 3 | 6 | 3 roles × 2 |
| 4 | 8 | 4 roles × 2 |
| 5 | 10 | 5 roles × 2 |
| 6 | 12 | 6 roles × 2 |

### Entry ID Initial Rule

- 通常メンバー: 名前の先頭1文字（大文字）。例: `backend` → `B`
- `-cx`メンバー: 通常のinitial + `X`。例: `backend-cx` → `BX`
- 例: `[H-B-001]` = backend通常、`[H-BX-001]` = backend-cx
- 通常メンバー間のinitial衝突回避は従来通り（衝突時は先頭2文字にフォールバック）
- 2文字フォールバック時: `-cx`メンバーも同様に2文字 + `X`。例: `backend-api` → `BA`、`backend-api-cx` → `BAX`

### Voting

- 全メンバー（通常・-cx）が投票権を持つ
- majority計算は全メンバー数ベース: ⌊N/2⌋ + 1

### Codex Advisory Replacement

既存boardのCodex advisory（非投票、fixed initial `X`、`### codex` subsection）は廃止。`-cx`メンバーが投票権ありの正規メンバーとしてCodexの視点を提供する。

### Audit Exclusion

Auditロールはチームメンバーに含めない。Auditはboardのラウンドフロー内でリーダーが実行する。

## Workflow

### Phase 1: Expertise Map Generation

1. `topic`と`domain_hints`を分析
2. `constraints`があれば制約として反映（例: a11y non-negotiable axis → a11yドメインを必ず含める）
3. `role_count`範囲内で関連する知識ドメインを特定
4. 各ドメインに対してロール名を割り当て
   - ロール名はkebab-case
   - 通常メンバー間のinitialが一意になるよう調整

### Phase 2: User Approval

1. ロール一覧を提示（名前 + discipline説明 + ダブリング後のメンバー名・initial）
2. ユーザーが承認 / 修正 / 質問に戻る（最大2回リターン）

### Phase 3: TeamCreate

1. 承認されたロールから全メンバー名を生成
2. initial_mapを構築
3. TeamCreate実行
4. ハンドオフ契約の情報を会話コンテキストに明示的に出力
5. team-composerスキル完了、boardスキルに制御を戻す

## -cx Member: codex exec Integration

`-cx`メンバーはスキルではなく`codex exec`を直接使用する（code-review-boardのcodex-reviewerと同じパターン）。

### Prompt Template

boardのspawn prompt内に以下のテンプレートを含める:

```
Before participating in the discussion, run a Codex exploration:

1. Write the following prompt to a temp file:
   "Analyze the codebase from a {role-description} perspective regarding: {topic}.
   Identify key considerations, potential issues, and insights that a {role-name}
   would find relevant. Cite specific file paths and line numbers as evidence."

2. Execute: cat /tmp/cx-explore-prompt.txt | codex exec --ephemeral -m gpt-5.3-codex

3. Clean up: rm -f /tmp/cx-explore-prompt.txt

4. Use the findings as your unique perspective when writing hypotheses and critiques.
   Reference Codex findings with [codex-explored] label.
```

### Error Handling

- `codex` CLI未インストール or 失敗時: `-cx`メンバーはCodex結果なしで通常メンバーとして参加。最初のエントリに `(Codex exploration skipped: CLI not found)` を記載。

## Invocation Pattern

### How Boards Invoke team-composer

各boardのSKILL.mdのsetupステップに以下を記述:

```
Invoke `forte:team-composer` with:
- topic: {the board's topic/proposition/bug description}
- team_name: {discussion-id / investigation-id}
- role_count: "3-6"
- constraints: {board-specific constraints, if any}

After team-composer completes, spawn each member with board-specific prompts.
```

### Precedent

- `deep-fix` → `discussion-board`: Skill toolで別スキルを起動する実績あり (deep-fix/SKILL.md:214)
- `deep-fix` → `superpowers:writing-plans`: 同様のパターン (deep-fix/SKILL.md:233)
- リーダー（=メインエージェント）がSkill toolを呼び出すため、subagentからのSkill tool呼び出し問題は発生しない

## Impact on Existing Boards

### Changes Required

各boardのSKILL.mdで以下を更新:

| Board | Current | After |
|-------|---------|-------|
| discussion-board | Expertise map + 6-10ロール + TeamCreate を自前実装 | setupで`team-composer` invoke、spawn promptのみ自前 |
| design-board | 4-10ロール提案 + Codex advisory + TeamCreate | setupで`team-composer` invoke（constraints不要）、spawn promptのみ自前。Codex advisory廃止 |
| frontend-design-board | 3-layer role + a11y必須軸 + Codex advisory + TeamCreate | setupで`team-composer` invoke（constraints: `["a11y non-negotiable axis"]`）、spawn promptのみ自前。Codex advisory廃止 |
| investigation-board | 4-10ロール + Codex advisory + TeamCreate | setupで`team-composer` invoke、spawn prompt（チェックリスト + few-shot例）は自前。Codex advisory廃止 |

### Breaking Changes

- メンバー数: 既存の固定範囲（6-10, 4-10等）→ ロール3-6 × 2 = 6-12名に統一
- Codex advisory: 全board廃止、`-cx`メンバーに置換
- Entry ID: `-cx`メンバーは`{initial}X`形式を使用（新規）
- 投票: 全メンバー（通常 + -cx）が投票権を持つ

## File Location

```
skills/
  team-composer/
    SKILL.md          # team-composer skill definition
```

Plugin metadata (plugin.json, marketplace.json) にスキル追加は不要（skills/配下に置くだけで認識される）。
