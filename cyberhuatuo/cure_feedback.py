"""Privacy-first local feedback evidence for prescription review."""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .case_quality import audit_case, is_reviewable_url
from .config import config
from .indexer import scan_cases

FEEDBACK_OUTCOMES = ("yes", "partial", "no")


def _default_feedback_path() -> Path:
    return Path(config.ROOT_DIR) / ".user_data" / "cure-feedback.jsonl"


def record_cure_feedback(
    case_id: str,
    outcome: str,
    *,
    verification: str = "",
    verification_method: str = "",
    evidence_url: str = "",
    contributor: str = "",
    cases: Iterable[dict[str, Any]] | None = None,
    feedback_path: Path | None = None,
) -> dict[str, Any]:
    """Append one case-bound local feedback event without storing the original query."""
    normalized_case_id = str(case_id or "").strip()
    normalized_outcome = str(outcome or "").strip().casefold()
    if normalized_outcome not in FEEDBACK_OUTCOMES:
        raise ValueError(f"outcome must be one of: {', '.join(FEEDBACK_OUTCOMES)}")

    case_list = list(cases if cases is not None else scan_cases())
    matched_case = next((case for case in case_list if str(case.get("id", "")) == normalized_case_id), None)
    if matched_case is None:
        raise ValueError(f"Unknown case ID: {normalized_case_id}")

    evidence_url = str(evidence_url or "").strip()
    if evidence_url and not is_reviewable_url(evidence_url):
        raise ValueError("evidence_url must be a non-placeholder HTTP(S) URL")

    quality = audit_case(matched_case.get("metadata", {}), matched_case.get("content", ""))
    verification = str(verification or "").strip()
    verification_method = str(verification_method or "").strip()
    event = {
        "schema_version": 1,
        "event_id": str(uuid.uuid4()),
        "case_id": normalized_case_id,
        "outcome": normalized_outcome,
        "quality_status_at_feedback": quality.effective_status,
        "verification": verification,
        "verification_method": verification_method,
        "evidence_url": evidence_url,
        "contributor": str(contributor or "").strip(),
        "reviewable": bool(
            normalized_outcome in {"yes", "partial"}
            and verification
            and verification_method
            and evidence_url
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "privacy": "local-only; original query and traceback are not stored",
    }

    path = Path(feedback_path) if feedback_path is not None else _default_feedback_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return event
