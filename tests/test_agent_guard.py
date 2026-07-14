import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cyberhuatuo.agent_guard import assess_command, format_guard_report
from cyberhuatuo.cli import _build_parser, cmd_guard
from cyberhuatuo.guard_report import (
    GuardReportError,
    build_guard_case_report,
    format_guard_case_report,
    redact_guard_text,
    write_guard_case_report,
)


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


def test_guard_report_formats_expected_decision(tmp_path):
    result = assess_command("rm -rf ./cache", cwd=tmp_path, workspace_root=tmp_path)

    report = format_guard_report(result, expected="ASK")

    assert "Expected: **ASK**" in report
    assert "Expected match: **yes**" in report


def test_cli_exposes_guard_without_an_execute_mode():
    parser = _build_parser()
    args = parser.parse_args(["guard", "rm -rf ./cache", "--workspace-root", ".", "--json"])

    assert args.command == "guard"
    assert args.shell_command == "rm -rf ./cache"
    assert args.json is True
    assert not hasattr(args, "execute")


def test_cli_expected_decision_uses_match_exit_contract(tmp_path, capsys):
    parser = _build_parser()
    matching = parser.parse_args([
        "guard",
        "rm -rf /",
        "--workspace-root",
        str(tmp_path),
        "--expected",
        "BLOCK",
    ])
    mismatch = parser.parse_args([
        "guard",
        "rm -rf /",
        "--workspace-root",
        str(tmp_path),
        "--expected",
        "ask",
    ])

    assert matching.expected == "block"
    assert cmd_guard(matching) == 0
    assert "Expected match: **yes**" in capsys.readouterr().out
    assert cmd_guard(mismatch) == 1
    assert "Expected match: **no**" in capsys.readouterr().out


