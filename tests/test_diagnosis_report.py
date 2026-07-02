import json

from cyberhuatuo.report import format_standard_report
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

    assert "Emergency Room: Paste The Traceback First" in readme
    assert "AI Agent Error Doctor" in readme
    assert "assets/cli_emergency_diagnosis_demo.gif" in readme
    assert "pip install langchain-openai" in readme

    assert "急诊入口：先粘贴报错" in readme_cn
    assert "AI Agent 报错急诊室" in readme_cn
    assert "assets/cli_emergency_diagnosis_demo.gif" in readme_cn
    assert "pip install langchain-openai" in readme_cn

    assert (root / "assets" / "cli_emergency_diagnosis_demo.gif").is_file()
    assert (root / "assets" / "cli_emergency_diagnosis_demo.cast").is_file()


def test_public_marketplace_copy_leads_with_traceback_diagnosis():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    codex_catalog = json.loads((root / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
    codex_plugin = json.loads((root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    claude_catalog = json.loads((root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))

    assert "tracebacks" in project["description"]
    assert "root cause" in project["description"]
    assert "exact fixes" in project["description"]

    codex_listing = codex_catalog["plugins"][0]["interface"]
    assert "tracebacks" in codex_listing["shortDescription"]
    assert "exact fixes" in codex_listing["shortDescription"]
    assert "First Soul Ring" in codex_listing["longDescription"]

    assert "Paste tracebacks" in codex_plugin["interface"]["shortDescription"]
    assert "root cause" in codex_plugin["interface"]["defaultPrompt"][0]

    claude_listing = claude_catalog["plugins"][0]["description"]
    assert "tracebacks" in claude_listing
    assert "exact fixes" in claude_listing
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
    assert "| 1 | LangChain 0.3 ChatOpenAI import failure | langchain | 82% | medium | Permanent |" in report
