---
id: "nourishing-windows-system-file-repair-001"
title: "Windows 系统文件损坏急救药方"
title_en: "Windows system file corruption repair prescription"
framework: "_nourishing"
framework_version: "Windows 10/11"
language: "powershell"
tags:
  - "windows"
  - "dism"
  - "sfc"
  - "system-repair"
  - "performance"
severity: "high"
complexity: "moderate"
case_type: "nourishing"
environment:
  python_version: "any"
  os: "windows"
created_at: "2026-07-03"
updated_at: "2026-07-03"
contributors:
  - github: "CyberHuaTuo"
source_url: "https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/repair-a-windows-image?view=windows-11"
related_cases: []
---

## 🧬 滋补概述
Nourishing Overview

当 Windows 出现系统组件损坏、应用异常崩溃、更新失败、系统明显变慢但找不到单一软件原因时，先不要使用来历不明的“一键优化”工具。优先使用 Windows 官方维护工具检查和修复组件存储与系统文件。

## 🏥 常见症状
Common Symptoms

- Windows 更新反复失败
- 系统应用打不开或频繁崩溃
- `Bad Image`、组件缺失、系统文件异常
- 系统明显变慢，重启后仍持续异常
- 运行 `sfc /scannow` 后提示发现损坏文件

## 💊 药方
Prescriptions

### 药方 1：管理员终端执行 DISM 健康检查

以管理员身份打开 Windows Terminal、PowerShell 或命令提示符，然后逐条执行：

```powershell
DISM.exe /Online /Cleanup-Image /CheckHealth
DISM.exe /Online /Cleanup-Image /ScanHealth
```

如果系统提示组件存储可修复，再执行：

```powershell
DISM.exe /Online /Cleanup-Image /RestoreHealth
```

### 药方 2：修复系统文件

DISM 修复完成后，继续执行：

```powershell
sfc /scannow
```

如果 SFC 修复了文件，重启后再运行一次：

```powershell
sfc /scannow
```

目标是看到 Windows Resource Protection 未发现完整性冲突，或已经成功修复损坏文件。

### 药方 3：不要做的事

- 不要运行来源不明的注册表清理器。
- 不要批量删除 `C:\Windows\WinSxS`。
- 不要在未备份情况下手动删除系统目录。
- 不要把系统慢直接归因于“垃圾太多”，先做健康检查。

## ✅ 验证
Verification

```powershell
DISM.exe /Online /Cleanup-Image /CheckHealth
sfc /scannow
```

验证标准：

- DISM 不再报告组件存储可修复或不可修复。
- SFC 不再报告无法修复的系统文件。
- 更新、系统应用启动、日常使用稳定性恢复正常。

## 🔗 参考资料
References

- Microsoft Learn: Repair a Windows Image
- Microsoft Learn: System File Checker and DISM repair workflows

---

> 🧬 本滋补药方由 [@CyberHuaTuo](https://github.com/CyberHuaTuo) 贡献 · 上医治未病，先查系统根基。
