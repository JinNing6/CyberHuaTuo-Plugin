---
id: platform-agent-windows-pid-001
title: "Windows 用 os.kill(pid, 0) 探活误杀 Agent 进程"
title_en: "Unix-style PID probing is destructive on Windows"
framework: platform-agent
framework_version: "Python 3.9+ on Windows"
language: python
tags: [windows, process, pid, liveness, agent]
severity: critical
complexity: moderate
quality_status: reviewed
disease_category: runtime-and-lifecycle
case_origin: maintainer-incident
origin_skill: windows-process-liveness-safety
reviewed_at: "2026-07-15"
reviewed_by: "JinNing6"
match_signatures:
  - "Windows os.kill pid 0 terminates process"
  - "Agent process exits during PID liveness check"
environment:
  python_version: ">=3.9"
  os: windows
created_at: "2026-07-15"
updated_at: "2026-07-15"
contributors:
  - github: JinNing6
source_url: "https://docs.python.org/3/library/os.html#os.kill"
related_cases: []
---

## 症状描述

Windows 上的 Agent broker、测试门禁或会话注册表在检查 PID 后突然退出、留下子进程，或者表现与 Unix 完全不同；代码通常把 `os.kill(pid, 0)` 当成只读探活。

## 根因分析

Python 官方文档说明，Windows 上除控制台特殊信号外，传给 `os.kill` 的其他信号值会通过 `TerminateProcess` 无条件终止进程，退出码就是该值。Unix 的信号 0 探测语义不能直接移植到 Windows。

## 药方

Windows 分支改用只读 `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)` 检查句柄是否可获得，并在 `finally` 中调用 `CloseHandle`；非 Windows 才保留 `os.kill(pid, 0)`。测试必须 patch `os.kill` 为一旦调用就失败，不能拿当前测试 PID 真实试错。

```python
handle = kernel32.OpenProcess(0x1000, False, int(pid))
if not handle:
    return False
try:
    return True
finally:
    kernel32.CloseHandle(handle)
```

## 验证

把被测模块的 `os.name` patch 为 `nt`，同时让 `os.kill` 抛 `AssertionError`，使用当前进程 PID 运行注册表快照并断言仍为 active；再覆盖无效 PID 和句柄关闭。本病例来自维护者既有 Windows 故障复盘，本轮未对任何真实进程执行探活或终止操作。

## 风险与回退

只申请 `PROCESS_QUERY_LIMITED_INFORMATION`，不要请求 `PROCESS_ALL_ACCESS`。每个成功打开的句柄必须关闭；不要解析本地化 `tasklist` 文本作为首选热路径。

## 参考资料

- https://docs.python.org/3/library/os.html#os.kill
- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openprocess
- https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle
