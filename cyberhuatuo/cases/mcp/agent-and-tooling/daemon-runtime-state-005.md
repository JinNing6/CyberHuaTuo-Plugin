---
id: mcp-daemon-runtime-state-005
title: "MCP 后台守护线程运行正常却读不到当前用户"
title_en: "MCP background daemon misses active runtime state"
framework: mcp
framework_version: "MCP 2025-06-18 lifecycle"
language: python
tags: [mcp, daemon, runtime-state, notification]
severity: high
complexity: complex
quality_status: reviewed
disease_category: agent-and-tooling
case_origin: maintainer-incident
origin_skill: mcp-background-daemon-runtime-state
reviewed_at: "2026-07-15"
reviewed_by: "JinNing6"
match_signatures:
  - "MCP background daemon misses active runtime state"
  - "MCP polling thread cannot read current user token"
environment:
  python_version: ">=3.9"
  os: any
created_at: "2026-07-15"
updated_at: "2026-07-15"
contributors:
  - github: JinNing6
source_url: "https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle"
related_cases: []
---

## 症状描述

MCP 工具手动调用时能看到登录用户、令牌和未读消息，但轮询守护线程虽然一直运行，却不主动通知；拆分模块或迁移入口后尤为常见。

## 根因分析

后台实现读取了复制到常量模块的旧用户或令牌，而 MCP 工具更新的是另一份活动运行时状态。静态配置、当前会话状态和持久化通知游标被混在一起，导致守护线程活着但观察的是错误状态；不同入口还可能启动不同实现。

## 药方

先映射 console script、`python -m`、插件 manifest 和包装器，确保它们启动同一个守护实现。通过一个小型运行时 accessor 读取当前用户和令牌；把 `last_notified_*` 与 `last_read_*` 分开持久化，避免未读消息每轮重复弹窗。Issue 正文首条消息和后续评论应分别处理。

```python
def active_identity() -> RuntimeIdentity:
    return runtime_state.current_identity()

def poll_once() -> None:
    identity = active_identity()
    notify_new_messages(identity, notification_cursor_store)
```

## 验证

测试中给真实运行时模块和旧常量设置冲突身份，让 sleep 在首轮后抛出以只执行一次轮询；分别覆盖首条正文、后续评论、自发消息、已通知未读和标签订阅，并验证至少一个真实入口启动修正后的 daemon。本病例来自维护者既有故障复盘，本轮未启动后台线程或连接外部 MCP 服务。

## 风险与回退

后台轮询必须遵守 MCP 生命周期和进程关闭边界，测试线程应能自行退出。不要在模块 import 时无条件启动 daemon，也不要把已通知游标等同于已读游标。

## 参考资料

- https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle
