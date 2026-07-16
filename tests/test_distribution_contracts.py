import ast
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest
import tomllib
import yaml

import scripts.check_release_boundary as release_boundary
from cyberhuatuo import install, marketplace
from scripts.check_release_boundary import _find_forbidden

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_PYPI_VERSION = "0.1.0"
CURRENT_VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
CURRENT_TAG = f"v{CURRENT_VERSION}"
MCP_SERVER_NAME = "io.github.JinNing6/cyberhuatuo"
LAUNCH_CLOSURE_ROWS = [
    "1. Remote acquisition routes",
    "2. PyPI Trusted Publisher",
    "3. GitHub release trigger",
    "4. Registry latest-version proof",
    "5. First public proof",
    "6. Recheck commands",
]


def _release_tuple(version: str) -> tuple[int, ...]:
    assert re.fullmatch(r"(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*", version)
    return tuple(int(part) for part in version.split("."))


def test_codex_plugin_manifest_points_to_existing_skills_and_mcp_config():
    manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))

    assert manifest["skills"] == "./skills/"
    assert manifest["mcpServers"] == "./.mcp.json"
    assert (ROOT / "skills" / "cyberhuatuo-rescue" / "SKILL.md").is_file()
    assert (ROOT / "skills" / "cyberhuatuo-soul-ring-visual" / "SKILL.md").is_file()
    assert (ROOT / ".mcp.json").is_file()


def test_marketplace_release_version_is_pypi_publishable_and_synced():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    package_init = (ROOT / "cyberhuatuo" / "__init__.py").read_text(encoding="utf-8")
    api_source = (ROOT / "cyberhuatuo" / "api.py").read_text(encoding="utf-8")
    codex_manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    claude_manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    claude_marketplace = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    desktop_manifest = json.loads((ROOT / "claude-desktop" / "manifest.json").read_text(encoding="utf-8"))
    desktop_project = tomllib.loads((ROOT / "claude-desktop" / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    version = project["version"]
    assert _release_tuple(version) > _release_tuple(PREVIOUS_PYPI_VERSION)
    assert version not in {PREVIOUS_PYPI_VERSION}
    assert f'__version__ = "{version}"' in package_init
    assert f'version="{version}"' in api_source
    assert codex_manifest["version"] == version
    assert claude_manifest["version"] == version
    assert claude_marketplace["plugins"][0]["version"] == version
    assert desktop_manifest["version"] == version
    assert desktop_project["version"] == version
    assert desktop_project["dependencies"] == [f"cyberhuatuo=={version}"]


def test_claude_plugin_manifest_points_to_existing_skills_and_mcp_config():
    manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))

    assert manifest["name"] == "cyberhuatuo-plugin"
    assert "CyberHuaTuo" in manifest["description"]
    assert manifest["skills"] == "./skills/"
    assert manifest["mcpServers"] == "./.mcp.json"
    assert "claude-code" in manifest["keywords"]
    assert (ROOT / "skills" / "cyberhuatuo-rescue" / "SKILL.md").is_file()
    assert (ROOT / "skills" / "cyberhuatuo-soul-ring-visual" / "SKILL.md").is_file()
    assert (ROOT / ".mcp.json").is_file()


def test_claude_code_marketplace_catalog_points_to_root_plugin():
    marketplace = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert marketplace["name"] == "cyberhuatuo"
    assert marketplace["owner"]["url"] == project["urls"]["Repository"]

    plugins = marketplace["plugins"]
    assert len(plugins) == 1
    plugin = plugins[0]
    assert plugin["name"] == manifest["name"]
    assert plugin["version"] == project["version"] == manifest["version"]
    assert plugin["source"] == "./"
    assert ".." not in plugin["source"]
    assert plugin["category"] == "Developer Tools"
    assert {"mcp", "claude-code", "debugging", "ai-agents", "soul-ring"} <= set(plugin["keywords"])


def test_soul_ring_visual_skill_routes_level_questions_to_chat_visible_artifacts():
    packaged_skill = ROOT / "skills" / "cyberhuatuo-soul-ring-visual" / "SKILL.md"
    local_skill = ROOT / ".agents" / "skills" / "cyberhuatuo-soul-ring-visual" / "SKILL.md"

    assert packaged_skill.is_file()
    assert local_skill.is_file()
    assert packaged_skill.read_text(encoding="utf-8") == local_skill.read_text(encoding="utf-8")

    text = packaged_skill.read_text(encoding="utf-8")
    assert "name: cyberhuatuo-soul-ring-visual" in text
    assert "Use when" in text
    for trigger in ("level", "rank", "badge", "visual", "等级", "魂环", "排名", "展示"):
        assert trigger in text
    for route in (
        "soul_ring_visual_artifact",
        "cyberhuatuo visual",
        "Markdown GIF",
        "PNG fallback",
        "record-share",
        "current real CyberHuaTuo contribution data",
    ):
        assert route in text
    assert "does not invent ranks, downloads, retention, referrals, rewards, or fake contributors" in text


def test_codex_marketplace_catalog_points_to_root_plugin():
    marketplace = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))

    assert marketplace["name"] == "cyberhuatuo"
    assert marketplace["interface"]["displayName"] == "CyberHuaTuo Plugins"

    plugins = marketplace["plugins"]
    assert len(plugins) == 1
    plugin = plugins[0]
    assert plugin["name"] == manifest["name"]
    assert plugin["source"] == {"source": "local", "path": "./"}
    assert plugin["policy"] == {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}
    assert ".." not in plugin["source"]["path"]
    assert plugin["category"] == "Developer Tools"
    assert plugin["interface"]["displayName"] == manifest["interface"]["displayName"]
    assert plugin["interface"]["shortDescription"]
    assert set(plugin["interface"]["capabilities"]) == set(manifest["interface"]["capabilities"])


def test_mcp_config_uses_uvx_console_script_entrypoint():
    mcp_config = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
    server = mcp_config["mcpServers"]["cyberhuatuo"]

    assert server["command"] == "uvx"
    assert server["args"] == ["--from", "cyberhuatuo", "cyberhuatuo-mcp"]


def test_mcp_registry_manifest_matches_pypi_package_and_readme():
    manifest = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert manifest["$schema"] == "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json"
    assert manifest["name"] == MCP_SERVER_NAME
    assert manifest["title"] == "CyberHuaTuo"
    assert 1 <= len(manifest["description"]) <= 100
    assert manifest["version"] == project["version"]
    assert manifest["repository"] == {
        "url": project["urls"]["Repository"],
        "source": "github",
        "id": "1256814099",
    }

    packages = manifest["packages"]
    assert len(packages) == 1
    package = packages[0]
    assert package["registryType"] == "pypi"
    assert package["identifier"] == project["name"] == "cyberhuatuo"
    assert package["version"] == project["version"]
    assert package["runtimeHint"] == "uvx"
    assert package["packageArguments"] == [{"type": "positional", "value": "mcp"}]
    assert package["transport"] == {"type": "stdio"}
    assert f"mcp-name: {MCP_SERVER_NAME}" in readme


def test_cli_mcp_subcommand_delegates_to_stdio_server(monkeypatch):
    from types import ModuleType

    from cyberhuatuo import cli

    fake_server = ModuleType("cyberhuatuo.mcp_server")
    calls = []

    def fake_main():
        calls.append("stdio")
        return 23

    fake_server.main = fake_main
    monkeypatch.setitem(sys.modules, "cyberhuatuo.mcp_server", fake_server)

    assert cli.cmd_mcp(None) == 23
    assert calls == ["stdio"]


def test_mcp_tools_have_directory_review_annotations():
    source_path = ROOT / "cyberhuatuo" / "mcp_server.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    tools = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "tool"
            ):
                tools.append((node.name, decorator))

    assert len(tools) >= 30
    for name, decorator in tools:
        annotation_kw = next((kw for kw in decorator.keywords if kw.arg == "annotations"), None)
        assert annotation_kw is not None, name
        assert isinstance(annotation_kw.value, ast.Call), name
        assert getattr(annotation_kw.value.func, "id", "") == "_tool_annotations", name
        assert annotation_kw.value.args, name
        assert isinstance(annotation_kw.value.args[0], ast.Constant), name
        assert isinstance(annotation_kw.value.args[0].value, str), name
        assert any(kw.arg == "read_only" for kw in annotation_kw.value.keywords), name
        assert any(kw.arg == "destructive" for kw in annotation_kw.value.keywords), name


def test_pyproject_exposes_cli_and_mcp_console_scripts():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["cyberhuatuo"] == "cyberhuatuo.cli:main"
    assert pyproject["project"]["scripts"]["cyberhuatuo-mcp"] == "cyberhuatuo.mcp_server:main"


def test_pyproject_has_marketplace_metadata_for_pypi_discovery():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]

    assert pyproject["build-system"]["requires"] == ["setuptools>=77.0"]
    assert project["license"] == "Apache-2.0"
    assert {"mcp", "codex", "claude", "ai-agents", "debugging", "soul-ring"} <= set(project["keywords"])
    assert any(dep.startswith("packaging>=") for dep in project["dependencies"])
    assert any(dep.startswith("tomli>=") and "python_version" in dep for dep in project["dependencies"])
    assert "Development Status :: 3 - Alpha" in project["classifiers"]
    assert "Intended Audience :: Developers" in project["classifiers"]
    assert "Topic :: Scientific/Engineering :: Artificial Intelligence" in project["classifiers"]
    assert "Topic :: Software Development :: Libraries :: Python Modules" in project["classifiers"]
    assert all(not classifier.startswith("License ::") for classifier in project["classifiers"])

    urls = project["urls"]
    assert urls["MCP Install Guide"].endswith("/blob/main/README_MCP.md")
    assert urls["Marketplace Release Plan"].endswith("/blob/main/docs/MARKETPLACE_RELEASE.md")


def test_pyproject_exposes_dev_quality_gate_extra():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    dev_deps = pyproject["project"]["optional-dependencies"]["dev"]
    assert any(dep.startswith("pytest>=") for dep in dev_deps)
    assert any(dep.startswith("pytest-asyncio>=") for dep in dev_deps)
    assert any(dep.startswith("ruff>=") for dep in dev_deps)
    assert any(dep.startswith("build>=") for dep in dev_deps)


def test_current_install_command_surface_selects_registry_or_git_bridge_from_real_pypi_metadata():
    def current_fetcher(url, _headers, _timeout):
        assert url == "https://pypi.org/pypi/cyberhuatuo/json"
        return {"info": {"version": CURRENT_VERSION}, "releases": {CURRENT_VERSION: []}, "urls": []}

    current_text = install.format_current_install_command(
        username="alice",
        framework="langchain",
        release_tag=CURRENT_TAG,
        target_contributors=3,
        fetcher=current_fetcher,
    )
    assert "Recommended install: `python -m pip install --upgrade cyberhuatuo`" in current_text
    assert "Git Tag Candidate Install Bridge" not in current_text
    assert "current_install_command" in current_text

    def stale_fetcher(url, _headers, _timeout):
        assert url == "https://pypi.org/pypi/cyberhuatuo/json"
        return {"info": {"version": PREVIOUS_PYPI_VERSION}, "releases": {PREVIOUS_PYPI_VERSION: []}, "urls": []}

    stale_text = install.format_current_install_command(
        username="alice",
        framework="langchain",
        release_tag="v0.2.1",
        target_contributors=3,
        fetcher=stale_fetcher,
    )
    assert "Install status: `registry-stale`" in stale_text
    assert "Canonical PyPI install: `python -m pip install --upgrade cyberhuatuo`" in stale_text
    assert (
        'python -m pip install --upgrade "cyberhuatuo @ '
        'git+https://github.com/JinNing6/CyberHuaTuo-Plugin.git@v0.2.1"'
    ) in stale_text
    assert "does not close the PyPI install loop" in stale_text


def test_candidate_install_smoke_gate_verifies_public_git_tag_install_and_cleans_success(tmp_path):
    created_temp = tmp_path / "candidate-smoke"
    removed: list[Path] = []
    calls: list[list[str]] = []

    def fake_mkdtemp(prefix: str) -> str:
        assert prefix == "cyberhuatuo-candidate-install-"
        created_temp.mkdir()
        return str(created_temp)

    def fake_rmtree(path: str | Path) -> None:
        removed.append(Path(path))

    def fake_runner(command, **_kwargs):
        command = [str(part) for part in command]
        calls.append(command)
        joined = " ".join(command)
        if "import cyberhuatuo" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=f"{CURRENT_VERSION}\n", stderr="")
        if "--help" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="install-command\nproof-pack\ncandidate-install-smoke\n",
                stderr="",
            )
        if "install-command" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="CyberHuaTuo Install Command\nGit Tag Candidate Install Bridge\ncyberhuatuo proof-pack\n",
                stderr="",
            )
        if "proof-pack" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="No-Network First Public Proof Pack\nExternal Contributor Path\ncyberhuatuo first-invite\n",
                stderr="",
            )
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    report = install.build_candidate_install_smoke(
        username="alice",
        framework="langchain",
        release_tag=CURRENT_TAG,
        target_contributors=5,
        repo="JinNing6/CyberHuaTuo-Plugin",
        pypi_project="cyberhuatuo",
        python_executable="python",
        runner=fake_runner,
        mkdtemp=fake_mkdtemp,
        rmtree=fake_rmtree,
    )
    text = install.format_candidate_install_smoke(report)

    assert report["status"] == "pass"
    assert report["temp_dir"] == str(created_temp)
    assert report["cleanup"] == "removed"
    assert removed == [created_temp]
    assert any(command[:3] == ["python", "-m", "venv"] for command in calls)
    assert any(
        f"cyberhuatuo @ git+https://github.com/JinNing6/CyberHuaTuo-Plugin.git@{CURRENT_TAG}" in argument
        for command in calls
        for argument in command
    )
    assert any("install-command" in command for command in calls for command in command)
    assert any("proof-pack" in command for command in calls for command in command)
    assert "Candidate Install Smoke Gate" in text
    assert "Status: pass" in text
    assert "Temporary environment cleanup: removed" in text
    assert "No downloads, retention, repost counts, referrals, rewards, or fake contributors are claimed." in text


def test_candidate_install_smoke_gate_retains_temp_dir_on_failure(tmp_path):
    created_temp = tmp_path / "candidate-smoke"
    removed: list[Path] = []

    def fake_mkdtemp(prefix: str) -> str:
        created_temp.mkdir()
        return str(created_temp)

    def fake_rmtree(path: str | Path) -> None:
        removed.append(Path(path))

    def fake_runner(command, **_kwargs):
        command = [str(part) for part in command]
        if "install" in command and any("git+https://github.com" in part for part in command):
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="tag not found")
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    report = install.build_candidate_install_smoke(
        username="alice",
        framework="langchain",
        release_tag="v0.2.1",
        repo="JinNing6/CyberHuaTuo-Plugin",
        pypi_project="cyberhuatuo",
        python_executable="python",
        runner=fake_runner,
        mkdtemp=fake_mkdtemp,
        rmtree=fake_rmtree,
    )
    text = install.format_candidate_install_smoke(report)

    assert report["status"] == "fail"
    assert report["cleanup"] == "retained"
    assert report["temp_dir"] == str(created_temp)
    assert removed == []
    assert "Status: fail" in text
    assert "Temporary environment cleanup: retained for inspection" in text
    assert "tag not found" in text


def test_candidate_install_smoke_gate_is_wired_into_release_surfaces():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_cn = (ROOT / "README_CN.md").read_text(encoding="utf-8")
    release_doc = (ROOT / "docs" / "MARKETPLACE_RELEASE.md").read_text(encoding="utf-8")
    cli_source = (ROOT / "cyberhuatuo" / "cli.py").read_text(encoding="utf-8")
    install_source = (ROOT / "cyberhuatuo" / "install.py").read_text(encoding="utf-8")
    marketplace_source = (ROOT / "cyberhuatuo" / "marketplace.py").read_text(encoding="utf-8")
    boundary_source = (ROOT / "scripts" / "check_release_boundary.py").read_text(encoding="utf-8")

    for text in (readme, readme_cn, release_doc, cli_source, install_source, marketplace_source, boundary_source):
        assert "candidate-install-smoke" in text
    assert "Candidate Install Smoke Gate" in readme
    assert "Candidate Install Smoke Gate" in release_doc
    assert "build_candidate_install_smoke" in install_source
    assert "format_candidate_install_smoke" in install_source
    assert "python -m cyberhuatuo candidate-install-smoke" in marketplace_source
    assert "not run automatically inside lightweight CI" in release_doc


def test_ci_runs_full_release_quality_gates():
    workflow_path = ROOT / ".github" / "workflows" / "ci.yml"

    assert workflow_path.is_file()
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

    assert workflow["name"] == "CI"
    assert workflow["on"]["push"] is None
    assert workflow["on"]["pull_request"] is None
    assert workflow["permissions"] == {"contents": "read"}

    jobs = workflow["jobs"]
    assert set(jobs) == {"quality-gates"}
    steps = jobs["quality-gates"]["steps"]
    step_text = "\n".join(
        str(step.get("run", "")) + "\n" + str(step.get("uses", ""))
        for step in steps
    )

    assert "actions/checkout@v4" in step_text
    assert "actions/setup-python@v5" in step_text
    assert 'python -m pip install -e ".[dev]"' in step_text
    assert "python -m ruff check ." in step_text
    assert "python -m pytest -q" in step_text
    assert "python -m cyberhuatuo launch-assets" in step_text
    assert "python -m build --sdist --wheel" in step_text
    assert "python scripts/check_release_boundary.py" in step_text
    assert step_text.index("python -m pytest -q") < step_text.index("python -m cyberhuatuo launch-assets")
    assert step_text.index("python -m cyberhuatuo launch-assets") < step_text.index("python -m build --sdist --wheel")


def test_pypi_publish_workflow_uses_trusted_publishing_after_quality_gates():
    workflow_path = ROOT / ".github" / "workflows" / "publish-pypi.yml"

    assert workflow_path.is_file()
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

    assert workflow["name"] == "Publish PyPI"
    assert workflow["on"]["release"]["types"] == ["published"]
    dispatch = workflow["on"]["workflow_dispatch"]
    assert dispatch["inputs"]["release_tag"]["required"] is True
    assert dispatch["inputs"]["release_tag"]["type"] == "string"
    assert "Existing v* tag" in dispatch["inputs"]["release_tag"]["description"]

    jobs = workflow["jobs"]
    assert set(jobs) == {"publish"}
    job = jobs["publish"]
    assert job["environment"] == "pypi"
    assert job["permissions"] == {"contents": "read", "id-token": "write"}

    steps = job["steps"]
    checkout_step = next(step for step in steps if step.get("uses") == "actions/checkout@v4")
    assert checkout_step["with"]["ref"] == "${{ steps.release.outputs.tag }}"
    assert checkout_step["with"]["fetch-depth"] == 0
    step_text = "\n".join(
        str(step.get("name", "")) + "\n" + str(step.get("run", "")) + "\n" + str(step.get("uses", ""))
        for step in steps
    )

    assert "Resolve release tag" in step_text
    assert "manual workflow_dispatch release_tag must start with v" in step_text
    assert "actions/checkout@v4" in step_text
    assert "git fetch --force origin main:refs/remotes/origin/main" in step_text
    assert "git merge-base --is-ancestor" in step_text
    assert "Package version matches release tag" in step_text
    assert "actions/setup-python@v5" in step_text
    assert 'python -m pip install -e ".[dev]"' in step_text
    assert "python -m ruff check ." in step_text
    assert "python -m pytest -q" in step_text
    assert "python -m cyberhuatuo launch-assets" in step_text
    assert "python -m build --sdist --wheel" in step_text
    assert "python scripts/check_release_boundary.py" in step_text
    assert "pypa/gh-action-pypi-publish@release/v1" in step_text
    assert "PYPI_TOKEN" not in workflow_path.read_text(encoding="utf-8")
    assert step_text.index("python -m pytest -q") < step_text.index("python -m cyberhuatuo launch-assets")
    assert step_text.index("python -m cyberhuatuo launch-assets") < step_text.index("python -m build --sdist --wheel")


