# Repository agent instructions

## Scope and safety

- This repository collects GitHub issue and pull request lifecycle activity from
  the repositories listed in `repos.txt`. Treat remote GitHub access as
  read-only.
- Do not inspect credentials, tokens, environment files, Keychain contents,
  private keys, or credential stores. Let the `gh` CLI use its existing
  authentication without printing or copying credential material.
- Do not use `gh` commands that create, edit, close, merge, delete, dispatch,
  or otherwise change GitHub resources. Collection uses the existing
  `activity_tracker.py` workflow and its GET-only `gh api` requests.
- Do not expand collection beyond `repos.txt` or collect repository source,
  secrets, comments, or reviews. The intended records are issue and pull
  request lifecycle events documented in `README.md`.
- Collection writes are limited to the ignored `data/` directory beside the
  script being run. The deployed LaunchAgent copy writes under
  `~/Library/Application Support/GitHubActivityTracker/data/`; a manual run
  from the repository writes under its local `data/` directory. Do not write
  elsewhere unless the user explicitly asks.
- Do not load, unload, bootstrap, kick, or otherwise alter a launchd job as part
  of routine inspection. Do not change account privacy settings or grant broad
  filesystem access to work around macOS privacy controls.
- Preserve existing work and generated data. Never clean, reset, overwrite, or
  discard user files.

## Workflow

- Read `README.md`, `activity_tracker.py`, `repos.txt`, and the LaunchAgent
  plist before proposing changes to collection behavior.
- For collection-specific tasks, follow the workflow described by this file:
  use the existing collector, preserve prior state, and report its bounded
  time coverage and local outputs. Do not claim a complete history.
- Distinguish the collector's GitHub API access (GET-only) from its local
  writes to `data/`. Do not describe the entire process as filesystem-read-only.
- Keep `activity_tracker.py` and `repos.txt` in this repository as the tracked
  source. If an explicitly requested deployment is made, copy both beside
  each other under `~/Library/Application Support/GitHubActivityTracker/`;
  the LaunchAgent must run that deployed copy rather than the source under
  `Documents`.
- Report the repositories and time window covered, local output files written,
  errors, and any run that was not performed. The collector uses a bounded
  lookback and incremental state.
- Before handoff, summarize changed files, permitted checks and their results,
  checks not run, assumptions, and unresolved operational or security risks.

## LaunchAgent troubleshooting

- Check the script's file mode and read access, then inspect the precise
  `StandardErrorPath` message. A script can be readable by Unix permissions
  while macOS privacy controls still deny a process access to a location under
  `Documents`.
- Do not recommend `chmod` as a fix when the script is already readable.
- Do not grant Full Disk Access or other broad privacy permissions as a
  workaround. Prefer a narrowly scoped, user-approved location outside
  protected folders (for example, a dedicated directory under
  `~/Library/Application Support/`) and update the LaunchAgent paths together
  if relocation is explicitly requested.
- Do not load, unload, bootstrap, or kick the agent unless the user explicitly
  asks for that operational change.
