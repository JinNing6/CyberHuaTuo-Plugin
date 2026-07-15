from cyberhuatuo import api
from cyberhuatuo.searcher import SearchResult


def _result(status: str = "reviewed") -> SearchResult:
    return SearchResult(
        case_id="general-ai-jsonl-bom-001",
        title="JSONL BOM",
        title_en="JSONL BOM",
        framework="general-ai",
        severity="high",
        complexity="simple",
        tags="jsonl,bom",
        filepath="cases/general-ai/jsonl-bom-001.md",
        distance=0.2,
        relevance=82.0,
        content="## Root Cause\n\nUTF-8 BOM changes the first JSON token.",
        source="常驻",
        quality_status=status,
        source_url="https://docs.python.org/3/library/json.html#character-encodings",
        verified_at="",
        disease_category="data-and-serialization",
        disease_category_label="数据与序列化科",
    )


async def test_search_and_diagnose_api_expose_quality_metadata(monkeypatch):
    monkeypatch.setattr(api, "_chroma_client", object())
    monkeypatch.setattr(api, "search_cases", lambda **kwargs: [_result()])

    search = await api.api_search(
        q="Unexpected UTF-8 BOM",
        framework=None,
        severity=None,
        complexity=None,
        top_k=5,
    )
    item = search["results"][0]
    assert item["quality_status"] == "reviewed"
    assert item["source_url"].startswith("https://docs.python.org/")
    assert item["disease_category"] == "data-and-serialization"
    assert item["trust_notice"] == "Reviewed candidate; verify before applying."

    async def fake_diagnose(*args, **kwargs):
        return "diagnosis"

    monkeypatch.setattr(api, "diagnose", fake_diagnose)
    diagnosis = await api.api_diagnose(
        q="Unexpected UTF-8 BOM",
        framework=None,
        api_key=None,
        provider=None,
        model=None,
    )
    matched = diagnosis["matched_cases"][0]
    assert matched["quality_status"] == "reviewed"
    assert matched["trust_notice"] == "Reviewed candidate; verify before applying."


async def test_cure_api_uses_reviewed_fallback_and_gold_only(monkeypatch):
    reviewed = _result()

    from cyberhuatuo.cure import CureMatch

    match = CureMatch(
        case_id=reviewed.case_id,
        title=reviewed.title,
        framework=reviewed.framework,
        framework_version="Python 3.10+",
        severity=reviewed.severity,
        disease_category=reviewed.disease_category,
        disease_category_label=reviewed.disease_category_label,
        quality_status="reviewed",
        relevance=90.0,
        root_cause="UTF-8 BOM changes the first JSON token.",
        prescription="Read the first line with utf-8-sig.",
        verification="Parse the JSONL and assert the first record remains.",
        safety="Read-only parsing change; revert the decoder if needed.",
        source_url=reviewed.source_url,
        evidence_urls=(),
        verified_at="",
    )

    def fake_find_cures(*args, **kwargs):
        return [] if kwargs.get("gold_only") else [match]

    monkeypatch.setattr("cyberhuatuo.cure.find_cures", fake_find_cures)
    fallback = await api.api_cure(
        q="Unexpected UTF-8 BOM",
        framework=None,
        disease_category=None,
        gold_only=False,
        top_k=1,
    )
    assert fallback["matches"][0]["quality_status"] == "reviewed"
    assert fallback["matches"][0]["trust_notice"] == "Reviewed candidate; verify before applying."

    strict = await api.api_cure(
        q="Unexpected UTF-8 BOM",
        framework=None,
        disease_category=None,
        gold_only=True,
        top_k=1,
    )
    assert strict["matches"] == []
