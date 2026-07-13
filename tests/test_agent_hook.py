import json
import subprocess
import sys
from pathlib import Path

from cyberhuatuo.agent_hook import evaluate_hook_payload

ROOT = Path(__file__).resolve().parents[1]


def _payload(command: str, *, codex: bool, cwd: Path) -> dict:
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": str(cwd),
        "tool_use_id": "tool-1",
    }
    if codex:
        payload["turn_id"] = "turn-1"
    return payload


def test_codex_block_uses_minimal_supported_deny_shape(tmp_path):
    output = evaluate_hook_payload(_payload("rm -rf /", codex=True, cwd=tmp_path))

    assert output == {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": output["hookSpecificOutput"]["permissionDecisionReason"],
        }
    }
    assert "CHT-FS-ROOT-001" in output["hookSpecificOutput"]["permissionDecisionReason"]


def test_codex_ask_is_converted_to_deny_because_codex_does_not_support_ask(tmp_path):
    output = evaluate_hook_payload(_payload("rm -rf ./build", codex=True, cwd=tmp_path))

    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "human approval" in output["hookSpecificOutput"]["permissionDecisionReason"].lower()


def test_claude_ask_remains_an_interactive_ask(tmp_path):
    output = evaluate_hook_payload(_payload("rm -rf ./build", codex=False, cwd=tmp_path))

    assert output["hookSpecificOutput"]["permissionDecision"] == "ask"


def test_safe_shell_command_returns_no_hook_decision(tmp_path):
    assert evaluate_hook_payload(_payload("git status --short", codex=True, cwd=tmp_path)) is None


def test_non_shell_tool_is_not_intercepted(tmp_path):
    payload = _payload("rm -rf /", codex=True, cwd=tmp_path)
    payload["tool_name"] = "mcp__docs__search"

    assert evaluate_hook_payload(payload) is None


def test_malformed_shell_payload_fails_closed(tmp_path):
    payload = _payload("rm -rf /", codex=True, cwd=tmp_path)
    payload["tool_input"] = {}

    output = evaluate_hook_payload(payload)

    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "CHT-HOOK-INPUT-001" in output["hookSpecificOutput"]["permissionDecisionReason"]


def test_bundled_hook_process_blocks_without_executing(tmp_path):
    script = ROOT / "hooks" / "pre_tool_guard.py"
    completed = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(_payload("rm -rf /", codex=True, cwd=tmp_path)),
        text=True,
        capture_output=True,
        check=False,
        cwd=tmp_path,
    )

    assert completed.returncode == 0
    output = json.loads(completed.stdout)
    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert completed.stderr == ""


def test_plugin_hook_manifest_targets_bash_pretooluse():
    hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    entries = hooks["hooks"]["PreToolUse"]

    assert entries[0]["matcher"] == "Bash"
    handler = entries[0]["hooks"][0]
    assert handler["type"] == "command"
    assert "pre_tool_guard.py" in handler["command"]

    for manifest_path in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
        manifest = json.loads((ROOT / manifest_path).read_text(encoding="utf-8"))
        assert manifest["hooks"] == "./hooks/hooks.json"

    packaging = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    assert "recursive-include hooks *.json *.py" in packaging


def test_public_surfaces_state_guard_and_enforcement_boundary():
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    chinese = (ROOT / "README_CN.md").read_text(encoding="utf-8")
    mcp = (ROOT / "README_MCP.md").read_text(encoding="utf-8")
    design = (ROOT / "docs" / "agent-action-guard.md").read_text(encoding="utf-8")

    assert "Agent Action Guard" in english
    assert "Agent 行医护栏" in chinese
    assert "agent_action_guard" in mcp
    assert "not a sandbox" in design
    assert "unified_exec" in design
    assert "independently implemented" in design
