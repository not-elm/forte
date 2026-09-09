# codex-engine — Shared Codex CLI Execution Contract

Single normative definition of how forte skills invoke the OpenAI Codex CLI.

Any skill that runs `codex exec` MUST follow this contract instead of embedding its own
invocation block. Skills own only their **prompt** and their `{PREFIX}` namespace — never
the invocation mechanics, the wait protocol, or the read-back rules.

**Prerequisite:** the `codex` CLI must be installed (`npm i -g @openai/codex`).

## Loading This Reference

1. Use `Glob pattern="**/codex-engine/REFERENCE.md"` to locate the file
2. Read it before constructing any Codex invocation

If the file is not found, display:

`> Warning: codex-engine reference not found. Using inline rules only.`

## Caller-Supplied Values

| Placeholder | Meaning |
|-------------|---------|
| `{PREFIX}` | Temp-file namespace, unique per skill and phase (e.g. `parallel-research-codex`, `cx-critique`) |
| `{prompt}` | The constructed prompt. Skill-specific — this contract does not constrain its content |

There are no other knobs. Timeout and reasoning effort are fixed by this contract (see below).

## Canonical Invocation

Codex runs **detached**. The Bash call returns immediately; completion is signalled by a
sentinel file carrying the exit code.

```bash
TMPFILE=$(mktemp /tmp/{PREFIX}-prompt-XXXXXX)
OUTFILE=$(mktemp /tmp/{PREFIX}-final-XXXXXX)
LOGFILE=$(mktemp /tmp/{PREFIX}-log-XXXXXX)
DONEFILE=$(mktemp /tmp/{PREFIX}-done-XXXXXX)
rm -f "$DONEFILE"

cat <<'PROMPT_EOF' > "$TMPFILE"
{prompt}
PROMPT_EOF

CODEX_CFG="${CODEX_HOME:-$HOME/.codex}/config.toml"
cfg_get() {
  awk -v sec="$1" -v key="$2" '
    /^[[:space:]]*\[/ { cur=$0; gsub(/^[[:space:]]*\[|\][[:space:]]*$/,"",cur); next }
    $0 ~ "^[[:space:]]*" key "[[:space:]]*=" && cur == sec {
      sub("^[^=]*=[[:space:]]*",""); sub(/[[:space:]]*#.*$/,""); gsub(/^"|"$/,""); print; exit }
  ' "$CODEX_CFG" 2>/dev/null
}
CODEX_PROFILE=$(cfg_get "" profile)
CODEX_MODEL=$(cfg_get "profiles.$CODEX_PROFILE" model)
[ -n "$CODEX_MODEL" ] || CODEX_MODEL=$(cfg_get "" model)
CODEX_EFFORT=$(cfg_get "profiles.$CODEX_PROFILE" model_reasoning_effort)
[ -n "$CODEX_EFFORT" ] || CODEX_EFFORT=$(cfg_get "" model_reasoning_effort)

nohup sh -c '
  cat "'"$TMPFILE"'" | codex exec --ephemeral -s read-only \
    -c approval_policy="never" -o "'"$OUTFILE"'" > "'"$LOGFILE"'" 2>&1
  echo $? > "'"$DONEFILE"'"
' >/dev/null 2>&1 &

printf 'CODEX_PID=%s\n' "$!"
printf 'CODEX_FINAL_OUTPUT=%s\n' "$OUTFILE"
printf 'CODEX_DONE_MARKER=%s\n' "$DONEFILE"
printf 'CODEX_LOG=%s\n' "$LOGFILE"
printf 'CODEX_PROMPT=%s\n' "$TMPFILE"
printf 'CODEX_MODEL=%s\n' "${CODEX_MODEL:-(codex default)}"
printf 'CODEX_EFFORT=%s\n' "${CODEX_EFFORT:-(codex default)}"
```

Flag rationale:

- `exec` — non-interactive subcommand. Any other invocation form can hang waiting on a TTY
- `--ephemeral` — skip session persistence; skills never resume sessions
- `-s read-only` — Codex may read the repo but never write, regardless of user-level sandbox config
- `-c approval_policy="never"` — without it the run inherits `approval_policy` from
  `~/.codex/config.toml` and can stall on an approval request. The read-only sandbox still
  blocks writes, so bypassing approval is safe here
- `-o "$OUTFILE"` — persist the final message separately from progress/event output
- temp file + stdin — passing the prompt as a CLI argument can exceed shell argument length
  limits (~32KB on Windows) and cause Codex to hang silently
