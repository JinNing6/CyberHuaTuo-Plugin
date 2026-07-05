---
id: "nourishing-windows-power-mode-optimization-005"
title: "Windows 电源模式与性能续航优化药方"
title_en: "Windows power mode and performance battery optimization prescription"
framework: "_nourishing"
framework_version: "Windows 10/11"
language: "powershell"
tags:
  - "windows"
  - "powercfg"
  - "power-mode"
  - "battery"
  - "performance"
severity: "medium"
complexity: "moderate"
case_type: "nourishing"
environment:
  python_version: "any"
  os: "windows"
created_at: "2026-07-05"
updated_at: "2026-07-05"
contributors:
  - github: "CyberHuaTuo"
source_url: "https://support.microsoft.com/en-us/windows/change-the-power-mode-for-your-windows-pc-c2aff038-22c9-f46d-5ca0-78696fdf2de8"
related_cases:
  - "nourishing-windows-battery-sleep-drain-003"
---

## 🧬 滋补概述
Nourishing Overview

电源优化不是简单把所有设备都拉到“最高性能”。正确做法是先看当前电源模式、睡眠唤醒、后台请求和电池健康，再按使用场景开方：插电性能、移动续航、睡眠稳定、风扇噪音分别优化。

## 🏥 常见症状
Common Symptoms

- 插电时编译、游戏、AI 工具运行不稳定或性能偏低
- 不插电时续航明显下降
- 合盖睡眠后掉电、发热或风扇转动
- 电脑空闲时仍被进程或设备阻止睡眠
- 不清楚当前使用的是省电、平衡还是高性能策略

## 💊 药方
Prescriptions

### 药方 1：先查看当前电源方案

PowerShell 或命令提示符执行：

```powershell
powercfg /getactivescheme
powercfg /list
```

目标是确认当前方案，不要在不知道原状态的情况下直接改配置。

### 药方 2：用官方电源模式做第一层调节

打开：

```text
Settings -> System -> Power & battery -> Power mode
```

建议：

- 插电跑编译、游戏、模型推理：优先测试 `Best performance`。
- 移动办公或出差：优先测试 `Best power efficiency`。
- 日常开发：优先保留 `Balanced` 或系统推荐模式。

不要为了“性能优化”长期牺牲散热、噪音和续航。电源模式是场景开关，不是永久越高越好。

### 药方 3：诊断是什么阻止睡眠或耗电

```powershell
powercfg /requests
powercfg /waketimers
powercfg /lastwake
```

常见线索：

- 某个音频、视频、同步、下载进程阻止睡眠
- 某个计划任务设置了唤醒定时器
- 外接键盘、鼠标、网卡或蓝牙设备唤醒系统

处理原则：

- 先改对应应用或设备设置。
- 不要直接禁用不认识的系统服务。
- 如果是外设唤醒，优先在设备管理器里确认设备名称和用途。

### 药方 4：生成续航和能效报告给 Agent 读

```powershell
powercfg /batteryreport /output "$env:USERPROFILE\Desktop\battery-report.html"
powercfg /energy /output "$env:USERPROFILE\Desktop\energy-report.html"
```

支持 Modern Standby 的设备再执行：

```powershell
powercfg /sleepstudy /output "$env:USERPROFILE\Desktop\sleepstudy-report.html"
```

把报告中的关键段落交给 Agent 总结时，注意不要上传真实用户名、公司路径、设备序列号或隐私文件路径。

### 药方 5：高风险操作必须先说明回退

不建议在短视频或自动 Agent 中直接执行：

```powershell
powercfg /restoredefaultschemes
```

这个命令会重置电源方案，可能清掉自定义方案。只有在电源方案明显损坏、你接受丢失自定义配置，并记录过当前状态后才考虑使用。

## ✅ 验证
Verification

优化后验证：

```powershell
powercfg /getactivescheme
powercfg /requests
powercfg /energy /output "$env:USERPROFILE\Desktop\energy-after.html"
```

验证标准：

- 当前电源模式符合使用场景。
- `powercfg /requests` 不再显示异常阻止睡眠的进程或设备。
- 睡眠后一晚掉电、空闲发热或风扇转动明显改善。
- 插电高负载场景下性能更稳定，且温度和噪音可接受。

## 🔗 参考资料
References

- Microsoft Support: Change the power mode for your Windows PC
- Microsoft Learn: Powercfg command-line options
- Microsoft Learn: Configure power settings

---

> 🧬 本滋补药方由 [@CyberHuaTuo](https://github.com/CyberHuaTuo) 贡献 · 先辨电源气血，再调性能阴阳。
