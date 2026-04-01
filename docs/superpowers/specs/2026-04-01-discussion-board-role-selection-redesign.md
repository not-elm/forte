# Discussion Board — Role Selection Redesign

> Date: 2026-04-01
> Status: Design approved
> Scope: skills/discussion-board/SKILL.md — setup/explore, setup/confirm, and role re-anchoring in hypothesize/critique/revise

## Problem

The current 3-layer role selection approach (discipline + stance + epistemic constraint) derived from fault-line mapping produces teams where roles are too dispersed relative to the investigation topic. Two specific issues:

1. **Irrelevant roles**: Fault-line mapping prioritizes diverse perspectives over topic relevance, producing members with little direct expertise in the subject matter.
2. **Forced uniqueness**: The implicit expectation that all members have different disciplines prevents spawning multiple experts in the same domain, even when deeper coverage of that domain would produce better discussion.

## Design

### 1. Replace fault-line map with expertise map (setup/explore)

**Remove:** Fault-line mapping (3-5 axes of disagreement), propositional entropy check based on fault lines, all references to "contested assumptions", "second-order consequences", "premise challenges".

**Add:** Expertise map generation. The leader analyzes the topic and identifies 6-10 expert domains directly required to discuss it in depth.

Format:
```
Expertise Map — {topic}
1. {domain}: {why this topic requires this expertise}
2. {domain}: {why this topic requires this expertise}
...
```

Rules:
- Only domains **directly relevant** to the topic. No "nice to have" domains.
- Same domain with different focus areas is allowed as separate entries (e.g., "Performance × Latency", "Performance × Throughput").
- Number of domains = planned team size (6-10).

**Question policy:**
- Focus on topic clarification. Target 2-3 questions, maximum 4.
- Question count is cumulative across explore visits (unchanged).
- If leader cannot identify 6 independent domains, ask one additional clarifying question (outside the 4-question limit) — replaces the current propositional entropy check.
- If user specifies roles upfront, skip explore (unchanged).

**Transition to setup/confirm:** When leader has an expertise map with enough domains for a 6-10 member team.

### 2. Simplify role format to discipline-only (setup/confirm)

**Remove:** 3-layer role construction (discipline + stance + epistemic constraint), "Expected argument" field, "Guards against" field, Mandatory Proposition Challenger role requirement.

**Add:** Single-layer role format with expected contribution.

Presentation format:
```
1. **{Role Name}** — {discipline/expertise domain}
   > Expected contribution: {concrete contribution this member brings to the discussion}
```

**Team size:**
- Range: 6-10 (minimum raised from 4 to 6).
- Default: 6. Leader adjusts based on topic complexity:
  - Focused topic → 6
  - Moderate complexity → 7-8
  - Multi-faceted/complex → 9-10
- Fewer than 6 is not permitted. More than 10: leader presents consolidation candidates.

**Duplicate domains allowed:** Multiple members may share the same domain if they cover different focus areas. Names must be distinct and meaningful (e.g., "Sentinel" and "Bastion" for two security-focused members).

**Name constraints:** Unchanged — short English names, unique first-letter initials, 2-letter fallback if collision is unavoidable.

**User approval gate:** Unchanged flow (present → modify/approve loop). Approval message simplified to: "These are the team members. Add, remove, or modify as needed."

- Max 3 re-presentations without convergence → ask user to specify roles in free text (unchanged).
- User requests more questions → return to explore, max 2 returns, cumulative question count (unchanged).

### 3. Simplify role re-anchoring (hypothesize, critique, revise)

**Current:** Restate each member's epistemic stance + epistemic constraint.

**Change to:** Restate each member's discipline + expected contribution.

Purpose is unchanged: prevent role collapse as WHITEBOARD accumulates content. The re-anchoring content is shorter but still provides the necessary identity anchor.

Affected phases:
- hypothesize (per-round re-anchoring in broadcast)
- critique (per-round re-anchoring in broadcast)
- revise (re-anchoring alongside audit findings)

### 4. No changes to other phases

The following remain unchanged: framing, audit, synthesize, ratify, concluded. Entry formats, WHITEBOARD.md template, SYNTHESIS.md template, Design Doc template, Conflict Prevention Rules, Ratification Rules, Communication Rules, and Timeout Policy are all unaffected.

## Summary of Changes

| Section | Before | After |
|---------|--------|-------|
| setup/explore | Fault-line map (3-5 axes of disagreement) | Expertise map (6-10 required domains) |
| setup/explore | Up to 6 questions | Up to 4 questions |
| setup/confirm | 3-layer role (discipline + stance + constraint) | Discipline only |
| setup/confirm | Expected argument + Guards against | Expected contribution |
| setup/confirm | Mandatory Proposition Challenger | Removed |
| setup/confirm | Team size 4-10, default varies | Team size 6-10, default 6 |
| hypothesize/critique/revise | Re-anchor with stance + constraint | Re-anchor with discipline + contribution |
