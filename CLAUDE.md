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
  code-review-board/   # Multi-perspective parallel code review (8 reviewer agents)
  codex-investigate/   # Bug root-cause investigation via Codex CLI
  codex-review/        # Design/code/hypothesis review via Codex CLI
  discussion-board/    # Structured team debate with iterative synthesis
  investigation-board/ # Evidence-based bug investigation via structured team debate
```

## Plugin Architecture

Each skill is a standalone SKILL.md with YAML frontmatter (name, description with trigger keywords) followed by the full skill specification.

### Key Patterns Across Skills

- **Codex-based skills** (codex-investigate, codex-review): Use `codex exec` CLI in read-only mode. Prompts are always written to a temp file and piped via stdin to avoid shell argument length limits.
- **Agent Team skills** (code-review-board, discussion-board, investigation-board): Use Claude Code's TeamCreate/SendMessage/Agent tools to orchestrate multiple parallel agents. Follow a 2-file model (WHITEBOARD.md for member writes, SYNTHESIS.md for leader-only writes) with per-member write zones and append-only conflict prevention.

## Adding a New Skill

1. Create `skills/<skill-name>/SKILL.md` with frontmatter and skill spec
2. Bump version in `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`
