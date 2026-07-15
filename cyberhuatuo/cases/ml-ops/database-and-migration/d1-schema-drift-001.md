---
id: ml-ops-d1-schema-drift-001
title: "Worker 健康但业务接口因 D1 迁移漂移失败"
title_en: "Healthy Worker fails data routes because D1 migrations drifted"
framework: ml-ops
framework_version: "Cloudflare Workers and D1"
language: typescript
tags: [cloudflare-d1, migration, schema-drift, worker]
severity: critical
complexity: moderate
quality_status: reviewed
disease_category: database-and-migration
case_origin: maintainer-incident
origin_skill: cloudflare-d1-worker-schema-drift-debug
reviewed_at: "2026-07-15"
reviewed_by: "JinNing6"
match_signatures:
  - "Cloudflare D1 no such column Worker health 200"
  - "D1 migration schema drift business route fails"
environment:
  python_version: "not-applicable"
  os: any
created_at: "2026-07-15"
updated_at: "2026-07-15"
contributors:
  - github: JinNing6
source_url: "https://developers.cloudflare.com/d1/reference/migrations/"
related_cases: []
---

## 症状描述

新版本应用显示“后端不可用”或数据加载失败，但 Worker 的 `/health`、`/ready` 和基础配置接口均返回 200；只有依赖新字段的业务接口失败。

## 根因分析

已部署 Worker 代码查询了新增列、索引或表，而远端 D1 尚未应用对应迁移。健康检查通常不走同一条数据库查询路径，因此只能证明 Worker 可达，不能证明生产数据库契约与代码一致。

## 药方

先确认客户端指向正确生产主机，再定位失败路由使用的表和列。用远端 `PRAGMA table_info` 与 `wrangler d1 migrations list --remote` 比较真实 schema 和代码期望；确认漂移后，只应用已经审阅的前向迁移，不修改已执行过的迁移文件。

```bash
npx wrangler d1 execute <database> --remote --command "PRAGMA table_info(<table>);"
npx wrangler d1 migrations list <database> --remote
npx wrangler d1 migrations apply <database> --remote
```

## 验证

迁移后再次读取 `PRAGMA table_info`，确认相关迁移不再 pending，并执行只覆盖可疑字段的最小查询；最后复查原失败接口以及健康、就绪接口。本病例来自维护者既有生产故障复盘，本轮没有连接或修改任何远端 D1 数据库。

## 风险与回退

远端迁移是生产变更，执行前必须确认数据库身份、备份与前向修复路径。不要打印用户原始数据；列名、迁移状态和最小计数通常足以诊断。

## 参考资料

- https://developers.cloudflare.com/d1/reference/migrations/
