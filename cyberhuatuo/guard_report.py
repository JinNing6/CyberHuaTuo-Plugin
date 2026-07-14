"""Privacy-preserving local case reports for Agent Action Guard decisions."""

from __future__ import annotations

import hashlib
import json
import ntpath
import os
import platform
import re
import tempfile
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .agent_guard import GuardAssessment

REPORT_SCHEMA = "cht-guard-report/v1"
REPORT_ERROR_EXIT = 4

_PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", re.IGNORECASE)
_SECRET_FLAG_RE = re.compile(
    r"(?i)(?P<prefix>--?(?:api[-_]?key|token|secret|password|passwd|pwd|credential)(?:\s+|=))"
    r"(?P<value>\"[^\"]*\"|'[^']*'|[^\s;&|]+)"
)
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)(?P<name>[A-Z_][A-Z0-9_]*(?:TOKEN|API_?KEY|SECRET|PASSWORD|PASSWD|PWD|CREDENTIAL)"
    r"[A-Z0-9_]*)\s*=\s*(?P<value>\"[^\"]*\"|'[^']*'|[^\s;&|]+)"
)
_SECRET_QUERY_RE = re.compile(
    r"(?i)(?P<name>(?:access_?token|api_?key|token|secret|password|passwd|credential))="
    r"(?P<value>[^&\s]+)"
)
_AUTHORIZATION_RE = re.compile(r"(?i)(?P<prefix>authorization\s*:\s*(?:bearer|basic)\s+)(?P<value>\S+)")
_KNOWN_TOKEN_RES = (
    re.compile(r"\bgh(?:p|o|u|s|r)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
)
_URL_AUTHORITY_RE = re.compile(r"(?i)\b(?P<scheme>[a-z][a-z0-9+.-]*://)(?P<authority>[^\s/]+)")
_WINDOWS_USER_PATH_RE = re.compile(
    r"(?i)(?P<prefix>\b[A-Z]:[\\/](?:Users|Documents and Settings)[\\/])(?P<user>[^\\/\s'\"`]+)"
)
_POSIX_USER_PATH_RE = re.compile(r"(?P<prefix>/(?:home|Users)/)(?P<user>[^/\s'\"`]+)")
_UNC_PATH_RE = re.compile(r"(?i)\\\\[^\\/\s'\"`]+[\\/][^\\/\s'\"`]+")
_WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"(?i)(?<![A-Za-z0-9_])[A-Z]:[\\/][^'\"`\r\n|;,]+")
_POSIX_ABSOLUTE_PATH_RE = re.compile(r"(?<![A-Za-z0-9:/])/(?![/*](?:\s|$))[^\s'\"`|;,)]+")
_WINDOWS_SWITCHES = {"/?", "/c", "/d", "/e", "/f", "/k", "/mir", "/q", "/s", "/w", "/y"}


class GuardReportError(ValueError):
    """Raised when a public-safe report cannot be produced or written."""


@dataclass(frozen=True)
class GuardCaseReport:
    """A redacted, serializable record that never contains the raw assessment."""

    schema: str
    case_fingerprint: str
    generated_at_utc: str
    cyberhuatuo_version: str
    agent_host: str
    operating_system: str
    shell: str
    expected: str
    actual: str
    matches_expected: bool
    helpful: str
    risk: str
    rule_ids: tuple[str, ...]
    reversible: bool
    command: str
    cwd: str
    workspace_root: str
    targets: tuple[str, ...]
    reasons: tuple[str, ...]
    safe_next_steps: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "schema": self.schema,
            "case_fingerprint": self.case_fingerprint,
            "generated_at_utc": self.generated_at_utc,
            "cyberhuatuo_version": self.cyberhuatuo_version,
            "agent_host": self.agent_host,
            "operating_system": self.operating_system,
            "shell": self.shell,
            "expected": self.expected,
            "actual": self.actual,
            "matches_expected": self.matches_expected,
            "helpful": self.helpful,
            "risk": self.risk,
            "rule_ids": list(self.rule_ids),
            "reversible": self.reversible,
            "executed": False,
            "command": self.command,
            "cwd": self.cwd,
            "workspace_root": self.workspace_root,
            "targets": list(self.targets),
            "reasons": list(self.reasons),
            "safe_next_steps": list(self.safe_next_steps),
        }


