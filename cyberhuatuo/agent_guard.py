"""Read-only preflight checks for destructive agent shell actions."""

from __future__ import annotations

import json
import ntpath
import os
import re
import shlex
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

_DELETE_COMMAND_RE = re.compile(
    r"(?i)(?:^|[;&|]\s*)(?:sudo\s+)?(?:[^\s;&|]*[\\/])?(?:remove-item|rm|del|erase|rd|rmdir|shred|clear-content)(?:\.exe)?\b"
)
_FIND_DELETE_RE = re.compile(r"(?i)\bfind\b[^\r\n;&|]*\s-delete\b")
_GIT_DESTRUCTIVE_RE = re.compile(r"(?i)\bgit\s+(?:clean\b|reset\s+--hard\b|checkout\s+--\b|restore\b)")
_MIRROR_DELETE_RE = re.compile(r"(?i)(?:\brobocopy\b[^\r\n]*\s/mir\b|\brsync\b[^\r\n]*\s--delete\b)")
_DISK_DESTRUCTIVE_RE = re.compile(
    r"(?i)(?:\bmkfs(?:\.[a-z0-9]+)?\b|\bwipefs\b|\bdiskpart\b|(?:^|\s)format(?:\.com)?\s+[a-z]:|"
    r"\bdd\b[^\r\n]*\bof=/dev/|\bcipher\s+/w:|\bsdelete\b|\bformat-volume\b|\bclear-disk\b|"
    r"\bremove-partition\b|\bsgdisk\b[^\r\n]*--zap-all\b)"
)
_DATABASE_DESTRUCTIVE_RE = re.compile(r"(?i)\b(?:drop\s+(?:database|schema|table)|truncate\s+table)\b")
_DYNAMIC_TARGET_RE = re.compile(r"(?:\$\{?[^\s}]+\}?|%[^%]+%|`[^`]+`)")
_WINDOWS_ROOT_RE = re.compile(r"(?i)^[a-z]:[\\/]*$")
_WINDOWS_ABSOLUTE_RE = re.compile(r"(?i)^[a-z]:[\\/]")
_WINDOWS_OPTION_RE = re.compile(r"(?i)^/[a-z?]+$")
_SHELL_OPERATOR_RE = re.compile(r"^(?:&&|\|\||[;&|])$")

_PROTECTED_ENV_TARGETS = {
    "$home",
    "${home}",
    "$env:userprofile",
    "$env:homepath",
    "%userprofile%",
    "%homepath%",
    "~",
    "~/",
    "~\\",
}


@dataclass(frozen=True)
class GuardAssessment:
    """A deterministic, serializable action preflight result."""

    decision: str
    risk: str
    command: str
    cwd: str
    workspace_root: str
    targets: tuple[str, ...]
    reasons: tuple[str, ...]
    reversible: bool
    safe_next_steps: tuple[str, ...]
    rule_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False, indent=2)


def _tokenize(command: str) -> list[str]:
    try:
        tokens = shlex.split(command, posix=False)
    except ValueError:
        tokens = command.split()
    return [token.strip().strip('"\'') for token in tokens if token.strip()]


def _command_variants(command: str) -> tuple[str, ...]:
    """Expose payloads passed through common shell-command wrappers."""
    variants = [command]
    tokens = _tokenize(command)
    wrappers = {
        "powershell": {"-command", "-c"},
        "powershell.exe": {"-command", "-c"},
        "pwsh": {"-command", "-c"},
        "pwsh.exe": {"-command", "-c"},
        "cmd": {"/c", "/k"},
        "cmd.exe": {"/c", "/k"},
        "bash": {"-c"},
        "sh": {"-c"},
        "zsh": {"-c"},
    }
    for index, token in enumerate(tokens[:-1]):
        normalized_token = token.replace("\\", "/").rsplit("/", 1)[-1].lower()
        markers = wrappers.get(normalized_token)
        if not markers or index + 1 >= len(tokens):
            continue
        if tokens[index + 1].lower() not in markers or index + 2 >= len(tokens):
            continue
        payload = " ".join(tokens[index + 2 :]).strip().strip('"\'')
        if payload and payload not in variants:
            variants.append(payload)
    return tuple(variants)


