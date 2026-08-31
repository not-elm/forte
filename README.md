# forte

notelm's personal collection of Claude Code skills, packaged as a plugin.

## Installation

```sh
claude plugin marketplace add https://github.com/not-elm/forte.git
claude plugin install forte
```

## Skills

### forte:codex-investigate

Run Codex CLI in read-only mode to investigate a bug's root cause from its symptoms. Describe the bug and Codex searches the codebase, identifies root causes with file paths and line numbers, assesses impact scope, and suggests fix approaches.

Arguments: free-form symptom description, plus optional additional context (OS, repro steps, error logs, file paths).

```
codex investigate the login page crashes after entering credentials on Safari
codex debug users report 500 errors on /api/orders since yesterday's deploy
```

### forte:discussion-board

Structured team debate with iterative synthesis using 4–10 role-based agents (scaled to topic complexity). Explores open-ended questions through rounds of hypothesize, critique, audit (via Codex), synthesize, and ratify phases. Produces a design doc when concluded.

Arguments: free-form proposition or question to explore.

```
discuss how should we handle rate limiting across our microservices
explore question what caching strategy best fits our read-heavy workload
```

## Prerequisites

[Codex CLI](https://github.com/openai/codex) is required for **codex-investigate**:

```
npm i -g @openai/codex
```

## License

MIT
