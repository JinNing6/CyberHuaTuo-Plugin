"""Verify that public release artifacts do not contain research-only files."""

from __future__ import annotations

import sys
import tarfile
import zipfile
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility
    import tomli as tomllib

PROJECT_NAME = "cyberhuatuo"

FORBIDDEN_PREFIXES = (
    "data/",
    "paper/",
    "paper_usenix/",
    "reports/",
    "cyberhuatuo/sandbox/",
)

FORBIDDEN_NAMES = {
    "academic_benchmark_report.md",
    "benchmark_report.md",
    "EPIDEMIC_REPORT.md",
    "py_files.txt",
}

REQUIRED_WHEEL_MEMBERS = (
    "cyberhuatuo/activation.py",
    "cyberhuatuo/achievements.py",
    "cyberhuatuo/agent_guard.py",
    "cyberhuatuo/agent_hook.py",
    "cyberhuatuo/cli.py",
    "cyberhuatuo/install.py",
    "cyberhuatuo/marketplace.py",
    "cyberhuatuo/mcp_server.py",
    "cyberhuatuo/soul_ring_visuals.py",
    "cyberhuatuo/submissions.py",
    "cyberhuatuo/traction.py",
)

REQUIRED_CONSOLE_SCRIPT_ENTRY_POINTS = (
    "cyberhuatuo = cyberhuatuo.cli:main",
    "cyberhuatuo-mcp = cyberhuatuo.mcp_server:main",
)

REQUIRED_WHEEL_METADATA_SNIPPETS = (
    "Name: cyberhuatuo",
    "Requires-Python: >=3.10",
    "Provides-Extra: dev",
    "Project-URL: Marketplace Release Plan",
    "Keywords:",
    "soul-ring",
    "Local Launch Asset Audit",
    "Full Public Growth Release Bundle",
    "Dirty Worktree Release Coverage",
    "Flywheel Closure Verdict",
    "Ready gates",
    "First Public Proof Kit",
    "Community Challenge Pack",
    "Prefilled Tournament Cup Issue",
    "Prefilled Season Board Issue",
    "cyberhuatuo launch-assets",
    "cyberhuatuo proof-pack",
    "cyberhuatuo first-invite",
    "cyberhuatuo install-command",
    "candidate-install-smoke",
    "Candidate Install Smoke Gate",
    "current_install_command",
    "CyberHuaTuo Install Command",
    "GitHub Web Release",
    "GitHub Actions workflow page",
    "fetch failures",
    "External Contributor Path",
    "First Contributor Invite Pack",
    "Next External Contributor Invite",
    "first_contributor_invite",
    "first_public_proof_pack",
    "Soul Ring Bounty Board",
    "cyberhuatuo bounty",
    "Git Tag Candidate Install Bridge",
    "does not close the PyPI install loop",
    "Growth and Bounty `record-return`",
    "contributor-counting rule",
    "cyberhuatuo market-ready",
    "Marketplace Submission Ledger",
    "cyberhuatuo record-market",
    "cyberhuatuo market-status",
    "cyberhuatuo launch-campaign",
    "cyberhuatuo visual",
    "soul_ring_visual_artifact",
    "cyberhuatuo evidence",
    "Soul Ring Evidence Card",
)

