import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator, FormatChecker

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility
    import tomli as tomllib

from cyberhuatuo.case_quality import audit_case, audit_knowledge_base
from cyberhuatuo.case_sync import CaseSyncer
from cyberhuatuo.case_taxonomy import (
    DISEASE_CATEGORIES,
    disease_category_label,
    infer_disease_category,
    normalize_disease_category,
)
from cyberhuatuo.config import _copy_bundled_knowledge_base
from cyberhuatuo.contributor import CaseSubmission, generate_case_markdown, save_case_file
from cyberhuatuo.cure import find_cures, format_cure
from cyberhuatuo.github_sync import count_contributor_cases
from cyberhuatuo.indexer import compute_case_manifest, scan_cases

ROOT = Path(__file__).resolve().parents[1]


def _gold_case() -> dict:
    return {
        "id": "langchain-import-chatmodel-001",
        "metadata": {
            "title": "ChatOpenAI import failure",
            "framework": "langchain",
            "framework_version": ">=1.0.0",
            "severity": "medium",
            "quality_status": "gold",
            "source_url": "https://docs.langchain.com/oss/python/integrations/chat/openai",
            "reviewed_at": "2026-07-14",
            "reviewed_by": "JinNing6",
            "verified_at": "2026-07-14",
            "verification_method": "isolated-import-test",
            "evidence_urls": ["https://pypi.org/project/langchain-openai/"],
            "match_signatures": [
                "ImportError: cannot import name ChatOpenAI from langchain",
                "from langchain import ChatOpenAI",
            ],
            "tags": ["import-error"],
        },
        "content": """## Root Cause

ChatOpenAI moved to the split langchain-openai integration package.

## Prescriptions

Install langchain-openai and import ChatOpenAI from langchain_openai.

## Verification

Run python -c and confirm the class name prints ChatOpenAI.

## Safety and Rollback

Restore the lockfile if dependency resolution fails.
""",
        "filepath": "cases/langchain/import-error/chatmodel-import-001.md",
        "content_sha256": "a" * 64,
    }


def test_quality_contract_does_not_infer_or_accept_invalid_gold():
    gold = _gold_case()
    quality = audit_case(gold["metadata"], gold["content"])
    assert quality.effective_status == "gold"
    assert quality.is_trusted_cure is True

    invalid_metadata = dict(gold["metadata"], evidence_urls=[])
    invalid = audit_case(invalid_metadata, gold["content"])
    assert invalid.declared_status == "gold"
    assert invalid.effective_status == "reviewed"
    assert "evidence_urls must contain reviewable HTTP(S) URLs" in invalid.violations

    legacy = audit_case({}, gold["content"])
    assert legacy.declared_status == "draft"
    assert legacy.effective_status == "draft"

    placeholder = dict(gold["metadata"], source_url="https://docs.example.org/chat-openai")
    placeholder_quality = audit_case(placeholder, gold["content"])
    assert placeholder_quality.effective_status == "draft"
    assert "missing reviewable source_url" in placeholder_quality.violations

    future = dict(gold["metadata"], verified_at="2999-01-01")
    future_quality = audit_case(future, gold["content"])
    assert future_quality.effective_status == "reviewed"
    assert "verified_at date cannot be in the future" in future_quality.violations

    missing_review = dict(gold["metadata"])
    missing_review.pop("reviewed_by")
    missing_review_quality = audit_case(missing_review, gold["content"])
    assert missing_review_quality.effective_status == "draft"
    assert "missing reviewed_by" in missing_review_quality.violations


