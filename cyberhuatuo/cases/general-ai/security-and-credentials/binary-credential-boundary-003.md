---
id: general-ai-binary-credential-003
title: "二进制密钥被 strip 静默截断导致随机验签失败"
title_en: "Binary credentials are corrupted by pre-validation strip"
framework: general-ai
framework_version: "Python 3.9+"
language: python
tags: [credential, binary, base64, cryptography]
severity: critical
complexity: moderate
quality_status: reviewed
disease_category: security-and-credentials
case_origin: maintainer-incident
origin_skill: binary-credential-format-boundary
reviewed_at: "2026-07-15"
reviewed_by: "JinNing6"
match_signatures:
  - "binary credential strip length verification failure"
  - "Ed25519 X25519 key bytes strip"
environment:
  python_version: ">=3.9"
  os: any
created_at: "2026-07-15"
updated_at: "2026-07-15"
contributors:
  - github: JinNing6
source_url: "https://docs.python.org/3/library/stdtypes.html#bytes.strip"
related_cases: []
---

## 症状描述

固定长度的 Ed25519/X25519 密钥、nonce、摘要或令牌从文件读入后偶发长度错误或验签失败；重新生成几次又可能恢复，表现像随机密码学故障。

## 根因分析

读取器在判断格式和长度前对原始 `bytes` 调用了 `.strip()`。`bytes.strip()` 删除的是两端所有属于指定集合或默认 ASCII 空白的字节，而原始二进制值完全可能以这些合法八位组开头或结尾，因此密钥被不可逆修改。

## 药方

先按原始长度识别固定长度二进制格式并原样返回；只有进入明确的 Base64 文本分支后才允许清理换行，并启用严格字符验证。格式可能歧义时使用显式格式参数或不同扩展名，未知和错误长度输入必须失败关闭。

```python
raw = path.read_bytes()
if len(raw) == EXPECTED_RAW_LENGTH:
    value = raw
else:
    value = base64.b64decode(raw.strip(), validate=True)
    if len(value) != EXPECTED_RAW_LENGTH:
        raise ValueError("invalid credential length")
```

## 验证

固定构造首尾分别为 ASCII 空白八位组、包含 NUL 和非 UTF-8 字节的原始凭据，断言读取前后逐字节一致；再覆盖合法 Base64、非法字符、错误长度和端到端验签。本病例来自维护者既有故障复盘，本轮没有接触真实凭据或重新执行密码学实验。

## 风险与回退

禁止记录原始密钥、令牌或解码内容，只记录类型、长度和不可逆哈希。不要在解析失败后静默生成替代凭据，也不要降低 Base64 严格校验。

## 参考资料

- https://docs.python.org/3/library/stdtypes.html#bytes.strip
- https://docs.python.org/3/library/base64.html#base64.b64decode
