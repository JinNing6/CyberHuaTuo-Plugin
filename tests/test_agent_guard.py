import json
from pathlib import Path

import pytest

from cyberhuatuo.agent_guard import assess_command, format_guard_report
from cyberhuatuo.cli import _build_parser, cmd_guard


@pytest.mark.parametrize(
    "command",
    [
        "Get-ChildItem -Force",
        "git status --short",
        "python -m pytest tests/test_delete_feature.py",
        "rg --files",
    ],
)
def test_read_only_commands_are_allowed(command, tmp_path):
    result = assess_command(command, cwd=tmp_path, workspace_root=tmp_path)

    assert result.decision == "allow"
    assert result.risk == "low"
    assert result.reversible is True


@pytest.mark.parametrize(
    "command",
    [
        r"Remove-Item C:\ -Recurse -Force",
        r"Remove-Item $HOME -Recurse -Force",
        r"del /s /q %USERPROFILE%\*",
        "rm -rf /",
        "rm -rf ~",
        "mkfs.ext4 /dev/sda1",
        "format C:",
        "diskpart /s wipe.txt",
        "powershell -Command \"Remove-Item C:\\\\ -Recurse -Force\"",
        "cmd /c \"rmdir /s /q C:\\\\\"",
        "bash -c 'rm -rf /'",
        "/usr/bin/rm -rf /",
        "sudo /bin/rm -rf /",
        '"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "Remove-Item C:\\\\ -Recurse -Force"',
        "Clear-Disk -Number 0 -RemoveData -Confirm:$false",
        "Format-Volume -DriveLetter C -FileSystem NTFS -Confirm:$false",
    ],
)
def test_machine_or_identity_scope_destruction_is_blocked(command, tmp_path):
    result = assess_command(command, cwd=tmp_path, workspace_root=tmp_path)

    assert result.decision == "block"
    assert result.risk == "critical"
    assert result.reversible is False
    assert result.reasons


def test_recursive_delete_inside_workspace_requires_human_approval(tmp_path):
    target = tmp_path / "build"
    target.mkdir()

    result = assess_command(
        "Remove-Item .\\build -Recurse -Force",
        cwd=tmp_path,
        workspace_root=tmp_path,
    )

    assert result.decision == "ask"
    assert result.risk == "high"
    assert result.reversible is False
    assert any("workspace" in reason.lower() for reason in result.reasons)


def test_delete_outside_workspace_is_blocked(tmp_path):
    workspace = tmp_path / "repo"
    workspace.mkdir()
    outside = tmp_path / "archive"
    outside.mkdir()

    result = assess_command(
        f'Remove-Item "{outside}" -Recurse -Force',
        cwd=workspace,
        workspace_root=workspace,
    )

    assert result.decision == "block"
    assert result.risk == "critical"
    assert any("outside" in reason.lower() for reason in result.reasons)


@pytest.mark.parametrize("command", ["git clean -fdx", "git reset --hard HEAD~1"])
def test_destructive_git_cleanup_requires_approval(command, tmp_path):
    result = assess_command(command, cwd=tmp_path, workspace_root=tmp_path)

    assert result.decision == "ask"
    assert result.risk == "high"


def test_dynamic_delete_target_is_blocked_when_scope_cannot_be_proven(tmp_path):
    result = assess_command(
        "Remove-Item $target -Recurse -Force",
        cwd=tmp_path,
        workspace_root=tmp_path,
    )

    assert result.decision == "block"
    assert any("dynamic" in reason.lower() or "resolve" in reason.lower() for reason in result.reasons)


def test_guard_result_is_serializable_and_explains_no_rollback(tmp_path):
    result = assess_command("rm -rf ./cache", cwd=tmp_path, workspace_root=tmp_path)
    payload = result.as_dict()
    report = format_guard_report(result)

    assert json.loads(json.dumps(payload))["decision"] == "ask"
    assert "Agent Action Guard" in report
    assert "No reliable rollback" in report
    assert "does not execute" in report
    assert result.rule_ids
    assert result.rule_ids[0].startswith("CHT-")


def test_cli_exposes_guard_without_an_execute_mode():
    parser = _build_parser()
    args = parser.parse_args(["guard", "rm -rf ./cache", "--workspace-root", ".", "--json"])

    assert args.command == "guard"
    assert args.shell_command == "rm -rf ./cache"
    assert args.json is True
    assert not hasattr(args, "execute")


def test_guard_self_test_reviews_three_cases_without_execute_mode(tmp_path, capsys):
    parser = _build_parser()
    args = parser.parse_args([
        "guard",
        "--self-test",
        "--workspace-root",
        str(tmp_path),
    ])

    assert args.shell_command is None
    assert args.self_test is True
    assert not hasattr(args, "execute")
    assert cmd_guard(args) == 0

    output = capsys.readouterr().out
    assert "SELF-TEST PASSED" in output
    assert "ALLOW" in output
    assert "ASK" in output
    assert "BLOCK" in output
    assert "No command was executed." in output


def test_guard_self_test_json_is_machine_readable(tmp_path, capsys):
    parser = _build_parser()
    args = parser.parse_args([
        "guard",
        "--self-test",
        "--workspace-root",
        str(tmp_path),
        "--json",
    ])

    assert cmd_guard(args) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "passed"
    assert payload["executed"] is False
    assert [case["actual"] for case in payload["cases"]] == ["allow", "ask", "block"]


def test_guard_requires_a_command_or_self_test(capsys):
    parser = _build_parser()
    args = parser.parse_args(["guard"])

    assert cmd_guard(args) == 1
    assert "Provide a shell command or use --self-test." in capsys.readouterr().err


def test_packaged_and_codex_guard_skills_match():
    root = Path(__file__).resolve().parents[1]
    packaged = root / "skills" / "cyberhuatuo-agent-guard" / "SKILL.md"
    codex = root / ".agents" / "skills" / "cyberhuatuo-agent-guard" / "SKILL.md"

    assert packaged.is_file()
    assert codex.is_file()
    assert packaged.read_text(encoding="utf-8") == codex.read_text(encoding="utf-8")
    text = packaged.read_text(encoding="utf-8")
    for required in ("agent_action_guard", "cyberhuatuo guard", "BLOCK", "ASK", "does not execute"):
        assert required in text