REQUIRED_SDIST_MEMBERS = (
    ".agents/plugins/marketplace.json",
    ".agents/skills/cyberhuatuo-agent-guard/SKILL.md",
    ".agents/skills/cyberhuatuo-soul-ring-visual/SKILL.md",
    ".claude-plugin/marketplace.json",
    ".claude-plugin/plugin.json",
    ".codex/config.toml",
    ".codex-plugin/plugin.json",
    ".github/ISSUE_TEMPLATE/soul-ring-bounty-board.yml",
    ".github/ISSUE_TEMPLATE/soul-ring-growth-flywheel.yml",
    ".github/ISSUE_TEMPLATE/soul-ring-launch-campaign.yml",
    ".github/ISSUE_TEMPLATE/soul-ring-mentor.yml",
    ".github/ISSUE_TEMPLATE/soul-ring-prescription.yml",
    ".github/ISSUE_TEMPLATE/soul-ring-season.yml",
    ".github/ISSUE_TEMPLATE/soul-ring-sect-recruit.yml",
    ".github/ISSUE_TEMPLATE/soul-ring-share-proof.yml",
    ".github/ISSUE_TEMPLATE/soul-ring-tournament.yml",
    ".github/pull_request_template.md",
    ".github/workflows/ci.yml",
    ".github/workflows/package-claude-mcpb.yml",
    ".github/workflows/publish-pypi.yml",
    ".github/workflows/soul-ring-bounty-board.yml",
    ".github/workflows/soul-ring-growth-flywheel.yml",
    ".github/workflows/soul-ring-issue.yml",
    ".github/workflows/soul-ring-launch-campaign.yml",
    ".github/workflows/soul-ring-mentor.yml",
    ".github/workflows/soul-ring-season.yml",
    ".github/workflows/soul-ring-sect-recruit.yml",
    ".github/workflows/soul-ring-share-proof.yml",
    ".github/workflows/soul-ring-tournament.yml",
    ".mcp.json",
    "README.md",
    "README_MCP.md",
    "claude-desktop/.mcpbignore",
    "claude-desktop/README.md",
    "claude-desktop/manifest.json",
    "claude-desktop/pyproject.toml",
    "claude-desktop/src/server.py",
    "docs/agent-action-guard.md",
    "docs/agent-guard-quickstart.md",
    "cyberhuatuo/activation.py",
    "cyberhuatuo/agent_guard.py",
    "cyberhuatuo/agent_hook.py",
    "cyberhuatuo/install.py",
    "cyberhuatuo/marketplace.py",
    "cyberhuatuo/soul_ring_visuals.py",
    "cyberhuatuo/submissions.py",
    "cyberhuatuo/traction.py",
    "docs/MARKETPLACE_RELEASE.md",
    "docs/PRIVACY.md",
    "hooks/hooks.json",
    "hooks/pre_tool_guard.py",
    "pyproject.toml",
    "skills/cyberhuatuo-agent-guard/SKILL.md",
    "skills/cyberhuatuo-soul-ring-visual/SKILL.md",
)

