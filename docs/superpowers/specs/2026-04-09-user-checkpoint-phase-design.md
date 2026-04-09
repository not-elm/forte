# User Checkpoint Phase Design

> Date: 2026-04-09
> Status: Draft
> Scope: board-engine shared + all board skills

## Summary

Add an optional `user-checkpoint` phase between `synthesize` and `ratify` in the standard debate cycle. When the leader identifies aspects that require user confirmation after synthesizing a round, the system pauses to ask the user questions before proceeding to ratification. This gives the user a structured opportunity to provide domain knowledge, business judgments, and factual inputs that the AI team cannot determine internally.

## Background

### Problem

Currently, board-type skills run their debate cycles autonomously without user interaction during rounds. User interaction points exist only at phase boundaries (design-board's user-review, frontend-design-board's user-review-1/2). This means:

1. Teams may ratify conclusions based on unverified assumptions about user requirements
2. Business trade-off decisions are made without user input
3. Factual premises known only to the user remain unchecked
4. Multi-round disagreements persist without the user's tiebreaking input
5. Process failures (audit failures, low-confidence conclusions) proceed without user awareness

### Existing User Interaction Points

| Board | Interaction | Timing | Mandatory |
|-------|------------|--------|-----------|
| design-board | user-review | Between Phase 1 and Phase 2 | Yes |
| frontend-design-board | user-review-1 | After Phase 1 ratify | Yes |
| frontend-design-board | user-review-2 | After Phase 2 ratify | Yes |
| discussion-board | (none) | — | — |
| investigation-board | (none) | — | — |

The new `user-checkpoint` is complementary: it operates **within** a round (between synthesize and ratify), is **optional** (skipped when no triggers match), and provides **targeted questions** rather than a full review.

## Design

### Phase Model Change

The standard debate cycle in board-engine REFERENCE.md changes from:

```
[Round N: hypothesize → critique → audit → revise (if needed) → synthesize → ratify]
```

To:

```
[Round N: hypothesize → critique → audit → revise (if needed) → synthesize → user-checkpoint (if needed) → ratify]
```

`user-checkpoint` is a conditional phase, like `revise`. It is skipped when no trigger conditions match.

### Trigger Condition Checklist

The leader evaluates this checklist after synthesize completes. If one or more conditions match, `user-checkpoint` is executed.

| # | Condition | Criteria | Example |
|---|-----------|----------|---------|
| 1 | **Domain requirement uncertainty** | The conclusion depends on user's business requirements or domain knowledge that the team cannot determine internally | "Is performance or UX the priority for this feature?" |
| 2 | **Business trade-off judgment** | Multiple technically valid options exist and a business judgment is needed | "Accept increased cost for high availability?" |
| 3 | **Unverified premise** | Facts underlying hypotheses cannot be verified by the team or audit, and only the user knows | "What is the actual concurrent connection count in production?" |
| 4 | **Scope boundary ambiguity** | The scope of the conclusion is unclear and user intent confirmation is needed | "Can this change break backward compatibility of the existing API?" |
| 5 | **Unresolvable member disagreement** | The same dispute persists in Round Context Packet's Open disputes for **2+ rounds** | "RDB vs NoSQL remains undecided for 2 consecutive rounds" |
| 6 | **Process confidence degradation** | Audit failed, unresolved inaccuracies (❌/⚠️) remain after revise, or Draft Conclusion confidence is **low** | "Codex timed out, audit was skipped" |

Each board skill can override: add board-specific conditions, or disable specific conditions.

### Evaluation Source

The leader references these SYNTHESIS.md sections to evaluate the checklist:

- **Draft Conclusion** — confidence level, unresolved items
- **Evidence Map** — claim confidence ratings
- **Round Context Packet** — open disputes, next-round focus
- **Audit results** (in WHITEBOARD-R{N}.md) — failure status, unresolved ❌/⚠️

### Execution Flow

