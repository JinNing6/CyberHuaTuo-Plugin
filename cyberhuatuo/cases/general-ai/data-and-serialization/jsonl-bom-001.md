---
id: general-ai-jsonl-bom-001
title: "Windows 下 JSONL 首条记录因 UTF-8 BOM 丢失"
title_en: "JSONL first record is lost because of a UTF-8 BOM"
framework: general-ai
framework_version: "Python 3.9+"
language: python
tags: [jsonl, utf-8-bom, ledger, windows]
severity: high
complexity: simple
quality_status: reviewed
disease_category: data-and-serialization
case_origin: maintainer-incident
origin_skill: jsonl-ledger-bom-proof
reviewed_at: "2026-07-15"
reviewed_by: "JinNing6"
match_signatures:
  - "Unexpected UTF-8 BOM"
  - "Unexpected UTF-8 BOM JSONL line 1 invalid JSON"
  - "JSONDecodeError Unexpected UTF-8 BOM"
environment:
  python_version: ">=3.9"
  os: any
created_at: "2026-07-15"
updated_at: "2026-07-15"
contributors:
  - github: JinNing6
source_url: "https://docs.python.org/3/library/json.html#character-encodings"
related_cases: []
---

## 症状描述

Windows 或编辑器改写过的 JSONL 台账在第一行报 `Unexpected UTF-8 BOM`，公开报告把真实的第一条事件当成坏记录，计数因此变成零或少一条。

## 根因分析

JSON 文本不应带 BOM，Python `json` 解码器遇到初始 BOM 会报错。读取器统一按普通 `utf-8` 打开时，BOM 会留在第一行开头并破坏 `json.loads`；问题属于读取兼容边界，不应通过删除台账或跳过第一行处理。

## 药方

只把 JSONL **读取路径**改为 `encoding="utf-8-sig"`，让解码器仅在文件开头消费 BOM；追加和新建仍使用普通 `utf-8`，避免继续扩散 BOM。逐行解析时继续保留后续坏记录的行号告警，不要吞掉所有 `JSONDecodeError`。

```python
lines = ledger_path.read_text(encoding="utf-8-sig").splitlines()
for line_number, line in enumerate(lines, start=1):
    if not line.strip():
        continue
    try:
        event = json.loads(line)
    except json.JSONDecodeError as exc:
        warnings.append(f"line {line_number} is not valid JSON: {exc.msg}")
```

## 验证

用 `encoding="utf-8-sig"` 写入包含一条真实事件的临时 JSONL，运行用户可见报告并确认事件计数为一、第一行没有 BOM 告警；再追加一条畸形 JSON，确认它仍产生精确的行号告警。本病例来自维护者既有故障复盘，本轮未重新执行该应用级实验。

## 风险与回退

不要对每一行调用 `lstrip("\ufeff")`，也不要把所有解码异常静默忽略。若改动造成非 BOM 文件回归，回退读取常量即可，原始台账内容不需要修改。

## 参考资料

- https://docs.python.org/3/library/json.html#character-encodings
- https://docs.python.org/3/library/codecs.html#encodings.utf_8_sig
