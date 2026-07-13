---
id: "nourishing-windows-packet-loss-route-jitter-008"
title: "Windows 丢包、延迟抖动与路由绕路诊断药方"
title_en: "Windows packet loss latency jitter and route detour diagnostic prescription"
framework: "_nourishing"
framework_version: "Windows 10/11"
language: "powershell"
tags:
  - "windows"
  - "network"
  - "packet-loss"
  - "latency"
  - "jitter"
  - "pathping"
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
source_url: "https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/pathping"
related_cases:
  - "nourishing-windows-network-diagnosis-006"
  - "nourishing-windows-dns-resolution-optimization-007"
---

## 🧬 滋补概述
Nourishing Overview

游戏卡顿、远程桌面顿一下、视频会议断续、AI 工具上传下载不稳，常见病灶不是“下载速度不够”，而是丢包、延迟抖动或路由绕路。诊断时要分清本机到路由器、路由器到运营商、运营商到目标服务三段，避免盲目重置系统网络。

## 🏥 常见症状
Common Symptoms

- 测速带宽正常，但游戏、会议、远程桌面仍卡顿
- 下载速度一会儿快一会儿慢
- `Request timed out`、`General failure` 或偶发 TCP 连接失败
- 只有某些网站、区域或服务慢
- 有线网络正常，Wi-Fi 异常，或反过来

## 💊 药方
Prescriptions

### 药方 1：先找本地网关

```powershell
Get-NetIPConfiguration
ipconfig
```

找到当前正在使用网卡的 `DefaultGateway`，例如 `192.168.1.1`。

### 药方 2：分段 ping，不要只 ping 一个公网地址

把 `<gateway>` 换成你的默认网关：

```powershell
ping /n 50 <gateway>
ping /n 50 1.1.1.1
ping /n 50 www.microsoft.com
```

读法：

- ping 网关都丢包或延迟大：优先查 Wi-Fi 信号、网线、路由器、网卡驱动。
- 网关稳定，公网 IP 丢包：优先查光猫、运营商、路由器出口或代理/VPN。
- IP 稳定，域名异常：转到 DNS 药方。

### 药方 3：用 pathping 看路径丢包

```powershell
pathping -n www.microsoft.com
```

`pathping` 会先显示路径，再统计各跳点丢包。它比单次 `tracert` 更适合判断哪一段链路不稳定，但耗时更长。

读法：

- 第一跳就丢包：本机到路由器链路优先排查。
- 中间某一跳显示丢包，但后续跳点正常：可能是该路由器限制 ICMP 回复，不一定是真丢包。
- 从某一跳开始后续都丢包或延迟升高：更像该段之后链路拥塞或路由问题。

### 药方 4：用 tracert 判断绕路

```powershell
tracert -d www.microsoft.com
```

观察：

- 跳数是否异常多。
- 是否先绕到很远地区再回来。
- 开关 VPN 或代理后路径是否变化。

不要把所有 `* * *` 都当成网络坏了，有些路由器不返回 ICMP 超时报文。

### 药方 5：常见低风险处理顺序

按风险从低到高处理：

1. 靠近路由器或切换 5GHz/6GHz Wi-Fi。
2. 用网线临时对比，区分 Wi-Fi 和外网问题。
3. 重启路由器和光猫，记录前后变化。
4. 暂停下载、网盘同步、游戏加速器、VPN，再复测。
5. 更新网卡驱动前先记录当前驱动版本。

不建议一上来执行：

```powershell
netsh int ip reset
netsh winsock reset
```

这类重置会改变系统网络状态，可能影响 VPN、代理、开发环境和公司网络配置。

### 药方 6：链路后悔药，回到原网络路径

丢包和绕路诊断里，很多动作发生在网络环境层，不一定是 Windows 配置层。后悔药要按动作记录：

- 切换 Wi-Fi 频段：记录原 SSID、频段和信号强度，异常时切回原网络。
- 关闭 VPN、代理、加速器：记录原连接状态和节点，异常时恢复原节点。
- 重启路由器或光猫：记录重启前后的 `pathping` 和 `tracert`，如果更差，恢复原有接线、Wi-Fi 和代理/VPN 状态。
- 更新网卡驱动：先记录驱动版本；如果更新后更差，用设备管理器回退驱动或安装原厂旧版本。
- 执行 `netsh int ip reset` 或 `netsh winsock reset`：只有在可接受 VPN、代理、开发网络受影响，并准备好重新配置时才考虑；这类动作不能保证“一键恢复”，不适合短视频自动演示。

给 Agent 的回退提示词：

```text
我做过以下网络调整：
<逐条列出动作、原值、新值、时间>

以下是调整前后的 ping/pathping/tracert：
<粘贴已打码结果>

请判断哪一步可能导致变差，并按最低风险顺序给出回退步骤。不要建议执行网络重置，除非说明影响范围和人工确认条件。
```

## ✅ 验证
Verification

```powershell
ping /n 50 <gateway>
ping /n 50 1.1.1.1
pathping -n www.microsoft.com
```

验证标准：

- 本地网关丢包为 0，延迟稳定。
- 公网目标丢包下降，最大延迟不再频繁尖刺。
- 开关 VPN/代理/加速器后的路径差异能被解释。
- 如果问题来自运营商或目标服务，能提供证据而不是继续乱改本机。

## 🔗 参考资料
References

- Microsoft Learn: ping
- Microsoft Learn: tracert
- Microsoft Learn: pathping
- Microsoft Learn: Test-NetConnection
- Microsoft Learn: netsh

---

> 🧬 本滋补药方由 [@CyberHuaTuo](https://github.com/CyberHuaTuo) 贡献 · 网络经络不通，先查哪一脉阻滞。