- `cfg_get` — reads the model and effort the run will inherit, so they can be announced before
  the wait starts (see below). It resolves the active profile first, then the top-level table,
  and stops at the first `[section]` header so `[projects.*]` entries never leak in. Costs no
  wall-clock and touches nothing the run depends on

Set the **launching** Bash call's `timeout` to the default. It returns in milliseconds; the
15-minute ceiling below applies to the detached run, not to this call.

## Model and Reasoning Effort

**Never pass `-m`, `--model`, or `-c model_reasoning_effort`.** The run inherits whatever the
user has configured in `~/.codex/config.toml`. Skills do not second-guess that setting.

Effort directly drives wall-clock: on one measured research prompt, `xhigh` took 9m16s where
`medium` took 3m00s. The 15-minute ceiling exists to accommodate high-effort configurations.
If a user's configuration routinely exceeds the ceiling, raise the ceiling here — do not
reintroduce per-skill effort overrides.

### Announcing the Resolved Configuration

Because effort is what decides whether a run takes three minutes or nine, the user must be
told which configuration they are waiting on **before** the wait begins, not after. Immediately
after the launching Bash call returns — before entering the wait protocol — display exactly one
line from its `CODEX_MODEL` / `CODEX_EFFORT` output:

```
> Codex: model=gpt-5.6-sol / reasoning effort=high
```

- One line, no surrounding commentary. It is a status marker, not a report section
- Print whatever the values are, `(codex default)` included — an unset key is itself
  information ("Codex is running on its own defaults")
- A skill dispatching several Codex runs at once prints one line per run, labelled with the
  member or axis it belongs to (e.g. `> Codex [architecture-cx]: model=… / reasoning effort=…`)
- These values are read from config, not from the live run. The run's own authoritative header
  (`model:` and `reasoning effort:` lines) lands in `CODEX_LOG` within about a second of
  launch; consult it only if a configuration mismatch is actually suspected

## Wait Protocol

Wait with a **Monitor until-loop** on the sentinel file. Do not use a foreground `sleep`.

- **Condition:** `CODEX_DONE_MARKER` exists
- **Ceiling:** 900 seconds (15 minutes), uniform across every skill

On ceiling exceeded: `kill "$CODEX_PID"`, treat the run as a timeout, and follow the failure
handling below. An orphaned Codex process is harmless — the run is `-s read-only` and its
output goes only to temp files that are then discarded.

## Read-Back Protocol

1. Read `CODEX_DONE_MARKER`. Its contents are the run's exit code.
2. On exit code `0`, use the file-reading tool on `CODEX_FINAL_OUTPUT`, from line 1 through
   EOF. If the tool paginates, continue in sequential, non-overlapping chunks until EOF.
3. **Never** use `tail`, `head`, or a line-count cap on the final-message file. A partial
   terminal excerpt is not valid input for synthesis or transcription.
4. Clean up only after the complete final message has been read:
   `rm -f "$CODEX_PROMPT" "$CODEX_FINAL_OUTPUT" "$CODEX_DONE_MARKER" "$CODEX_LOG"`

## Failure Handling

| Exit code | Meaning | Action |
|-----------|---------|--------|
| `0` | Success | Proceed to read-back |
| `127` | `codex` not installed | Apply the calling skill's Codex-unavailable fallback |
| other non-zero | Codex failed | Surface `CODEX_LOG` contents, then apply the skill's failure path |
| (ceiling exceeded) | Timeout | Kill `CODEX_PID`, treat as failure, note the timeout |

The calling skill decides what a failure *means* — some degrade to a partial report, others
abort. This contract only defines how the failure is detected and reported.

Always clean up temp files on every path, including failure.

## Common Mistakes

- **Passing a model or effort flag** — the contract inherits the user's CLI configuration.
  Per-skill overrides are what this reference exists to eliminate
- **Skipping the model/effort line, or printing it after the run** — its whole purpose is to
  let the user judge the expected wait before committing to it
- **Setting a per-skill Bash timeout for the Codex run** — the detached run is bounded by the
  Monitor ceiling, not by the Bash tool. The old 180s/300s/600s per-skill values are gone
- **Using the Bash tool's `run_in_background` instead of this block** — background completion
  notifications have been observed firing prematurely for long Codex runs, which makes the
  skill read an empty output file. The sentinel file is the only completion signal to trust
- **Using a subcommand other than `codex exec`** — other forms may hang
- **Passing the prompt as a CLI argument** — exceeds shell argument length limits
- **Truncating the final message** — read `CODEX_FINAL_OUTPUT` from line 1 through EOF
- **Cleaning up before reading** — the output file must survive until the read completes