def _is_option(token: str) -> bool:
    if token in {"/", "./", "../", ".\\", "..\\"}:
        return False
    if token.startswith("-"):
        return True
    return bool(_WINDOWS_OPTION_RE.fullmatch(token))


def _extract_delete_targets(command: str) -> tuple[str, ...]:
    command_names = {"remove-item", "rm", "del", "erase", "rd", "rmdir", "shred", "clear-content"}
    targets: list[str] = []

    for variant in _command_variants(command):
        tokens = _tokenize(variant)
        lowered = [token.lower() for token in tokens]
        for index, token in enumerate(lowered):
            normalized = token.rstrip(";|&").replace("\\", "/").rsplit("/", 1)[-1]
            if normalized.endswith(".exe"):
                normalized = normalized[:-4]
            if normalized not in command_names:
                continue
            for candidate in tokens[index + 1 :]:
                candidate = candidate.rstrip(";|&")
                if not candidate or _SHELL_OPERATOR_RE.fullmatch(candidate):
                    break
                if _is_option(candidate):
                    continue
                targets.append(candidate)
            break
        if targets:
            break

    if not targets and _FIND_DELETE_RE.search(command):
        tokens = _tokenize(command)
        lowered = [token.lower() for token in tokens]
        try:
            find_index = lowered.index("find")
            if find_index + 1 < len(tokens) and not _is_option(tokens[find_index + 1]):
                targets.append(tokens[find_index + 1])
        except ValueError:
            pass

    return tuple(dict.fromkeys(targets))


def _contains_wildcard(target: str) -> bool:
    return any(marker in target for marker in ("*", "?", "[", "]"))


def _is_protected_identity_target(target: str) -> bool:
    value = target.strip().lower().rstrip("/\\")
    if value in {item.rstrip("/\\") for item in _PROTECTED_ENV_TARGETS}:
        return True
    return value.startswith(("$home/", "$home\\", "%userprofile%/", "%userprofile%\\"))


def _is_machine_root(target: str) -> bool:
    value = target.strip()
    if value in {"/", "/*", "\\", "\\*"}:
        return True
    return bool(_WINDOWS_ROOT_RE.fullmatch(value.rstrip("*")))


def _is_system_path(target: str) -> bool:
    value = target.replace("/", "\\").lower().rstrip("\\*")
    windows_prefixes = (
        r"c:\windows",
        r"c:\program files",
        r"c:\program files (x86)",
        r"c:\programdata",
        r"c:\users",
    )
    if value.startswith(windows_prefixes):
        return True
    posix_value = target.replace("\\", "/").lower().rstrip("/*")
    return posix_value == "/home" or posix_value.startswith(
        ("/etc", "/usr", "/var", "/boot", "/dev", "/proc", "/sys", "/root", "/home/")
    )


def _looks_dynamic(target: str) -> bool:
    if _is_protected_identity_target(target):
        return False
    return bool(_DYNAMIC_TARGET_RE.search(target))


def _resolve_target(target: str, cwd: Path) -> str | None:
    value = target.strip().strip('"\'')
    if not value or _looks_dynamic(value) or _contains_wildcard(value) or value.startswith("~"):
        return None

    if _WINDOWS_ABSOLUTE_RE.match(value):
        return ntpath.normcase(ntpath.normpath(value))

    local_value = value.replace("\\", os.sep).replace("/", os.sep)
    try:
        return os.path.normcase(str((cwd / local_value).resolve(strict=False)))
    except (OSError, RuntimeError, ValueError):
        return None


def _is_within(resolved_target: str, workspace_root: Path) -> bool:
    workspace_text = str(workspace_root.resolve(strict=False))
    if _WINDOWS_ABSOLUTE_RE.match(resolved_target):
        if not _WINDOWS_ABSOLUTE_RE.match(workspace_text):
            return False
        try:
            return ntpath.commonpath([ntpath.normcase(resolved_target), ntpath.normcase(workspace_text)]) == ntpath.normcase(
                workspace_text
            )
        except ValueError:
            return False
    try:
        return os.path.commonpath([resolved_target, os.path.normcase(workspace_text)]) == os.path.normcase(workspace_text)
    except ValueError:
        return False