def test_claude_desktop_mcpb_manifest_uses_uv_runtime_and_privacy_policy():
    manifest_path = ROOT / "claude-desktop" / "manifest.json"
    wrapper_path = ROOT / "claude-desktop" / "src" / "server.py"
    pyproject_path = ROOT / "claude-desktop" / "pyproject.toml"
    ignore_path = ROOT / "claude-desktop" / ".mcpbignore"
    readme_path = ROOT / "claude-desktop" / "README.md"
    privacy_path = ROOT / "docs" / "PRIVACY.md"

    assert manifest_path.is_file()
    assert wrapper_path.is_file()
    assert pyproject_path.is_file()
    assert ignore_path.is_file()
    assert readme_path.is_file()
    assert privacy_path.is_file()

    root_project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["manifest_version"] == "0.4"
    assert manifest["name"] == "cyberhuatuo"
    assert manifest["display_name"] == "CyberHuaTuo"
    assert manifest["version"] == root_project["version"]
    assert manifest["license"] == root_project["license"]
    assert manifest["server"]["type"] == "uv"
    assert manifest["server"]["entry_point"] == "src/server.py"
    assert manifest["server"]["mcp_config"]["command"] == "uv"
    assert manifest["server"]["mcp_config"]["args"] == [
        "run",
        "--directory",
        "${__dirname}",
        "src/server.py",
    ]
    assert manifest["compatibility"]["platforms"] == ["darwin", "linux", "win32"]
    assert manifest["compatibility"]["runtimes"]["python"] == ">=3.10"
    assert "soul-ring" in manifest["keywords"]
    assert "ai-agents" in manifest["keywords"]
    assert manifest["privacy_policies"] == [
        "https://github.com/JinNing6/CyberHuaTuo-Plugin/blob/main/docs/PRIVACY.md"
    ]

    tools = manifest["tools"]
    assert any(tool["name"] == "diagnose" for tool in tools)
    assert any(tool["name"] == "upload_prescription" for tool in tools)
    assert any(tool["name"] == "soul_ring_campaign_pack" for tool in tools)
    assert any(tool["name"] == "soul_ring_bounty_board" for tool in tools)
    assert any(tool["name"] == "soul_ring_launch_campaign" for tool in tools)
    launch_campaign_tool = next(tool for tool in tools if tool["name"] == "soul_ring_launch_campaign")
    assert "Campaign Recap And Next Sprint" in launch_campaign_tool["description"]
    assert "next growth_campaign command" in launch_campaign_tool["description"]
    assert "traction-proof --record-snapshot" in launch_campaign_tool["description"]
    assert any(tool["name"] == "marketplace_submission_copy" for tool in tools)
    assert any(tool["name"] == "record_marketplace_submission" for tool in tools)
    assert any(tool["name"] == "marketplace_submission_status" for tool in tools)
    assert any(tool["name"] == "current_install_command" for tool in tools)
    assert any(tool["name"] == "first_contributor_invite" for tool in tools)
    assert any(tool["name"] == "soul_ring_traction_proof" for tool in tools)
    assert any(tool["name"] == "record_soul_ring_traction_snapshot" for tool in tools)
    assert any(tool["name"] == "marketplace_readiness_gate" for tool in tools)
    assert any(tool["name"] == "first_public_proof_pack" for tool in tools)
    bounty_tool = next(tool for tool in tools if tool["name"] == "soul_ring_bounty_board")
    traction_tool = next(tool for tool in tools if tool["name"] == "soul_ring_traction_proof")
    snapshot_tool = next(tool for tool in tools if tool["name"] == "record_soul_ring_traction_snapshot")
    preflight_tool = next(tool for tool in tools if tool["name"] == "marketplace_readiness_gate")
    launch_asset_tool = next(tool for tool in tools if tool["name"] == "local_launch_asset_audit")
    proof_pack_tool = next(tool for tool in tools if tool["name"] == "first_public_proof_pack")
    market_copy_tool = next(tool for tool in tools if tool["name"] == "marketplace_submission_copy")
    record_market_tool = next(tool for tool in tools if tool["name"] == "record_marketplace_submission")
    market_status_tool = next(tool for tool in tools if tool["name"] == "marketplace_submission_status")
    install_command_tool = next(tool for tool in tools if tool["name"] == "current_install_command")
    first_invite_tool = next(tool for tool in tools if tool["name"] == "first_contributor_invite")
    record_return_tool = next(tool for tool in tools if tool["name"] == "record_soul_ring_external_return")
    record_share_tool = next(tool for tool in tools if tool["name"] == "record_soul_ring_share_attribution")
    assert "coverage gap" in bounty_tool["description"]
    assert "cyberhuatuo bounty" in bounty_tool["description"]
    assert "does not invent downloads" in bounty_tool["description"]
    assert "PyPI listing" in market_copy_tool["description"]
    assert "Claude MCPB listing" in market_copy_tool["description"]
    assert "Codex plugin listing" in market_copy_tool["description"]
    assert "GitHub Release post" in market_copy_tool["description"]
    assert "Community Challenge Pack" in market_copy_tool["description"]
    assert "record-return" in market_copy_tool["description"]
    assert "record-share" in market_copy_tool["description"]
    assert "does not invent downloads" in market_copy_tool["description"]
    assert "Marketplace Submission Ledger" in record_market_tool["description"]
    assert "reviewable public URL" in record_market_tool["description"]
    assert "cyberhuatuo record-market" in record_market_tool["description"]
    assert "does not invent downloads" in record_market_tool["description"]
    assert "Marketplace Submission Ledger" in market_status_tool["description"]
    assert "cyberhuatuo market-status" in market_status_tool["description"]
    assert "record-market" in market_status_tool["description"]
    assert "does not invent approvals" in market_status_tool["description"]
    assert "PyPI JSON API latest-version proof" in install_command_tool["description"]
    assert "Git Tag Candidate Install Bridge" in install_command_tool["description"]
    assert "cyberhuatuo install-command" in install_command_tool["description"]
    assert "does not invent downloads" in install_command_tool["description"]
    assert "target one external contributor" in first_invite_tool["description"]
    assert "First Soul Ring Prescription" in first_invite_tool["description"]
    assert "record-session" in first_invite_tool["description"]
    assert "does not invent downloads" in first_invite_tool["description"]
    assert "first_contributor_invite" in record_return_tool["description"]
    assert "first_public_proof_pack" in record_return_tool["description"]
    assert "next external contributor" in record_return_tool["description"]
    assert "does not invent downloads" in record_return_tool["description"]
    assert "first_contributor_invite" in record_share_tool["description"]
    assert "first_public_proof_pack" in record_share_tool["description"]
    assert "next external contributor" in record_share_tool["description"]
    assert "does not invent downloads" in record_share_tool["description"]
    assert "GitHub Pull Requests API" in traction_tool["description"]
    assert "GitHub Contents API" in traction_tool["description"]
    assert "GitHub Releases API" in traction_tool["description"]
    assert "release.published" in traction_tool["description"]
    assert "workflow_dispatch fallback" in traction_tool["description"]
    assert "PyPI JSON API package readiness" in traction_tool["description"]
    assert "missing default-branch IssueOps files are launch blockers" in traction_tool["description"]
    assert "provenance warnings" in traction_tool["description"]
    assert "PR authors" in traction_tool["description"]
    assert "separate from IssueOps issue counts" in traction_tool["description"]
    assert "fetch failures" in traction_tool["description"]
    assert "No-Network First Public Proof Pack" in traction_tool["description"]
    assert "PR author proof" in snapshot_tool["description"]
    assert "PyPI package readiness" in snapshot_tool["description"]
    assert "remote IssueOps readiness" in snapshot_tool["description"]
    assert "Launch Closure Checklist" in preflight_tool["description"]
    assert "Flywheel Closure Verdict" in preflight_tool["description"]
    assert "Ready gates" in preflight_tool["description"]
    assert "closed, not closed, or unverified" in preflight_tool["description"]
    assert "First Public Proof Kit" in preflight_tool["description"]
    assert "Community Challenge Pack" in preflight_tool["description"]
    assert "Protected Publish Fallback command" in preflight_tool["description"]
    assert "Local Launch Asset Audit" in preflight_tool["description"]
    assert "Full Public Growth Release Bundle" in preflight_tool["description"]
    assert "Public Release Operator Runbook" in preflight_tool["description"]
    assert "Dirty Worktree Release Coverage" in preflight_tool["description"]
    assert "Growth Flywheel Issue" in preflight_tool["description"]
    assert "Share Proof Issue" in preflight_tool["description"]
    assert "PyPI Trusted Publisher" in preflight_tool["description"]
    assert "release.published" in preflight_tool["description"]
    assert "workflow_dispatch fallback" in preflight_tool["description"]
    assert "Codex" in preflight_tool["description"]
    assert "Full Public Growth Release Bundle" in launch_asset_tool["description"]
    assert "Public Release Operator Runbook" in launch_asset_tool["description"]
    assert "gh release create" in launch_asset_tool["description"]
    assert "gh workflow run publish-pypi.yml" in launch_asset_tool["description"]
    assert "Dirty Worktree Release Coverage" in launch_asset_tool["description"]
    assert "git status --porcelain" in launch_asset_tool["description"]
    assert "No-Network First Public Proof Pack" in proof_pack_tool["description"]
    assert "Community Challenge Pack" in proof_pack_tool["description"]
    assert "does not fetch public metrics" in proof_pack_tool["description"]
    assert "cyberhuatuo proof-pack" in proof_pack_tool["description"]
    assert "Protected Publish Fallback command" in proof_pack_tool["description"]
    assert "gh workflow run publish-pypi.yml -f release_tag=<tag>" in proof_pack_tool["description"]
    assert "no PYPI_TOKEN fallback is allowed" in proof_pack_tool["description"]
    assert "Created Growth Issue URL" in proof_pack_tool["description"]
    assert "record-return" in proof_pack_tool["description"]
    assert "External Contributor Path" in proof_pack_tool["description"]
    assert "first-session command" in proof_pack_tool["description"]
    assert "first contribution command" in proof_pack_tool["description"]
    assert any(tool["name"] == "soul_ring_activation_funnel" for tool in tools)
    assert any(tool["name"] == "record_soul_ring_external_return" for tool in tools)
    assert any(tool["name"] == "record_soul_ring_share_attribution" for tool in tools)
    assert any(tool["name"] == "record_soul_ring_evidence" for tool in tools)
    assert any(tool["name"] == "soul_ring_share_attribution_report" for tool in tools)
    assert any(tool["name"] == "soul_ring_share_proof_leaderboard" for tool in tools)
    evidence_tool = next(tool for tool in tools if tool["name"] == "record_soul_ring_evidence")
    assert "Soul Ring Evidence Card" in evidence_tool["description"]
    assert "reviewable public evidence" in evidence_tool["description"]
    assert "append-only" in evidence_tool["description"]
    assert all("description" in tool for tool in tools)

    wrapper = wrapper_path.read_text(encoding="utf-8")
    assert "from cyberhuatuo.mcp_server import main" in wrapper
    assert "main()" in wrapper

    mcpb_project = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    assert mcpb_project["project"]["dependencies"] == [f"cyberhuatuo=={root_project['version']}"]

    ignore = ignore_path.read_text(encoding="utf-8")
    assert ".venv/" in ignore
    assert "server/venv/" in ignore
    assert "*.egg-info/" in ignore

    readme = readme_path.read_text(encoding="utf-8")
    privacy = privacy_path.read_text(encoding="utf-8")
    assert "Privacy Policy" in readme
    assert "Privacy Policy" in privacy
    assert "CyberHuaTuo" in privacy


def test_claude_mcpb_workflow_validates_and_packs_desktop_extension():
    workflow_path = ROOT / ".github" / "workflows" / "package-claude-mcpb.yml"

    assert workflow_path.is_file()
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

    assert workflow["name"] == "Package Claude MCPB"
    assert workflow["on"]["pull_request"] is None
    assert workflow["on"]["release"]["types"] == ["published"]
    assert workflow["permissions"] == {"contents": "read"}

    jobs = workflow["jobs"]
    assert set(jobs) == {"package-claude-mcpb"}
    steps = jobs["package-claude-mcpb"]["steps"]
    step_text = "\n".join(
        str(step.get("name", "")) + "\n" + str(step.get("run", "")) + "\n" + str(step.get("uses", ""))
        for step in steps
    )

    assert "actions/checkout@v4" in step_text
    assert "actions/setup-node@v4" in step_text
    assert "npm install -g @anthropic-ai/mcpb" in step_text
    assert "mcpb validate claude-desktop" in step_text
    assert "mcpb pack claude-desktop dist/cyberhuatuo-claude-desktop.mcpb" in step_text
    assert "actions/upload-artifact@v4" in step_text


def test_marketplace_release_doc_covers_pypi_claude_and_codex_paths():
    doc_path = ROOT / "docs" / "MARKETPLACE_RELEASE.md"
    release_launch_assets_command = (
        "cyberhuatuo launch-assets --username <maintainer-github> --framework langchain "
        f"--release-tag {CURRENT_TAG} --target-contributors 3"
    )

    assert doc_path.is_file()
    doc = doc_path.read_text(encoding="utf-8")

    assert "PyPI project already exists" in doc
    assert "0.1.0 was uploaded on 2026-03-12" in doc
    assert "Do not try to re-upload `0.1.0`" in doc
    assert "additional Trusted Publisher" in doc
    assert "JinNing6/CyberHuaTuo-Plugin" in doc
    assert "PyPI Trusted Publishing" in doc
    assert ".github/workflows/publish-pypi.yml" in doc
    assert "pypa/gh-action-pypi-publish@release/v1" in doc
    assert "workflow_dispatch" in doc
    assert "release_tag" in doc
    assert "origin/main" in doc
    assert "without `PYPI_TOKEN`" in doc
    assert "uvx --from cyberhuatuo cyberhuatuo-mcp" in doc
    assert "Claude Connectors Directory" in doc
    assert "claude-plugins-official" in doc
    assert "claude.ai/admin-settings/directory/submissions/plugins/new" in doc
    assert "platform.claude.com/plugins/submit" in doc
    assert "MCPB" in doc
    assert "claude-desktop/manifest.json" in doc
    assert ".claude-plugin/marketplace.json" in doc
    assert ".github/workflows/package-claude-mcpb.yml" in doc
    assert "mcpb validate claude-desktop" in doc
    assert "claude plugin marketplace add JinNing6/CyberHuaTuo-Plugin" in doc
    assert "claude plugin validate ." in doc
    assert ".claude-plugin/plugin.json" in doc
    assert "Codex plugin directory" in doc
    assert ".codex-plugin/plugin.json" in doc
    assert ".agents/plugins/marketplace.json" in doc
    assert "codex plugin marketplace add JinNing6/CyberHuaTuo-Plugin" in doc
    assert "codex mcp list" in doc
    assert "## MCP Registry" in doc
    assert "io.github.JinNing6/cyberhuatuo" in doc
    assert "mcp-publisher validate" in doc
    assert "mcp-publisher publish" in doc
    assert "registry.modelcontextprotocol.io/v0.1/servers" in doc
    assert "cyberhuatuo record-return" in doc
    assert "cyberhuatuo activation" in doc
    assert "cyberhuatuo record-share" in doc
    assert "cyberhuatuo share-report" in doc
    assert "cyberhuatuo share-leaderboard" in doc
    assert "cyberhuatuo market-ready" in doc
    assert "python scripts/check_marketplace_release.py --remote --strict-remote" in doc
    assert "Campaign Recap And Next Sprint" in doc
    assert "observed real contributors" in doc
    assert "next `growth_campaign` command" in doc
    assert "traction-proof --record-snapshot" in doc
    assert "PyPI package readiness" in doc
    assert "Remote IssueOps Readiness" in doc
    assert "GitHub Releases API" in doc
    assert "release.published" in doc
    assert "GitHub Contents API" in doc
    assert "issues/new?..." in doc
    assert "install-loop blocker" in doc
    assert "activation ledger" in doc.lower()
    assert "soul ring" in doc.lower()
    assert "accepted-prescription" in doc
    assert "No public channel claim is considered launched until the install command has been tested from a clean environment" in doc
    assert "Flywheel Closure Verdict" in doc
    assert "`closed`, `not closed`, or `unverified`" in doc
    assert "Ready gates" in doc
    assert "Launch Closure Checklist" in doc
    assert "marketplace_readiness_gate" in doc
    assert "First Public Proof Kit" in doc
    assert "Community Challenge Pack" in doc
    assert "Prefilled Tournament Cup Issue" in doc
    assert "Prefilled Mentor Pact Issue" in doc
    assert "Prefilled Sect Recruitment Issue" in doc
    assert "Prefilled Season Board Issue" in doc
    assert "Created Growth Issue URL" in doc
    assert "Created Share Proof Issue URL" in doc
    assert "Copy-ready public proof post" in doc
    assert "Local Launch Asset Audit" in doc
    assert "cyberhuatuo launch-assets" in doc
    assert release_launch_assets_command in doc
    assert "Full Public Growth Release Bundle" in doc
    assert "Public Release Operator Runbook" in doc
    assert "gh release create" in doc
    assert "gh workflow run publish-pypi.yml" in doc
    assert "Dirty Worktree Release Coverage" in doc
    assert "No-Network First Public Proof Pack" in doc
    assert "cyberhuatuo proof-pack" in doc
    assert "cyberhuatuo market-copy" in doc
    assert "Marketplace Submission Copy Pack" in doc
    assert "Submission Portals And Evidence URLs" in doc
    assert "PyPI Trusted Publisher settings: https://pypi.org/manage/project/cyberhuatuo/settings/publishing/" in doc
    assert "Claude plugin submit (Console): https://platform.claude.com/plugins/submit" in doc
    assert "Claude Connectors Directory submission guide: https://claude.com/docs/connectors/building/submission" in doc
    assert "Codex plugin evidence: `codex plugin marketplace add JinNing6/CyberHuaTuo-Plugin`" in doc
    assert "PyPI listing copy" in doc
    assert "Claude MCPB listing copy" in doc
    assert "Codex plugin listing copy" in doc
    assert "Protected Publish Fallback" in doc
    assert f"gh workflow run publish-pypi.yml -f release_tag={CURRENT_TAG}" in doc
    assert "gh run list --workflow publish-pypi.yml --limit 5" in doc
    assert "no `PYPI_TOKEN` fallback is allowed" in doc
    assert "External Contributor Path" in doc
    assert "first-session command" in doc
    assert "contributor-counting rule" in doc
    assert "does not stage files, publish releases, upload to PyPI, mutate remotes, or claim traction" in doc