def _replace_literal(text: str, value: str, placeholder: str) -> str:
    value = (value or "").strip()
    if not value:
        return text
    flags = re.IGNORECASE if "\\" in value or re.match(r"(?i)^[a-z]:", value) else 0
    return re.sub(re.escape(value), lambda _match: placeholder, text, flags=flags)


def _path_variants(value: str) -> tuple[str, ...]:
    variants = {value}
    if "\\" in value or "/" in value:
        variants.add(value.replace("\\", "/"))
        variants.add(value.replace("/", "\\"))
    return tuple(sorted((item for item in variants if item), key=len, reverse=True))


def _redact_workspace_name(text: str, workspace_root: str) -> str:
    names = {Path(workspace_root).name, ntpath.basename(workspace_root.rstrip("\\/"))}
    for name in sorted((item for item in names if len(item) >= 5), key=len, reverse=True):
        pattern = re.compile(rf"(?i)(?<![A-Za-z0-9_.-]){re.escape(name)}(?=[\\/])")
        text = pattern.sub("<WORKSPACE_NAME>", text)
    return text


def _redact_posix_path(match: re.Match) -> str:
    value = match.group(0)
    if value.lower() in _WINDOWS_SWITCHES:
        return value
    return "<ABSOLUTE_PATH>"


def _normalize_control_characters(text: str) -> str:
    return "".join(character if character in "\n\t" or ord(character) >= 32 else "?" for character in text)


def redact_guard_text(
    value: str,
    *,
    cwd: str,
    workspace_root: str,
    custom_redactions: Sequence[str] = (),
) -> str:
    """Redact secrets, identities, hosts, URLs, and local paths from one report field."""

    text = _normalize_control_characters(str(value or ""))
    if _PRIVATE_KEY_RE.search(text):
        raise GuardReportError("A private-key block was detected; no public report was generated.")

    for secret in custom_redactions:
        if not secret:
            raise GuardReportError("Custom redaction values cannot be empty.")
        text = _replace_literal(text, secret, "<REDACTED_CUSTOM>")

    text = _SECRET_FLAG_RE.sub(lambda match: f"{match.group('prefix')}<REDACTED_SECRET>", text)
    text = _SECRET_ASSIGNMENT_RE.sub(lambda match: f"{match.group('name')}=<REDACTED_SECRET>", text)
    text = _SECRET_QUERY_RE.sub(lambda match: f"{match.group('name')}=<REDACTED_SECRET>", text)
    text = _AUTHORIZATION_RE.sub(lambda match: f"{match.group('prefix')}<REDACTED_SECRET>", text)
    for token_re in _KNOWN_TOKEN_RES:
        text = token_re.sub("<REDACTED_SECRET>", text)

    replacements: list[tuple[str, str]] = []
    if workspace_root:
        replacements.extend((variant, "<WORKSPACE>") for variant in _path_variants(workspace_root))
    if cwd and os.path.normcase(cwd) != os.path.normcase(workspace_root):
        replacements.extend((variant, "<CWD>") for variant in _path_variants(cwd))
    home = str(Path.home())
    replacements.extend((variant, "<HOME>") for variant in _path_variants(home))
    hostname = platform.node().strip()
    if len(hostname) >= 2:
        replacements.append((hostname, "<HOST>"))
    for raw, placeholder in sorted(replacements, key=lambda item: len(item[0]), reverse=True):
        text = _replace_literal(text, raw, placeholder)

    text = _redact_workspace_name(text, workspace_root)
    text = _URL_AUTHORITY_RE.sub(lambda match: f"{match.group('scheme')}<URL_HOST>", text)
    text = _WINDOWS_USER_PATH_RE.sub(lambda match: f"{match.group('prefix')}<USER>", text)
    text = _POSIX_USER_PATH_RE.sub(lambda match: f"{match.group('prefix')}<USER>", text)
    text = _UNC_PATH_RE.sub("<UNC_PATH>", text)
    text = _WINDOWS_ABSOLUTE_PATH_RE.sub("<ABSOLUTE_PATH>", text)
    text = _POSIX_ABSOLUTE_PATH_RE.sub(_redact_posix_path, text)

    if _PRIVATE_KEY_RE.search(text) or any(token_re.search(text) for token_re in _KNOWN_TOKEN_RES):
        raise GuardReportError("A likely secret remained after redaction; no public report was generated.")
    return text


