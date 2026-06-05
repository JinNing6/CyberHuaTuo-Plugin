"""Public traction proof for the CyberHuaTuo soul-ring launch loop."""

from __future__ import annotations

import json
import os
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from packaging.version import InvalidVersion, Version

from . import __version__
from .activation import load_activation_events

DEFAULT_REPO = "JinNing6/CyberHuaTuo-Plugin"
DEFAULT_PYPI_PROJECT = "cyberhuatuo"
ISSUE_LABELS = (
    "soul-ring",
    "accepted-prescription",
    "soul-ring-share-proof",
    "soul-ring-launch-campaign",
)
JSONL_READ_ENCODING = "utf-8-sig"
ISSUEOPS_REQUIRED_FILES = (
    ("First Soul Ring Prescription Issue Form", ".github/ISSUE_TEMPLATE/soul-ring-prescription.yml"),
    ("First Soul Ring comment workflow", ".github/workflows/soul-ring-issue.yml"),
    ("Growth Flywheel Issue Form", ".github/ISSUE_TEMPLATE/soul-ring-growth-flywheel.yml"),
    ("Growth Flywheel comment workflow", ".github/workflows/soul-ring-growth-flywheel.yml"),
    ("Bounty Board Issue Form", ".github/ISSUE_TEMPLATE/soul-ring-bounty-board.yml"),
    ("Bounty Board comment workflow", ".github/workflows/soul-ring-bounty-board.yml"),
    ("Share Proof Issue Form", ".github/ISSUE_TEMPLATE/soul-ring-share-proof.yml"),
    ("Share Proof comment workflow", ".github/workflows/soul-ring-share-proof.yml"),
    ("Launch Campaign Issue Form", ".github/ISSUE_TEMPLATE/soul-ring-launch-campaign.yml"),
    ("Launch Campaign comment workflow", ".github/workflows/soul-ring-launch-campaign.yml"),
    ("Tournament Cup Issue Form", ".github/ISSUE_TEMPLATE/soul-ring-tournament.yml"),
    ("Tournament Cup comment workflow", ".github/workflows/soul-ring-tournament.yml"),
    ("Mentor Pact Issue Form", ".github/ISSUE_TEMPLATE/soul-ring-mentor.yml"),
    ("Mentor Pact comment workflow", ".github/workflows/soul-ring-mentor.yml"),
    ("Sect Recruitment Issue Form", ".github/ISSUE_TEMPLATE/soul-ring-sect-recruit.yml"),
    ("Sect Recruitment comment workflow", ".github/workflows/soul-ring-sect-recruit.yml"),
    ("Season Board Issue Form", ".github/ISSUE_TEMPLATE/soul-ring-season.yml"),
    ("Season Board comment workflow", ".github/workflows/soul-ring-season.yml"),
)
DELTA_FIELDS = (
    ("stars", "stars"),
    ("forks", "forks"),
    ("watchers", "watchers"),
    ("subscribers", "subscribers"),
    ("open_issues", "open issues"),
    ("pull_request_authors", "pull request authors"),
    ("pypi_releases", "PyPI releases"),
    ("latest_files", "latest files"),
    ("soul_ring_issues", "soul-ring issues"),
    ("accepted_prescriptions", "accepted prescriptions"),
    ("share_proof_issues", "share-proof issues"),
    ("external_returns", "external returns"),
    ("first_sessions", "first sessions"),
    ("share_attributions", "share attributions"),
    ("target_contributors", "target contributors"),
)


def _clean(value: str | None, default: str = "", max_len: int = 200) -> str:
    text = (value or "").strip()
    return (text or default)[:max_len]


def _normalize_username(username: str | None) -> str:
    return _clean(username, "your-github-username").lstrip("@") or "your-github-username"


def _normalize_framework(framework: str | None) -> str:
    return _clean(framework, "langchain").lower().replace(" ", "-") or "langchain"


def _clamp_target(value: int | str | None, default: int = 3) -> int:
    try:
        target = int(value) if value is not None else default
    except (TypeError, ValueError):
        target = default
    if target <= 0:
        target = default
    return max(1, min(target, 100))


