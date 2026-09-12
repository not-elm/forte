---
name: qwen-commit
description: Use when an authorized workflow is about to create a new Git commit after selecting and staging the intended changes.
---

# qwen-commit

Requires Python 3.9+, Git, and Ollama with `qwen3.8:27b-q8_0` installed.
`QWEN_COMMIT_MODEL` overrides it; generated messages are English Conventional
Commits. The runner captures and validates the staged tree.

1. The caller stages intended files. Use the target repository as cwd.
2. Choose one mode: existing full text (including trailers) goes in a private
   mode-0600 `--message-file PATH`; no subject uses Qwen; required trailers on a
   generated subject repeat `--trailer 'Key: value'`. Never invent full text to
   skip Qwen or combine the option modes.
3. Resolve `scripts/qwen_commit.py` relative to THIS skill and run once:

   ```sh
   python3 "<resolved-skill-directory>/scripts/qwen_commit.py" [message options]
   ```

4. Delete only a caller-created message file. Report `hash`/`subject` or the
   short error. If `committed` is true/unknown, inspect Git before retrying.

Load only its ≤1 KiB result; do not read source, diffs, prompts, or model logs.
Wait on that command session. A lost session means unknown.

No staging, amend, push, retry, cloud fallback, model pull, or caller substitute.
Preserve permissions and hooks. Its Git commit is
terminal; do not invoke this skill around it. `/forte:qwen-commit` stays explicit.
