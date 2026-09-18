# codex-engine — Shared Codex CLI Execution Contract

Single normative definition of how forte skills invoke the OpenAI Codex CLI.

Any skill that runs `codex exec` MUST follow this contract instead of embedding its own
invocation block. Skills own only their **prompt**, their `{PREFIX}` namespace, and the
**workload tier** they declare — never the invocation mechanics, the effort policy, the wait
protocol, or the read-back rules.

**Prerequisite:** the `codex` CLI must be installed (`npm i -g @openai/codex`).

## Loading This Reference

1. Use `Glob pattern="**/codex-engine/REFERENCE.md"` to locate the file
2. Read it before constructing any Codex invocation

If the file is not found, display:

`> Warning: codex-engine reference not found. Using inline rules only.`

## Caller-Supplied Values

| Placeholder | Required | Meaning |
|-------------|----------|---------|
| `{PREFIX}` | yes | Temp-file namespace, unique per skill and phase (e.g. `parallel-research-codex`, `cx-critique`) |
| `{prompt}` | yes | The constructed prompt. Skill-specific — this contract does not constrain its content |
| `{TIER}` | yes | Workload class: `light`, `standard`, or `deep` (see below) |
| `{SCOPE}` | no | Paths the caller already located with Glob/Grep, space-separated. Shapes the budget block |

There are no other knobs. The model is never overridden, and reasoning effort is derived from
the tier — it can only ever move **down** from the user's configuration, never up.

## Workload Tiers

Codex capacity is a finite budget: a ChatGPT plan enforces usage limits, and a single board
discussion issues 20-30 runs. The tier is how a caller states how much of that budget a
particular run deserves.

| Tier | Use for | Target effort | Repository access |
|------|---------|---------------|-------------------|
| `light` | Verification and transcription-shaped work, where exploration is not the point — fact-checking claims, critiquing entries the prompt already carries | `low` | `{SCOPE}` plus files those paths explicitly cite (so a `file:line` claim stays verifiable); no searching or listing; project docs (`AGENTS.md`) not loaded |
| `standard` | Judgment over an already-identified target — reviewing a spec or a plan, forming hypotheses on a stated topic | `medium` | Starts at `{SCOPE}`, may step outside to verify a reference |
| `deep` | Exploration *is* the work — root-cause investigation, open research | Inherited (no override) | Unrestricted |

Assignments in force across the plugin:

| Call site | `{PREFIX}` | Tier |
|-----------|------------|------|
| parallel-research | `parallel-research-codex` | `deep` |
| codex-investigate | `codex-investigate` | `deep` |
| trio-brainstorming CP2 (approaches) | `trio-cp2` | `deep` |
| board `-cx` initial exploration | `cx-explore` | `deep` |
| spec-review | `spec-review-codex` | `standard` |
| plan-review | `plan-review-codex` | `standard` |
| trio-brainstorming CP1 (questions) | `trio-cp1` | `standard` |
| board hypothesize | `cx-hypothesize` | `standard` |
| board framing | `cx-framing` | `light` |
| board critique | `cx-critique` | `light` |
| board audit (fact-check) | `board-audit` | `light` |

A new call site that does not obviously fit takes the **lighter** tier; raise it only after a
run comes back visibly under-reasoned.

## Effort Resolution

The user's `~/.codex/config.toml` is a **ceiling, not a floor**. The contract lowers effort for
cheap workloads and otherwise stays out of the way:

1. `WANT` = the lower of the tier target and `FORTE_CODEX_MAX_EFFORT` (a session-wide override
   the user can export when they are close to their limit). Both unset (`deep`, no override)
   means nothing is passed at all.
2. If the user's configured effort is already at or below `WANT`, pass nothing.
3. Otherwise pass `-c model_reasoning_effort="$WANT"`.

Ranking: `minimal < low < medium < high < xhigh`. Only `low` and `medium` are ever passed, so
a model that rejects `xhigh` is never affected. **Effort is never raised above the user's
configuration.**

When the user has configured no effort at all, the tier target is passed as-is. Codex's own
default is `medium`, so this lowers (`light`) or matches (`standard`) — it does not raise.

Effort directly drives both spend and wall-clock: on one measured research prompt, `xhigh` took
9m16s where `medium` took 3m00s. That is the whole reason tiers exist, and also why the 15-minute
ceiling below accommodates high-effort configurations.

