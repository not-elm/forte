# Discussion Board — setup/explore フェーズ追加設計

> Date: 2026-03-27
> Status: Draft
> Scope: `skills/discussion-board/SKILL.md` の setup フェーズ変更

## Summary

discussion-board の setup フェーズを `setup/explore` → `setup/confirm` の2サブフェーズに分割する。議論の前にリーダーがユーザーと対話的に観点を洗い出し、その結果をチームのロール構成に直接反映させることで、議論の質と方向性を改善する。

## Background

現行の discussion-board では、setup フェーズでリーダーが命題を分析し 4-10 のロールを一方的に提案する。ユーザーは承認/修正できるが、ロール提案の根拠となる観点がユーザーとの対話なしに決まるため、議論の方向性がリーダーの分析に依存する。

ユーザーとの対話を通じて観点を固めることで、議論に含めるべき視点が明確になり、チーム構成の精度が上がる。

## Design

### Phase Model の変更

**現行:**
```
setup → framing → [Round N: hypothesize → critique → audit → revise → synthesize → ratify] → concluded
```

**新:**
```
setup/explore → setup/confirm → framing → [Round N: hypothesize → critique → audit → revise → synthesize → ratify] → concluded
```

Phase Model テーブル変更:

| Phase | Who | What |
|-------|-----|------|
| setup/explore | Leader + User | 命題を分析し、ユーザーに1問ずつ質問して観点を洗い出す |
| setup/confirm | Leader + User | 観点リスト（名前＋説明＋必要性）を提示、ユーザー承認後にチーム作成＋ファイル作成 |

framing 以降の行は変更なし。

### setup/explore 仕様

**リーダーの行動:**

1. 命題を受け取ったら、まず明確さを評価する
2. 1問ずつ質問する（複数質問を1メッセージにまとめない）
3. 可能な限り選択肢形式で質問する（オープンエンドも可）
4. 質問の焦点:
   - 命題の背景・動機（なぜこの議論が必要か）
   - 目的・ゴール（何が決まれば成功か）
   - 既知の制約・前提条件
   - 特に重視したい観点や除外したい観点
5. 十分な情報が集まったら、質問を切り上げて setup/confirm に遷移する

**明確さに応じた質問数:**
- 背景・目的・制約が十分明確 → 2-3問で完了
- 曖昧・広範 → 4-6問まで掘り下げ

**遷移条件（いずれかを満たしたら confirm へ）:**

1. **十分な観点が導出可能** — 命題の複雑さに見合う数の観点を導出できる情報が揃った（リーダーが判断）。目安: 命題の目的・背景が把握でき、主要な制約・前提が明らかになり、互いに独立した観点を4つ以上言語化できる状態。
2. **最大6問に到達** — 情報が不十分でも打ち切り、得られた情報で最善の観点リストを生成する。

6問到達時に観点が4つ未満の場合は、リーダーが補完して最低4つにする（setup/confirm の補完ルールに従う）。

### setup/confirm 仕様

**観点リスト提示:**

各観点を以下の形式で提示する:

```markdown
## 提案する観点（= チームメンバー）

1. **{観点名}** — {一言説明}
   > なぜ必要か: {この議論でこの観点が重要な理由}

2. **{観点名}** — {一言説明}
   > なぜ必要か: {理由}

...
```

**観点の数 = チーム人数（4-10の範囲）。**

**名前の制約:**
- 英語の短い名前（1-2語、スペース区切り）
- サブセクションヘッダー（`### {name}`）として使えること
- イニシャル（先頭1文字大文字）がチーム内で重複しないこと（ID形式 `[H-{initial}-{seq}]` の衝突防止）
- イニシャル重複時はリーダーが名前を調整して回避する

**ユーザー却下時のフロー:**
- ユーザーが修正を要求 → リーダーがフィードバックを反映して観点リストを再提示（confirm 内でループ）
- ユーザーが「もっと質問して」と要求 → explore に戻る
- 最大3回の再提示で収束しない場合、ユーザーに自由記述でロールを指定してもらう

**補完・統合ルール:**
- 4未満の場合: リーダーが命題に関連する補完的な観点を追加提案し、理由を明示する
- 10超の場合: 類似する観点を統合候補として提示し、ユーザーに選択を委ねる

**ユーザーが最初からロールを指定した場合:**
- explore をスキップし、指定されたロールで confirm に直接入る（名前の制約チェックのみ実施）

**承認後の処理:**
- 各観点名をそのままロール名（= メンバー名）としてチーム作成
- WHITEBOARD.md + SYNTHESIS.md を作成（既存テンプレート通り）
- `docs/discussions/{discussion-id}/` を `.gitignore` に追加（既存ルール通り）

### 既存仕様への影響範囲

**変更が必要:**

| 箇所 | 変更内容 |
|------|---------|
| Phase Model（テキスト＋テーブル） | `setup` → `setup/explore → setup/confirm` に分割 |
| Workflow Overview テーブル | 同上、2行に分割 |
| Phase Notes `### setup` | 削除し、`### setup/explore` と `### setup/confirm` に置き換え |
| Core Principles 1行目 | 「Analyze proposition, suggest roles」の記述を新フローに合わせて更新 |

**変更不要:**

| 箇所 | 理由 |
|------|------|
| framing 以降の全フェーズ | チーム作成後の動作は同一 |
| Entry Formats 全体 | IDフォーマット・記法に変更なし |
| WHITEBOARD.md / SYNTHESIS.md テンプレート | メンバー名のプレースホルダ構造は同一 |
| Conflict Prevention Rules | per-member write zones 等のルールは不変 |
| Communication Rules | broadcast ルールは不変 |
| Ratification Rules / Timeout Policy | 不変 |

## Codex Review Summary

Codex CLI によるレビューで以下の指摘があり、設計に反映済み:

- **名前の制約追加** — ロール名がIDイニシャル・サブセクションヘッダーとして機能する制約を明示
- **却下フローの定義** — confirm でのループ、explore への戻り、最大再提示回数を規定
- **打ち切り条件の明確化** — 「十分」の目安を具体的に定義
- **補完・統合ルールの定義** — 4未満・10超のケースの処理を明示
- **ロール指定済みケース** — explore スキップルールを追加
