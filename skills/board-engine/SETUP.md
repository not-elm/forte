# Board Engine — Setup Reference

Minimal reference for board skill setup phase. For full debate rules, entry formats, and conflict prevention rules, read `REFERENCE.md` at framing kickoff.

---

## File Model

Each discussion uses three file types in its working directory:

1. **Base WHITEBOARD.md** — Created at setup. Contains topic, framing. Becomes **read-only** after framing completes.
2. **Per-round WHITEBOARD-R{N}.md** — Created by leader at each round's hypothesize phase. One file per round.
3. **SYNTHESIS.md** — Leader-only file for cumulative state (Evidence Map, Draft Conclusion, Round Context Packet, etc.).

## Round Numbering

- Round numbers are **monotonically increasing**, never reset.
- For 2-phase boards: numbering continues across phases (e.g., Phase 1 R1, R2 → Phase 2 R3, R4).

## Per-Round WHITEBOARD-R{N}.md Template

```markdown
# WHITEBOARD — {id} / Round {N}
> Round: {N}
> Created: {YYYY-MM-DD}

## Hypotheses
### {member-A}
### {member-B}
<!-- ... per team member -->

## Critique
### {member-A}
### {member-B}
<!-- ... per team member -->

## Audit
```

Sections start empty. Board skills may add additional sections.

## Setup Checklist

1. Invoke `forte:team-composer` with topic, team_name, role_count, domain_hints, constraints
2. After Handoff Contract received: create working directory with base WHITEBOARD.md + SYNTHESIS.md
3. Spawn members (normal + -cx) with board-specific prompts
4. At framing kickoff: read `REFERENCE.md` for full debate rules