## Canonical Invocation

Codex runs **detached**. The Bash call returns immediately; completion is signalled by a
sentinel file carrying the exit code.

```bash
TIER={TIER}                 # light | standard | deep
SCOPE='{SCOPE}'             # empty string when the caller supplies none

TMPFILE=$(mktemp /tmp/{PREFIX}-prompt-XXXXXX)
OUTFILE=$(mktemp /tmp/{PREFIX}-final-XXXXXX)
LOGFILE=$(mktemp /tmp/{PREFIX}-log-XXXXXX)
DONEFILE=$(mktemp /tmp/{PREFIX}-done-XXXXXX)
rm -f "$DONEFILE"

cat <<'PROMPT_EOF' > "$TMPFILE"
{prompt}
PROMPT_EOF

# Execution Budget — engine-owned. Callers never write this block into their own prompt.
{
  echo
  echo '## Execution Budget'
  case "$TIER" in
    light)
      if [ -n "$SCOPE" ]; then
        echo "- Read only these paths, plus any file they explicitly cite: $SCOPE"
        echo '- Do not search, list, or otherwise explore the repository beyond that.'
      else
        echo '- Do not explore the repository beyond what this prompt already contains.'
      fi
      ;;
    standard)
      if [ -n "$SCOPE" ]; then
        echo "- Start from these paths: $SCOPE"
        echo '- Step outside them only to verify something they reference.'
      fi
      ;;
    deep)
      if [ -n "$SCOPE" ]; then
        echo "- Suggested starting points (not a restriction): $SCOPE"
      fi
      ;;
  esac
  echo '- Do not re-read a file you have already read.'
  echo '- No preamble, no restating of the task, no summary of what you read. Answer only.'
} >> "$TMPFILE"

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

effort_rank() {
  case "$1" in
    minimal) echo 0 ;; low) echo 1 ;; medium) echo 2 ;; high) echo 3 ;; xhigh) echo 4 ;; *) echo -1 ;;
  esac
}

case "$TIER" in
  light)    WANT=low ;;
  standard) WANT=medium ;;
  *)        WANT= ;;
esac

if [ -n "$FORTE_CODEX_MAX_EFFORT" ] && [ "$(effort_rank "$FORTE_CODEX_MAX_EFFORT")" -ge 0 ]; then
  if [ -z "$WANT" ] || [ "$(effort_rank "$FORTE_CODEX_MAX_EFFORT")" -lt "$(effort_rank "$WANT")" ]; then
    WANT="$FORTE_CODEX_MAX_EFFORT"
  fi
fi

EFFORT_ARG=""
RESOLVED_EFFORT="${CODEX_EFFORT:-(codex default)}"
if [ -n "$WANT" ] && { [ -z "$CODEX_EFFORT" ] || [ "$(effort_rank "$CODEX_EFFORT")" -gt "$(effort_rank "$WANT")" ]; }; then
  EFFORT_ARG="-c model_reasoning_effort=\"$WANT\""
  RESOLVED_EFFORT="$WANT"
fi

DOC_ARG=""
if [ "$TIER" = light ]; then DOC_ARG="-c project_doc_max_bytes=0"; fi

nohup sh -c '
  cat "'"$TMPFILE"'" | codex exec --ephemeral -s read-only \
    -c approval_policy="never" '"$EFFORT_ARG"' '"$DOC_ARG"' -o "'"$OUTFILE"'" > "'"$LOGFILE"'" 2>&1
  echo $? > "'"$DONEFILE"'"
' >/dev/null 2>&1 &

printf 'CODEX_PID=%s\n' "$!"
printf 'CODEX_FINAL_OUTPUT=%s\n' "$OUTFILE"
printf 'CODEX_DONE_MARKER=%s\n' "$DONEFILE"
printf 'CODEX_LOG=%s\n' "$LOGFILE"
printf 'CODEX_PROMPT=%s\n' "$TMPFILE"
printf 'CODEX_TIER=%s\n' "$TIER"
printf 'CODEX_MODEL=%s\n' "${CODEX_MODEL:-(codex default)}"
printf 'CODEX_EFFORT=%s\n' "$RESOLVED_EFFORT"
printf 'CODEX_CONFIG_EFFORT=%s\n' "${CODEX_EFFORT:-(codex default)}"
```

