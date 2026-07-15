"""Fast, offline-first prescription lookup for the CLI."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any

from .case_quality import PrescriptionQuality, audit_case
from .case_taxonomy import DISEASE_CATEGORIES, disease_category_label, normalize_disease_category
from .indexer import scan_cases


@dataclass(frozen=True)
class CureMatch:
    case_id: str
    title: str
    framework: str
    framework_version: str
    severity: str
    disease_category: str
    disease_category_label: str
    quality_status: str
    relevance: float
    root_cause: str
    prescription: str
    verification: str
    safety: str
    source_url: str
    evidence_urls: tuple[str, ...]
    verified_at: str

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence_urls"] = list(self.evidence_urls)
        data["trust_notice"] = trust_notice(self.quality_status)
        return data


def _tokens(text: str) -> set[str]:
    lowered = text.casefold()
    latin = set(re.findall(r"[a-z0-9][a-z0-9_.-]{1,}", lowered))
    cjk_runs = re.findall(r"[\u4e00-\u9fff]+", lowered)
    cjk = set()
    for run in cjk_runs:
        if len(run) == 1:
            cjk.add(run)
        else:
            cjk.update(run[index:index + 2] for index in range(len(run) - 1))
    return latin | cjk


_GENERIC_SIGNATURE_TOKENS = {
    "a", "an", "and", "at", "cannot", "error", "exception", "failed", "failure",
    "for", "from", "in", "import", "importerror", "invalid", "is", "line", "name",
    "of", "on", "the", "to", "with",
}


def _signature_values(case: dict[str, Any]) -> list[str]:
    metadata = case.get("metadata", {})
    raw = metadata.get("match_signatures", [])
    if isinstance(raw, str):
        raw = [raw]
    if isinstance(raw, list):
        signatures = [str(value).strip() for value in raw if str(value).strip()]
        if signatures:
            return signatures
    tags = metadata.get("tags", [])
    tag_text = " ".join(str(tag) for tag in tags) if isinstance(tags, list) else str(tags)
    return [
        str(metadata.get("title_en", "")),
        str(metadata.get("title", "")),
        tag_text,
    ]


def _relevance(query: str, case: dict[str, Any]) -> float:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0
    metadata = case.get("metadata", {})
    framework_tokens = _tokens(str(metadata.get("framework", "")))
    best = 0.0
    for signature in _signature_values(case):
        signature_tokens = _tokens(signature)
        if not signature_tokens:
            continue
        specific_tokens = signature_tokens - _GENERIC_SIGNATURE_TOKENS - framework_tokens
        if specific_tokens and not (specific_tokens & query_tokens):
            continue
        overlap = signature_tokens & query_tokens
        coverage = len(overlap) / len(signature_tokens)
        specific_coverage = (
            len(specific_tokens & query_tokens) / len(specific_tokens)
            if specific_tokens else coverage
        )
        score = (coverage * 60.0) + (specific_coverage * 40.0)
        best = max(best, score)
    return round(min(100.0, best), 1)


def trust_notice(status: str) -> str:
    notices = {
        "gold": "Gold verified cure.",
        "reviewed": "Reviewed candidate; verify before applying.",
        "draft": "Unverified draft; reference only.",
    }
    return notices.get(str(status).strip().lower(), "Unverified result; reference only.")


def _collect_matches(
    query: str,
    *,
    statuses: set[str],
    framework: str | None,
    requested_category: str,
    min_relevance: float,
    cases: Iterable[dict[str, Any]],
) -> list[CureMatch]:
    matches: list[CureMatch] = []
    normalized_framework = str(framework or "").strip().casefold()
    for case in cases:
        metadata = case.get("metadata", {})
        if normalized_framework and str(metadata.get("framework", "")).strip().casefold() != normalized_framework:
            continue
        normalized_category = normalize_disease_category(metadata.get("disease_category"))
        if requested_category and normalized_category != requested_category:
            continue
        quality: PrescriptionQuality = audit_case(metadata, case.get("content", ""))
        if quality.effective_status not in statuses:
            continue
        relevance = _relevance(query, case)
        if relevance < min_relevance:
            continue
        raw_evidence = metadata.get("evidence_urls", [])
        if isinstance(raw_evidence, str):
            raw_evidence = [raw_evidence]
        evidence = tuple(str(url) for url in raw_evidence) if isinstance(raw_evidence, list) else ()
        matches.append(CureMatch(
            case_id=str(case.get("id", "")),
            title=str(metadata.get("title", "")),
            framework=str(metadata.get("framework", "unknown")),
            framework_version=str(metadata.get("framework_version", "")),
            severity=str(metadata.get("severity", "medium")),
            disease_category=normalized_category,
            disease_category_label=disease_category_label(normalized_category),
            quality_status=quality.effective_status,
            relevance=relevance,
            root_cause=quality.root_cause,
            prescription=quality.prescription,
            verification=quality.verification,
            safety=quality.safety,
            source_url=str(metadata.get("source_url", "")),
            evidence_urls=evidence,
            verified_at=str(metadata.get("verified_at", "")),
        ))
    matches.sort(key=lambda item: item.relevance, reverse=True)
    return matches


def find_cures(
    query: str,
    *,
    framework: str | None = None,
    disease_category: str | None = None,
    top_k: int = 1,
    min_relevance: float = 45.0,
    include_reviewed: bool | None = None,
    include_drafts: bool = False,
    gold_only: bool = False,
    cases: Iterable[dict[str, Any]] | None = None,
) -> list[CureMatch]:
    """Find Gold first, then one clearly labeled Reviewed candidate when needed."""
    requested_category = str(disease_category or "").strip().lower()
    if requested_category and requested_category not in DISEASE_CATEGORIES:
        return []
    case_list = list(cases if cases is not None else scan_cases())
    shared = {
        "query": query,
        "framework": framework,
        "requested_category": requested_category,
        "min_relevance": min_relevance,
        "cases": case_list,
    }
    gold = _collect_matches(statuses={"gold"}, **shared)
    if gold:
        return gold[:max(1, top_k)]
    if gold_only:
        return []
    if include_reviewed is not False:
        reviewed = _collect_matches(statuses={"reviewed"}, min_relevance=max(60.0, min_relevance), **{
            key: value for key, value in shared.items() if key != "min_relevance"
        })
        if reviewed:
            return reviewed[:1]
    if include_drafts:
        drafts = _collect_matches(statuses={"draft"}, **shared)
        return drafts[:max(1, top_k)]
    return []


def format_cure(match: CureMatch) -> str:
    """Format a cure as an action-first terminal result."""
    safety = match.safety or (
        f"适用版本: {match.framework_version or '见药方正文'}\n\n"
        f"风险级别: {match.severity}\n\n未声明自动系统改动；执行前请在当前项目环境中验证。"
    )
    evidence = list(dict.fromkeys([match.source_url, *match.evidence_urls]))
    evidence_lines = "\n".join(f"- {url}" for url in evidence if url) or "- 未提供"
    heading = {
        "gold": "GOLD",
        "reviewed": "REVIEWED CANDIDATE - VERIFY BEFORE APPLYING",
        "draft": "DRAFT - UNVERIFIED REFERENCE ONLY",
    }.get(match.quality_status, "UNVERIFIED")
    return "\n".join([
        f"# [{heading}] {match.title}",
        "",
        (
            f"病例: {match.case_id} | 科室: {match.disease_category_label} "
            f"({match.disease_category}) | 框架: {match.framework} | 匹配度: {match.relevance:.1f}%"
        ),
        "",
        "## 病灶 / Root Cause",
        match.root_cause,
        "",
        "## 药方 / Exact Fix",
        match.prescription,
        "",
        "## 验证 / Verification",
        match.verification or "该候选药方尚无可复现验证记录。",
        "",
        "## 风险与回退 / Safety",
        safety,
        "",
        f"## 证据 / Evidence (verified {match.verified_at or 'unknown'})",
        evidence_lines,
        "",
        "## 反馈 / Local Feedback",
        (
            f"确认后可记录本地证据：`cyberhuatuo cure-feedback {match.case_id} "
            "yes|partial|no --verification \"<result>\" --verification-method \"<method>\"`"
        ),
        "不会上传原始报错，也不会自动执行药方。",
    ])


def cure_result_json(matches: list[CureMatch]) -> str:
    return json.dumps({"matches": [match.as_dict() for match in matches]}, ensure_ascii=False, indent=2)