def test_cli_expected_json_is_machine_readable(tmp_path, capsys):
    parser = _build_parser()
    args = parser.parse_args([
        "guard",
        "rm -rf ./cache",
        "--cwd",
        str(tmp_path),
        "--workspace-root",
        str(tmp_path),
        "--expected",
        "ask",
        "--json",
    ])

    assert cmd_guard(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["expected"] == "ask"
    assert payload["matches_expected"] is True


def test_cli_exit_zero_only_masks_decision_mismatch(tmp_path, capsys):
    parser = _build_parser()
    args = parser.parse_args([
        "guard",
        "rm -rf /",
        "--workspace-root",
        str(tmp_path),
        "--expected",
        "allow",
        "--exit-zero",
    ])

    assert cmd_guard(args) == 0
    assert "Expected match: **no**" in capsys.readouterr().out


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


def test_redacted_guard_report_contains_no_raw_secret_identity_or_path(tmp_path, capsys):
    parser = _build_parser()
    report_path = tmp_path / "reports" / "guard-report.md"
    raw_token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
    command = rf'Remove-Item "C:\Users\Alice\SecretRepo" -Recurse -Force --token {raw_token}'
    args = parser.parse_args([
        "guard",
        command,
        "--workspace-root",
        str(tmp_path / "PrivateWorkspace"),
        "--expected",
        "block",
        "--report",
        str(report_path),
        "--confirm-report",
        "--redact",
        "SecretRepo",
        "--agent-host",
        "codex",
        "--shell",
        "PowerShell",
        "--helpful",
        "no",
    ])

    assert cmd_guard(args) == 0
    output = capsys.readouterr().out
    report = report_path.read_text(encoding="utf-8")

    for private_value in (raw_token, "Alice", "SecretRepo", str(tmp_path)):
        assert private_value not in output
        assert private_value not in report
    assert "<REDACTED_SECRET>" in report
    assert "Command executed by this report: **no**" in report
    assert "Agent host: `codex`" in report
    assert "Expected: **BLOCK**" in report
    assert "Actual: **BLOCK**" in report
    assert "Case fingerprint: `CHT-GUARD-" in report
    assert "Generated locally" in report
    assert "No network request or public upload was performed." in output


def test_guard_report_requires_expected_and_rejects_raw_json(tmp_path, capsys):
    parser = _build_parser()
    missing_expected = parser.parse_args([
        "guard",
        "git status --short",
        "--report",
        str(tmp_path / "missing.md"),
    ])
    raw_json = parser.parse_args([
        "guard",
        "git status --short",
        "--expected",
        "allow",
        "--report",
        str(tmp_path / "raw-json.md"),
        "--json",
    ])

    assert cmd_guard(missing_expected) == 4
    assert "--report requires --expected" in capsys.readouterr().err
    assert cmd_guard(raw_json) == 4
    assert "cannot be combined with --json" in capsys.readouterr().err


def test_noninteractive_report_requires_explicit_confirmation(tmp_path, capsys, monkeypatch):
    parser = _build_parser()
    report_path = tmp_path / "guard-report.md"
    args = parser.parse_args([
        "guard",
        "git status --short",
        "--expected",
        "allow",
        "--report",
        str(report_path),
    ])
    monkeypatch.setattr(sys, "stdin", io.StringIO())

    assert cmd_guard(args) == 4
    captured = capsys.readouterr()
    assert "Guard report preview" in captured.out
    assert "requires --confirm-report" in captured.err
    assert not report_path.exists()


def test_report_operational_error_is_not_masked_by_exit_zero(tmp_path, capsys):
    parser = _build_parser()
    report_path = tmp_path / "guard-report.md"
    report_path.write_text("existing", encoding="utf-8")
    args = parser.parse_args([
        "guard",
        "git status --short",
        "--expected",
        "allow",
        "--report",
        str(report_path),
        "--confirm-report",
        "--exit-zero",
    ])

    assert cmd_guard(args) == 4
    assert report_path.read_text(encoding="utf-8") == "existing"
    assert "Report already exists" in capsys.readouterr().err


def test_report_overwrite_is_explicit_and_atomic(tmp_path):
    path = tmp_path / "guard-report.md"
    written = write_guard_case_report(path, "first\n")

    assert written == path.resolve()
    with pytest.raises(GuardReportError, match="already exists"):
        write_guard_case_report(path, "second\n")
    write_guard_case_report(path, "second\n", overwrite=True)
    assert path.read_text(encoding="utf-8") == "second\n"


def test_private_key_material_fails_closed(tmp_path, capsys):
    parser = _build_parser()
    report_path = tmp_path / "guard-report.md"
    args = parser.parse_args([
        "guard",
        "echo -----BEGIN PRIVATE KEY-----",
        "--expected",
        "allow",
        "--report",
        str(report_path),
        "--confirm-report",
    ])

    assert cmd_guard(args) == 4
    assert "private-key block" in capsys.readouterr().err
    assert not report_path.exists()


def test_case_fingerprint_uses_redacted_canonical_case(tmp_path):
    assessment = assess_command(
        "rm -rf ./client-alpha/cache",
        cwd=tmp_path,
        workspace_root=tmp_path,
    )
    first = build_guard_case_report(
        assessment,
        expected="ask",
        custom_redactions=("client-alpha",),
        generated_at=datetime(2026, 7, 14, 0, 0, tzinfo=timezone.utc),
    )
    second = build_guard_case_report(
        assessment,
        expected="ASK",
        custom_redactions=("client-alpha",),
        generated_at=datetime(2026, 7, 15, 0, 0, tzinfo=timezone.utc),
    )

    assert first.case_fingerprint == second.case_fingerprint
    assert "client-alpha" not in format_guard_case_report(first)


def test_redaction_removes_url_authority_and_absolute_paths(tmp_path):
    raw = "curl https://user:pass@internal.example/api?token=abc C:\\Company\\Private /srv/private/data"

    redacted = redact_guard_text(raw, cwd=str(tmp_path), workspace_root=str(tmp_path))

    assert "user:pass" not in redacted
    assert "internal.example" not in redacted
    assert "C:\\Company" not in redacted
    assert "/srv/private" not in redacted
    assert "token=abc" not in redacted
    assert "https://<URL_HOST>" in redacted
    assert "<ABSOLUTE_PATH>" in redacted


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
