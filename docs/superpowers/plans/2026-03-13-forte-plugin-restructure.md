# Forte Plugin Restructure Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure forte into a registerable Claude Code plugin installable via git URL.

**Architecture:** Move the repo to `~/workspace/forte/`, rename `plugins/` to `skills/`, add `.claude-plugin/` metadata directory with `plugin.json` and `marketplace.json`, replace `.gitignore`, update `CLAUDE.md`, add MIT LICENSE, and set git remote.

**Tech Stack:** Git, Claude Code plugin system (SKILL.md, plugin.json, marketplace.json)

**Spec:** `docs/superpowers/specs/2026-03-13-forte-plugin-restructure-design.md`

---

## Chunk 1: Repository Move and Restructure

### Task 1: Move repo to standalone location

**Files:**
- Move: `~/workspace/Zenn/forte/` → `~/workspace/forte/`

- [ ] **Step 1: Move the repository**

```bash
mv ~/workspace/Zenn/forte ~/workspace/forte
```

- [ ] **Step 2: Verify the move**

```bash
ls ~/workspace/forte/.git
ls ~/workspace/forte/plugins/
```

Expected: `.git` directory exists, `plugins/` contains 4 skill directories.

- [ ] **Step 3: Change working directory**

```bash
cd ~/workspace/forte
```

All subsequent steps operate from `~/workspace/forte/`.

---

### Task 2: Rename plugins/ to skills/

**Files:**
- Rename: `plugins/` → `skills/`

- [ ] **Step 1: Rename the directory**

```bash
git mv plugins skills
```

- [ ] **Step 2: Verify skill files are intact**

```bash
ls skills/code-review-board/SKILL.md
ls skills/codex-investigate/SKILL.md
ls skills/codex-review/SKILL.md
ls skills/discussion-board/SKILL.md
```

Expected: All 4 SKILL.md files present.

- [ ] **Step 3: Commit**

```bash
git commit -m "rename plugins/ to skills/ for Claude Code plugin convention"
```

---

### Task 3: Create .claude-plugin/plugin.json

**Files:**
- Create: `.claude-plugin/plugin.json`

- [ ] **Step 1: Create directory and file**

```bash
mkdir -p .claude-plugin
```

Write `.claude-plugin/plugin.json`:

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

- [ ] **Step 2: Verify valid JSON**

```bash
cat .claude-plugin/plugin.json | python3 -m json.tool > /dev/null
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "add plugin.json metadata for Claude Code registration"
```

---

### Task 4: Create .claude-plugin/marketplace.json

**Files:**
- Create: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Write the file**

Write `.claude-plugin/marketplace.json`:

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

- [ ] **Step 2: Verify valid JSON**

```bash
cat .claude-plugin/marketplace.json | python3 -m json.tool > /dev/null
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/marketplace.json
git commit -m "add marketplace.json for git URL installation"
```

---

### Task 5: Create LICENSE

**Files:**
- Create: `LICENSE`

- [ ] **Step 1: Write MIT license**

Write `LICENSE`:

```
MIT License

Copyright (c) 2026 notelm

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: Commit**

```bash
git add LICENSE
git commit -m "add MIT license"
```

---

### Task 6: Replace .gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Replace contents**

Write `.gitignore`:

```gitignore
node_modules/
.DS_Store
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "replace default-deny gitignore with standard one"
```

---

### Task 7: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Replace contents**

Write `CLAUDE.md`:

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is "forte" — notelm's personal collection of Claude Code skills, packaged as a Claude Code plugin installable via git URL.

## Repository Structure

` ` `
.claude-plugin/
  plugin.json          # Plugin metadata
  marketplace.json     # Marketplace definition for git URL installation
skills/
  code-review-board/   # Multi-perspective parallel code review (8 reviewer agents)
  codex-investigate/   # Bug root-cause investigation via Codex CLI
  codex-review/        # Design/code/hypothesis review via Codex CLI
  discussion-board/    # Structured team debate with iterative synthesis
` ` `

## Plugin Architecture

Each skill is a standalone SKILL.md with YAML frontmatter (name, description with trigger keywords) followed by the full skill specification.

### Key Patterns Across Skills

- **Codex-based skills** (codex-investigate, codex-review): Use `codex exec` CLI in read-only mode. Prompts are always written to a temp file and piped via stdin to avoid shell argument length limits.
- **Agent Team skills** (code-review-board, discussion-board): Use Claude Code's TeamCreate/SendMessage/Agent tools to orchestrate multiple parallel agents. Follow a 2-file model (WHITEBOARD.md for member writes, SYNTHESIS.md for leader-only writes) with per-member write zones and append-only conflict prevention.

## Adding a New Skill

1. Create `skills/<skill-name>/SKILL.md` with frontmatter and skill spec
2. Bump version in `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "update CLAUDE.md for new plugin structure"
```

---

### Task 8: Clean up and set remote

**Files:**
- Remove: `docs/` directory

- [ ] **Step 1: Remove design-time docs directory**

```bash
git rm -r docs/
git commit -m "remove design-time docs directory"
```

- [ ] **Step 2: Set git remote**

```bash
git remote add origin https://github.com/not-elm/forte.git
```

- [ ] **Step 3: Verify final structure**

```bash
find . -not -path './.git/*' -not -path './.git' | sort
```

Expected output:

```
.
./.claude-plugin
./.claude-plugin/marketplace.json
./.claude-plugin/plugin.json
./.gitignore
./CLAUDE.md
./LICENSE
./skills
./skills/code-review-board
./skills/code-review-board/SKILL.md
./skills/codex-investigate
./skills/codex-investigate/SKILL.md
./skills/codex-review
./skills/codex-review/SKILL.md
./skills/discussion-board
./skills/discussion-board/SKILL.md
```

- [ ] **Step 4: Verify remote**

```bash
git remote -v
```

Expected: `origin https://github.com/not-elm/forte.git (fetch)` and `(push)`.