def test_marketplace_readiness_gate_passes_local_release_contracts_without_remote_claims():
    report = marketplace.build_marketplace_readiness(ROOT, remote=False)
    text = marketplace.format_marketplace_readiness(report)

    assert report["local_ready"] is True
    assert report["remote_checked"] is False
    assert report["exit_code"] == 0
    assert report["closure_verdict"]["verdict"] == "unverified"
    assert report["closure_verdict"]["ready_count"] == 1
    assert report["closure_verdict"]["total_gates"] == 6
    assert "Marketplace Readiness Gate" in text
    assert "Local release gate: ready" in text
    assert "Remote launch gate: skipped" in text
    assert "## Flywheel Closure Verdict" in text
    assert "Verdict: unverified" in text
    assert "Ready gates: 1 / 6" in text
    assert "Public state was not fetched" in text
    assert "| Remote acquisition routes | pending |" in text
    assert "PyPI local release chain: pass" in text
    assert "protected manual workflow_dispatch tag fallback" in text
    assert "launch-assets/lint/tests/build/release-boundary" in text
    assert "Claude local release chain: pass" in text
    assert "Codex local release chain: pass" in text
    assert "IssueOps local acquisition files: pass" in text
    assert "cyberhuatuo traction-proof" in text
    assert "python scripts/check_marketplace_release.py --remote --strict-remote" in text
    assert "## Launch Closure Checklist" in text
    previous = -1
    for row in LAUNCH_CLOSURE_ROWS:
        current = text.index(row)
        assert current > previous
        previous = current
    assert "| 1 | Remote acquisition routes | pending |" in text
    assert "| 2 | PyPI Trusted Publisher | manual |" in text
    assert "| 3 | GitHub release trigger | pending |" in text
    assert "| 4 | Registry latest-version proof | pending |" in text
    assert "| 5 | First public proof | pending |" in text
    assert "| 6 | Recheck commands | pass |" in text
    assert "cyberhuatuo market-ready --remote --strict-remote" in text
    assert "cyberhuatuo proof-pack --username your-github-username --framework langchain" in text
    assert "cyberhuatuo market-copy --username your-github-username --framework langchain" in text
    assert "## First Public Proof Kit" in text
    assert "Prefilled Growth Flywheel Issue:" in text
    assert "template=soul-ring-growth-flywheel.yml" in text
    assert "Prefilled Share Proof Issue:" in text
    assert "template=soul-ring-share-proof.yml" in text
    assert "Prefilled Bounty Board Issue:" in text
    assert "template=soul-ring-bounty-board.yml" in text
    assert "### Community Challenge Pack" in text
    assert "Prefilled Tournament Cup Issue:" in text
    assert "Prefilled Mentor Pact Issue:" in text
    assert "Prefilled Sect Recruitment Issue:" in text
    assert "Prefilled Season Board Issue:" in text
    assert "Created Growth Issue URL: <created Growth Issue URL after submission>" in text
    assert "Created Share Proof Issue URL: <created Share Proof Issue URL after submission>" in text
    assert "Created Bounty Board Issue URL: <created Bounty Board Issue URL after submission>" in text
    assert "## Community Challenge Pack" in text
    assert "Prefilled Tournament Cup Issue:" in text
    assert "template=soul-ring-tournament.yml" in text
    assert "Prefilled Mentor Pact Issue:" in text
    assert "template=soul-ring-mentor.yml" in text
    assert "Prefilled Sect Recruitment Issue:" in text
    assert "template=soul-ring-sect-recruit.yml" in text
    assert "Prefilled Season Board Issue:" in text
    assert "template=soul-ring-season.yml" in text
    assert "Created Tournament Issue URL: <created Tournament Issue URL after submission>" in text
    assert "Created Mentor Pact Issue URL: <created Mentor Pact Issue URL after submission>" in text
    assert "Created Sect Recruitment Issue URL: <created Sect Recruitment Issue URL after submission>" in text
    assert "Created Season Board Issue URL: <created Season Board Issue URL after submission>" in text
    assert "cyberhuatuo tournament your-github-username <external-contributor-github-username>" in text
    assert "cyberhuatuo mentor your-github-username <external-contributor-github-username> --framework langchain" in text
    assert "cyberhuatuo sect-recruit CyberHuaTuo-Sect your-github-username --invitee <external-contributor-github-username> --framework langchain" in text
    assert "cyberhuatuo season --framework langchain --top-n 10" in text
    assert "Tournament wins, mentor seniority, sect membership, season history, adoption, and rewards are not invented" in text
    assert "### Protected Publish Fallback" in text
    assert "GitHub Web Release:" in text
    assert "https://github.com/JinNing6/CyberHuaTuo-Plugin/releases/new?tag=%3Crelease-tag%3E" in text
    assert "GitHub Actions workflow page:" in text
    assert "https://github.com/JinNing6/CyberHuaTuo-Plugin/actions/workflows/publish-pypi.yml" in text
    assert "gh workflow run publish-pypi.yml -f release_tag=<release-tag>" in text
    assert "gh run list --workflow publish-pypi.yml --limit 5" in text
    assert "PyPI Trusted Publisher must match this repository, workflow file, and `pypi` environment." in text
    assert "No `PYPI_TOKEN` fallback is allowed." in text
    assert "### Git Tag Candidate Install Bridge" in text
    assert "Canonical PyPI install: `python -m pip install --upgrade cyberhuatuo`" in text
    assert (
        'python -m pip install --upgrade "cyberhuatuo @ '
        'git+https://github.com/JinNing6/CyberHuaTuo-Plugin.git@<release-tag>"'
    ) in text
    assert "does not close the PyPI install loop" in text
    assert "Recheck PyPI latest-version proof before claiming public install readiness." in text
    assert (
        "cyberhuatuo record-return --username your-github-username --framework langchain "
        '--surface "Growth Flywheel Issue" --source-url <created Growth Issue URL after submission>'
    ) in text
    assert (
        "cyberhuatuo record-return --username your-github-username --framework auto "
        '--surface "Bounty Board Issue" --source-url <created Bounty Board Issue URL after submission>'
    ) in text
    assert (
        "cyberhuatuo record-share --username your-github-username --framework langchain "
        "--share-url <public share URL after posting> --source-url <created Share Proof Issue URL after submission>"
    ) in text
    assert text.index('--surface "Bounty Board Issue"') < text.index(
        "cyberhuatuo bounty --username your-github-username"
    )
    assert "Copy-ready public proof post" in text
    assert "No downloads, retention, repost counts, referrals, rewards, or fake contributors are claimed." in text
    assert "## External Contributor Path" in text
    assert "External contributor username: `<external-contributor-github-username>`" in text
    assert "python -m pip install --upgrade cyberhuatuo" in text
    assert (
        "cyberhuatuo record-session --username <external-contributor-github-username> "
        '--framework langchain --surface "First external contributor session" '
        "--source-url <created Growth Issue URL after submission>"
    ) in text
    assert "cyberhuatuo challenge --username <external-contributor-github-username> --framework langchain" in text
    assert "First Soul Ring Prescription Issue:" in text
    assert "template=soul-ring-prescription.yml" in text
    assert "github_username=%3Cexternal-contributor-github-username%3E" in text
    assert "External Share Proof Issue:" in text
    assert "source_url=%3Ccreated+First+Soul+Ring+Prescription+Issue+URL+after+submission%3E" in text
    assert "Created First Soul Ring Prescription Issue URL: <created First Soul Ring Prescription Issue URL after submission>" in text
    assert (
        "Only real public Issue authors, public Pull Request authors, and local ledger actors "
        "count toward target contributors."
    ) in text
    assert "Copy-ready external contributor invite" in text
    assert "No downloads, rewards, referrals, or fake contributors are claimed." in text
    assert "## Local Launch Asset Audit" in text
    assert "Status: pass" in text
    assert "Read-only: does not stage files, publish releases, upload to PyPI, mutate remotes, or claim traction." in text
    assert "IssueOps acquisition bundle" in text
    assert "Package and marketplace metadata" in text
    assert "### Minimal Git Add Commands" in text
    assert "git add .github/ISSUE_TEMPLATE/soul-ring-prescription.yml" in text
    for path in (
        ".github/ISSUE_TEMPLATE/soul-ring-prescription.yml",
        ".github/workflows/soul-ring-issue.yml",
        ".github/ISSUE_TEMPLATE/soul-ring-tournament.yml",
        ".github/workflows/soul-ring-tournament.yml",
        ".github/ISSUE_TEMPLATE/soul-ring-mentor.yml",
        ".github/workflows/soul-ring-mentor.yml",
        ".github/ISSUE_TEMPLATE/soul-ring-sect-recruit.yml",
        ".github/workflows/soul-ring-sect-recruit.yml",
        ".github/ISSUE_TEMPLATE/soul-ring-season.yml",
        ".github/workflows/soul-ring-season.yml",
    ):
        assert path in text
    assert ".github/ISSUE_TEMPLATE/soul-ring-bounty-board.yml" in text
    assert ".github/workflows/soul-ring-bounty-board.yml" in text
    assert ".github/workflows/soul-ring-share-proof.yml" in text
    assert "git add .github/workflows/publish-pypi.yml" in text
    assert ".codex-plugin/plugin.json" in text
    assert ".agents/plugins/marketplace.json" in text
    assert "claude-desktop/manifest.json" in text
    assert "## Full Public Growth Release Bundle" in text
    assert "IssueOps public acquisition routes" in text
    assert "Marketplace package metadata and docs" in text
    assert "Public growth runtime modules and scripts" in text
    assert "Growth tests and release gates" in text
    assert "## Public Release Operator Runbook" in text
    assert (
        "Read-only: this runbook prints release commands but does not stage, commit, "
        "push, tag, create releases, or publish packages."
    ) in text
    assert "Use the Full Bundle Git Add Commands above, then review `git diff --cached`." in text
    assert "git push origin HEAD:main" in text
    assert "GitHub Web Release: https://github.com/JinNing6/CyberHuaTuo-Plugin/releases/new?tag=%3Crelease-tag%3E" in text
    assert "GitHub Actions workflow page: https://github.com/JinNing6/CyberHuaTuo-Plugin/actions/workflows/publish-pypi.yml" in text
    assert "gh release create <release-tag>" in text
    assert "--verify-tag --notes-from-tag" in text
    assert "gh workflow run publish-pypi.yml -f release_tag=<release-tag>" in text
    assert "cyberhuatuo market-copy --username your-github-username --framework langchain --release-tag <release-tag> --target-contributors 3" in text
    assert "workflow_dispatch requires `.github/workflows/publish-pypi.yml` to be on the default branch." in text
    assert "git add cyberhuatuo/activation.py" in text
    assert "tests/test_soul_ring_growth.py" in text
    assert "## Dirty Worktree Release Coverage" in text
    assert "git status --porcelain" in text


def test_marketplace_readiness_gate_blocks_strict_remote_when_pypi_lags_local_version():
    content_prefix = "https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin/contents/"

    def fake_fetcher(url, _headers, _timeout):
        if url == "https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin":
            return {
                "stargazers_count": 1,
                "forks_count": 0,
                "watchers_count": 1,
                "subscribers_count": 0,
                "open_issues_count": 0,
            }
        if url.startswith("https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin/pulls?"):
            return []
        if url == f"https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin/releases/tags/{CURRENT_TAG}":
            return {
                "tag_name": CURRENT_TAG,
                "draft": False,
                "prerelease": False,
                "html_url": f"https://github.com/JinNing6/CyberHuaTuo-Plugin/releases/tag/{CURRENT_TAG}",
                "published_at": "2026-06-04T00:00:00Z",
            }
        if url.startswith("https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin/issues?"):
            return []
        if url.startswith(content_prefix):
            path = url.removeprefix(content_prefix)
            return {"type": "file", "path": path}
        if url == "https://pypi.org/pypi/cyberhuatuo/json":
            return {"info": {"version": PREVIOUS_PYPI_VERSION}, "releases": {PREVIOUS_PYPI_VERSION: []}, "urls": []}
        raise AssertionError(url)

    report = marketplace.build_marketplace_readiness(
        ROOT,
        remote=True,
        strict_remote=True,
        release_tag=CURRENT_TAG,
        fetcher=fake_fetcher,
    )
    text = marketplace.format_marketplace_readiness(report)

    assert report["local_ready"] is True
    assert report["remote_checked"] is True
    assert report["remote_ready"] is False
    assert report["exit_code"] == 1
    assert report["closure_verdict"]["verdict"] == "not closed"
    assert report["closure_verdict"]["ready_count"] == 3
    assert report["closure_verdict"]["total_gates"] == 6
    assert "Remote launch gate: blocked" in text
    assert "## Flywheel Closure Verdict" in text
    assert "Verdict: not closed" in text
    assert "Ready gates: 3 / 6" in text
    assert "PyPI Trusted Publisher, Registry latest-version proof, First public proof" in text
    assert "PyPI remote package: fail" in text
    assert "install-loop launch blocker" in text
    assert ".github/workflows/publish-pypi.yml" in text
    assert "Remote IssueOps default branch: pass" in text
    assert "## Launch Closure Checklist" in text
    assert "| 1 | Remote acquisition routes | pass |" in text
    assert "| 3 | GitHub release trigger | pass |" in text
    assert "| 4 | Registry latest-version proof | fail |" in text
    assert "| 5 | First public proof | pending |" in text
    assert "## First Public Proof Kit" in text
    assert "Created Growth Issue URL: <created Growth Issue URL after submission>" in text
    assert "Created Share Proof Issue URL: <created Share Proof Issue URL after submission>" in text
    assert "Copy-ready public proof post" in text
    assert "## Local Launch Asset Audit" in text
    assert "git add .github/ISSUE_TEMPLATE/soul-ring-prescription.yml" in text
    assert ".github/ISSUE_TEMPLATE/soul-ring-growth-flywheel.yml" in text
    assert "## Public Release Operator Runbook" in text
    assert f"GitHub Web Release: https://github.com/JinNing6/CyberHuaTuo-Plugin/releases/new?tag={CURRENT_TAG}" in text
    assert "GitHub Actions workflow page: https://github.com/JinNing6/CyberHuaTuo-Plugin/actions/workflows/publish-pypi.yml" in text
    assert f"gh release create {CURRENT_TAG}" in text
    assert f"dist/cyberhuatuo-{CURRENT_VERSION}.tar.gz" in text
    assert f"gh workflow run publish-pypi.yml -f release_tag={CURRENT_TAG}" in text
    assert f"cyberhuatuo market-copy --username your-github-username --framework langchain --release-tag {CURRENT_TAG} --target-contributors 3" in text


def test_marketplace_readiness_gate_reports_closed_only_when_all_public_closure_gates_pass(tmp_path, monkeypatch):
    monkeypatch.setenv("CYBERHUATUO_ACTIVATION_LEDGER", str(tmp_path / "activation-events.jsonl"))
    content_prefix = "https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin/contents/"

    def fake_fetcher(url, _headers, _timeout):
        if url == "https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin":
            return {
                "stargazers_count": 7,
                "forks_count": 2,
                "watchers_count": 7,
                "subscribers_count": 1,
                "open_issues_count": 4,
            }
        if url.startswith("https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin/pulls?"):
            return []
        if url == "https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin/releases/tags/v0.2.1":
            return {
                "tag_name": "v0.2.1",
                "draft": False,
                "prerelease": False,
                "html_url": "https://github.com/JinNing6/CyberHuaTuo-Plugin/releases/tag/v0.2.1",
                "published_at": "2026-06-04T00:00:00Z",
            }
        if url.startswith("https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin/issues?"):
            if "labels=soul-ring&" in url:
                return [
                    {"user": {"login": "alice"}},
                    {"user": {"login": "bob"}},
                    {"user": {"login": "carol"}},
                ]
            return []
        if url.startswith(content_prefix):
            path = url.removeprefix(content_prefix)
            return {"type": "file", "path": path}
        if url == "https://pypi.org/pypi/cyberhuatuo/json":
            return {"info": {"version": CURRENT_VERSION}, "releases": {CURRENT_VERSION: []}, "urls": []}
        raise AssertionError(url)

    report = marketplace.build_marketplace_readiness(
        ROOT,
        remote=True,
        strict_remote=True,
        release_tag=CURRENT_TAG,
        target_contributors=3,
        fetcher=fake_fetcher,
    )
    text = marketplace.format_marketplace_readiness(report)

    assert report["local_ready"] is True
    assert report["remote_checked"] is True
    assert report["remote_ready"] is True
    assert report["exit_code"] == 0
    assert report["closure_verdict"]["verdict"] == "closed"
    assert report["closure_verdict"]["ready_count"] == 6
    assert report["closure_verdict"]["total_gates"] == 6
    assert report["closure_verdict"]["blocking_gates"] == []
    assert "Remote launch gate: ready" in text
    assert "## Flywheel Closure Verdict" in text
    assert "Verdict: closed" in text
    assert "Ready gates: 6 / 6" in text
    assert "All closure gates are supported by real local and public evidence." in text
    assert "| First public proof | pass | Observed 3 / 3 real contributor identities" in text
    assert "No downloads, retention, repost counts, referrals, rewards, reviews, or fake contributors are claimed." in text


def test_marketplace_readiness_gate_blocks_strict_remote_when_release_tag_is_missing():
    content_prefix = "https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin/contents/"

    def fake_fetcher(url, _headers, _timeout):
        if url == "https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin":
            return {
                "stargazers_count": 1,
                "forks_count": 0,
                "watchers_count": 1,
                "subscribers_count": 0,
                "open_issues_count": 0,
            }
        if url.startswith("https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin/pulls?"):
            return []
        if url == f"https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin/releases/tags/{CURRENT_TAG}":
            raise OSError("HTTP 404: Not Found")
        if url.startswith("https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin/issues?"):
            return []
        if url.startswith(content_prefix):
            path = url.removeprefix(content_prefix)
            return {"type": "file", "path": path}
        if url == "https://pypi.org/pypi/cyberhuatuo/json":
            return {"info": {"version": CURRENT_VERSION}, "releases": {CURRENT_VERSION: []}, "urls": []}
        raise AssertionError(url)

    report = marketplace.build_marketplace_readiness(
        ROOT,
        remote=True,
        strict_remote=True,
        release_tag=CURRENT_TAG,
        fetcher=fake_fetcher,
    )
    text = marketplace.format_marketplace_readiness(report)

    assert report["local_ready"] is True
    assert report["remote_checked"] is True
    assert report["remote_ready"] is True
    assert report["exit_code"] == 0
    assert "Remote launch gate: ready" in text
    assert "GitHub release trigger: warn" in text
    assert "protected workflow_dispatch release_tag fallback" in text
    assert "Publish a GitHub Release for public provenance" in text
    assert "PyPI remote package: pass" in text
    assert "| 1 | Remote acquisition routes | pass |" in text
    assert "| 3 | GitHub release trigger | fallback |" in text
    assert "| 4 | Registry latest-version proof | pass |" in text
    assert "## First Public Proof Kit" in text
    assert "Prefilled Growth Flywheel Issue:" in text
    assert "Prefilled Share Proof Issue:" in text
    assert "### Install Decision Surface" in text
    assert "cyberhuatuo install-command --username your-github-username --framework langchain" in text
    assert "## Local Launch Asset Audit" in text


