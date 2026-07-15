"""
CyberHuaTuo 药方贡献生成器
帮助开发者快速生成规范格式的病例文件
"""

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path
from typing import Any

import litellm
import yaml

from .case_taxonomy import infer_disease_category, normalize_disease_category
from .config import config
from .doc_sources import get_agent_framework_keys

# 框架枚举值（从 doc_sources 动态获取 Agent 框架列表）
FRAMEWORKS = get_agent_framework_keys()

# 严重性枚举
SEVERITIES = ["low", "medium", "high", "critical"]

# 复杂度枚举
COMPLEXITIES = ["simple", "moderate", "complex", "extreme"]

# 复杂度对应的 emoji
COMPLEXITY_EMOJI = {
    "simple": "🟢",
    "moderate": "🟡",
    "complex": "🔴",
    "extreme": "⚫",
}


@dataclass
class CaseSubmission:
    """用户提交的药方数据"""
    framework: str
    title: str
    title_en: str = ""
    error_message: str = ""
    symptom: str = ""
    root_cause: str = ""
    prescription: str = ""
    severity: str = "medium"
    complexity: str = "moderate"
    tags: list[str] = field(default_factory=list)
    framework_version: str = ""
    language: str = "python"
    contributor_github: str = "anonymous"
    source_url: str = ""
    verification: str = ""
    verification_method: str = ""
    evidence_urls: list[str] = field(default_factory=list)
    disease_category: str = ""
    safety: str = ""


async def smart_extract_contribution(
    issue_text: str,
    prescription: str,
    framework_hint: str = "auto",
    source_url: str = "",
    api_key: str = None,
    provider: str = "openai"
) -> dict[str, Any]:
    """
    使用 LLM 自动提取诊断病例所需的详细信息
    """
    system_prompt = "你是一个资深的高星炼丹师和程序员专家，正在整理一份《赛博华佗》的 AI 技术纠错药方。"
    user_prompt = f"""
下面是用户提交的极简报错和修复记录，你需要推断并提取出所有必须的结构化字段。

用户遇到的问题（症状/报错）：
{issue_text}

用户的解决方案（药方）：
{prescription}

用户提示的框架：{framework_hint}
参考链接：{source_url}

请输出纯合法的 JSON 内容，不要包含任何 Markdown code block 头尾包裹！
返回字段说明：
- "framework": 如果用户提示了非 auto 框架，请尊重。如果是 auto，请根据代码识别归类出具体框架或工具名（如 langchain, pytorch, transformers, crewai, openai-sdk, fastapi 等小写短名）。覆盖范围包括 AI Agent 框架、LLM SDK、深度学习框架、ML 工具、MLOps 工具等所有 AI 相关技术栈。
- "title": 中文问题标题，20字内简洁有力。
- "title_en": 匹配的英文问题标题。
- "symptom": 症状详细描述（基于输入总结提炼清晰的现象）。
- "error_message": 提取出的纯报错日志或 Traceback（若无也可适当放空）。
- "root_cause": 你根据经验推断的根本原因分析。
- "prescription": 使用 Markdown 格式详细描述修复方案，尽量给出带有 diff 标志的代码块。
- "severity": 只能是 "low", "medium", "high", "critical" 之一。
- "complexity": 只能是 "simple", "moderate", "complex", "extreme" 之一。
- "tags": ["tag1", "tag2"]（2-4个英文或中文标签串）。

一定要确保输出纯正 JSON 能够被 python 的 json.loads 成功解析！
"""
    model_name = "gpt-4o"
    if provider == "anthropic":
        model_name = "claude-3-5-sonnet-20241022"

    try:
        kwargs = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2
        }
        if api_key:
            kwargs["api_key"] = api_key

        response = await litellm.acompletion(**kwargs)
        raw_content = response.choices[0].message.content.strip()

        # Clean up any potential markdown formatting from the response
        if raw_content.startswith("```json"):
            raw_content = raw_content[7:]
        elif raw_content.startswith("```"):
            raw_content = raw_content[3:]
        if raw_content.endswith("```"):
            raw_content = raw_content[:-3]

        return json.loads(raw_content.strip())
    except Exception as e:
        print(f"Error extracting contribution via LLM: {e}")
        # Default fallback
        return {
            "framework": framework_hint if framework_hint and framework_hint.lower() != 'auto' else "unknown",
            "title": "自动分析失败请手动修改",
            "title_en": "Auto-generation failed",
            "symptom": issue_text,
            "error_message": "",
            "root_cause": "AI extraction failed.",
            "prescription": prescription,
            "severity": "medium",
            "complexity": "moderate",
            "tags": ["needs-review"]
        }


