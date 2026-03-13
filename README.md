# forte

notelm's personal collection of Claude Code skills, packaged as a plugin.

## Installation

```sh
claude plugin marketplace add https://github.com/not-elm/forte.git
claude plugin install forte
```

## Skills

| Skill | Description | Triggers |
|-------|-------------|----------|
| **code-review-board** | Multi-perspective code review using 7 parallel reviewer agents | `/code-review`, `review code`, `code review`, `コードレビュー`, `レビュー` |
| **codex-investigate** | Bug root-cause investigation via Codex CLI | `codex investigate`, `codex debug`, `codex 調査`, `原因調査` |
| **codex-review** | Design/code/hypothesis review via Codex CLI | `codex review`, `design review with codex`, `hypothesis verification`, `second opinion on code` |
| **discussion-board** | Structured team debate with iterative synthesis | `discuss`, `explore question`, `how should we`, `open forum`, `議論`, `検討`, `どうすべき` |

## Prerequisites

[Codex CLI](https://github.com/openai/codex) is required for **codex-investigate** and **codex-review**:

```
npm i -g @openai/codex
```

## License

MIT
