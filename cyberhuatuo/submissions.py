"""Marketplace submission evidence ledger for CyberHuaTuo."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from . import __version__
from .traction import DEFAULT_PYPI_PROJECT, DEFAULT_REPO

REQUIRED_CHANNELS = ("pypi", "claude-code", "claude-desktop", "codex", "github-release")
VALID_CHANNELS = (*REQUIRED_CHANNELS, "agent-marketplace", "other")
VALID_STATUSES = ("submitted", "pending", "needs-review", "approved", "published", "rejected", "blocked")
COMPLETE_STATUSES = {"approved", "published"}
JSONL_READ_ENCODING = "utf-8-sig"

NON_FABRICATION_NOTICE = (
    "No downloads, retention, repost counts, referrals, rewards, reviews, or fake contributors are invented."
)


def get_marketplace_submission_ledger_path() -> Path:
    """Return the local append-only marketplace submission ledger path."""
    configured = os.getenv("CYBERHUATUO_MARKETPLACE_SUBMISSION_LEDGER", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".cyberhuatuo" / "marketplace" / "submissions.jsonl"


def _clean(value: str | None, default: str = "", max_len: int = 500) -> str:
    text = (value or "").strip()
    return (text or default)[:max_len]


def _normalize_username(username: str | None) -> str:
    return _clean(username, "your-github-username").lstrip("@") or "your-github-username"


def _normalize_framework(framework: str | None) -> str:
    return _clean(framework, "langchain").lower().replace(" ", "-") or "langchain"


def _normalize_release_tag(release_tag: str | None) -> str:
    return _clean(release_tag, f"v{__version__}") or f"v{__version__}"


def _normalize_repo(repo: str | None) -> str:
    slug = _clean(repo, DEFAULT_REPO).strip("/")
    parts = [part for part in slug.split("/") if part]
    if len(parts) != 2:
        return DEFAULT_REPO
    return f"{parts[0]}/{parts[1]}"


def _normalize_channel(channel: str | None) -> str:
    return _clean(channel, "").lower().replace("_", "-").replace(" ", "-")


def _normalize_status(status: str | None) -> str:
    return _clean(status, "").lower().replace("_", "-").replace(" ", "-")


def _is_reviewable_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _md_cell(value: str | None) -> str:
    text = _clean(value, "-", max_len=400)
    return text.replace("|", "\\|").replace("\n", " ")


def _record_market_command(
    username: str,
    framework: str,
    channel: str,
    release_tag: str,
    repo: str,
    pypi_project: str,
) -> str:
    return (
        f"cyberhuatuo record-market --username {username} --framework {framework} "
        f"--channel {channel} --status submitted --submission-url <reviewable public URL> "
        f"--release-tag {release_tag} --repo {repo} --pypi-project {pypi_project}"
    )


def _market_status_command(username: str, framework: str, release_tag: str, repo: str, pypi_project: str) -> str:
    return (
        f"cyberhuatuo market-status --username {username} --framework {framework} "
        f"--release-tag {release_tag} --repo {repo} --pypi-project {pypi_project}"
    )


def _market_copy_command(username: str, framework: str, release_tag: str, repo: str, pypi_project: str) -> str:
    return (
        f"cyberhuatuo market-copy --username {username} --framework {framework} "
        f"--release-tag {release_tag} --target-contributors 3 --repo {repo} --pypi-project {pypi_project}"
    )


def _traction_command(username: str, framework: str, release_tag: str, repo: str, pypi_project: str) -> str:
    return (
        f"cyberhuatuo traction-proof --username {username} --framework {framework} "
        f"--release-tag {release_tag} --target-contributors 3 --repo {repo} --pypi-project {pypi_project}"
    )


def record_marketplace_submission(
    *,
    username: str = "your-github-username",
    framework: str = "langchain",
    channel: str,
    status: str,
    submission_url: str,
    release_tag: str = "",
    repo: str = DEFAULT_REPO,
    pypi_project: str = DEFAULT_PYPI_PROJECT,
    note: str = "",
) -> dict[str, Any]:
    """Append one marketplace submission proof event to the local JSONL ledger."""
    clean_username = _normalize_username(username)
    clean_framework = _normalize_framework(framework)
    clean_channel = _normalize_channel(channel)
    clean_status = _normalize_status(status)
    clean_release = _normalize_release_tag(release_tag)
    clean_repo = _normalize_repo(repo)
    clean_project = _clean(pypi_project, DEFAULT_PYPI_PROJECT)
    clean_url = _clean(submission_url, max_len=1000)
    ledger_path = get_marketplace_submission_ledger_path()

    if clean_channel not in VALID_CHANNELS:
        return {
            "ok": False,
            "path": str(ledger_path),
            "error": f"channel must be one of: {', '.join(VALID_CHANNELS)}",
            "event": {},
        }
    if clean_status not in VALID_STATUSES:
        return {
            "ok": False,
            "path": str(ledger_path),
            "error": f"status must be one of: {', '.join(VALID_STATUSES)}",
            "event": {},
        }
    if not _is_reviewable_http_url(clean_url):
        return {
            "ok": False,
            "path": str(ledger_path),
            "error": "submission_url must be a reviewable public URL using http(s)",
            "event": {},
        }

    event = {
        "schema_version": 1,
        "event_id": uuid.uuid4().hex,
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "username": clean_username,
        "framework": clean_framework,
        "channel": clean_channel,
        "status": clean_status,
        "submission_url": clean_url,
        "release_tag": clean_release,
        "repo": clean_repo,
        "pypi_project": clean_project,
        "note": _clean(note, max_len=1000),
    }

    try:
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with ledger_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError as exc:
        return {"ok": False, "path": str(ledger_path), "error": str(exc), "event": event}

    return {"ok": True, "path": str(ledger_path), "error": "", "event": event}


def load_marketplace_submission_events(
    *,
    username: str = "",
    framework: str = "",
    release_tag: str = "",
    repo: str = "",
    pypi_project: str = "",
    path: Path | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Load marketplace submission events, returning parse/access warnings separately."""
    ledger_path = path or get_marketplace_submission_ledger_path()
    target_username = _normalize_username(username).lower() if username else ""
    target_framework = _normalize_framework(framework) if framework else ""
    target_release = _normalize_release_tag(release_tag) if release_tag else ""
    target_repo = _normalize_repo(repo).lower() if repo else ""
    target_project = _clean(pypi_project, DEFAULT_PYPI_PROJECT).lower() if pypi_project else ""
    warnings: list[str] = []
    events: list[dict[str, Any]] = []

    if not ledger_path.exists():
        return [], [f"marketplace submission ledger missing: {ledger_path}"]

    try:
        lines = ledger_path.read_text(encoding=JSONL_READ_ENCODING).splitlines()
    except OSError as exc:
        return [], [f"marketplace submission ledger unreadable: {ledger_path}: {exc}"]

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            warnings.append(f"line {line_number} is not valid JSON: {exc.msg}")
            continue

        channel = _normalize_channel(str(event.get("channel", "")))
        status = _normalize_status(str(event.get("status", "")))
        if channel not in VALID_CHANNELS:
            warnings.append(f"line {line_number} has unsupported channel")
            continue
        if status not in VALID_STATUSES:
            warnings.append(f"line {line_number} has unsupported status")
            continue
        if not _is_reviewable_http_url(str(event.get("submission_url", ""))):
            warnings.append(f"line {line_number} has non-reviewable submission_url")
            continue
        if target_username and str(event.get("username", "")).lower() != target_username:
            continue
        if target_framework and str(event.get("framework", "")).lower() != target_framework:
            continue
        if target_release and str(event.get("release_tag", "")) != target_release:
            continue
        if target_repo and str(event.get("repo", "")).lower() != target_repo:
            continue
        if target_project and str(event.get("pypi_project", "")).lower() != target_project:
            continue
        events.append(event)

    return events, warnings