_FRAMEWORK_PATTERN = re.compile(r"^[a-z0-9_][a-z0-9_-]{0,63}$")


def normalize_framework(framework: str) -> str:
    """Normalize and validate a framework key before it reaches a filesystem path."""
    normalized = str(framework or "").strip().casefold()
    if not _FRAMEWORK_PATTERN.fullmatch(normalized) or normalized in {".", ".."}:
        raise ValueError(
            "framework must be a safe lowercase identifier containing only letters, digits, '-' or '_'"
        )
    return normalized


def _ascii_slug(*values: str) -> str:
    for value in values:
        normalized = unicodedata.normalize("NFKD", str(value or ""))
        ascii_value = normalized.encode("ascii", "ignore").decode("ascii").casefold()
        words = re.findall(r"[a-z0-9]+", ascii_value)
        if words:
            return "-".join(words[:6])[:64].strip("-")
    digest_source = "\x1f".join(str(value or "") for value in values)
    return f"case-{hashlib.sha256(digest_source.encode('utf-8')).hexdigest()[:12]}"


def generate_case_id(framework: str, title: str, title_en: str = "") -> str:
    """基于框架和标题生成唯一病例 ID"""
    framework = normalize_framework(framework)
    keyword_slug = _ascii_slug(title_en, title)

    # 获取同框架下的下一个序号
    framework_dir = config.CASES_DIR / framework
    existing_ids = set()
    if framework_dir.exists():
        for f in framework_dir.rglob("*.md"):
            if not f.name.startswith("_"):
                existing_ids.add(f.stem)
                existing_ids.add(f"{framework}-{f.stem}")

    # 寻找可用序号
    for seq in range(1, 1000):
        case_id = f"{framework}-{keyword_slug}-{seq:03d}"
        if case_id not in existing_ids:
            return case_id

    raise RuntimeError(f"No available case sequence for {framework}-{keyword_slug}")


def determine_category(tags: list[str], error_message: str) -> str:
    """根据标签和错误信息推断问题类别目录"""
    category_keywords = {
        "import-error": ["import", "module", "package"],
        "breaking-change": ["breaking", "migration", "upgrade", "deprecated"],
        "memory": ["memory", "leak", "oom", "out of memory"],
        "performance": ["slow", "performance", "timeout", "latency"],
        "tool-calling": ["tool", "function call", "mcp"],
        "agent-behavior": ["loop", "stuck", "infinite", "agent"],
        "authentication": ["api key", "auth", "token", "credential"],
        "configuration": ["config", "setup", "install", "environment"],
        "retrieval": ["retrieval", "rag", "vector", "embedding", "search"],
    }

    combined_text = " ".join(tags + [error_message]).lower()

    for category, keywords in category_keywords.items():
        if any(kw in combined_text for kw in keywords):
            return category

    return "general"


