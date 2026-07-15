"""
CyberHuaTuo 索引构建器
解析 cases/ 目录下所有 .md 病例文件，构建 ChromaDB 向量索引
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from .case_quality import audit_case
from .case_taxonomy import disease_category_label, normalize_disease_category
from .config import config

INDEX_SCHEMA_VERSION = 3

if TYPE_CHECKING:
    import chromadb


def parse_case_file(filepath: Path) -> dict[str, Any] | None:
    """
    解析单个病例文件，提取 YAML 元数据和 Markdown 正文

    Returns:
        dict 包含 metadata 和 content，解析失败返回 None
    """
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  ⚠️ 无法读取文件 {filepath}: {e}")
        return None

    # 解析 YAML Front Matter
    yaml_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    if not yaml_match:
        print(f"  ⚠️ 文件缺少 YAML Front Matter: {filepath}")
        return None

    try:
        metadata = yaml.safe_load(yaml_match.group(1))
    except yaml.YAMLError as e:
        print(f"  ⚠️ YAML 解析错误 {filepath}: {e}")
        return None

    content = yaml_match.group(2).strip()

    # 构建用于 Embedding 的文本（标题 + 症状 + 错误信息 + 药方）
    category = normalize_disease_category(metadata.get("disease_category"))
    embedding_text = (
        f"{metadata.get('title', '')} {metadata.get('title_en', '')} "
        f"{category} {disease_category_label(category)} {content}"
    )

    return {
        "id": metadata.get("id", filepath.stem),
        "metadata": metadata,
        "content": content,
        "embedding_text": embedding_text,
        "filepath": str(filepath.relative_to(config.ROOT_DIR)),
        "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def scan_cases(cases_dir: Path | None = None) -> list[dict[str, Any]]:
    """
    扫描 cases/ 目录，解析所有病例文件

    Returns:
        解析成功的病例列表
    """
    cases_dir = cases_dir or config.CASES_DIR

    if not cases_dir.exists():
        print(f"⚠️ 病例目录不存在: {cases_dir}")
        return []

    cases = []
    md_files = sorted(cases_dir.rglob("*.md"))

    for filepath in md_files:
        # 跳过索引文件（_index.md 等），但不跳过 _nourishing 目录下的文件
        if filepath.name.startswith("_"):
            continue

        case = parse_case_file(filepath)
        if case:
            # 自动标记 case_type：滋补药方 or 治病药方
            rel_path = str(filepath.relative_to(cases_dir))
            if rel_path.startswith("_nourishing"):
                case["metadata"]["case_type"] = "nourishing"
            else:
                case["metadata"]["case_type"] = "treatment"
            cases.append(case)

    return cases


def compute_case_manifest(cases: list[dict[str, Any]]) -> str:
    """Return a stable fingerprint for the exact case corpus and index schema."""
    digest = hashlib.sha256(f"index-schema:{INDEX_SCHEMA_VERSION}\n".encode())
    for case in sorted(cases, key=lambda item: item["filepath"]):
        digest.update(f"{case['filepath']}:{case['content_sha256']}\n".encode())
    return digest.hexdigest()


def _collection_metadata(manifest: str, case_count: int) -> dict[str, str | int]:
    return {
        "description": "CyberHuaTuo 病例知识库",
        "index_schema_version": INDEX_SCHEMA_VERSION,
        "case_manifest_sha256": manifest,
        "case_manifest_count": case_count,
    }


def build_index(force_rebuild: bool = False) -> tuple[chromadb.ClientAPI, int]:
    """
    构建或加载 ChromaDB 向量索引

    Args:
        force_rebuild: 是否强制重建索引

    Returns:
        (chroma_client, 索引中的病例数量)
    """
    print("🩺 CyberHuaTuo 索引构建器")
    print("=" * 40)

    import chromadb

    # 扫描病例文件
    print(f"📂 扫描病例目录: {config.CASES_DIR}")
    cases = scan_cases()
    manifest = compute_case_manifest(cases)
    expected_metadata = _collection_metadata(manifest, len(cases))

    # 初始化 ChromaDB（持久化存储）
    client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
    collection = client.get_or_create_collection(
        name=config.COLLECTION_NAME,
        metadata=expected_metadata,
    )
    existing_count = collection.count()
    current_metadata = collection.metadata or {}

    index_is_fresh = (
        existing_count == len(cases)
        and current_metadata.get("index_schema_version") == INDEX_SCHEMA_VERSION
        and current_metadata.get("case_manifest_sha256") == manifest
        and current_metadata.get("case_manifest_count") == len(cases)
    )
    if index_is_fresh and not force_rebuild:
        print(f"✅ 索引内容指纹匹配（{existing_count} 个病例），跳过构建")
        return client, existing_count

    if force_rebuild:
        print("🔄 强制刷新索引...")
    else:
        print(f"🔄 病例内容已变化或旧索引不完整（当前 {existing_count}，期望 {len(cases)}），开始刷新...")

    if not cases:
        print("⚠️ 未找到任何病例文件")
        existing_ids = collection.get().get("ids", [])
        if existing_ids:
            collection.delete(ids=existing_ids)
        collection.modify(metadata=expected_metadata)
        return client, 0

    print(f"📋 发现 {len(cases)} 个病例文件")

    # 批量添加到向量数据库
    ids = []
    documents = []
    metadatas = []

    for case in cases:
        case_id = case["id"]
        # 用文件路径的 hash 确保 ID 唯一性
        unique_id = hashlib.md5(case["filepath"].encode()).hexdigest()[:12] + "_" + case_id
        ids.append(unique_id)
        documents.append(case["embedding_text"])

        # ChromaDB metadata 只支持 str/int/float/bool
        quality = audit_case(case["metadata"], case["content"])
        meta = {
            "case_id": case["id"],
            "title": case["metadata"].get("title", ""),
            "title_en": case["metadata"].get("title_en", ""),
            "framework": case["metadata"].get("framework", "unknown"),
            "severity": case["metadata"].get("severity", "medium"),
            "complexity": case["metadata"].get("complexity", "moderate"),
            "case_type": case["metadata"].get("case_type", "treatment"),
            "disease_category": normalize_disease_category(case["metadata"].get("disease_category")),
            "disease_category_label": disease_category_label(case["metadata"].get("disease_category")),
            "filepath": case["filepath"],
            "quality_status": quality.effective_status,
            "source_url": str(case["metadata"].get("source_url", "")),
            "verified_at": str(case["metadata"].get("verified_at", "")),
        }

        # 提取贡献者 Github 署名
        contributors = case["metadata"].get("contributors", [])
        if isinstance(contributors, list) and len(contributors) > 0 and isinstance(contributors[0], dict):
            meta["contributor"] = contributors[0].get("github", "")
        else:
            meta["contributor"] = ""

        # 将 tags 列表转为逗号分隔字符串
        tags = case["metadata"].get("tags", [])
        if isinstance(tags, list):
            meta["tags"] = ",".join(tags)
        else:
            meta["tags"] = str(tags)

        metadatas.append(meta)

    # Upsert first, then remove stale rows. Metadata is committed last so an
    # interrupted refresh is retried on the next run.
    print(f"🧠 生成向量并刷新 {len(ids)} 个病例...")
    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    existing_ids = set(collection.get().get("ids", []))
    stale_ids = sorted(existing_ids - set(ids))
    if stale_ids:
        collection.delete(ids=stale_ids)

    final_count = collection.count()
    if final_count != len(ids):
        raise RuntimeError(f"索引刷新后数量不一致：期望 {len(ids)}，实际 {final_count}")
    collection.modify(metadata=expected_metadata)

    print(f"✅ 索引刷新完成！共 {final_count} 个病例已入库")
    return client, final_count


def get_case_content(filepath: str) -> str | None:
    """根据相对路径读取病例文件完整内容"""
    full_path = config.ROOT_DIR / filepath
    if full_path.exists():
        return full_path.read_text(encoding="utf-8")
    return None
