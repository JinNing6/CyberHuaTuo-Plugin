---
id: "nourishing-windows-storage-pressure-002"
title: "Windows 磁盘空间不足清理药方"
title_en: "Windows low disk space cleanup prescription"
framework: "_nourishing"
framework_version: "Windows 10/11"
language: "powershell"
tags:
  - "windows"
  - "storage-sense"
  - "disk-cleanup"
  - "low-disk-space"
  - "performance"
severity: "medium"
complexity: "simple"
case_type: "nourishing"
environment:
  python_version: "any"
  os: "windows"
created_at: "2026-07-03"
updated_at: "2026-07-03"
contributors:
  - github: "CyberHuaTuo"
source_url: "https://learn.microsoft.com/en-us/windows/configuration/storage/storage-sense"
related_cases:
  - "nourishing-windows-system-file-repair-001"
---

## 🧬 滋补概述
Nourishing Overview

系统盘空间不足会导致 Windows 更新失败、虚拟内存受限、浏览器和 IDE 缓存异常、Agent 工具链安装失败。清理优先走 Windows 官方 Storage Sense 和应用级缓存，不要直接删除系统目录。

## 🏥 常见症状
Common Symptoms

- `C:` 盘剩余空间低于 10% 或低于 20GB
- Windows Update 下载或安装失败
- `pip install`、`npm install`、模型下载失败
- 浏览器、IDE、Docker 或包管理器缓存占用巨大
- 系统频繁提示释放空间

## 💊 药方
Prescriptions

### 药方 1：用 Storage Sense 清理临时文件

打开：

```text
Settings -> System -> Storage -> Storage Sense
```

建议先开启或手动运行以下项目：

- Temporary files
- Recycle Bin cleanup
- Windows Update cleanup
- Delivery Optimization files
- Thumbnails

谨慎项：

- Downloads folder cleanup 可能删除下载目录文件，除非你确认下载目录无重要文件。
- Locally available cloud content 会影响 OneDrive 等云盘的本地缓存策略，先确认同步状态。

### 药方 2：检查大目录，不直接盲删

PowerShell 查看用户目录下最大的一级目录：

```powershell
Get-ChildItem $env:USERPROFILE -Force -Directory |
  ForEach-Object {
    $size = (Get-ChildItem $_.FullName -Force -Recurse -ErrorAction SilentlyContinue |
      Measure-Object Length -Sum).Sum
    [PSCustomObject]@{ Path = $_.FullName; GB = [math]::Round($size / 1GB, 2) }
  } |
  Sort-Object GB -Descending |
  Select-Object -First 20
```

优先处理可再生成缓存：

- 浏览器缓存
- IDE 缓存
- 包管理器缓存
- 旧安装包和重复下载文件

### 药方 3：保留系统安全边界

不要手动删除：

- `C:\Windows\WinSxS`
- `C:\Windows\Installer`
- `C:\ProgramData\Microsoft`
- 不认识的驱动目录或系统服务目录

这些目录误删可能导致更新、卸载、修复和驱动功能损坏。

## ✅ 验证
Verification

```powershell
Get-PSDrive -PSProvider FileSystem
```

验证标准：

- 系统盘至少恢复到 15% 以上空闲空间，或至少空出 20GB。
- Windows Update 和常用开发工具安装恢复正常。
- 清理后重启一次，确认没有应用配置或同步状态异常。

## 🔗 参考资料
References

- Microsoft Learn: Configure Storage Sense in Windows

---

> 🧬 本滋补药方由 [@CyberHuaTuo](https://github.com/CyberHuaTuo) 贡献 · 清瘀不伤正，先清缓存，再动根基。