def _safe_steps(decision: str) -> tuple[str, ...]:
    common = (
        "List and resolve every target path before changing anything.",
        "Create a verified snapshot, backup, or quarantine copy outside the target tree.",
        "Prefer moving files to a quarantine directory or recycle bin over permanent deletion.",
    )
    if decision == "allow":
        return ("No destructive filesystem action was detected; keep the command inside the declared workspace.",)
    if decision == "ask":
        return common + ("Require explicit human approval for the exact resolved targets before execution.",)
    return common + ("Do not execute this command; reduce its scope and run the guard again.",)


def assess_command(
    command: str,
    *,
    cwd: str | Path | None = None,
    workspace_root: str | Path | None = None,
    allowed_roots: Sequence[str | Path] | None = None,
) -> GuardAssessment:
    """Assess a proposed shell command without executing or modifying it."""

    command = (command or "").strip()
    cwd_path = Path(cwd or os.getcwd()).resolve(strict=False)
    workspace_path = Path(workspace_root or cwd_path).resolve(strict=False)
    allowed_paths = [Path(path).resolve(strict=False) for path in (allowed_roots or ())]
    allowed_paths.insert(0, workspace_path)

    command_variants = _command_variants(command)
    delete_action = any(_DELETE_COMMAND_RE.search(value) or _FIND_DELETE_RE.search(value) for value in command_variants)
    git_action = any(_GIT_DESTRUCTIVE_RE.search(value) for value in command_variants)
    mirror_action = any(_MIRROR_DELETE_RE.search(value) for value in command_variants)
    disk_action = any(_DISK_DESTRUCTIVE_RE.search(value) for value in command_variants)
    database_action = any(_DATABASE_DESTRUCTIVE_RE.search(value) for value in command_variants)
    destructive = delete_action or git_action or mirror_action or disk_action or database_action

    if not destructive:
        return GuardAssessment(
            decision="allow",
            risk="low",
            command=command,
            cwd=str(cwd_path),
            workspace_root=str(workspace_path),
            targets=(),
            reasons=("No destructive filesystem, disk, database, mirror-delete, or destructive Git signature was detected.",),
            reversible=True,
            safe_next_steps=_safe_steps("allow"),
            rule_ids=("CHT-GUARD-000",),
        )

    if disk_action:
        reasons = ("Disk formatting, partitioning, wiping, or raw-device overwrite commands are machine-scope operations.",)
        return GuardAssessment(
            "block",
            "critical",
            command,
            str(cwd_path),
            str(workspace_path),
            (),
            reasons,
            False,
            _safe_steps("block"),
            ("CHT-DISK-001",),
        )

    if database_action:
        reasons = ("Database DROP/TRUNCATE scope cannot be proven safe from a shell string or rolled back reliably.",)
        return GuardAssessment(
            "block",
            "critical",
            command,
            str(cwd_path),
            str(workspace_path),
            (),
            reasons,
            False,
            _safe_steps("block"),
            ("CHT-DATA-001",),
        )

    if git_action:
        reasons = ("Destructive Git cleanup/reset can discard tracked changes or untracked files inside the workspace.",)
        return GuardAssessment(
            "ask",
            "high",
            command,
            str(cwd_path),
            str(workspace_path),
            (str(workspace_path),),
            reasons,
            False,
            _safe_steps("ask"),
            ("CHT-GIT-001",),
        )

    targets = _extract_delete_targets(command)
    if mirror_action and not targets:
        reasons = ("Mirror/delete synchronization can remove destination files, but destination scope was not proven.",)
        return GuardAssessment(
            "block",
            "critical",
            command,
            str(cwd_path),
            str(workspace_path),
            (),
            reasons,
            False,
            _safe_steps("block"),
            ("CHT-SYNC-001",),
        )

    if not targets:
        reasons = ("A destructive action was detected, but its exact target paths could not be resolved.",)
        return GuardAssessment(
            "block",
            "critical",
            command,
            str(cwd_path),
            str(workspace_path),
            (),
            reasons,
            False,
            _safe_steps("block"),
            ("CHT-SCOPE-UNRESOLVED-001",),
        )

    reasons: list[str] = []
    rule_ids: list[str] = []
    decision = "ask"
    risk = "high"
    for target in targets:
        if _is_machine_root(target):
            decision, risk = "block", "critical"
            reasons.append(f"Target {target!r} is a filesystem or drive root.")
            rule_ids.append("CHT-FS-ROOT-001")
            continue
        if _is_protected_identity_target(target):
            decision, risk = "block", "critical"
            reasons.append(f"Target {target!r} resolves to a user home/profile scope.")
            rule_ids.append("CHT-FS-HOME-001")
            continue
        if _is_system_path(target):
            decision, risk = "block", "critical"
            reasons.append(f"Target {target!r} is a system or broad user-directory path.")
            rule_ids.append("CHT-FS-SYSTEM-001")
            continue
        if _looks_dynamic(target):
            decision, risk = "block", "critical"
            reasons.append(f"Target {target!r} is dynamic and cannot be resolved before execution.")
            rule_ids.append("CHT-SCOPE-DYNAMIC-001")
            continue
        if _contains_wildcard(target):
            decision, risk = "block", "critical"
            reasons.append(f"Target {target!r} contains a wildcard, so the deletion scope is not bounded.")
            rule_ids.append("CHT-SCOPE-WILDCARD-001")
            continue

        resolved = _resolve_target(target, cwd_path)
        if resolved is None:
            decision, risk = "block", "critical"
            reasons.append(f"Target {target!r} could not be resolved to an absolute path.")
            rule_ids.append("CHT-SCOPE-UNRESOLVED-001")
            continue
        if any(_is_within(resolved, allowed_root) for allowed_root in allowed_paths):
            reasons.append(f"Resolved target {resolved!r} is inside the declared workspace/allowed roots, but deletion is permanent.")
            rule_ids.append("CHT-FS-PERMANENT-001")
        else:
            decision, risk = "block", "critical"
            reasons.append(f"Resolved target {resolved!r} is outside the declared workspace/allowed roots.")
            rule_ids.append("CHT-SCOPE-OUTSIDE-001")

    return GuardAssessment(
        decision=decision,
        risk=risk,
        command=command,
        cwd=str(cwd_path),
        workspace_root=str(workspace_path),
        targets=targets,
        reasons=tuple(reasons),
        reversible=False,
        safe_next_steps=_safe_steps(decision),
        rule_ids=tuple(dict.fromkeys(rule_ids)),
    )