def generate_case_markdown(submission: CaseSubmission, case_id: str | None = None) -> str:
    """
    从用户提交数据生成规范的 YAML + Markdown 病例文件

    Returns:
        完整的 .md 文件内容
    """
    framework = normalize_framework(submission.framework)
    case_id = case_id or generate_case_id(framework, submission.title, submission.title_en)
    today = date.today().isoformat()
    disease_category = normalize_disease_category(submission.disease_category) if submission.disease_category else (
        infer_disease_category(
            submission.tags,
            submission.title,
            submission.title_en,
            submission.error_message,
            submission.symptom,
            submission.root_cause,
        )
    )

    metadata = {
        "id": case_id,
        "title": submission.title,
        "title_en": submission.title_en,
        "framework": framework,
        "framework_version": submission.framework_version,
        "language": submission.language,
        "tags": submission.tags or ["general"],
        "severity": submission.severity,
        "complexity": submission.complexity,
        "quality_status": "draft",
        "disease_category": disease_category,
        "environment": {"python_version": ">=3.9", "os": "any"},
        "created_at": today,
        "updated_at": today,
        "contributors": [{"github": submission.contributor_github}],
        "source_url": submission.source_url,
        "verification_method": submission.verification_method,
        "evidence_urls": submission.evidence_urls,
        "related_cases": [],
    }
    yaml_section = "---\n" + yaml.safe_dump(
        metadata,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    ).rstrip() + "\n---"

    # 构建 Markdown 正文
    sections = []

    sections.append(f"## 🏥 症状描述\nSymptom Description\n\n{submission.symptom or '（请补充症状描述）'}")

    if submission.error_message:
        sections.append(f"## 🔍 错误信息\nError Message\n\n```\n{submission.error_message}\n```")

    if submission.root_cause:
        sections.append(f"## 🔬 根因分析\nRoot Cause Analysis\n\n{submission.root_cause}")

    if submission.prescription:
        sections.append(f"## 💊 药方\nPrescriptions\n\n### 药方 1\n\n{submission.prescription}")
    else:
        sections.append("## 💊 药方\nPrescriptions\n\n### 药方 1\n\n（请补充解决方案）")

    if submission.verification:
        sections.append(f"## ✅ 验证记录\nVerification\n\n{submission.verification}")
    else:
        sections.append("## ✅ 验证记录\nVerification\n\n（待复现验证，当前仅为草稿药方）")

    if submission.safety:
        sections.append(f"## ⚠️ 风险与回退\nSafety and Rollback\n\n{submission.safety}")
    else:
        sections.append(
            "## ⚠️ 风险与回退\nSafety and Rollback\n\n"
            "（待补充影响范围、验证失败信号和回退步骤；补全前不要自动执行。）"
        )

    references = list(dict.fromkeys([
        submission.source_url,
        *submission.evidence_urls,
    ]))
    reference_body = "\n".join(f"- {url}" for url in references if url) or "- （请补充参考链接）"
    sections.append(f"## 🔗 参考资料\nReferences\n\n{reference_body}")

    body = "\n\n".join(sections)

    return f"{yaml_section}\n\n{body}\n"


def save_case_file(submission: CaseSubmission) -> dict:
    """
    保存病例文件到 cases/ 目录

    Returns:
        dict 包含文件路径和 case_id
    """
    framework = normalize_framework(submission.framework)
    normalized_submission = replace(submission, framework=framework)
    cases_root = Path(config.CASES_DIR).resolve(strict=False)
    cases_root.mkdir(parents=True, exist_ok=True)

    category = determine_category(submission.tags, submission.error_message)
    target_dir = (cases_root / framework / category).resolve(strict=False)
    try:
        target_dir.relative_to(cases_root)
    except ValueError as exc:
        raise ValueError("framework resolved outside the configured cases directory") from exc
    target_dir.mkdir(parents=True, exist_ok=True)

    for _attempt in range(1000):
        case_id = generate_case_id(framework, submission.title, submission.title_en)
        content = generate_case_markdown(normalized_submission, case_id=case_id)
        filename = f"{case_id.removeprefix(f'{framework}-')}.md"
        filepath = (target_dir / filename).resolve(strict=False)
        try:
            filepath.relative_to(cases_root)
        except ValueError as exc:
            raise ValueError("generated case path resolved outside the configured cases directory") from exc
        try:
            with filepath.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
            break
        except FileExistsError:
            continue
    else:
        raise RuntimeError("Could not allocate a unique case ID after 1000 attempts")

    try:
        relative_path = str(filepath.relative_to(Path(config.ROOT_DIR).resolve(strict=False)))
    except ValueError:
        relative_path = str(filepath.relative_to(cases_root.parent))

    return {
        "case_id": case_id,
        "filepath": relative_path,
        "absolute_path": str(filepath),
        "content_preview": content[:500],
        "quality_status": "draft",
    }
