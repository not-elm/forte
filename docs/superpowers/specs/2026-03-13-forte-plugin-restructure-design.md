# Forte Plugin Restructure Design

> Date: 2026-03-13
> Status: Approved
> Author: notelm

## Summary

Restructure the forte project from an informal skill collection nested under `~/workspace/Zenn/forte/` into a standalone Claude Code plugin at `~/workspace/forte/`, installable via git URL.

## Background

Forte is notelm's personal collection of Claude Code skills (code-review-board, codex-investigate, codex-review, discussion-board). Currently it lacks the metadata files required for Claude Code plugin registration and uses a non-standard directory layout (`plugins/` instead of `skills/`). The goal is to make it installable via `https://github.com/not-elm/forte.git`.

## Prerequisites

- The GitHub repository `https://github.com/not-elm/forte.git` must exist (create it if it doesn't).

## Design

### Target Structure

```
~/workspace/forte/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── skills/
│   ├── code-review-board/
│   │   └── SKILL.md
│   ├── codex-investigate/
│   │   └── SKILL.md
│   ├── codex-review/
│   │   └── SKILL.md
│   └── discussion-board/
│       └── SKILL.md
├── .gitignore
├── CLAUDE.md
└── LICENSE
```

Note: The `docs/` directory used during design is not part of the final structure and will be removed after implementation.

### plugin.json

```json
{
  "name": "forte",
  "description": "notelm's personal collection of Claude Code skills",
  "version": "1.0.0",
  "author": {
    "name": "notelm"
  },
  "repository": "https://github.com/not-elm/forte.git",
  "license": "MIT"
}
```

### marketplace.json

Follows the reference format from the superpowers plugin. The `source` is `"./"` because the marketplace.json lives inside the plugin repo itself.

```json
{
  "name": "forte",
  "description": "notelm's personal collection of Claude Code skills",
  "owner": {
    "name": "notelm"
  },
  "plugins": [
    {
      "name": "forte",
      "description": "notelm's personal collection of Claude Code skills",
      "version": "1.0.0",
      "source": "./",
      "author": {
        "name": "notelm"
      }
    }
  ]
}
```

### .gitignore

Replace the current default-deny whitelist with a standard gitignore:

```gitignore
node_modules/
.DS_Store
```

The default-deny pattern was needed when forte was nested inside the Zenn repo. As a standalone repo, all files should be tracked normally.

### CLAUDE.md

Update to reflect the new structure:

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is "forte" — notelm's personal collection of Claude Code skills, packaged as a Claude Code plugin installable via git URL.

## Repository Structure

.claude-plugin/
  plugin.json          # Plugin metadata
  marketplace.json     # Marketplace definition for git URL installation
skills/
  code-review-board/   # Multi-perspective parallel code review (8 reviewer agents)
  codex-investigate/   # Bug root-cause investigation via Codex CLI
  codex-review/        # Design/code/hypothesis review via Codex CLI
  discussion-board/    # Structured team debate with iterative synthesis

## Plugin Architecture

Each skill is a standalone SKILL.md with YAML frontmatter (name, description with trigger keywords) followed by the full skill specification.

### Key Patterns Across Skills

- Codex-based skills (codex-investigate, codex-review): Use codex exec CLI in read-only mode. Prompts are always written to a temp file and piped via stdin to avoid shell argument length limits.
- Agent Team skills (code-review-board, discussion-board): Use Claude Code's TeamCreate/SendMessage/Agent tools to orchestrate multiple parallel agents. Follow a 2-file model (WHITEBOARD.md for member writes, SYNTHESIS.md for leader-only writes) with per-member write zones and append-only conflict prevention.

## Adding a New Skill

1. Create skills/<skill-name>/SKILL.md with frontmatter and skill spec
2. Bump version in .claude-plugin/plugin.json and .claude-plugin/marketplace.json
```

### LICENSE

MIT license, copyright 2026 notelm.

### Git Remote

Set origin to `https://github.com/not-elm/forte.git`. Forte already has its own `.git` directory (it is an independent repo, not a subdirectory of the Zenn repo), so this is a `git remote set-url` or `git remote add` depending on whether a remote is already configured.

## Migration Steps

1. Move the repo directory from `~/workspace/Zenn/forte/` to `~/workspace/forte/` (preserves `.git/` and all history)
2. Rename `plugins/` to `skills/`
3. Create `.claude-plugin/plugin.json`
4. Create `.claude-plugin/marketplace.json`
5. Create `LICENSE` (MIT)
6. Replace `.gitignore`
7. Update `CLAUDE.md`
8. Remove `docs/` directory (design-time artifact)
9. Set git remote origin to `https://github.com/not-elm/forte.git`

No changes to any SKILL.md files — audited and confirmed they contain no references to the `plugins/` directory path.

## What Is NOT Changing

- All four SKILL.md files remain exactly as they are
- No new skills are added
- No hooks, tests, or README.md are added (can be done later)