def build_marketplace_submission_status(
    *,
    username: str = "your-github-username",
    framework: str = "langchain",
    release_tag: str = "",
    repo: str = DEFAULT_REPO,
    pypi_project: str = DEFAULT_PYPI_PROJECT,
) -> dict[str, Any]:
    """Build a marketplace submission status report from the local ledger."""
    clean_username = _normalize_username(username)
    clean_framework = _normalize_framework(framework)
    clean_release = _normalize_release_tag(release_tag)
    clean_repo = _normalize_repo(repo)
    clean_project = _clean(pypi_project, DEFAULT_PYPI_PROJECT)
    events, warnings = load_marketplace_submission_events(
        username=clean_username,
        framework=clean_framework,
        release_tag=clean_release,
        repo=clean_repo,
        pypi_project=clean_project,
    )

    latest_by_channel: dict[str, dict[str, Any]] = {}
    for event in sorted(events, key=lambda row: str(row.get("timestamp_utc", ""))):
        latest_by_channel[str(event["channel"])] = event

    rows: list[dict[str, str]] = []
    for channel in REQUIRED_CHANNELS:
        event = latest_by_channel.get(channel)
        if event is None:
            rows.append(
                {
                    "channel": channel,
                    "status": "missing",
                    "evidence_url": "-",
                    "timestamp_utc": "-",
                    "next_command": _record_market_command(
                        clean_username,
                        clean_framework,
                        channel,
                        clean_release,
                        clean_repo,
                        clean_project,
                    ),
                }
            )
            continue
        status = str(event.get("status", "missing"))
        rows.append(
            {
                "channel": channel,
                "status": status,
                "evidence_url": str(event.get("submission_url", "-")),
                "timestamp_utc": str(event.get("timestamp_utc", "-")),
                "next_command": (
                    "Recheck approval/published state only from the same public channel."
                    if status in COMPLETE_STATUSES
                    else _record_market_command(clean_username, clean_framework, channel, clean_release, clean_repo, clean_project)
                ),
            }
        )

    complete_count = sum(1 for row in rows if row["status"] in COMPLETE_STATUSES)
    return {
        "title": "Marketplace Submission Ledger",
        "ledger_path": str(get_marketplace_submission_ledger_path()),
        "username": clean_username,
        "framework": clean_framework,
        "release_tag": clean_release,
        "repo": clean_repo,
        "pypi_project": clean_project,
        "events": events,
        "warnings": warnings,
        "rows": rows,
        "event_count": len(events),
        "required_channel_count": len(REQUIRED_CHANNELS),
        "approved_or_published_count": complete_count,
        "missing_channels": [row["channel"] for row in rows if row["status"] == "missing"],
        "status_command": _market_status_command(clean_username, clean_framework, clean_release, clean_repo, clean_project),
        "market_copy_command": _market_copy_command(clean_username, clean_framework, clean_release, clean_repo, clean_project),
        "traction_command": _traction_command(clean_username, clean_framework, clean_release, clean_repo, clean_project),
        "non_fabrication_notice": NON_FABRICATION_NOTICE,
    }