REQUIRED_SDIST_TEXT_SNIPPETS = {
    "README.md": (
        "Local Launch Asset Audit",
        "Full Public Growth Release Bundle",
        "Public Release Operator Runbook",
        "gh release create",
        "gh workflow run publish-pypi.yml",
        "Dirty Worktree Release Coverage",
        "cyberhuatuo launch-assets",
        "cyberhuatuo proof-pack",
        "cyberhuatuo first-invite",
        "cyberhuatuo install-command",
        "candidate-install-smoke",
        "Candidate Install Smoke Gate",
        "current_install_command",
        "CyberHuaTuo Install Command",
        "Install Decision Surface",
        "cyberhuatuo market-copy",
        "Marketplace Submission Ledger",
        "cyberhuatuo record-market",
        "cyberhuatuo market-status",
        "Marketplace Submission Copy Pack",
        "First Contributor Invite Pack",
        "Next External Contributor Invite",
        "first_contributor_invite",
        "first_public_proof_pack",
        "Community Challenge Pack",
        "Flywheel Closure Verdict",
        "Ready gates",
        "Prefilled Tournament Cup Issue",
        "Prefilled Season Board Issue",
        "Soul Ring Bounty Board",
        "cyberhuatuo bounty",
        "Git Tag Candidate Install Bridge",
        "does not close the PyPI install loop",
        "Growth and Bounty `record-return`",
        'record-return --surface "Bounty Board Issue"',
        "Prefilled Bounty Board Issue",
        "Created Bounty Board Issue URL",
        ".github/ISSUE_TEMPLATE/soul-ring-bounty-board.yml",
        ".github/workflows/soul-ring-bounty-board.yml",
        "Protected Publish Fallback",
        "gh workflow run publish-pypi.yml",
        "GitHub Web Release",
        "GitHub Actions workflow page",
        "fetch failures",
        "External Contributor Path",
        "contributor-counting rule",
        "cyberhuatuo market-ready --remote --strict-remote",
        "cyberhuatuo launch-campaign",
        "cyberhuatuo visual",
        "soul_ring_visual_artifact",
        "cyberhuatuo evidence",
        "Soul Ring Evidence Card",
    ),
    "README_MCP.md": (
        "marketplace_readiness_gate",
        "local_launch_asset_audit",
        "marketplace_submission_copy",
        "record_marketplace_submission",
        "marketplace_submission_status",
        "first_contributor_invite",
        "first_public_proof_pack",
        "Next External Contributor Invite",
        "current_install_command",
        "cyberhuatuo install-command",
        "candidate-install-smoke",
        "Candidate Install Smoke Gate",
        "CyberHuaTuo Install Command",
        "Install Decision Surface",
        "cyberhuatuo first-invite",
        "soul_ring_visual_artifact",
        "cyberhuatuo visual",
        "cyberhuatuo market-copy",
        "cyberhuatuo record-market",
        "cyberhuatuo market-status",
        "Marketplace Submission Ledger",
        "cyberhuatuo launch-assets",
        "Community Challenge Pack",
        "Flywheel Closure Verdict",
        "Ready gates",
        "Prefilled Tournament Cup Issue",
        "Prefilled Season Board Issue",
        "GitHub Web Release",
        "GitHub Actions workflow page",
        "soul_ring_bounty_board",
        "cyberhuatuo bounty",
        "Git Tag Candidate Install Bridge",
        "does not close the PyPI install loop",
        "Growth and Bounty `record-return`",
        'record-return --surface "Bounty Board Issue"',
        "Prefilled Bounty Board Issue",
        "Created Bounty Board Issue URL",
        ".github/ISSUE_TEMPLATE/soul-ring-bounty-board.yml",
        ".github/workflows/soul-ring-bounty-board.yml",
    ),
    ".github/workflows/soul-ring-bounty-board.yml": (
        "Launch Closure Checklist",
        "cyberhuatuo market-ready --remote --strict-remote",
        'cyberhuatuo record-return --username ${username} --framework ${framework} --surface "Bounty Board Issue" --source-url ${issueUrl}',
        "cyberhuatuo activation --username ${username}",
        "cyberhuatuo flywheel --username ${username}",
        "cyberhuatuo bounty --username ${username}",
    ),
    ".github/workflows/soul-ring-issue.yml": (
        "Launch Closure Checklist",
        "cyberhuatuo proof-pack --username",
        "cyberhuatuo market-copy --username",
        "cyberhuatuo market-ready --remote --strict-remote",
        '--surface "First Soul Ring Issue" --source-url ${issueUrl}',
    ),
    ".github/workflows/soul-ring-tournament.yml": (
        "Launch Closure Checklist",
        "cyberhuatuo proof-pack --username",
        "cyberhuatuo market-copy --username",
        "cyberhuatuo market-ready --remote --strict-remote",
        '--surface "Tournament Issue" --source-url ${issueUrl}',
    ),
    ".github/workflows/soul-ring-mentor.yml": (
        "Launch Closure Checklist",
        "cyberhuatuo proof-pack --username",
        "cyberhuatuo market-copy --username",
        "cyberhuatuo market-ready --remote --strict-remote",
        '--surface "Mentor Pact Issue" --source-url ${issueUrl}',
    ),
    ".github/workflows/soul-ring-sect-recruit.yml": (
        "Launch Closure Checklist",
        "cyberhuatuo proof-pack --username",
        "cyberhuatuo market-copy --username",
        "cyberhuatuo market-ready --remote --strict-remote",
        '--surface "Sect Recruitment Issue" --source-url ${issueUrl}',
    ),
    ".github/workflows/soul-ring-season.yml": (
        "Launch Closure Checklist",
        "cyberhuatuo proof-pack --username",
        "cyberhuatuo market-copy --username",
        "cyberhuatuo market-ready --remote --strict-remote",
        '--surface "Season Board Issue" --source-url ${issueUrl}',
    ),
    ".github/workflows/soul-ring-pr.yml": (
        "Launch Closure Checklist",
        "cyberhuatuo proof-pack --username",
        "cyberhuatuo market-copy --username",
        "cyberhuatuo market-ready --remote --strict-remote",
        '--surface "Pull Request" --source-url ${prUrl}',
    ),
    ".github/workflows/ci.yml": (
        "python -m cyberhuatuo launch-assets",
        "python -m build --sdist --wheel",
        "python scripts/check_release_boundary.py",
    ),
    ".github/workflows/publish-pypi.yml": (
        "id-token: write",
        "workflow_dispatch",
        "release_tag",
        "manual workflow_dispatch release_tag must start with v",
        "git fetch --force origin main:refs/remotes/origin/main",
        "git merge-base --is-ancestor",
        "Package version matches release tag",
        "python -m cyberhuatuo launch-assets",
        "python -m build --sdist --wheel",
        "python scripts/check_release_boundary.py",
        "pypa/gh-action-pypi-publish@release/v1",
    ),
    ".github/workflows/package-claude-mcpb.yml": (
        "mcpb validate claude-desktop",
        "mcpb pack claude-desktop dist/cyberhuatuo-claude-desktop.mcpb",
    ),
    "docs/MARKETPLACE_RELEASE.md": (
        "PyPI Trusted Publishing",
        "workflow_dispatch",
        "release_tag",
        "Protected Publish Fallback",
        "gh workflow run publish-pypi.yml",
        "GitHub Web Release",
        "GitHub Actions workflow page",
        "Marketplace Submission Copy Pack",
        "cyberhuatuo market-copy",
        "marketplace_submission_copy",
        "cyberhuatuo record-market",
        "cyberhuatuo market-status",
        "record_marketplace_submission",
        "marketplace_submission_status",
        "Marketplace Submission Ledger",
        "First Contributor Invite Pack",
        "Next External Contributor Invite",
        "Community Challenge Pack",
        "Flywheel Closure Verdict",
        "Ready gates",
        "Prefilled Tournament Cup Issue",
        "Prefilled Season Board Issue",
        "cyberhuatuo first-invite",
        "first_contributor_invite",
        "CyberHuaTuo Install Command",
        "cyberhuatuo install-command",
        "candidate-install-smoke",
        "Candidate Install Smoke Gate",
        "current_install_command",
        "Install Decision Surface",
        "Soul Ring Bounty Board",
        "cyberhuatuo bounty",
        "Git Tag Candidate Install Bridge",
        "does not close the PyPI install loop",
        "Growth and Bounty `record-return`",
        'record-return --surface "Bounty Board Issue"',
        "Prefilled Bounty Board Issue",
        ".github/ISSUE_TEMPLATE/soul-ring-bounty-board.yml",
        ".github/workflows/soul-ring-bounty-board.yml",
        "Local Launch Asset Audit",
        "Full Public Growth Release Bundle",
        "Public Release Operator Runbook",
        "gh release create",
        "gh workflow run publish-pypi.yml",
        "Dirty Worktree Release Coverage",
        "External Contributor Path",
        "fetch failures",
        "contributor-counting rule",
        "cyberhuatuo evidence",
        "Soul Ring Evidence Card",
        "claude plugin validate",
        "codex plugin marketplace add",
    ),
    "docs/agent-guard-quickstart.md": (
        "cyberhuatuo guard --self-test",
        "No command was executed.",
        "SELF-TEST PASSED",
        "agent_action_guard",
    ),
    "hooks/hooks.json": (
        "PreToolUse",
        "pre_tool_guard.py",
    ),
    "skills/cyberhuatuo-agent-guard/SKILL.md": (
        "Decision Contract",
        "Never reinterpret `ASK` as approval.",
        "Never bypass `BLOCK`",
    ),
    "cyberhuatuo/marketplace.py": (
        "install_decision",
        "Install Decision Surface",
        "current_install_command",
        "CyberHuaTuo Install Command",
        "bounty_record_return_command",
        "install_loop_bridge",
        "candidate_git_install_command",
        "candidate_smoke_command",
        "python -m cyberhuatuo candidate-install-smoke",
        "Git Tag Candidate Install Bridge",
        "does not close the PyPI install loop",
        '--surface "Bounty Board Issue"',
        "Created Bounty Board Issue URL",
        "Community Challenge Pack",
        "Flywheel Closure Verdict",
        "ready_count",
        "Prefilled Tournament Cup Issue",
        "Prefilled Season Board Issue",
        "Growth, Share, and Bounty proof URLs",
        "submission_ledger",
        "record-market",
        "market-status",
    ),
    "cyberhuatuo/activation.py": (
        "Next External Contributor Invite",
        "first_contributor_invite",
        "first_public_proof_pack",
        "cyberhuatuo first-invite",
        "cyberhuatuo proof-pack",
    ),
    "cyberhuatuo/install.py": (
        "CyberHuaTuo Install Command",
        "current_install_command",
        "format_current_install_command",
        "build_candidate_install_smoke",
        "format_candidate_install_smoke",
        "Candidate Install Smoke Gate",
        "PyPI JSON API",
        "Git Tag Candidate Install Bridge",
        "does not close the PyPI install loop",
    ),
    "cyberhuatuo/submissions.py": (
        "Marketplace Submission Ledger",
        "VALID_STATUSES",
        "VALID_CHANNELS",
        "CYBERHUATUO_MARKETPLACE_SUBMISSION_LEDGER",
        "format_record_marketplace_submission",
        "format_marketplace_submission_status",
    ),
}