def test_first_public_proof_pack_is_no_network_and_cli_recordable():
    pack = marketplace.build_first_public_proof_pack(
        repo="JinNing6/CyberHuaTuo-Plugin",
        pypi_project="cyberhuatuo",
        username="alice",
        framework="langchain",
        release_tag="v0.2.1",
        target_contributors=5,
    )
    text = marketplace.format_first_public_proof_pack(pack)

    assert pack["network"] == "not_fetched"
    assert "No-Network First Public Proof Pack" in text
    assert "does not fetch public metrics" in text
    assert "does not write ledger events" in text
    assert "does not publish releases" in text
    assert "does not invent traction" in text
    assert (
        "cyberhuatuo launch-assets --username alice --framework langchain "
        "--release-tag v0.2.1 --target-contributors 5"
    ) in text
    assert "Prefilled Growth Flywheel Issue:" in text
    assert "template=soul-ring-growth-flywheel.yml" in text
    assert "Prefilled Share Proof Issue:" in text
    assert "template=soul-ring-share-proof.yml" in text
    assert "Prefilled Bounty Board Issue:" in text
    assert "template=soul-ring-bounty-board.yml" in text
    assert "Created Growth Issue URL: <created Growth Issue URL after submission>" in text
    assert "Created Share Proof Issue URL: <created Share Proof Issue URL after submission>" in text
    assert "Created Bounty Board Issue URL: <created Bounty Board Issue URL after submission>" in text
    assert "### Protected Publish Fallback" in text
    assert "gh workflow run publish-pypi.yml -f release_tag=v0.2.1" in text
    assert "gh run list --workflow publish-pypi.yml --limit 5" in text
    assert "No `PYPI_TOKEN` fallback is allowed." in text
    assert "### Git Tag Candidate Install Bridge" in text
    assert "Canonical PyPI install: `python -m pip install --upgrade cyberhuatuo`" in text
    assert (
        'python -m pip install --upgrade "cyberhuatuo @ '
        'git+https://github.com/JinNing6/CyberHuaTuo-Plugin.git@v0.2.1"'
    ) in text
    assert "does not close the PyPI install loop" in text
    assert "Recheck PyPI latest-version proof before claiming public install readiness." in text
    assert "## Install Decision Surface" in text
    assert (
        "cyberhuatuo install-command --username alice --framework langchain "
        "--release-tag v0.2.1 --target-contributors 5 --repo JinNing6/CyberHuaTuo-Plugin "
        "--pypi-project cyberhuatuo"
    ) in text
    assert "MCP install decision tool: `current_install_command`" in text
    assert "paste its Recommended Install" in text
    assert (
        "cyberhuatuo record-return --username alice --framework langchain "
        '--surface "Growth Flywheel Issue" --source-url <created Growth Issue URL after submission>'
    ) in text
    assert (
        "cyberhuatuo record-return --username alice --framework auto "
        '--surface "Bounty Board Issue" --source-url <created Bounty Board Issue URL after submission>'
    ) in text
    assert (
        "cyberhuatuo record-share --username alice --framework langchain "
        "--share-url <public share URL after posting> --source-url <created Share Proof Issue URL after submission>"
    ) in text
    assert text.index('--surface "Bounty Board Issue"') < text.index(
        "cyberhuatuo bounty --username alice"
    )
    assert (
        "cyberhuatuo market-ready --remote --strict-remote --username alice "
        "--framework langchain --release-tag v0.2.1 --target-contributors 5"
    ) in text
    assert (
        "cyberhuatuo market-copy --username alice --framework langchain "
        "--release-tag v0.2.1 --target-contributors 5"
    ) in text
    assert (
        "cyberhuatuo bounty --username alice --framework auto --top-n 8 "
        "--release-tag v0.2.1 --target-contributors 5"
    ) in text
    assert (
        "cyberhuatuo first-invite --username alice --invitee <external-contributor-github-username> "
        "--framework langchain --release-tag v0.2.1 --target-contributors 5 "
        "--source-url <created Growth Issue URL after submission>"
    ) in text
    assert (
        "cyberhuatuo traction-proof --username alice --framework langchain "
        "--release-tag v0.2.1 --target-contributors 5"
    ) in text
    assert "Copy-ready public proof post" in text
    assert "No downloads, retention, repost counts, referrals, rewards, or fake contributors are claimed." in text


def test_first_contributor_invite_pack_targets_one_external_contributor_without_fake_progress():
    pack = marketplace.build_first_contributor_invite_pack(
        repo="JinNing6/CyberHuaTuo-Plugin",
        pypi_project="cyberhuatuo",
        username="alice",
        invitee="bob",
        framework="langchain",
        release_tag="v0.2.1",
        target_contributors=5,
        source_url="https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/123",
    )
    text = marketplace.format_first_contributor_invite_pack(pack)

    assert pack["network"] == "not_fetched"
    assert pack["invitee"] == "bob"
    assert "First Contributor Invite Pack" in text
    assert "Target invitee: `bob`" in text
    assert "Candidate Snapshot" in text
    assert "No public metrics are fetched" in text
    assert "First Soul Ring Prescription Issue:" in text
    assert "github_username=bob" in text
    assert "External Share Proof Issue:" in text
    assert (
        'cyberhuatuo record-session --username bob --framework langchain '
        '--surface "First external contributor session" '
        "--source-url https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/123"
    ) in text
    assert "cyberhuatuo challenge --username bob --framework langchain" in text
    assert "cyberhuatuo proof-pack --username alice --framework langchain --release-tag v0.2.1 --target-contributors 5" in text
    assert "cyberhuatuo market-copy --username alice --framework langchain --release-tag v0.2.1 --target-contributors 5" in text
    assert "cyberhuatuo traction-proof --username alice --framework langchain --release-tag v0.2.1 --target-contributors 5" in text
    assert "## Install Decision Surface" in text
    assert (
        "cyberhuatuo install-command --username alice --framework langchain "
        "--release-tag v0.2.1 --target-contributors 5 --repo JinNing6/CyberHuaTuo-Plugin "
        "--pypi-project cyberhuatuo"
    ) in text
    assert "MCP install decision tool: `current_install_command`" in text
    assert "paste its Recommended Install" in text
    assert "Only real public Issue authors, public Pull Request authors, and local ledger actors" in text
    assert "does not invent downloads, retention, repost counts, referrals, rewards, reviews, or fake contributors" in text
    assert "<external-contributor-github-username>" not in text


def test_marketplace_submission_copy_pack_is_channel_specific_and_non_fabricating():
    pack = marketplace.build_marketplace_submission_copy_pack(
        repo="JinNing6/CyberHuaTuo-Plugin",
        pypi_project="cyberhuatuo",
        username="alice",
        framework="langchain",
        release_tag="v0.2.1",
        target_contributors=5,
    )
    text = marketplace.format_marketplace_submission_copy_pack(pack)

    assert pack["network"] == "not_fetched"
    assert pack["version"] == "0.2.1"
    assert "Marketplace Submission Copy Pack" in text
    assert "No public metrics are fetched" in text
    assert "does not invent downloads, retention, repost counts, referrals, rewards, reviews, or fake contributors" in text
    assert "## PyPI Listing Copy" in text
    assert "Project URLs to expose" in text
    assert "MCP Install Guide" in text
    assert "Marketplace Release Plan" in text
    assert "python -m pip install --upgrade cyberhuatuo" in text
    assert "uvx --from cyberhuatuo cyberhuatuo-mcp" in text
    assert "## Install Decision Commands" in text
    assert (
        "cyberhuatuo install-command --username alice --framework langchain "
        "--release-tag v0.2.1 --target-contributors 5 --repo JinNing6/CyberHuaTuo-Plugin "
        "--pypi-project cyberhuatuo"
    ) in text
    assert "current_install_command" in text
    assert "paste its Recommended Install" in text
    assert "## Claude MCPB Listing Copy" in text
    assert "Claude Desktop install note" in text
    assert "dist/cyberhuatuo-claude-desktop.mcpb" in text
    assert "mcpb validate claude-desktop" in text
    assert "mcpb pack claude-desktop dist/cyberhuatuo-claude-desktop.mcpb" in text
    assert "## Codex Plugin Listing Copy" in text
    assert ".codex-plugin/plugin.json" in text
    assert ".agents/plugins/marketplace.json" in text
    assert "codex plugin marketplace add JinNing6/CyberHuaTuo-Plugin" in text
    assert "## GitHub Release Post" in text
    assert "GitHub Web Release: https://github.com/JinNing6/CyberHuaTuo-Plugin/releases/new?tag=v0.2.1" in text
    assert "GitHub Actions workflow page: https://github.com/JinNing6/CyberHuaTuo-Plugin/actions/workflows/publish-pypi.yml" in text
    assert "gh release create v0.2.1" in text
    assert "## Submission Portals And Evidence URLs" in text
    assert "PyPI Trusted Publisher settings: https://pypi.org/manage/project/cyberhuatuo/settings/publishing/" in text
    assert "PyPI project page: https://pypi.org/project/cyberhuatuo/" in text
    assert "Claude plugin submit (Console): https://platform.claude.com/plugins/submit" in text
    assert (
        "Claude.ai directory submit (Team/Enterprise): "
        "https://claude.ai/admin-settings/directory/submissions/plugins/new"
    ) in text
    assert "Claude Connectors Directory submission guide: https://claude.com/docs/connectors/building/submission" in text
    assert "Claude Connectors Directory: https://www.claude.com/connectors" in text
    assert "Codex plugin evidence: `codex plugin marketplace add JinNing6/CyberHuaTuo-Plugin`" in text
    assert "Codex workspace Apps settings evidence" in text
    assert "Do not record the prefilled form URL as proof" in text
    assert "## Public Proof CTA" in text
    assert "## Marketplace Submission Ledger" in text
    assert "cyberhuatuo record-market --username alice --framework langchain --channel pypi --status submitted" in text
    assert "cyberhuatuo record-market --username alice --framework langchain --channel claude-code --status submitted" in text
    assert "cyberhuatuo record-market --username alice --framework langchain --channel claude-desktop --status submitted" in text
    assert "cyberhuatuo record-market --username alice --framework langchain --channel codex --status submitted" in text
    assert "cyberhuatuo record-market --username alice --framework langchain --channel github-release --status submitted" in text
    assert "cyberhuatuo market-status --username alice --framework langchain --release-tag v0.2.1" in text
    assert "Prefilled Bounty Board Issue:" in text
    assert "template=soul-ring-bounty-board.yml" in text
    assert "Created Bounty Board Issue URL: <created Bounty Board Issue URL after submission>" in text
    assert "## Git Tag Candidate Install Bridge" in text
    assert "Canonical PyPI install: `python -m pip install --upgrade cyberhuatuo`" in text
    assert (
        'python -m pip install --upgrade "cyberhuatuo @ '
        'git+https://github.com/JinNing6/CyberHuaTuo-Plugin.git@v0.2.1"'
    ) in text
    assert "does not close the PyPI install loop" in text
    assert "cyberhuatuo bounty --username alice --framework auto --top-n 8 --release-tag v0.2.1 --target-contributors 5" in text
    assert "cyberhuatuo record-return --username alice --framework langchain" in text
    assert (
        "cyberhuatuo record-return --username alice --framework auto "
        '--surface "Bounty Board Issue" --source-url <created Bounty Board Issue URL after submission>'
    ) in text
    assert "cyberhuatuo record-share --username alice --framework langchain" in text
    assert "cyberhuatuo traction-proof --username alice --framework langchain --release-tag v0.2.1 --target-contributors 5" in text
    assert "target 5 real first-ring contributors" in text
    assert "Only real public Issue authors, public Pull Request authors, and local ledger actors count" in text
    assert "Copy-ready maintainer announcement" in text
    assert "First Soul Ring" in text


def test_cli_marketplace_submission_ledger_round_trip(tmp_path):
    env = {"CYBERHUATUO_MARKETPLACE_SUBMISSION_LEDGER": str(tmp_path / "marketplace-submissions.jsonl")}

    record_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "record-market",
            "--username",
            "alice",
            "--framework",
            "langchain",
            "--channel",
            "pypi",
            "--status",
            "submitted",
            "--submission-url",
            "https://pypi.org/project/cyberhuatuo/",
            "--release-tag",
            "v0.2.1",
        ],
        cwd=ROOT,
        env={**os.environ.copy(), **env},
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert record_result.returncode == 0, record_result.stdout + record_result.stderr
    assert "Marketplace submission recorded" in record_result.stdout

    status_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "market-status",
            "--username",
            "alice",
            "--framework",
            "langchain",
            "--release-tag",
            "v0.2.1",
        ],
        cwd=ROOT,
        env={**os.environ.copy(), **env},
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert status_result.returncode == 0, status_result.stdout + status_result.stderr
    assert "Marketplace Submission Ledger" in status_result.stdout
    assert "pypi | submitted | https://pypi.org/project/cyberhuatuo/" in status_result.stdout


def test_launch_asset_audit_prints_full_release_bundle_and_dirty_coverage():
    audit = marketplace.build_launch_asset_audit(
        ROOT,
        git_status_lines=[
            " M cyberhuatuo/marketplace.py",
            "?? tests/test_distribution_contracts.py",
            " M private-launch-note.md",
        ],
    )
    text = marketplace.format_launch_asset_audit(audit)

    assert audit["status"] == "pass"
    assert audit["dirty_worktree"]["available"] is True
    assert "Full Public Growth Release Bundle" in text
    assert "This full bundle prevents publishing stale PyPI/Claude/Codex growth code" in text
    assert "IssueOps public acquisition routes" in text
    assert "Marketplace package metadata and docs" in text
    assert "Public growth runtime modules and scripts" in text
    assert "Growth tests and release gates" in text
    assert "git add .github/ISSUE_TEMPLATE/soul-ring-prescription.yml" in text
    assert ".github/ISSUE_TEMPLATE/soul-ring-growth-flywheel.yml" in text
    assert "git add README.md README_CN.md README_MCP.md" in text
    assert "git add cyberhuatuo/activation.py cyberhuatuo/achievements.py" in text
    assert "git add scripts/check_marketplace_release.py scripts/check_release_boundary.py" in text
    assert "Public Release Operator Runbook" in text
    assert "GitHub Web Release: https://github.com/JinNing6/CyberHuaTuo-Plugin/releases/new?tag=%3Crelease-tag%3E" in text
    assert "GitHub Actions workflow page: https://github.com/JinNing6/CyberHuaTuo-Plugin/actions/workflows/publish-pypi.yml" in text
    assert "gh release create <release-tag>" in text
    assert "gh workflow run publish-pypi.yml -f release_tag=<release-tag>" in text
    assert "Dirty Worktree Release Coverage" in text
    assert "Captured with read-only `git status --porcelain`" in text
    assert "| M | cyberhuatuo/marketplace.py | full public growth release bundle |" in text
    assert "| ?? | tests/test_distribution_contracts.py | full public growth release bundle |" in text
    assert "| M | private-launch-note.md | requires separate review |" in text
    assert (
        "Review before release: changed files outside the full public growth release bundle "
        "must be staged intentionally or left out with a written reason."
    ) in text