Flag rationale:

- `exec` — non-interactive subcommand. Any other invocation form can hang waiting on a TTY
- `--ephemeral` — skip session persistence; skills never resume sessions
- `-s read-only` — Codex may read the repo but never write, regardless of user-level sandbox config
- `-c approval_policy="never"` — without it the run inherits `approval_policy` from
  `~/.codex/config.toml` and can stall on an approval request. The read-only sandbox still
  blocks writes, so bypassing approval is safe here
- `-c model_reasoning_effort` — passed only when the tier's target is **below** the user's
  configuration. See Effort Resolution
- `-c project_doc_max_bytes=0` (`light` only) — a repository's `AGENTS.md` is loaded into every
  run's context by default. A fact-check does not need repository conventions, and a board
  issues a dozen of those per discussion
- `-o "$OUTFILE"` — persist the final message separately from progress/event output
- temp file + stdin — passing the prompt as a CLI argument can exceed shell argument length
  limits (~32KB on Windows) and cause Codex to hang silently
- `cfg_get` — reads the model and effort the run would inherit, so the resolved configuration
  can be announced before the wait starts, and so effort resolution knows the ceiling. Costs no
  wall-clock and touches nothing the run depends on

Set the **launching** Bash call's `timeout` to the default. It returns in milliseconds; the
15-minute ceiling below applies to the detached run, not to this call.

**Shell state does not persist between Bash calls.** Every command after the launch — the wait,
the read-back, the ledger append, the cleanup — must use the literal paths printed above, not
the variable names.

### Announcing the Resolved Configuration

Because effort decides whether a run takes three minutes or nine, the user must be told which
configuration they are waiting on **before** the wait begins, not after. Immediately after the
launching Bash call returns — before entering the wait protocol — display exactly one line
built from its output:

```
> Codex: model=gpt-5.6-sol / effort=medium (tier=standard, config=high)
```

- One line, no surrounding commentary. It is a status marker, not a report section
- Print whatever the values are, `(codex default)` included — an unset key is itself
  information ("Codex is running on its own defaults")
- When `CODEX_EFFORT` and `CODEX_CONFIG_EFFORT` differ, the parenthetical is the whole point:
  it shows the user that the tier saved them a step of reasoning effort
- A skill dispatching several Codex runs at once prints one line per run, labelled with the
  member or axis it belongs to (e.g. `> Codex [architecture-cx]: …`)
- These values are read from config, not from the live run. The run's own authoritative header
  (`model:` and `reasoning effort:` lines) lands in `CODEX_LOG` within about a second of
  launch; consult it only if a configuration mismatch is actually suspected

## Wait Protocol

Wait with a **Monitor until-loop** on the sentinel file. Do not use a foreground `sleep`.

- **Condition:** `CODEX_DONE_MARKER` exists
- **Ceiling:** 900 seconds (15 minutes), uniform across every skill

On ceiling exceeded: `kill` the launch's `CODEX_PID`, treat the run as a timeout, and follow the
failure handling below. An orphaned Codex process is harmless — the run is `-s read-only` and
its output goes only to temp files that are then discarded.

## Read-Back Protocol

1. Read `CODEX_DONE_MARKER`. Its contents are the run's exit code.
2. On exit code `0`, use the file-reading tool on `CODEX_FINAL_OUTPUT`, from line 1 through
   EOF. If the tool paginates, continue in sequential, non-overlapping chunks until EOF.
3. **Never** use `tail`, `head`, or a line-count cap on the final-message file. A partial
   terminal excerpt is not valid input for synthesis or transcription.
4. If `CODEX_FINAL_OUTPUT` is empty or missing, inspect `CODEX_LOG` before concluding
   anything — an exhausted usage limit can end a run without a final message.
5. Record the run in the ledger (below), then clean up:
   `rm -f <prompt> <final output> <done marker> <log>` using the literal paths from launch.

### Usage Ledger

Spend is invisible unless it is written down, and a board issues 20-30 runs. After read-back and
**before** cleanup, append one line per run:

