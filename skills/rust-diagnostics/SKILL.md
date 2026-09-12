---
name: rust-diagnostics
description: Use when the assistant is about to run cargo check or cargo clippy while working in a Rust project.
---

# rust-diagnostics

Run one local command so raw Cargo output stays outside caller context. It
executes the requested check once and returns one compact JSON line; local Qwen
explains only ambiguous evidence.

Resolve `scripts/rust_diagnostics.py` relative to THIS installed skill. From
the target repository, preserve the requested toolchain and Cargo arguments:

```text
python3 <skill-dir>/scripts/rust_diagnostics.py [--toolchain NAME] check -- <Cargo arguments>
python3 <skill-dir>/scripts/rust_diagnostics.py [--toolchain NAME] clippy -- <Cargo arguments>
```

Forward the requested package, features, target, manifest, profile,
locking/offline, toolchain, and later lint arguments unchanged. The runner owns
JSON/color flags and rejects `--fix`; add no command, feature, or lint policy.

Read the result first. Open only its referenced report/diagnostic artifact when
needed; do not routinely load stdout/stderr. Wait on the original command
session and never launch a replacement run.

The runner may create normal Cargo artifacts but never edits source or applies
suggestions. Its Cargo process is terminal: do not invoke this skill around it.
No retry, cloud summary, suggested-command execution, or model pull.

`/forte:rust-diagnostics` remains available explicitly. Preserve host
permissions and higher-priority user instructions.