def test_marketplace_readiness_cli_and_script_expose_release_gate():
    cli_result = subprocess.run(
        [sys.executable, "-m", "cyberhuatuo", "market-ready", "--no-remote"],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert cli_result.returncode == 0, cli_result.stdout + cli_result.stderr
    assert "Marketplace Readiness Gate" in cli_result.stdout
    assert "Local release gate: ready" in cli_result.stdout
    assert "Remote launch gate: skipped" in cli_result.stdout
    assert "Flywheel Closure Verdict" in cli_result.stdout
    assert "Verdict: unverified" in cli_result.stdout
    assert "Ready gates: 1 / 6" in cli_result.stdout
    assert "Launch Closure Checklist" in cli_result.stdout
    assert "First Public Proof Kit" in cli_result.stdout
    assert "Community Challenge Pack" in cli_result.stdout
    assert "cyberhuatuo market-copy --username your-github-username --framework langchain" in cli_result.stdout
    assert "cyberhuatuo first-invite --username your-github-username --invitee <external-contributor-github-username>" in cli_result.stdout
    assert "Local Launch Asset Audit" in cli_result.stdout

    script_result = subprocess.run(
        [sys.executable, "scripts/check_marketplace_release.py", "--no-remote"],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert script_result.returncode == 0, script_result.stdout + script_result.stderr
    assert "Marketplace Readiness Gate" in script_result.stdout
    assert "python scripts/check_marketplace_release.py --remote --strict-remote" in script_result.stdout
    assert "Launch Closure Checklist" in script_result.stdout
    assert "First Public Proof Kit" in script_result.stdout
    assert "Community Challenge Pack" in script_result.stdout
    assert "Local Launch Asset Audit" in script_result.stdout

    launch_assets_result = subprocess.run(
        [sys.executable, "-m", "cyberhuatuo", "launch-assets"],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert launch_assets_result.returncode == 0, launch_assets_result.stdout + launch_assets_result.stderr
    assert "Local Launch Asset Audit" in launch_assets_result.stdout
    assert "Read-only: does not stage files, publish releases, upload to PyPI, mutate remotes, or claim traction." in launch_assets_result.stdout
    assert "git add .github/ISSUE_TEMPLATE/soul-ring-prescription.yml" in launch_assets_result.stdout
    assert ".github/ISSUE_TEMPLATE/soul-ring-growth-flywheel.yml" in launch_assets_result.stdout
    assert "git add .github/workflows/publish-pypi.yml" in launch_assets_result.stdout
    assert "Full Public Growth Release Bundle" in launch_assets_result.stdout
    assert "Dirty Worktree Release Coverage" in launch_assets_result.stdout

    proof_pack_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "proof-pack",
            "--username",
            "alice",
            "--framework",
            "langchain",
            "--release-tag",
            "v0.2.1",
            "--target-contributors",
            "5",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert proof_pack_result.returncode == 0, proof_pack_result.stdout + proof_pack_result.stderr
    assert "No-Network First Public Proof Pack" in proof_pack_result.stdout
    assert "Prefilled Growth Flywheel Issue:" in proof_pack_result.stdout
    assert "Prefilled Bounty Board Issue:" in proof_pack_result.stdout
    assert "template=soul-ring-bounty-board.yml" in proof_pack_result.stdout
    assert "Community Challenge Pack" in proof_pack_result.stdout
    assert "template=soul-ring-tournament.yml" in proof_pack_result.stdout
    assert "template=soul-ring-mentor.yml" in proof_pack_result.stdout
    assert "template=soul-ring-sect-recruit.yml" in proof_pack_result.stdout
    assert "template=soul-ring-season.yml" in proof_pack_result.stdout
    assert "cyberhuatuo season --framework langchain --top-n 10" in proof_pack_result.stdout
    assert "cyberhuatuo record-return --username alice --framework langchain" in proof_pack_result.stdout
    assert (
        "cyberhuatuo record-return --username alice --framework auto "
        '--surface "Bounty Board Issue" --source-url <created Bounty Board Issue URL after submission>'
    ) in proof_pack_result.stdout
    assert "Git Tag Candidate Install Bridge" in proof_pack_result.stdout
    assert (
        'python -m pip install --upgrade "cyberhuatuo @ '
        'git+https://github.com/JinNing6/CyberHuaTuo-Plugin.git@v0.2.1"'
    ) in proof_pack_result.stdout
    assert "does not close the PyPI install loop" in proof_pack_result.stdout
    assert "External Contributor Path" in proof_pack_result.stdout
    assert "cyberhuatuo challenge --username <external-contributor-github-username> --framework langchain" in proof_pack_result.stdout
    assert "Only real public Issue authors, public Pull Request authors, and local ledger actors" in proof_pack_result.stdout
    assert "cyberhuatuo market-ready --remote --strict-remote --username alice" in proof_pack_result.stdout
    assert "cyberhuatuo market-copy --username alice --framework langchain --release-tag v0.2.1 --target-contributors 5" in proof_pack_result.stdout
    assert "cyberhuatuo bounty --username alice --framework auto --top-n 8 --release-tag v0.2.1 --target-contributors 5" in proof_pack_result.stdout
    assert "cyberhuatuo first-invite --username alice --invitee <external-contributor-github-username>" in proof_pack_result.stdout

    market_copy_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "market-copy",
            "--username",
            "alice",
            "--framework",
            "langchain",
            "--release-tag",
            "v0.2.1",
            "--target-contributors",
            "5",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert market_copy_result.returncode == 0, market_copy_result.stdout + market_copy_result.stderr
    assert "Marketplace Submission Copy Pack" in market_copy_result.stdout
    assert "PyPI Listing Copy" in market_copy_result.stdout
    assert "Claude MCPB Listing Copy" in market_copy_result.stdout
    assert "Codex Plugin Listing Copy" in market_copy_result.stdout
    assert "GitHub Release Post" in market_copy_result.stdout
    assert "Prefilled Bounty Board Issue:" in market_copy_result.stdout
    assert "Community Challenge Pack" in market_copy_result.stdout
    assert "template=soul-ring-tournament.yml" in market_copy_result.stdout
    assert "template=soul-ring-mentor.yml" in market_copy_result.stdout
    assert "template=soul-ring-sect-recruit.yml" in market_copy_result.stdout
    assert "template=soul-ring-season.yml" in market_copy_result.stdout
    assert "Created Bounty Board Issue URL: <created Bounty Board Issue URL after submission>" in market_copy_result.stdout
    assert (
        "cyberhuatuo record-return --username alice --framework auto "
        '--surface "Bounty Board Issue" --source-url <created Bounty Board Issue URL after submission>'
    ) in market_copy_result.stdout
    assert "Git Tag Candidate Install Bridge" in market_copy_result.stdout
    assert (
        'python -m pip install --upgrade "cyberhuatuo @ '
        'git+https://github.com/JinNing6/CyberHuaTuo-Plugin.git@v0.2.1"'
    ) in market_copy_result.stdout
    assert "cyberhuatuo bounty --username alice --framework auto --top-n 8 --release-tag v0.2.1 --target-contributors 5" in market_copy_result.stdout
    assert "No public metrics are fetched" in market_copy_result.stdout

    first_invite_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "first-invite",
            "--username",
            "alice",
            "--invitee",
            "bob",
            "--framework",
            "langchain",
            "--release-tag",
            "v0.2.1",
            "--target-contributors",
            "5",
            "--source-url",
            "https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/123",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert first_invite_result.returncode == 0, first_invite_result.stdout + first_invite_result.stderr
    assert "First Contributor Invite Pack" in first_invite_result.stdout
    assert "Target invitee: `bob`" in first_invite_result.stdout
    assert "cyberhuatuo challenge --username bob --framework langchain" in first_invite_result.stdout
    assert "cyberhuatuo traction-proof --username alice --framework langchain --release-tag v0.2.1" in first_invite_result.stdout


def test_mcp_exposes_marketplace_readiness_gate_tool():
    source = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "def marketplace_readiness_gate(" in source
    assert "Community Challenge Pack" in source
    assert "Tournament Cup, Mentor Pact, Sect" in source
    assert "def current_install_command(" in source
    assert "format_current_install_command" in source
    assert "cyberhuatuo install-command" in source
    assert "Git Tag Candidate Install Bridge" in source
    assert "build_marketplace_readiness" in source
    assert "format_marketplace_readiness" in source
    assert "Launch Closure Checklist" in source
    assert "First Public Proof Kit" in source
    assert "Local Launch Asset Audit" in source
    assert "build_launch_asset_audit" in source
    assert "def first_public_proof_pack(" in source
    assert "format_first_public_proof_pack" in source
    assert "def first_contributor_invite(" in source
    assert "build_first_contributor_invite_pack" in source
    assert "format_first_contributor_invite_pack" in source
    assert "def marketplace_submission_copy(" in source
    assert "def record_marketplace_submission(" in source
    assert "def marketplace_submission_status(" in source
    assert "build_marketplace_submission_copy_pack" in source
    assert "format_marketplace_submission_copy_pack" in source
    assert "format_record_marketplace_submission" in source
    assert "format_marketplace_submission_status" in source
    assert "Marketplace Submission Copy Pack" in source
    assert "Marketplace Submission Ledger" in source
    assert "cyberhuatuo market-copy" in source
    assert "cyberhuatuo record-market" in source
    assert "cyberhuatuo market-status" in source
    assert "cyberhuatuo first-invite" in source
    assert "Prefilled Growth Flywheel Issue" in source
    assert "No-Network First Public Proof Pack" in source
    assert "cyberhuatuo proof-pack" in source
    assert "market-ready --remote --strict-remote" in source
    assert "PyPI Trusted Publisher" in source


def test_release_boundary_flags_research_only_archive_members():
    names = [
        "cyberhuatuo-0.1.0/cyberhuatuo/mcp_server.py",
        "cyberhuatuo-0.1.0/reports/generated.md",
        "cyberhuatuo-0.1.0/academic_benchmark_report.md",
    ]

    assert _find_forbidden(names) == names[1:]


def test_release_boundary_checks_current_version_archives_only(tmp_path, monkeypatch, capsys):
    dist = tmp_path / "dist"
    dist.mkdir()
    stale_wheel = dist / "cyberhuatuo-0.1.0-py3-none-any.whl"
    stale_wheel.write_bytes(b"stale")
    current_wheel = dist / "cyberhuatuo-0.2.1-py3-none-any.whl"
    current_wheel.write_bytes(b"current")
    current_sdist = dist / "cyberhuatuo-0.2.1.tar.gz"
    current_sdist.write_bytes(b"current")

    checked_archives: list[str] = []

    def fake_iter_archive_names(path: Path) -> list[str]:
        checked_archives.append(path.name)
        if path == stale_wheel:
            raise PermissionError("stale archive should not be opened")
        return []

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(release_boundary, "_read_project_version", lambda _root: "0.2.1")
    monkeypatch.setattr(release_boundary, "_iter_archive_names", fake_iter_archive_names)
    monkeypatch.setattr(release_boundary, "_find_release_contract_violations", lambda _path, _version: [])

    assert release_boundary.main() == 0

    output = capsys.readouterr().out
    assert checked_archives == [current_wheel.name, current_sdist.name]
    assert "cyberhuatuo-0.1.0" not in output
    assert "cyberhuatuo-0.2.1-py3-none-any.whl has no forbidden" in output
    assert "cyberhuatuo-0.2.1.tar.gz includes marketplace release contract assets" in output


def test_release_boundary_flags_missing_marketplace_wheel_contracts(tmp_path):
    wheel_path = tmp_path / "cyberhuatuo-0.2.1-py3-none-any.whl"
    with zipfile.ZipFile(wheel_path, "w") as archive:
        archive.writestr("cyberhuatuo/cli.py", "")
        archive.writestr(
            "cyberhuatuo-0.2.1.dist-info/entry_points.txt",
            "[console_scripts]\ncyberhuatuo = cyberhuatuo.cli:main\n",
        )
        archive.writestr("cyberhuatuo-0.2.1.dist-info/METADATA", "Name: cyberhuatuo\nVersion: 0.2.1\n")

    violations = release_boundary._find_release_contract_violations(wheel_path, "0.2.1")

    assert "missing wheel member: cyberhuatuo/marketplace.py" in violations
    assert "missing wheel member: cyberhuatuo/install.py" in violations
    assert "missing wheel member: cyberhuatuo/traction.py" in violations
    assert "missing console script entry point: cyberhuatuo-mcp = cyberhuatuo.mcp_server:main" in violations
    assert "missing wheel METADATA snippet: Local Launch Asset Audit" in violations
    assert "missing wheel METADATA snippet: cyberhuatuo proof-pack" in violations
    assert "missing wheel METADATA snippet: cyberhuatuo first-invite" in violations
    assert "missing wheel METADATA snippet: GitHub Web Release" in violations


def test_release_boundary_flags_missing_marketplace_sdist_contracts(tmp_path):
    sdist_path = tmp_path / "cyberhuatuo-0.2.1.tar.gz"

    def add_text(archive: tarfile.TarFile, name: str, text: str) -> None:
        payload = text.encode("utf-8")
        info = tarfile.TarInfo(f"cyberhuatuo-0.2.1/{name}")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))

    with tarfile.open(sdist_path, "w:gz") as archive:
        add_text(archive, "README.md", "CyberHuaTuo\n")
        add_text(archive, "pyproject.toml", "[project]\nname = 'cyberhuatuo'\nversion = '0.2.1'\n")
        add_text(archive, ".github/workflows/ci.yml", "run: python -m pytest -q\n")

    violations = release_boundary._find_release_contract_violations(sdist_path, "0.2.1")

    assert "missing sdist member: .github/ISSUE_TEMPLATE/soul-ring-growth-flywheel.yml" in violations
    assert "missing sdist member: .github/ISSUE_TEMPLATE/soul-ring-bounty-board.yml" in violations
    assert "missing sdist member: .github/ISSUE_TEMPLATE/soul-ring-prescription.yml" in violations
    assert "missing sdist member: .github/workflows/soul-ring-tournament.yml" in violations
    assert "missing sdist member: .github/workflows/soul-ring-mentor.yml" in violations
    assert "missing sdist member: .github/workflows/soul-ring-sect-recruit.yml" in violations
    assert "missing sdist member: .github/workflows/soul-ring-season.yml" in violations
    assert "missing sdist member: cyberhuatuo/install.py" in violations
    assert "missing sdist member: docs/MARKETPLACE_RELEASE.md" in violations
    assert "missing .github/workflows/ci.yml snippet: python -m cyberhuatuo launch-assets" in violations
    assert "missing README.md snippet: Local Launch Asset Audit" in violations


def test_cli_help_exposes_core_and_mcp_commands():
    result = subprocess.run(
        [sys.executable, "-m", "cyberhuatuo", "--help"],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "diagnose" in result.stdout
    assert "search" in result.stdout
    assert "cyberhuatuo-mcp" in result.stdout


def test_readmes_document_codex_and_claude_plugin_install_paths():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_cn = (ROOT / "README_CN.md").read_text(encoding="utf-8")
    readme_mcp = (ROOT / "README_MCP.md").read_text(encoding="utf-8")

    for text in (readme, readme_cn, readme_mcp):
        assert ".claude-plugin/plugin.json" in text
        assert ".claude-plugin/marketplace.json" in text
        assert "claude --plugin-dir ." in text
        assert "claude plugin marketplace add JinNing6/CyberHuaTuo-Plugin" in text
        assert ".codex-plugin/plugin.json" in text
        assert ".agents/plugins/marketplace.json" in text
        assert "codex plugin marketplace add JinNing6/CyberHuaTuo-Plugin" in text
        assert "GitHub Contents API" in text
        assert "GitHub Releases API" in text
        assert "release.published" in text
        assert "Launch Closure Checklist" in text
        assert "First Public Proof Kit" in text
        assert "No-Network First Public Proof Pack" in text
        assert "Local Launch Asset Audit" in text
        assert "marketplace_readiness_gate" in text
        assert "cyberhuatuo proof-pack" in text
        assert "GitHub Web Release" in text
        assert "GitHub Actions workflow page" in text
        assert "External Contributor Path" in text
        assert "contributor-counting rule" in text
        assert "cyberhuatuo launch-assets" in text
        assert "cyberhuatuo install-command" in text
        assert "current_install_command" in text
        assert "CyberHuaTuo Install Command" in text
        assert "PyPI JSON API" in text

    assert "docs/MARKETPLACE_RELEASE.md" in readme
    assert "PyPI Trusted Publishing" in readme
    assert "PyPI package readiness" in readme
    assert "Release Trigger" in readme
    assert "Protected Fallback Readiness" in readme
    assert "IssueOps forms/workflows" in readme
    assert "additional Trusted Publisher" in readme
    assert "Anthropic's official directory" in readme
    assert "Claude markets" in readme
    assert "Codex plugin directory" in readme
    assert "additional Trusted Publisher" in readme_cn
    assert "install-loop launch blocker" in readme_cn
    assert "Anthropic 官方插件目录" in readme_cn
    assert "remote IssueOps readiness" in readme_mcp
    assert "PyPI package readiness" in readme_mcp
    assert "GitHub Releases API" in readme_mcp
    assert "release.published" in readme_mcp
    assert "docs/MARKETPLACE_RELEASE.md" in readme_mcp


def test_source_distribution_includes_agent_plugin_manifests():
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    assert "recursive-include .codex-plugin *.json" in manifest
    assert "recursive-include .claude-plugin *.json" in manifest
    assert "recursive-include .agents/plugins *.json" in manifest
    assert "recursive-include .github/ISSUE_TEMPLATE *.yml" in manifest
    assert "recursive-include .github/workflows *.yml" in manifest
    assert "include .github/pull_request_template.md" in manifest
    assert "recursive-include docs *.md" in manifest
    assert "recursive-include claude-desktop *.json *.toml *.py *.md" in manifest
    assert "include claude-desktop/.mcpbignore" in manifest
    assert "include server.json" in manifest


def test_github_issue_form_guides_first_soul_ring_real_prescription():
    form_path = ROOT / ".github" / "ISSUE_TEMPLATE" / "soul-ring-prescription.yml"

    assert form_path.is_file()
    form = yaml.safe_load(form_path.read_text(encoding="utf-8"))

    assert form["name"] == "First Soul Ring Prescription"
    assert "real AI-agent fix" in form["description"]
    assert "soul-ring" in form["labels"]
    assert "first-soul-ring" in form["labels"]

    body = form["body"]
    assert isinstance(body, list)
    fields_by_id = {
        item["id"]: item
        for item in body
        if isinstance(item, dict) and item.get("type") != "markdown" and "id" in item
    }

    required_ids = {
        "github_username",
        "framework",
        "symptom",
        "root_cause",
        "prescription",
        "verification",
        "real_data_ack",
    }
    assert required_ids <= set(fields_by_id)
    for field_id in required_ids:
        assert fields_by_id[field_id]["validations"]["required"] is True

    framework_options = fields_by_id["framework"]["attributes"]["options"]
    assert "langchain" in framework_options
    assert "mcp" in framework_options
    assert "crewai" in framework_options

    markdown_blocks = [
        item["attributes"]["value"]
        for item in body
        if isinstance(item, dict) and item.get("type") == "markdown"
    ]
    assert any("cyberhuatuo ladder <your-github-username> --framework <framework>" in block for block in markdown_blocks)
    assert any("Soul Ring Breakthrough Ladder" in block for block in markdown_blocks)

    ack_options = fields_by_id["real_data_ack"]["attributes"]["options"]
    assert any("real error" in option["label"] for option in ack_options)
    assert any("not invented" in option["label"] for option in ack_options)


def test_github_issue_form_guides_soul_ring_tournament_event():
    form_path = ROOT / ".github" / "ISSUE_TEMPLATE" / "soul-ring-tournament.yml"

    assert form_path.is_file()
    form = yaml.safe_load(form_path.read_text(encoding="utf-8"))

    assert form["name"] == "Soul Ring Tournament Cup"
    assert "public soul-ring cup" in form["description"]
    assert "soul-ring" in form["labels"]
    assert "soul-ring-tournament" in form["labels"]

    body = form["body"]
    fields_by_id = {
        item["id"]: item
        for item in body
        if isinstance(item, dict) and item.get("type") != "markdown" and "id" in item
    }

    required_ids = {
        "event_name",
        "framework",
        "participants",
        "event_goal",
        "real_data_ack",
    }
    assert required_ids <= set(fields_by_id)
    for field_id in required_ids:
        assert fields_by_id[field_id]["validations"]["required"] is True

    framework_options = fields_by_id["framework"]["attributes"]["options"]
    assert "langchain" in framework_options
    assert "mcp" in framework_options
    assert "crewai" in framework_options

    markdown_blocks = [
        item["attributes"]["value"]
        for item in body
        if isinstance(item, dict) and item.get("type") == "markdown"
    ]
    assert any("cyberhuatuo tournament <participants...> --framework <framework>" in block for block in markdown_blocks)
    assert any("cyberhuatuo tournament-settle <participants...> --framework <framework>" in block for block in markdown_blocks)
    assert any("Soul Ring Tournament Settlement" in block for block in markdown_blocks)

    ack_options = fields_by_id["real_data_ack"]["attributes"]["options"]
    assert any("real GitHub usernames" in option["label"] for option in ack_options)
    assert any("not invented" in option["label"] for option in ack_options)


def test_github_issue_form_guides_soul_ring_sect_recruitment_event():
    form_path = ROOT / ".github" / "ISSUE_TEMPLATE" / "soul-ring-sect-recruit.yml"

    assert form_path.is_file()
    form = yaml.safe_load(form_path.read_text(encoding="utf-8"))

    assert form["name"] == "Soul Ring Sect Recruitment"
    assert "public soul-ring sect recruitment" in form["description"]
    assert "soul-ring" in form["labels"]
    assert "soul-ring-sect" in form["labels"]

    body = form["body"]
    fields_by_id = {
        item["id"]: item
        for item in body
        if isinstance(item, dict) and item.get("type") != "markdown" and "id" in item
    }

    required_ids = {
        "sect_name",
        "framework",
        "members",
        "invitee",
        "recruitment_goal",
        "real_data_ack",
    }
    assert required_ids <= set(fields_by_id)
    for field_id in required_ids:
        assert fields_by_id[field_id]["validations"]["required"] is True

    framework_options = fields_by_id["framework"]["attributes"]["options"]
    assert "langchain" in framework_options
    assert "mcp" in framework_options
    assert "crewai" in framework_options

    markdown_blocks = [
        item["attributes"]["value"]
        for item in body
        if isinstance(item, dict) and item.get("type") == "markdown"
    ]
    assert any(
        "cyberhuatuo sect-recruit <sect-name> <members...> --invitee <invitee> --framework <framework>"
        in block
        for block in markdown_blocks
    )
    assert any(
        "cyberhuatuo sect-hall <sect-name> <members...> --framework <framework>" in block
        for block in markdown_blocks
    )
    assert any(
        "cyberhuatuo sect-quest <sect-name> <members...> --framework <framework>" in block
        for block in markdown_blocks
    )
    assert any("Soul Ring Sect Recruitment Scroll" in block for block in markdown_blocks)

    ack_options = fields_by_id["real_data_ack"]["attributes"]["options"]
    assert any("real GitHub usernames" in option["label"] for option in ack_options)
    assert any("current real member snapshots" in option["label"] for option in ack_options)
    assert any("not invented" in option["label"] for option in ack_options)


def test_github_issue_form_guides_soul_ring_mentor_pact_event():
    form_path = ROOT / ".github" / "ISSUE_TEMPLATE" / "soul-ring-mentor.yml"

    assert form_path.is_file()
    form = yaml.safe_load(form_path.read_text(encoding="utf-8"))

    assert form["name"] == "Soul Ring Mentor Pact"
    assert "public soul-ring mentor pact" in form["description"]
    assert "soul-ring" in form["labels"]
    assert "soul-ring-mentor" in form["labels"]

    body = form["body"]
    fields_by_id = {
        item["id"]: item
        for item in body
        if isinstance(item, dict) and item.get("type") != "markdown" and "id" in item
    }

    required_ids = {
        "mentor_username",
        "apprentice_username",
        "framework",
        "mentorship_goal",
        "real_data_ack",
    }
    assert required_ids <= set(fields_by_id)
    for field_id in required_ids:
        assert fields_by_id[field_id]["validations"]["required"] is True

    framework_options = fields_by_id["framework"]["attributes"]["options"]
    assert "langchain" in framework_options
    assert "mcp" in framework_options
    assert "crewai" in framework_options

    markdown_blocks = [
        item["attributes"]["value"]
        for item in body
        if isinstance(item, dict) and item.get("type") == "markdown"
    ]
    assert any(
        "cyberhuatuo mentor <mentor-github> <apprentice-github> --framework <framework>"
        in block
        for block in markdown_blocks
    )
    assert any(
        "cyberhuatuo challenge --username <apprentice-github> --framework <framework>"
        in block
        for block in markdown_blocks
    )
    assert any(
        "cyberhuatuo ladder <apprentice-github> --framework <framework>" in block
        for block in markdown_blocks
    )
    assert any("Soul Ring Mentor Pact" in block for block in markdown_blocks)

    ack_options = fields_by_id["real_data_ack"]["attributes"]["options"]
    assert any("real GitHub usernames" in option["label"] for option in ack_options)
    assert any("current real snapshots" in option["label"] for option in ack_options)
    assert any("not invented" in option["label"] for option in ack_options)


def test_github_issue_form_guides_soul_ring_season_board_event():
    form_path = ROOT / ".github" / "ISSUE_TEMPLATE" / "soul-ring-season.yml"

    assert form_path.is_file()
    form = yaml.safe_load(form_path.read_text(encoding="utf-8"))

    assert form["name"] == "Soul Ring Season Board"
    assert "public soul-ring season board" in form["description"]
    assert "soul-ring" in form["labels"]
    assert "soul-ring-season" in form["labels"]

    body = form["body"]
    fields_by_id = {
        item["id"]: item
        for item in body
        if isinstance(item, dict) and item.get("type") != "markdown" and "id" in item
    }

    required_ids = {
        "season_name",
        "framework",
        "top_n",
        "season_goal",
        "real_data_ack",
    }
    assert required_ids <= set(fields_by_id)
    for field_id in required_ids:
        assert fields_by_id[field_id]["validations"]["required"] is True

    framework_options = fields_by_id["framework"]["attributes"]["options"]
    assert "langchain" in framework_options
    assert "mcp" in framework_options
    assert "crewai" in framework_options

    markdown_blocks = [
        item["attributes"]["value"]
        for item in body
        if isinstance(item, dict) and item.get("type") == "markdown"
    ]
    assert any(
        "cyberhuatuo season --framework <framework> --top-n <top-n>" in block
        for block in markdown_blocks
    )
    assert any(
        "cyberhuatuo arena <github-username> --top-n <top-n>" in block
        for block in markdown_blocks
    )
    assert any(
        "cyberhuatuo duel <leader-github> <chaser-github> --framework <framework>" in block
        for block in markdown_blocks
    )
    assert any("Soul Ring Season Board" in block for block in markdown_blocks)

    ack_options = fields_by_id["real_data_ack"]["attributes"]["options"]
    assert any("current real leaderboard snapshot" in option["label"] for option in ack_options)
    assert any("historical seasons are not invented" in option["label"] for option in ack_options)


def test_github_issue_form_guides_soul_ring_growth_flywheel_event():
    form_path = ROOT / ".github" / "ISSUE_TEMPLATE" / "soul-ring-growth-flywheel.yml"

    assert form_path.is_file()
    form = yaml.safe_load(form_path.read_text(encoding="utf-8"))

    assert form["name"] == "Soul Ring Growth Flywheel"
    assert "public growth flywheel" in form["description"]
    assert "soul-ring" in form["labels"]
    assert "soul-ring-growth" in form["labels"]

    body = form["body"]
    fields_by_id = {
        item["id"]: item
        for item in body
        if isinstance(item, dict) and item.get("type") != "markdown" and "id" in item
    }

    required_ids = {
        "github_username",
        "framework",
        "growth_surface",
        "real_signal",
        "bottleneck_guess",
        "campaign_hook",
        "real_data_ack",
    }
    assert required_ids <= set(fields_by_id)
    for field_id in required_ids:
        assert fields_by_id[field_id]["validations"]["required"] is True

    framework_options = fields_by_id["framework"]["attributes"]["options"]
    assert "langchain" in framework_options
    assert "mcp" in framework_options
    assert "crewai" in framework_options

    markdown_blocks = [
        item["attributes"]["value"]
        for item in body
        if isinstance(item, dict) and item.get("type") == "markdown"
    ]
    assert any(
        "cyberhuatuo flywheel --username <github-username> --framework <framework>" in block
        for block in markdown_blocks
    )
    assert any("campaign hook" in block.lower() for block in markdown_blocks)
    assert any("Soul Ring Growth Flywheel" in block for block in markdown_blocks)
    assert any("downloads, retention, and attribution are disclosed as missing" in block for block in markdown_blocks)

    ack_options = fields_by_id["real_data_ack"]["attributes"]["options"]
    assert any("real external signal" in option["label"] for option in ack_options)
    assert any("No downloads, retention, or attribution metrics are invented" in option["label"] for option in ack_options)


def test_github_issue_form_guides_soul_ring_bounty_board_event():
    form_path = ROOT / ".github" / "ISSUE_TEMPLATE" / "soul-ring-bounty-board.yml"

    assert form_path.is_file()
    form = yaml.safe_load(form_path.read_text(encoding="utf-8"))

    assert form["name"] == "Soul Ring Bounty Board"
    assert "claimable framework coverage gaps" in form["description"]
    assert "soul-ring" in form["labels"]
    assert "soul-ring-bounty" in form["labels"]

    body = form["body"]
    fields_by_id = {
        item["id"]: item
        for item in body
        if isinstance(item, dict) and item.get("type") != "markdown" and "id" in item
    }

    required_ids = {
        "github_username",
        "framework",
        "top_n",
        "release_tag",
        "target_contributors",
        "real_data_ack",
    }
    assert required_ids <= set(fields_by_id)
    for field_id in required_ids:
        assert fields_by_id[field_id]["validations"]["required"] is True

    framework_options = fields_by_id["framework"]["attributes"]["options"]
    assert "auto" in framework_options
    assert "autogen" in framework_options
    assert "dspy" in framework_options
    assert "mcp" in framework_options

    markdown_blocks = [
        item["attributes"]["value"]
        for item in body
        if isinstance(item, dict) and item.get("type") == "markdown"
    ]
    assert any(
        "cyberhuatuo bounty --username <github-username> --framework auto" in block
        for block in markdown_blocks
    )
    assert any("Soul Ring Bounty Board" in block for block in markdown_blocks)
    assert any("First Soul Ring Prescription Issue" in block for block in markdown_blocks)

    ack_options = fields_by_id["real_data_ack"]["attributes"]["options"]
    assert any("real local case coverage" in option["label"] for option in ack_options)
    assert any("No downloads, retention, repost counts, referrals, rewards, reviews, or fake contributors are invented" in option["label"] for option in ack_options)


@pytest.mark.parametrize(
    ("filename", "name", "label", "required_fields"),
    [
        (
            "guard-false-positive.yml",
            "Guard False Positive",
            "false-positive",
            {"guard_report", "why_safe", "minimal_reproduction", "safety_ack"},
        ),
        (
            "guard-false-negative.yml",
            "Guard False Negative",
            "false-negative",
            {"guard_report", "destructive_effect", "minimal_reproduction", "routing_ack"},
        ),
        (
            "guard-integration-gap.yml",
            "Guard Integration Gap",
            "integration-gap",
            {"agent_host", "failed_stage", "guard_report", "observed_integration", "environment", "routing_ack"},
        ),
    ],
)
def test_guard_issue_forms_collect_real_redacted_cases(filename, name, label, required_fields):
    form_path = ROOT / ".github" / "ISSUE_TEMPLATE" / filename

    assert form_path.is_file()
    form_text = form_path.read_text(encoding="utf-8")
    form = yaml.safe_load(form_text)

    assert form["name"] == name
    assert "agent-guard" in form["labels"]
    assert label in form["labels"]
    assert "triage" in form["labels"]
    fields = {item["id"]: item for item in form["body"] if item.get("id")}
    assert required_fields <= set(fields)
    for field_id in required_fields:
        assert fields[field_id]["validations"]["required"] is True
    assert "not a fabricated adoption case" in form_text
    assert "did not execute a dangerous command solely" in form_text
    assert "--report reports/guard-report.md" in form_text or filename == "guard-integration-gap.yml"

    if filename != "guard-false-positive.yml":
        assert "security/advisories/new" in form_text
        assert "private vulnerability reporting" in form_text.lower() or "GitHub Security Advisories" in form_text


def test_security_policy_routes_guard_bypasses_privately_and_misclassifications_publicly():
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    privacy = (ROOT / "docs" / "PRIVACY.md").read_text(encoding="utf-8")

    assert "security/advisories/new" in security
    assert "guard-false-positive.yml" in security
    assert "guard-false-negative.yml" in security
    assert "guard-integration-gap.yml" in security
    assert "Do not execute a destructive command solely" in security
    assert "performs no network request or automatic public upload" in security
    assert "Agent Action Guard Reports" in privacy
    assert "Only the redacted report is written" in privacy
    assert "security/advisories/new" in privacy


def test_github_issue_template_config_turns_new_issue_into_soul_ring_mission_hall():
    config_path = ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml"

    assert config_path.is_file()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    assert config["blank_issues_enabled"] is False
    contact_links = config["contact_links"]
    assert isinstance(contact_links, list)
    assert len(contact_links) == 11

    links_by_name = {link["name"]: link for link in contact_links}
    assert set(links_by_name) == {
        "Private Guard Security Report",
        "Agent Traceback Clinic",
        "Soul Ring Mission Hall",
        "Soul Ring Growth Flywheel",
        "Soul Ring Bounty Board",
        "Soul Ring Tournament Cup",
        "Soul Ring Sect Recruitment",
        "Soul Ring Mentor Pact",
        "Soul Ring Season Board",
        "Install CyberHuaTuo MCP",
        "Sect Arena / Team Challenge",
    }

    private_security = links_by_name["Private Guard Security Report"]
    assert private_security["url"] == (
        "https://github.com/JinNing6/CyberHuaTuo-Plugin/security/advisories/new"
    )
    assert "Privately report" in private_security["about"]

    mission = links_by_name["Soul Ring Mission Hall"]
    assert mission["url"] == (
        "https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/new"
        "?template=soul-ring-prescription.yml"
    )
    assert "First Soul Ring Prescription" in mission["about"]
    assert "cyberhuatuo challenge" in mission["about"]

    tournament = links_by_name["Soul Ring Tournament Cup"]
    assert tournament["url"] == (
        "https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/new"
        "?template=soul-ring-tournament.yml"
    )
    assert "tournament" in tournament["about"]
    assert "cyberhuatuo tournament-settle" in tournament["about"]

    sect_recruitment = links_by_name["Soul Ring Sect Recruitment"]
    assert sect_recruitment["url"] == (
        "https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/new"
        "?template=soul-ring-sect-recruit.yml"
    )
    assert "sect recruitment" in sect_recruitment["about"]
    assert "cyberhuatuo sect-recruit" in sect_recruitment["about"]

    mentor = links_by_name["Soul Ring Mentor Pact"]
    assert mentor["url"] == (
        "https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/new"
        "?template=soul-ring-mentor.yml"
    )
    assert "mentor pact" in mentor["about"]
    assert "cyberhuatuo mentor" in mentor["about"]

    season = links_by_name["Soul Ring Season Board"]
    assert season["url"] == (
        "https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/new"
        "?template=soul-ring-season.yml"
    )
    assert "season board" in season["about"]
    assert "cyberhuatuo season" in season["about"]

    flywheel = links_by_name["Soul Ring Growth Flywheel"]
    assert flywheel["url"] == (
        "https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/new"
        "?template=soul-ring-growth-flywheel.yml"
    )
    assert "growth flywheel" in flywheel["about"]
    assert "cyberhuatuo flywheel" in flywheel["about"]
    assert "missing metrics are disclosed" in flywheel["about"]

    bounty = links_by_name["Soul Ring Bounty Board"]
    assert bounty["url"] == (
        "https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/new"
        "?template=soul-ring-bounty-board.yml"
    )
    assert "coverage gaps" in bounty["about"]
    assert "cyberhuatuo bounty" in bounty["about"]

    mcp = links_by_name["Install CyberHuaTuo MCP"]
    assert mcp["url"] == "https://github.com/JinNing6/CyberHuaTuo-Plugin/blob/main/README_MCP.md"
    assert "Codex" in mcp["about"]
    assert "Claude" in mcp["about"]

    sect = links_by_name["Sect Arena / Team Challenge"]
    assert sect["url"] == "https://github.com/JinNing6/CyberHuaTuo-Plugin/blob/main/README.md"
    assert "sect-hall" in sect["about"]
    assert "sect-arena" in sect["about"]


def test_readmes_surface_github_first_soul_ring_issue_form():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_cn = (ROOT / "README_CN.md").read_text(encoding="utf-8")
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

    assert ".github/ISSUE_TEMPLATE/soul-ring-prescription.yml" in readme
    assert "First Soul Ring Prescription" in readme
    assert ".github/ISSUE_TEMPLATE/config.yml" in readme
    assert "Soul Ring Mission Hall" in readme
    assert "Soul Ring Breakthrough Ladder" in readme
    assert ".github/workflows/soul-ring-promote.yml" in readme
    assert "accepted-prescription" in readme
    assert ".github/ISSUE_TEMPLATE/soul-ring-prescription.yml" in readme_cn
    assert "First Soul Ring Prescription" in readme_cn
    assert ".github/ISSUE_TEMPLATE/config.yml" in readme_cn
    assert "Soul Ring Mission Hall" in readme_cn
    assert "Soul Ring Breakthrough Ladder" in readme_cn
    assert ".github/workflows/soul-ring-promote.yml" in readme_cn
    assert "accepted-prescription" in readme_cn
    assert ".github/workflows/soul-ring-promote.yml" in contributing
    assert "accepted-prescription" in contributing
    assert "soul-ring-promoted-pr" in contributing


def test_public_contribution_entrypoints_do_not_point_to_obsolete_prescription_template():
    public_files = [
        ROOT / "README.md",
        ROOT / "README_CN.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "cyberhuatuo" / "bot_matcher.py",
    ]

    for path in public_files:
        text = path.read_text(encoding="utf-8")
        assert "template=prescription.yml" not in text, path
        assert "tools/validate.py" not in text, path
        assert "template=soul-ring-prescription.yml" in text, path

    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert ".github/ISSUE_TEMPLATE/soul-ring-prescription.yml" in contributing
    assert "First Soul Ring Prescription" in contributing
    assert "python -m pytest" in contributing
    assert "python -m ruff check ." in contributing


def test_readmes_surface_github_soul_ring_tournament_issue_form():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_cn = (ROOT / "README_CN.md").read_text(encoding="utf-8")

    assert ".github/ISSUE_TEMPLATE/soul-ring-tournament.yml" in readme
    assert ".github/workflows/soul-ring-tournament.yml" in readme
    assert "Soul Ring Tournament Cup" in readme
    assert "Soul Ring Tournament Settlement" in readme
    assert "cyberhuatuo tournament-settle" in readme
    assert ".github/ISSUE_TEMPLATE/soul-ring-tournament.yml" in readme_cn
    assert ".github/workflows/soul-ring-tournament.yml" in readme_cn
    assert "Soul Ring Tournament Cup" in readme_cn
    assert "Soul Ring Tournament Settlement" in readme_cn
    assert "cyberhuatuo tournament-settle" in readme_cn


def test_readmes_surface_github_soul_ring_sect_recruitment_issue_form():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_cn = (ROOT / "README_CN.md").read_text(encoding="utf-8")

    assert ".github/ISSUE_TEMPLATE/soul-ring-sect-recruit.yml" in readme
    assert ".github/workflows/soul-ring-sect-recruit.yml" in readme
    assert "Soul Ring Sect Recruitment" in readme
    assert "Soul Ring Sect Recruitment Scroll" in readme
    assert "cyberhuatuo sect-recruit" in readme
    assert ".github/ISSUE_TEMPLATE/soul-ring-sect-recruit.yml" in readme_cn
    assert ".github/workflows/soul-ring-sect-recruit.yml" in readme_cn
    assert "Soul Ring Sect Recruitment" in readme_cn
    assert "Soul Ring Sect Recruitment Scroll" in readme_cn
    assert "cyberhuatuo sect-recruit" in readme_cn


def test_readmes_surface_github_soul_ring_mentor_pact_issue_form():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_cn = (ROOT / "README_CN.md").read_text(encoding="utf-8")

    assert ".github/ISSUE_TEMPLATE/soul-ring-mentor.yml" in readme
    assert ".github/workflows/soul-ring-mentor.yml" in readme
    assert "Soul Ring Mentor Pact" in readme
    assert "cyberhuatuo mentor" in readme
    assert ".github/ISSUE_TEMPLATE/soul-ring-mentor.yml" in readme_cn
    assert ".github/workflows/soul-ring-mentor.yml" in readme_cn
    assert "Soul Ring Mentor Pact" in readme_cn
    assert "cyberhuatuo mentor" in readme_cn


def test_readmes_surface_github_soul_ring_season_board_issue_form():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_cn = (ROOT / "README_CN.md").read_text(encoding="utf-8")

    assert ".github/ISSUE_TEMPLATE/soul-ring-season.yml" in readme
    assert ".github/workflows/soul-ring-season.yml" in readme
    assert "Soul Ring Season Board" in readme
    assert "cyberhuatuo season" in readme
    assert ".github/ISSUE_TEMPLATE/soul-ring-season.yml" in readme_cn
    assert ".github/workflows/soul-ring-season.yml" in readme_cn
    assert "Soul Ring Season Board" in readme_cn
    assert "cyberhuatuo season" in readme_cn


def test_readmes_surface_github_soul_ring_growth_flywheel_issue_form():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_cn = (ROOT / "README_CN.md").read_text(encoding="utf-8")
    readme_mcp = (ROOT / "README_MCP.md").read_text(encoding="utf-8")

    assert ".github/ISSUE_TEMPLATE/soul-ring-growth-flywheel.yml" in readme
    assert ".github/workflows/soul-ring-growth-flywheel.yml" in readme
    assert ".github/ISSUE_TEMPLATE/soul-ring-share-proof.yml" in readme
    assert ".github/workflows/soul-ring-share-proof.yml" in readme
    assert ".github/ISSUE_TEMPLATE/soul-ring-bounty-board.yml" in readme
    assert ".github/workflows/soul-ring-bounty-board.yml" in readme
    assert "Soul Ring Growth Flywheel" in readme
    assert "Soul Ring Share Proof" in readme
    assert "Soul Ring Bounty Board" in readme
    assert "cyberhuatuo flywheel" in readme
    assert "cyberhuatuo bounty" in readme
    assert "cyberhuatuo activation" in readme
    assert "cyberhuatuo record-return" in readme
    assert "cyberhuatuo record-share" in readme
    assert "cyberhuatuo share-report" in readme
    assert "cyberhuatuo share-leaderboard" in readme
    assert "No downloads, retention, or attribution metrics are invented" in readme
    assert ".github/ISSUE_TEMPLATE/soul-ring-growth-flywheel.yml" in readme_cn
    assert ".github/workflows/soul-ring-growth-flywheel.yml" in readme_cn
    assert ".github/ISSUE_TEMPLATE/soul-ring-share-proof.yml" in readme_cn
    assert ".github/workflows/soul-ring-share-proof.yml" in readme_cn
    assert ".github/ISSUE_TEMPLATE/soul-ring-bounty-board.yml" in readme_cn
    assert ".github/workflows/soul-ring-bounty-board.yml" in readme_cn
    assert "Soul Ring Growth Flywheel" in readme_cn
    assert "Soul Ring Share Proof" in readme_cn
    assert "Soul Ring Bounty Board" in readme_cn
    assert "cyberhuatuo flywheel" in readme_cn
    assert "cyberhuatuo bounty" in readme_cn
    assert "cyberhuatuo activation" in readme_cn
    assert "cyberhuatuo record-return" in readme_cn
    assert "cyberhuatuo record-share" in readme_cn
    assert "cyberhuatuo share-report" in readme_cn
    assert "cyberhuatuo share-leaderboard" in readme_cn
    assert "No downloads, retention, or attribution metrics are invented" in readme_cn
    assert "soul_ring_growth_flywheel" in readme_mcp
    assert "soul_ring_activation_funnel" in readme_mcp
    assert "soul_ring_share_attribution_report" in readme_mcp
    assert "record_soul_ring_external_return" in readme_mcp
    assert "record_soul_ring_share_attribution" in readme_mcp
    assert "soul_ring_bounty_board" in readme_mcp


def test_readmes_surface_github_soul_ring_launch_campaign_issue_form():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_cn = (ROOT / "README_CN.md").read_text(encoding="utf-8")
    readme_mcp = (ROOT / "README_MCP.md").read_text(encoding="utf-8")

    assert ".github/ISSUE_TEMPLATE/soul-ring-launch-campaign.yml" in readme
    assert ".github/workflows/soul-ring-launch-campaign.yml" in readme
    assert "Soul Ring Launch Campaign" in readme
    assert "cyberhuatuo launch-campaign" in readme
    assert "Campaign Recap And Next Sprint" in readme
    assert "observed real contributors" in readme
    assert "next `growth_campaign` command" in readme
    assert "traction-proof --record-snapshot" in readme
    assert ".github/ISSUE_TEMPLATE/soul-ring-launch-campaign.yml" in readme_cn
    assert ".github/workflows/soul-ring-launch-campaign.yml" in readme_cn
    assert "Soul Ring Launch Campaign" in readme_cn
    assert "cyberhuatuo launch-campaign" in readme_cn
    assert "Campaign Recap And Next Sprint" in readme_cn
    assert "next growth_campaign command" in readme_cn
    assert "soul_ring_launch_campaign" in readme_mcp
    assert "Campaign Recap And Next Sprint" in readme_mcp
    assert "traction-proof --record-snapshot" in readme_mcp


def test_readmes_surface_soul_ring_traction_proof_public_api_contract():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_cn = (ROOT / "README_CN.md").read_text(encoding="utf-8")
    readme_mcp = (ROOT / "README_MCP.md").read_text(encoding="utf-8")
    release_plan = (ROOT / "docs" / "MARKETPLACE_RELEASE.md").read_text(encoding="utf-8")

    for text in (readme, readme_cn, release_plan):
        assert "cyberhuatuo traction-proof" in text
        assert "GitHub REST API" in text
        assert "GitHub Pull Requests API" in text
        assert "PyPI JSON API" in text
        assert "PR" in text
        assert "stars, forks, watchers" in text
        assert "downloads are not used" in text
        assert "Target contributor progress" in text
        assert "No-Network First Public Proof Pack" in text
        assert "fetch failures" in text
        assert "--record-snapshot" in text
        assert "append-only" in text

    assert "soul_ring_traction_proof" in readme_mcp
    assert "record_soul_ring_traction_snapshot" in readme_mcp
    assert "GitHub REST API" in readme_mcp
    assert "GitHub Pull Requests API" in readme_mcp
    assert "PyPI JSON API" in readme_mcp
    assert "PR authors" in readme_mcp
    assert "not contributor progress" in readme_mcp
    assert "No-Network First Public Proof Pack" in readme_mcp
    assert "fetch failures" in readme_mcp
    assert "append-only" in readme_mcp


def test_readmes_surface_marketplace_submission_ledger():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_mcp = (ROOT / "README_MCP.md").read_text(encoding="utf-8")
    release_plan = (ROOT / "docs" / "MARKETPLACE_RELEASE.md").read_text(encoding="utf-8")

    for text in (readme, readme_mcp, release_plan):
        assert "Marketplace Submission Ledger" in text
        assert "Submission Portals And Evidence URLs" in text
        assert "Claude plugin submit (Console): https://platform.claude.com/plugins/submit" in text
        assert "Codex plugin evidence: `codex plugin marketplace add JinNing6/CyberHuaTuo-Plugin`" in text
        assert "cyberhuatuo record-market" in text
        assert "cyberhuatuo market-status" in text
        assert "reviewable public URL" in text
        assert "does not invent downloads" in text

    assert "record_marketplace_submission" in readme_mcp
    assert "marketplace_submission_status" in readme_mcp
    assert "record-market" in release_plan
    assert "market-status" in release_plan


def test_readmes_surface_first_contributor_invite_pack():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_cn = (ROOT / "README_CN.md").read_text(encoding="utf-8")
    readme_mcp = (ROOT / "README_MCP.md").read_text(encoding="utf-8")
    release_plan = (ROOT / "docs" / "MARKETPLACE_RELEASE.md").read_text(encoding="utf-8")

    for text in (readme, readme_cn, release_plan):
        assert "cyberhuatuo first-invite" in text
        assert "First Contributor Invite Pack" in text
        assert "first external contributor" in text
        assert "record-session" in text
        assert "does not invent downloads" in text
        assert "Next External Contributor Invite" in text
        assert "first_contributor_invite" in text
        assert "first_public_proof_pack" in text

    assert "first_contributor_invite" in readme_mcp
    assert "First Contributor Invite Pack" in readme_mcp
    assert "cyberhuatuo first-invite" in readme_mcp
    assert "target one external contributor" in readme_mcp
    assert "Next External Contributor Invite" in readme_mcp
    assert "first_public_proof_pack" in readme_mcp


def test_github_issue_form_guides_soul_ring_launch_campaign_event():
    form_path = ROOT / ".github" / "ISSUE_TEMPLATE" / "soul-ring-launch-campaign.yml"

    assert form_path.is_file()
    form = yaml.safe_load(form_path.read_text(encoding="utf-8"))

    assert form["name"] == "Soul Ring Launch Campaign"
    assert "target first-ring contributors" in form["description"]
    assert "soul-ring" in form["labels"]
    assert "soul-ring-launch-campaign" in form["labels"]

    body = form["body"]
    fields_by_id = {
        item["id"]: item
        for item in body
        if item.get("type") not in {"markdown", "checkboxes"}
    }
    assert fields_by_id["github_username"]["validations"]["required"] is True
    assert fields_by_id["framework"]["validations"]["required"] is True
    assert fields_by_id["launch_surface"]["validations"]["required"] is True
    assert fields_by_id["target_contributors"]["validations"]["required"] is True
    assert fields_by_id["real_signal"]["validations"]["required"] is True
    assert fields_by_id["campaign_hook"]["validations"]["required"] is True

    markdown_blocks = [
        item["attributes"]["value"]
        for item in body
        if item.get("type") == "markdown"
    ]
    assert any("cyberhuatuo launch-campaign" in block for block in markdown_blocks)
    assert any("cyberhuatuo record-return" in block for block in markdown_blocks)
    assert any("cyberhuatuo share-leaderboard" in block for block in markdown_blocks)
    assert any("No downloads, retention, repost counts, referrals, rewards, or Spirit Power are invented" in block for block in markdown_blocks)


def test_github_issue_form_guides_soul_ring_share_proof_event():
    form_path = ROOT / ".github" / "ISSUE_TEMPLATE" / "soul-ring-share-proof.yml"

    assert form_path.is_file()
    form = yaml.safe_load(form_path.read_text(encoding="utf-8"))

    assert form["name"] == "Soul Ring Share Proof"
    assert "public soul-ring share URL" in form["description"]
    assert "soul-ring" in form["labels"]
    assert "soul-ring-share-proof" in form["labels"]

    body = form["body"]
    fields_by_id = {
        item["id"]: item
        for item in body
        if isinstance(item, dict) and item.get("type") != "markdown" and "id" in item
    }

    required_ids = {
        "github_username",
        "framework",
        "share_url",
        "proof_context",
        "real_data_ack",
    }
    assert required_ids <= set(fields_by_id)
    for field_id in required_ids:
        assert fields_by_id[field_id]["validations"]["required"] is True

    assert "source_url" in fields_by_id
    assert fields_by_id["source_url"]["validations"]["required"] is False
    framework_options = fields_by_id["framework"]["attributes"]["options"]
    assert "langchain" in framework_options
    assert "mcp" in framework_options
    assert "crewai" in framework_options

    markdown_blocks = [
        item["attributes"]["value"]
        for item in body
        if isinstance(item, dict) and item.get("type") == "markdown"
    ]
    assert any("cyberhuatuo record-share" in block for block in markdown_blocks)
    assert any("cyberhuatuo share-report" in block for block in markdown_blocks)
    assert any("cyberhuatuo share-leaderboard" in block for block in markdown_blocks)

    ack_options = fields_by_id["real_data_ack"]["attributes"]["options"]
    assert any("reviewable public URL" in option["label"] for option in ack_options)
    assert any("not invented" in option["label"] for option in ack_options)


def test_readmes_surface_soul_ring_pr_settlement_template():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_cn = (ROOT / "README_CN.md").read_text(encoding="utf-8")

    assert ".github/pull_request_template.md" in readme
    assert ".github/workflows/soul-ring-pr.yml" in readme
    assert "Soul Ring PR Settlement" in readme
    assert "cyberhuatuo ladder" in readme
    assert ".github/pull_request_template.md" in readme_cn
    assert ".github/workflows/soul-ring-pr.yml" in readme_cn
    assert "Soul Ring PR Settlement" in readme_cn
    assert "cyberhuatuo ladder" in readme_cn


def test_readmes_surface_soul_ring_evidence_gate_route():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_cn = (ROOT / "README_CN.md").read_text(encoding="utf-8")
    readme_mcp = (ROOT / "README_MCP.md").read_text(encoding="utf-8")
    release_plan = (ROOT / "docs" / "MARKETPLACE_RELEASE.md").read_text(encoding="utf-8")

    for text in (readme, readme_cn, readme_mcp, release_plan):
        assert "cyberhuatuo evidence" in text
        assert "Soul Ring Evidence Card" in text
        assert "reviewable public evidence" in text
        assert "append-only" in text
        assert "not invented" in text


def test_github_workflow_comments_on_first_soul_ring_issue_with_next_actions():
    workflow_path = ROOT / ".github" / "workflows" / "soul-ring-issue.yml"

    assert workflow_path.is_file()
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

    assert workflow["name"] == "Soul Ring Issue Onboarding"
    assert workflow["on"]["issues"]["types"] == ["opened"]
    assert workflow["permissions"] == {"issues": "write", "contents": "read"}

    jobs = workflow["jobs"]
    assert set(jobs) == {"first-soul-ring-comment"}
    job = jobs["first-soul-ring-comment"]
    assert "contains(github.event.issue.labels.*.name, 'first-soul-ring')" in job["if"]
    assert "startsWith(github.event.issue.title, '[Soul Ring Prescription]')" in job["if"]
    assert "github.event.issue.pull_request == null" in job["if"]

    steps = job["steps"]
    assert len(steps) == 1
    step = steps[0]
    assert step["uses"] == "actions/github-script@v8"
    assert "run" not in step

    script = step["with"]["script"]
    assert "github.rest.issues.createComment" in script
    assert "const issueUrl = issue.html_url" in script
    assert "Launch Closure Checklist" in script
    assert "cyberhuatuo proof-pack --username" in script
    assert "cyberhuatuo market-copy --username" in script
    assert "cyberhuatuo market-ready --remote --strict-remote --username" in script
    assert "cyberhuatuo record-return --username" in script
    assert '--surface "First Soul Ring Issue" --source-url ${issueUrl}' in script
    assert "cyberhuatuo challenge --username" in script
    assert "cyberhuatuo ladder" in script
    assert "cyberhuatuo upload --title" in script
    assert "cyberhuatuo ranking" in script
    assert "cyberhuatuo card" in script
    assert "cyberhuatuo campaign" in script
    assert "Soul Ring Breakthrough Ladder" in script
    assert "next gate" in script
    assert "real-data pledge" in script
    assert "not invented" in script
    assert "actions/checkout" not in workflow_path.read_text(encoding="utf-8")


def test_github_workflow_promotes_accepted_first_soul_ring_issue_to_case_pr():
    workflow_path = ROOT / ".github" / "workflows" / "soul-ring-promote.yml"

    assert workflow_path.is_file()
    workflow_text = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)

    assert workflow["name"] == "Soul Ring Prescription Promotion"
    assert workflow["on"]["issues"]["types"] == ["labeled"]
    assert workflow["permissions"] == {
        "contents": "write",
        "issues": "write",
        "pull-requests": "write",
    }

    jobs = workflow["jobs"]
    assert set(jobs) == {"promote-first-soul-ring-prescription"}
    job = jobs["promote-first-soul-ring-prescription"]
    assert "github.event.issue.pull_request == null" in job["if"]
    assert "contains(github.event.issue.labels.*.name, 'first-soul-ring')" in job["if"]
    assert "contains(github.event.issue.labels.*.name, 'accepted-prescription')" in job["if"]
    assert "!contains(github.event.issue.labels.*.name, 'soul-ring-promoted-pr')" in job["if"]

    steps = job["steps"]
    assert len(steps) == 1
    step = steps[0]
    assert step["uses"] == "actions/github-script@v8"
    assert "run" not in step

    script = step["with"]["script"]
    assert "parseIssueForm" in script
    assert "Framework or tool" in script
    assert "Real symptom and reproduction" in script
    assert "Root cause" in script
    assert "Prescription / fix" in script
    assert "Verification evidence" in script
    assert "cases/${framework}/community/${caseId}.md" in script
    assert "github.rest.git.createRef" in script
    assert "github.rest.repos.createOrUpdateFileContents" in script
    assert "github.rest.pulls.create" in script
    assert "github.rest.issues.createComment" in script
    assert "soul-ring-promoted-pr" in script
    assert "cyberhuatuo ladder" in script
    assert "cyberhuatuo campaign" in script
    assert "accepted-prescription" in script
    assert "actions/checkout" not in workflow_text
    assert "\nrun:" not in workflow_text


def test_github_workflow_comments_on_soul_ring_tournament_issue_with_public_event_commands():
    workflow_path = ROOT / ".github" / "workflows" / "soul-ring-tournament.yml"

    assert workflow_path.is_file()
    workflow_text = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)

    assert workflow["name"] == "Soul Ring Tournament IssueOps"
    assert workflow["on"]["issues"]["types"] == ["opened"]
    assert workflow["permissions"] == {"issues": "write", "contents": "read"}

    jobs = workflow["jobs"]
    assert set(jobs) == {"soul-ring-tournament-comment"}
    job = jobs["soul-ring-tournament-comment"]
    assert "contains(github.event.issue.labels.*.name, 'soul-ring-tournament')" in job["if"]
    assert "startsWith(github.event.issue.title, '[Soul Ring Tournament]')" in job["if"]
    assert "github.event.issue.pull_request == null" in job["if"]

    steps = job["steps"]
    assert len(steps) == 1
    step = steps[0]
    assert step["uses"] == "actions/github-script@v8"
    assert "run" not in step

    script = step["with"]["script"]
    assert "github.rest.issues.createComment" in script
    assert "const issue = context.payload.issue" in script
    assert "const issueUrl = issue.html_url" in script
    assert "replaceAll(\"`\", \"'\")" in script
    assert "Soul Ring Tournament Cup" in script
    assert "Launch Closure Checklist" in script
    assert "cyberhuatuo proof-pack --username" in script
    assert "cyberhuatuo market-copy --username" in script
    assert "cyberhuatuo market-ready --remote --strict-remote --username" in script
    assert "cyberhuatuo record-return --username" in script
    assert '--surface "Tournament Issue" --source-url ${issueUrl}' in script
    assert "cyberhuatuo tournament" in script
    assert "cyberhuatuo tournament-settle" in script
    assert "cyberhuatuo duel" in script
    assert "cyberhuatuo challenge --username" in script
    assert "cyberhuatuo campaign" in script
    assert "Soul Ring Tournament Settlement" in script
    assert "current real prescription counts" in script
    assert "not invented" in script
    assert "actions/checkout" not in workflow_text
    assert "\nrun:" not in workflow_text