def test_public_library_has_explicit_quality_states_and_valid_schema():
    cases = scan_cases(ROOT / "cases")
    report = audit_knowledge_base(scan_cases(ROOT / "cases"))
    assert report["total"] >= 53
    assert report["invalid"] == []

    expected_trusted = {
        "langchain-import-chatmodel-001": "gold",
        "general-ai-fastapi-contract-005": "reviewed",
        "general-ai-jsonl-bom-001": "reviewed",
        "general-ai-sys-modules-isolation-002": "reviewed",
        "general-ai-binary-credential-003": "reviewed",
        "general-ai-windows-atomic-004": "reviewed",
        "mcp-daemon-runtime-state-005": "reviewed",
        "ml-ops-d1-schema-drift-001": "reviewed",
        "platform-agent-windows-pid-001": "reviewed",
    }
    effective = {
        case["id"]: audit_case(case["metadata"], case["content"]).effective_status
        for case in cases
    }
    assert expected_trusted.items() <= effective.items()

    schema = json.loads((ROOT / "schema" / "case.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    failures = {
        case["id"]: [error.message for error in validator.iter_errors(case["metadata"])]
        for case in cases
        if list(validator.iter_errors(case["metadata"]))
    }
    assert failures == {}


def test_disease_taxonomy_is_stable_and_new_drafts_are_inferred():
    assert normalize_disease_category("DATA-AND-SERIALIZATION") == "data-and-serialization"
    assert normalize_disease_category("legacy-unknown") == "other"
    assert disease_category_label("data-and-serialization") == "数据与序列化科"
    assert infer_disease_category(["jsonl", "bom"], "line 1 invalid JSON") == "data-and-serialization"
    assert "agent-and-tooling" in DISEASE_CATEGORIES


def test_historical_incident_cases_are_reviewed_and_category_filterable():
    cases = scan_cases(ROOT / "cases")
    reviewed = [
        case for case in cases
        if audit_case(case["metadata"], case["content"]).effective_status == "reviewed"
    ]
    assert len(reviewed) == 8
    assert all(case["metadata"]["case_origin"] == "maintainer-incident" for case in reviewed)
    assert all(case["metadata"]["origin_skill"] for case in reviewed)
    assert all(case["metadata"]["disease_category"] in DISEASE_CATEGORIES for case in reviewed)

    bom_case = next(case for case in reviewed if case["id"] == "general-ai-jsonl-bom-001")
    query = "Unexpected UTF-8 BOM JSONL line 1 invalid JSON"
    matches = find_cures(
        query,
        disease_category="data-and-serialization",
        cases=[bom_case],
    )
    assert len(matches) == 1
    assert matches[0].quality_status == "reviewed"
    assert matches[0].disease_category_label == "数据与序列化科"
    assert "科室: 数据与序列化科" in format_cure(matches[0])
    assert find_cures(
        query,
        disease_category="security-and-credentials",
        cases=[bom_case],
    ) == []
    assert find_cures(query, gold_only=True, cases=[bom_case]) == []
    assert find_cures("Unexpected UTF-8 BOM", cases=[bom_case])[0].case_id == "general-ai-jsonl-bom-001"


def test_fast_cure_returns_gold_and_rejects_unrelated_queries():
    cases = [_gold_case()]
    matches = find_cures(
        "ImportError ChatOpenAI from langchain",
        framework="langchain",
        cases=cases,
    )
    assert len(matches) == 1
    assert matches[0].quality_status == "gold"
    output = format_cure(matches[0])
    assert "## 病灶 / Root Cause" in output
    assert "## 药方 / Exact Fix" in output
    assert "## 验证 / Verification" in output
    assert "## 风险与回退 / Safety" in output

    assert find_cures("C盘空间不足", cases=cases) == []


def test_fast_cure_uses_explicit_signatures_and_handles_long_tracebacks():
    cases = [_gold_case()]
    unrelated = [
        "ImportError: cannot import name BaseModel from pydantic",
        "ImportError: cannot import name AgentExecutor from langchain.agents",
        "HTTP 401 invalid api key openai",
    ]
    assert all(find_cures(query, cases=cases) == [] for query in unrelated)

    long_traceback = "\n".join([
        "Traceback (most recent call last):",
        *[f'  File "worker_{index}.py", line {index}, in run' for index in range(200)],
        "ImportError: cannot import name 'ChatOpenAI' from 'langchain'",
    ])
    matches = find_cures(long_traceback, framework=" LANGCHAIN ", cases=cases)
    assert len(matches) == 1
    assert matches[0].case_id == "langchain-import-chatmodel-001"


def test_mcp_verified_cure_uses_gold_first_then_reviewed_fallback():
    from cyberhuatuo.mcp_server import verified_cure

    output = verified_cure(
        "ImportError: cannot import name ChatOpenAI from langchain",
        framework="langchain",
    )
    assert "# [GOLD] LangChain 中 ChatOpenAI 导入失败" in output
    assert "python -m pip install -U langchain-openai" in output
    assert "未执行" not in output

    reviewed_output = verified_cure(
        "Unexpected UTF-8 BOM JSONL line 1 invalid JSON",
        disease_category="data-and-serialization",
    )
    assert "# [REVIEWED CANDIDATE - VERIFY BEFORE APPLYING]" in reviewed_output
    assert "科室: 数据与序列化科" in reviewed_output
    assert "cure-feedback general-ai-jsonl-bom-001" in reviewed_output

    strict_output = verified_cure(
        "Unexpected UTF-8 BOM JSONL line 1 invalid JSON",
        disease_category="data-and-serialization",
        gold_only=True,
    )
    assert "未找到达到当前质量门槛" in strict_output


def test_generated_submission_is_draft_with_verification_fields():
    content = generate_case_markdown(CaseSubmission(
        framework="langchain",
        title='Quoted: "title"',
        title_en="Quoted title",
        error_message="ModuleNotFoundError: package is not installed",
        root_cause="A real root cause with sufficient detail.",
        prescription="Apply the exact tested fix.",
        verification="Run pytest and observe one passing test.",
        verification_method="targeted-pytest",
        evidence_urls=["https://github.com/example/project/actions/1"],
        source_url="https://github.com/example/project/issues/1",
        safety="Only changes the isolated test fixture; revert the patch to roll back.",
    ), case_id="langchain-quoted-title-001")

    assert "quality_status: draft" in content
    assert "disease_category: dependency-and-version" in content
    assert "verification_method: targeted-pytest" in content
    assert "https://github.com/example/project/actions/1" in content
    assert "## ✅ 验证记录" in content
    assert "## ⚠️ 风险与回退" in content


def test_case_save_is_ascii_confined_and_never_overwrites(tmp_path, monkeypatch):
    from cyberhuatuo import contributor

    cases_dir = tmp_path / "cases"
    monkeypatch.setattr(contributor.config, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(contributor.config, "CASES_DIR", cases_dir)

    submission = CaseSubmission(
        framework="langchain",
        title="中文报错药方",
        title_en="Chinese error prescription",
        prescription="Install the corrected package and rerun the failing import.",
    )
    first = save_case_file(submission)
    second = save_case_file(submission)

    assert first["case_id"] != second["case_id"]
    assert re.fullmatch(r"[a-z0-9]+-[a-z0-9-]+-[0-9]{3}", first["case_id"])
    assert Path(first["absolute_path"]).read_text(encoding="utf-8") != ""
    assert Path(second["absolute_path"]).is_file()

    escaped = tmp_path / "escaped"
    with pytest.raises(ValueError, match="framework"):
        save_case_file(CaseSubmission(
            framework="../escaped",
            title="escape",
            title_en="escape",
            prescription="must not write",
        ))
    assert not escaped.exists()


def test_cure_feedback_is_local_case_bound_evidence(tmp_path):
    from cyberhuatuo.cure_feedback import record_cure_feedback

    feedback_path = tmp_path / "feedback" / "cure-feedback.jsonl"
    event = record_cure_feedback(
        "langchain-import-chatmodel-001",
        "partial",
        verification="Import succeeds, but one downstream call still needs migration.",
        verification_method="isolated-import-test",
        evidence_url="https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/1",
        cases=[_gold_case()],
        feedback_path=feedback_path,
    )
    stored = json.loads(feedback_path.read_text(encoding="utf-8").strip())
    assert stored == event
    assert event["outcome"] == "partial"
    assert event["quality_status_at_feedback"] == "gold"
    assert event["reviewable"] is True
    assert "query" not in event

    with pytest.raises(ValueError, match="Unknown case ID"):
        record_cure_feedback(
            "missing-case-001",
            "yes",
            cases=[_gold_case()],
            feedback_path=feedback_path,
        )

    with pytest.raises(ValueError, match="outcome"):
        record_cure_feedback(
            "langchain-import-chatmodel-001",
            "maybe",
            cases=[_gold_case()],
            feedback_path=feedback_path,
        )


def test_draft_and_new_statusless_cases_do_not_count_but_bounded_legacy_cases_do(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text("""---
contributors:
  - github: alice
quality_status: draft
---
""", encoding="utf-8")
    legacy = tmp_path / "legacy.md"
    legacy.write_text("""---
contributors:
  - github: alice
created_at: 2026-07-14
---
""", encoding="utf-8")
    statusless_new = tmp_path / "statusless-new.md"
    statusless_new.write_text("""---
contributors:
  - github: alice
created_at: 2026-07-15
---
""", encoding="utf-8")
    reviewed = tmp_path / "reviewed.md"
    reviewed.write_text("""---
contributors:
  - github: alice
quality_status: reviewed
---
""", encoding="utf-8")

    assert count_contributor_cases("alice", cases_dir=tmp_path) == 2


def test_soul_ring_promotion_generates_reviewed_evidence_bearing_case():
    workflow = (ROOT / ".github" / "workflows" / "soul-ring-promote.yml").read_text(encoding="utf-8")
    assert 'parseIssueForm(issue.body || "", "Reviewable source or evidence URL")' in workflow
    assert 'String(issue.number).padStart(3, "0")' in workflow
    assert 'quality_status: "reviewed"' in workflow
    assert "reviewed_by:" in workflow
    assert "verification_method:" in workflow
    assert "evidence_urls:" in workflow
    assert "## Safety and Rollback" in workflow


def test_soul_ring_entrypoints_do_not_route_contributors_to_old_releases():
    files = [
        *(ROOT / ".github" / "workflows").glob("soul-ring-*.yml"),
        *(ROOT / ".github" / "ISSUE_TEMPLATE").glob("soul-ring-*.yml"),
    ]
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    expected = f"v{version}"
    stale = {}
    for path in files:
        tags = set(re.findall(r"v\d+\.\d+\.\d+", path.read_text(encoding="utf-8")))
        if tags - {expected}:
            stale[path.relative_to(ROOT).as_posix()] = sorted(tags - {expected})
    assert stale == {}


def test_bundled_sync_updates_managed_files_and_preserves_user_edits(tmp_path):
    source_cases = tmp_path / "bundle" / "cases"
    source_schema = tmp_path / "bundle" / "schema"
    target = tmp_path / "cache"
    source_cases.mkdir(parents=True)
    source_schema.mkdir(parents=True)
    (source_cases / "case.md").write_text("bundle-v1", encoding="utf-8")
    (source_schema / "case.schema.json").write_text('{"version": 1}', encoding="utf-8")

    _copy_bundled_knowledge_base(source_cases, source_schema, target)
    assert (target / "cases" / "case.md").read_text(encoding="utf-8") == "bundle-v1"

    (target / "cases" / "case.md").write_text("user-edit", encoding="utf-8")
    (source_cases / "case.md").write_text("bundle-v2", encoding="utf-8")
    (source_cases / "new.md").write_text("new-case", encoding="utf-8")
    (source_schema / "case.schema.json").write_text('{"version": 2}', encoding="utf-8")
    _copy_bundled_knowledge_base(source_cases, source_schema, target)

    assert (target / "cases" / "case.md").read_text(encoding="utf-8") == "user-edit"
    assert (target / "cases" / "new.md").read_text(encoding="utf-8") == "new-case"
    assert json.loads((target / "schema" / "case.schema.json").read_text(encoding="utf-8"))["version"] == 2


def test_runtime_case_sync_is_append_only(tmp_path, monkeypatch):
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir()
    existing = cases_dir / "existing.md"
    existing.write_text("locally-reviewed", encoding="utf-8")
    syncer = CaseSyncer(cases_dir=cases_dir, root_dir=tmp_path, sync_interval_minutes=5)
    captured = []

    monkeypatch.setattr(syncer, "_quick_check_changed", lambda: True)
    monkeypatch.setattr(syncer, "_fetch_remote_tree", lambda: {
        "cases/existing.md": "remote-different-sha",
        "cases/new.md": "remote-new-sha",
    })
    monkeypatch.setattr(syncer, "_compute_local_shas", lambda: {
        "cases/existing.md": "local-reviewed-sha",
    })
    monkeypatch.setattr(syncer, "_download_files", lambda paths: captured.extend(paths) or len(paths))

    assert syncer._do_sync() == 1
    assert captured == ["cases/new.md"]
    assert existing.read_text(encoding="utf-8") == "locally-reviewed"


def test_runtime_downloader_never_replaces_existing_case(tmp_path, monkeypatch):
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir()
    existing = cases_dir / "existing.md"
    existing.write_text("locally-reviewed", encoding="utf-8")
    syncer = CaseSyncer(cases_dir=cases_dir, root_dir=tmp_path, sync_interval_minutes=5)

    def unexpected_network(*_args, **_kwargs):
        raise AssertionError("existing files must be skipped before network access")

    monkeypatch.setattr("cyberhuatuo.case_sync.urllib.request.urlopen", unexpected_network)
    assert syncer._download_files(["cases/existing.md"]) == 0
    assert existing.read_text(encoding="utf-8") == "locally-reviewed"


def test_importing_mcp_server_does_not_start_case_sync_thread():
    source = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")
    before_main, main_body = source.split("def main():", 1)
    assert "_case_syncer.start_background_sync()" not in before_main
    assert "_case_syncer.start_background_sync()" in main_body


class _FakeCollection:
    def __init__(self, metadata):
        self.metadata = metadata
        self.rows = {}
        self.upsert_calls = 0

    def count(self):
        return len(self.rows)

    def get(self):
        return {"ids": list(self.rows)}

    def upsert(self, ids, documents, metadatas):
        self.upsert_calls += 1
        for case_id, document, metadata in zip(ids, documents, metadatas, strict=True):
            self.rows[case_id] = (document, metadata)

    def delete(self, ids):
        for case_id in ids:
            self.rows.pop(case_id, None)

    def modify(self, metadata):
        self.metadata = metadata


class _FakeClient:
    def __init__(self):
        self.collection = None

    def get_or_create_collection(self, name, metadata):
        if self.collection is None:
            self.collection = _FakeCollection(metadata)
        return self.collection


def _write_case(path: Path, case_id: str, title: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"""---
id: {case_id}
title: {title}
title_en: Test case
framework: langchain
severity: medium
complexity: simple
contributors:
  - github: alice
---

## Root Cause

A substantive root cause for this regression case.

## Prescriptions

A substantive exact prescription for this regression case.
""", encoding="utf-8")


def test_index_refreshes_when_case_manifest_changes(tmp_path, monkeypatch):
    from cyberhuatuo import indexer

    cases_dir = tmp_path / "cases"
    _write_case(cases_dir / "one.md", "langchain-index-one-001", "First index case")
    client = _FakeClient()
    monkeypatch.setattr(indexer.config, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(indexer.config, "CASES_DIR", cases_dir)
    monkeypatch.setattr(indexer.config, "CHROMA_DB_PATH", str(tmp_path / "chroma"))
    monkeypatch.setitem(sys.modules, "chromadb", SimpleNamespace(PersistentClient=lambda path: client))

    _, first_count = indexer.build_index()
    first_manifest = client.collection.metadata["case_manifest_sha256"]
    assert first_count == 1
    first_row = next(iter(client.collection.rows.values()))
    assert first_row[1]["disease_category"] == "other"
    assert first_row[1]["disease_category_label"] == "综合科"

    _write_case(cases_dir / "two.md", "langchain-index-two-002", "Second index case")
    _, second_count = indexer.build_index()
    assert second_count == 2
    assert client.collection.metadata["case_manifest_sha256"] != first_manifest
    assert client.collection.upsert_calls == 2


def test_manifest_includes_content_and_schema_version():
    first = _gold_case()
    second = dict(first, content_sha256="b" * 64)
    assert compute_case_manifest([first]) != compute_case_manifest([second])