def format_record_marketplace_submission(
    *,
    username: str = "your-github-username",
    framework: str = "langchain",
    channel: str,
    status: str,
    submission_url: str,
    release_tag: str = "",
    repo: str = DEFAULT_REPO,
    pypi_project: str = DEFAULT_PYPI_PROJECT,
    note: str = "",
) -> str:
    """Record and format one marketplace submission proof event."""
    result = record_marketplace_submission(
        username=username,
        framework=framework,
        channel=channel,
        status=status,
        submission_url=submission_url,
        release_tag=release_tag,
        repo=repo,
        pypi_project=pypi_project,
        note=note,
    )
    if not result["ok"]:
        return "\n".join(
            [
                "# Marketplace Submission Not Recorded",
                "",
                f"- Marketplace submission not recorded: {result['error']}.",
                f"- Ledger: `{result['path']}`",
                "- Required: channel, status, release tag, and a reviewable public URL using http(s).",
                f"- Supported channels: {', '.join(VALID_CHANNELS)}",
                f"- Supported statuses: {', '.join(VALID_STATUSES)}",
                f"- {NON_FABRICATION_NOTICE}",
            ]
        )

    event = result["event"]
    status_command = _market_status_command(
        event["username"], event["framework"], event["release_tag"], event["repo"], event["pypi_project"]
    )
    market_copy_command = _market_copy_command(
        event["username"], event["framework"], event["release_tag"], event["repo"], event["pypi_project"]
    )
    traction_snapshot_command = (
        f"cyberhuatuo traction-proof --username {event['username']} --framework {event['framework']} "
        f"--release-tag {event['release_tag']} --target-contributors 3 --record-snapshot "
        f"--repo {event['repo']} --pypi-project {event['pypi_project']}"
    )
    return "\n".join(
        [
            "# Marketplace Submission Recorded",
            "",
            "- Marketplace submission recorded: yes",
            f"- Ledger: `{result['path']}`",
            f"- Channel: {event['channel']}",
            f"- Status: {event['status']}",
            f"- Evidence URL: {event['submission_url']}",
            f"- Release tag: `{event['release_tag']}`",
            "- This records submission evidence only; it does not claim approval unless the recorded status is approved or published.",
            "",
            "## Next Commands",
            "```bash",
            status_command,
            market_copy_command,
            traction_snapshot_command,
            "```",
            "",
            f"- {NON_FABRICATION_NOTICE}",
        ]
    )