def test_github_workflow_comments_on_soul_ring_sect_recruitment_issue_with_public_commands():
    workflow_path = ROOT / ".github" / "workflows" / "soul-ring-sect-recruit.yml"

    assert workflow_path.is_file()
    workflow_text = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)

    assert workflow["name"] == "Soul Ring Sect Recruitment IssueOps"
    assert workflow["on"]["issues"]["types"] == ["opened"]
    assert workflow["permissions"] == {"issues": "write", "contents": "read"}

    jobs = workflow["jobs"]
    assert set(jobs) == {"soul-ring-sect-recruit-comment"}
    job = jobs["soul-ring-sect-recruit-comment"]
    assert "contains(github.event.issue.labels.*.name, 'soul-ring-sect')" in job["if"]
    assert "startsWith(github.event.issue.title, '[Soul Ring Sect]')" in job["if"]
    assert "github.event.issue.pull_request == null" in job["if"]

    steps = job["steps"]
    assert len(steps) == 1
    step = steps[0]
    assert step["uses"] == "actions/github-script@v8"
    assert "run" not in step

    script = step["with"]["script"]
    assert "github.rest.issues.createComment" in script
    assert "const issue = context.payload.issue" in script
    assert "const issueUrl = issue.html_url" in script
    assert "replaceAll(\"`\", \"'\")" in script
    assert "Soul Ring Sect Recruitment" in script
    assert "Launch Closure Checklist" in script
    assert "cyberhuatuo proof-pack --username" in script
    assert "cyberhuatuo market-copy --username" in script
    assert "cyberhuatuo market-ready --remote --strict-remote --username" in script
    assert "cyberhuatuo record-return --username" in script
    assert '--surface "Sect Recruitment Issue" --source-url ${issueUrl}' in script
    assert "cyberhuatuo sect-recruit" in script
    assert "cyberhuatuo sect-hall" in script
    assert "cyberhuatuo sect-quest" in script
    assert "cyberhuatuo sect-duel" in script
    assert "cyberhuatuo challenge --username" in script
    assert "cyberhuatuo campaign" in script
    assert "Soul Ring Sect Recruitment Scroll" in script
    assert "current real member snapshots" in script
    assert "not invented" in script
    assert "actions/checkout" not in workflow_text
    assert "\nrun:" not in workflow_text


