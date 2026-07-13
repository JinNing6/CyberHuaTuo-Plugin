---
id: "nourishing-windows-dns-resolution-optimization-007"
title: "Windows DNS 解析慢诊断与优化药方"
title_en: "Windows slow DNS resolution diagnostic and optimization prescription"
framework: "_nourishing"
framework_version: "Windows 10/11"
language: "powershell"
tags:
  - "windows"
  - "network"
  - "dns"
  - "resolve-dnsname"
  - "nslookup"
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
source_url: "https://learn.microsoft.com/en-us/powershell/module/dnsclient/resolve-dnsname"
related_cases:
  - "nourishing-windows-network-diagnosis-006"
  - "nourishing-windows-packet-loss-route-jitter-008"
---

## 🧬 滋补概述
Nourishing Overview

网页“转圈很久才开始加载”、AI API 第一次连接慢、包管理器偶发找不到域名，很多时候不是带宽问题，而是 DNS 解析慢、DNS 被劫持、代理/VPN 改写解析路径，或本机 DNS 缓存污染。DNS 优化要先比对解析结果和耗时，再决定是否换 DNS、清缓存或处理代理。

## 🏥 常见症状
Common Symptoms

- 打开新网站时卡在很久才开始加载
- `ping` IP 正常，但 `ping` 域名慢或失败
- 浏览器提示 DNS probe、name not resolved、找不到服务器
- AI SDK、GitHub、npm、pip、模型下载偶发域名解析失败
- 开关代理、VPN、加速器后问题变化明显

## 💊 药方
Prescriptions

### 药方 1：查看当前 DNS 来源

```powershell
Get-DnsClientServerAddress -AddressFamily IPv4
ipconfig /all
```

重点看：

- 当前 DNS 是否来自路由器、运营商、公司 VPN 或手动配置。
- 是否存在多个虚拟网卡、VPN 网卡、代理软件网卡。
- 同时连接 Wi-Fi、以太网、VPN 时，先确认真正走的是哪张网卡。

### 药方 2：用同一域名比对不同 DNS

```powershell
Resolve-DnsName www.microsoft.com
Resolve-DnsName www.microsoft.com -Server 1.1.1.1
Resolve-DnsName www.microsoft.com -Server 8.8.8.8
Resolve-DnsName www.microsoft.com -Server 223.5.5.5
```

读法：

- 默认 DNS 明显失败，公共 DNS 成功：优先怀疑当前 DNS 或 VPN/代理解析链。
- 不同 DNS 返回的地址差异很大：可能受到 CDN 地域、运营商或代理策略影响，不一定是错误。
- 公司内网或校园网域名不要随意改用公共 DNS，否则可能导致内网服务解析失败。

### 药方 3：检查本地缓存，不急着永久改 DNS

查看缓存：

```powershell
ipconfig /displaydns
```

如果确认缓存污染或解析异常，可以在记录原始症状后清理缓存：

```powershell
ipconfig /flushdns
```

注意：清 DNS 缓存是低风险操作，但第一次重新访问网站可能略慢。它不是长期优化方案，只能排除缓存层问题。

### 药方 4：换 DNS 前先写清楚回退

不建议 Agent 自动替用户执行永久 DNS 修改。更稳的做法是让用户手动在系统设置或路由器中调整，并记录原值。

建议决策：

- 家庭网络：优先在路由器或当前网卡里测试可信 DNS。
- 公司、校园、VPN：先不要改 DNS，避免内网解析失效。
- 国内常用服务慢：测试本地运营商 DNS、路由器 DNS、可信国内公共 DNS。
- 海外开发服务慢：测试代理/VPN 的 DNS 行为，不要只换本机 DNS。

### 药方 5：DNS 后悔药，恢复原解析

改 DNS 前先保存当前 DNS 配置：

```powershell
$backupRoot = Join-Path $env:USERPROFILE "Desktop\cht-network-backup"
New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
Get-DnsClientServerAddress | Export-Clixml (Join-Path $backupRoot "dns-before.xml")
Get-NetIPConfiguration | Export-Clixml (Join-Path $backupRoot "ip-config-before.xml")
```

如果原来是 DHCP 自动下发 DNS，后悔药是恢复为 DHCP DNS：

```powershell
Set-DnsClientServerAddress -InterfaceAlias "<你的网卡名>" -ResetServerAddresses
```

如果原来是手动 DNS，后悔药是恢复原服务器地址：

```powershell
Set-DnsClientServerAddress -InterfaceAlias "<你的网卡名>" -ServerAddresses @("<原DNS1>", "<原DNS2>")
```

不要在不知道原来是 DHCP 还是手动 DNS 的情况下直接回退。先打开 `dns-before.xml` 或查看保存的截图，确认原始状态。

## ✅ 验证
Verification

```powershell
Resolve-DnsName www.microsoft.com
ping /n 10 www.microsoft.com
Test-NetConnection www.microsoft.com -Port 443 -InformationLevel Detailed
```

验证标准：

- 域名解析稳定返回结果。
- 首次打开网站的等待时间下降。
- 改 DNS 后内网、公司 VPN、常用开发服务没有失效。
- 能说清楚原 DNS、新 DNS 和回退方式。

## 🔗 参考资料
References

- Microsoft Learn: Resolve-DnsName
- Microsoft Learn: Troubleshoot DNS client name resolution issues
- Microsoft Learn: Test-NetConnection
- Microsoft Learn: Set-DnsClientServerAddress
- Microsoft Learn: Export-Clixml

---

> 🧬 本滋补药方由 [@CyberHuaTuo](https://github.com/CyberHuaTuo) 贡献 · 名不正则网不通，先正 DNS 之名。
