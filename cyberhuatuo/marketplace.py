"""Marketplace release readiness checks for CyberHuaTuo."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib

import yaml

from . import __version__
from .achievements import get_cultivation_profile
from .traction import (
    DEFAULT_PYPI_PROJECT,
    DEFAULT_REPO,
    ISSUEOPS_REQUIRED_FILES,
    build_soul_ring_traction_proof,
    fetch_public_json,
)

LAUNCH_ASSET_METADATA_FILES = [
    ".github/workflows/publish-pypi.yml",
    ".github/workflows/package-claude-mcpb.yml",
    ".codex-plugin/plugin.json",
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    ".agents/plugins/marketplace.json",
    ".mcp.json",
    "pyproject.toml",
    "README.md",
    "README_MCP.md",
    "docs/MARKETPLACE_RELEASE.md",
    "docs/PRIVACY.md",
    "claude-desktop/manifest.json",
    "claude-desktop/pyproject.toml",
    "claude-desktop/src/server.py",
    "claude-desktop/.mcpbignore",
]

PUBLIC_GROWTH_RELEASE_BUNDLE_GROUPS = (
    (
        "IssueOps public acquisition routes",
        (
            ".github/ISSUE_TEMPLATE/config.yml",
            ".github/ISSUE_TEMPLATE/soul-ring-growth-flywheel.yml",
            ".github/workflows/soul-ring-growth-flywheel.yml",
            ".github/ISSUE_TEMPLATE/soul-ring-bounty-board.yml",
            ".github/workflows/soul-ring-bounty-board.yml",
            ".github/ISSUE_TEMPLATE/soul-ring-share-proof.yml",
            ".github/workflows/soul-ring-share-proof.yml",
            ".github/ISSUE_TEMPLATE/soul-ring-launch-campaign.yml",
            ".github/workflows/soul-ring-launch-campaign.yml",
            ".github/ISSUE_TEMPLATE/soul-ring-prescription.yml",
            ".github/workflows/soul-ring-issue.yml",
            ".github/workflows/soul-ring-pr.yml",
            ".github/workflows/soul-ring-promote.yml",
            ".github/ISSUE_TEMPLATE/soul-ring-season.yml",
            ".github/workflows/soul-ring-season.yml",
            ".github/ISSUE_TEMPLATE/soul-ring-mentor.yml",
            ".github/workflows/soul-ring-mentor.yml",
            ".github/ISSUE_TEMPLATE/soul-ring-sect-recruit.yml",
            ".github/workflows/soul-ring-sect-recruit.yml",
            ".github/ISSUE_TEMPLATE/soul-ring-tournament.yml",
            ".github/workflows/soul-ring-tournament.yml",
            ".github/pull_request_template.md",
        ),
    ),
    (
        "Marketplace package metadata and docs",
        (
            "README.md",
            "README_CN.md",
            "README_MCP.md",
            "docs/MARKETPLACE_RELEASE.md",
            "docs/PRIVACY.md",
            "docs/superpowers/specs/2026-06-02-soul-ring-growth-loop-design.md",
            "pyproject.toml",
            "requirements.txt",
            "MANIFEST.in",
            "CONTRIBUTING.md",
            ".codex-plugin/plugin.json",
            ".claude-plugin/plugin.json",
            ".claude-plugin/marketplace.json",
            ".agents/plugins/marketplace.json",
            ".mcp.json",
            "claude-desktop/manifest.json",
            "claude-desktop/pyproject.toml",
            "claude-desktop/README.md",
            "claude-desktop/src/server.py",
            "claude-desktop/.mcpbignore",
            ".github/workflows/ci.yml",
            ".github/workflows/publish-pypi.yml",
            ".github/workflows/package-claude-mcpb.yml",
        ),
    ),
    (
        "Public growth runtime modules and scripts",
        (
            "cyberhuatuo/activation.py",
            "cyberhuatuo/achievements.py",
            "cyberhuatuo/cli.py",
            "cyberhuatuo/install.py",
            "cyberhuatuo/marketplace.py",
            "cyberhuatuo/mcp_server.py",
            "cyberhuatuo/submissions.py",
            "cyberhuatuo/traction.py",
            "cyberhuatuo/__init__.py",
            "cyberhuatuo/__main__.py",
            "cyberhuatuo/api.py",
            "cyberhuatuo/bot_matcher.py",
            "cyberhuatuo/cli_effects.py",
            "cyberhuatuo/contributor.py",
            "cyberhuatuo/social.py",
        ),
    ),
    (
        "Growth tests and release gates",
        (
            "scripts/check_marketplace_release.py",
            "scripts/check_release_boundary.py",
            "tests/test_distribution_contracts.py",
            "tests/test_soul_ring_growth.py",
            "tests/test_quality_gates.py",
        ),
    ),
)


def _unique_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for path in paths:
        normalized = path.replace("\\", "/").strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)
    return unique


FULL_PUBLIC_GROWTH_RELEASE_BUNDLE = tuple(
    _unique_paths([
        path
        for _group, paths in PUBLIC_GROWTH_RELEASE_BUNDLE_GROUPS
        for path in paths
    ])
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _read_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _ok(name: str, *details: str, scope: str = "local") -> dict[str, Any]:
    return {"name": name, "status": "pass", "scope": scope, "details": [detail for detail in details if detail]}


def _warn(name: str, *details: str, scope: str = "remote") -> dict[str, Any]:
    return {"name": name, "status": "warn", "scope": scope, "details": [detail for detail in details if detail]}


def _fail(name: str, *details: str, scope: str = "local") -> dict[str, Any]:
    return {"name": name, "status": "fail", "scope": scope, "details": [detail for detail in details if detail]}


def _require_files(root: Path, files: list[str], name: str) -> dict[str, Any]:
    missing = [path for path in files if not (root / path).is_file()]
    if missing:
        return _fail(name, "Missing files: " + ", ".join(f"`{path}`" for path in missing))
    return _ok(name, "All required files exist.")


def _workflow_step_text(workflow: dict[str, Any]) -> str:
    jobs = workflow.get("jobs", {})
    chunks: list[str] = []
    if not isinstance(jobs, dict):
        return ""
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps", []) or []:
            if not isinstance(step, dict):
                continue
            chunks.extend(str(step.get(key, "")) for key in ("name", "run", "uses"))
    return "\n".join(chunks)


def _workflow_on(workflow: dict[str, Any]) -> Any:
    return workflow.get("on", workflow.get(True, {}))


def _asset_row(group: str, path: str, status: str, evidence: str) -> dict[str, str]:
    return {"group": group, "path": path, "status": status, "evidence": evidence}


def _issue_form_audit(root: Path, path: str) -> dict[str, str]:
    full_path = root / path
    if not full_path.is_file():
        return _asset_row("IssueOps acquisition bundle", path, "fail", "Missing local issue form.")
    try:
        form = _read_yaml(full_path)
    except (OSError, yaml.YAMLError) as exc:
        return _asset_row("IssueOps acquisition bundle", path, "fail", f"Could not parse issue form YAML: {exc}.")

    failures = []
    for key in ("name", "description", "title", "labels", "body"):
        if not form.get(key):
            failures.append(key)
    if not isinstance(form.get("body"), list):
        failures.append("body list")
    if failures:
        return _asset_row("IssueOps acquisition bundle", path, "fail", "Missing valid form fields: " + ", ".join(failures) + ".")
    return _asset_row("IssueOps acquisition bundle", path, "pass", "Issue form has name, description, title, labels, and body.")


def _issueops_workflow_audit(root: Path, path: str) -> dict[str, str]:
    full_path = root / path
    if not full_path.is_file():
        return _asset_row("IssueOps acquisition bundle", path, "fail", "Missing local comment workflow.")
    text = full_path.read_text(encoding="utf-8")
    try:
        workflow = _read_yaml(full_path)
    except (OSError, yaml.YAMLError) as exc:
        return _asset_row("IssueOps acquisition bundle", path, "fail", f"Could not parse workflow YAML: {exc}.")

    failures = []
    if not workflow.get("name"):
        failures.append("missing workflow name")
    event = _workflow_on(workflow)
    issues_event = event.get("issues", {}) if isinstance(event, dict) else {}
    if issues_event.get("types") != ["opened"]:
        failures.append("workflow must trigger on issues.opened")
    if workflow.get("permissions") != {"issues": "write", "contents": "read"}:
        failures.append("workflow permissions must be issues: write and contents: read")
    if "actions/checkout" in text:
        failures.append("comment workflow must not checkout code")
    if "\nrun:" in text:
        failures.append("comment workflow must not run repository scripts")

    if failures:
        return _asset_row("IssueOps acquisition bundle", path, "fail", "; ".join(failures) + ".")
    return _asset_row("IssueOps acquisition bundle", path, "pass", "Comment-only workflow uses issues.opened and minimal write permissions.")


def _metadata_file_audit(root: Path, path: str) -> dict[str, str]:
    full_path = root / path
    if not full_path.is_file():
        return _asset_row("Package and marketplace metadata", path, "fail", "Missing local release asset.")
    return _asset_row("Package and marketplace metadata", path, "pass", "Required release asset exists.")


def _read_git_status_lines(root: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=root,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            check=False,
        )
    except OSError as exc:
        return {"available": False, "source": "git status --porcelain", "error": str(exc), "lines": []}

    if result.returncode != 0:
        error = (result.stderr or result.stdout).strip() or f"git exited with {result.returncode}"
        return {"available": False, "source": "git status --porcelain", "error": error, "lines": []}

    return {
        "available": True,
        "source": "git status --porcelain",
        "error": "",
        "lines": result.stdout.splitlines(),
    }


def _path_is_in_bundle(path: str, bundle_paths: tuple[str, ...]) -> bool:
    if path in set(bundle_paths):
        return True
    prefix = path.rstrip("/") + "/"
    return any(bundle_path.startswith(prefix) for bundle_path in bundle_paths)


def _parse_git_status_line(line: str) -> dict[str, str] | None:
    if len(line) < 4:
        return None
    status = line[:2].strip() or line[:2]
    path = line[3:].strip()
    if " -> " in path:
        path = path.rsplit(" -> ", 1)[-1].strip()
    path = path.strip('"').replace("\\", "/")
    if not path:
        return None
    return {"status": status, "path": path}


def _build_dirty_worktree_report(
    root: Path,
    bundle_paths: tuple[str, ...],
    git_status_lines: list[str] | None,
) -> dict[str, Any]:
    status_payload = (
        {"available": True, "source": "provided git status lines", "error": "", "lines": git_status_lines}
        if git_status_lines is not None
        else _read_git_status_lines(root)
    )
    entries: list[dict[str, str]] = []
    for line in status_payload["lines"]:
        parsed = _parse_git_status_line(line)
        if parsed is None:
            continue
        coverage = (
            "full public growth release bundle"
            if _path_is_in_bundle(parsed["path"], bundle_paths)
            else "requires separate review"
        )
        entries.append({**parsed, "coverage": coverage})

    covered = [entry for entry in entries if entry["coverage"] == "full public growth release bundle"]
    outside = [entry for entry in entries if entry["coverage"] == "requires separate review"]
    return {
        "available": status_payload["available"],
        "source": status_payload["source"],
        "error": status_payload["error"],
        "entries": entries,
        "covered_count": len(covered),
        "outside_count": len(outside),
        "total_count": len(entries),
        "clean": status_payload["available"] and not entries,
        "review_notice": (
            "Review before release: changed files outside the full public growth release bundle "
            "must be staged intentionally or left out with a written reason."
        ),
    }


def _bundle_groups_for_output() -> list[dict[str, Any]]:
    return [
        {"name": group, "paths": list(paths), "git_add_command": "git add " + " ".join(paths)}
        for group, paths in PUBLIC_GROWTH_RELEASE_BUNDLE_GROUPS
    ]


def _version_from_release_tag(release_tag: str) -> str:
    release = _field_text(release_tag, "<release-tag>")
    if release == "<release-tag>":
        return "<version>"
    return release[1:] if release.startswith("v") and len(release) > 1 else release


def _release_web_links(repo: str, pypi_project: str, release_tag: str) -> list[dict[str, str]]:
    slug = _repo_slug(repo)
    release = _field_text(release_tag, "<release-tag>")
    clean_project = _field_text(pypi_project, DEFAULT_PYPI_PROJECT)
    return [
        {
            "label": "GitHub Web Release",
            "url": f"https://github.com/{slug}/releases/new?{urlencode({'tag': release})}",
            "note": "Use when GitHub CLI is unavailable; attach dist artifacts and publish a non-draft release.",
        },
        {
            "label": "GitHub Actions workflow page",
            "url": f"https://github.com/{slug}/actions/workflows/publish-pypi.yml",
            "note": "Use the Run workflow button with release_tag after the workflow is on the default branch.",
        },
        {
            "label": "PyPI Trusted Publisher settings",
            "url": f"https://pypi.org/manage/project/{clean_project}/settings/publishing/",
            "note": "Add this repository, workflow file, and pypi environment before publishing.",
        },
    ]


def _build_release_operator_runbook(
    *,
    repo: str = DEFAULT_REPO,
    pypi_project: str = DEFAULT_PYPI_PROJECT,
    release_tag: str = "",
    username: str = "your-github-username",
    framework: str = "langchain",
    target_contributors: int = 3,
) -> dict[str, Any]:
    clean_project = _field_text(pypi_project, DEFAULT_PYPI_PROJECT)
    release = _field_text(release_tag, "<release-tag>")
    version = _version_from_release_tag(release_tag)
    clean_username = _field_text(username, "your-github-username")
    clean_framework = _field_text(framework, "langchain")
    target = _positive_target(target_contributors)
    web_links = _release_web_links(repo, clean_project, release)
    release_audit_command = (
        f"python -m cyberhuatuo launch-assets --username {clean_username} "
        f"--framework {clean_framework} --release-tag {release} --target-contributors {target} "
        f"--repo {_repo_slug(repo)} --pypi-project {clean_project}"
    )
    return {
        "title": "Public Release Operator Runbook",
        "read_only": (
            "Read-only: this runbook prints release commands but does not stage, commit, "
            "push, tag, create releases, or publish packages."
        ),
        "repository": _repo_slug(repo),
        "release_tag": release,
        "version": version,
        "sections": [
            {
                "title": "Quality Gates",
                "commands": [
                    "python -m ruff check .",
                    "python -m pytest -q",
                    release_audit_command,
                    "python -m build --sdist --wheel",
                    "python scripts/check_release_boundary.py",
                    f"python -m twine check dist/{clean_project}-{version}*",
                ],
            },
            {
                "title": "Default Branch Handoff",
                "commands": [
                    "git status --short",
                    "# Use the Full Bundle Git Add Commands above, then review `git diff --cached`.",
                    "git diff --cached",
                    f'git commit -m "Release CyberHuaTuo {release} public growth loop"',
                    "git push origin HEAD:main",
                ],
            },
            {
                "title": "Release Or Protected Publish",
                "web_links": web_links,
                "commands": [
                    f'git tag -a {release} -m "CyberHuaTuo {release}"',
                    f"git push origin {release}",
                    (
                        f"gh release create {release} dist/{clean_project}-{version}.tar.gz "
                        f"dist/{clean_project}-{version}-py3-none-any.whl "
                        f"dist/{clean_project}-claude-desktop.mcpb --verify-tag --notes-from-tag"
                    ),
                    f"gh workflow run publish-pypi.yml -f release_tag={release}",
                    "gh run list --workflow publish-pypi.yml --limit 5",
                ],
            },
            {
                "title": "Registry And Proof Recheck",
                "commands": [
                    (
                        f"cyberhuatuo market-copy --username {clean_username} --framework {clean_framework} "
                        f"--release-tag {release} --target-contributors {target}"
                    ),
                    (
                        f"cyberhuatuo market-ready --remote --strict-remote --username {clean_username} "
                        f"--framework {clean_framework} --release-tag {release} --target-contributors {target}"
                    ),
                    (
                        f"python -m cyberhuatuo candidate-install-smoke --username {clean_username} "
                        f"--framework {clean_framework} --release-tag {release} --target-contributors {target} "
                        f"--repo {_repo_slug(repo)} --pypi-project {clean_project}"
                    ),
                    (
                        f"cyberhuatuo traction-proof --username {clean_username} --framework {clean_framework} "
                        f"--release-tag {release} --target-contributors {target}"
                    ),
                    (
                        f"python scripts/check_marketplace_release.py --remote --strict-remote --username {clean_username} "
                        f"--framework {clean_framework} --release-tag {release} --target-contributors {target}"
                    ),
                ],
            },
        ],
        "web_links": web_links,
        "validation_points": [
            "workflow_dispatch requires `.github/workflows/publish-pypi.yml` to be on the default branch.",
            "GitHub Web Release can prefill the tag when GitHub CLI is unavailable.",
            "GitHub Actions workflow page exposes the manual Run workflow button for workflow_dispatch.",
            "`gh release create --verify-tag` keeps the public GitHub Release tied to the pushed tag.",
            "PyPI Trusted Publisher must match this repository, workflow file, and `pypi` environment.",
            "No `PYPI_TOKEN` fallback is allowed.",
            "First proof still requires a created public Issue, PR, Discussion, release, or social URL.",
            "Run `python -m cyberhuatuo candidate-install-smoke` before sharing a Git tag candidate bridge with outside contributors.",
        ],
    }


def build_launch_asset_audit(
    root: str | Path = ".",
    *,
    git_status_lines: list[str] | None = None,
    repo: str = DEFAULT_REPO,
    pypi_project: str = DEFAULT_PYPI_PROJECT,
    release_tag: str = "",
    username: str = "your-github-username",
    framework: str = "langchain",
    target_contributors: int = 3,
) -> dict[str, Any]:
    """Build a read-only local audit of launch assets that must reach the default branch."""
    root_path = Path(root).resolve()
    rows: list[dict[str, str]] = []
    for _label, path in ISSUEOPS_REQUIRED_FILES:
        if path.startswith(".github/ISSUE_TEMPLATE/"):
            rows.append(_issue_form_audit(root_path, path))
        elif path.startswith(".github/workflows/"):
            rows.append(_issueops_workflow_audit(root_path, path))
        else:
            rows.append(_metadata_file_audit(root_path, path))

    rows.extend(_metadata_file_audit(root_path, path) for path in LAUNCH_ASSET_METADATA_FILES)

    release_checks = [
        _version_sync_check(root_path),
        _pypi_local_check(root_path),
        _claude_local_check(root_path),
        _codex_local_check(root_path),
        _issueops_local_check(root_path),
    ]
    for check in release_checks:
        status = "pass" if check["status"] == "pass" else "fail"
        evidence = "; ".join(check.get("details") or [check["status"]])
        rows.append(_asset_row("Release contract checks", check["name"], status, evidence))

    status = "pass" if all(row["status"] == "pass" for row in rows) else "fail"
    issueops_paths = [path for _label, path in ISSUEOPS_REQUIRED_FILES]
    metadata_paths = LAUNCH_ASSET_METADATA_FILES
    return {
        "title": "Local Launch Asset Audit",
        "root": str(root_path),
        "status": status,
        "read_only": True,
        "disclosure": "Read-only: does not stage files, publish releases, upload to PyPI, mutate remotes, or claim traction.",
        "rows": rows,
        "minimal_git_add_commands": [
            "git add " + " ".join(issueops_paths),
            "git add " + " ".join(metadata_paths),
        ],
        "full_release_bundle_groups": _bundle_groups_for_output(),
        "full_release_bundle_paths": list(FULL_PUBLIC_GROWTH_RELEASE_BUNDLE),
        "release_operator_runbook": _build_release_operator_runbook(
            repo=repo,
            pypi_project=pypi_project,
            release_tag=release_tag,
            username=username,
            framework=framework,
            target_contributors=target_contributors,
        ),
        "dirty_worktree": _build_dirty_worktree_report(
            root_path,
            FULL_PUBLIC_GROWTH_RELEASE_BUNDLE,
            git_status_lines,
        ),
    }


def _version_sync_check(root: Path) -> dict[str, Any]:
    try:
        project = _read_toml(root / "pyproject.toml")["project"]
        version = project["version"]
        package_init = (root / "cyberhuatuo" / "__init__.py").read_text(encoding="utf-8")
        codex_manifest = _read_json(root / ".codex-plugin" / "plugin.json")
        claude_manifest = _read_json(root / ".claude-plugin" / "plugin.json")
        claude_marketplace = _read_json(root / ".claude-plugin" / "marketplace.json")
        desktop_manifest = _read_json(root / "claude-desktop" / "manifest.json")
        desktop_project = _read_toml(root / "claude-desktop" / "pyproject.toml")["project"]
    except (KeyError, OSError, json.JSONDecodeError) as exc:
        return _fail("Version sync", f"Could not read release metadata: {exc}")

    mismatches = []
    expected = {
        "cyberhuatuo.__version__": f'__version__ = "{version}"' in package_init,
        ".codex-plugin/plugin.json": codex_manifest.get("version") == version,
        ".claude-plugin/plugin.json": claude_manifest.get("version") == version,
        ".claude-plugin/marketplace.json": (claude_marketplace.get("plugins") or [{}])[0].get("version") == version,
        "claude-desktop/manifest.json": desktop_manifest.get("version") == version,
        "claude-desktop/pyproject.toml": desktop_project.get("version") == version,
        "claude-desktop dependency pin": desktop_project.get("dependencies") == [f"cyberhuatuo=={version}"],
    }
    for label, matched in expected.items():
        if not matched:
            mismatches.append(label)

    if mismatches:
        return _fail("Version sync", "Mismatched release version fields: " + ", ".join(mismatches))
    return _ok("Version sync", f"All release surfaces use `{version}`.", f"PyPI package name: `{project['name']}`.")


def _pypi_local_check(root: Path) -> dict[str, Any]:
    workflow_path = root / ".github" / "workflows" / "publish-pypi.yml"
    if not workflow_path.is_file():
        return _fail("PyPI local release chain", "Missing `.github/workflows/publish-pypi.yml`.")
    workflow = _read_yaml(workflow_path)
    event = _workflow_on(workflow)
    job = (workflow.get("jobs") or {}).get("publish", {})
    steps = job.get("steps", []) if isinstance(job, dict) else []
    step_text = _workflow_step_text(workflow)
    failures = []

    if workflow.get("name") != "Publish PyPI":
        failures.append("workflow name is not `Publish PyPI`")
    release_event = event.get("release", {}) if isinstance(event, dict) else {}
    if release_event.get("types") != ["published"]:
        failures.append("workflow must trigger on release.published")
    dispatch_event = event.get("workflow_dispatch", {}) if isinstance(event, dict) else {}
    dispatch_input = ((dispatch_event.get("inputs") or {}).get("release_tag") or {}) if isinstance(dispatch_event, dict) else {}
    if dispatch_input.get("required") is not True or dispatch_input.get("type") != "string":
        failures.append("workflow_dispatch must require a string `release_tag` input")
    if job.get("environment") != "pypi":
        failures.append("publish job must use GitHub environment `pypi`")
    if job.get("permissions") != {"contents": "read", "id-token": "write"}:
        failures.append("publish job must request only contents: read and id-token: write")
    checkout_step = next(
        (step for step in steps if isinstance(step, dict) and step.get("uses") == "actions/checkout@v4"),
        {},
    )
    checkout_with = checkout_step.get("with", {}) if isinstance(checkout_step, dict) else {}
    if checkout_with.get("ref") != "${{ steps.release.outputs.tag }}":
        failures.append("checkout must use the resolved release tag")
    if checkout_with.get("fetch-depth") != 0:
        failures.append("checkout must use fetch-depth: 0")
    for required in (
        "Resolve release tag",
        "manual workflow_dispatch release_tag must start with v",
        "actions/checkout@v4",
        "git fetch --force origin main:refs/remotes/origin/main",
        "git merge-base --is-ancestor",
        "Package version matches release tag",
        'python -m pip install -e ".[dev]"',
        "python -m ruff check .",
        "python -m pytest -q",
        "python -m cyberhuatuo launch-assets",
        "python -m build --sdist --wheel",
        "python scripts/check_release_boundary.py",
        "pypa/gh-action-pypi-publish@release/v1",
    ):
        if required not in step_text:
            failures.append(f"missing step `{required}`")
    if "PYPI_TOKEN" in workflow_path.read_text(encoding="utf-8"):
        failures.append("workflow must not use stored `PYPI_TOKEN`")

    if failures:
        return _fail("PyPI local release chain", *failures)
    return _ok(
        "PyPI local release chain",
        "Trusted Publishing workflow supports release.published plus a protected manual workflow_dispatch tag fallback, then runs launch-assets/lint/tests/build/release-boundary before upload.",
        "External requirement: add this repo/workflow/environment as a Trusted Publisher on the existing PyPI project.",
    )


def _claude_local_check(root: Path) -> dict[str, Any]:
    files = [
        ".claude-plugin/plugin.json",
        ".claude-plugin/marketplace.json",
        "claude-desktop/manifest.json",
        "claude-desktop/pyproject.toml",
        "claude-desktop/src/server.py",
        "claude-desktop/.mcpbignore",
        "docs/PRIVACY.md",
        ".github/workflows/package-claude-mcpb.yml",
    ]
    file_check = _require_files(root, files, "Claude local release chain")
    if file_check["status"] == "fail":
        return file_check

    manifest = _read_json(root / "claude-desktop" / "manifest.json")
    workflow = _read_yaml(root / ".github" / "workflows" / "package-claude-mcpb.yml")
    step_text = _workflow_step_text(workflow)
    failures = []
    if manifest.get("server", {}).get("type") != "uv":
        failures.append("Claude Desktop MCPB server type must be `uv`")
    if not manifest.get("privacy_policies"):
        failures.append("Claude Desktop manifest must link a privacy policy")
    for required in ("mcpb validate claude-desktop", "mcpb pack claude-desktop dist/cyberhuatuo-claude-desktop.mcpb"):
        if required not in step_text:
            failures.append(f"missing workflow step `{required}`")

    if failures:
        return _fail("Claude local release chain", *failures)
    return _ok(
        "Claude local release chain",
        "Claude Code plugin catalog and Claude Desktop MCPB assets are present.",
        "Validate with `claude plugin validate .`, then `mcpb validate claude-desktop` and `mcpb pack claude-desktop dist/cyberhuatuo-claude-desktop.mcpb`.",
    )


def _codex_local_check(root: Path) -> dict[str, Any]:
    files = [
        ".codex-plugin/plugin.json",
        ".agents/plugins/marketplace.json",
        ".mcp.json",
        "skills/cyberhuatuo-rescue/SKILL.md",
    ]
    file_check = _require_files(root, files, "Codex local release chain")
    if file_check["status"] == "fail":
        return file_check

    codex_manifest = _read_json(root / ".codex-plugin" / "plugin.json")
    marketplace = _read_json(root / ".agents" / "plugins" / "marketplace.json")
    mcp_config = _read_json(root / ".mcp.json")
    server = (mcp_config.get("mcpServers") or {}).get("cyberhuatuo", {})
    failures = []
    if codex_manifest.get("skills") != "./skills/":
        failures.append("Codex manifest must point to `./skills/`")
    if codex_manifest.get("mcpServers") != "./.mcp.json":
        failures.append("Codex manifest must point to `./.mcp.json`")
    if server.get("command") != "uvx" or server.get("args") != ["--from", "cyberhuatuo", "cyberhuatuo-mcp"]:
        failures.append("MCP config must use `uvx --from cyberhuatuo cyberhuatuo-mcp`")
    if (marketplace.get("plugins") or [{}])[0].get("source") != {"source": "local", "path": "./"}:
        failures.append("Codex marketplace catalog must point at the repository root")

    if failures:
        return _fail("Codex local release chain", *failures)
    return _ok(
        "Codex local release chain",
        "Codex plugin manifest, marketplace catalog, skill path, and MCP install command are aligned.",
        "Install path after PyPI release: `codex mcp add cyberhuatuo -- uvx --from cyberhuatuo cyberhuatuo-mcp`.",
    )


def _issueops_local_check(root: Path) -> dict[str, Any]:
    paths = [path for _label, path in ISSUEOPS_REQUIRED_FILES]
    missing = [path for path in paths if not (root / path).is_file()]
    if missing:
        return _fail("IssueOps local acquisition files", "Missing files: " + ", ".join(f"`{path}`" for path in missing))

    unsafe = []
    for path in paths:
        text = (root / path).read_text(encoding="utf-8")
        if path.startswith(".github/workflows/") and ("actions/checkout" in text or "\nrun:" in text):
            unsafe.append(path)
    if unsafe:
        return _fail("IssueOps local acquisition files", "Comment-only workflows contain checkout/run steps: " + ", ".join(unsafe))
    return _ok(
        "IssueOps local acquisition files",
        (
            "First Soul Ring, Growth Flywheel, Bounty Board, Share Proof, Launch Campaign, "
            "Tournament, Mentor Pact, Sect Recruitment, and Season Board forms/workflows exist locally."
        ),
        "External requirement: push these files to the repository default branch before treating `issues/new?...` links as live loops.",
    )


def _remote_checks(
    *,
    repo: str,
    pypi_project: str,
    username: str,
    framework: str,
    release_tag: str,
    target_contributors: int,
    timeout: int,
    strict_remote: bool,
    fetcher,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    proof = build_soul_ring_traction_proof(
        username,
        framework,
        release_tag=release_tag,
        target_contributors=target_contributors,
        repo=repo,
        pypi_project=pypi_project,
        timeout=timeout,
        fetcher=fetcher,
    )
    checks: list[dict[str, Any]] = []
    remote_fail = _fail if strict_remote else _warn

    issueops = proof["issueops_readiness"]
    if issueops["ready"]:
        checks.append(_ok("Remote IssueOps default branch", "All required IssueOps files are visible through GitHub Contents API.", scope="remote"))
    else:
        missing = ", ".join(f"`{row['path']}`" for row in issueops["missing"])
        checks.append(remote_fail(
            "Remote IssueOps default branch",
            f"{issueops['missing_count']} required files are missing or unverified: {missing}",
            "Recovery: merge the local IssueOps forms/workflows to the repository default branch.",
            scope="remote",
        ))

    release = proof["release_readiness"]
    distribution = proof["distribution_readiness"]
    if release["ready"]:
        checks.append(_ok("GitHub release trigger", release["reason"], scope="remote"))
    elif distribution["ready"]:
        fallback_reason = release["reason"].replace("release-trigger launch blocker: ", "")
        checks.append(_warn(
            "GitHub release trigger",
            f"GitHub Release is not verified, but PyPI latest-version proof is current: {fallback_reason}",
            (
                "Protected workflow_dispatch release_tag fallback can close the registry path; "
                "Publish a GitHub Release for public provenance."
            ),
            scope="remote",
        ))
    else:
        release_recovery = (
            "Recovery: Re-run with `GITHUB_TOKEN` or `GH_TOKEN` if GitHub API access is rate-limited; "
            "if the tag is truly missing, publish a non-draft, non-prerelease GitHub Release so "
            "`.github/workflows/publish-pypi.yml` can run on `release.published`, or run the protected "
            "manual `workflow_dispatch` `release_tag` fallback when release publication is unavailable."
            if release["status"] == "unverified"
            else (
                "Recovery: Publish a non-draft, non-prerelease GitHub Release so "
                "`.github/workflows/publish-pypi.yml` can run on `release.published`, or run the protected "
                "manual `workflow_dispatch` `release_tag` fallback when release publication is unavailable."
            )
        )
        checks.append(remote_fail(
            "GitHub release trigger",
            release["reason"],
            release_recovery,
            scope="remote",
        ))

    if distribution["ready"]:
        checks.append(_ok("PyPI remote package", distribution["reason"], scope="remote"))
    else:
        checks.append(remote_fail(
            "PyPI remote package",
            distribution["reason"],
            "Recovery: publish through `.github/workflows/publish-pypi.yml`, then re-run `cyberhuatuo traction-proof`.",
            scope="remote",
        ))

    checks.append(_warn("Remote traction weakest bridge", proof["weakest"], scope="remote"))
    return checks, proof


def _find_check(checks: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    return next((check for check in checks if check.get("name") == name), None)


def _row(order: int, gate: str, status: str, evidence: str, next_action: str) -> dict[str, Any]:
    return {
        "order": order,
        "gate": gate,
        "status": status,
        "evidence": evidence,
        "next_action": next_action,
    }


def _build_launch_closure_checklist(
    checks: list[dict[str, Any]],
    *,
    proof: dict[str, Any] | None,
    remote: bool,
    username: str,
    framework: str,
    release_tag: str,
    target_contributors: int,
) -> list[dict[str, Any]]:
    local_issueops = _find_check(checks, "IssueOps local acquisition files")
    local_pypi = _find_check(checks, "PyPI local release chain")
    release = release_tag or "<tag>"
    strict_command = (
        f"cyberhuatuo market-ready --remote --strict-remote --username {username} "
        f"--framework {framework} --release-tag {release} --target-contributors {target_contributors}"
    )
    proof_command = (
        f"cyberhuatuo traction-proof --username {username} --framework {framework} "
        f"--release-tag {release} --target-contributors {target_contributors}"
    )

    if proof is None:
        acquisition_status = "pending" if local_issueops and local_issueops["status"] == "pass" else "fail"
        publisher_status = "manual" if local_pypi and local_pypi["status"] == "pass" else "fail"
        return [
            _row(
                1,
                "Remote acquisition routes",
                acquisition_status,
                "Local full public acquisition IssueOps files exist; default branch not verified."
                if acquisition_status == "pending"
                else "Local IssueOps files are incomplete.",
                "Push the full public acquisition IssueOps bundle to the repository default branch, then run the strict remote market-ready gate.",
            ),
            _row(
                2,
                "PyPI Trusted Publisher",
                publisher_status,
                "Local OIDC workflow is ready; PyPI project publisher configuration is a maintainer-side manual setting."
                if publisher_status == "manual"
                else "Local PyPI publishing workflow is incomplete.",
                "Add owner/repo `JinNing6/CyberHuaTuo-Plugin`, workflow `.github/workflows/publish-pypi.yml`, environment `pypi` as a PyPI Trusted Publisher.",
            ),
            _row(
                3,
                "GitHub release trigger",
                "pending",
                "`release.published` cannot be verified until a public GitHub Release tag exists.",
                "Publish a non-draft, non-prerelease GitHub Release for the target version.",
            ),
            _row(
                4,
                "Registry latest-version proof",
                "pending",
                "PyPI JSON API latest-version proof was not requested in local-only mode.",
                "After the publish workflow completes, verify PyPI latest version with the strict remote gate.",
            ),
            _row(
                5,
                "First public proof",
                "pending",
                "No real public contributor identity proof has been fetched yet.",
                "Open the Growth or Share Proof Issue route, then record the created public URL with record-return or record-share.",
            ),
            _row(
                6,
                "Recheck commands",
                "pass",
                "Local CLI and release script expose repeatable preflight and proof commands.",
                f"Run `{strict_command}` and `{proof_command}`.",
            ),
        ]

    issueops = proof["issueops_readiness"]
    release_readiness = proof["release_readiness"]
    distribution = proof["distribution_readiness"]
    contributors = len(proof["contributor_actors"])
    target = proof["target"]

    acquisition_status = "pass" if issueops["ready"] else "fail"
    registry_status = "pass" if distribution["ready"] else "fail"
    release_status = "pass" if release_readiness["ready"] else ("fallback" if registry_status == "pass" else "fail")
    publisher_status = "pass" if distribution["ready"] else "manual"
    public_proof_status = "pass" if contributors >= target else "pending"
    if remote and acquisition_status == "fail":
        public_proof_status = "pending"

    return [
        _row(
            1,
            "Remote acquisition routes",
            acquisition_status,
            "GitHub Contents API sees the required full public acquisition IssueOps files on the default branch."
            if acquisition_status == "pass"
            else f"{issueops['missing_count']} default-branch IssueOps files are missing or unverified.",
            (
                "Keep First Soul Ring, Growth, Bounty, Share, Launch, Tournament, Mentor, "
                "Sect Recruitment, and Season IssueOps files on the default branch."
            )
            if acquisition_status == "pass"
            else "Merge the local IssueOps forms/workflows before using public issue-form URLs.",
        ),
        _row(
            2,
            "PyPI Trusted Publisher",
            publisher_status,
            "PyPI serves the current local version, so the registry path has produced the expected release."
            if publisher_status == "pass"
            else "PyPI Trusted Publisher setup is not publicly inspectable and the registry latest version is not current.",
            "Keep the GitHub `pypi` environment protected."
            if publisher_status == "pass"
            else "Add the repository/workflow/environment as a PyPI Trusted Publisher, publish the release, then re-run the gate.",
        ),
        _row(
            3,
            "GitHub release trigger",
            release_status,
            release_readiness["reason"]
            if release_status != "fallback"
            else (
                "GitHub Release is not verified, but PyPI latest-version proof is current; "
                "the protected workflow_dispatch release_tag fallback can close the registry path."
            ),
            "The `release.published` trigger is ready for the PyPI workflow."
            if release_status == "pass"
            else (
                "Publish a GitHub Release for public provenance."
                if release_status == "fallback"
                else (
                    "Publish a non-draft, non-prerelease GitHub Release for the target version, or run the "
                    "protected manual workflow_dispatch release_tag fallback when release publication is unavailable."
                )
            ),
        ),
        _row(
            4,
            "Registry latest-version proof",
            registry_status,
            distribution["reason"],
            "Clean installs should receive the current marketplace build."
            if registry_status == "pass"
            else "Wait for or fix the PyPI workflow, then verify PyPI JSON API latest version again.",
        ),
        _row(
            5,
            "First public proof",
            public_proof_status,
            f"Observed {contributors} / {target} real contributor identities from public issues, PRs, and local ledger actors.",
            "Raise the target or open the next campaign."
            if public_proof_status == "pass"
            else "Create Growth or Share Proof issues, then record the created public URLs in the activation/share ledger.",
        ),
        _row(
            6,
            "Recheck commands",
            "pass",
            "Preflight and traction proof commands are repeatable from CLI, script, and MCP.",
            f"Run `{strict_command}` and `{proof_command}`.",
        ),
    ]


_CLOSURE_READY_STATUSES = {"pass", "fallback"}


def _build_flywheel_closure_verdict(
    checklist: list[dict[str, Any]],
    *,
    remote_checked: bool,
    local_ready: bool,
) -> dict[str, Any]:
    total = len(checklist)
    ready_rows = [
        row
        for row in checklist
        if str(row.get("status", "")).strip().lower() in _CLOSURE_READY_STATUSES
    ]
    blocking_rows = [
        row
        for row in checklist
        if str(row.get("status", "")).strip().lower() not in _CLOSURE_READY_STATUSES
    ]
    blocking_gates = [str(row.get("gate", "")) for row in blocking_rows if row.get("gate")]

    if not local_ready:
        verdict = "not closed"
        summary = "Local release contracts are failing; the public flywheel cannot be closed."
    elif not remote_checked:
        verdict = "unverified"
        summary = "Public state was not fetched; local release readiness is not proof of a closed public flywheel."
    elif blocking_rows:
        verdict = "not closed"
        summary = "Closure blockers: " + ", ".join(blocking_gates) + "."
    else:
        verdict = "closed"
        summary = "All closure gates are supported by real local and public evidence."

    return {
        "title": "Flywheel Closure Verdict",
        "verdict": verdict,
        "ready_count": len(ready_rows),
        "total_gates": total,
        "blocking_gates": blocking_gates,
        "summary": summary,
        "evidence_basis": (
            "Closure uses local release gates plus GitHub Contents API, GitHub Releases API, "
            "PyPI JSON API, public Issue/PR authors, and local activation/share ledger actors "
            "when remote mode is enabled."
        ),
        "non_fabrication_notice": (
            "No downloads, retention, repost counts, referrals, rewards, reviews, or fake contributors are claimed."
        ),
        "rows": checklist,
    }


def build_marketplace_readiness(
    root: str | Path = ".",
    *,
    remote: bool = False,
    strict_remote: bool = False,
    repo: str = DEFAULT_REPO,
    pypi_project: str = DEFAULT_PYPI_PROJECT,
    username: str = "your-github-username",
    framework: str = "langchain",
    release_tag: str = "",
    target_contributors: int = 3,
    timeout: int = 10,
    fetcher=fetch_public_json,
) -> dict[str, Any]:
    """Build a local and optional remote marketplace readiness report."""
    root_path = Path(root).resolve()
    checks = [
        _version_sync_check(root_path),
        _pypi_local_check(root_path),
        _claude_local_check(root_path),
        _codex_local_check(root_path),
        _issueops_local_check(root_path),
    ]
    proof = None
    if remote:
        remote_checks, proof = _remote_checks(
            repo=repo,
            pypi_project=pypi_project,
            username=username,
            framework=framework,
            release_tag=release_tag,
            target_contributors=target_contributors,
            timeout=timeout,
            strict_remote=strict_remote,
            fetcher=fetcher,
        )
        checks.extend(remote_checks)

    local_ready = all(check["status"] != "fail" for check in checks if check["scope"] == "local")
    remote_ready = (
        False
        if remote and any(check["status"] == "fail" for check in checks if check["scope"] == "remote")
        else bool(remote)
    )
    exit_code = 0
    if not local_ready or (strict_remote and remote and not remote_ready):
        exit_code = 1

    closure_checklist = _build_launch_closure_checklist(
        checks,
        proof=proof,
        remote=remote,
        username=username,
        framework=framework,
        release_tag=release_tag,
        target_contributors=target_contributors,
    )
    closure_verdict = _build_flywheel_closure_verdict(
        closure_checklist,
        remote_checked=bool(remote),
        local_ready=local_ready,
    )
    first_public_proof_kit = build_first_public_proof_pack(
        repo=repo,
        pypi_project=pypi_project,
        username=username,
        framework=framework,
        release_tag=release_tag,
        target_contributors=target_contributors,
    )

    return {
        "title": "Marketplace Readiness Gate",
        "root": str(root_path),
        "repo": repo,
        "pypi_project": pypi_project,
        "release_tag": release_tag,
        "checks": checks,
        "local_ready": local_ready,
        "remote_checked": bool(remote),
        "remote_ready": remote_ready,
        "strict_remote": bool(strict_remote),
        "exit_code": exit_code,
        "traction_proof": proof,
        "closure_verdict": closure_verdict,
        "closure_checklist": closure_checklist,
        "first_public_proof_kit": first_public_proof_kit,
        "launch_asset_audit": build_launch_asset_audit(
            root_path,
            repo=repo,
            pypi_project=pypi_project,
            release_tag=release_tag,
            username=username,
            framework=framework,
            target_contributors=target_contributors,
        ),
    }


def _format_check(check: dict[str, Any]) -> list[str]:
    lines = [f"- {check['name']}: {check['status']}"]
    for detail in check.get("details", []):
        lines.append(f"  - {detail}")
    return lines


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def format_launch_asset_audit(audit: dict[str, Any], *, heading_level: int = 1) -> str:
    """Format the local launch asset audit as markdown."""
    prefix = "#" * max(1, heading_level)
    section = "##" if heading_level == 1 else "###"
    subsection = "###" if heading_level == 1 else "####"
    lines = [
        f"{prefix} Local Launch Asset Audit",
        "",
        f"- Repository root: `{audit['root']}`",
        f"- Status: {audit['status']}",
        f"- {audit['disclosure']}",
        "",
        f"{section} Asset Checks",
        "| Group | Path | Status | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for row in audit.get("rows", []):
        lines.append(
            f"| {_cell(row['group'])} | {_cell(row['path'])} | {_cell(row['status'])} | {_cell(row['evidence'])} |"
        )
    lines.extend([
        "",
        f"{section} Minimal Git Add Commands",
        "```bash",
        *audit.get("minimal_git_add_commands", []),
        "```",
        "",
        f"{section} Full Public Growth Release Bundle",
        "",
        "This full bundle prevents publishing stale PyPI/Claude/Codex growth code after only the public IssueOps routes are staged.",
        "",
        "| Group | Files |",
        "| --- | --- |",
    ])
    for group in audit.get("full_release_bundle_groups", []):
        paths = ", ".join(f"`{path}`" for path in group.get("paths", []))
        lines.append(f"| {_cell(group.get('name', ''))} | {_cell(paths)} |")

    full_commands = [
        str(group.get("git_add_command", ""))
        for group in audit.get("full_release_bundle_groups", [])
        if group.get("git_add_command")
    ]
    lines.extend([
        "",
        f"{section} Full Bundle Git Add Commands",
        "```bash",
        *full_commands,
        "```",
        "",
    ])

    runbook = audit.get("release_operator_runbook") or {}
    if runbook:
        lines.extend([
            f"{section} Public Release Operator Runbook",
            "",
            f"- {runbook['read_only']}",
            f"- Repository: `{runbook['repository']}`",
            f"- Release tag: `{runbook['release_tag']}`",
            f"- Package version: `{runbook['version']}`",
        ])
        for block in runbook.get("sections", []):
            lines.extend([
                "",
                f"{subsection} {block['title']}",
            ])
            links = block.get("web_links") or []
            if links:
                lines.extend(f"- {link['label']}: {link['url']}" for link in links)
                lines.extend(f"  - {link['note']}" for link in links if link.get("note"))
            commands = block.get("commands", [])
            if commands:
                lines.extend([
                    "```bash",
                    *commands,
                    "```",
                ])
        lines.extend(["", f"{subsection} Validation Boundaries"])
        lines.extend(f"- {point}" for point in runbook.get("validation_points", []))
        lines.append("")

    lines.extend([
        f"{section} Dirty Worktree Release Coverage",
        "",
        "- Captured with read-only `git status --porcelain` when available.",
    ])
    dirty = audit.get("dirty_worktree") or {}
    if not dirty.get("available"):
        lines.append(f"- Git status unavailable: {dirty.get('error', 'unknown error')}")
    elif dirty.get("clean"):
        lines.append("- Worktree status: clean; no changed tracked or untracked files were reported.")
    else:
        lines.extend([
            (
                "- Worktree status: "
                f"{dirty.get('covered_count', 0)} covered by the full bundle; "
                f"{dirty.get('outside_count', 0)} require separate review."
            ),
            "",
            "| Status | Path | Release coverage |",
            "| --- | --- | --- |",
        ])
        for entry in dirty.get("entries", []):
            lines.append(
                f"| {_cell(entry.get('status', ''))} | {_cell(entry.get('path', ''))} | "
                f"{_cell(entry.get('coverage', ''))} |"
            )
        lines.extend(["", f"- {dirty.get('review_notice', '')}"])

    lines.extend([
        "",
        "These commands are printed for review only; this audit does not stage files or mutate remote state.",
    ])
    return "\n".join(lines)


def _field_text(value: Any, default: str, *, limit: int = 180) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    if not text:
        text = default
    return " ".join(text.split())[:limit]


def _repo_slug(repo: str) -> str:
    text = _field_text(repo, DEFAULT_REPO, limit=220)
    for prefix in ("https://github.com/", "http://github.com/"):
        if text.startswith(prefix):
            text = text.removeprefix(prefix)
    if text.endswith(".git"):
        text = text[:-4]
    parts = [part for part in text.strip("/").split("/") if part]
    if len(parts) < 2:
        return DEFAULT_REPO
    return "/".join(parts[:2])


def _positive_target(value: int) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return 3


def _install_decision_command(
    *,
    repo: str,
    pypi_project: str,
    username: str,
    framework: str,
    release_tag: str,
    target_contributors: int,
) -> str:
    return (
        f"cyberhuatuo install-command --username {username} --framework {framework} "
        f"--release-tag {release_tag} --target-contributors {target_contributors} "
        f"--repo {repo} --pypi-project {pypi_project}"
    )


def _candidate_install_smoke_command(
    *,
    repo: str,
    pypi_project: str,
    username: str,
    framework: str,
    release_tag: str,
    target_contributors: int,
) -> str:
    return (
        f"python -m cyberhuatuo candidate-install-smoke --username {username} --framework {framework} "
        f"--release-tag {release_tag} --target-contributors {target_contributors} "
        f"--repo {repo} --pypi-project {pypi_project}"
    )


def _install_decision_surface(
    *,
    command: str,
    mcp_tool: str = "current_install_command",
) -> dict[str, str]:
    return {
        "command": command,
        "mcp_tool": mcp_tool,
        "rule": (
            "Run the CLI install decision or call the MCP install decision tool before sending anyone to "
            "PyPI, Claude, Codex, or an MCP marketplace; paste its Recommended Install into the invite. "
            "Canonical PyPI install is valid only when registry proof is current, otherwise use the bounded "
            "Git tag bridge without claiming the PyPI install loop is closed."
        ),
    }


def _build_first_public_proof_kit(
    *,
    repo: str,
    pypi_project: str,
    username: str,
    framework: str,
    release_tag: str,
    target_contributors: int,
) -> dict[str, Any]:
    slug = _repo_slug(repo)
    repo_url = f"https://github.com/{slug}"
    clean_username = _field_text(username, "your-github-username")
    clean_framework = _field_text(framework, "langchain")
    clean_project = _field_text(pypi_project, DEFAULT_PYPI_PROJECT)
    release = _field_text(release_tag, "<release-tag>")
    target = _positive_target(target_contributors)
    created_growth_url = "<created Growth Issue URL after submission>"
    created_share_url = "<created Share Proof Issue URL after submission>"
    created_bounty_url = "<created Bounty Board Issue URL after submission>"
    created_prescription_url = "<created First Soul Ring Prescription Issue URL after submission>"
    public_share_url = "<public share URL after posting>"
    external_username = "<external-contributor-github-username>"

    growth_params = {
        "template": "soul-ring-growth-flywheel.yml",
        "title": f"[Soul Ring Growth] First public proof for {clean_username}",
        "github_username": clean_username,
        "framework": clean_framework,
        "growth_surface": "PyPI release",
        "real_signal": (
            f"CyberHuaTuo {release} market-ready preflight for PyPI project `{clean_project}`. "
            "Use the created issue URL after submission as proof."
        ),
        "bottleneck_guess": "First public proof is pending: submit this issue, then record the created public URL.",
        "campaign_hook": (
            f"Recruit {target} real first-ring contributors through install, issue proof, ledger attribution, "
            "and share proof."
        ),
    }
    share_params = {
        "template": "soul-ring-share-proof.yml",
        "title": f"[Soul Ring Share Proof] {clean_framework} {release} first public proof",
        "github_username": clean_username,
        "framework": clean_framework,
        "share_url": public_share_url,
        "source_url": created_growth_url,
        "proof_context": (
            f"First public CyberHuaTuo {release} share proof. Record only created public Issue, PR, "
            "Discussion, release, or social post URLs."
        ),
    }
    bounty_params = {
        "template": "soul-ring-bounty-board.yml",
        "title": f"[Soul Ring Bounty] {release} claimable framework gaps",
        "github_username": clean_username,
        "framework": "auto",
        "top_n": "8",
        "release_tag": release,
        "target_contributors": str(target),
        "real_data_ack": (
            "I understand this board must use real local case coverage and must not invent downloads, "
            "retention, repost counts, referrals, rewards, reviews, or fake contributors."
        ),
    }
    prescription_params = {
        "template": "soul-ring-prescription.yml",
        "title": f"[Soul Ring Prescription] {clean_framework} first external contributor proof",
        "github_username": external_username,
        "framework": clean_framework,
        "symptom": "<real error, traceback, broken behavior, environment, and reproduction steps>",
        "root_cause": "<real root cause after investigation>",
        "prescription": "<real fix, commands, patch, or configuration change>",
        "verification": "<real command, test, log, screenshot, or production evidence>",
    }
    external_share_params = {
        "template": "soul-ring-share-proof.yml",
        "title": f"[Soul Ring Share Proof] {clean_framework} {release} external contributor proof",
        "github_username": external_username,
        "framework": clean_framework,
        "share_url": public_share_url,
        "source_url": created_prescription_url,
        "proof_context": (
            f"External contributor first-proof path for CyberHuaTuo {release}. "
            "Record the created First Soul Ring Prescription Issue URL after submission."
        ),
    }

    growth_issue_url = f"{repo_url}/issues/new?{urlencode(growth_params)}"
    share_issue_url = f"{repo_url}/issues/new?{urlencode(share_params)}"
    bounty_issue_url = f"{repo_url}/issues/new?{urlencode(bounty_params)}"
    first_prescription_issue_url = f"{repo_url}/issues/new?{urlencode(prescription_params)}"
    external_share_issue_url = f"{repo_url}/issues/new?{urlencode(external_share_params)}"
    strict_command = (
        f"cyberhuatuo market-ready --remote --strict-remote --username {clean_username} "
        f"--framework {clean_framework} --release-tag {release} --target-contributors {target}"
    )
    launch_assets_command = (
        f"cyberhuatuo launch-assets --username {clean_username} --framework {clean_framework} "
        f"--release-tag {release} --target-contributors {target}"
    )
    proof_pack_command = (
        f"cyberhuatuo proof-pack --username {clean_username} --framework {clean_framework} "
        f"--release-tag {release} --target-contributors {target}"
    )
    market_copy_command = (
        f"cyberhuatuo market-copy --username {clean_username} --framework {clean_framework} "
        f"--release-tag {release} --target-contributors {target}"
    )
    bounty_command = (
        f"cyberhuatuo bounty --username {clean_username} --framework auto --top-n 8 "
        f"--release-tag {release} --target-contributors {target}"
    )
    bounty_record_return_command = (
        f"cyberhuatuo record-return --username {clean_username} --framework auto "
        f'--surface "Bounty Board Issue" --source-url {created_bounty_url}'
    )
    first_invite_command = (
        f"cyberhuatuo first-invite --username {clean_username} --invitee {external_username} "
        f"--framework {clean_framework} --release-tag {release} --target-contributors {target} "
        f"--source-url {created_growth_url}"
    )
    traction_command = (
        f"cyberhuatuo traction-proof --username {clean_username} --framework {clean_framework} "
        f"--release-tag {release} --target-contributors {target}"
    )
    install_decision_command = _install_decision_command(
        repo=slug,
        pypi_project=clean_project,
        username=clean_username,
        framework=clean_framework,
        release_tag=release,
        target_contributors=target,
    )
    candidate_smoke_command = _candidate_install_smoke_command(
        repo=slug,
        pypi_project=clean_project,
        username=clean_username,
        framework=clean_framework,
        release_tag=release,
        target_contributors=target,
    )
    install_decision = _install_decision_surface(command=install_decision_command)
    fallback_publish_command = f"gh workflow run publish-pypi.yml -f release_tag={release}"
    fallback_run_list_command = "gh run list --workflow publish-pypi.yml --limit 5"
    fallback_web_links = _release_web_links(slug, clean_project, release)
    candidate_git_install_command = (
        f'python -m pip install --upgrade "{clean_project} @ git+{repo_url}.git@{release}"'
    )
    external_session_command = (
        f"cyberhuatuo record-session --username {external_username} --framework {clean_framework} "
        f'--surface "First external contributor session" --source-url {created_growth_url}'
    )
    external_challenge_command = (
        f"cyberhuatuo challenge --username {external_username} --framework {clean_framework}"
    )
    contributor_counting_rule = (
        "Only real public Issue authors, public Pull Request authors, and local ledger actors "
        "count toward target contributors."
    )
    community_challenge_pack = _build_community_challenge_pack(
        repo_url=repo_url,
        username=clean_username,
        framework=clean_framework,
        release_tag=release,
        target_contributors=target,
    )

    return {
        "title": "No-Network First Public Proof Pack",
        "network": "not_fetched",
        "network_disclosure": (
            "No-network: does not fetch public metrics, does not write ledger events, "
            "does not publish releases, and does not invent traction."
        ),
        "repo_url": repo_url,
        "repo": slug,
        "pypi_project": clean_project,
        "username": clean_username,
        "framework": clean_framework,
        "release_tag": release,
        "target_contributors": target,
        "install_decision": install_decision,
        "community_challenge_pack": community_challenge_pack,
        "growth_issue_url": growth_issue_url,
        "share_issue_url": share_issue_url,
        "bounty_issue_url": bounty_issue_url,
        "created_growth_url": created_growth_url,
        "created_share_url": created_share_url,
        "created_bounty_url": created_bounty_url,
        "bounty_record_return_command": bounty_record_return_command,
        "created_prescription_url": created_prescription_url,
        "prerequisite_gates": [
            f"Run `{launch_assets_command}` and push the IssueOps files to the default branch.",
            (
                "Configure PyPI Trusted Publisher, then publish a non-draft, non-prerelease "
                "GitHub Release or run the protected workflow_dispatch release_tag fallback."
            ),
            "Submit the Growth, Share Proof, or Bounty Board issue, then record only the created public URL.",
        ],
        "protected_publish_fallback": {
            "disclosure": (
                "Use only when the existing tag is on the default-branch release commit and "
                "GitHub Release publication is unavailable."
            ),
            "commands": [
                fallback_publish_command,
                fallback_run_list_command,
            ],
            "web_links": fallback_web_links,
            "validation_points": [
                "PyPI Trusted Publisher must match this repository, workflow file, and `pypi` environment.",
                "The workflow verifies the v* tag, origin/main reachability, package-version equality, and release gates.",
                "GitHub Actions workflow page exposes the manual Run workflow button for workflow_dispatch.",
                "No `PYPI_TOKEN` fallback is allowed.",
            ],
        },
        "install_loop_bridge": {
            "canonical_install_command": f"python -m pip install --upgrade {clean_project}",
            "candidate_git_install_command": candidate_git_install_command,
            "candidate_smoke_command": candidate_smoke_command,
            "recheck_command": strict_command,
            "disclosure": (
                "Use this Git tag candidate install bridge only after the public v* tag exists "
                "and PyPI latest is stale or cannot be verified; run the Candidate Install Smoke Gate before "
                "sending the bridge to external contributors; it does not close the PyPI install loop."
            ),
            "completion_rule": "Recheck PyPI latest-version proof before claiming public install readiness.",
        },
        "ledger_commands": [
            (
                f"cyberhuatuo record-return --username {clean_username} --framework {clean_framework} "
                f'--surface "Growth Flywheel Issue" --source-url {created_growth_url}'
            ),
            bounty_record_return_command,
            (
                f"cyberhuatuo record-share --username {clean_username} --framework {clean_framework} "
                f"--share-url {public_share_url} --source-url {created_share_url}"
            ),
        ],
        "recheck_commands": [
            install_decision_command,
            candidate_smoke_command,
            proof_pack_command,
            market_copy_command,
            bounty_command,
            first_invite_command,
            strict_command,
            traction_command,
            (
                f"python scripts/check_marketplace_release.py --remote --strict-remote --username {clean_username} "
                f"--framework {clean_framework} --release-tag {release} --target-contributors {target}"
            ),
        ],
        "external_contributor_path": {
            "username_placeholder": external_username,
            "install_decision_command": install_decision_command,
            "mcp_install_decision_tool": install_decision["mcp_tool"],
            "install_decision_rule": install_decision["rule"],
            "first_prescription_issue_url": first_prescription_issue_url,
            "external_share_issue_url": external_share_issue_url,
            "created_prescription_url": created_prescription_url,
            "first_session_command": external_session_command,
            "first_contribution_command": external_challenge_command,
            "maintainer_direct_invite_command": first_invite_command,
            "commands": [
                "# Paste the Recommended Install from CyberHuaTuo Install Command here",
                external_session_command,
                external_challenge_command,
            ],
            "contributor_counting_rule": contributor_counting_rule,
            "created_issue_rule": (
                "The First Soul Ring Prescription and Share Proof form URLs are entrypoints; "
                "record only the created public Issue URLs after submission."
            ),
            "copy_ready_invite": (
                f"First external CyberHuaTuo {release} contributor path: start with `{install_decision_command}` "
                f"or MCP `{install_decision['mcp_tool']}`, paste its Recommended Install, "
                f"run `{external_challenge_command}`, submit one real First Soul Ring Prescription, then open the "
                "Share Proof issue with the created prescription URL. "
                f"{contributor_counting_rule} No downloads, rewards, referrals, or fake contributors are claimed."
            ),
        },
        "copy_ready_public_proof_post": (
            f"CyberHuaTuo {release} public proof sprint: target {target} real first-ring contributors. "
            f"Start with `{install_decision_command}` or MCP `{install_decision['mcp_tool']}`, "
            f"paste its Recommended Install, optionally run `uvx --from {clean_project} cyberhuatuo-mcp`, "
            f"open a real First Soul Ring prescription at {repo_url}/issues/new?template=soul-ring-prescription.yml, "
            f"or request claimable framework gaps at {repo_url}/issues/new?template=soul-ring-bounty-board.yml, "
            "then submit Growth, Share, and Bounty proof URLs back to the ledger. "
            "No downloads, retention, repost counts, referrals, rewards, or fake contributors are claimed."
        ),
        "disclosure": "Form URLs are entrypoints, not proof URLs. Use the created public URL after submission.",
        "non_fabrication_notice": (
            "No downloads, retention, repost counts, referrals, rewards, or fake contributors are claimed."
        ),
    }


def _build_community_challenge_pack(
    *,
    repo_url: str,
    username: str,
    framework: str,
    release_tag: str,
    target_contributors: int,
) -> dict[str, Any]:
    clean_username = _field_text(username, "your-github-username")
    clean_framework = _field_text(framework, "langchain")
    release = _field_text(release_tag, "<release-tag>")
    target = _positive_target(target_contributors)
    external_username = "<external-contributor-github-username>"
    third_username = "<third-github-username>"
    fourth_username = "<fourth-github-username>"
    event_name = f"{clean_framework} Soul Cup"
    sect_name = "CyberHuaTuo-Sect"
    season_name = f"{clean_framework} Soul Season"
    created_tournament_url = "<created Tournament Issue URL after submission>"
    created_mentor_url = "<created Mentor Pact Issue URL after submission>"
    created_sect_url = "<created Sect Recruitment Issue URL after submission>"
    created_season_url = "<created Season Board Issue URL after submission>"

    tournament_participants = "\n".join([
        clean_username,
        external_username,
        third_username,
        fourth_username,
    ])
    tournament_params = {
        "template": "soul-ring-tournament.yml",
        "title": f"[Soul Ring Tournament] {clean_framework} {release} public cup",
        "event_name": event_name,
        "framework": clean_framework,
        "participants": tournament_participants,
        "event_goal": (
            f"Invite {target} real first-ring contributors to publish real {clean_framework} fixes, "
            "then settle the cup from current CyberHuaTuo prescription counts."
        ),
    }
    mentor_params = {
        "template": "soul-ring-mentor.yml",
        "title": f"[Soul Ring Mentor] {clean_framework} {release} first-ring pact",
        "mentor_username": clean_username,
        "apprentice_username": external_username,
        "framework": clean_framework,
        "mentorship_goal": (
            f"Guide one external contributor through a real {clean_framework} fix, first-ring challenge, "
            "and public proof URL."
        ),
    }
    sect_params = {
        "template": "soul-ring-sect-recruit.yml",
        "title": f"[Soul Ring Sect] {clean_framework} {release} recruitment",
        "sect_name": sect_name,
        "framework": clean_framework,
        "members": clean_username,
        "invitee": external_username,
        "recruitment_goal": (
            f"Recruit one real agent builder into {sect_name}, publish one real {clean_framework} fix, "
            "and turn the current sect snapshot into a public quest."
        ),
    }
    season_params = {
        "template": "soul-ring-season.yml",
        "title": f"[Soul Ring Season] {clean_framework} {release} current board",
        "season_name": season_name,
        "framework": clean_framework,
        "top_n": "10",
        "season_goal": (
            f"Publish the current {clean_framework} leaderboard, name the real current champion, "
            "and invite the next chaser to submit one real fix."
        ),
    }

    tournament_issue_url = f"{repo_url}/issues/new?{urlencode(tournament_params)}"
    mentor_issue_url = f"{repo_url}/issues/new?{urlencode(mentor_params)}"
    sect_issue_url = f"{repo_url}/issues/new?{urlencode(sect_params)}"
    season_issue_url = f"{repo_url}/issues/new?{urlencode(season_params)}"
    tournament_command = (
        f"cyberhuatuo tournament {clean_username} {external_username} {third_username} {fourth_username} "
        f"--framework {clean_framework} --event \"{event_name}\""
    )
    tournament_settle_command = (
        f"cyberhuatuo tournament-settle {clean_username} {external_username} {third_username} {fourth_username} "
        f"--framework {clean_framework} --event \"{event_name}\""
    )
    mentor_command = (
        f"cyberhuatuo mentor {clean_username} {external_username} --framework {clean_framework}"
    )
    apprentice_challenge_command = (
        f"cyberhuatuo challenge --username {external_username} --framework {clean_framework}"
    )
    apprentice_ladder_command = f"cyberhuatuo ladder {external_username} --framework {clean_framework}"
    sect_recruit_command = (
        f"cyberhuatuo sect-recruit {sect_name} {clean_username} --invitee {external_username} "
        f"--framework {clean_framework}"
    )
    sect_hall_command = f"cyberhuatuo sect-hall {sect_name} {clean_username} --framework {clean_framework}"
    sect_quest_command = f"cyberhuatuo sect-quest {sect_name} {clean_username} --framework {clean_framework}"
    season_command = f"cyberhuatuo season --framework {clean_framework} --top-n 10"
    arena_command = f"cyberhuatuo arena {clean_username} --top-n 10"
    duel_command = f"cyberhuatuo duel {clean_username} {external_username} --framework {clean_framework}"
    non_fabrication = (
        "Tournament wins, mentor seniority, sect membership, season history, adoption, and rewards are not invented; "
        "replace placeholders with real GitHub usernames before public posting."
    )
    copy_ready_post = (
        f"CyberHuaTuo {release} community challenge sprint: use the Tournament, Mentor Pact, "
        "Sect Recruitment, and Season Board issue forms to turn first-ring proof into public events. "
        f"Start with `{tournament_command}`, `{mentor_command}`, `{sect_recruit_command}`, and `{season_command}`. "
        f"{non_fabrication}"
    )

    return {
        "title": "Community Challenge Pack",
        "purpose": (
            "Turn market attention into social loops: public cup, mentor-apprentice onboarding, "
            "sect recruitment, and current-season leaderboard chase."
        ),
        "tournament_issue_url": tournament_issue_url,
        "mentor_issue_url": mentor_issue_url,
        "sect_issue_url": sect_issue_url,
        "season_issue_url": season_issue_url,
        "created_tournament_url": created_tournament_url,
        "created_mentor_url": created_mentor_url,
        "created_sect_url": created_sect_url,
        "created_season_url": created_season_url,
        "commands": [
            tournament_command,
            tournament_settle_command,
            mentor_command,
            apprentice_challenge_command,
            apprentice_ladder_command,
            sect_recruit_command,
            sect_hall_command,
            sect_quest_command,
            season_command,
            arena_command,
            duel_command,
        ],
        "copy_ready_post": copy_ready_post,
        "non_fabrication_notice": non_fabrication,
        "created_issue_rule": (
            "These issue-form URLs are entrypoints; record only created public Issue URLs after submission."
        ),
    }


def build_first_public_proof_pack(
    *,
    repo: str = DEFAULT_REPO,
    pypi_project: str = DEFAULT_PYPI_PROJECT,
    username: str = "your-github-username",
    framework: str = "langchain",
    release_tag: str = "",
    target_contributors: int = 3,
) -> dict[str, Any]:
    """Build a no-network first public proof pack for marketplace launch operators."""
    return _build_first_public_proof_kit(
        repo=repo,
        pypi_project=pypi_project,
        username=username,
        framework=framework,
        release_tag=release_tag,
        target_contributors=target_contributors,
    )


def _reviewable_or_placeholder_url(value: str, fallback: str) -> str:
    text = _field_text(value, fallback, limit=600)
    if text.startswith(("https://", "http://")):
        return text
    return fallback


def _candidate_snapshot_line(invitee: str) -> str:
    try:
        profile = get_cultivation_profile(invitee)
    except Exception:
        return (
            f"Candidate Snapshot: @{invitee} could not be read from the local contribution snapshot; "
            "treat this as an unverified invite until they submit a created public Issue or PR URL."
        )

    count = int(profile.get("contribution_count", 0) or 0)
    title = f"{profile.get('title_emoji', '')} {profile.get('title_en', 'Intern Apprentice')}".strip()
    if count <= 0:
        return (
            f"Candidate Snapshot: @{invitee} has 0 local CyberHuaTuo prescription(s) in the current "
            "knowledge-base snapshot; this is a real cold-start invite, not claimed traction."
        )
    rank = profile.get("global_rank", 0)
    total = profile.get("global_total", 0)
    return (
        f"Candidate Snapshot: @{invitee} has {count} local CyberHuaTuo prescription(s), title {title}, "
        f"rank #{rank} / {total} in the current snapshot."
    )


def build_first_contributor_invite_pack(
    *,
    repo: str = DEFAULT_REPO,
    pypi_project: str = DEFAULT_PYPI_PROJECT,
    username: str = "your-github-username",
    invitee: str = "external-contributor-github-username",
    framework: str = "langchain",
    release_tag: str = "",
    target_contributors: int = 3,
    source_url: str = "",
) -> dict[str, Any]:
    """Build a no-network direct invite for one first-ring external contributor."""
    slug = _repo_slug(repo)
    repo_url = f"https://github.com/{slug}"
    clean_project = _field_text(pypi_project, DEFAULT_PYPI_PROJECT)
    clean_username = _field_text(username, "your-github-username")
    clean_invitee = _field_text(invitee, "external-contributor-github-username").lstrip("@")
    clean_framework = _field_text(framework, "langchain")
    release = _field_text(release_tag, f"v{__version__}")
    target = _positive_target(target_contributors)
    created_source_url = _reviewable_or_placeholder_url(
        source_url,
        "<created Growth Issue URL after submission>",
    )
    public_share_url = "<public share URL after posting>"
    created_prescription_url = "<created First Soul Ring Prescription Issue URL after submission>"
    prescription_params = {
        "template": "soul-ring-prescription.yml",
        "title": f"[Soul Ring Prescription] {clean_framework} first external contributor proof",
        "github_username": clean_invitee,
        "framework": clean_framework,
        "symptom": "<real error, traceback, broken behavior, environment, and reproduction steps>",
        "root_cause": "<real root cause after investigation>",
        "prescription": "<real fix, commands, patch, or configuration change>",
        "verification": "<real command, test, log, screenshot, or production evidence>",
    }
    share_params = {
        "template": "soul-ring-share-proof.yml",
        "title": f"[Soul Ring Share Proof] {clean_framework} {release} external contributor proof",
        "github_username": clean_invitee,
        "framework": clean_framework,
        "share_url": public_share_url,
        "source_url": created_prescription_url,
        "proof_context": (
            f"External contributor first-proof path for CyberHuaTuo {release}. "
            "Record the created First Soul Ring Prescription Issue URL after submission."
        ),
    }
    first_prescription_issue_url = f"{repo_url}/issues/new?{urlencode(prescription_params)}"
    external_share_issue_url = f"{repo_url}/issues/new?{urlencode(share_params)}"
    record_session_command = (
        f"cyberhuatuo record-session --username {clean_invitee} --framework {clean_framework} "
        f'--surface "First external contributor session" --source-url {created_source_url}'
    )
    challenge_command = f"cyberhuatuo challenge --username {clean_invitee} --framework {clean_framework}"
    install_decision_command = _install_decision_command(
        repo=slug,
        pypi_project=clean_project,
        username=clean_username,
        framework=clean_framework,
        release_tag=release,
        target_contributors=target,
    )
    install_decision = _install_decision_surface(command=install_decision_command)
    proof_pack_command = (
        f"cyberhuatuo proof-pack --username {clean_username} --framework {clean_framework} "
        f"--release-tag {release} --target-contributors {target}"
    )
    market_copy_command = (
        f"cyberhuatuo market-copy --username {clean_username} --framework {clean_framework} "
        f"--release-tag {release} --target-contributors {target}"
    )
    traction_command = (
        f"cyberhuatuo traction-proof --username {clean_username} --framework {clean_framework} "
        f"--release-tag {release} --target-contributors {target}"
    )
    contributor_counting_rule = (
        "Only real public Issue authors, public Pull Request authors, and local ledger actors "
        "count toward target contributors."
    )
    non_fabrication = (
        "This invite pack does not invent downloads, retention, repost counts, referrals, rewards, "
        "reviews, or fake contributors."
    )
    candidate_snapshot = _candidate_snapshot_line(clean_invitee)

    return {
        "title": "First Contributor Invite Pack",
        "network": "not_fetched",
        "network_disclosure": (
            "No public metrics are fetched; this invite is generated from local release metadata, "
            "local contribution snapshots, and operator inputs."
        ),
        "repo": slug,
        "repo_url": repo_url,
        "pypi_project": clean_project,
        "maintainer": clean_username,
        "invitee": clean_invitee,
        "framework": clean_framework,
        "release_tag": release,
        "target_contributors": target,
        "install_decision": install_decision,
        "source_url": created_source_url,
        "candidate_snapshot": candidate_snapshot,
        "first_prescription_issue_url": first_prescription_issue_url,
        "external_share_issue_url": external_share_issue_url,
        "created_prescription_url": created_prescription_url,
        "record_session_command": record_session_command,
        "challenge_command": challenge_command,
        "invitee_commands": [
            "# Paste the Recommended Install from CyberHuaTuo Install Command here",
            record_session_command,
            challenge_command,
        ],
        "recheck_commands": [
            install_decision_command,
            proof_pack_command,
            market_copy_command,
            traction_command,
        ],
        "contributor_counting_rule": contributor_counting_rule,
        "created_issue_rule": (
            "Issue form URLs are entrypoints; record only created public Issue, PR, Discussion, "
            "release, or social URLs after submission."
        ),
        "copy_ready_invite": (
            f"@{clean_invitee} this is a direct First Soul Ring invite for CyberHuaTuo {release}: "
            f"start with `{install_decision_command}` or MCP `{install_decision['mcp_tool']}`, "
            f"paste its Recommended Install, run `{challenge_command}`, submit one real "
            f"{clean_framework} prescription through the First Soul Ring issue, then open the Share Proof issue "
            f"with the created prescription URL. {contributor_counting_rule} {non_fabrication}"
        ),
        "non_fabrication_notice": non_fabrication,
    }


def format_first_contributor_invite_pack(pack: dict[str, Any]) -> str:
    """Format a direct first-contributor invite as markdown."""
    lines = [
        "# First Contributor Invite Pack",
        "",
        f"- Repository: `{pack['repo']}`",
        f"- PyPI project: `{pack['pypi_project']}`",
        f"- Release tag: `{pack['release_tag']}`",
        f"- Maintainer: `{pack['maintainer']}`",
        f"- Target invitee: `{pack['invitee']}`",
        f"- Target contributors: {pack['target_contributors']}",
        f"- {pack['network_disclosure']}",
        f"- {pack['non_fabrication_notice']}",
        "",
        "## Candidate Snapshot",
        f"- {pack['candidate_snapshot']}",
        "",
        *_install_decision_surface_lines(pack["install_decision"], heading_level=2),
        "",
        "## Issue Entrypoints",
        f"- First Soul Ring Prescription Issue: {pack['first_prescription_issue_url']}",
        f"- External Share Proof Issue: {pack['external_share_issue_url']}",
        f"- Created First Soul Ring Prescription Issue URL: {pack['created_prescription_url']}",
        f"- Created-issue proof rule: {pack['created_issue_rule']}",
        f"- Contributor-counting rule: {pack['contributor_counting_rule']}",
        "",
        "## Invitee Commands",
        "```bash",
        *pack["invitee_commands"],
        "```",
        "",
        "## Maintainer Recheck Commands",
        "```bash",
        *pack["recheck_commands"],
        "```",
        "",
        "## Copy-ready direct invite",
        "```text",
        pack["copy_ready_invite"],
        "```",
    ]
    return "\n".join(lines)


def _install_decision_surface_lines(surface: dict[str, str], *, heading_level: int = 2) -> list[str]:
    prefix = "#" * max(1, heading_level)
    return [
        f"{prefix} Install Decision Surface",
        "",
        f"- CLI install decision command: `{surface['command']}`",
        f"- MCP install decision tool: `{surface['mcp_tool']}`",
        f"- {surface['rule']}",
    ]


def _external_contributor_path_lines(path: dict[str, Any], *, heading_level: int = 2) -> list[str]:
    prefix = "#" * max(1, heading_level)
    lines = [
        f"{prefix} External Contributor Path",
        "",
        f"- External contributor username: `{path['username_placeholder']}`",
        f"- Install decision command: `{path['install_decision_command']}`",
        f"- MCP install decision tool: `{path['mcp_install_decision_tool']}`",
        f"- Install decision rule: {path['install_decision_rule']}",
        f"- First Soul Ring Prescription Issue: {path['first_prescription_issue_url']}",
        f"- External Share Proof Issue: {path['external_share_issue_url']}",
        f"- Created First Soul Ring Prescription Issue URL: {path['created_prescription_url']}",
        f"- Maintainer direct invite command: `{path['maintainer_direct_invite_command']}`",
        f"- Created-issue proof rule: {path['created_issue_rule']}",
        f"- Contributor-counting rule: {path['contributor_counting_rule']}",
        "",
        f"{prefix}# External Contributor Commands",
        "```bash",
        *path["commands"],
        "```",
        "",
        f"{prefix}# Copy-ready external contributor invite",
        "```text",
        path["copy_ready_invite"],
        "```",
    ]
    return lines


def _protected_publish_fallback_lines(fallback: dict[str, Any], *, heading_level: int = 3) -> list[str]:
    prefix = "#" * max(1, heading_level)
    lines = [
        f"{prefix} Protected Publish Fallback",
        "",
        f"- {fallback['disclosure']}",
    ]
    for link in fallback.get("web_links", []):
        lines.append(f"- {link['label']}: {link['url']}")
        if link.get("note"):
            lines.append(f"  - {link['note']}")
    lines.extend([
        "```bash",
        *fallback["commands"],
        "```",
    ])
    lines.extend(f"- {point}" for point in fallback.get("validation_points", []))
    return lines


def _install_loop_bridge_lines(bridge: dict[str, Any], *, heading_level: int = 3) -> list[str]:
    prefix = "#" * max(1, heading_level)
    commands = [bridge["candidate_git_install_command"]]
    if bridge.get("candidate_smoke_command"):
        commands.append(bridge["candidate_smoke_command"])
    commands.append(bridge["recheck_command"])
    return [
        f"{prefix} Git Tag Candidate Install Bridge",
        "",
        f"- Canonical PyPI install: `{bridge['canonical_install_command']}`",
        f"- {bridge['disclosure']}",
        "```bash",
        *commands,
        "```",
        f"- {bridge['completion_rule']}",
    ]


def _community_challenge_pack_lines(pack: dict[str, Any], *, heading_level: int = 2) -> list[str]:
    prefix = "#" * max(1, heading_level)
    return [
        f"{prefix} Community Challenge Pack",
        "",
        f"- Purpose: {pack['purpose']}",
        f"- Prefilled Tournament Cup Issue: {pack['tournament_issue_url']}",
        f"- Prefilled Mentor Pact Issue: {pack['mentor_issue_url']}",
        f"- Prefilled Sect Recruitment Issue: {pack['sect_issue_url']}",
        f"- Prefilled Season Board Issue: {pack['season_issue_url']}",
        f"- Created Tournament Issue URL: {pack['created_tournament_url']}",
        f"- Created Mentor Pact Issue URL: {pack['created_mentor_url']}",
        f"- Created Sect Recruitment Issue URL: {pack['created_sect_url']}",
        f"- Created Season Board Issue URL: {pack['created_season_url']}",
        f"- Created-issue rule: {pack['created_issue_rule']}",
        "```bash",
        *pack["commands"],
        "```",
        "### Copy-ready community challenge post" if heading_level <= 2 else "#### Copy-ready community challenge post",
        "```text",
        pack["copy_ready_post"],
        "```",
        f"- {pack['non_fabrication_notice']}",
    ]


def format_first_public_proof_pack(pack: dict[str, Any]) -> str:
    """Format a no-network first public proof pack as markdown."""
    lines = [
        "# No-Network First Public Proof Pack",
        "",
        f"- Repository: `{pack['repo']}`",
        f"- PyPI project: `{pack['pypi_project']}`",
        f"- Release tag: `{pack['release_tag']}`",
        f"- Target contributors: {pack['target_contributors']}",
        f"- {pack['network_disclosure']}",
        f"- {pack['disclosure']}",
        "",
        "## Prerequisite Gates",
    ]
    lines.extend(f"- {gate}" for gate in pack.get("prerequisite_gates", []))
    lines.extend([
        "",
        "## Proof Form Entrypoints",
        f"- Prefilled Growth Flywheel Issue: {pack['growth_issue_url']}",
        f"- Prefilled Share Proof Issue: {pack['share_issue_url']}",
        f"- Prefilled Bounty Board Issue: {pack['bounty_issue_url']}",
        f"- Created Growth Issue URL: {pack['created_growth_url']}",
        f"- Created Share Proof Issue URL: {pack['created_share_url']}",
        f"- Created Bounty Board Issue URL: {pack['created_bounty_url']}",
        "",
        *_community_challenge_pack_lines(pack["community_challenge_pack"], heading_level=2),
        "",
        *_protected_publish_fallback_lines(pack["protected_publish_fallback"], heading_level=3),
        "",
        *_install_loop_bridge_lines(pack["install_loop_bridge"], heading_level=3),
        "",
        *_install_decision_surface_lines(pack["install_decision"], heading_level=2),
        "",
        "## CLI Ledger Commands",
        "```bash",
        *pack["ledger_commands"],
        "```",
        "",
        *_external_contributor_path_lines(pack["external_contributor_path"], heading_level=2),
        "",
        "## Recheck Commands",
        "```bash",
        *pack["recheck_commands"],
        "```",
        "",
        "## Copy-ready public proof post",
        "```text",
        pack["copy_ready_public_proof_post"],
        "```",
        "",
        f"- {pack['non_fabrication_notice']}",
    ])
    return "\n".join(lines)


def build_marketplace_submission_copy_pack(
    *,
    repo: str = DEFAULT_REPO,
    pypi_project: str = DEFAULT_PYPI_PROJECT,
    username: str = "your-github-username",
    framework: str = "langchain",
    release_tag: str = "",
    target_contributors: int = 3,
) -> dict[str, Any]:
    """Build no-network listing copy for PyPI, Claude, Codex, and release posts."""
    slug = _repo_slug(repo)
    repo_url = f"https://github.com/{slug}"
    clean_username = _field_text(username, "your-github-username")
    clean_framework = _field_text(framework, "langchain")
    clean_project = _field_text(pypi_project, DEFAULT_PYPI_PROJECT)
    release = _field_text(release_tag, f"v{__version__}")
    version = _version_from_release_tag(release)
    if version == "<version>":
        version = __version__
    target = _positive_target(target_contributors)
    proof = _build_first_public_proof_kit(
        repo=slug,
        pypi_project=clean_project,
        username=clean_username,
        framework=clean_framework,
        release_tag=release,
        target_contributors=target,
    )
    created_growth_url = proof["created_growth_url"]
    created_share_url = proof["created_share_url"]
    created_bounty_url = proof["created_bounty_url"]
    public_share_url = "<public share URL after posting>"
    non_fabrication = (
        "This copy pack does not invent downloads, retention, repost counts, referrals, "
        "rewards, reviews, or fake contributors."
    )
    install_command = f"python -m pip install --upgrade {clean_project}"
    mcp_command = f"uvx --from {clean_project} cyberhuatuo-mcp"
    install_decision_command = _install_decision_command(
        repo=slug,
        pypi_project=clean_project,
        username=clean_username,
        framework=clean_framework,
        release_tag=release,
        target_contributors=target,
    )
    install_decision = _install_decision_surface(command=install_decision_command)
    record_return_command = (
        f"cyberhuatuo record-return --username {clean_username} --framework {clean_framework} "
        f'--surface "Marketplace listing" --source-url {created_growth_url}'
    )
    record_share_command = (
        f"cyberhuatuo record-share --username {clean_username} --framework {clean_framework} "
        f"--share-url {public_share_url} --source-url {created_share_url}"
    )
    bounty_record_return_command = proof["bounty_record_return_command"]
    bounty_command = (
        f"cyberhuatuo bounty --username {clean_username} --framework auto --top-n 8 "
        f"--release-tag {release} --target-contributors {target}"
    )
    traction_command = (
        f"cyberhuatuo traction-proof --username {clean_username} --framework {clean_framework} "
        f"--release-tag {release} --target-contributors {target}"
    )
    release_command = (
        f"gh release create {release} dist/{clean_project}-{version}.tar.gz "
        f"dist/{clean_project}-{version}-py3-none-any.whl "
        "dist/cyberhuatuo-claude-desktop.mcpb --verify-tag --notes-from-tag"
    )
    release_web_links = _release_web_links(slug, clean_project, release)
    submission_portals = [
        {
            "channel": "pypi",
            "label": "PyPI Trusted Publisher settings",
            "url": f"https://pypi.org/manage/project/{clean_project}/settings/publishing/",
            "evidence": (
                "After the workflow publishes, record the PyPI project page or release file page; "
                "do not record a private settings page as public evidence."
            ),
            "record_command": (
                f"cyberhuatuo record-market --username {clean_username} --framework {clean_framework} "
                f"--channel pypi --status published --submission-url https://pypi.org/project/{clean_project}/ "
                f"--release-tag {release} --repo {slug} --pypi-project {clean_project}"
            ),
        },
        {
            "channel": "pypi",
            "label": "PyPI project page",
            "url": f"https://pypi.org/project/{clean_project}/",
            "evidence": "Use this public URL after PyPI serves the current local version.",
            "record_command": "",
        },
        {
            "channel": "claude-code",
            "label": "Claude Code plugin submit",
            "url": "https://claude.ai/settings/plugins/submit",
            "evidence": (
                "Record the reviewable plugin submission URL, status page, issue, or public listing after submission."
            ),
            "record_command": (
                f"cyberhuatuo record-market --username {clean_username} --framework {clean_framework} "
                f"--channel claude-code --status submitted --submission-url <reviewable Claude Code submission URL> "
                f"--release-tag {release} --repo {slug} --pypi-project {clean_project}"
            ),
        },
        {
            "channel": "claude-code",
            "label": "Claude Code plugin submit fallback",
            "url": "https://platform.claude.com/plugins/submit",
            "evidence": "Use this fallback submission surface when the Claude app route is unavailable.",
            "record_command": "",
        },
        {
            "channel": "claude-desktop",
            "label": "Claude Connectors Directory submission guide",
            "url": "https://claude.com/docs/connectors/building/submission",
            "evidence": (
                "Follow the Desktop extensions (MCPB) form from the official guide, then record the reviewable "
                "submission/listing URL."
            ),
            "record_command": (
                f"cyberhuatuo record-market --username {clean_username} --framework {clean_framework} "
                f"--channel claude-desktop --status submitted --submission-url <reviewable Claude MCPB submission URL> "
                f"--release-tag {release} --repo {slug} --pypi-project {clean_project}"
            ),
        },
        {
            "channel": "claude-desktop",
            "label": "Claude Connectors Directory",
            "url": "https://www.claude.com/connectors",
            "evidence": "Record the public connector listing URL only after the connector is listed or reviewable.",
            "record_command": "",
        },
        {
            "channel": "codex",
            "label": "Codex plugin evidence",
            "url": f"`codex plugin marketplace add {slug}`",
            "evidence": (
                "Record a reviewable workspace rollout note, marketplace catalog URL, or pilot issue after a real "
                "Codex install path exists."
            ),
            "record_command": (
                f"cyberhuatuo record-market --username {clean_username} --framework {clean_framework} "
                f"--channel codex --status submitted --submission-url <reviewable Codex rollout URL> "
                f"--release-tag {release} --repo {slug} --pypi-project {clean_project}"
            ),
        },
        {
            "channel": "codex",
            "label": "Codex workspace Apps settings evidence",
            "url": "Workspace settings > Apps or plugin directory",
            "evidence": (
                "Do not claim public Codex directory approval from local catalog installation; record only a "
                "reviewable admin rollout, pilot, or listing URL."
            ),
            "record_command": "",
        },
    ]
    submission_channels = ("pypi", "claude-code", "claude-desktop", "codex", "github-release")
    record_market_commands = [
        (
            f"cyberhuatuo record-market --username {clean_username} --framework {clean_framework} "
            f"--channel {channel} --status submitted --submission-url <reviewable public URL> "
            f"--release-tag {release} --repo {slug} --pypi-project {clean_project}"
        )
        for channel in submission_channels
    ]
    market_status_command = (
        f"cyberhuatuo market-status --username {clean_username} --framework {clean_framework} "
        f"--release-tag {release} --repo {slug} --pypi-project {clean_project}"
    )
    contributor_rule = (
        "Only real public Issue authors, public Pull Request authors, and local ledger actors count "
        "toward target contributors."
    )

    return {
        "title": "Marketplace Submission Copy Pack",
        "network": "not_fetched",
        "network_disclosure": (
            "No public metrics are fetched; this pack is generated from local release metadata and operator inputs."
        ),
        "repo": slug,
        "repo_url": repo_url,
        "pypi_project": clean_project,
        "pypi_url": f"https://pypi.org/project/{clean_project}/",
        "username": clean_username,
        "framework": clean_framework,
        "release_tag": release,
        "version": version,
        "target_contributors": target,
        "install_command": install_command,
        "mcp_command": mcp_command,
        "install_decision": install_decision,
        "install_loop_bridge": proof["install_loop_bridge"],
        "community_challenge_pack": proof["community_challenge_pack"],
        "non_fabrication_notice": non_fabrication,
        "contributor_counting_rule": contributor_rule,
        "pypi": {
            "short": (
                "CyberHuaTuo turns AI-agent failures into reusable prescriptions, MCP tools, "
                "and a First Soul Ring contribution loop."
            ),
            "long": (
                f"CyberHuaTuo {release} ships a Python CLI, shared MCP server, Codex plugin, "
                "Claude Desktop MCPB package, and real-data soul-ring growth surfaces for "
                f"{clean_framework} debugging workflows."
            ),
            "project_urls": [
                ("Homepage", repo_url),
                ("Repository", repo_url),
                ("MCP Install Guide", f"{repo_url}/blob/main/README_MCP.md"),
                ("Marketplace Release Plan", f"{repo_url}/blob/main/docs/MARKETPLACE_RELEASE.md"),
                ("Privacy Policy", f"{repo_url}/blob/main/docs/PRIVACY.md"),
            ],
            "commands": [install_command, mcp_command],
        },
        "claude": {
            "short": "One-click Claude Desktop extension for CyberHuaTuo AI-agent diagnosis and soul-ring contribution routing.",
            "install_note": (
                "Install `dist/cyberhuatuo-claude-desktop.mcpb` in Claude Desktop after validating the bundle."
            ),
            "validation_commands": [
                "claude plugin validate .",
                "mcpb validate claude-desktop",
                "mcpb pack claude-desktop dist/cyberhuatuo-claude-desktop.mcpb",
            ],
            "review_notes": [
                "Tool annotations distinguish read-only reports from ledger-writing tools.",
                "Privacy policy is linked from `claude-desktop/manifest.json`.",
                "Working examples route diagnose, market-ready, proof-pack, and first-ring contribution flows.",
            ],
        },
        "codex": {
            "short": (
                "Codex plugin bundle for diagnosing AI-agent failures, using CyberHuaTuo MCP tools, "
                "and following a team soul-ring contribution process."
            ),
            "files": [".codex-plugin/plugin.json", ".agents/plugins/marketplace.json", ".mcp.json"],
            "install_commands": [
                f"codex plugin marketplace add {slug}",
                "codex mcp list",
            ],
            "usage_prompt": (
                f"Use CyberHuaTuo to diagnose this {clean_framework} failure, then generate my First Soul Ring path."
            ),
        },
        "github_release": {
            "command": release_command,
            "web_links": release_web_links,
            "post": (
                f"CyberHuaTuo {release} is the public growth-loop release: PyPI install, Claude MCPB, "
                "Codex plugin metadata, IssueOps proof routes, and First Soul Ring contributor activation."
            ),
        },
        "submission_portals": submission_portals,
        "public_proof_cta": {
            "growth_issue_url": proof["growth_issue_url"],
            "share_issue_url": proof["share_issue_url"],
            "bounty_issue_url": proof["bounty_issue_url"],
            "created_bounty_url": created_bounty_url,
            "record_return_command": record_return_command,
            "bounty_record_return_command": bounty_record_return_command,
            "record_share_command": record_share_command,
            "bounty_command": bounty_command,
            "traction_command": traction_command,
            "copy": (
                f"CyberHuaTuo {release} public proof sprint: target {target} real first-ring contributors. "
                f"Start with `{install_decision_command}` or MCP `{install_decision['mcp_tool']}`, "
                f"paste its Recommended Install, run `{mcp_command}` for agent clients, submit a real "
                "First Soul Ring prescription or request the Bounty Board for claimable framework gaps, "
                "then record created Growth, Share, and Bounty proof URLs. "
                "If PyPI latest still lags, use the Git tag candidate install bridge only after the tag exists. "
                f"{contributor_rule} {non_fabrication}"
            ),
        },
        "submission_ledger": {
            "title": "Marketplace Submission Ledger",
            "disclosure": (
                "After each real PyPI, Claude Code, Claude Desktop MCPB, Codex, or GitHub Release "
                "submission, record the reviewable public URL. The ledger records status evidence only "
                "and does not claim approval unless the recorded status is approved or published."
            ),
            "channels": list(submission_channels),
            "record_commands": record_market_commands,
            "status_command": market_status_command,
        },
        "maintainer_announcement": (
            f"CyberHuaTuo {release} is ready for PyPI, Claude Desktop MCPB, and Codex plugin submission copy. "
            f"The first public loop is simple: `{install_decision_command}`, paste its Recommended Install, "
            "run the First Soul Ring challenge, publish a "
            f"real {clean_framework} prescription, request claimable gaps with `{bounty_command}`, "
            f"record each market submission with `{market_status_command}`, and record created Growth, Share, "
            "and Bounty proof URLs. If PyPI latest still lags, use the "
            "Git tag candidate install bridge only after the tag exists and keep the registry recheck open. "
            f"{contributor_rule} "
            "First Soul Ring momentum is tracked through public Issues, PRs, and append-only local ledgers, "
            "not vanity metrics."
        ),
    }


def format_marketplace_submission_copy_pack(pack: dict[str, Any]) -> str:
    """Format a marketplace submission copy pack as markdown."""
    pypi = pack["pypi"]
    claude = pack["claude"]
    codex = pack["codex"]
    release = pack["github_release"]
    portals = pack["submission_portals"]
    proof = pack["public_proof_cta"]
    ledger = pack["submission_ledger"]
    lines = [
        "# Marketplace Submission Copy Pack",
        "",
        f"- Repository: `{pack['repo']}`",
        f"- PyPI project: `{pack['pypi_project']}`",
        f"- Release tag: `{pack['release_tag']}`",
        f"- Package version: `{pack['version']}`",
        f"- Target contributors: {pack['target_contributors']}",
        f"- {pack['network_disclosure']}",
        f"- {pack['non_fabrication_notice']}",
        "",
        "## Install Decision Commands",
        "",
        f"- CLI install decision command: `{pack['install_decision']['command']}`",
        f"- MCP install decision tool: `{pack['install_decision']['mcp_tool']}`",
        f"- {pack['install_decision']['rule']}",
        "",
        "## PyPI Listing Copy",
        "",
        f"- PyPI URL: {pack['pypi_url']}",
        f"- Short description: {pypi['short']}",
        f"- Long description: {pypi['long']}",
        "- Install commands:",
        "```bash",
        *pypi["commands"],
        "```",
        "- Project URLs to expose:",
    ]
    lines.extend(f"  - {label}: {url}" for label, url in pypi["project_urls"])
    lines.extend([
        "",
        "## Claude MCPB Listing Copy",
        "",
        f"- Short description: {claude['short']}",
        f"- Claude Desktop install note: {claude['install_note']}",
        "- Validation commands:",
        "```bash",
        *claude["validation_commands"],
        "```",
        "- Review notes:",
    ])
    lines.extend(f"  - {note}" for note in claude["review_notes"])
    lines.extend([
        "",
        "## Codex Plugin Listing Copy",
        "",
        f"- Short description: {codex['short']}",
        f"- Usage prompt: {codex['usage_prompt']}",
        "- Listing files:",
    ])
    lines.extend(f"  - `{path}`" for path in codex["files"])
    lines.extend([
        "- Install and verification commands:",
        "```bash",
        *codex["install_commands"],
        "```",
        "",
        "## GitHub Release Post",
        "",
        *(f"- {link['label']}: {link['url']}" for link in release.get("web_links", [])),
        "```bash",
        release["command"],
        "```",
        "```text",
        release["post"],
        "```",
        "",
        "## Submission Portals And Evidence URLs",
        "",
        "- Do not record the prefilled form URL as proof; record the reviewable URL created after submission.",
        "- Public evidence must be an http(s) URL when passed to `record-market`; private settings pages are setup steps, not public proof.",
        "",
        "| Channel | Portal | Evidence boundary | Record command |",
        "| --- | --- | --- | --- |",
    ])
    for portal in portals:
        command = portal.get("record_command") or "Use the paired record command after a reviewable public URL exists."
        portal_label = f"{portal['label']}: {portal['url']}"
        lines.append(
            f"| {_cell(portal['channel'])} | {_cell(portal_label)} | "
            f"{_cell(portal['evidence'])} | {_cell(command)} |"
        )
    lines.extend([
        "",
        "## Public Proof CTA",
        "",
        f"- Prefilled Growth Flywheel Issue: {proof['growth_issue_url']}",
        f"- Prefilled Share Proof Issue: {proof['share_issue_url']}",
        f"- Prefilled Bounty Board Issue: {proof['bounty_issue_url']}",
        f"- Created Bounty Board Issue URL: {proof['created_bounty_url']}",
        f"- Contributor-counting rule: {pack['contributor_counting_rule']}",
        "```bash",
        proof["record_return_command"],
        proof["bounty_record_return_command"],
        proof["record_share_command"],
        proof["bounty_command"],
        proof["traction_command"],
        "```",
        "```text",
        proof["copy"],
        "```",
        "",
        *_community_challenge_pack_lines(pack["community_challenge_pack"], heading_level=2),
        "",
        "## Marketplace Submission Ledger",
        "",
        f"- {ledger['disclosure']}",
        "- Record commands after real submission URLs exist:",
        "```bash",
        *ledger["record_commands"],
        ledger["status_command"],
        "```",
        "",
        *_install_loop_bridge_lines(pack["install_loop_bridge"], heading_level=2),
        "",
        "## Copy-ready maintainer announcement",
        "",
        "```text",
        pack["maintainer_announcement"],
        "```",
    ])
    return "\n".join(lines)


def format_marketplace_readiness(report: dict[str, Any]) -> str:
    """Format a marketplace readiness report as markdown."""
    remote_gate = "skipped"
    if report["remote_checked"]:
        remote_gate = "ready" if report["remote_ready"] else "blocked"
    local_gate = "ready" if report["local_ready"] else "blocked"
    lines = [
        "# Marketplace Readiness Gate",
        "",
        f"- Repository root: `{report['root']}`",
        f"- Release tag: `{report['release_tag'] or 'not specified'}`",
        f"- PyPI project: `{report['pypi_project']}`",
        f"- Local release gate: {local_gate}",
        f"- Remote launch gate: {remote_gate}",
    ]
    verdict = report.get("closure_verdict") or {}
    if verdict:
        lines.extend([
            "",
            "## Flywheel Closure Verdict",
            f"- Verdict: {verdict['verdict']}",
            f"- Ready gates: {verdict['ready_count']} / {verdict['total_gates']}",
            f"- Reason: {verdict['summary']}",
            f"- Evidence basis: {verdict['evidence_basis']}",
            f"- {verdict['non_fabrication_notice']}",
            "",
            "| Gate | Status | Evidence | Next action |",
            "| --- | --- | --- | --- |",
        ])
        for row in verdict.get("rows", []):
            lines.append(
                f"| {_cell(row['gate'])} | {_cell(row['status'])} | "
                f"{_cell(row['evidence'])} | {_cell(row['next_action'])} |"
            )
    lines.extend([
        "",
        "## Checks",
    ])
    for check in report["checks"]:
        lines.extend(_format_check(check))

    checklist = report.get("closure_checklist") or []
    if checklist:
        ordered_gates = " -> ".join(f"{row['order']}. {row['gate']}" for row in checklist)
        lines.extend([
            "",
            "## Launch Closure Checklist",
            f"Order: {ordered_gates}",
            "",
            "| # | Gate | Status | Evidence | Next action |",
            "| --- | --- | --- | --- | --- |",
        ])
        for row in checklist:
            lines.append(
                f"| {row['order']} | {_cell(row['gate'])} | {_cell(row['status'])} | "
                f"{_cell(row['evidence'])} | {_cell(row['next_action'])} |"
            )

    first_proof = report.get("first_public_proof_kit") or {}
    if first_proof:
        lines.extend([
            "",
            "## First Public Proof Kit",
            f"- {first_proof['disclosure']}",
            f"- Prefilled Growth Flywheel Issue: {first_proof['growth_issue_url']}",
            f"- Prefilled Share Proof Issue: {first_proof['share_issue_url']}",
            f"- Prefilled Bounty Board Issue: {first_proof['bounty_issue_url']}",
            f"- Created Growth Issue URL: {first_proof['created_growth_url']}",
            f"- Created Share Proof Issue URL: {first_proof['created_share_url']}",
            f"- Created Bounty Board Issue URL: {first_proof['created_bounty_url']}",
            "",
            *_community_challenge_pack_lines(first_proof["community_challenge_pack"], heading_level=3),
            "",
            *_protected_publish_fallback_lines(first_proof["protected_publish_fallback"], heading_level=3),
            "",
            *_install_loop_bridge_lines(first_proof["install_loop_bridge"], heading_level=3),
            "",
            *_install_decision_surface_lines(first_proof["install_decision"], heading_level=3),
            "",
            "### Ledger Commands",
            "```bash",
            *first_proof["ledger_commands"],
            "```",
            "",
            *_external_contributor_path_lines(first_proof["external_contributor_path"], heading_level=3),
            "",
            "### Recheck Commands",
            "```bash",
            *first_proof["recheck_commands"],
            "```",
            "",
            "### Copy-ready public proof post",
            "```text",
            first_proof["copy_ready_public_proof_post"],
            "```",
            "",
            f"- {first_proof['non_fabrication_notice']}",
        ])

    launch_asset_audit = report.get("launch_asset_audit") or {}
    if launch_asset_audit:
        lines.extend([
            "",
            format_launch_asset_audit(launch_asset_audit, heading_level=2),
        ])

    lines.extend([
        "",
        "## Next Actions",
        "- If local checks fail, fix manifests, workflows, or version sync before publishing.",
        "- If remote PyPI is blocked, add this repository as a PyPI Trusted Publisher and publish through `.github/workflows/publish-pypi.yml`.",
        "- If remote IssueOps is blocked, merge the local IssueOps files to the repository default branch before using `issues/new?...` links as acquisition loops.",
        "- Generate `cyberhuatuo market-copy` before filling PyPI, Claude, Codex, or release announcement forms.",
        "- Use the Launch Closure Checklist as the launch stop/go list for PyPI, Claude, and Codex market pushes.",
        "- Run `cyberhuatuo traction-proof --username <github-username> --framework langchain --release-tag <tag> --target-contributors 3` after every public launch pulse.",
        "- Run `python scripts/check_marketplace_release.py --remote --strict-remote` after PyPI and the default branch are updated.",
    ])
    return "\n".join(lines)