def _default_shell_name() -> str:
    shell = os.environ.get("COMSPEC", "").strip() or os.environ.get("SHELL", "").strip()
    if not shell:
        return "unknown"
    return ntpath.basename(shell.replace("/", "\\")) or "unknown"


def _operating_system_label() -> str:
    values = [platform.system(), platform.release(), platform.machine()]
    return " ".join(value for value in values if value).strip() or "unknown"


def _case_fingerprint(command: str, expected: str, actual: str, rule_ids: Sequence[str]) -> str:
    canonical = {
        "schema": REPORT_SCHEMA,
        "command": " ".join(command.split()),
        "expected": expected,
        "actual": actual,
        "rule_ids": sorted(rule_ids),
    }
    digest = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return f"CHT-GUARD-{digest[:16].upper()}"


def build_guard_case_report(
    assessment: GuardAssessment,
    *,
    expected: str,
    agent_host: str = "manual-cli",
    shell: str | None = None,
    helpful: str = "unsure",
    custom_redactions: Sequence[str] = (),
    generated_at: datetime | None = None,
) -> GuardCaseReport:
    """Build a redacted report without retaining raw assessment fields in the result."""

    expected = expected.strip().lower()
    if expected not in {"allow", "ask", "block"}:
        raise GuardReportError("Expected decision must be ALLOW, ASK, or BLOCK.")
    helpful = helpful.strip().lower()
    if helpful not in {"yes", "no", "unsure"}:
        raise GuardReportError("Helpful must be yes, no, or unsure.")

    context = {
        "cwd": assessment.cwd,
        "workspace_root": assessment.workspace_root,
        "custom_redactions": custom_redactions,
    }
    command = redact_guard_text(assessment.command, **context)
    redacted_cwd = redact_guard_text(assessment.cwd, **context)
    redacted_workspace = redact_guard_text(assessment.workspace_root, **context)
    targets = tuple(redact_guard_text(target, **context) for target in assessment.targets)
    reasons = tuple(redact_guard_text(reason, **context) for reason in assessment.reasons)
    safe_next_steps = tuple(redact_guard_text(step, **context) for step in assessment.safe_next_steps)
    redacted_host = redact_guard_text(agent_host or "manual-cli", **context)
    redacted_shell = redact_guard_text(shell or _default_shell_name(), **context)

    timestamp = generated_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    timestamp = timestamp.astimezone(timezone.utc)

    return GuardCaseReport(
        schema=REPORT_SCHEMA,
        case_fingerprint=_case_fingerprint(command, expected, assessment.decision, assessment.rule_ids),
        generated_at_utc=timestamp.isoformat(timespec="seconds").replace("+00:00", "Z"),
        cyberhuatuo_version=__version__,
        agent_host=redacted_host,
        operating_system=_operating_system_label(),
        shell=redacted_shell,
        expected=expected,
        actual=assessment.decision,
        matches_expected=assessment.decision == expected,
        helpful=helpful,
        risk=assessment.risk,
        rule_ids=assessment.rule_ids,
        reversible=assessment.reversible,
        command=command,
        cwd=redacted_cwd,
        workspace_root=redacted_workspace,
        targets=targets,
        reasons=reasons,
        safe_next_steps=safe_next_steps,
    )