```bash
USAGE=$(grep -iE 'token' <CODEX_LOG> | tail -1)
printf '%s\t%s\t%s\t%s\t%s\n' "$(date +%Y-%m-%dT%H:%M:%S)" '{PREFIX}' '{TIER}' '<resolved effort>' \
  "${USAGE:-tokens n/a}" >> "${FORTE_CODEX_LEDGER:-/tmp/forte-codex-usage.log}"
```

The token line's exact format is Codex's own and is not guaranteed; the `grep` is deliberately
loose and `tokens n/a` is a normal outcome, never an error. A skill that issues many runs (any
board) reports the session total from this file when it concludes:
`> Codex: 26 runs this session ({FORTE_CODEX_LEDGER})`.

## Failure Handling

| Classification | Detection | Action |
|----------------|-----------|--------|
| Success | exit code `0` and a non-empty final message | Proceed to read-back |
| Not installed | exit code `127` | Apply the calling skill's Codex-unavailable fallback |
| **Usage limit** | `CODEX_LOG` matches `/usage limit|rate limit|too many requests|\b429\b/i`, with a non-zero exit **or** an empty final message | Apply the degradation rules below |
| Failure | any other non-zero exit | Surface `CODEX_LOG` contents, then apply the skill's failure path |
| Timeout | ceiling exceeded | Kill `CODEX_PID`, treat as failure, note the timeout |

Detection command (literal paths from launch):

```bash
STATUS=$(cat <CODEX_DONE_MARKER>)
grep -qiE 'usage limit|rate limit|too many requests|\b429\b' <CODEX_LOG> && echo USAGE_LIMIT
grep -oiE 'try again at [^.]*' <CODEX_LOG> | tail -1
```

Always clean up temp files on every path, including failure.

## Usage-Limit Degradation

`usage_limit` is the one failure this contract does not leave to the caller's discretion. A plan's
capacity refills on a clock; nothing the session does brings it back sooner.

1. **Never retry.** Not in the same phase, not with a lighter tier, not "once more to be sure".
2. **Never abort the user's task.** Every caller MUST define a path that completes without Codex.
   A skill whose entire value is Codex mediation still completes — degraded and labelled.
3. **Say it once**, at the point of degradation, including the reset time when the log carries one:

   ```
   > Codex: usage limit reached — retry after 4:01 AM. Continuing without Codex.
   ```

4. **Record it where the output lives** — a report note, a ledger row, a `Positions & Dissent`
   entry. Silence reads as a Codex opinion that was never given.

Degradation path per caller:

| Caller | Path |
|--------|------|
| parallel-research / spec-review / plan-review | Existing "Claude Code Agent only" fallback, with the ⚠ note at report top |
| trio-brainstorming | Same as its `127` row: continue as plain brainstorming, record `Codex (rev N): usage limit` |
| codex-investigate | Claude investigates with the same prompt and labels the report as Codex-free |
| board skills | All `-cx` members withdraw; the board continues with the remaining members (see board-engine REFERENCE.md) |

## Common Mistakes

- **Passing a model flag** — the model always comes from the user's CLI configuration
- **Raising effort above the user's configuration** — the config is a ceiling. Tiers only lower
- **Omitting `{TIER}`** — it is required. There is no default tier; an unstated tier is a caller bug
- **Writing the Execution Budget block into the caller's prompt** — the engine appends it. A
  caller that writes its own ends up with two, contradicting each other
- **Skipping the model/effort line, or printing it after the run** — its whole purpose is to
  let the user judge the expected wait before committing to it
- **Reusing shell variables across Bash calls** — shell state does not persist. Wait, read-back,
  ledger and cleanup use the literal paths printed at launch
- **Setting a per-skill Bash timeout for the Codex run** — the detached run is bounded by the
  Monitor ceiling, not by the Bash tool
- **Using the Bash tool's `run_in_background` instead of this block** — background completion
  notifications have been observed firing prematurely for long Codex runs, which makes the
  skill read an empty output file. The sentinel file is the only completion signal to trust
- **Using a subcommand other than `codex exec`** — other forms may hang
- **Passing the prompt as a CLI argument** — exceeds shell argument length limits
- **Truncating the final message** — read `CODEX_FINAL_OUTPUT` from line 1 through EOF
- **Cleaning up before reading** — the output file must survive until the read completes
- **Retrying after a usage limit, or letting one end the user's task** — see the degradation rules
