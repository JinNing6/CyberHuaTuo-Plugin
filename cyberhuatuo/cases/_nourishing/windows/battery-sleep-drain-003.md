---
id: "nourishing-windows-battery-sleep-drain-003"
title: "Windows 笔记本续航和睡眠耗电诊断药方"
title_en: "Windows battery and sleep drain diagnosis prescription"
framework: "_nourishing"
framework_version: "Windows 10/11"
language: "powershell"
tags:
  - "windows"
  - "powercfg"
  - "battery"
  - "sleepstudy"
  - "performance"
severity: "medium"
complexity: "moderate"
case_type: "nourishing"
environment:
  python_version: "any"
  os: "windows"
created_at: "2026-07-03"
updated_at: "2026-07-03"
contributors:
  - github: "CyberHuaTuo"
source_url: "https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/powercfg-command-line-options"
related_cases: []
---

## 🧬 滋补概述
Nourishing Overview

笔记本续航突然下降、睡眠后掉电、风扇空转，不能只靠“换电源模式”判断。Windows 内置 `powercfg` 可以生成电池、能耗和睡眠诊断报告，先定位是哪类进程、设备或电源状态在耗电。

## 🏥 常见症状
Common Symptoms

- 合盖或睡眠后掉电明显
- 待机时机器发热、风扇转动
- 电池健康度下降或容量异常
- 空闲时 CPU 唤醒频繁
- 不知道是应用、驱动还是系统电源配置导致耗电

## 💊 药方
Prescriptions

### 药方 1：生成电池报告

```powershell
powercfg /batteryreport /output "$env:USERPROFILE\Desktop\battery-report.html"
```

重点看：

- Design Capacity
- Full Charge Capacity
- Cycle Count
- Recent usage
- Battery life estimates

如果 Full Charge Capacity 明显低于 Design Capacity，属于电池健康问题，不要用软件优化掩盖硬件衰减。

### 药方 2：生成能耗诊断报告

以管理员身份执行：

```powershell
powercfg /energy /output "$env:USERPROFILE\Desktop\energy-report.html"
```

让电脑保持空闲约 60 秒，报告会列出常见能效和电池寿命问题。

### 药方 3：诊断睡眠耗电

支持 Modern Standby 的设备可以执行：

```powershell
powercfg /sleepstudy /output "$env:USERPROFILE\Desktop\sleepstudy-report.html"
```

重点看：

- 每次睡眠会话的耗电量
- Active time
- Top offenders
- 设备或进程唤醒原因

### 药方 4：查看最后一次唤醒来源

```powershell
powercfg /lastwake
powercfg /waketimers
```

如果发现某个外设、计划任务或驱动频繁唤醒，再去设备管理器、任务计划程序或对应软件中处理。

## ✅ 验证
Verification

验证标准：

- `battery-report.html` 能解释电池容量是否衰减。
- `energy-report.html` 能指出高耗能配置或设备。
- `sleepstudy-report.html` 能定位睡眠期间的异常活动。
- 修改电源或设备配置后，下一晚睡眠掉电明显下降。

## 🔗 参考资料
References

- Microsoft Learn: Powercfg command-line options
- Microsoft Learn: Modern standby SleepStudy

---

> 🧬 本滋补药方由 [@CyberHuaTuo](https://github.com/CyberHuaTuo) 贡献 · 先望其气血，再调其息眠。
