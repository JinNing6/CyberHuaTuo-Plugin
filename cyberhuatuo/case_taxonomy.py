"""Stable disease categories for prescriptions and retrieval."""

from __future__ import annotations

from collections.abc import Iterable

DISEASE_CATEGORIES: dict[str, str] = {
    "dependency-and-version": "依赖与版本科",
    "runtime-and-lifecycle": "运行时与生命周期科",
    "data-and-serialization": "数据与序列化科",
    "api-and-schema": "API 与契约科",
    "storage-and-filesystem": "存储与文件系统科",
    "database-and-migration": "数据库与迁移科",
    "security-and-credentials": "安全与凭据科",
    "agent-and-tooling": "Agent 与工具链科",
    "network-and-integration": "网络与集成科",
    "performance-and-resource": "性能与资源科",
    "ui-and-interaction": "界面与交互科",
    "system-configuration": "系统与配置科",
    "other": "综合科",
}

DISEASE_CATEGORY_KEYS = tuple(DISEASE_CATEGORIES)
DEFAULT_DISEASE_CATEGORY = "other"

_CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("security-and-credentials", ("credential", "secret", "token", "auth", "base64", "api key")),
    ("database-and-migration", ("database", "migration", "schema drift", "d1", "sql")),
    ("storage-and-filesystem", ("filesystem", "directory", "file", "atomic", "rename", "disk")),
    ("api-and-schema", ("response model", "contract", "schema", "validation", "fastapi", "pydantic")),
    ("dependency-and-version", ("dependency", "version", "importerror", "module not found", "package")),
    ("agent-and-tooling", ("agent", "mcp", "tool", "daemon", "codex", "claude code")),
    ("network-and-integration", ("network", "dns", "proxy", "http", "websocket", "integration")),
    ("performance-and-resource", ("performance", "memory", "cpu", "latency", "timeout", "resource")),
    ("ui-and-interaction", ("ui", "widget", "render", "click", "state", "layout")),
    ("system-configuration", ("configuration", "config", "environment", "registry", "power mode")),
    ("data-and-serialization", ("json", "jsonl", "bom", "encoding", "serialization", "deserialize")),
    ("runtime-and-lifecycle", ("runtime", "lifecycle", "process", "pid", "thread", "sys.modules")),
)


def normalize_disease_category(value: object) -> str:
    """Return a valid category key, falling back for legacy or unknown values."""
    normalized = str(value or "").strip().lower()
    return normalized if normalized in DISEASE_CATEGORIES else DEFAULT_DISEASE_CATEGORY


def disease_category_label(value: object) -> str:
    return DISEASE_CATEGORIES[normalize_disease_category(value)]


def infer_disease_category(
    tags: Iterable[object] = (),
    *texts: object,
) -> str:
    """Infer a stable category for new drafts when the author did not choose one."""
    searchable = " ".join([*(str(tag) for tag in tags), *(str(text) for text in texts)]).casefold()
    for category, keywords in _CATEGORY_KEYWORDS:
        if any(keyword in searchable for keyword in keywords):
            return category
    return DEFAULT_DISEASE_CATEGORY
