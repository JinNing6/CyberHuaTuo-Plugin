---
id: general-ai-windows-atomic-004
title: "Windows 原子发布目录时偶发 WinError 5"
title_en: "Atomic staged-directory publication intermittently fails on Windows"
framework: general-ai
framework_version: "Python 3.9+"
language: python
tags: [windows, atomic-rename, filesystem, artifact]
severity: high
complexity: complex
quality_status: reviewed
disease_category: storage-and-filesystem
case_origin: maintainer-incident
origin_skill: windows-atomic-directory-publish
reviewed_at: "2026-07-15"
reviewed_by: "JinNing6"
match_signatures:
  - "PermissionError WinError 5 Access is denied os.replace"
  - "Windows atomic directory publish os.rename"
environment:
  python_version: ">=3.9"
  os: windows
created_at: "2026-07-15"
updated_at: "2026-07-15"
contributors:
  - github: JinNing6
source_url: "https://docs.python.org/3/library/os.html#os.replace"
related_cases: []
---

## 症状描述

完整产物已经写入同盘 staging 目录，但发布为最终不可变目录的 `os.rename`、`os.replace` 或 `Path.replace` 在 Windows 偶发 `PermissionError: [WinError 5] Access is denied`。

## 根因分析

当源目标同盘、文件句柄已关闭且目标不存在时，短暂的目录访问拒绝可能来自扫描器或系统竞争；但目标已出现表示并发发布，持续拒绝则更可能是 ACL 或生命周期错误。这三类情况不能用无限重试或复制覆盖混为一谈。

## 药方

把同文件系统原子重命名保留为唯一提交点。使用发布子树之外的跨进程锁，在锁内再次确认目标不存在；只对目标仍不存在时的 `PermissionError` 做有限次数指数退避，其他异常立即抛出，目标在重试期间出现则按重复发布失败处理。

```python
for attempt in range(MAX_ATTEMPTS):
    if final.exists():
        raise FileExistsError(final)
    try:
        os.rename(staging, final)
        break
    except PermissionError:
        if attempt + 1 == MAX_ATTEMPTS:
            raise
        time.sleep(min(0.01 * (2 ** attempt), 0.1))
```

## 验证

通过故障注入让前两次重命名抛 `PermissionError`、第三次执行真实重命名，断言最终目录完整且 staging 消失；另测预存目标拒绝覆盖和重试耗尽不产生半成品。本病例来自维护者既有故障复盘，本轮未重新运行 Windows 故障注入。

## 风险与回退

不能回退到递归复制后删除，否则最终路径会暴露部分状态。重试必须有上限并限定异常类型；永久权限错误应修复 ACL、句柄或生命周期，而不是扩大重试预算。

## 参考资料

- https://docs.python.org/3/library/os.html#os.replace
- https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexw
