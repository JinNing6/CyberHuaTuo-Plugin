"""Current public install command surface for CyberHuaTuo."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError

from packaging.version import InvalidVersion, Version

from . import __version__
from .traction import DEFAULT_PYPI_PROJECT, DEFAULT_REPO, fetch_public_json


def _clean(value: str | None, default: str, limit: int = 200) -> str:
    text = (value or "").strip()
    return (text or default)[:limit]


def _repo_slug(value: str | None) -> str:
    slug = _clean(value, DEFAULT_REPO).strip("/")
    parts = [part for part in slug.split("/") if part]
    if len(parts) != 2:
        return DEFAULT_REPO
    return f"{parts[0]}/{parts[1]}"


def _positive_target(value: int | str | None, default: int = 3) -> int:
    try:
        target = int(value) if value is not None else default
    except (TypeError, ValueError):
        target = default
    return max(1, min(target, 100))


def _versions_match(left: str, right: str) -> bool:
    try:
        return Version(left) == Version(right)
    except InvalidVersion:
        return left.strip() == right.strip()


def _venv_python_path(env_dir: Path) -> Path:
    if os.name == "nt":
        return env_dir / "Scripts" / "python.exe"
    return env_dir / "bin" / "python"


def _command_text(command: list[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(command)
    import shlex

    return shlex.join(command)


def _output_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _tail(value: str | bytes | None, limit: int = 1200) -> str:
    text = _output_text(value).strip()
    if len(text) <= limit:
        return text
    return text[-limit:]


def _run_smoke_step(
    *,
    name: str,
    command: list[str],
    runner,
    timeout: int,
    expected_stdout: tuple[str, ...] = (),
    cwd: str | None = None,
) -> dict[str, object]:
    try:
        completed = runner(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "name": name,
            "command": command,
            "command_text": _command_text(command),
            "status": "fail",
            "returncode": "timeout",
            "stdout": _tail(exc.stdout),
            "stderr": _tail(exc.stderr) or f"timed out after {timeout} seconds",
            "missing_stdout": list(expected_stdout),
        }
    except OSError as exc:
        return {
            "name": name,
            "command": command,
            "command_text": _command_text(command),
            "status": "fail",
            "returncode": "os-error",
            "stdout": "",
            "stderr": str(exc),
            "missing_stdout": list(expected_stdout),
        }

    stdout = _output_text(getattr(completed, "stdout", ""))
    missing = [snippet for snippet in expected_stdout if snippet not in stdout]
    returncode = int(getattr(completed, "returncode", 1))
    return {
        "name": name,
        "command": command,
        "command_text": _command_text(command),
        "status": "pass" if returncode == 0 and not missing else "fail",
        "returncode": returncode,
        "stdout": _tail(stdout),
        "stderr": _tail(getattr(completed, "stderr", "")),
        "missing_stdout": missing,
    }


def _pypi_result(project: str, timeout: int, fetcher) -> dict[str, object]:
    url = f"https://pypi.org/pypi/{project}/json"
    try:
        payload = fetcher(url, None, timeout)
    except HTTPError as exc:
        return {"ok": False, "url": url, "error": f"HTTP {exc.code}: {exc.reason}", "latest_version": "unknown"}
    except URLError as exc:
        return {"ok": False, "url": url, "error": str(exc.reason), "latest_version": "unknown"}
    except OSError as exc:
        return {"ok": False, "url": url, "error": str(exc), "latest_version": "unknown"}
    except Exception as exc:  # pragma: no cover - defensive recovery surface
        return {"ok": False, "url": url, "error": str(exc), "latest_version": "unknown"}

    info = payload.get("info", {}) if isinstance(payload, dict) else {}
    latest = str(info.get("version", "")).strip() if isinstance(info, dict) else ""
    if not latest:
        return {"ok": False, "url": url, "error": "missing PyPI info.version", "latest_version": "unknown"}
    return {"ok": True, "url": url, "error": "", "latest_version": latest}


def build_candidate_install_smoke(
    *,
    username: str = "your-github-username",
    framework: str = "langchain",
    release_tag: str = "",
    target_contributors: int = 3,
    repo: str = DEFAULT_REPO,
    pypi_project: str = DEFAULT_PYPI_PROJECT,
    timeout: int = 600,
    keep_temp: bool = False,
    python_executable: str | None = None,
    runner=subprocess.run,
    mkdtemp=tempfile.mkdtemp,
    rmtree=shutil.rmtree,
) -> dict[str, object]:
    """Install the public Git tag in a disposable venv and verify the launch route."""
    clean_repo = _repo_slug(repo)
    clean_project = _clean(pypi_project, DEFAULT_PYPI_PROJECT).lower()
    clean_username = _clean(username, "your-github-username").lstrip("@") or "your-github-username"
    clean_framework = _clean(framework, "langchain").lower().replace(" ", "-") or "langchain"
    release = _clean(release_tag, f"v{__version__}")
    target = _positive_target(target_contributors)
    request_timeout = _positive_target(timeout, default=600)
    python_cmd = python_executable or sys.executable
    temp_dir = Path(mkdtemp(prefix="cyberhuatuo-candidate-install-")).resolve()
    venv_python = _venv_python_path(temp_dir)
    install_requirement = f"{clean_project} @ git+https://github.com/{clean_repo}.git@{release}"
    common_route_args = [
        "--username",
        clean_username,
        "--framework",
        clean_framework,
        "--release-tag",
        release,
        "--target-contributors",
        str(target),
        "--repo",
        clean_repo,
        "--pypi-project",
        clean_project,
    ]
    step_specs: list[tuple[str, list[str], tuple[str, ...]]] = [
        ("Create disposable virtual environment", [python_cmd, "-m", "venv", str(temp_dir)], ()),
        ("Upgrade pip inside disposable environment", [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], ()),
        (
            "Install public Git tag candidate",
            [str(venv_python), "-m", "pip", "install", "--upgrade", install_requirement],
            (),
        ),
        (
            "Verify installed CyberHuaTuo version",
            [str(venv_python), "-c", "import cyberhuatuo; print(cyberhuatuo.__version__)"],
            (__version__,),
        ),
        (
            "Verify console command surface",
            [str(venv_python), "-m", "cyberhuatuo", "--help"],
            ("install-command", "proof-pack", "candidate-install-smoke"),
        ),
        (
            "Verify install decision surface",
            [str(venv_python), "-m", "cyberhuatuo", "install-command", *common_route_args, "--timeout", "5"],
            ("CyberHuaTuo Install Command", "proof-pack"),
        ),
        (
            "Verify first proof and invite route",
            [str(venv_python), "-m", "cyberhuatuo", "proof-pack", *common_route_args],
            ("No-Network First Public Proof Pack", "External Contributor Path", "first-invite"),
        ),
    ]

    steps: list[dict[str, object]] = []
    failed_step = ""
    for name, command, expected in step_specs:
        result = _run_smoke_step(
            name=name,
            command=command,
            runner=runner,
            timeout=request_timeout,
            expected_stdout=expected,
        )
        steps.append(result)
        if result["status"] != "pass":
            failed_step = name
            break

    status = "pass" if not failed_step else "fail"
    cleanup = "retained"
    cleanup_error = ""
    if status == "pass" and not keep_temp:
        try:
            rmtree(temp_dir)
            cleanup = "removed"
        except OSError as exc:
            status = "fail"
            cleanup = "retained"
            cleanup_error = str(exc)
            failed_step = "Remove disposable virtual environment"
    elif status == "pass" and keep_temp:
        cleanup = "retained (--keep-temp)"

    return {
        "title": "Candidate Install Smoke Gate",
        "status": status,
        "repo": clean_repo,
        "pypi_project": clean_project,
        "release_tag": release,
        "local_version": __version__,
        "username": clean_username,
        "framework": clean_framework,
        "target_contributors": target,
        "temp_dir": str(temp_dir),
        "cleanup": cleanup,
        "cleanup_error": cleanup_error,
        "failed_step": failed_step,
        "install_requirement": install_requirement,
        "candidate_install_command": f'python -m pip install --upgrade "{install_requirement}"',
        "steps": steps,
        "disclosure": (
            "Creates a disposable virtual environment, installs the exact public Git tag with pip Direct URL "
            "syntax, verifies version, console command, install surface, and proof/invite route."
        ),
        "completion_rule": (
            "Pass this smoke gate before asking outside contributors to use the Git Tag Candidate Install Bridge; "
            "the bridge still does not close the PyPI install loop."
        ),
        "non_fabrication_notice": (
            "No downloads, retention, repost counts, referrals, rewards, or fake contributors are claimed."
        ),
    }


def build_current_install_command(
    *,
    username: str = "your-github-username",
    framework: str = "langchain",
    release_tag: str = "",
    target_contributors: int = 3,
    repo: str = DEFAULT_REPO,
    pypi_project: str = DEFAULT_PYPI_PROJECT,
    timeout: int = 10,
    fetcher=fetch_public_json,
) -> dict[str, object]:
    """Fetch PyPI latest-version proof and choose the current public install command."""
    clean_repo = _repo_slug(repo)
    clean_project = _clean(pypi_project, DEFAULT_PYPI_PROJECT).lower()
    clean_username = _clean(username, "your-github-username").lstrip("@") or "your-github-username"
    clean_framework = _clean(framework, "langchain").lower().replace(" ", "-") or "langchain"
    release = _clean(release_tag, f"v{__version__}")
    target = _positive_target(target_contributors)
    request_timeout = _positive_target(timeout, default=10)

    pypi = _pypi_result(clean_project, request_timeout, fetcher)
    canonical_install_command = f"python -m pip install --upgrade {clean_project}"
    candidate_git_install_command = (
        f'python -m pip install --upgrade "{clean_project} @ git+https://github.com/{clean_repo}.git@{release}"'
    )
    registry_current = bool(pypi["ok"]) and _versions_match(str(pypi["latest_version"]), __version__)
    if registry_current:
        status = "registry-current"
        recommended = canonical_install_command
        decision = (
            f"PyPI latest `{pypi['latest_version']}` matches local package metadata `{__version__}`; "
            "canonical registry install is the current public path."
        )
    elif pypi["ok"]:
        status = "registry-stale"
        recommended = candidate_git_install_command
        decision = (
            f"PyPI latest `{pypi['latest_version']}` does not match local package metadata `{__version__}`; "
            "use the bounded Git tag candidate bridge until PyPI is refreshed."
        )
    else:
        status = "registry-unverified"
        recommended = candidate_git_install_command
        decision = (
            "PyPI latest-version proof could not be verified; use the bounded Git tag candidate bridge "
            "and recheck PyPI before claiming public install readiness."
        )

    first_action_command = f"cyberhuatuo challenge --username {clean_username} --framework {clean_framework}"
    proof_pack_command = (
        f"cyberhuatuo proof-pack --username {clean_username} --framework {clean_framework} "
        f"--release-tag {release} --target-contributors {target} --repo {clean_repo} --pypi-project {clean_project}"
    )
    market_ready_command = (
        f"cyberhuatuo market-ready --remote --strict-remote --username {clean_username} "
        f"--framework {clean_framework} --release-tag {release} --target-contributors {target} "
        f"--repo {clean_repo} --pypi-project {clean_project}"
    )
    traction_command = (
        f"cyberhuatuo traction-proof --username {clean_username} --framework {clean_framework} "
        f"--release-tag {release} --target-contributors {target} --repo {clean_repo} --pypi-project {clean_project}"
    )
    market_copy_command = (
        f"cyberhuatuo market-copy --username {clean_username} --framework {clean_framework} "
        f"--release-tag {release} --target-contributors {target} --repo {clean_repo} --pypi-project {clean_project}"
    )
    candidate_smoke_command = (
        f"cyberhuatuo candidate-install-smoke --username {clean_username} --framework {clean_framework} "
        f"--release-tag {release} --target-contributors {target} --repo {clean_repo} --pypi-project {clean_project}"
    )

    return {
        "title": "CyberHuaTuo Install Command",
        "status": status,
        "decision": decision,
        "repo": clean_repo,
        "pypi_project": clean_project,
        "release_tag": release,
        "local_version": __version__,
        "pypi_result": pypi,
        "canonical_install_command": canonical_install_command,
        "candidate_git_install_command": candidate_git_install_command,
        "recommended_install_command": recommended,
        "first_action_command": first_action_command,
        "proof_pack_command": proof_pack_command,
        "market_ready_command": market_ready_command,
        "traction_command": traction_command,
        "market_copy_command": market_copy_command,
        "candidate_smoke_command": candidate_smoke_command,
        "mcp_route": "current_install_command",
        "bridge_disclosure": (
            "The Git Tag Candidate Install Bridge is only a bounded recovery path after the public v* tag exists; "
            "it does not close the PyPI install loop."
        ),
        "completion_rule": "Recheck PyPI latest-version proof before claiming public install readiness.",
        "non_fabrication_notice": (
            "This install command surface does not invent downloads, retention, repost counts, referrals, "
            "rewards, reviews, approvals, or fake contributors."
        ),
    }


def format_current_install_command(
    *,
    username: str = "your-github-username",
    framework: str = "langchain",
    release_tag: str = "",
    target_contributors: int = 3,
    repo: str = DEFAULT_REPO,
    pypi_project: str = DEFAULT_PYPI_PROJECT,
    timeout: int = 10,
    fetcher=fetch_public_json,
) -> str:
    """Format the current public install command as a compact operator runbook."""
    report = build_current_install_command(
        username=username,
        framework=framework,
        release_tag=release_tag,
        target_contributors=target_contributors,
        repo=repo,
        pypi_project=pypi_project,
        timeout=timeout,
        fetcher=fetcher,
    )
    pypi = report["pypi_result"]
    pypi_status = "pass" if pypi["ok"] else "fail"
    lines = [
        "# CyberHuaTuo Install Command",
        "",
        f"- Repository: `{report['repo']}`",
        f"- PyPI project: `{report['pypi_project']}`",
        f"- Local package version: `{report['local_version']}`",
        f"- Release tag: `{report['release_tag']}`",
        f"- PyPI JSON API: {pypi_status} ({pypi['url']})",
        f"- PyPI latest version: `{pypi['latest_version']}`",
        f"- Install status: `{report['status']}`",
        f"- Decision: {report['decision']}",
        f"- {report['non_fabrication_notice']}",
        "",
        "## Recommended Install",
        f"- Recommended install: `{report['recommended_install_command']}`",
        "```bash",
        report["recommended_install_command"],
        "```",
    ]
    if not pypi["ok"]:
        lines.append(f"- Registry error: {pypi['error']}")
    if report["status"] != "registry-current":
        lines.extend([
            "",
            "## Git Tag Candidate Install Bridge",
            f"- Canonical PyPI install: `{report['canonical_install_command']}`",
            f"- {report['bridge_disclosure']}",
            "```bash",
            report["candidate_git_install_command"],
            report["candidate_smoke_command"],
            report["market_ready_command"],
            "```",
            f"- {report['completion_rule']}",
        ])
    lines.extend([
        "",
        "## First Soul Ring Route",
        "```bash",
        report["first_action_command"],
        report["proof_pack_command"],
        report["market_copy_command"],
        report["traction_command"],
        "```",
        "",
        "## Claude / Codex MCP Route",
        f"- Call MCP tool `{report['mcp_route']}` first, then `first_public_proof_pack` for the same release tag.",
    ])
    return "\n".join(lines)


def format_candidate_install_smoke(report: dict[str, object]) -> str:
    """Format a candidate install smoke report."""
    cleanup = str(report["cleanup"])
    cleanup_label = "retained for inspection" if cleanup == "retained" else cleanup
    lines = [
        "# Candidate Install Smoke Gate",
        "",
        f"- Repository: `{report['repo']}`",
        f"- PyPI project: `{report['pypi_project']}`",
        f"- Release tag: `{report['release_tag']}`",
        f"- Local package version expected: `{report['local_version']}`",
        f"- Status: {report['status']}",
        f"- Temporary environment: `{report['temp_dir']}`",
        f"- Temporary environment cleanup: {cleanup_label}",
        f"- Install requirement: `{report['install_requirement']}`",
        f"- {report['disclosure']}",
        f"- {report['completion_rule']}",
        f"- {report['non_fabrication_notice']}",
    ]
    if report.get("failed_step"):
        lines.append(f"- Failed step: {report['failed_step']}")
    if report.get("cleanup_error"):
        lines.append(f"- Cleanup error: {report['cleanup_error']}")

    lines.extend([
        "",
        "## Candidate Install Command",
        "```bash",
        str(report["candidate_install_command"]),
        "```",
        "",
        "## Smoke Steps",
        "",
        "| Step | Status | Command | Evidence |",
        "| --- | --- | --- | --- |",
    ])
    for step in report["steps"]:
        stdout = str(step.get("stdout") or "").replace("\n", " / ")
        stderr = str(step.get("stderr") or "").replace("\n", " / ")
        evidence = stdout or stderr or f"returncode {step['returncode']}"
        missing = step.get("missing_stdout") or []
        if missing:
            evidence = f"missing stdout snippets: {', '.join(str(item) for item in missing)}; {evidence}"
        lines.append(
            f"| {step['name']} | {step['status']} | `{step['command_text']}` | {evidence} |"
        )
    return "\n".join(lines)