def format_marketplace_submission_status(
    *,
    username: str = "your-github-username",
    framework: str = "langchain",
    release_tag: str = "",
    repo: str = DEFAULT_REPO,
    pypi_project: str = DEFAULT_PYPI_PROJECT,
) -> str:
    """Format the current marketplace submission status report."""
    report = build_marketplace_submission_status(
        username=username,
        framework=framework,
        release_tag=release_tag,
        repo=repo,
        pypi_project=pypi_project,
    )
    lines = [
        "# Marketplace Submission Ledger",
        "",
        f"- Ledger: `{report['ledger_path']}`",
        f"- Repository: `{report['repo']}`",
        f"- PyPI project: `{report['pypi_project']}`",
        f"- Release tag: `{report['release_tag']}`",
        f"- Username / framework: @{report['username']} / `{report['framework']}`",
        f"- Approved or published channels: {report['approved_or_published_count']} / {report['required_channel_count']}",
        f"- Event count: {report['event_count']}",
        "- This ledger records reviewable public URL evidence only; missing rows are not treated as proof of rejection.",
        f"- {report['non_fabrication_notice']}",
    ]
    if report["warnings"]:
        lines.extend(["", "## Ledger Warnings"])
        lines.extend(f"- {warning}" for warning in report["warnings"])

    lines.extend(
        [
            "",
            "## Channel Status",
            "",
            "| Channel | Latest status | Evidence URL | Timestamp | Next command |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in report["rows"]:
        lines.append(
            f"| {_md_cell(row['channel'])} | {_md_cell(row['status'])} | {_md_cell(row['evidence_url'])} | "
            f"{_md_cell(row['timestamp_utc'])} | `{_md_cell(row['next_command'])}` |"
        )

    lines.extend(
        [
            "",
            "## Next Commands",
            "```bash",
            report["status_command"],
            report["market_copy_command"],
            report["traction_command"],
            "```",
        ]
    )
    if report["missing_channels"]:
        lines.extend(["", "## Missing Channels"])
        lines.extend(
            f"- {channel}: run `{_record_market_command(report['username'], report['framework'], channel, report['release_tag'], report['repo'], report['pypi_project'])}`"
            for channel in report["missing_channels"]
        )
    return "\n".join(lines)
