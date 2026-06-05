"""Activation event ledger for the CyberHuaTuo soul-ring growth loop."""

from __future__ import annotations

import json
import os
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse

from . import __version__

VALID_EVENT_TYPES = {
    "external_return",
    "first_session",
    "first_prescription",
    "repeat_contribution",
    "collaboration",
    "share_attribution",
}
JSONL_READ_ENCODING = "utf-8-sig"

STAGES = [
    ("external_return", "External return"),
    ("first_session", "First-session exposure"),
    ("first_prescription", "First prescription"),
    ("repeat_contribution", "Repeat contribution"),
    ("collaboration", "Collaboration / sect"),
    ("share_attribution", "Public share attribution"),
]


def get_activation_ledger_path() -> Path:
    """Return the local activation ledger path."""
    configured = os.getenv("CYBERHUATUO_ACTIVATION_LEDGER", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".cyberhuatuo" / "activation" / "events.jsonl"


def _clean(value: str | None, default: str = "", max_len: int = 500) -> str:
    text = (value or "").strip()
    if not text:
        return default
    return text[:max_len]


def _normalize_username(username: str | None) -> str:
    return _clean(username, "your-github-username").lstrip("@") or "your-github-username"


def _normalize_framework(framework: str | None) -> str:
    return _clean(framework, "langchain").lower().replace(" ", "-") or "langchain"


def _command_token(value: str | None, default: str) -> str:
    return _clean(value, default).replace(" ", "-") or default


def _clamp_top_n(value: int | str | None, default: int = 10) -> int:
    try:
        size = int(value) if value is not None else default
    except (TypeError, ValueError):
        size = default
    return max(1, min(size, 50))


def _md_cell(value: str | None) -> str:
    text = _clean(value, "-", max_len=300)
    return text.replace("|", "\\|").replace("\n", " ")


def _members_for_command(members: list[str] | tuple[str, ...] | str | None, username: str) -> list[str]:
    if members is None:
        values = [username]
    elif isinstance(members, str):
        values = [part for part in members.replace(",", " ").split() if part]
    else:
        values = [str(part).strip() for part in members if str(part).strip()]
    seen = set()
    normalized = []
    for member in values:
        key = member.lower()
        if key and key not in seen:
            normalized.append(member)
            seen.add(key)
    if username.lower() not in seen:
        normalized.insert(0, username)
    return normalized or [username]


def _is_reviewable_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _share_proof_issue_url(
    username: str = "<github-username>",
    framework: str = "langchain",
    share_url: str = "",
    proof_context: str = "Public share proof for the Soul Ring contribution loop.",
) -> str:
    params = {
        "template": "soul-ring-share-proof.yml",
        "title": f"[Soul Ring Share Proof] {framework} public share proof",
        "github_username": username,
        "framework": framework,
        "proof_context": proof_context,
    }
    if share_url:
        params["share_url"] = share_url
    return f"https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/new?{urlencode(params)}"


def _event_label(event_type: str) -> str:
    if event_type == "share_attribution":
        return "Share attribution"
    return dict(STAGES).get(event_type, event_type.replace("_", " ").title())


def _current_release_tag() -> str:
    return f"v{__version__}"


def _recorded_public_proof_url(event: dict) -> str:
    for field in ("source_url", "share_url"):
        value = _clean(str(event.get(field, "")), max_len=600)
        if _is_reviewable_http_url(value):
            return value
    return "<created public proof URL after submission>"


def _next_external_contributor_invite_lines(event: dict) -> list[str]:
    username = _normalize_username(str(event.get("username", "")))
    framework = _normalize_framework(str(event.get("framework", "")))
    release_tag = _current_release_tag()
    target_contributors = 3
    invitee = "external-contributor-github-username"
    proof_url = _recorded_public_proof_url(event)
    first_invite_command = (
        f"cyberhuatuo first-invite --username {username} --invitee {invitee} "
        f"--framework {framework} --release-tag {release_tag} --target-contributors {target_contributors} "
        f"--source-url {proof_url}"
    )
    proof_pack_command = (
        f"cyberhuatuo proof-pack --username {username} --framework {framework} "
        f"--release-tag {release_tag} --target-contributors {target_contributors}"
    )
    mcp_first_invite = (
        f'first_contributor_invite(github_username="{username}", invitee="{invitee}", '
        f'framework="{framework}", release_tag="{release_tag}", target_contributors={target_contributors}, '
        f'source_url="{proof_url}")'
    )
    mcp_proof_pack = (
        f'first_public_proof_pack(github_username="{username}", framework="{framework}", '
        f'release_tag="{release_tag}", target_contributors={target_contributors})'
    )
    return [
        "## Next External Contributor Invite",
        "",
        "- Route this recorded public proof into one direct outside-contributor invite before opening another report.",
        f"- Recorded proof source for invite: {proof_url}",
        "",
        "### Terminal commands",
        "```bash",
        first_invite_command,
        proof_pack_command,
        "```",
        "",
        "### MCP equivalents for Claude / Codex",
        "```text",
        mcp_first_invite,
        mcp_proof_pack,
        "```",
    ]


def record_activation_event(
    username: str,
    framework: str,
    event_type: str,
    *,
    source_url: str = "",
    surface: str = "",
    share_url: str = "",
    note: str = "",
) -> dict:
    """Append one activation event to the local JSONL ledger."""
    event_type = _clean(event_type)
    if event_type not in VALID_EVENT_TYPES:
        return {
            "ok": False,
            "path": str(get_activation_ledger_path()),
            "error": f"unsupported event_type: {event_type}",
            "event": {},
        }

    source_url = _clean(source_url)
    share_url = _clean(share_url)
    if event_type in {"external_return", "first_session"} and not _is_reviewable_http_url(source_url):
        return {
            "ok": False,
            "path": str(get_activation_ledger_path()),
            "error": "source_url must be a reviewable http(s) URL",
            "event": {},
        }
    if event_type == "share_attribution" and not _is_reviewable_http_url(share_url):
        return {
            "ok": False,
            "path": str(get_activation_ledger_path()),
            "error": "share_url must be a reviewable http(s) URL",
            "event": {},
        }
    if source_url and not _is_reviewable_http_url(source_url):
        return {
            "ok": False,
            "path": str(get_activation_ledger_path()),
            "error": "source_url must be a reviewable http(s) URL",
            "event": {},
        }

    path = get_activation_ledger_path()
    event = {
        "schema_version": 1,
        "event_id": uuid.uuid4().hex,
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "username": _normalize_username(username),
        "framework": _normalize_framework(framework),
        "event_type": event_type,
        "surface": _clean(surface, max_len=200),
        "source_url": source_url,
        "share_url": share_url,
        "note": _clean(note, max_len=1000),
    }

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError as exc:
        return {"ok": False, "path": str(path), "error": str(exc), "event": event}

    return {"ok": True, "path": str(path), "error": "", "event": event}


def load_activation_events(username: str = "", framework: str = "", path: Path | None = None) -> tuple[list[dict], list[str]]:
    """Load activation events, returning parse or access warnings separately."""
    ledger_path = path or get_activation_ledger_path()
    target_username = _normalize_username(username).lower() if username else ""
    target_framework = _normalize_framework(framework) if framework else ""
    warnings: list[str] = []
    events: list[dict] = []

    if not ledger_path.exists():
        return [], [f"activation ledger missing: {ledger_path}"]

    try:
        lines = ledger_path.read_text(encoding=JSONL_READ_ENCODING).splitlines()
    except OSError as exc:
        return [], [f"activation ledger unreadable: {ledger_path}: {exc}"]

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            warnings.append(f"line {line_number} is not valid JSON: {exc.msg}")
            continue
        if event.get("event_type") not in VALID_EVENT_TYPES:
            warnings.append(f"line {line_number} has unsupported event_type")
            continue
        if target_username and str(event.get("username", "")).lower() != target_username:
            continue
        if target_framework and str(event.get("framework", "")).lower() != target_framework:
            continue
        events.append(event)

    return events, warnings


def _stage_evidence(events: list[dict]) -> str:
    if not events:
        return "missing in ledger"
    latest = sorted(events, key=lambda event: str(event.get("timestamp_utc", "")))[-1]
    if latest.get("share_url"):
        return f"latest share URL: {latest['share_url']}"
    if latest.get("source_url"):
        return f"latest source URL: {latest['source_url']}"
    if latest.get("surface"):
        return f"latest surface: {latest['surface']}"
    return "recorded in ledger"


def build_activation_funnel(
    username: str = "",
    framework: str = "",
    sect_name: str = "CyberHuaTuo Sect",
    members: list[str] | tuple[str, ...] | str | None = None,
    top_n: int = 10,
) -> dict:
    """Build a funnel snapshot from local activation events."""
    user = _normalize_username(username)
    target_framework = _normalize_framework(framework)
    try:
        board_size = _clamp_top_n(top_n)
    except (TypeError, ValueError):
        board_size = 10

    events, warnings = load_activation_events(user, target_framework)
    counts = Counter(event["event_type"] for event in events)
    stage_events = {
        event_type: [event for event in events if event.get("event_type") == event_type]
        for event_type, _label in STAGES
    }

    weakest = ""
    if not events:
        weakest = "External return"
    else:
        previous_count = None
        for event_type, label in STAGES:
            count = counts.get(event_type, 0)
            if count == 0 and (previous_count is None or previous_count > 0):
                weakest = label
                break
            previous_count = count
        if not weakest:
            weakest = min(STAGES, key=lambda item: counts.get(item[0], 0))[1]

    sect_command = _command_token(sect_name, "CyberHuaTuo-Sect")
    member_args = " ".join(_members_for_command(members, user))
    commands = {
        "external_return": (
            f"cyberhuatuo record-return --username {user} --framework {target_framework} "
            '--surface "PyPI / Claude / Codex launch" --source-url <https-url>'
        ),
        "first_session": (
            f"cyberhuatuo record-session --username {user} --framework {target_framework} "
            '--surface "First agent session" --source-url <https-url>'
        ),
        "first_prescription": f"cyberhuatuo challenge --username {user} --framework {target_framework}",
        "repeat_contribution": f"cyberhuatuo quest {user} --framework {target_framework}",
        "collaboration": f"cyberhuatuo sect-arena --sect {sect_command} {member_args} --framework {target_framework}",
        "share_attribution": f"cyberhuatuo record-share --username {user} --framework {target_framework} --share-url <https-url>",
    }

    rows = []
    for event_type, label in STAGES:
        rows.append({
            "event_type": event_type,
            "label": label,
            "count": counts.get(event_type, 0),
            "evidence": _stage_evidence(stage_events[event_type]),
            "next_command": commands[event_type],
        })

    return {
        "username": user,
        "framework": target_framework,
        "sect_name": sect_command,
        "members": member_args,
        "top_n": board_size,
        "path": str(get_activation_ledger_path()),
        "events": events,
        "warnings": warnings,
        "rows": rows,
        "weakest_stage": weakest,
        "flywheel_command": (
            f"cyberhuatuo flywheel --username {user} --framework {target_framework} "
            f"--sect {sect_command} --members {member_args} --top-n {board_size}"
        ),
    }


def build_share_attribution_report(
    username: str = "",
    framework: str = "",
    top_n: int = 10,
) -> dict:
    """Build a public share-attribution report from local activation events."""
    user = _normalize_username(username)
    target_framework = _normalize_framework(framework)
    board_size = _clamp_top_n(top_n)

    events, warnings = load_activation_events(user, target_framework)
    share_events = [
        event
        for event in events
        if event.get("event_type") == "share_attribution"
    ]
    share_events = sorted(
        share_events,
        key=lambda event: str(event.get("timestamp_utc", "")),
        reverse=True,
    )
    source_urls = {
        str(event.get("source_url", "")).strip()
        for event in events
        if event.get("event_type") in {"external_return", "first_session"}
        and str(event.get("source_url", "")).strip()
    }
    share_events_with_source = [
        event for event in share_events if str(event.get("source_url", "")).strip()
    ]
    bridged_events = [
        event
        for event in share_events_with_source
        if str(event.get("source_url", "")).strip() in source_urls
    ]

    actor_counts = Counter(str(event.get("username", user)) or user for event in share_events)
    surface_counts = Counter(_clean(str(event.get("surface", "")), "unspecified") for event in share_events)
    artifact_counts = Counter(str(event.get("share_url", "")).strip() for event in share_events)

    record_share_command = (
        f"cyberhuatuo record-share --username {user} --framework {target_framework} "
        "--share-url <https-url>"
    )
    record_share_bridge_command = f"{record_share_command} --source-url <https-url>"
    record_return_command = (
        f"cyberhuatuo record-return --username {user} --framework {target_framework} "
        '--surface "Share source" --source-url <https-url>'
    )
    activation_command = f"cyberhuatuo activation --username {user} --framework {target_framework}"
    flywheel_command = f"cyberhuatuo flywheel --username {user} --framework {target_framework}"
    report_command = f"cyberhuatuo share-report --username {user} --framework {target_framework} --top-n {board_size}"
    leaderboard_command = f"cyberhuatuo share-leaderboard --framework {target_framework} --top-n {board_size}"

    if not share_events:
        bottleneck = "No public share proof recorded"
        next_command = record_share_command
    elif len(share_events_with_source) < len(share_events):
        bottleneck = "Source-to-share bridge missing"
        next_command = record_share_bridge_command
    elif len(bridged_events) < len(share_events_with_source):
        bottleneck = "Source bridge not yet recorded as external return"
        next_command = record_return_command
    else:
        bottleneck = "First-session / contribution proof needs activation funnel"
        next_command = activation_command

    return {
        "username": user,
        "framework": target_framework,
        "top_n": board_size,
        "path": str(get_activation_ledger_path()),
        "warnings": warnings,
        "events": events,
        "share_events": share_events,
        "share_events_with_source": share_events_with_source,
        "bridged_events": bridged_events,
        "actor_counts": actor_counts,
        "surface_counts": surface_counts,
        "artifact_counts": artifact_counts,
        "bottleneck": bottleneck,
        "next_command": next_command,
        "commands": {
            "record_share": record_share_command,
            "record_share_bridge": record_share_bridge_command,
            "record_return": record_return_command,
            "activation": activation_command,
            "flywheel": flywheel_command,
            "report": report_command,
            "leaderboard": leaderboard_command,
        },
        "share_proof_issue_url": _share_proof_issue_url(user, target_framework),
    }


def build_share_proof_leaderboard(
    framework: str = "",
    top_n: int = 10,
) -> dict:
    """Build a leaderboard from reviewable public share-attribution events."""
    target_framework = _normalize_framework(framework)
    board_size = _clamp_top_n(top_n)

    events, warnings = load_activation_events("", target_framework)
    share_events = [
        event
        for event in events
        if event.get("event_type") == "share_attribution"
        and _is_reviewable_http_url(str(event.get("share_url", "")).strip())
    ]
    share_events = sorted(
        share_events,
        key=lambda event: str(event.get("timestamp_utc", "")),
        reverse=True,
    )

    proof_urls_by_actor: dict[str, set[str]] = {}
    proof_events_by_actor: dict[str, list[dict]] = {}
    for event in share_events:
        username = _normalize_username(str(event.get("username", "")))
        share_url = str(event.get("share_url", "")).strip()
        proof_urls_by_actor.setdefault(username, set()).add(share_url)
        proof_events_by_actor.setdefault(username, []).append(event)

    rows = []
    for username, proof_urls in proof_urls_by_actor.items():
        actor_events = proof_events_by_actor.get(username, [])
        latest_event = actor_events[0] if actor_events else {}
        rows.append({
            "username": username,
            "score": len(proof_urls),
            "event_count": len(actor_events),
            "proof_urls": sorted(proof_urls),
            "latest_share_url": str(latest_event.get("share_url", "")).strip(),
            "latest_surface": _clean(str(latest_event.get("surface", "")), "unspecified"),
            "latest_timestamp": str(latest_event.get("timestamp_utc", "")).strip(),
        })
    rows.sort(key=lambda row: (-int(row["score"]), str(row["username"]).lower()))
    rows = rows[:board_size]

    return {
        "framework": target_framework,
        "top_n": board_size,
        "path": str(get_activation_ledger_path()),
        "warnings": warnings,
        "events": events,
        "share_events": share_events,
        "rows": rows,
        "unique_share_url_count": sum(len(urls) for urls in proof_urls_by_actor.values()),
        "commands": {
            "record_share": (
                f"cyberhuatuo record-share --username <github-username> --framework {target_framework} "
                "--share-url <https-url>"
            ),
            "share_report": (
                f"cyberhuatuo share-report --username <github-username> --framework {target_framework} "
                f"--top-n {board_size}"
            ),
            "leaderboard": f"cyberhuatuo share-leaderboard --framework {target_framework} --top-n {board_size}",
        },
        "share_proof_issue_url": _share_proof_issue_url("<github-username>", target_framework),
    }


def _format_counter(counter: Counter, empty: str, top_n: int, *, prefix_at: bool = False) -> list[str]:
    if not counter:
        return [f"- {empty}"]
    rows = []
    for key, count in counter.most_common(top_n):
        label = f"@{key}" if prefix_at else key
        rows.append(f"- {label}: {count} share proof event(s)")
    return rows


def format_share_attribution_report(
    username: str = "",
    framework: str = "",
    top_n: int = 10,
) -> str:
    """Return a markdown share-attribution report from the local ledger."""
    report = build_share_attribution_report(username, framework, top_n)
    proof_rows = [
        "| Share URL | Source URL | Surface | Timestamp | Event ID |",
        "|---|---|---|---|---|",
    ]
    for event in report["share_events"][: report["top_n"]]:
        proof_rows.append(
            "| "
            f"{_md_cell(event.get('share_url'))} | "
            f"{_md_cell(event.get('source_url'))} | "
            f"{_md_cell(event.get('surface'))} | "
            f"{_md_cell(event.get('timestamp_utc'))} | "
            f"{_md_cell(event.get('event_id'))} |"
        )
    if len(proof_rows) == 2:
        proof_rows.append("| No share proof recorded | - | - | - | - |")

    warnings = report["warnings"] or ["ledger readable"]
    commands = report["commands"]
    source_count = len(report["share_events_with_source"])
    bridged_count = len(report["bridged_events"])
    command_lines = []
    for command in (
        report["next_command"],
        commands["record_share"],
        commands["record_share_bridge"],
        commands["report"],
        commands["leaderboard"],
        commands["activation"],
        commands["flywheel"],
    ):
        if command not in command_lines:
            command_lines.append(command)

    return "\n".join([
        "# Soul Ring Share Attribution Report",
        "",
        f"- GitHub: @{report['username']}",
        f"- Target Framework: `{report['framework']}`",
        f"- Ledger: `{report['path']}`",
        f"- Share proof events: {len(report['share_events'])}",
        f"- Source-to-share bridges: {bridged_count} / {source_count}",
        f"- Current Proof Bottleneck: {report['bottleneck']}",
        "- No downloads, retention, repost counts, referral conversions, or rewards are invented.",
        "",
        "## Contribution Pull",
        f"- Public share proofs recorded for this contributor/framework: {len(report['share_events'])}",
        f"- Share proofs with a source URL: {source_count}",
        f"- Share proofs whose source is also recorded as external return/session: {bridged_count}",
        "",
        "## Proof URLs",
        *proof_rows,
        "",
        "## Source-To-Share Bridges",
        f"- Share events with source URL: {source_count}",
        f"- Share events with source URL already recorded as external return/session: {bridged_count}",
        f"- Missing source bridge count: {max(0, len(report['share_events']) - bridged_count)}",
        "",
        "## Actor Pull",
        *_format_counter(report["actor_counts"], "No actor has public share proof yet.", report["top_n"], prefix_at=True),
        "",
        "## Artifact Pull",
        *_format_counter(report["surface_counts"], "No share surface has proof yet.", report["top_n"]),
        "",
        "## Proof Artifact URLs",
        *_format_counter(report["artifact_counts"], "No public share URL has been recorded yet.", report["top_n"]),
        "",
        "## Ledger Health",
        *[f"- {warning}" for warning in warnings],
        "",
        "## Public Share Proof Issue",
        f"- Prefilled Share Proof Issue: {report['share_proof_issue_url']}",
        "",
        "## Next Proof Commands",
        "```bash",
        *command_lines,
        "```",
    ])


def format_share_proof_leaderboard(
    framework: str = "",
    top_n: int = 10,
) -> str:
    """Return a markdown share-proof leaderboard from the local ledger."""
    leaderboard = build_share_proof_leaderboard(framework, top_n)
    commands = leaderboard["commands"]
    rows = [
        "| Rank | Actor | Share Proof Score | Reviewable URLs | Latest Proof URL | Next Command |",
        "|---:|---|---:|---|---|---|",
    ]
    for rank, row in enumerate(leaderboard["rows"], start=1):
        proof_urls = "<br>".join(_md_cell(url) for url in row["proof_urls"][:3])
        if len(row["proof_urls"]) > 3:
            proof_urls += f"<br>+{len(row['proof_urls']) - 3} more"
        rows.append(
            f"| {rank} | @{_md_cell(row['username'])} | {row['score']} | "
            f"{proof_urls or '-'} | {_md_cell(row['latest_share_url'])} | "
            f"`cyberhuatuo share-report --username {row['username']} --framework {leaderboard['framework']} --top-n {leaderboard['top_n']}` |"
        )
    if len(rows) == 2:
        rows.append("| - | No public share proof recorded yet | 0 | - | - | `" + commands["record_share"] + "` |")

    warnings = leaderboard["warnings"] or ["ledger readable"]
    empty_note = []
    if not leaderboard["share_events"]:
        empty_note = [
            "",
            "## Empty-State Rule",
            "- No public share proof recorded yet; a missing ledger is not treated as proven zero propagation.",
        ]

    return "\n".join([
        "# Soul Ring Share Proof Leaderboard",
        "",
        f"- Target Framework: `{leaderboard['framework']}`",
        f"- Ledger: `{leaderboard['path']}`",
        f"- Share proof events: {len(leaderboard['share_events'])}",
        f"- Reviewable unique share URLs: {leaderboard['unique_share_url_count']}",
        "- Scoring Formula: share proof score = count of unique reviewable public http(s) share URLs recorded as share_attribution events.",
        "- Duplicate URLs count once per actor.",
        "- No downloads, retention, repost counts, referral conversions, rewards, or Spirit Power are invented.",
        "",
        "## Leaderboard",
        *rows,
        "",
        "## Ledger Health",
        *[f"- {warning}" for warning in warnings],
        "",
        "## Public Share Proof Issue",
        f"- Prefilled Share Proof Issue: {leaderboard['share_proof_issue_url']}",
        *empty_note,
        "",
        "## Proof Commands",
        "```bash",
        commands["record_share"],
        commands["share_report"],
        commands["leaderboard"],
        "```",
    ])


def format_activation_funnel(
    username: str = "",
    framework: str = "",
    sect_name: str = "CyberHuaTuo Sect",
    members: list[str] | tuple[str, ...] | str | None = None,
    top_n: int = 10,
) -> str:
    """Return a markdown activation funnel report from the local ledger."""
    funnel = build_activation_funnel(username, framework, sect_name, members, top_n)
    market_ready_command = (
        f"cyberhuatuo market-ready --remote --strict-remote --username {funnel['username']} "
        f"--framework {funnel['framework']} --release-tag <tag> --target-contributors 3"
    )
    proof_pack_command = (
        f"cyberhuatuo proof-pack --username {funnel['username']} --framework {funnel['framework']} "
        "--release-tag <tag> --target-contributors 3"
    )
    rows = [
        "| Stage | Real Events | Conversion Evidence | Next Command |",
        "|---|---:|---|---|",
    ]
    for row in funnel["rows"]:
        rows.append(
            f"| {row['label']} | {row['count']} | {row['evidence']} | `{row['next_command']}` |"
        )

    warnings = funnel["warnings"] or ["ledger readable"]
    return "\n".join([
        "# Soul Ring Activation Funnel",
        "",
        f"- GitHub: @{funnel['username']}",
        f"- Target Framework: `{funnel['framework']}`",
        f"- Ledger: `{funnel['path']}`",
        "- Event Formula: local JSONL events recorded by CyberHuaTuo activation tools; no external analytics are backfilled.",
        "- First-session exposure is tracked separately from first prescription, repeat contribution, collaboration, and sharing.",
        f"- Weakest Conversion Stage: {funnel['weakest_stage']}",
        "- No downloads, retention, or attribution metrics are invented.",
        "",
        "## Funnel Stages",
        *rows,
        "",
        "## Ledger Health",
        *[f"- {warning}" for warning in warnings],
        "",
        "## Launch Closure Checklist",
        "- Run the marketplace preflight before claiming PyPI / Claude / Codex launch readiness.",
        "```bash",
        proof_pack_command,
        market_ready_command,
        "```",
        "",
        "## Return To Flywheel",
        "```bash",
        funnel["flywheel_command"],
        "```",
    ])


def _format_record_result(result: dict, event_type: str) -> str:
    label = _event_label(event_type)
    if not result.get("ok"):
        return "\n".join([
            f"# Soul Ring {label} Event",
            "",
            f"- {label} not recorded: {result.get('error', 'unknown write failure')}",
            f"- Ledger: `{result.get('path', get_activation_ledger_path())}`",
            "- No activation, attribution, downloads, or retention metrics are invented.",
        ])

    event = result["event"]
    lines = [
        f"# Soul Ring {label} Event",
        "",
        f"- {label} recorded",
        f"- Ledger: `{result['path']}`",
        f"- Event ID: `{event['event_id']}`",
        f"- GitHub: @{event['username']}",
        f"- Framework: `{event['framework']}`",
    ]
    if event.get("surface"):
        lines.append(f"- Surface: {event['surface']}")
    if event.get("source_url"):
        lines.append(f"- Source URL: {event['source_url']}")
    if event.get("share_url"):
        lines.append(f"- Share URL: {event['share_url']}")
    lines.extend([
        "",
        *_next_external_contributor_invite_lines(event),
        "",
        "## Reports And Rechecks",
        "```bash",
        f"cyberhuatuo proof-pack --username {event['username']} --framework {event['framework']} --release-tag <tag> --target-contributors 3",
        f"cyberhuatuo market-ready --remote --strict-remote --username {event['username']} --framework {event['framework']} --release-tag <tag> --target-contributors 3",
        f"cyberhuatuo activation --username {event['username']} --framework {event['framework']}",
        f"cyberhuatuo flywheel --username {event['username']} --framework {event['framework']}",
        "```",
        "",
        "Launch Closure Checklist must pass before this recorded return is treated as a market-ready loop.",
        "",
        "No downloads, retention, or attribution metrics are invented.",
    ])
    return "\n".join(lines)


def format_record_external_return(
    username: str,
    framework: str,
    surface: str,
    source_url: str,
    note: str = "",
) -> str:
    result = record_activation_event(
        username,
        framework,
        "external_return",
        surface=surface,
        source_url=source_url,
        note=note,
    )
    return _format_record_result(result, "external_return")


def format_record_first_session(
    username: str,
    framework: str,
    surface: str,
    source_url: str,
    note: str = "",
) -> str:
    result = record_activation_event(
        username,
        framework,
        "first_session",
        surface=surface,
        source_url=source_url,
        note=note,
    )
    return _format_record_result(result, "first_session")


def format_record_share_attribution(
    username: str,
    framework: str,
    share_url: str,
    *,
    source_url: str = "",
    surface: str = "Public share",
    note: str = "",
) -> str:
    result = record_activation_event(
        username,
        framework,
        "share_attribution",
        surface=surface,
        source_url=source_url,
        share_url=share_url,
        note=note,
    )
    return _format_record_result(result, "share_attribution")
