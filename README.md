# forte

notelm's personal collection of Claude Code skills, packaged as a plugin.

## Installation

```sh
claude plugin marketplace add https://github.com/not-elm/forte.git
claude plugin install forte
```

## Skills

### forte:code-review-board

Multi-perspective code review from 7 perspectives (security, correctness, performance, etc.) using parallel reviewer agents. Each reviewer writes findings independently, then debates validity across rounds, and a leader synthesizes into a report with fix checklists.

| Argument | Description |
|----------|-------------|
| `target` (required) | File or directory paths to review |
| `--spec <path>` | Specification document for compliance checks |
| `--perspectives <list>` | Comma-separated perspectives to include; prefix with `-` to exclude |
| `--rounds <N>` | Number of debate rounds (default: 2, set 0 to skip debate) |

```
/code-review src/api/
/code-review src/api/ --spec docs/plans/api-design.md
/code-review src/api/ --perspectives security,correctness,performance
/code-review src/api/ --perspectives -codex-reviewer
```

### forte:codex-investigate

Run Codex CLI in read-only mode to investigate a bug's root cause from its symptoms. Describe the bug and Codex searches the codebase, identifies root causes with file paths and line numbers, assesses impact scope, and suggests fix approaches.

Arguments: free-form symptom description, plus optional additional context (OS, repro steps, error logs, file paths).

```
codex investigate the login page crashes after entering credentials on Safari
codex debug users report 500 errors on /api/orders since yesterday's deploy
```

### forte:codex-review

Run Codex CLI in read-only mode to review design documents, code, or hypotheses. Automatically selects review type (design/code/hypothesis) and finds contradictions, ambiguities, bugs, edge cases, and improvements.

Arguments: file paths and/or free text describing what to review.

```
codex review src/auth/middleware.ts
codex review docs/plans/api-design.md -- check for contradictions with the current implementation
```

### forte:discussion-board

Structured team debate with iterative synthesis using 4–10 role-based agents (scaled to topic complexity). Explores open-ended questions through rounds of hypothesize, critique, audit (via Codex), synthesize, and ratify phases. Produces a design doc when concluded.

Arguments: free-form proposition or question to explore.

```
discuss how should we handle rate limiting across our microservices
explore question what caching strategy best fits our read-heavy workload
```

## Prerequisites

[Codex CLI](https://github.com/openai/codex) is required for **codex-investigate** and **codex-review**:

```
npm i -g @openai/codex
```

## License

MIT
