"""Quality contract for public CyberHuaTuo prescriptions."""

from __future__ import annotations

import ipaddress
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import urlparse

QUALITY_STATUSES = ("draft", "reviewed", "gold")
TRUSTED_CURE_STATUSES = ("gold",)

_PLACEHOLDER_MARKERS = (
    "请补充",
    "todo",
    "tbd",
    "placeholder",
    "xxxxx",
    "example.com",
)
_SECTION_SUBTITLES = {
    "root cause analysis",
    "prescription",
    "prescriptions",
    "verification",
    "safety and rollback",
}


@dataclass(frozen=True)
class PrescriptionQuality:
    """Declared and effective quality for one prescription."""

    declared_status: str
    effective_status: str
    violations: tuple[str, ...]
    root_cause: str
    prescription: str
    verification: str
    safety: str

    @property
    def is_valid(self) -> bool:
        return not self.violations

    @property
    def is_trusted_cure(self) -> bool:
        return self.effective_status in TRUSTED_CURE_STATUSES


def extract_markdown_section(content: str, labels: Iterable[str]) -> str:
    """Return the body of the first level-two section matching any label."""
    wanted = tuple(label.casefold() for label in labels)
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", content, flags=re.MULTILINE))
    for index, match in enumerate(matches):
        heading = re.sub(r"[^\w\u4e00-\u9fff]+", " ", match.group(1)).casefold()
        if not any(label in heading for label in wanted):
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        section = content[start:end].strip()
        lines = section.splitlines()
        if lines:
            subtitle = re.sub(r"[^\w\u4e00-\u9fff]+", " ", lines[0]).strip().casefold()
            if subtitle in _SECTION_SUBTITLES or any(
                subtitle == label.rstrip("s") or subtitle.rstrip("s") == label.rstrip("s")
                for label in wanted
            ):
                section = "\n".join(lines[1:]).strip()
        return section
    return ""


def _is_substantive(value: str) -> bool:
    clean = value.strip()
    if len(clean) < 8:
        return False
    lowered = clean.casefold()
    return not any(marker in lowered for marker in _PLACEHOLDER_MARKERS)


def is_reviewable_url(value: str) -> bool:
    """Return whether a URL is an externally reviewable HTTP(S) reference."""
    parsed = urlparse((value or "").strip())
    hostname = (parsed.hostname or "").casefold().rstrip(".")
    if parsed.scheme not in {"http", "https"} or not hostname or parsed.username or parsed.password:
        return False
    placeholder_hosts = {
        "example.com", "example.org", "example.net", "localhost",
    }
    if (
        hostname in placeholder_hosts
        or hostname.endswith((".example.com", ".example.org", ".example.net", ".invalid", ".localhost", ".test"))
    ):
        return False
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return "." in hostname
    return not (address.is_private or address.is_loopback or address.is_reserved or address.is_unspecified)


def _valid_iso_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _future_iso_date(value: Any) -> bool:
    if not _valid_iso_date(value):
        return False
    return date.fromisoformat(str(value)) > date.today()


def _match_signatures(metadata: dict[str, Any]) -> list[str]:
    raw = metadata.get("match_signatures", [])
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if _is_substantive(str(item))]


def _evidence_urls(metadata: dict[str, Any]) -> list[str]:
    raw = metadata.get("evidence_urls", [])
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def audit_case(metadata: dict[str, Any], content: str) -> PrescriptionQuality:
    """Audit one case without inferring a higher status than it declares."""
    raw_status = str(metadata.get("quality_status", "draft") or "draft").strip().lower()
    declared_status = raw_status if raw_status in QUALITY_STATUSES else "draft"

    root_cause = extract_markdown_section(content, ("根因", "root cause"))
    prescription = extract_markdown_section(content, ("药方", "prescription", "fix"))
    verification = extract_markdown_section(content, ("验证", "verification"))
    safety = extract_markdown_section(content, ("风险", "回退", "safety", "rollback"))

    reviewed_violations: list[str] = []
    if not _is_substantive(root_cause):
        reviewed_violations.append("missing substantive root-cause section")
    if not _is_substantive(prescription):
        reviewed_violations.append("missing substantive prescription section")
    if not is_reviewable_url(str(metadata.get("source_url", ""))):
        reviewed_violations.append("missing reviewable source_url")
    if not _is_substantive(safety):
        reviewed_violations.append("missing substantive safety and rollback section")
    if not _valid_iso_date(metadata.get("reviewed_at")):
        reviewed_violations.append("missing valid reviewed_at date")
    elif _future_iso_date(metadata.get("reviewed_at")):
        reviewed_violations.append("reviewed_at date cannot be in the future")
    if not str(metadata.get("reviewed_by", "")).strip():
        reviewed_violations.append("missing reviewed_by")
    if not _match_signatures(metadata):
        reviewed_violations.append("missing substantive match_signatures")

    gold_violations = list(reviewed_violations)
    if not _is_substantive(verification):
        gold_violations.append("missing substantive verification section")
    if not _valid_iso_date(metadata.get("verified_at")):
        gold_violations.append("missing valid verified_at date")
    elif _future_iso_date(metadata.get("verified_at")):
        gold_violations.append("verified_at date cannot be in the future")
    if not str(metadata.get("verification_method", "")).strip():
        gold_violations.append("missing verification_method")
    evidence_urls = _evidence_urls(metadata)
    if not evidence_urls or any(not is_reviewable_url(url) for url in evidence_urls):
        gold_violations.append("evidence_urls must contain reviewable HTTP(S) URLs")

    if raw_status not in QUALITY_STATUSES:
        violations = (f"unknown quality_status: {raw_status}",)
        effective_status = "draft"
    elif declared_status == "gold" and gold_violations:
        violations = tuple(gold_violations)
        effective_status = "reviewed" if not reviewed_violations else "draft"
    elif declared_status == "reviewed" and reviewed_violations:
        violations = tuple(reviewed_violations)
        effective_status = "draft"
    else:
        violations = ()
        effective_status = declared_status

    return PrescriptionQuality(
        declared_status=declared_status,
        effective_status=effective_status,
        violations=violations,
        root_cause=root_cause,
        prescription=prescription,
        verification=verification,
        safety=safety,
    )


def audit_knowledge_base(cases: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Summarize effective quality levels for parsed cases."""
    counts = {status: 0 for status in QUALITY_STATUSES}
    invalid: list[dict[str, Any]] = []
    total = 0
    for case in cases:
        total += 1
        quality = audit_case(case.get("metadata", {}), case.get("content", ""))
        counts[quality.effective_status] += 1
        if quality.violations:
            invalid.append({
                "case_id": case.get("id", ""),
                "declared_status": quality.declared_status,
                "effective_status": quality.effective_status,
                "violations": list(quality.violations),
            })
    return {"total": total, "counts": counts, "invalid": invalid}