def test_github_workflow_comments_on_soul_ring_mentor_pact_issue_with_public_commands():
    workflow_path = ROOT / ".github" / "workflows" / "soul-ring-mentor.yml"

    assert workflow_path.is_file()
    workflow_text = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)

    assert workflow["name"] == "Soul Ring Mentor Pact IssueOps"
    assert workflow["on"]["issues"]["types"] == ["opened"]
    assert workflow["permissions"] == {"issues": "write", "contents": "read"}

    jobs = workflow["jobs"]
    assert set(jobs) == {"soul-ring-mentor-comment"}
    job = jobs["soul-ring-mentor-comment"]
    assert "contains(github.event.issue.labels.*.name, 'soul-ring-mentor')" in job["if"]
    assert "startsWith(github.event.issue.title, '[Soul Ring Mentor]')" in job["if"]
    assert "github.event.issue.pull_request == null" in job["if"]

    steps = job["steps"]
    assert len(steps) == 1
    step = steps[0]
    assert step["uses"] == "actions/github-script@v8"
    assert "run" not in step

    script = step["with"]["script"]
    assert "github.rest.issues.createComment" in script
    assert "const issue = context.payload.issue" in script
    assert "const issueUrl = issue.html_url" in script
    assert "replaceAll(\"`\", \"'\")" in script
    assert "Soul Ring Mentor Pact" in script
    assert "Launch Closure Checklist" in script
    assert "cyberhuatuo proof-pack --username" in script
    assert "cyberhuatuo market-copy --username" in script
    assert "cyberhuatuo market-ready --remote --strict-remote --username" in script
    assert "cyberhuatuo record-return --username" in script
    assert '--surface "Mentor Pact Issue" --source-url ${issueUrl}' in script
    assert "cyberhuatuo mentor" in script
    assert "cyberhuatuo challenge --username" in script
    assert "cyberhuatuo quest" in script
    assert "cyberhuatuo ladder" in script
    assert "cyberhuatuo duel" in script
    assert "cyberhuatuo campaign" in script
    assert "current real snapshots" in script
    assert "not invented" in script
    assert "actions/checkout" not in workflow_text
    assert "\nrun:" not in workflow_text