def _fenced_text(value: str) -> str:
    longest_run = max((len(match.group(0)) for match in re.finditer(r"`+", value)), default=0)
    fence = "`" * max(3, longest_run + 1)
    return f"{fence}text\n{value}\n{fence}"


def format_guard_case_report(report: GuardCaseReport) -> str:
    """Format a public-reviewable Markdown case report."""

    lines = [
        "# CyberHuaTuo Guard Case Report",
        "",
        "> Local redacted preview. Review every field before sharing it publicly.",
        "",
        f"- Schema: `{report.schema}`",
        f"- Case fingerprint: `{report.case_fingerprint}`",
        f"- Generated at: `{report.generated_at_utc}`",
        f"- CyberHuaTuo: `{report.cyberhuatuo_version}`",
        f"- Agent host: `{report.agent_host}`",
        f"- OS: `{report.operating_system}`",
        f"- Shell: `{report.shell}`",
        "- Command executed by this report: **no**",
        f"- Expected: **{report.expected.upper()}**",
        f"- Actual: **{report.actual.upper()}**",
        f"- Expected match: **{'yes' if report.matches_expected else 'no'}**",
        f"- Helpful: **{report.helpful}**",
        f"- Risk: **{report.risk.upper()}**",
        f"- Rules: **{', '.join(report.rule_ids) or 'none'}**",
        f"- Reversible: **{'yes' if report.reversible else 'no'}**",
        "",
        "## Redacted command",
        "",
        _fenced_text(report.command),
        "",
        "## Redacted context",
        "",
        f"- CWD: `{report.cwd}`",
        f"- Workspace: `{report.workspace_root}`",
    ]
    if report.targets:
        lines.append(f"- Parsed targets: {', '.join(f'`{target}`' for target in report.targets)}")
    else:
        lines.append("- Parsed targets: none")
    lines.extend(["", "## Reasons"])
    lines.extend(f"- {reason}" for reason in report.reasons)
    lines.extend(["", "## Safer prescription"])
    lines.extend(f"{index}. {step}" for index, step in enumerate(report.safe_next_steps, 1))
    lines.extend(
        [
            "",
            "## Privacy and safety",
            "",
            "- Generated locally; report generation performs no network request or public upload.",
            "- The reviewed command was not executed.",
            "- Automatic redaction reduces risk but cannot identify every private business term or repository name.",
            "- Recheck the preview and use `--redact <literal>` for any additional private identifier before sharing.",
            "- Security-relevant Hook, parser, or wrapper bypasses belong in private vulnerability reporting.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_guard_case_report(path: str | Path, content: str, *, overwrite: bool = False) -> Path:
    """Write only the redacted report, refusing implicit overwrite and existing symlinks."""

    destination = Path(path).expanduser()
    if destination.exists() and destination.is_symlink():
        raise GuardReportError(f"Refusing to write a Guard report through a symlink: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)

    if not overwrite:
        try:
            with destination.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError as exc:
            raise GuardReportError(
                f"Report already exists: {destination}. Use --overwrite-report only after reviewing the existing file."
            ) from exc
        except Exception:
            if destination.exists():
                destination.unlink(missing_ok=True)
            raise
    else:
        temporary_path: Path | None = None
        try:
            descriptor, raw_path = tempfile.mkstemp(
                dir=destination.parent,
                prefix=f".{destination.name}.",
                suffix=".tmp",
                text=True,
            )
            temporary_path = Path(raw_path)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, destination)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink(missing_ok=True)

    with suppress(OSError):
        destination.chmod(0o600)
    return destination.resolve(strict=False)
