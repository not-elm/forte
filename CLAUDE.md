# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is "forte" — notelm's personal collection of Claude Code skills, packaged as a Claude Code plugin installable via git URL.

## Repository Structure

```
.claude-plugin/
  plugin.json          # Plugin metadata
  marketplace.json     # Marketplace definition for git URL installation
skills/
  autopilot/           # Full-pipeline orchestrator: spec → reviews → plan → implementation → code-review → simplify
  batch-fix/           # Batch-fix code review findings with clear solutions
  board-engine/        # Shared debate engine reference for all board skills (round-split WB, debate cycle, rules)
  codex-engine/        # Shared Codex CLI execution contract for all codex-based skills (invocation, wait, read-back)
  codex-investigate/   # Bug root-cause investigation via Codex CLI
  deep-fix/            # Deep-fix complex code review findings requiring design
  design-board/        # Implementation design via 2-phase structured team debate
  discussion-board/    # Structured team debate with iterative synthesis
  frontend-design-board/ # Frontend design discussion via 2-phase team debate
  investigation-board/ # Evidence-based bug investigation via structured team debate
  parallel-research/   # Parallel topic investigation via Codex CLI + Claude Code Agent
  plan-review/         # Parallel implementation-plan review via Codex CLI + Claude Code Agent (4 fixed axes)
  spec-review/         # Parallel spec/design-doc review via Codex CLI + Claude Code Agent (4 fixed axes)
  team-composer/       # Shared team composition for board skills (expertise map + always-doubling)
```

## Plugin Architecture

Each skill is a standalone SKILL.md with YAML frontmatter (name, description with trigger keywords) followed by the full skill specification.

### Key Patterns Across Skills

- **Codex-based skills** (codex-investigate, parallel-research, plan-review, spec-review, plus board `-cx` members): Invocation mechanics are defined once in `codex-engine/REFERENCE.md` — detached `codex exec` in read-only mode, prompt via temp file + stdin, completion signalled by a sentinel file carrying the exit code, a 900s Monitor wait ceiling, and full-file read-back. Each SKILL.md owns only its prompt and its `{PREFIX}`; it never sets a timeout, a model, or a reasoning effort. `parallel-research`, `spec-review`, and `plan-review` additionally dispatch a Claude Code Agent in parallel within a single message.
- **Agent Team skills** (design-board, discussion-board, frontend-design-board, investigation-board): Use Claude Code's TeamCreate/SendMessage/Agent tools to orchestrate multiple parallel agents. Follow a round-split WHITEBOARD model (base WHITEBOARD.md + per-round WHITEBOARD-R{N}.md for member writes, SYNTHESIS.md for leader-only writes) with per-member write zones and append-only conflict prevention. Shared debate rules are in `board-engine/REFERENCE.md`; each board SKILL.md contains only board-specific logic.
- **Orchestrator skills** (autopilot): Chain existing skills via sequential Skill invocations with pipeline-side gate overrides (standing answers to downstream skills' user prompts). Own only stage ordering, arguments, ledger, and stop conditions — never duplicate stage logic.

## Adding a New Skill

1. Create `skills/<skill-name>/SKILL.md` with frontmatter and skill spec
2. Bump version in `.claude-plugin/plugin.json` (`marketplace.json` has no version field)
