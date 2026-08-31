---
name: parallel-research
description: >
  Use when investigating topics by dispatching parallel research to Codex CLI and Claude Code Agent.
  Triggers: parallel research, 並列調査, dual investigate, parallel investigate, 並列リサーチ
---

# Parallel Research

## Overview

Dispatch parallel investigations to Codex CLI (codebase-focused) and a Claude Code Agent (codebase + web), then synthesize a unified report in the terminal. Two AI perspectives on the same topic, combined into one coherent answer.

**Prerequisite:** The `codex` CLI must be installed (`npm i -g @openai/codex`). If unavailable, fall back to Claude Code Agent results only.

**Shared contract:** Codex invocation mechanics live in codex-engine REFERENCE.md. Before Phase 4:

1. Use `Glob pattern="**/codex-engine/REFERENCE.md"` to locate the file
2. Read it

If not found, display: `> Warning: codex-engine reference not found. Using inline rules only.`

## When to Use

- When you want multiple AI perspectives on a technical question, design decision, or bug
- When you want both codebase analysis (Codex) and broader research (Claude Code Agent + Web)
- When a single investigation might miss something

**When NOT to use:**
- Simple questions or explanations that don't need parallel investigation
- File modification tasks (this skill is read-only)
- Deep multi-round debates (use investigation-board or discussion-board instead)

## Workflow

```dot
digraph parallel_research {
    rankdir=TB;
    "Receive topic" [shape=box];
    "Classify topic" [shape=box];
    "Build prompts" [shape=box];
    "Display status" [shape=box];
    "Launch Bash + Agent\nin parallel" [shape=box];
    "Synthesize report" [shape=box];
    "Display to user" [shape=doublecircle];

    "Receive topic" -> "Classify topic";
    "Classify topic" -> "Build prompts";
    "Build prompts" -> "Display status";
    "Display status" -> "Launch Bash + Agent\nin parallel";
    "Launch Bash + Agent\nin parallel" -> "Synthesize report";
    "Synthesize report" -> "Display to user";
}
```

### Phase 1: Receive Topic

Receive the topic from the user via skill arguments. The topic is free-form text describing what to investigate.

If no topic is provided in the arguments, ask the user with AskUserQuestion:
> "What topic would you like me to investigate with parallel research?"

### Phase 2: Classify Topic

Classify the topic into one of three categories to determine prompt strategy:

| Category | Criteria | Codex Instructions | Claude Code Agent Instructions |
|----------|----------|-------------------|-------------------------------|
| **Code** | Mentions specific files, functions, bugs, or implementation details | Investigate the codebase | Investigate the codebase (different perspective) |
| **Knowledge** | General technical concepts, design patterns, best practices | Search codebase for related implementations | Web search + codebase investigation |
| **Mixed** | Contains elements of both | Investigate the codebase | Web search + codebase investigation |

When uncertain, default to **Mixed**.

### Phase 3: Build Prompts

Build separate prompts for Codex and Claude Code Agent.

**Shared output format (include in both prompts):**
```
Report your findings in this structure:
- Summary (3-5 sentences)
- Detailed findings (bullet points)
- Sources (file paths, URLs, etc.)
- Confidence: High / Medium / Low with reasoning
```

**Codex prompt template:**
```
## Research Topic
{user_topic}

## Instructions
Investigate this topic by reading the codebase. {category_specific_codex_instructions}

Cite specific file paths and line numbers as evidence.
Be concise — if a section has no findings, write "N/A".

## Output Format
{shared_output_format}
```

**Category-specific Codex instructions:**
- **Code:** "Focus on the specific files and functions mentioned. Trace the execution flow, identify related code, and analyze the behavior."
- **Knowledge:** "Search the codebase for implementations related to this concept. Identify patterns, usage examples, and any deviations from standard practices."
- **Mixed:** "Investigate both the specific code mentioned and broader patterns in the codebase related to this topic."

**Claude Code Agent prompt template:**
```
## Research Topic
{user_topic}

## Instructions
Investigate this topic thoroughly. {category_specific_agent_instructions}

Report only what you find with evidence. Do not speculate.

## Output Format
{shared_output_format}
```

