---
id: "nourishing-windows-network-diagnosis-006"
title: "Windows 网速变慢网络体检总药方"
title_en: "Windows network slowdown diagnostic prescription"
framework: "_nourishing"
framework_version: "Windows 10/11"
language: "powershell"
tags:
  - "windows"
  - "network"
  - "speed"
  - "ping"
  - "tracert"
  - "test-netconnection"
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
source_url: "https://learn.microsoft.com/en-us/powershell/module/nettcpip/test-netconnection"
related_cases:
  - "nourishing-windows-dns-resolution-optimization-007"
  - "nourishing-windows-packet-loss-route-jitter-008"
  - "nourishing-windows-tcp-adapter-tuning-009"
---

## 🧬 滋补概述
Nourishing Overview

网速慢不能直接归因于宽带差，也不应该上来就执行“网络重置”“改注册表”“关闭所有网卡节能”。正确做法是先把网络链路分层体检：DNS 解析、基础连通、延迟抖动、丢包、路由路径、网卡状态、后台连接占用。赛博华佗只先读证据，再按病灶开方。

## 🏥 常见症状
Common Symptoms

- 浏览器打开网页慢，但下载速度有时正常
- AI 工具、包管理器、模型下载、GitHub 或 API 连接不稳定
- 游戏或远程桌面延迟高、突然卡顿
- 同一个 Wi-Fi 下手机正常，电脑异常
- 换浏览器无效，但重启网络或电脑后短暂恢复
- 不知道问题来自 DNS、Wi-Fi、路由器、运营商还是本机网卡设置

## 💊 药方
Prescriptions

### 药方 1：先保护隐私，再收集症状

把网络报告交给 Agent 前，先打码：

- 本机用户名和用户目录路径
- 公司域名、内网域名、VPN 地址
- 公网 IP、MAC 地址、Wi-Fi SSID
- 代理地址、账号、设备序列号

不要把完整 `ipconfig /all`、公司 VPN 路由、内网 DNS 直接公开贴到社交平台或 issue。

### 药方 2：分开测试 IP 连通和域名解析

命令提示符或 PowerShell 执行：

```powershell
ping /n 20 1.1.1.1
ping /n 20 www.microsoft.com
Test-NetConnection www.microsoft.com -InformationLevel Detailed
```

读法：

- IP ping 稳定、域名 ping 慢：优先怀疑 DNS 解析或代理。
- 两者都慢或丢包：继续查 Wi-Fi、路由、运营商链路或本机网卡。
- `Test-NetConnection` 的 TCP 连接失败但 ping 成功：优先查端口、防火墙、代理或目标服务。

### 药方 3：看路径，不要只看测速网站

```powershell
tracert -d www.microsoft.com
pathping -n www.microsoft.com
```

读法：

- 前 1-2 跳延迟高或丢包：优先查本机 Wi-Fi、网线、路由器、光猫。
- 中间运营商跳点明显抖动：可能是运营商链路、跨网或拥塞。
- 只有目标站点慢：可能是目标服务、CDN、代理或区域路由问题。

### 药方 4：只读查看本机网络状态

```powershell
ipconfig /all
Get-NetAdapter | Sort-Object Status, Name
Get-NetIPConfiguration
Get-NetTCPConnection -State Established |
  Group-Object RemoteAddress |
  Sort-Object Count -Descending |
  Select-Object -First 20
```

用途：

- `ipconfig /all` 看 DNS、网关、DHCP、代理相关线索。
- `Get-NetAdapter` 看实际在用的是 Wi-Fi、以太网、虚拟网卡还是 VPN。
- `Get-NetTCPConnection` 找异常大量连接的远端地址，但不要只凭地址直接结束进程。

### 药方 5：交给 Agent 的最小诊断输入

```text
我的 Windows 网络变慢。以下是已打码的诊断结果：

1. ping /n 20 1.1.1.1:
<粘贴结果>

2. ping /n 20 www.microsoft.com:
<粘贴结果>

3. tracert -d www.microsoft.com:
<粘贴结果>

4. pathping -n www.microsoft.com:
<粘贴结果>

5. ipconfig /all 的 DNS、网关、适配器部分：
<粘贴结果，已打码>

请判断更可能是 DNS、丢包、路由、Wi-Fi、本机网卡、代理/VPN，还是目标服务问题。只给诊断和人工确认步骤，不要直接修改系统配置。
```

### 药方 6：后悔药协议，先存档再开方

任何会改变系统网络状态的操作，都必须先生成“存档丸”。这一步只读取配置，不修改网络：

```powershell
$backupRoot = Join-Path $env:USERPROFILE "Desktop\cht-network-backup"
New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null

ipconfig /all > (Join-Path $backupRoot "ipconfig-all-before.txt")
netsh interface tcp show global > (Join-Path $backupRoot "tcp-global-before.txt")
Get-DnsClientServerAddress | Export-Clixml (Join-Path $backupRoot "dns-before.xml")
Get-NetAdapter | Export-Clixml (Join-Path $backupRoot "adapter-before.xml")
Get-NetAdapterAdvancedProperty -Name "*" | Export-Clixml (Join-Path $backupRoot "adapter-advanced-before.xml")
```

如果要检查网卡电源管理，需要管理员 PowerShell：

```powershell
Get-NetAdapterPowerManagement | Export-Clixml (Join-Path $backupRoot "adapter-power-before.xml")
```

后悔药规则：

- 没有存档丸，不开会修改系统状态的方。
- 一次只改一个病灶，例如只改 DNS，或只改某个网卡高级属性。
- 药方必须写清楚原值、新值、验证命令和回退命令。
- 如果无法给出回退命令，这个动作只能列为“人工确认项”，不能让 Agent 自动执行。
- `ipconfig /flushdns` 属于低风险缓存清理，不需要恢复旧缓存；DNS 缓存会重新生成。

## ✅ 验证
Verification

优化后不要只凭体感判断。至少复测：

```powershell
ping /n 20 1.1.1.1
ping /n 20 www.microsoft.com
tracert -d www.microsoft.com
```

验证标准：

- 丢包率下降或消失。
- 平均延迟和最大延迟差距缩小，抖动减少。
- DNS 解析慢、TCP 连接失败或路径绕路的病灶有明确解释。
- 修改过任何网络配置后，都能说明回退方式。

## 🔗 参考资料
References

- Microsoft Learn: Test-NetConnection
- Microsoft Learn: ping
- Microsoft Learn: tracert
- Microsoft Learn: pathping
- Microsoft Learn: Export-Clixml
- Microsoft Learn: Import-Clixml

---

> 🧬 本滋补药方由 [@CyberHuaTuo](https://github.com/CyberHuaTuo) 贡献 · 网速先辨经络，再通其脉。
