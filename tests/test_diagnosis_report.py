import json

from cyberhuatuo.diagnosis import build_diagnosis_prompt
from cyberhuatuo.report import calculate_confidence, format_standard_report
from cyberhuatuo.searcher import SearchResult

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility
    import tomli as tomllib


def test_readmes_keep_emergency_room_entry_before_worldbuilding():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    readme = (root / "README.md").read_text(encoding="utf-8")[:2500]
    readme_cn = (root / "README_CN.md").read_text(encoding="utf-8")[:2500]

    assert "Emergency Room: Cure First, Refine Later" in readme
    assert "Your agent is sick" in readme
    assert "agent-native" in readme
    assert "save_prescription" in readme
    assert "upload_prescription" in readme
    assert "assets/cli_emergency_diagnosis_demo.gif" in readme
    assert "cyberhuatuo cure" in readme
    assert "python -m pip install -U langchain-openai" in readme

    assert "急诊入口：先救活，再炼方" in readme_cn
    assert "你的 Agent 生病了" in readme_cn
    assert "最轻的入口" in readme_cn
    assert "save_prescription" in readme_cn
    assert "upload_prescription" in readme_cn
    assert "assets/cli_emergency_diagnosis_demo.gif" in readme_cn
    assert "cyberhuatuo cure" in readme_cn
    assert "python -m pip install -U langchain-openai" in readme_cn

    assert (root / "assets" / "cli_emergency_diagnosis_demo.gif").is_file()
    assert (root / "assets" / "cli_emergency_diagnosis_demo.cast").is_file()


def test_public_marketplace_copy_leads_with_mcp_self_rescue():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    codex_catalog = json.loads((root / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
    codex_plugin = json.loads((root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    claude_catalog = json.loads((root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))

    assert "self-rescue" in project["description"]
    assert "MCP" in project["description"]
    assert "tracebacks" in project["description"]
    assert "exact fixes" in project["description"]
    assert "save/upload" in project["description"]

    codex_listing = codex_catalog["plugins"][0]["interface"]
    assert "agent gets sick" in codex_listing["shortDescription"]
    assert "HuaTuo" in codex_listing["shortDescription"]
    assert "coding agent gets sick" in codex_listing["longDescription"]
    assert "reusable prescription" in codex_listing["longDescription"]

    assert "agent gets sick" in codex_plugin["interface"]["shortDescription"]
    assert "keep the cure" in codex_plugin["interface"]["shortDescription"]
    assert "diagnose" in codex_plugin["interface"]["defaultPrompt"][0]
    assert "apply the cure" in codex_plugin["interface"]["defaultPrompt"][0]
    assert "Save this solved issue" in codex_plugin["interface"]["defaultPrompt"][2]

    claude_listing = claude_catalog["plugins"][0]["description"]
    assert "coding agent gets sick" in claude_listing
    assert "traceback" in claude_listing
    assert "apply the cure" in claude_listing
    assert "save or upload" in claude_listing
    assert "First Soul Ring" in claude_listing


def test_diagnosis_report_prescribes_top_case_when_llm_key_is_missing():
    case_content = """---
id: langchain-import-chatmodel-001
---

## Symptom

ImportError after upgrading LangChain.

## Prescriptions

### Prescription 1: use the split integration package

```bash
pip install langchain-openai
```

```python
from langchain_openai import ChatOpenAI
```

### Prescription 2: temporary compatibility layer

```bash
pip install langchain-community
```
"""

    report = format_standard_report(
        query="ImportError: cannot import name 'ChatOpenAI' from 'langchain'",
        results=[
            SearchResult(
                case_id="langchain-import-chatmodel-001",
                title="LangChain 0.3 ChatOpenAI import failure",
                title_en="ChatOpenAI import error after LangChain 0.3",
                framework="langchain",
                severity="medium",
                complexity="simple",
                tags="import-error,breaking-change",
                filepath="cases/langchain/import-error/chatmodel-import-001.md",
                distance=0.2,
                relevance=82.0,
                content=case_content,
                source="常驻",
                quality_status="gold",
                source_url="https://docs.langchain.com/oss/python/integrations/chat/openai",
                verified_at="2026-07-14",
            )
        ],
        diagnosis_text="⚠️ 未配置 LLM API Key，无法使用 AI 诊断功能。",
        framework="langchain",
    )

    assert "## [PRESCRIBE] Knowledge-Base Cure" in report
    assert "LLM diagnosis is unavailable" in report
    assert "pip install langchain-openai" in report
    assert "from langchain_openai import ChatOpenAI" in report
    assert "pip install langchain-community" not in report
    assert "| 1 | LangChain 0.3 ChatOpenAI import failure | langchain | 82% | medium | Gold | Permanent |" in report


def test_diagnosis_prompt_and_report_preserve_quality_boundaries():
    draft = SearchResult(
        case_id="draft-case-001",
        title="Unverified draft",
        title_en="Unverified draft",
        framework="general-ai",
        severity="high",
        complexity="moderate",
        tags="draft",
        filepath="cases/general-ai/draft.md",
        distance=0.1,
        relevance=90.0,
        content="## Prescriptions\n\nDelete a system directory.",
        source="常驻",
        quality_status="draft",
    )

    prompt = build_diagnosis_prompt("system is slow", [draft])[1]["content"]
    assert "质量状态: draft" in prompt
    assert "Draft 只能作为未验证线索" in prompt

    report = format_standard_report(
        query="system is slow",
        results=[draft],
        diagnosis_text="⚠️ 未配置 LLM API Key，无法使用 AI 诊断功能。",
    )
    assert "## [PRESCRIBE] Knowledge-Base Cure" not in report
    assert "unverified Draft reference" in report
    assert "concrete cure" not in report
    assert "| 1 | Unverified draft | general-ai | 90% | high | Draft | Permanent |" in report


def test_confidence_counts_normalized_chinese_source_labels():
    permanent = SearchResult(
        case_id="case-001",
        title="Permanent case",
        title_en="Permanent case",
        framework="general-ai",
        severity="medium",
        complexity="simple",
        tags="test",
        filepath="cases/permanent.md",
        distance=1.0,
        relevance=50.0,
        content=None,
        source="常驻",
    )
    ephemeral = SearchResult(
        case_id="case-002",
        title="Ephemeral case",
        title_en="Ephemeral case",
        framework="general-ai",
        severity="medium",
        complexity="simple",
        tags="test",
        filepath="",
        distance=1.0,
        relevance=50.0,
        content=None,
        source="瞬时",
    )

    assert calculate_confidence([permanent, ephemeral]).score == 50
