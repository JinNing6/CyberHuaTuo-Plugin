---
id: "nourishing-windows-tcp-adapter-tuning-009"
title: "Windows TCP 与网卡高级参数体检药方"
title_en: "Windows TCP and network adapter advanced settings checkup prescription"
framework: "_nourishing"
framework_version: "Windows 10/11"
language: "powershell"
tags:
  - "windows"
  - "network"
  - "tcp"
  - "netsh"
  - "netadapter"
  - "performance"
severity: "medium"
complexity: "complex"
case_type: "nourishing"
environment:
  python_version: "any"
  os: "windows"
created_at: "2026-07-05"
updated_at: "2026-07-05"
contributors:
  - github: "CyberHuaTuo"
source_url: "https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/netsh"
related_cases:
  - "nourishing-windows-network-diagnosis-006"
  - "nourishing-windows-packet-loss-route-jitter-008"
  - "nourishing-windows-power-mode-optimization-005"
---

## 🧬 滋补概述
Nourishing Overview

所谓“底层算法优化网速”，真正能落地的是检查 TCP 全局参数、网卡高级属性、网卡电源管理、驱动能力和异常连接状态。这里面很多参数和驱动、网卡、路由器、VPN、公司策略有关，不能套用网上的一键优化命令。赛博华佗的原则是：只读体检优先，修改必须逐项、可回退、可验证。

## 🏥 常见症状
Common Symptoms

- 同一网络下这台电脑比其他设备慢
- 大文件下载吞吐不稳定
- 游戏或会议延迟尖刺，但测速带宽看起来正常
- 插电和电池模式下网络稳定性不同
- 更新驱动、装 VPN、装加速器后网络表现变化
- 不知道网卡高级参数是否被“优化软件”改过

## 💊 药方
Prescriptions

### 药方 1：只读查看 TCP 全局参数

```powershell
netsh interface tcp show global
```

重点看：

- Receive Window Auto-Tuning Level
- Receive-Side Scaling State
- ECN Capability
- Timestamps
- Initial RTO

这些参数不是越开越快，也不是越关越稳。不同 Windows 版本、驱动和网络设备组合会有不同表现。

### 药方 2：只读查看网卡高级属性

```powershell
Get-NetAdapter | Sort-Object Status, Name
Get-NetAdapterAdvancedProperty -Name "*"
```

常见线索：

- Energy Efficient Ethernet
- Large Send Offload
- Receive Side Scaling
- Flow Control
- Interrupt Moderation
- Speed & Duplex

不要直接照搬“全部禁用 Offload”“全部关闭节能”。这些功能可能提升吞吐，也可能在特定驱动上造成延迟或兼容问题。先定位症状，再单项测试。

### 药方 3：查看网卡电源管理

部分命令需要管理员 PowerShell：

```powershell
Get-NetAdapterPowerManagement
```

如果网络在睡眠唤醒后断流、插电正常但电池异常、Wi-Fi 间歇掉线，可以把网卡电源管理和电源模式一起交给 Agent 诊断。

### 药方 4：记录驱动和统计信息

```powershell
Get-NetAdapter | Format-List Name, InterfaceDescription, Status, LinkSpeed, DriverInformation
Get-NetAdapterStatistics
```

用途：

- 确认当前实际工作的网卡和驱动版本。
- 对比更新驱动或换网络前后的错误包、丢弃包和吞吐变化。
- 排除虚拟网卡、VPN 网卡抢占优先级的问题。

### 药方 5：修改前的硬边界

修改 TCP 或网卡高级参数前必须满足：

- 已经有前后可对比的 `ping`、`pathping`、下载或业务场景数据。
- 一次只改一个参数。
- 记录原值、截图或导出结果。
- 能明确恢复到原设置。
- 公司、校园、生产机器、VPN 环境先不要自动改。

不建议 Agent 自动执行：

```powershell
netsh int tcp set global autotuninglevel=disabled
netsh int ip reset
netsh winsock reset
Set-NetAdapterAdvancedProperty ...
Disable-NetAdapterPowerManagement ...
```

这些命令会改变系统网络行为，可能影响 VPN、代理、公司网络、远程桌面和开发环境。短视频里只适合展示“体检和开方”，不适合演示真实自动修改。

### 药方 6：TCP 与网卡后悔药，按原值恢复

修改前先保存原始状态：

```powershell
$backupRoot = Join-Path $env:USERPROFILE "Desktop\cht-network-backup"
New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null

netsh interface tcp show global > (Join-Path $backupRoot "tcp-global-before.txt")
Get-NetAdapter | Export-Clixml (Join-Path $backupRoot "adapter-before.xml")
Get-NetAdapterAdvancedProperty -Name "*" | Export-Clixml (Join-Path $backupRoot "adapter-advanced-before.xml")
Get-NetAdapterStatistics | Export-Clixml (Join-Path $backupRoot "adapter-statistics-before.xml")
```

如果改了某个网卡高级属性，后悔药必须恢复这个属性的原值，而不是恢复全部默认：

```powershell
Set-NetAdapterAdvancedProperty `
  -Name "<网卡名>" `
  -DisplayName "<属性名>" `
  -DisplayValue "<原DisplayValue>"
```

只有确认要恢复厂商默认值时，才考虑：

```powershell
Reset-NetAdapterAdvancedProperty -Name "<网卡名>" -DisplayName "<属性名>"
```

如果改了网卡电源管理，后悔药要按原状态恢复。管理员 PowerShell 先存档：

```powershell
Get-NetAdapterPowerManagement | Export-Clixml (Join-Path $backupRoot "adapter-power-before.xml")
```

如果原状态是开启某项电源管理，恢复时才使用：

```powershell
Enable-NetAdapterPowerManagement -Name "<网卡名>"
```

如果原状态是关闭某项电源管理，恢复时才使用：

```powershell
Disable-NetAdapterPowerManagement -Name "<网卡名>"
```

注意：启用或禁用网卡电源管理可能重启网卡，导致短暂断网。远程桌面、SSH、会议、下载任务中不要执行。

## ✅ 验证
Verification

修改后复测同一目标、同一网络、同一场景：

```powershell
netsh interface tcp show global
ping /n 50 1.1.1.1
pathping -n www.microsoft.com
Test-NetConnection www.microsoft.com -Port 443 -InformationLevel Detailed
```

验证标准：

- 关键参数变化与本次修改一致。
- 延迟、抖动、丢包或吞吐指标有明确改善。
- VPN、代理、远程桌面、AI SDK、包管理器仍能正常使用。
- 没有因为追求“加速”引入新的断流、蓝屏、驱动异常或睡眠问题。

## 🔗 参考资料
References

- Microsoft Learn: netsh
- Microsoft Learn: Get-NetAdapterAdvancedProperty
- Microsoft Learn: Set-NetAdapterAdvancedProperty
- Microsoft Learn: Reset-NetAdapterAdvancedProperty
- Microsoft Learn: Get-NetAdapterPowerManagement
- Microsoft Learn: Enable-NetAdapterPowerManagement
- Microsoft Learn: Disable-NetAdapterPowerManagement
- Microsoft Learn: Test-NetConnection

---

> 🧬 本滋补药方由 [@CyberHuaTuo](https://github.com/CyberHuaTuo) 贡献 · 底层之脉不可乱针，先验其象，再动其针。