def format_guard_report(assessment: GuardAssessment, *, expected: str | None = None) -> str:
    """Format a compact report suitable for CLI and MCP surfaces."""

    icon = {"allow": "ALLOW", "ask": "ASK", "block": "BLOCK"}[assessment.decision]
    lines = [
        "# CyberHuaTuo Agent Action Guard",
        "",
        f"- Decision: **{icon}**",
        f"- Risk: **{assessment.risk.upper()}**",
        f"- Rules: **{', '.join(assessment.rule_ids) or 'none'}**",
        f"- Reversible: **{'yes' if assessment.reversible else 'no'}**",
        f"- Workspace: `{assessment.workspace_root}`",
        "- This guard is read-only and does not execute, rewrite, or approve the proposed command.",
    ]
    if expected is not None:
        normalized_expected = expected.strip().lower()
        if normalized_expected not in {"allow", "ask", "block"}:
            raise ValueError("expected must be ALLOW, ASK, or BLOCK")
        lines.extend(
            [
                f"- Expected: **{normalized_expected.upper()}**",
                f"- Expected match: **{'yes' if assessment.decision == normalized_expected else 'no'}**",
            ]
        )
    if assessment.targets:
        lines.append(f"- Parsed targets: {', '.join(f'`{target}`' for target in assessment.targets)}")
    lines.extend(["", "## Reasons"])
    lines.extend(f"- {reason}" for reason in assessment.reasons)
    lines.extend(["", "## Safer prescription"])
    lines.extend(f"{index}. {step}" for index, step in enumerate(assessment.safe_next_steps, 1))
    if not assessment.reversible:
        lines.extend(["", "**No reliable rollback is assumed for permanent deletion.**"])
    return "\n".join(lines)


def assess_many(
    commands: Iterable[str],
    *,
    cwd: str | Path | None = None,
    workspace_root: str | Path | None = None,
) -> tuple[GuardAssessment, ...]:
    return tuple(assess_command(command, cwd=cwd, workspace_root=workspace_root) for command in commands)
