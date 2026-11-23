# GitHub Activity Tracker (read-only)

A local macOS LaunchAgent collects pull request and issue lifecycle events from the configured GitHub repositories each weekday at 7:00 a.m. local time. It uses gh api for read-only requests and writes all generated activity under the ignored data/ directory.

## Files

- activity_tracker.py reads repository lifecycle events and deduplicates them in data/activity.jsonl.
- data/daily-summary.md is regenerated from the structured history after each successful run.
- data/state.json stores the last successful run time so a later run can catch up after sleep or a missed day.
- data/logs/tracker.log records run status and errors.
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

Run once manually: /usr/bin/python3 ./activity_tracker.py

Edit repos.txt to change the tracked repositories. The LaunchAgent runs the script on weekdays only; it does not run immediately when loaded.
