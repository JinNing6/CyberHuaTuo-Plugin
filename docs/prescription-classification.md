# Prescription Classification

CyberHuaTuo classifies a prescription by its primary failure boundary. The category is retrieval metadata, not a replacement for framework, root-cause code, severity, or quality state.

## Stable departments

| Category key | Display label | Typical boundary |
|---|---|---|
| `dependency-and-version` | 依赖与版本科 | Import, package split, compatibility, upgrade |
| `runtime-and-lifecycle` | 运行时与生命周期科 | Process, module registry, thread, startup, shutdown |
| `data-and-serialization` | 数据与序列化科 | JSON, encoding, parsing, serialization |
| `api-and-schema` | API 与契约科 | Response model, validation, API contract |
| `storage-and-filesystem` | 存储与文件系统科 | Files, directories, atomic publication, disk state |
| `database-and-migration` | 数据库与迁移科 | Schema drift, migration, table, index |
| `security-and-credentials` | 安全与凭据科 | Keys, tokens, authentication, secret parsing |
| `agent-and-tooling` | Agent 与工具链科 | MCP, coding agents, tool calls, daemon integration |
| `network-and-integration` | 网络与集成科 | DNS, proxy, HTTP, external integration |
| `performance-and-resource` | 性能与资源科 | CPU, memory, latency, resource exhaustion |
| `ui-and-interaction` | 界面与交互科 | Rendering, state, input, layout |
| `system-configuration` | 系统与配置科 | Environment, registry, OS configuration |
| `other` | 综合科 | Legacy or genuinely cross-boundary cases |

Keys are stable machine identifiers. Chinese labels can evolve without breaking CLI, MCP, or index filters. Legacy cases without `disease_category` resolve to `other`; new generated drafts infer a category from their tags and failure text, and maintainers can correct it during review.

## Historical incident policy

A maintainer-confirmed incident may enter the library as `reviewed` without rerunning a costly external or production experiment when all of these are present:

1. A substantive symptom, root cause, exact prescription, verification procedure, and safety boundary.
2. `case_origin: maintainer-incident`, `origin_skill`, and `reviewed_at` provenance.
3. A reviewable primary documentation URL supporting the relevant API or platform semantics.
4. Explicit wording that the original incident was not rerun in the current review.

Historical provenance does not automatically create Gold. Promotion to `gold` still requires dated reproducible verification, a named verification method, and reviewable evidence URLs under the quality contract.

## Current reviewed seed set

| Origin skill | Department |
|---|---|
| `jsonl-ledger-bom-proof` | 数据与序列化科 |
| `python-test-module-registry-isolation` | 运行时与生命周期科 |
| `binary-credential-format-boundary` | 安全与凭据科 |
| `windows-atomic-directory-publish` | 存储与文件系统科 |
| `cloudflare-d1-worker-schema-drift-debug` | 数据库与迁移科 |
| `fastapi-response-contract-boundary` | API 与契约科 |
| `windows-process-liveness-safety` | 运行时与生命周期科 |
| `mcp-background-daemon-runtime-state` | Agent 与工具链科 |

## User path

```bash
cyberhuatuo departments
cyberhuatuo cure "Unexpected UTF-8 BOM"
cyberhuatuo cure "Unexpected UTF-8 BOM" --category data-and-serialization
cyberhuatuo cure "Unexpected UTF-8 BOM" --gold-only
cyberhuatuo search "schema drift" --category database-and-migration
```

`cure` is Gold-first. When Gold does not match, it may return one explicitly labeled Reviewed candidate for verification; `--gold-only` disables that fallback. Category filtering never changes a prescription's quality state.