def get_traction_snapshot_ledger_path() -> Path:
    """Return the local append-only traction snapshot ledger path."""
    configured = os.getenv("CYBERHUATUO_TRACTION_SNAPSHOT_LEDGER", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".cyberhuatuo" / "traction" / "snapshots.jsonl"


def _repo_slug(value: str | None) -> str:
    slug = _clean(value, DEFAULT_REPO).strip("/")
    parts = [part for part in slug.split("/") if part]
    if len(parts) != 2:
        return DEFAULT_REPO
    return f"{parts[0]}/{parts[1]}"


def _int_value(payload: dict, key: str) -> int:
    try:
        return int(payload.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0


def fetch_public_json(url: str, headers: dict[str, str] | None = None, timeout: int = 10):
    """Fetch one public JSON document using Python's standard library."""
    request_headers = {
        "Accept": "application/json",
        "User-Agent": "CyberHuaTuo-Traction-Proof",
    }
    if "api.github.com" in url:
        request_headers["Accept"] = "application/vnd.github+json"
        request_headers["X-GitHub-Api-Version"] = "2022-11-28"
        token = os.getenv("GITHUB_TOKEN", "").strip() or os.getenv("GH_TOKEN", "").strip()
        if token:
            request_headers["Authorization"] = f"Bearer {token}"
    if headers:
        request_headers.update(headers)
    request = Request(url, headers=request_headers, method="GET")
    with urlopen(request, timeout=timeout) as response:  # noqa: S310
        body = response.read().decode("utf-8")
    return json.loads(body)


def _fetch(fetcher, url: str, timeout: int) -> dict:
    try:
        payload = fetcher(url, None, timeout)
    except HTTPError as exc:
        return {"ok": False, "url": url, "error": f"HTTP {exc.code}: {exc.reason}", "payload": None}
    except URLError as exc:
        return {"ok": False, "url": url, "error": str(exc.reason), "payload": None}
    except OSError as exc:
        return {"ok": False, "url": url, "error": str(exc), "payload": None}
    except Exception as exc:  # pragma: no cover - defensive recovery surface
        return {"ok": False, "url": url, "error": str(exc), "payload": None}
    return {"ok": True, "url": url, "error": "", "payload": payload}


def _github_issue_url(repo: str, label: str) -> str:
    params = urlencode({"state": "all", "labels": label, "per_page": 100})
    return f"https://api.github.com/repos/{repo}/issues?{params}"


def _github_pulls_url(repo: str) -> str:
    params = urlencode({"state": "all", "per_page": 100})
    return f"https://api.github.com/repos/{repo}/pulls?{params}"


def _github_release_url(repo: str, tag: str) -> str:
    encoded_tag = quote(tag, safe="")
    return f"https://api.github.com/repos/{repo}/releases/tags/{encoded_tag}"


def _github_contents_url(repo: str, path: str) -> str:
    encoded_path = quote(path, safe="/")
    return f"https://api.github.com/repos/{repo}/contents/{encoded_path}"


def _build_issueops_readiness(issueops_results: dict[str, dict]) -> dict:
    rows: list[dict] = []
    missing: list[dict] = []
    for label, path in ISSUEOPS_REQUIRED_FILES:
        result = issueops_results.get(path, {})
        payload = result.get("payload") if isinstance(result, dict) else None
        ready = (
            bool(result.get("ok"))
            and isinstance(payload, dict)
            and payload.get("type") == "file"
            and payload.get("path") == path
        )
        row = {
            "label": label,
            "path": path,
            "ready": ready,
            "status": "ready" if ready else "missing or unverified",
            "url": result.get("url", "") if isinstance(result, dict) else "",
            "error": result.get("error", "") if isinstance(result, dict) else "",
        }
        rows.append(row)
        if not ready:
            missing.append(row)
    return {
        "ready": not missing,
        "missing_count": len(missing),
        "rows": rows,
        "missing": missing,
    }


def _build_release_readiness(release_result: dict, release_tag: str) -> dict:
    if not release_result["ok"]:
        error = release_result.get("error", "")
        status = "blocked" if "HTTP 404" in error or "Not Found" in error else "unverified"
        return {
            "ready": False,
            "status": status,
            "release_tag": release_tag,
            "url": release_result.get("url", ""),
            "html_url": "",
            "published_at": "",
            "reason": (
                f"release-trigger launch blocker: GitHub Releases API could not verify `{release_tag}` ({error})."
            ),
        }

    payload = release_result.get("payload")
    if not isinstance(payload, dict):
        return {
            "ready": False,
            "status": "blocked",
            "release_tag": release_tag,
            "url": release_result.get("url", ""),
            "html_url": "",
            "published_at": "",
            "reason": "release-trigger launch blocker: GitHub Releases API did not return a release object.",
        }

    tag_name = _clean(str(payload.get("tag_name", "")), "")
    draft = bool(payload.get("draft"))
    prerelease = bool(payload.get("prerelease"))
    html_url = _clean(str(payload.get("html_url", "")), "")
    published_at = _clean(str(payload.get("published_at", "")), "")
    blockers: list[str] = []
    if tag_name != release_tag:
        blockers.append(f"returned tag `{tag_name or 'unknown'}` does not match requested `{release_tag}`")
    if draft:
        blockers.append("release is still draft")
    if prerelease:
        blockers.append("release is marked prerelease")
    if not published_at:
        blockers.append("release has no published_at timestamp")
    if blockers:
        return {
            "ready": False,
            "status": "blocked",
            "release_tag": release_tag,
            "url": release_result.get("url", ""),
            "html_url": html_url,
            "published_at": published_at,
            "reason": "release-trigger launch blocker: " + "; ".join(blockers) + ".",
        }

    return {
        "ready": True,
        "status": "ready",
        "release_tag": release_tag,
        "url": release_result.get("url", ""),
        "html_url": html_url,
        "published_at": published_at,
        "reason": f"GitHub Release `{release_tag}` is published and can trigger the PyPI release workflow.",
    }


def _build_distribution_readiness(pypi_result: dict, pypi_version: str) -> dict:
    local_version = __version__
    if not pypi_result["ok"]:
        return {
            "ready": False,
            "status": "unverified",
            "local_version": local_version,
            "pypi_version": pypi_version,
            "reason": "PyPI JSON API fetch failed; package registry readiness is unverified.",
        }

    try:
        remote = Version(pypi_version)
        local = Version(local_version)
    except InvalidVersion as exc:
        return {
            "ready": False,
            "status": "blocked",
            "local_version": local_version,
            "pypi_version": pypi_version,
            "reason": f"Version could not be compared with Python packaging rules: {exc}",
        }

    if remote < local:
        return {
            "ready": False,
            "status": "blocked",
            "local_version": local_version,
            "pypi_version": pypi_version,
            "reason": (
                f"install-loop launch blocker: `pip install` would deliver PyPI `{pypi_version}`, "
                f"older than local growth-tool version `{local_version}`."
            ),
        }

    return {
        "ready": True,
        "status": "ready",
        "local_version": local_version,
        "pypi_version": pypi_version,
        "reason": f"PyPI latest `{pypi_version}` is not older than local growth-tool version `{local_version}`.",
    }


def _issue_authors(payload) -> set[str]:
    if not isinstance(payload, list):
        return set()
    authors: set[str] = set()
    for item in payload:
        if not isinstance(item, dict) or item.get("pull_request"):
            continue
        user = item.get("user") or {}
        login = _clean(str(user.get("login", "")), "")
        if login:
            authors.add(login)
    return authors


def _pull_request_authors(payload) -> set[str]:
    if not isinstance(payload, list):
        return set()
    authors: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            continue
        user = item.get("user") or {}
        login = _clean(str(user.get("login", "")), "")
        if login:
            authors.add(login)
    return authors


def _pull_request_count(payload) -> int:
    return len(payload) if isinstance(payload, list) else 0


def _format_status(label: str, result: dict) -> str:
    if result["ok"]:
        return f"{label}: fetched"
    return f"{label}: fetch failed ({result['error']})"


def _format_actor_list(actors: set[str]) -> str:
    if not actors:
        return "none yet"
    return ", ".join(f"@{actor}" for actor in sorted(actors, key=str.lower))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _as_plain_counts(counter: Counter) -> dict[str, int]:
    return {str(key): int(value) for key, value in counter.items() if value}


def _snapshot_numbers_from_event(event: dict) -> dict[str, int]:
    repo_metrics = event.get("repo_metrics", {}) if isinstance(event.get("repo_metrics"), dict) else {}
    pypi_metrics = event.get("pypi_metrics", {}) if isinstance(event.get("pypi_metrics"), dict) else {}
    pull_request_metrics = (
        event.get("pull_request_metrics", {})
        if isinstance(event.get("pull_request_metrics"), dict)
        else {}
    )
    issue_counts = event.get("issue_counts", {}) if isinstance(event.get("issue_counts"), dict) else {}
    ledger_counts = event.get("ledger_counts", {}) if isinstance(event.get("ledger_counts"), dict) else {}
    target_progress = event.get("target_progress", {}) if isinstance(event.get("target_progress"), dict) else {}
    return {
        "stars": _int_value(repo_metrics, "stars"),
        "forks": _int_value(repo_metrics, "forks"),
        "watchers": _int_value(repo_metrics, "watchers"),
        "subscribers": _int_value(repo_metrics, "subscribers"),
        "open_issues": _int_value(repo_metrics, "open_issues"),
        "pull_request_authors": _int_value(pull_request_metrics, "authors"),
        "pypi_releases": _int_value(pypi_metrics, "release_count"),
        "latest_files": _int_value(pypi_metrics, "latest_file_count"),
        "soul_ring_issues": _int_value(issue_counts, "soul-ring"),
        "accepted_prescriptions": _int_value(issue_counts, "accepted-prescription"),
        "share_proof_issues": _int_value(issue_counts, "soul-ring-share-proof"),
        "external_returns": _int_value(ledger_counts, "external_return"),
        "first_sessions": _int_value(ledger_counts, "first_session"),
        "share_attributions": _int_value(ledger_counts, "share_attribution"),
        "target_contributors": _int_value(target_progress, "contributors"),
    }


def _format_delta(value: int) -> str:
    if value >= 0:
        return f"+{value}"
    return str(value)


def _format_delta_line(deltas: dict[str, int]) -> str:
    return ", ".join(
        f"{label} {_format_delta(deltas.get(key, 0))}"
        for key, label in DELTA_FIELDS
    )


def _iter_public_api_results(proof: dict) -> list[dict]:
    results = [
        proof.get("repo_result") or {},
        proof.get("pulls_result") or {},
        proof.get("release_result") or {},
        proof.get("pypi_result") or {},
    ]
    results.extend((proof.get("issue_results") or {}).values())
    results.extend((proof.get("issueops_results") or {}).values())
    return results


def _needs_no_network_proof_pack(proof: dict) -> bool:
    for result in _iter_public_api_results(proof):
        if result.get("ok"):
            continue
        error = str(result.get("error") or "")
        if error and not error.startswith("HTTP 404"):
            return True
    return False


def _format_inline_no_network_proof_pack(
    *,
    repo: str,
    pypi_project: str,
    username: str,
    framework: str,
    release_tag: str,
    target_contributors: int,
) -> list[str]:
    from .marketplace import build_first_public_proof_pack, format_first_public_proof_pack

    pack = build_first_public_proof_pack(
        repo=repo,
        pypi_project=pypi_project,
        username=username,
        framework=framework,
        release_tag=release_tag,
        target_contributors=target_contributors,
    )
    lines = format_first_public_proof_pack(pack).splitlines()
    if lines:
        lines[0] = "## No-Network First Public Proof Pack"
    return lines


def load_traction_snapshots(
    username: str = "",
    framework: str = "",
    repo: str = "",
    pypi_project: str = "",
    path: Path | None = None,
) -> tuple[list[dict], list[str]]:
    """Load append-only traction snapshots, returning parse/access warnings separately."""
    ledger_path = path or get_traction_snapshot_ledger_path()
    target_username = _normalize_username(username).lower() if username else ""
    target_framework = _normalize_framework(framework) if framework else ""
    target_repo = _repo_slug(repo) if repo else ""
    target_project = _clean(pypi_project, DEFAULT_PYPI_PROJECT).lower() if pypi_project else ""
    warnings: list[str] = []
    snapshots: list[dict] = []

    if not ledger_path.exists():
        return [], [f"traction snapshot ledger missing: {ledger_path}"]

    try:
        lines = ledger_path.read_text(encoding=JSONL_READ_ENCODING).splitlines()
    except OSError as exc:
        return [], [f"traction snapshot ledger unreadable: {ledger_path}: {exc}"]

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            snapshot = json.loads(line)
        except json.JSONDecodeError as exc:
            warnings.append(f"line {line_number} is not valid JSON: {exc.msg}")
            continue
        if snapshot.get("snapshot_type") != "soul_ring_traction":
            warnings.append(f"line {line_number} has unsupported snapshot_type")
            continue
        if target_username and str(snapshot.get("username", "")).lower() != target_username:
            continue
        if target_framework and str(snapshot.get("framework", "")).lower() != target_framework:
            continue
        if target_repo and str(snapshot.get("repo", "")) != target_repo:
            continue
        if target_project and str(snapshot.get("pypi_project", "")).lower() != target_project:
            continue
        snapshots.append(snapshot)

    return snapshots, warnings or ["traction snapshot ledger readable"]


def _build_snapshot_event(proof: dict, previous: dict | None, note: str) -> dict:
    issue_counts = {label: len(proof["issue_authors"][label]) for label in ISSUE_LABELS}
    ledger_counts = _as_plain_counts(proof["ledger_counts"])
    return {
        "schema_version": 1,
        "snapshot_id": uuid.uuid4().hex,
        "snapshot_type": "soul_ring_traction",
        "timestamp_utc": _utc_now(),
        "username": proof["username"],
        "framework": proof["framework"],
        "release": proof["release"],
        "repo": proof["repo"],
        "pypi_project": proof["pypi_project"],
        "target_contributors": proof["target"],
        "previous_snapshot_id": previous.get("snapshot_id", "") if previous else "",
        "repo_metrics": dict(proof["repo_metrics"]),
        "pypi_metrics": dict(proof["pypi_metrics"]),
        "pull_request_metrics": dict(proof["pull_request_metrics"]),
        "issue_counts": issue_counts,
        "ledger_counts": ledger_counts,
        "target_progress": {
            "contributors": len(proof["contributor_actors"]),
            "target": proof["target"],
            "actors": sorted(proof["contributor_actors"], key=str.lower),
        },
        "api_fetch_ok": {
            "github_repo": bool(proof["repo_result"]["ok"]),
            "github_pull_requests": bool(proof["pulls_result"]["ok"]),
            "github_release": bool(proof["release_result"]["ok"]),
            "pypi_json": bool(proof["pypi_result"]["ok"]),
            "github_issues": {
                label: bool(result["ok"])
                for label, result in proof["issue_results"].items()
            },
            "github_contents": {
                path: bool(result["ok"])
                for path, result in proof["issueops_results"].items()
            },
        },
        "release_readiness": dict(proof["release_readiness"]),
        "issueops_readiness": {
            "ready": bool(proof["issueops_readiness"]["ready"]),
            "missing": [row["path"] for row in proof["issueops_readiness"]["missing"]],
            "checked_paths": [path for _label, path in ISSUEOPS_REQUIRED_FILES],
        },
        "distribution_readiness": dict(proof["distribution_readiness"]),
        "weakest": proof["weakest"],
        "note": _clean(note, max_len=500),
        "append_only_notice": "append-only reviewable real snapshot",
        "non_fabrication": (
            "downloads, retention, repost counts, referrals, rewards, and private analytics are not recorded"
        ),
    }


def record_traction_snapshot(proof: dict, *, note: str = "", path: Path | None = None) -> dict:
    """Append one reviewable real traction snapshot and calculate deltas from the previous snapshot."""
    ledger_path = path or get_traction_snapshot_ledger_path()
    snapshots, warnings = load_traction_snapshots(
        proof["username"],
        proof["framework"],
        proof["repo"],
        proof["pypi_project"],
        ledger_path,
    )
    previous = snapshots[-1] if snapshots else None
    event = _build_snapshot_event(proof, previous, note)
    current_numbers = _snapshot_numbers_from_event(event)
    previous_numbers = _snapshot_numbers_from_event(previous) if previous else {}
    deltas = {
        key: current_numbers.get(key, 0) - previous_numbers.get(key, 0)
        for key, _label in DELTA_FIELDS
    } if previous else {}

    try:
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with ledger_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError as exc:
        return {
            "ok": False,
            "path": str(ledger_path),
            "error": str(exc),
            "event": event,
            "previous": previous,
            "deltas": deltas,
            "warnings": warnings,
        }

    return {
        "ok": True,
        "path": str(ledger_path),
        "error": "",
        "event": event,
        "previous": previous,
        "deltas": deltas,
        "warnings": warnings,
    }


def _command_base(
    name: str,
    username: str,
    framework: str,
    target: int,
    release: str,
    include_release: bool,
) -> str:
    command = f"cyberhuatuo {name} --username {username} --framework {framework}"
    if include_release:
        command += f" --release-tag {release}"
    return f"{command} --target-contributors {target}"


def build_soul_ring_traction_proof(
    github_username: str = "your-github-username",
    framework: str = "langchain",
    *,
    release_tag: str = "",
    target_contributors: int | str = 3,
    repo: str = DEFAULT_REPO,
    pypi_project: str = DEFAULT_PYPI_PROJECT,
    timeout: int | str = 10,
    fetcher=fetch_public_json,
) -> dict:
    """Build a public traction proof snapshot from real APIs and local ledger events."""
    username = _normalize_username(github_username)
    target_framework = _normalize_framework(framework)
    target = _clamp_target(target_contributors)
    repo_name = _repo_slug(repo)
    project = _normalize_framework(pypi_project).replace("-", "_") if pypi_project == "" else _clean(pypi_project, DEFAULT_PYPI_PROJECT)
    include_release = bool((release_tag or "").strip())
    release = _clean(release_tag, f"v{__version__}")
    try:
        request_timeout = max(1, min(int(timeout), 30))
    except (TypeError, ValueError):
        request_timeout = 10

    repo_url = f"https://api.github.com/repos/{repo_name}"
    pulls_url = _github_pulls_url(repo_name)
    release_url = _github_release_url(repo_name, release)
    pypi_url = f"https://pypi.org/pypi/{project}/json"
    repo_result = _fetch(fetcher, repo_url, request_timeout)
    pulls_result = _fetch(fetcher, pulls_url, request_timeout)
    release_result = _fetch(fetcher, release_url, request_timeout)
    pypi_result = _fetch(fetcher, pypi_url, request_timeout)

    issue_results = {
        label: _fetch(fetcher, _github_issue_url(repo_name, label), request_timeout)
        for label in ISSUE_LABELS
    }
    issueops_results = {
        path: _fetch(fetcher, _github_contents_url(repo_name, path), request_timeout)
        for _label, path in ISSUEOPS_REQUIRED_FILES
    }
    issueops_readiness = _build_issueops_readiness(issueops_results)
    issue_authors = {
        label: _issue_authors(result["payload"]) if result["ok"] else set()
        for label, result in issue_results.items()
    }
    pull_request_authors = _pull_request_authors(pulls_result["payload"]) if pulls_result["ok"] else set()
    pull_request_count = _pull_request_count(pulls_result["payload"]) if pulls_result["ok"] else 0

    ledger_events, ledger_warnings = load_activation_events("", target_framework)
    ledger_counts = Counter(event.get("event_type", "") for event in ledger_events)
    ledger_actors = {
        _normalize_username(str(event.get("username", "")))
        for event in ledger_events
        if event.get("event_type") in {"external_return", "first_session", "share_attribution"}
    }
    ledger_actors.discard("your-github-username")

    contributor_actors = set()
    contributor_actors.update(issue_authors["soul-ring"])
    contributor_actors.update(issue_authors["accepted-prescription"])
    contributor_actors.update(issue_authors["soul-ring-share-proof"])
    contributor_actors.update(pull_request_authors)
    contributor_actors.update(ledger_actors)

    repo_payload = repo_result["payload"] if isinstance(repo_result["payload"], dict) else {}
    pypi_payload = pypi_result["payload"] if isinstance(pypi_result["payload"], dict) else {}
    pypi_info = pypi_payload.get("info", {}) if isinstance(pypi_payload, dict) else {}
    pypi_releases = pypi_payload.get("releases", {}) if isinstance(pypi_payload, dict) else {}
    pypi_urls = pypi_payload.get("urls", []) if isinstance(pypi_payload, dict) else []
    pypi_version = _clean(str(pypi_info.get("version", "")), "unknown")
    release_readiness = _build_release_readiness(release_result, release)
    distribution_readiness = _build_distribution_readiness(pypi_result, pypi_version)

    if (
        not repo_result["ok"]
        or not pulls_result["ok"]
        or not pypi_result["ok"]
        or (not release_result["ok"] and release_readiness["status"] == "unverified")
        or any(not result["ok"] for result in issue_results.values())
    ):
        weakest = "public API fetch recovery needed"
    elif not issueops_readiness["ready"]:
        weakest = "remote IssueOps readiness blocker"
    elif not release_readiness["ready"] and not distribution_readiness["ready"]:
        weakest = "release trigger or protected manual publish fallback blocker"
    elif not distribution_readiness["ready"]:
        weakest = "package registry launch blocker"
    elif ledger_counts.get("external_return", 0) == 0:
        weakest = "external-return proof missing after public attention"
    elif ledger_counts.get("first_session", 0) == 0:
        weakest = "first-session proof missing after public attention"
    elif len(contributor_actors) < target:
        weakest = "target first-ring contributor identities not reached"
    elif ledger_counts.get("share_attribution", 0) == 0:
        weakest = "public share attribution proof missing"
    else:
        weakest = "raise target or open the next launch campaign"

    return {
        "username": username,
        "framework": target_framework,
        "release": release,
        "include_release": include_release,
        "target": target,
        "repo": repo_name,
        "pypi_project": project,
        "repo_result": repo_result,
        "pulls_result": pulls_result,
        "release_result": release_result,
        "pypi_result": pypi_result,
        "issue_results": issue_results,
        "issueops_results": issueops_results,
        "issueops_readiness": issueops_readiness,
        "release_readiness": release_readiness,
        "distribution_readiness": distribution_readiness,
        "issue_authors": issue_authors,
        "pull_request_authors": pull_request_authors,
        "ledger_events": ledger_events,
        "ledger_warnings": ledger_warnings,
        "ledger_counts": ledger_counts,
        "ledger_actors": ledger_actors,
        "contributor_actors": contributor_actors,
        "repo_metrics": {
            "stars": _int_value(repo_payload, "stargazers_count"),
            "forks": _int_value(repo_payload, "forks_count"),
            "watchers": _int_value(repo_payload, "watchers_count"),
            "subscribers": _int_value(repo_payload, "subscribers_count"),
            "open_issues": _int_value(repo_payload, "open_issues_count"),
        },
        "pypi_metrics": {
            "version": pypi_version,
            "release_count": len(pypi_releases) if isinstance(pypi_releases, dict) else 0,
            "latest_file_count": len(pypi_urls) if isinstance(pypi_urls, list) else 0,
        },
        "pull_request_metrics": {
            "authors": len(pull_request_authors),
            "pull_requests": pull_request_count,
        },
        "weakest": weakest,
    }


def format_soul_ring_traction_proof(
    github_username: str = "your-github-username",
    framework: str = "langchain",
    *,
    release_tag: str = "",
    target_contributors: int | str = 3,
    repo: str = DEFAULT_REPO,
    pypi_project: str = DEFAULT_PYPI_PROJECT,
    timeout: int | str = 10,
    record_snapshot: bool = False,
    snapshot_note: str = "",
    fetcher=fetch_public_json,
) -> str:
    """Return a markdown public traction proof report."""
    proof = build_soul_ring_traction_proof(
        github_username,
        framework,
        release_tag=release_tag,
        target_contributors=target_contributors,
        repo=repo,
        pypi_project=pypi_project,
        timeout=timeout,
        fetcher=fetcher,
    )
    snapshot_result = record_traction_snapshot(
        proof,
        note=snapshot_note,
    ) if record_snapshot else None
    username = proof["username"]
    framework_name = proof["framework"]
    target = proof["target"]
    release = proof["release"]
    include_release = proof["include_release"]

    traction_command = _command_base("traction-proof", username, framework_name, target, release, include_release)
    if record_snapshot:
        traction_command += " --record-snapshot"
    market_ready_command = (
        f"cyberhuatuo market-ready --remote --strict-remote --username {username} "
        f"--framework {framework_name} --release-tag {release} --target-contributors {target}"
    )
    proof_pack_command = (
        f"cyberhuatuo proof-pack --username {username} --framework {framework_name} "
        f"--release-tag {release} --target-contributors {target}"
    )
    market_copy_command = (
        f"cyberhuatuo market-copy --username {username} --framework {framework_name} "
        f"--release-tag {release} --target-contributors {target}"
    )
    launch_campaign_command = _command_base("launch-campaign", username, framework_name, target, release, include_release)
    record_return_command = (
        f"cyberhuatuo record-return --username {username} --framework {framework_name} "
        '--surface "PyPI / Claude / Codex launch" --source-url <https-url>'
    )
    record_session_command = (
        f"cyberhuatuo record-session --username {username} --framework {framework_name} "
        '--surface "First agent session" --source-url <https-url>'
    )
    activation_command = f"cyberhuatuo activation --username {username} --framework {framework_name}"
    flywheel_command = f"cyberhuatuo flywheel --username {username} --framework {framework_name}"
    record_share_command = f"cyberhuatuo record-share --username {username} --framework {framework_name} --share-url <https-url>"
    share_report_command = f"cyberhuatuo share-report --username {username} --framework {framework_name} --top-n 10"
    share_leaderboard_command = f"cyberhuatuo share-leaderboard --framework {framework_name} --top-n 10"

    repo_metrics = proof["repo_metrics"]
    pypi_metrics = proof["pypi_metrics"]
    release_readiness = proof["release_readiness"]
    distribution_readiness = proof["distribution_readiness"]
    issueops_readiness = proof["issueops_readiness"]
    issue_authors = proof["issue_authors"]
    pull_request_metrics = proof["pull_request_metrics"]
    ledger_counts = proof["ledger_counts"]
    warnings = proof["ledger_warnings"] or ["ledger readable"]
    no_network_pack_lines = []
    if _needs_no_network_proof_pack(proof):
        no_network_pack_lines = _format_inline_no_network_proof_pack(
            repo=proof["repo"],
            pypi_project=proof["pypi_project"],
            username=username,
            framework=framework_name,
            release_tag=release,
            target_contributors=target,
        )

    issue_fetch_lines = []
    for label in ISSUE_LABELS:
        issue_fetch_lines.append(f"- {label}: {_format_status('GitHub Issues API', proof['issue_results'][label])}")

    issueops_lines = [
        f"- {row['label']}: {row['status']} -- `{row['path']}`"
        + (f" ({row['error']})" if row["error"] and not row["ready"] else "")
        for row in issueops_readiness["rows"]
    ]
    issueops_summary = (
        "ready"
        if issueops_readiness["ready"]
        else f"blocked ({issueops_readiness['missing_count']} missing/unverified)"
    )

    release_status = release_readiness["status"]
    if not release_readiness["ready"] and distribution_readiness["ready"]:
        release_status = f"{release_status} (protected workflow_dispatch release_tag fallback acceptable after PyPI proof)"
    release_lines = [
        (
            "- Formula: GitHub Releases API `releases/tags/{tag}` should return a matching, "
            "published, non-draft, non-prerelease release for public provenance; if the PyPI latest-version proof is already current, "
            "the protected manual `workflow_dispatch` `release_tag` fallback can close the registry path without `PYPI_TOKEN`."
        ),
        f"- Status: {release_status}",
        f"- Release tag: `{release_readiness['release_tag']}`",
        f"- GitHub Releases API URL: {release_readiness['url']}",
        f"- Release proof: {release_readiness['reason']}",
    ]
    if release_readiness.get("html_url"):
        release_lines.append(f"- Release page: {release_readiness['html_url']}")
    if release_readiness.get("published_at"):
        release_lines.append(f"- Published at: `{release_readiness['published_at']}`")
    if not release_readiness["ready"] and distribution_readiness["ready"]:
        release_lines.extend([
            "- Fallback proof: PyPI latest-version proof is current, so the install-loop registry path is not blocked by the missing GitHub Release.",
            "- Recovery route: publish a GitHub Release for public provenance, then re-run the proof command.",
            "- Protected fallback route: `.github/workflows/publish-pypi.yml` accepts manual `workflow_dispatch` `release_tag`, verifies tag format, origin/main reachability, package-version equality, and OIDC publishing without `PYPI_TOKEN`.",
            f"- Recheck command: `cyberhuatuo traction-proof --username {username} --framework {framework_name} --release-tag {release} --target-contributors {target}`.",
        ])
    elif not release_readiness["ready"]:
        release_lines.extend([
            "- Recovery route: publish a non-draft, non-prerelease GitHub Release after local quality gates pass, or run the protected manual `workflow_dispatch` `release_tag` fallback when release publication is unavailable.",
            "- Required release path: `.github/workflows/publish-pypi.yml` listens for `release.published` and also protects manual `workflow_dispatch` with tag reachability plus package-version checks.",
            f"- Recheck command: `cyberhuatuo traction-proof --username {username} --framework {framework_name} --release-tag {release} --target-contributors {target}`.",
        ])

    distribution_lines = [
        (
            "- Formula: PyPI JSON API `info.version` must be greater than or equal to "
            f"local growth-tool version `{distribution_readiness['local_version']}` using Python packaging version ordering."
        ),
        f"- Status: {distribution_readiness['status']}",
        f"- PyPI latest version: `{distribution_readiness['pypi_version']}`",
        f"- Local growth-tool version: `{distribution_readiness['local_version']}`",
        f"- Registry proof: {distribution_readiness['reason']}",
    ]
    if not distribution_readiness["ready"]:
        distribution_lines.extend([
            (
                "- Recovery route: use PyPI Trusted Publishing through "
                "`.github/workflows/publish-pypi.yml`; do not use a stored `PYPI_TOKEN`."
            ),
            "- Recovery commands: `python -m ruff check .`, `python -m pytest -q`, `python -m build --sdist --wheel`, `python scripts/check_release_boundary.py`.",
            f"- Recheck command: `cyberhuatuo traction-proof --username {username} --framework {framework_name} --target-contributors {target}`.",
        ])

    snapshot_lines = [
        "## Snapshot History",
    ]
    if snapshot_result is None:
        snapshot_lines.extend([
            "- Snapshot History: not recorded",
            f"- Snapshot ledger: `{get_traction_snapshot_ledger_path()}`",
            "- Use `--record-snapshot` to append a reviewable real snapshot after a public launch check.",
            "- Snapshot recording is opt-in, append-only, and compares only against prior real snapshots.",
        ])
    elif not snapshot_result["ok"]:
        snapshot_lines.extend([
            "- Snapshot recorded: no",
            f"- Snapshot ledger: `{snapshot_result['path']}`",
            f"- Snapshot write failure: {snapshot_result['error']}",
            "- Snapshot write failures are recovery surfaces, not zero-growth claims.",
        ])
    else:
        snapshot_lines.extend([
            "- Snapshot recorded: yes",
            f"- Snapshot ledger: `{snapshot_result['path']}`",
            f"- Snapshot id: `{snapshot_result['event']['snapshot_id']}`",
        ])
        previous = snapshot_result["previous"]
        if previous:
            snapshot_lines.extend([
                f"- Compared against previous real snapshot: `{previous.get('snapshot_id', '')}`",
                f"- Velocity deltas: {_format_delta_line(snapshot_result['deltas'])}",
                "- Velocity deltas are from append-only real snapshots, not static vanity metrics.",
            ])
        else:
            snapshot_lines.extend([
                "- Previous snapshot: none yet",
                "- Velocity deltas require at least two recorded real snapshots.",
            ])

    return "\n".join([
        "# Soul Ring Traction Proof",
        "",
        f"- GitHub: @{username}",
        f"- Target Framework: `{framework_name}`",
        f"- Release: `{release}`",
        f"- Repository: `{proof['repo']}`",
        f"- PyPI project: `{proof['pypi_project']}`",
        f"- GitHub Repository API: {_format_status('GitHub Repository API', proof['repo_result']).split(': ', 1)[1]}",
        f"- GitHub Pull Requests API: {_format_status('GitHub Pull Requests API', proof['pulls_result']).split(': ', 1)[1]}",
        f"- GitHub Release readiness: {release_readiness['status']}",
        f"- PyPI JSON API: {_format_status('PyPI JSON API', proof['pypi_result']).split(': ', 1)[1]}",
        f"- PyPI package readiness: {distribution_readiness['status']}",
        f"- Remote IssueOps readiness: {issueops_summary}",
        (
            f"- Public attention signals: stars {repo_metrics['stars']}, forks {repo_metrics['forks']}, "
            f"watchers {repo_metrics['watchers']}, subscribers {repo_metrics['subscribers']}, "
            f"open issues {repo_metrics['open_issues']}"
        ),
        "- Stars/forks/watchers are attention signals, not contributor progress.",
        f"- PyPI version: `{pypi_metrics['version']}`",
        f"- PyPI releases observed: {pypi_metrics['release_count']}; latest files observed: {pypi_metrics['latest_file_count']}",
        "- PyPI downloads are not used; PyPI JSON API `downloads` is deprecated and not a traction proof source.",
        (
            "- Public IssueOps proof: "
            f"soul-ring issues {len(issue_authors['soul-ring'])}, "
            f"accepted prescriptions {len(issue_authors['accepted-prescription'])}, "
            f"share-proof issues {len(issue_authors['soul-ring-share-proof'])}"
        ),
        (
            "- Public Pull Request proof: "
            f"PR authors {pull_request_metrics['authors']}, "
            f"pull requests {pull_request_metrics['pull_requests']}"
        ),
        "- PR authors are contributor identities, but PRs stay separate from IssueOps issue counts.",
        (
            "- Local ledger proof: "
            f"external returns {ledger_counts.get('external_return', 0)}, "
            f"first sessions {ledger_counts.get('first_session', 0)}, "
            f"share attributions {ledger_counts.get('share_attribution', 0)}"
        ),
        (
            f"- Target contributor progress: {len(proof['contributor_actors'])} / {target} "
            "real contributor identities"
        ),
        f"- Real contributor identities: {_format_actor_list(proof['contributor_actors'])}",
        f"- Weakest external proof bridge: {proof['weakest']}",
        "- Fetch failures are recovery surfaces, not zero traction claims.",
        (
            "- Non-fabrication rule: downloads are not used; stars, forks, watchers, subscribers, reposts, "
            "retention, and referral conversions are not inferred; rewards are not invented."
        ),
        "",
        "## Public API Fetch Health",
        f"- GitHub repo URL: {proof['repo_result']['url']}",
        f"- GitHub pulls URL: {proof['pulls_result']['url']}",
        f"- GitHub release URL: {proof['release_result']['url']}",
        f"- PyPI JSON URL: {proof['pypi_result']['url']}",
        f"- Pull requests: {_format_status('GitHub Pull Requests API', proof['pulls_result'])}",
        *issue_fetch_lines,
        "",
        "## Release Trigger Readiness",
        *release_lines,
        "",
        "## Distribution Readiness",
        *distribution_lines,
        "",
        "## Remote IssueOps Readiness",
        "- Formula: GitHub Contents API on the repository default branch; issues/new?... links are form entrypoints, not proof URLs.",
        f"- Readiness: {issueops_summary}",
        *issueops_lines,
        "- Missing remote IssueOps files are public launch blockers; do not treat form URLs as live acquisition loops until fixed.",
        "",
        "## Ledger Health",
        *[f"- {warning}" for warning in warnings],
        "",
        *snapshot_lines,
        "",
        "## Launch Closure Checklist",
        "- Run the marketplace readiness preflight before treating this proof as a closed PyPI / Claude / Codex launch loop.",
        "```bash",
        proof_pack_command,
        market_copy_command,
        market_ready_command,
        "```",
        "",
        *no_network_pack_lines,
        "",
        "## Next Proof Commands",
        "```bash",
        proof_pack_command,
        market_copy_command,
        market_ready_command,
        traction_command,
        launch_campaign_command,
        record_return_command,
        record_session_command,
        activation_command,
        flywheel_command,
        record_share_command,
        share_report_command,
        share_leaderboard_command,
        "```",
    ])
