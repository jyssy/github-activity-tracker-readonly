#!/usr/bin/env python3
"""Collect read-only GitHub issue and pull request lifecycle activity."""

import datetime as dt
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
LOGS = DATA / "logs"
REPOS_FILE = ROOT / "repos.txt"
STATE_FILE = DATA / "state.json"
ACTIVITY_FILE = DATA / "activity.jsonl"
DIGEST_FILE = DATA / "daily-summary.md"
GH = "/opt/homebrew/bin/gh"
OVERLAP = dt.timedelta(hours=6)
INITIAL_LOOKBACK = dt.timedelta(hours=24)
TRACKED_EVENTS = {"closed", "merged", "reopened"}

os.umask(0o077)
LOGS.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOGS / "tracker.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("activity-tracker")


def parse_time(value):
    if not value:
        return None
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def iso_utc(value):
    return value.astimezone(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_repositories():
    repos = []
    for raw in REPOS_FILE.read_text(encoding="utf-8").splitlines():
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
            raise ValueError("repos.txt contains an invalid owner/repository entry")
        repos.append(value)
    if not repos:
        raise ValueError("repos.txt has no repositories")
    return list(dict.fromkeys(repos))


def flatten_pages(payload):
    if not isinstance(payload, list):
        raise RuntimeError("GitHub API returned an unexpected response")
    flattened = []
    for page in payload:
        if isinstance(page, list):
            flattened.extend(page)
        else:
            flattened.append(page)
    return flattened


def gh_api(endpoint, fields=None):
    command = [
        GH, "api", "--paginate", "--slurp", "--method", "GET",
        "-H", "Accept: application/vnd.github+json",
    ]
    for key, value in (fields or {}).items():
        command.extend(["-f", f"{key}={value}"])
    command.append(endpoint)
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"gh api failed with exit status {result.returncode}")
    try:
        return flatten_pages(json.loads(result.stdout))
    except (json.JSONDecodeError, TypeError) as exc:
        raise RuntimeError("GitHub API returned invalid JSON") from exc


def in_window(value, start, end):
    timestamp = parse_time(value)
    return timestamp is not None and start <= timestamp <= end


def make_id(repo, number, event_type, source_id, timestamp):
    stable = f"{repo}|{number}|{event_type}|{source_id or timestamp}"
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def collect(repo, start, end):
    issues = gh_api(
        f"repos/{repo}/issues",
        {"state": "all", "since": iso_utc(start), "per_page": "100"},
    )
    records = []
    for issue in issues:
        if not isinstance(issue, dict) or "number" not in issue:
            continue
        number = issue["number"]
        is_pr = "pull_request" in issue
        item_url = issue.get("html_url", "")
        title = issue.get("title", "")
        user = issue.get("user") or {}
        created = issue.get("created_at")
        if in_window(created, start, end):
            records.append({
                "event_id": make_id(repo, number, "opened", "opened", created),
                "timestamp": created,
                "repo": repo,
                "type": "opened",
                "number": number,
                "title": title,
                "actor": user.get("login"),
                "url": item_url,
                "pull_request": is_pr,
            })

        timeline = gh_api(
            f"repos/{repo}/issues/{number}/timeline",
            {"per_page": "100"},
        )
        merged_times = {
            event.get("created_at")
            for event in timeline
            if isinstance(event, dict) and event.get("event") == "merged"
        }
        for event in timeline:
            if not isinstance(event, dict):
                continue
            event_type = event.get("event")
            timestamp = event.get("created_at")
            if event_type not in TRACKED_EVENTS or not in_window(timestamp, start, end):
                continue
            if event_type == "closed" and is_pr and timestamp in merged_times:
                continue
            actor = event.get("actor") or event.get("user") or {}
            source_id = event.get("id") or event.get("node_id")
            records.append({
                "event_id": make_id(repo, number, event_type, source_id, timestamp),
                "timestamp": timestamp,
                "repo": repo,
                "type": event_type,
                "number": number,
                "title": title,
                "actor": actor.get("login"),
                "url": item_url,
                "pull_request": is_pr,
            })
    return records


def load_existing_ids():
    ids = set()
    if not ACTIVITY_FILE.exists():
        return ids
    with ACTIVITY_FILE.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError("activity.jsonl has an invalid line; stopping to protect history") from exc
            if item.get("event_id"):
                ids.add(item["event_id"])
    return ids


def write_digest():
    records = []
    if ACTIVITY_FILE.exists():
        with ACTIVITY_FILE.open(encoding="utf-8") as stream:
            records = [json.loads(line) for line in stream if line.strip()]
    records.sort(key=lambda item: (item.get("timestamp", ""), item.get("repo", ""), item.get("number", 0)))
    grouped = {}
    for item in records:
        timestamp = parse_time(item["timestamp"])
        local_day = timestamp.astimezone().date().isoformat()
        grouped.setdefault(local_day, []).append(item)

    lines = [
        "# GitHub Activity Digest",
        "",
        "Lifecycle activity for the configured repositories. Generated locally from activity.jsonl.",
        "",
    ]
    if not grouped:
        lines.extend(["No lifecycle events recorded yet.", ""])
    for day, items in grouped.items():
        lines.extend([f"## {day}", ""])
        for item in items:
            kind = "PR" if item.get("pull_request") else "Issue"
            actor = f" by @{item['actor']}" if item.get("actor") else ""
            title = item.get("title", "").replace("[", "\\[").replace("]", "\\]")
            link = item.get("url") or ""
            lines.append(
                f"- **{item['type']}** {kind} [#{item['number']}: {title}]({link}) "
                f"in {item['repo']}{actor}"
            )
        lines.append("")
    DIGEST_FILE.write_text("\n".join(lines), encoding="utf-8")


def save_state(value):
    fd, temporary = tempfile.mkstemp(prefix=".state-", dir=DATA)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2)
            stream.write("\n")
        os.replace(temporary, STATE_FILE)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    if not Path(GH).is_file():
        raise RuntimeError("gh CLI was not found at the configured path")
    repos = read_repositories()
    now = dt.datetime.now(dt.timezone.utc)
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        previous = parse_time(state["last_success_utc"])
        start = previous - OVERLAP
    else:
        start = now - INITIAL_LOOKBACK

    log.info("Collecting lifecycle activity for %d repositories", len(repos))
    collected = []
    for repo in repos:
        log.info("Reading %s", repo)
        collected.extend(collect(repo, start, now))

    known = load_existing_ids()
    new_records = [item for item in collected if item["event_id"] not in known]
    new_records.sort(key=lambda item: (item["timestamp"], item["repo"], item["number"], item["type"]))
    if new_records:
        with ACTIVITY_FILE.open("a", encoding="utf-8") as stream:
            for item in new_records:
                stream.write(json.dumps(item, sort_keys=True, ensure_ascii=False) + "\n")
    write_digest()
    save_state({"last_success_utc": iso_utc(now)})
    log.info("Run completed: %d new lifecycle events", len(new_records))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log.error("Run failed: %s", exc)
        sys.exit(1)
