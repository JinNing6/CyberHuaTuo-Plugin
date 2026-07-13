"""PreToolUse protocol adapter for the CyberHuaTuo action guard."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .agent_guard import GuardAssessment, assess_command

_SHELL_TOOL_NAMES = {
    "bash",
    "launch-process",
    "powershell",
    "shell",
    "shell_command",
}


def _hook_output(decision: str, reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }


def _assessment_reason(assessment: GuardAssessment, *, human_approval: bool = False) -> str:
    rule_text = ", ".join(assessment.rule_ids) or "CHT-GUARD-UNKNOWN"
    reason = assessment.reasons[0] if assessment.reasons else "The proposed action did not pass policy review."
    prefix = "Human approval is required. " if human_approval else ""
    return f"CyberHuaTuo [{rule_text}] {prefix}{reason}"


def evaluate_hook_payload(
    payload: Mapping[str, Any],
    *,
    workspace_root: str | Path | None = None,
) -> dict[str, Any] | None:
    """Return a host hook decision, or None when the host should continue."""
    tool_name = str(payload.get("tool_name") or "").strip().lower()
    if tool_name not in _SHELL_TOOL_NAMES:
        return None

    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, Mapping) else None
    if not isinstance(command, str) or not command.strip():
        return _hook_output(
            "deny",
            "CyberHuaTuo [CHT-HOOK-INPUT-001] Shell hook input has no reviewable command; denied fail-closed.",
        )

    cwd = str(payload.get("cwd") or os.getcwd())
    root = workspace_root or os.environ.get("CYBERHUATUO_WORKSPACE_ROOT") or cwd
    try:
        assessment = assess_command(command, cwd=cwd, workspace_root=root)
    except Exception as exc:
        return _hook_output(
            "deny",
            f"CyberHuaTuo [CHT-HOOK-RUNTIME-001] Guard evaluation failed closed: {type(exc).__name__}.",
        )

    if assessment.decision == "allow":
        return None
    if assessment.decision == "block":
        return _hook_output("deny", _assessment_reason(assessment))

    is_codex = bool(str(payload.get("turn_id") or "").strip())
    if is_codex:
        # Codex PreToolUse does not currently support "ask"; returning it fails open.
        return _hook_output("deny", _assessment_reason(assessment, human_approval=True))
    return _hook_output("ask", _assessment_reason(assessment, human_approval=True))


def run_hook(stdin: Any = None, stdout: Any = None) -> int:
    """Read one hook event and emit only protocol JSON when a decision is needed."""
    input_stream = stdin or sys.stdin
    output_stream = stdout or sys.stdout
    try:
        payload = json.load(input_stream)
        if not isinstance(payload, Mapping):
            raise TypeError("hook payload must be an object")
        output = evaluate_hook_payload(payload)
    except Exception as exc:
        output = _hook_output(
            "deny",
            f"CyberHuaTuo [CHT-HOOK-JSON-001] Hook input could not be parsed; denied fail-closed ({type(exc).__name__}).",
        )

    if output is not None:
        json.dump(output, output_stream, ensure_ascii=False, separators=(",", ":"))
        output_stream.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_hook())