def _normalize_archive_name(name: str) -> str:
    name = name.replace("\\", "/").lstrip("./")
    parts = name.split("/")
    if parts and parts[0].startswith("cyberhuatuo-") and not parts[0].endswith((".dist-info", ".egg-info")):
        return "/".join(parts[1:])
    return name


def _iter_archive_names(path: Path) -> list[str]:
    if path.suffix == ".whl" or path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            return archive.namelist()
    if path.suffixes[-2:] == [".tar", ".gz"] or path.suffix == ".tgz":
        with tarfile.open(path, "r:gz") as archive:
            return archive.getnames()
    raise ValueError(f"Unsupported archive type: {path}")


def _find_forbidden(names: list[str]) -> list[str]:
    violations: list[str] = []
    for raw_name in names:
        name = _normalize_archive_name(raw_name)
        filename = Path(name).name
        if filename in FORBIDDEN_NAMES or any(name.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
            violations.append(raw_name)
    return violations


def _archive_kind(path: Path) -> str:
    if path.suffix == ".whl" or path.suffix == ".zip":
        return "wheel"
    if path.suffixes[-2:] == [".tar", ".gz"] or path.suffix == ".tgz":
        return "sdist"
    raise ValueError(f"Unsupported archive type: {path}")


def _read_project_version(root: Path) -> str:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    return str(project["version"])


def _find_current_archive(archives: list[Path], version: str, suffix: str) -> Path | None:
    expected_prefix = f"{PROJECT_NAME}-{version}"
    for archive in archives:
        if archive.name.startswith(expected_prefix) and archive.name.endswith(suffix):
            return archive
    return None


def _read_archive_member(path: Path, normalized_target: str) -> str | None:
    if path.suffix == ".whl" or path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            for raw_name in archive.namelist():
                if _normalize_archive_name(raw_name) == normalized_target:
                    return archive.read(raw_name).decode("utf-8", errors="replace")
        return None

    if path.suffixes[-2:] == [".tar", ".gz"] or path.suffix == ".tgz":
        with tarfile.open(path, "r:gz") as archive:
            for member in archive.getmembers():
                if _normalize_archive_name(member.name) != normalized_target or not member.isfile():
                    continue
                stream = archive.extractfile(member)
                if stream is None:
                    return None
                return stream.read().decode("utf-8", errors="replace")
        return None

    raise ValueError(f"Unsupported archive type: {path}")


def _find_normalized_member_by_suffix(names: list[str], suffix: str) -> str | None:
    for raw_name in names:
        normalized = _normalize_archive_name(raw_name)
        if normalized.endswith(suffix):
            return normalized
    return None


def _find_missing_members(names: list[str], required: tuple[str, ...], label: str) -> list[str]:
    normalized_names = {_normalize_archive_name(name) for name in names}
    return [f"missing {label} member: {member}" for member in required if member not in normalized_names]


def _find_release_contract_violations(path: Path, version: str) -> list[str]:
    names = _iter_archive_names(path)
    kind = _archive_kind(path)

    if kind == "wheel":
        return _find_wheel_contract_violations(path, names, version)
    if kind == "sdist":
        return _find_sdist_contract_violations(path, names)
    raise ValueError(f"Unsupported archive type: {path}")


def _find_wheel_contract_violations(path: Path, names: list[str], version: str) -> list[str]:
    violations = _find_missing_members(names, REQUIRED_WHEEL_MEMBERS, "wheel")

    entry_points_member = _find_normalized_member_by_suffix(names, ".dist-info/entry_points.txt")
    if entry_points_member is None:
        violations.append("missing wheel member: *.dist-info/entry_points.txt")
    else:
        entry_points = _read_archive_member(path, entry_points_member) or ""
        for snippet in REQUIRED_CONSOLE_SCRIPT_ENTRY_POINTS:
            if snippet not in entry_points:
                violations.append(f"missing console script entry point: {snippet}")

    metadata_member = _find_normalized_member_by_suffix(names, ".dist-info/METADATA")
    if metadata_member is None:
        violations.append("missing wheel member: *.dist-info/METADATA")
    else:
        metadata = _read_archive_member(path, metadata_member) or ""
        for snippet in (f"Version: {version}", *REQUIRED_WHEEL_METADATA_SNIPPETS):
            if snippet not in metadata:
                violations.append(f"missing wheel METADATA snippet: {snippet}")

    return violations


def _find_sdist_contract_violations(path: Path, names: list[str]) -> list[str]:
    violations = _find_missing_members(names, REQUIRED_SDIST_MEMBERS, "sdist")

    for member, snippets in REQUIRED_SDIST_TEXT_SNIPPETS.items():
        text = _read_archive_member(path, member)
        if text is None:
            continue
        for snippet in snippets:
            if snippet not in text:
                violations.append(f"missing {member} snippet: {snippet}")

    return violations


def main() -> int:
    dist_dir = Path("dist")
    archives = sorted(dist_dir.glob("*.whl")) + sorted(dist_dir.glob("*.tar.gz"))
    if not archives:
        print("No release archives found under dist/. Run `python -m build` first.")
        return 1

    version = _read_project_version(Path("."))
    failed = False
    current_archives = (
        _find_current_archive(archives, version, ".whl"),
        _find_current_archive(archives, version, ".tar.gz"),
    )
    expected_labels = ("wheel", "sdist")
    for archive, label in zip(current_archives, expected_labels):
        if archive is None:
            failed = True
            print(f"[FAIL] dist/ is missing the current {label} artifact for {PROJECT_NAME} {version}.")
            continue

        violations = _find_forbidden(_iter_archive_names(archive))
        if violations:
            failed = True
            print(f"[FAIL] {archive} contains forbidden release files:")
            for item in violations:
                print(f"  - {item}")
        else:
            print(f"[OK] {archive} has no forbidden research-only files.")

    for archive in current_archives:
        if archive is None:
            continue

        contract_violations = _find_release_contract_violations(archive, version)
        if contract_violations:
            failed = True
            print(f"[FAIL] {archive} is missing marketplace release contract assets:")
            for item in contract_violations:
                print(f"  - {item}")
        else:
            print(f"[OK] {archive} includes marketplace release contract assets.")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