**Category-specific Agent instructions:**
- **Code:** "Use Read, Grep, and Glob to investigate the codebase from a different angle than a pure code search. Look for architectural context, related tests, documentation, and usage patterns."
- **Knowledge:** "Use WebSearch and WebFetch to research this topic online (documentation, Stack Overflow, blog posts, RFCs). Also check the codebase with Read/Grep/Glob for related implementations."
- **Mixed:** "Combine codebase investigation (Read/Grep/Glob) with web research (WebSearch/WebFetch) to build a complete picture."

### Phase 4: Launch Parallel

Display a status message, then launch both investigations in a **single message** with two tool calls:

**Status message (display before tool calls):**
> "Codex と Claude Code Agent に並列で調査を依頼しています（3〜5分程度かかることがあります）..."

**Tool call 1 — Bash (Codex):** the canonical invocation from codex-engine REFERENCE.md with:

| Value | |
|-------|---|
| `{PREFIX}` | `parallel-research-codex` |
| `{prompt}` | `{codex_prompt}` built in Phase 3 |

The call returns immediately — the detached run does not block the Agent call that follows it.
Research is the slowest Codex workload in this plugin, which is why the reference's 900s
ceiling matters most here.

**Tool call 2 — Agent:**
```json
{
  "description": "parallel-research Claude investigation",
  "prompt": "{agent_prompt}"
}
```
- Uses general-purpose agent (default subagent_type)
- Agent has access to Read, Grep, Glob, WebSearch, WebFetch

**Both tool calls MUST be in the same message for true parallel execution.**

Then wait per the reference's wait protocol: a Monitor until-loop on `CODEX_DONE_MARKER` with
a 900s ceiling, and read `CODEX_FINAL_OUTPUT` from line 1 through EOF before synthesis.

**Codex unavailable fallback:** If `CODEX_DONE_MARKER` reports exit code 127, proceed with Claude Code Agent results only. Note this in the report.

### Phase 5: Synthesize Report

After both results return (or one result + one error), synthesize into this format and display in the terminal:

```markdown
## Parallel Research Report: {topic}

### Overall Conclusion
{Integrated conclusion drawing from both investigations}

### Agreement
{Points where both Codex and Claude Code Agent reached the same conclusion}

### Differences & Complementary Findings
{Points found by only one side, or where perspectives differ}

### Codex Findings
{Summary of Codex investigation results}

### Claude Code Findings
{Summary of Claude Code Agent investigation results}

### Confidence
{Overall confidence level with reasoning}
```

**Confidence rubric:**

| Level | Criteria |
|-------|----------|
| **High** | Both agree and provide concrete evidence (file paths, URLs) |
| **Medium** | Mostly agree with minor differences, or evidence is limited |
| **Low** | Significant disagreement, weak evidence, or only one source available |

**Fallback cases:**
- If only one side returned results, still use this format but note the missing source and set confidence to Low
- If one side's output doesn't match the expected structure, include whatever was returned under the appropriate section and note it was unstructured
- If both fail, report the error to the user and stop

## Error Handling

| Situation | Action |
|-----------|--------|
| Codex CLI not installed (exit 127) or ceiling exceeded (900s) | Report with Claude Code Agent results only. Add note: "⚠ Codex未使用: {reason}" at report top |
| Agent failure | Report with Codex results only. Add note: "⚠ Claude Code Agent未使用: {reason}" at report top |
| Both fail | Display error message and stop |
| Partial/malformed output from either side | Best-effort integration, note which side was incomplete |

## Common Mistakes

Invocation-level mistakes (subcommand, approval policy, CLI-argument prompts, truncation,
model/effort flags, `run_in_background`) are covered in codex-engine REFERENCE.md.
Skill-specific:

- **Not launching both tools in the same message**: Codex Bash call and Agent call MUST be in a single message for parallel execution. Sequential calls defeat the purpose of this skill.
- **Waiting on Codex before dispatching the Agent**: the detached Bash call returns immediately, so there is no reason to serialize. Dispatch both, then run the wait protocol once.
- **Synthesizing from one side while the other is still running**: complete the wait protocol before Phase 5, or the report silently drops half its input.
