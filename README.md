# GitHub Activity Tracker (read-only)

A local macOS LaunchAgent collects pull request and issue lifecycle events from the configured GitHub repositories each weekday at 7:00 a.m. local time. It uses `gh api` for read-only requests. The tracked source lives in this repository; the LaunchAgent runs a deployed copy under `~/Library/Application Support/GitHubActivityTracker/` so macOS privacy controls for `Documents` do not block Python from reading the script. Runtime data and logs are written under that deployed directory's `data/` folder.

## Files

- `activity_tracker.py` is the tracked source. The installed copy is `~/Library/Application Support/GitHubActivityTracker/activity_tracker.py`.
- `repos.txt` is the tracked repository list and is copied beside the deployed script.
- The deployed script deduplicates events in `~/Library/Application Support/GitHubActivityTracker/data/activity.jsonl`.
- `data/state.json` in this repository is a local symlink to the deployed state file for convenient viewing; it remains ignored by Git with the rest of `data/`.
- `data/daily-summary.md` is regenerated from the structured history after each successful run and starts with the latest run status, including an explicit “No new activity found in this run” line when the run adds no events.
- `data/state.json` stores the last successful run time and latest run message so a later run can catch up after sleep or a missed day.
- `data/logs/tracker.log` records run status and errors. launchd stdout and stderr logs are stored in the same `data/logs/` directory.
- launchd/com.access-ci.github-activity-tracker.plist is the LaunchAgent installed in ~/Library/LaunchAgents/.

The first run covers the preceding 24 hours. Later runs query from the previous successful run with a six-hour overlap. Existing records are deduplicated. Comments and reviews are not collected.

## Requirements

- macOS with launchd
- gh installed at /opt/homebrew/bin/gh
- gh already authenticated for an account that can read the listed repositories

The tracker does not read or store GitHub credentials. gh handles authentication.

## Manage the service

Inspect status: launchctl print gui/$(id -u)/com.access-ci.github-activity-tracker

Unload it: launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.access-ci.github-activity-tracker.plist

Load it again: launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.access-ci.github-activity-tracker.plist

Run the deployed copy once manually: `/usr/bin/python3 "$HOME/Library/Application Support/GitHubActivityTracker/activity_tracker.py"`

Edit the tracked `repos.txt` to change the repository list, then copy it to the deployed directory. When changing collector code, update the tracked script and copy it to the deployed directory. The plist runs the deployed copy on weekdays only; it does not run immediately when loaded.
