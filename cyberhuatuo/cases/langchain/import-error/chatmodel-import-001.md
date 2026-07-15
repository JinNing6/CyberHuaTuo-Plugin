---
id: "langchain-import-chatmodel-001"
title: "LangChain 中 ChatOpenAI 导入失败"
title_en: "ChatOpenAI import error in current LangChain packages"
framework: "langchain"
framework_version: ">=1.0.0"
language: "python"
tags:
  - "import-error"
  - "breaking-change"
  - "migration"
severity: "medium"
complexity: "simple"
quality_status: "gold"
environment:
  python_version: ">=3.9"
  os: "any"
created_at: "2026-03-10"
updated_at: "2026-07-14"
verified_at: "2026-07-14"
verification_method: "isolated-import-test"
reviewed_at: "2026-07-14"
reviewed_by: "JinNing6"
match_signatures:
  - "ImportError: cannot import name ChatOpenAI from langchain"
  - "from langchain import ChatOpenAI"
contributors:
  - github: "CyberHuaTuo"
source_url: "https://docs.langchain.com/oss/python/integrations/chat/openai"
evidence_urls:
  - "https://docs.langchain.com/oss/python/integrations/chat/openai"
  - "https://pypi.org/project/langchain-openai/"
related_cases: []
---

## 🏥 症状描述
Symptom Description

当前 LangChain 环境中继续使用 `from langchain import ChatOpenAI` 时，导入语句报错，应用无法启动。

## 🔍 错误信息
Error Message

```python
ImportError: cannot import name 'ChatOpenAI' from 'langchain'
```

完整堆栈：

```
Traceback (most recent call last):
  File "app.py", line 3, in <module>
    from langchain import ChatOpenAI
ImportError: cannot import name 'ChatOpenAI' from 'langchain' (/usr/local/lib/python3.11/site-packages/langchain/__init__.py)
```

## 🔬 根因分析
Root Cause Analysis

LangChain 的 OpenAI 集成由独立包 `langchain-openai` 提供。当前官方安装与导入方式是安装该集成包，并从 `langchain_openai` 导入 `ChatOpenAI`；主包 `langchain` 不再导出这个类。

## 💊 药方
Prescriptions

### 药方 1：更新导入路径 ✅ 推荐

**适用版本**: 当前拆分集成包的 LangChain 版本；本药方已在 `langchain==1.3.13` 与 `langchain-openai==1.3.5` 验证。

1. 安装独立的 OpenAI 集成包：

```bash
python -m pip install -U langchain-openai
```

2. 更新导入语句：

```python
# ❌ 主包不再导出 ChatOpenAI
from langchain import ChatOpenAI

# ✅ 当前官方集成包
from langchain_openai import ChatOpenAI
```

3. 其他常用类的迁移：

```python
# Embeddings
from langchain_openai import OpenAIEmbeddings

# LLM
from langchain_openai import OpenAI
```

## ✅ 验证记录
Verification

2026-07-14 在一次性 Python 虚拟环境中执行：

```bash
python -m pip install "langchain==1.3.13" "langchain-openai==1.3.5"
python -c "from langchain_openai import ChatOpenAI; print(ChatOpenAI.__name__)"
```

预期且实测输出：

```text
ChatOpenAI
```

同一环境执行旧导入 `from langchain import ChatOpenAI`，实测得到 `ImportError`。

## ⚠️ 风险与回退
Safety and Rollback

- 该药方只安装独立集成包并修改 Python 导入路径，不执行系统级配置变更。
- 如果项目使用锁文件，应同步更新并提交锁文件；验证失败时恢复原分支或锁文件。
- 不要在源码中写入 API Key；通过环境变量提供 `OPENAI_API_KEY`。

## 🔗 参考资料
References

- [LangChain ChatOpenAI 官方集成文档](https://docs.langchain.com/oss/python/integrations/chat/openai)
- [langchain-openai PyPI 发布页](https://pypi.org/project/langchain-openai/)

---

> 本药方由 [@CyberHuaTuo](https://github.com/JinNing6/CyberHuaTuo-Plugin) 维护 · 如有新的版本证据，欢迎 [提交 PR](https://github.com/JinNing6/CyberHuaTuo-Plugin/pulls)