def test_github_workflow_comments_on_soul_ring_season_board_issue_with_public_commands():
    workflow_path = ROOT / ".github" / "workflows" / "soul-ring-season.yml"

    assert workflow_path.is_file()
    workflow_text = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)

    assert workflow["name"] == "Soul Ring Season IssueOps"
    assert workflow["on"]["issues"]["types"] == ["opened"]
    assert workflow["permissions"] == {"issues": "write", "contents": "read"}

    jobs = workflow["jobs"]
    assert set(jobs) == {"soul-ring-season-comment"}
    job = jobs["soul-ring-season-comment"]
    assert "contains(github.event.issue.labels.*.name, 'soul-ring-season')" in job["if"]
    assert "startsWith(github.event.issue.title, '[Soul Ring Season]')" in job["if"]
    assert "github.event.issue.pull_request == null" in job["if"]

    steps = job["steps"]
    assert len(steps) == 1
    step = steps[0]
    assert step["uses"] == "actions/github-script@v8"
    assert "run" not in step

    script = step["with"]["script"]
    assert "github.rest.issues.createComment" in script
    assert "const issue = context.payload.issue" in script
    assert "const issueUrl = issue.html_url" in script
    assert "replaceAll(\"`\", \"'\")" in script
    assert "Soul Ring Season Board" in script
    assert "Launch Closure Checklist" in script
    assert "cyberhuatuo proof-pack --username" in script
    assert "cyberhuatuo market-copy --username" in script
    assert "cyberhuatuo market-ready --remote --strict-remote --username" in script
    assert "cyberhuatuo record-return --username" in script
    assert '--surface "Season Board Issue" --source-url ${issueUrl}' in script
    assert "cyberhuatuo season" in script
    assert "cyberhuatuo arena" in script
    assert "cyberhuatuo duel" in script
    assert "cyberhuatuo challenge --username" in script
    assert "cyberhuatuo quest" in script
    assert "cyberhuatuo campaign" in script
    assert "current real leaderboard snapshot" in script
    assert "historical seasons are not invented" in script
    assert "actions/checkout" not in workflow_text
    assert "\nrun:" not in workflow_text


def test_github_workflow_comments_on_soul_ring_growth_flywheel_issue_with_public_commands():
    workflow_path = ROOT / ".github" / "workflows" / "soul-ring-growth-flywheel.yml"

    assert workflow_path.is_file()
    workflow_text = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)

    assert workflow["name"] == "Soul Ring Growth Flywheel IssueOps"
    assert workflow["on"]["issues"]["types"] == ["opened"]
    assert workflow["permissions"] == {"issues": "write", "contents": "read"}

    jobs = workflow["jobs"]
    assert set(jobs) == {"soul-ring-growth-flywheel-comment"}
    job = jobs["soul-ring-growth-flywheel-comment"]
    assert "contains(github.event.issue.labels.*.name, 'soul-ring-growth')" in job["if"]
    assert "startsWith(github.event.issue.title, '[Soul Ring Growth]')" in job["if"]
    assert "github.event.issue.pull_request == null" in job["if"]

    steps = job["steps"]
    assert len(steps) == 1
    step = steps[0]
    assert step["uses"] == "actions/github-script@v8"
    assert "run" not in step

    script = step["with"]["script"]
    assert "github.rest.issues.createComment" in script
    assert "const issue = context.payload.issue" in script
    assert "replaceAll(\"`\", \"'\")" in script
    assert "Soul Ring Growth Flywheel" in script
    assert "cyberhuatuo record-return --username" in script
    assert "cyberhuatuo market-ready --remote --strict-remote --username" in script
    assert "cyberhuatuo proof-pack --username" in script
    assert "cyberhuatuo market-copy --username" in script
    assert "Launch Closure Checklist" in script
    assert "cyberhuatuo activation --username" in script
    assert "cyberhuatuo flywheel --username" in script
    assert "cyberhuatuo leaderboard --top-n" in script
    assert "cyberhuatuo bounty --username" in script
    assert "cyberhuatuo quest" in script
    assert "cyberhuatuo season --framework" in script
    assert "cyberhuatuo sect-arena --sect" in script
    assert "cyberhuatuo record-share --username" in script
    assert "current real contribution records" in script
    assert "activation ledger" in script.lower()
    assert "No downloads, retention, or attribution metrics are invented" in script
    assert "actions/checkout" not in workflow_text
    assert "\nrun:" not in workflow_text
    assert "cyberhuatuo sect-war" not in workflow_text


def test_github_workflow_comments_on_soul_ring_bounty_board_issue_with_sanitized_numbers():
    workflow_path = ROOT / ".github" / "workflows" / "soul-ring-bounty-board.yml"

    assert workflow_path.is_file()
    workflow_text = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)

    assert workflow["name"] == "Soul Ring Bounty Board IssueOps"
    assert workflow["on"]["issues"]["types"] == ["opened"]
    assert workflow["permissions"] == {"issues": "write", "contents": "read"}

    jobs = workflow["jobs"]
    assert set(jobs) == {"soul-ring-bounty-board-comment"}
    job = jobs["soul-ring-bounty-board-comment"]
    assert "contains(github.event.issue.labels.*.name, 'soul-ring-bounty')" in job["if"]
    assert "startsWith(github.event.issue.title, '[Soul Ring Bounty]')" in job["if"]
    assert "github.event.issue.pull_request == null" in job["if"]

    steps = job["steps"]
    assert len(steps) == 1
    step = steps[0]
    assert step["uses"] == "actions/github-script@v8"
    assert "run" not in step

    script = step["with"]["script"]
    assert "github.rest.issues.createComment" in script
    assert "const issue = context.payload.issue" in script
    assert "const issueUrl = issue.html_url" in script
    assert "issue.body || \"\"" in script
    assert "Number.parseInt" in script
    assert "Math.min(parsedTopN, 50)" in script
    assert "Math.min(parsedTarget, 100)" in script
    assert "--top-n ${topN}" in script
    assert "--target-contributors ${target}" in script
    assert "--top-n ${issue.body}" not in script
    assert "--target-contributors ${issue.body}" not in script
    assert "Soul Ring Bounty Board" in script
    assert "Launch Closure Checklist" in script
    assert "cyberhuatuo market-ready --remote --strict-remote --username" in script
    assert "cyberhuatuo record-return --username" in script
    assert '--surface "Bounty Board Issue" --source-url ${issueUrl}' in script
    assert "cyberhuatuo activation --username" in script
    assert "cyberhuatuo flywheel --username" in script
    assert "cyberhuatuo bounty --username" in script
    assert "cyberhuatuo challenge --username" in script
    assert "cyberhuatuo first-invite --username" in script
    assert "cyberhuatuo proof-pack --username" in script
    assert "cyberhuatuo market-copy --username" in script
    assert "cyberhuatuo traction-proof --username" in script
    assert script.index("cyberhuatuo record-return --username") < script.index("cyberhuatuo bounty --username")
    assert script.index("cyberhuatuo record-return --username") < script.index("cyberhuatuo challenge --username")
    assert "First Soul Ring Prescription Issue" in script
    assert "coverage gap" in script.lower()
    assert "No downloads, retention, repost counts, referrals, rewards, reviews, or fake contributors are invented" in script
    assert "actions/checkout" not in workflow_text
    assert "\nrun:" not in workflow_text


def test_github_workflow_comments_on_soul_ring_launch_campaign_issue_with_sanitized_target():
    workflow_path = ROOT / ".github" / "workflows" / "soul-ring-launch-campaign.yml"

    assert workflow_path.is_file()
    workflow_text = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)

    assert workflow["name"] == "Soul Ring Launch Campaign IssueOps"
    assert workflow["on"]["issues"]["types"] == ["opened"]
    assert workflow["permissions"] == {"issues": "write", "contents": "read"}

    jobs = workflow["jobs"]
    assert set(jobs) == {"soul-ring-launch-campaign-comment"}
    job = jobs["soul-ring-launch-campaign-comment"]
    assert "contains(github.event.issue.labels.*.name, 'soul-ring-launch-campaign')" in job["if"]
    assert "startsWith(github.event.issue.title, '[Soul Ring Launch Campaign]')" in job["if"]
    assert "github.event.issue.pull_request == null" in job["if"]

    steps = job["steps"]
    assert len(steps) == 1
    step = steps[0]
    assert step["uses"] == "actions/github-script@v8"
    assert "run" not in step

    script = step["with"]["script"]
    assert "github.rest.issues.createComment" in script
    assert "const issue = context.payload.issue" in script
    assert "issue.body || \"\"" in script
    assert "Number.parseInt" in script
    assert "Math.min(parsedTarget, 100)" in script
    assert "--target-contributors ${target}" in script
    assert "--target-contributors ${issue.body}" not in script
    assert "cyberhuatuo launch-campaign --username" in script
    assert "cyberhuatuo market-ready --remote --strict-remote --username" in script
    assert "cyberhuatuo proof-pack --username" in script
    assert "cyberhuatuo market-copy --username" in script
    assert "Launch Closure Checklist" in script
    assert "cyberhuatuo record-return --username" in script
    assert "cyberhuatuo activation --username" in script
    assert "cyberhuatuo flywheel --username" in script
    assert "cyberhuatuo record-share --username" in script
    assert "cyberhuatuo share-leaderboard --framework" in script
    assert "No downloads, retention, repost counts, referrals, rewards, or Spirit Power are invented" in script
    assert "actions/checkout" not in workflow_text
    assert "\nrun:" not in workflow_text


def test_github_workflow_comments_on_soul_ring_share_proof_issue_with_public_commands():
    workflow_path = ROOT / ".github" / "workflows" / "soul-ring-share-proof.yml"

    assert workflow_path.is_file()
    workflow_text = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)

    assert workflow["name"] == "Soul Ring Share Proof IssueOps"
    assert workflow["on"]["issues"]["types"] == ["opened"]
    assert workflow["permissions"] == {"issues": "write", "contents": "read"}

    jobs = workflow["jobs"]
    assert set(jobs) == {"soul-ring-share-proof-comment"}
    job = jobs["soul-ring-share-proof-comment"]
    assert "contains(github.event.issue.labels.*.name, 'soul-ring-share-proof')" in job["if"]
    assert "startsWith(github.event.issue.title, '[Soul Ring Share Proof]')" in job["if"]
    assert "github.event.issue.pull_request == null" in job["if"]

    steps = job["steps"]
    assert len(steps) == 1
    step = steps[0]
    assert step["uses"] == "actions/github-script@v8"
    assert "run" not in step

    script = step["with"]["script"]
    assert "github.rest.issues.createComment" in script
    assert "const issue = context.payload.issue" in script
    assert "issue.html_url" in script
    assert "replaceAll(\"`\", \"'\")" in script
    assert "Soul Ring Share Proof" in script
    assert "cyberhuatuo market-ready --remote --strict-remote --username" in script
    assert "cyberhuatuo proof-pack --username" in script
    assert "cyberhuatuo market-copy --username" in script
    assert "Launch Closure Checklist" in script
    assert "cyberhuatuo record-share --username" in script
    assert "--source-url ${issueUrl}" in script
    assert "cyberhuatuo share-report --username" in script
    assert "cyberhuatuo share-leaderboard --framework" in script
    assert "cyberhuatuo activation --username" in script
    assert "cyberhuatuo flywheel --username" in script
    assert "No downloads, retention, repost counts, referral conversions, or rewards are invented" in script
    assert "actions/checkout" not in workflow_text
    assert "\nrun:" not in workflow_text


def test_github_workflow_comments_on_pull_request_with_soul_ring_settlement():
    workflow_path = ROOT / ".github" / "workflows" / "soul-ring-pr.yml"

    assert workflow_path.is_file()
    workflow_text = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)

    assert workflow["name"] == "Soul Ring PR Settlement"
    assert workflow["on"]["pull_request_target"]["types"] == ["opened", "reopened", "ready_for_review"]
    assert workflow["permissions"] == {"issues": "write", "contents": "read"}

    jobs = workflow["jobs"]
    assert set(jobs) == {"soul-ring-pr-comment"}
    job = jobs["soul-ring-pr-comment"]
    assert "github.event.pull_request.draft == false" in job["if"]

    steps = job["steps"]
    assert len(steps) == 1
    step = steps[0]
    assert step["uses"] == "actions/github-script@v8"
    assert "run" not in step

    script = step["with"]["script"]
    assert "github.rest.issues.createComment" in script
    assert "const pr = context.payload.pull_request" in script
    assert "const prUrl = pr.html_url" in script
    assert "replaceAll(\"`\", \"'\")" in script
    assert "Soul Ring PR Settlement" in script
    assert "Launch Closure Checklist" in script
    assert "cyberhuatuo proof-pack --username" in script
    assert "cyberhuatuo market-copy --username" in script
    assert "cyberhuatuo market-ready --remote --strict-remote --username" in script
    assert "cyberhuatuo record-return --username" in script
    assert '--surface "Pull Request" --source-url ${prUrl}' in script
    assert "cyberhuatuo upload --title" in script
    assert "cyberhuatuo ladder" in script
    assert "--framework <framework>" in script
    assert "cyberhuatuo ranking" in script
    assert "cyberhuatuo card" in script
    assert "cyberhuatuo campaign" in script
    assert "cyberhuatuo sect-hall" in script
    assert "Soul Ring Breakthrough Ladder" in script
    assert "next gate" in script
    assert "real-data pledge" in script
    assert "not invented" in script
    assert "actions/checkout" not in workflow_text
    assert "\nrun:" not in workflow_text


def test_github_pull_request_template_turns_real_fix_into_soul_ring_settlement():
    template_path = ROOT / ".github" / "pull_request_template.md"

    assert template_path.is_file()
    template = template_path.read_text(encoding="utf-8")

    assert "Soul Ring PR Settlement" in template
    assert "GitHub username" in template
    assert "Framework" in template
    assert "Linked First Soul Ring issue" in template
    assert "Real symptom" in template
    assert "Root cause" in template
    assert "Fix summary" in template
    assert "Verification evidence" in template
    assert "real-data pledge" in template
    assert "not invented" in template
    assert "cyberhuatuo upload --title" in template
    assert "--contributor <github-username>" in template
    assert "cyberhuatuo ladder <github-username> --framework <framework>" in template
    assert "cyberhuatuo ranking <github-username>" in template
    assert "cyberhuatuo card <github-username>" in template
    assert "cyberhuatuo campaign <github-username> --framework <framework>" in template
    assert ".github/ISSUE_TEMPLATE/soul-ring-prescription.yml" in template
