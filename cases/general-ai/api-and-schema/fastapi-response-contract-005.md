---
id: general-ai-fastapi-contract-005
title: "FastAPI 严格响应模型遇到旧数据返回 500"
title_en: "FastAPI response validation fails on legacy stored data"
framework: general-ai
framework_version: "FastAPI with Pydantic v2"
language: python
tags: [fastapi, pydantic, response-model, legacy-data]
severity: high
complexity: moderate
quality_status: reviewed
disease_category: api-and-schema
case_origin: maintainer-incident
origin_skill: fastapi-response-contract-boundary
reviewed_at: "2026-07-15"
reviewed_by: "JinNing6"
match_signatures:
  - "FastAPI ResponseValidationError legacy stored data missing required response field"
  - "ResponseValidationError response_model field required"
environment:
  python_version: ">=3.9"
  os: any
created_at: "2026-07-15"
updated_at: "2026-07-15"
contributors:
  - github: JinNing6
source_url: "https://fastapi.tiangolo.com/tutorial/response-model/"
related_cases: []
---

## 症状描述

FastAPI 端点能读到数据库记录，却在返回阶段抛 `ResponseValidationError` 并产生 500；常见于旧 JSON 行缺少后来新增的必填响应字段，或分析接口对同一指标给出不同口径。

## 根因分析

FastAPI 会用 `response_model` 验证、过滤并序列化返回值。输入模型只约束新写入，无法自动修复历史或外部写入的数据；如果服务层直接把旧行交给严格响应模型，契约不一致会在响应边界被正确暴露。

## 药方

保留严格 `response_model`，在统一的服务序列化器中显式规范旧数据：补安全默认值、丢弃或校正无效可选字段，同时维持新写入的严格校验。分析指标应选一个权威来源并从它派生所有次级总量，避免不同接口各算一套。

```python
def normalize_legacy_row(row: dict) -> dict:
    normalized = dict(row)
    normalized.setdefault("target_window", "unknown")
    normalized.setdefault("legacy_signal", False)
    return normalized

payload = ResponseModel.model_validate(normalize_legacy_row(stored_row))
```

## 验证

用包含缺失字段和非法可选值的历史行测试统一 normalizer，并让最终字典通过真实响应 Pydantic 模型；再做原失败 API 冒烟和跨接口指标恒等式测试。本病例来自维护者既有故障复盘，本轮未创建或清理真实 API 测试数据。

## 风险与回退

不要删除 `response_model` 或把必填字段全部改为可选，这会把数据漂移隐藏到客户端。默认值必须是产品契约允许的明确语义，不能伪造业务事实。

## 参考资料

- https://fastapi.tiangolo.com/tutorial/response-model/