1. Leader evaluates trigger checklist against SYNTHESIS.md artifacts
2. **No match** → skip to ratify
3. **Match** → construct questions and present via AskUserQuestion (single call, all questions in numbered list)
4. Record user response in SYNTHESIS.md `## User Checkpoint` → `### Round {N}`
5. Branch on response:
   - **Confirmation only** (no direction change needed) → include user response in ratify broadcast, proceed to ratify
   - **Direction change needed** → skip ratify, create WHITEBOARD-R{N+1}.md, re-enter hypothesize with user response as new constraint in broadcast
   - **Direction change criteria:** The user explicitly states a direction change is needed, OR the user's answer invalidates a key claim in the Draft Conclusion (leader judgment). When ambiguous, leader asks a follow-up: "この回答を踏まえて、現在の結論の方向で投票に進んでよいですか？"

### AskUserQuestion Format

```
Round {N} の統合結果について、以下の点を確認させてください。

1. {question}
   背景: {why this needs user input, citing entry IDs}

2. {question}
   背景: {why this needs user input, citing entry IDs}

回答後、チームの投票（ratify）に進みます。
方向転換が必要な場合はその旨お伝えください。
```

### SYNTHESIS.md Record Format

```markdown
## User Checkpoint
### Round {N}
- **Trigger:** {matched condition number(s) and name(s)}
- **Questions:** {questions asked}
- **Response:** {user's response verbatim}
- **Action:** ratify / re-enter hypothesize with constraint: {constraint summary}
```

### SYNTHESIS.md Template Update

Add `## User Checkpoint` section to SYNTHESIS.md templates in all board skills:

```markdown
## User Checkpoint
```

(Empty section, populated per-round when user-checkpoint fires.)

### Board-Specific Applicability

| Board | Phase 1 | Phase 2 | Notes |
|-------|---------|---------|-------|
| discussion-board | N/A (single phase) | N/A | All 6 conditions apply to the single debate cycle |
| design-board | Not applied | All 6 conditions | Phase 1 has no audit/revise/ratify; user-review serves as gate |
| frontend-design-board | Conditions 1-5 only | All 6 conditions | Phase 1 has no audit/revise → condition 6 is irrelevant |
| investigation-board | N/A (single phase) | N/A | All 6 conditions apply |

### Interaction with Existing Mechanisms

- **user-review (design-board, frontend-design-board)**: These are mandatory, phase-boundary reviews. user-checkpoint is optional, within-round. No conflict.
- **Ratify push-back**: If user-checkpoint leads to ratify, members can still push back. If user-checkpoint leads to hypothesize re-entry, no ratify occurs that round.
- **Max rounds**: user-checkpoint does not consume an additional round. The round counter increments only when hypothesize restarts.
- **Timeout policy**: No timeout for user-checkpoint (user is a human, not an agent). Leader waits for response.

### Conflict Prevention

No new conflict rules needed. user-checkpoint is leader-only (AskUserQuestion + SYNTHESIS.md write), consistent with existing rule #2 (SYNTHESIS.md is leader-only).

## Changes Required

### board-engine/REFERENCE.md

1. Update Standard Debate Cycle string to include `user-checkpoint (if needed)`
2. Add new `### user-checkpoint` section between `### synthesize` and `### ratify`
3. Add User Checkpoint entry format to Shared Entry Formats

### board-engine/SETUP.md

No changes needed (setup reference does not detail per-phase steps).

### discussion-board/SKILL.md

1. Update Phase Model string
2. Add `user-checkpoint` row to phase table
3. Add `## User Checkpoint` to SYNTHESIS.md template

### design-board/SKILL.md

1. Update Phase 2 debate cycle string
2. Note: Phase 1 is excluded (no ratify loop)
3. Add `## User Checkpoint` to phase-2/SYNTHESIS.md template

### investigation-board/SKILL.md

1. Update Phase Model string
2. Add `## User Checkpoint` to SYNTHESIS.md template

### frontend-design-board/SKILL.md

1. Update Phase 1 and Phase 2 debate cycle strings
2. Note Phase 1 override: condition 6 disabled
3. Add `## User Checkpoint` to both phase SYNTHESIS templates
4. Update `references/synthesis-templates.md` accordingly
