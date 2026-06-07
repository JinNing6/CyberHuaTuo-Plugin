# 🩺 CyberHuaTuo MCP Server

> 让所有 AI Coding 工具都能调用赛博华佗的「望闻问切」诊断能力
> Make CyberHuaTuo available in every AI coding tool

## 什么是 MCP？

**MCP (Model Context Protocol)** 是由 Anthropic 发起的开放协议，让 AI 助手能够连接外部工具和数据源。支持 MCP 的工具包括：

- **Claude Desktop** (Anthropic)
- **Cursor** (AI 代码编辑器)
- **Windsurf** (Codeium)
- **VS Code + GitHub Copilot**
- **Gemini CLI** (Google)
- **Continue** (开源 AI 编程助手)
- 以及更多...

## 快速开始

### ⚡ 方式一：一行直连（推荐！）

> **前提**：安装 [uv](https://docs.astral.sh/uv/getting-started/installation/)（Python 包管理工具）

在任意 AI 工具（Claude Desktop / Cursor / VS Code / Gemini CLI）中添加：

```json
{
  "mcpServers": {
    "cyberhuatuo": {
      "command": "uvx",
      "args": ["--from", "cyberhuatuo", "cyberhuatuo-mcp"]
    }
  }
}
```

> `uvx` 自动从 PyPI 安装并运行，无需手动操作。与 Anthropic 官方 MCP Server 相同的标准方式。

---

### 🧩 方式二：直接作为 Codex / Claude Code 插件加载

仓库根目录同时包含两个插件清单：

- `.codex-plugin/plugin.json`：Codex 插件清单，指向 `./skills/` 与 `./.mcp.json`
- `.claude-plugin/plugin.json`：Claude Code 插件清单，指向同一套 `./skills/` 与 `./.mcp.json`

在仓库根目录本地测试 Claude Code 插件：

```bash
claude --plugin-dir .
```

Claude Desktop MCPB assets live in `claude-desktop/manifest.json`, and the packaging workflow lives in `.github/workflows/package-claude-mcpb.yml`.

Marketplace catalogs:

- `.agents/plugins/marketplace.json`: Codex marketplace catalog pointing at the repository-root plugin.
- `.claude-plugin/marketplace.json`: Claude Code marketplace catalog pointing at the repository-root plugin.

Marketplace release SOP lives in [`docs/MARKETPLACE_RELEASE.md`](docs/MARKETPLACE_RELEASE.md). The current PyPI project `cyberhuatuo` already exists, so this repository must be added as an additional Trusted Publisher and released with a version newer than `0.1.0`; the PyPI workflow supports `release.published` plus a protected manual `workflow_dispatch` `release_tag` fallback that still verifies an existing `v*` tag, `origin/main` reachability, package-version equality, and OIDC publishing without `PYPI_TOKEN`. Claude Code community submission, Claude Desktop MCPB packaging, and Codex marketplace rollout are tracked there.

Marketplace readiness gate:

```bash
cyberhuatuo install-command --username your-github-username --framework langchain --release-tag v0.2.1 --target-contributors 3
cyberhuatuo market-ready --no-remote
cyberhuatuo launch-assets --username your-github-username --framework langchain --release-tag v0.2.1 --target-contributors 3
cyberhuatuo proof-pack --username your-github-username --framework langchain --release-tag v0.2.1 --target-contributors 3
python -m cyberhuatuo candidate-install-smoke --username your-github-username --framework langchain --release-tag v0.2.1 --target-contributors 3
cyberhuatuo first-invite --username your-github-username --invitee external-contributor-github-username --framework langchain --release-tag v0.2.1 --target-contributors 3 --source-url https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/123
cyberhuatuo bounty --username your-github-username --framework auto --top-n 8 --release-tag v0.2.1 --target-contributors 3
cyberhuatuo market-copy --username your-github-username --framework langchain --release-tag v0.2.1 --target-contributors 3
cyberhuatuo record-market --username your-github-username --framework langchain --channel pypi --status submitted --submission-url <reviewable public URL> --release-tag v0.2.1
cyberhuatuo market-status --username your-github-username --framework langchain --release-tag v0.2.1
python scripts/check_marketplace_release.py --no-remote

cyberhuatuo market-ready --remote --strict-remote --username your-github-username --framework langchain --release-tag v0.2.1 --target-contributors 3
python scripts/check_marketplace_release.py --remote --strict-remote --username your-github-username --framework langchain --release-tag v0.2.1 --target-contributors 3
```

The same short install decision is available inside Claude/Codex through the MCP tool `current_install_command`. It returns a **CyberHuaTuo Install Command** by fetching real PyPI JSON API latest-version proof: if PyPI is current, it recommends canonical `python -m pip install --upgrade cyberhuatuo`; if PyPI is stale or unverified, it prints the bounded **Git Tag Candidate Install Bridge** plus `candidate-install-smoke`, states that the bridge does not close the PyPI install loop, then routes directly to `challenge`, `proof-pack`, `market-copy`, and `traction-proof`.

The same preflight is available inside Claude/Codex through the MCP tool `marketplace_readiness_gate`. It first prints a **Flywheel Closure Verdict** with `closed`, `not closed`, or `unverified`, **Ready gates** / total gate counts, real evidence basis, blocking gates, and the non-fabrication rule. Its **Launch Closure Checklist** then orders the final public push gates: remote acquisition routes, PyPI Trusted Publisher, GitHub `release.published` trigger or protected `workflow_dispatch` fallback readiness, registry latest-version proof, first public proof, and recheck commands. It also prints a **First Public Proof Kit** with Prefilled Growth Flywheel Issue, Share Proof Issue, and Bounty Board Issue URLs, Created Growth Issue URL, Created Share Proof Issue URL, and Created Bounty Board Issue URL placeholders, a **Community Challenge Pack** with Prefilled Tournament Cup Issue, Prefilled Mentor Pact Issue, Prefilled Sect Recruitment Issue, Prefilled Season Board Issue, created-Issue placeholders, and commands for `tournament`, `mentor`, `sect-recruit`, and `season`, a **Protected Publish Fallback** command (`gh workflow run publish-pypi.yml -f release_tag=v0.2.1`) plus **GitHub Web Release**, **GitHub Actions workflow page**, PyPI Trusted Publisher settings links, a **Git Tag Candidate Install Bridge** plus **Candidate Install Smoke Gate** for stale PyPI recovery after the public tag exists, an **Install Decision Surface** that routes maintainers through `cyberhuatuo install-command` / MCP `current_install_command` before sending contributors to PyPI, Claude, Codex, or MCP marketplaces, Growth and Bounty `record-return` ledger commands, Share `record-share` attribution, an External Contributor Path, `cyberhuatuo bounty`, `market-copy` submission copy routing, recheck commands, and a copy-ready public proof post. The bridge keeps canonical `python -m pip install --upgrade cyberhuatuo` visible, may show `python -m pip install --upgrade "cyberhuatuo @ git+https://github.com/JinNing6/CyberHuaTuo-Plugin.git@v0.2.1"`, must be verified with `python -m cyberhuatuo candidate-install-smoke`, and does not close the PyPI install loop. When the maintainer needs to target one external contributor from that exposure, `first_contributor_invite` / `cyberhuatuo first-invite` returns a **First Contributor Invite Pack** with a local candidate snapshot, an Install Decision Surface, First Soul Ring issue URLs, record-session and challenge commands, proof rechecks, and copy-ready direct invite text that tells the maintainer to paste the Recommended Install. It also prints a **Local Launch Asset Audit** and the standalone `cyberhuatuo launch-assets` command gives the same read-only audit with a **Full Public Growth Release Bundle**, a **Public Release Operator Runbook** with `git push origin HEAD:main`, **GitHub Web Release**, **GitHub Actions workflow page**, `gh release create ... --verify-tag --notes-from-tag`, protected publish fallback, `cyberhuatuo market-copy`, candidate install smoke, and **Dirty Worktree Release Coverage**. For release-specific handoff, use `cyberhuatuo launch-assets --username your-github-username --framework langchain --release-tag v0.2.1 --target-contributors 3` so the runbook keeps the same target context. It may read `git status --porcelain`, but it does not stage files, publish releases, upload to PyPI, mutate remotes, or claim traction. When public APIs are rate-limited, `first_public_proof_pack` / `cyberhuatuo proof-pack` returns the **No-Network First Public Proof Pack** without fetching public metrics or inventing traction.

When the release operator needs an external-contributor target list, `soul_ring_bounty_board` / `cyberhuatuo bounty` returns a **Soul Ring Bounty Board** from real local framework coverage gap data. It ranks claimable First Soul Ring Prescription Issue routes, prints `challenge`, `first-invite`, `proof-pack`, `market-copy`, and `traction-proof` commands, and does not invent downloads, retention, repost counts, referrals, rewards, reviews, or fake contributors.

GitHub Bounty Board IssueOps is exposed through `.github/ISSUE_TEMPLATE/soul-ring-bounty-board.yml` and `.github/workflows/soul-ring-bounty-board.yml`; it comments the launch preflight, then `cyberhuatuo record-return --surface "Bounty Board Issue" --source-url <created Issue URL>`, `activation`, and `flywheel` before safe `cyberhuatuo bounty` runbook commands, and does not checkout or run repository scripts.

When the release operator needs copy for actual market forms, `marketplace_submission_copy` / `cyberhuatuo market-copy` returns a **Marketplace Submission Copy Pack** with PyPI listing copy, Claude MCPB listing copy, Codex plugin listing copy, GitHub Release post text, **GitHub Web Release** and **GitHub Actions workflow page** links, project URLs, install/validation commands, a **Submission Portals And Evidence URLs** section, public proof CTAs, a **Community Challenge Pack** for Tournament, Mentor Pact, Sect Recruitment, and Season Board routes, a Git Tag Candidate Install Bridge plus `candidate-install-smoke` for stale PyPI recovery, a **Marketplace Submission Ledger** block with `cyberhuatuo record-market` / `cyberhuatuo market-status`, and the same non-fabrication boundary used by traction proof. Submission portal anchors: PyPI Trusted Publisher settings: https://pypi.org/manage/project/cyberhuatuo/settings/publishing/; Claude Code plugin submit: https://claude.ai/settings/plugins/submit; Claude Connectors Directory submission guide: https://claude.com/docs/connectors/building/submission; Codex plugin evidence: `codex plugin marketplace add JinNing6/CyberHuaTuo-Plugin`. After a real PyPI, Claude Code, Claude Desktop MCPB, Codex, or GitHub Release submission exists, `record_marketplace_submission` / `cyberhuatuo record-market` records its reviewable public URL; `marketplace_submission_status` / `cyberhuatuo market-status` reports missing channels without inventing downloads, retention, repost counts, referrals, rewards, reviews, approvals, or fake contributors.

Marketplace install:

```bash
claude plugin marketplace add JinNing6/CyberHuaTuo-Plugin
claude plugin install cyberhuatuo-plugin@cyberhuatuo

codex plugin marketplace add JinNing6/CyberHuaTuo-Plugin
```

```bash
npm install -g @anthropic-ai/mcpb
mcpb validate claude-desktop
mcpb pack claude-desktop dist/cyberhuatuo-claude-desktop.mcpb
```

Codex 会通过 `.codex-plugin/plugin.json` 发现 CyberHuaTuo Skill 和 MCP Server；Claude Code 会通过 `.claude-plugin/plugin.json` 使用同一套 Skill/MCP 能力。

---

### 🚀 方式三：GitHub 直连（获取最新开发版）

如果想使用 GitHub 上的最新代码（可能包含尚未发布到 PyPI 的新功能）：

#### Claude Desktop

编辑 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "cyberhuatuo": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/JinNing6/CyberHuaTuo-Plugin", "cyberhuatuo-mcp"]
    }
  }
}
```

#### Cursor

在 Cursor 设置中添加 MCP Server：

```json
{
  "mcpServers": {
    "cyberhuatuo": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/JinNing6/CyberHuaTuo-Plugin", "cyberhuatuo-mcp"]
    }
  }
}
```

#### VS Code (Copilot Chat)

在 `.vscode/settings.json` 中添加：

```json
{
  "mcp": {
    "servers": {
      "cyberhuatuo": {
        "command": "uvx",
        "args": ["--from", "git+https://github.com/JinNing6/CyberHuaTuo-Plugin", "cyberhuatuo-mcp"]
      }
    }
  }
}
```

#### Gemini CLI

在 `~/.gemini/settings.json` 中添加：

```json
{
  "mcpServers": {
    "cyberhuatuo": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/JinNing6/CyberHuaTuo-Plugin", "cyberhuatuo-mcp"]
    }
  }
}
```

> **工作原理**：
> `uvx` 会自动从 GitHub 仓库下载代码 → 安装依赖 → 启动 MCP Server。
> 首次运行时会自动从 GitHub 获取最新的知识库数据。
> 无需手动 clone 或 pip install。

---

### 方式四：本地安装（开发者 / 离线使用）

如果你需要修改代码或离线使用：

```bash
# 1. 克隆仓库
git clone https://github.com/JinNing6/CyberHuaTuo-Plugin.git
cd CyberHuaTuo

# 2. 安装依赖
pip install -r requirements.txt
```

然后在 AI 工具中配置：

```json
{
  "mcpServers": {
    "cyberhuatuo": {
      "command": "python",
      "args": ["-m", "cyberhuatuo.mcp_server"],
      "cwd": "/path/to/CyberHuaTuo"
    }
  }
}
```

> **提示**: 将 `/path/to/CyberHuaTuo` 替换为你的实际项目路径。

### 3. 开始使用

配置完成后，在 AI 助手中直接提问即可：

- *"帮我诊断这个 LangChain 报错: ImportError: cannot import name 'ChatOpenAI' from 'langchain'"*
- *"搜索一下 CrewAI 相关的已知问题"*
- *"对这段 Agent 代码做安全体检"*

## 🌐 品牌矩阵 (Brand Matrix)

为了保护开源生态并提供全球化的无缝使用体验，CyberHuaTuo 团队在 PyPI 上建立了一系列涵盖东西方古代医学神祗的**官方别名包（Alias Packages）**。

您可以执行、安装以下**任意一个**名字，它们都会自动包含并重定向至最核心的 `cyberhuatuo` 引擎：

*   **东方建安神医 (核心)**：`cyberhuatuo`, `openhuatuo`
*   **希罗神话系**：`cyber-asclepius`, `open-asclepius`, `cyber-panacea`, `open-panacea`
*   **人类医学先驱**：`cyber-hippocrates`, `open-hippocrates`, `cyber-galen`, `open-galen`
*   **古老文明极客**：`cyber-imhotep`, `open-imhotep`, `cyber-avicenna`, `open-avicenna`

无论您身处何种文化语境，执行 `uvx <上述任意名字>` 即可直接唤醒赛博神医为你诊断代码。

---

## 可用工具 (Tools)

### 🩺 `diagnose` — 望闻问切 AI 诊断

使用知识库 + LLM 对报错信息进行「望闻问切」诊断，给出药方。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | ✅ | 报错信息或问题描述 |
| `framework` | string | ❌ | 按框架过滤 |
| `top_k` | int | ❌ | 参考病例数量（默认 5） |

### 🔍 `search_knowledge_base` — 向量语义搜索

在病例知识库中进行向量语义搜索，无需 LLM API Key。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | ✅ | 搜索查询 |
| `framework` | string | ❌ | 按框架过滤 |
| `severity` | string | ❌ | 按严重性过滤（low/medium/high/critical） |
| `complexity` | string | ❌ | 按复杂度过滤（simple/moderate/complex/extreme） |
| `top_k` | int | ❌ | 返回数量（默认 5） |

### 🛡️ `security_checkup` — Agent 代码安全体检

六经脉安全检测：沙箱隔离、密钥安全、Prompt 安全、输出安全、韧性设计、可观测性。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `code` | string | ✅ | 要检测的代码 |

### 📚 `fetch_official_docs` — 获取官方文档

通过 Context7 获取 50+ 框架的最新官方文档（LangChain、PyTorch、FastAPI 等）。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `framework` | string | ✅ | 框架标识（如 langchain, pytorch） |
| `query` | string | ✅ | 查询内容 |
| `top_k` | int | ❌ | 文档片段数量（默认 5） |

### ⛏️ `mine_github_issue` — GitHub Issue 淘金

从 GitHub Issue 中提取问题和解决方案，提炼为标准病例格式。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `owner` | string | ✅ | 仓库所有者 |
| `repo` | string | ✅ | 仓库名称 |
| `issue_number` | int | ✅ | Issue 编号 |

### 📋 `list_frameworks` — 查询支持框架

列出赛博华佗覆盖的所有框架和技术栈。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `category` | string | ❌ | 按分类过滤（agent/foundation/infrastructure） |
| `search` | string | ❌ | 关键词搜索 |

### 📥 `save_prescription` — 保存贡献药方（本地 + 自动同步 GitHub）

保存药方到本地知识库。如果配置了 `GITHUB_TOKEN` 且 `GITHUB_SYNC_ENABLED=true`，会自动推送到 GitHub 仓库。保存后会自动分配 ID、重载缓存索引，并返回**贡献者名医堂称号**和**即时追环**结算。

当 `contributor_github` 不是 `anonymous` 时，返回结果会显示本次贡献对应的丹术方向、当前魂环、`下一环` 目标，以及可直接复制的分享命令：`cyberhuatuo card <github_username>`。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | ✅ | 标题（建议以中文为主，20字以内） |
| `prescription` | string | ✅ | 详细修复方案 (能解决问题的代码/思路等) |
| `framework` | string | ✅ | 框架表示 (如 `langchain`, `fastapi`) |
| `symptom` | string | ❌ | 针对症状的详细描述 |
| `error_message`| string | ❌ | 极简报错或 Traceback 会有助于之后被匹配 |
| `root_cause` | string | ❌ | 根本原因分析解释 |
| `severity` | string | ❌ | 严重性 (`low`/`medium`/`high`/`critical`) |
| `complexity` | string | ❌ | 复杂性等级 (`simple`/`moderate`/`complex`/`extreme`) |
| `tags` | array | ❌ | 自定义标签集 |
| `title_en` | string | ❌ | 对应的英文标题 |
| `contributor_github` | string | ❌ | 贡献者 GitHub 用户名（用于名医堂称号追踪） |

### 🌐 `upload_prescription` — 上传药方到 GitHub（必须配置 GITHUB_TOKEN）

与 `save_prescription` 参数完全相同，但**强制要求**同步到 GitHub 仓库。适合外部贡献者通过 MCP 直接向社区贡献药方。无 `GITHUB_TOKEN` 时会返回配置引导。

支持两种同步策略（自动选择）：
- **直接推送**：如果你是仓库 Owner/Collaborator
- **Fork + PR**：外部贡献者自动 Fork 并创建 PR

上传成功后同样返回即时追环结算，例如：`下一环: 黄环 · 再贡献 1 方即可点亮。` 这让智能体可以把“贡献成功”直接转化为“继续冲下一环”和“分享修为卡”的下一步动作。

### 🏅 `my_contribution_stats` — 查询名医堂称号

查询指定 GitHub 用户在赛博华佗知识库中的贡献次数和当前称号。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `github_username` | string | ✅ | GitHub 用户名 |

**称号体系**：

| 称号 | 条件 |
|:---:|:---:|
| 🏥 坐堂医师 Resident Doctor | 1+ 贡献 |
| ⚕️ 主治医师 Attending Physician | 3+ 贡献 |
| 👨‍⚕️ 名医 Renowned Doctor | 5+ 贡献 |
| 🌟 神医 Divine Doctor | 10+ 贡献 |
| 👑 华佗再世 Hua Tuo Reborn | 20+ 贡献 |

### 🔮 `first_soul_ring_challenge` — 生成第一魂环挑战入口

当用户问“怎么获得第一魂环”“开始魂环挑战”或需要一个新手贡献入口时调用。工具会返回与 CLI `cyberhuatuo challenge --username <github_username> --framework <framework>` 对齐的一屏路径：提交真实修复、查看排名、生成分享卡，并保持 `下一环` 目标可见。

### 🔮 `soul_ring_mission_hall` — 生成魂环任务大厅

当用户问“我该怎么开始”“给我一个魂环任务大厅”“把 Issue、PR、个人魂环和宗门行动串起来”“让这个项目更容易爆火传播”时调用。工具会基于当前真实 GitHub 贡献快照生成一屏任务大厅：First Soul Ring Issue、PR Settlement、个人 `challenge` / `quest` / `card` / `campaign`、MCP 安装、`sect-hall` / `sect-quest` / `sect-arena` 命令和可复制传播文案。对应 CLI：`cyberhuatuo mission --username <github_username> --framework <framework> --sect <sect_name> --members <members...>`。

### `soul_ring_bounty_board` -- generate the Soul Ring Bounty Board

Use when PyPI / Claude / Codex launch attention needs to become concrete first-ring contribution tasks instead of generic community copy. The tool reads real local case files and supported framework definitions, ranks current framework coverage gaps, creates claimable First Soul Ring Prescription Issue routes, and prints `cyberhuatuo bounty`, `challenge`, `first-invite`, `proof-pack`, `market-copy`, and `traction-proof` commands. It does not fetch public metrics, write ledger events, create issues, publish releases, upload to PyPI, submit marketplace forms, or invent downloads, retention, repost counts, referrals, rewards, reviews, or fake contributors. Corresponding CLI: `cyberhuatuo bounty --username <github_username> --framework auto --top-n <N> --release-tag <tag> --target-contributors <N>`.

### 🔮 `soul_ring_launch_scroll` — 生成市场爆发启动卷轴

当用户问“怎么推到 PyPI / Claude / Codex”“准备发布帖”“生成首发传播作战面”“让魂环体系爆起来”时调用。工具会把当前真实发布资产串成一屏 Launch Scroll：PyPI 包、Claude Code 插件、Claude Desktop MCPB、Codex 插件、First Soul Ring Issue、`accepted-prescription` 晋升 workflow、GitHub Discussion / Release Post、X / Weibo 和 Agent Prompt。对应 CLI：`cyberhuatuo launch --username <github_username> --framework <framework> --release-tag <tag>`。

### `soul_ring_launch_campaign` -- generate the Soul Ring Launch Campaign

Use when PyPI / Claude / Codex / GitHub / X / Weibo launch attention is cold and needs a target first-ring contributor campaign instead of generic launch copy. The tool returns the release tag, launch surface, target contributor count, current real ranked contributors, Prefilled Growth Flywheel Issue, Prefilled Share Proof Issue, activation / flywheel / share-leaderboard commands, GitHub Discussion / Release Post copy, social copy, an agent prompt, and a Campaign Recap And Next Sprint section. The recap reports observed real contributors, reached-vs-target, shortfall, a disclosed next-target rule, copy-ready recap text, the next `growth_campaign` command, and `traction-proof --record-snapshot` proof recording. It does not invent downloads, retention, repost counts, referrals, rewards, Spirit Power, campaign-specific conversions, or fake users. Corresponding CLI: `cyberhuatuo launch-campaign --username <github_username> --framework <framework> --release-tag <tag> --target-contributors <N>`.

### `current_install_command` -- get the current public install command

Use before sending a contributor from PyPI, Claude, Codex, or an MCP marketplace into the First Soul Ring loop. The tool fetches real PyPI JSON API latest-version proof and returns a **CyberHuaTuo Install Command**: canonical `python -m pip install --upgrade cyberhuatuo` only when PyPI latest matches the local package version, otherwise the bounded Git Tag Candidate Install Bridge plus `candidate-install-smoke`, `challenge`, `proof-pack`, `market-copy`, and `traction-proof` follow-ups. It does not publish releases, write ledgers, submit marketplace forms, or invent downloads, retention, referrals, rewards, approvals, or fake contributors. Corresponding CLI: `cyberhuatuo install-command --username <github_username> --framework <framework> --release-tag <tag>`.

### `marketplace_readiness_gate` -- run the Marketplace Readiness Gate

Use before pushing CyberHuaTuo to PyPI, Claude Code, Claude Desktop MCPB, Codex, or any public agent marketplace. The tool returns the same first-screen **Flywheel Closure Verdict** and **Launch Closure Checklist** as `cyberhuatuo market-ready`: `closed` / `not closed` / `unverified`, **Ready gates** / total gate counts, real evidence basis, blocking gates, remote acquisition routes, PyPI Trusted Publisher, GitHub `release.published` trigger or protected `workflow_dispatch` fallback readiness, registry latest-version proof, first public proof, and recheck commands. It also returns a **First Public Proof Kit** with Prefilled Growth Flywheel Issue, Share Proof Issue, and Bounty Board Issue URLs, Created Growth Issue URL, Created Share Proof Issue URL, and Created Bounty Board Issue URL placeholders, a **Community Challenge Pack** with Prefilled Tournament Cup Issue, Prefilled Mentor Pact Issue, Prefilled Sect Recruitment Issue, and Prefilled Season Board Issue form URLs, a **Protected Publish Fallback** command (`gh workflow run publish-pypi.yml -f release_tag=<tag>`) plus **GitHub Web Release**, **GitHub Actions workflow page**, PyPI Trusted Publisher settings links, a **Git Tag Candidate Install Bridge** (`python -m pip install --upgrade "<project> @ git+https://github.com/<owner>/<repo>.git@<tag>"`) plus Candidate Install Smoke Gate that does not close the PyPI install loop, an **Install Decision Surface** that routes through `cyberhuatuo install-command` / MCP `current_install_command` before any marketplace invite, Growth and Bounty `record-return` ledger commands, Share `record-share` attribution, `market-copy` submission copy routing, recheck commands, and a copy-ready public proof post, plus a **Local Launch Asset Audit** with minimal `git add` commands, a **Full Public Growth Release Bundle**, a **Public Release Operator Runbook** with **GitHub Web Release**, **GitHub Actions workflow page**, `gh release create`, `gh workflow run publish-pypi.yml`, `cyberhuatuo market-copy`, and `python -m cyberhuatuo candidate-install-smoke`, and **Dirty Worktree Release Coverage** for changed files that would otherwise be omitted from the market push. In remote mode it fetches GitHub Contents API, GitHub Releases API, and PyPI JSON API state; it does not create releases, publish to PyPI, or mutate remote state. Corresponding CLI: `cyberhuatuo market-ready --remote --strict-remote --username <github_username> --framework <framework> --release-tag <tag> --target-contributors <N>`.

### `local_launch_asset_audit` -- run the Local Launch Asset Audit

Use when the remote default branch is missing IssueOps files or before pushing a PyPI / Claude / Codex release PR. The tool validates local Issue Forms, comment-only workflows, package metadata, plugin manifests, Trusted Publishing workflow, Claude MCPB assets, and shared MCP entrypoints, then prints exact minimal `git add` commands, a **Full Public Growth Release Bundle** for docs / package metadata / IssueOps / workflows / runtime growth modules / scripts / tests, and **Dirty Worktree Release Coverage** from read-only `git status --porcelain`. It does not stage files, publish releases, upload to PyPI, mutate remotes, or claim traction. Corresponding CLI: `cyberhuatuo launch-assets --username <github_username> --framework <framework> --release-tag <tag> --target-contributors <N>`.

### `first_public_proof_pack` -- generate the No-Network First Public Proof Pack

Use when GitHub/PyPI public APIs are rate-limited, marketplace review is pending, or the operator needs the first proof runbook without remote preflight. The tool returns Prefilled Growth Flywheel Issue, Share Proof Issue, and Bounty Board Issue URLs, Created Growth Issue URL, Created Share Proof Issue URL, and Created Bounty Board Issue URL placeholders, a **Community Challenge Pack** with Prefilled Tournament Cup Issue, Prefilled Mentor Pact Issue, Prefilled Sect Recruitment Issue, and Prefilled Season Board Issue form URLs plus copy-ready public event commands, a **Protected Publish Fallback** block with `gh workflow run publish-pypi.yml -f release_tag=<tag>`, `gh run list --workflow publish-pypi.yml --limit 5`, **GitHub Web Release**, **GitHub Actions workflow page**, PyPI Trusted Publisher settings links, a **Git Tag Candidate Install Bridge** that keeps canonical `pip install <project>` visible and offers a direct git tag candidate only after the public tag exists, a Candidate Install Smoke Gate command, an **Install Decision Surface** that tells operators to paste the `cyberhuatuo install-command` / MCP `current_install_command` Recommended Install, terminal Growth and Bounty `record-return` CLI ledger commands, Share `record-share` attribution, `cyberhuatuo bounty`, an **External Contributor Path** with pasted Recommended Install, first-session command, first contribution command, First Soul Ring Prescription Issue, Share Proof Issue URL, created-Issue proof rule, contributor-counting rule, recheck commands, and copy-ready public proof / invite text. The fallback still requires the PyPI Trusted Publisher to match this repository, workflow file, and `pypi` environment; no `PYPI_TOKEN` fallback is allowed. The bridge does not close the PyPI install loop; recheck PyPI latest-version proof before claiming public install readiness. It does not fetch public metrics, write ledger events, create issues, publish releases, upload to PyPI by itself, or invent traction. Corresponding CLI: `cyberhuatuo proof-pack --username <github_username> --framework <framework> --release-tag <tag> --target-contributors <N>`.

### `first_contributor_invite` -- generate the First Contributor Invite Pack

Use when a PyPI / Claude / Codex / GitHub / X / Weibo launch surface needs to target one external contributor after a first public proof route exists. The tool returns a local Candidate Snapshot, First Soul Ring Prescription Issue URL, Share Proof Issue URL, `record-session` command, `challenge` command, proof-pack / market-copy / traction-proof recheck commands, contributor-counting rule, and copy-ready direct invite text. It does not fetch public metrics, write ledger events, create issues, publish releases, upload to PyPI, submit marketplace forms, or invent downloads, retention, repost counts, referrals, rewards, reviews, or fake contributors. Corresponding CLI: `cyberhuatuo first-invite --username <github_username> --invitee <github_username> --framework <framework> --release-tag <tag> --target-contributors <N> --source-url <created Growth Issue URL>`.

### `marketplace_submission_copy` -- generate the Marketplace Submission Copy Pack

Use when PyPI / Claude / Codex submission forms need consistent channel-specific copy after release gates are ready. The tool returns PyPI listing copy and project URLs, Claude MCPB listing copy and validation commands, Codex plugin listing copy and install checks, GitHub Release post text, public proof CTAs with Prefilled Bounty Board Issue, Created Bounty Board Issue URL, Growth and Bounty `record-return`, Share `record-share`, `cyberhuatuo bounty`, `traction-proof`, a **Community Challenge Pack** for Tournament, Mentor Pact, Sect Recruitment, and Season Board issue routes, Git Tag Candidate Install Bridge plus Candidate Install Smoke Gate commands, Marketplace Submission Ledger record commands, and a copy-ready maintainer announcement. It does not fetch public metrics, write ledger events, publish releases, upload to PyPI, submit marketplace forms, invent downloads, retention, repost counts, referrals, rewards, reviews, fake contributors, or close the PyPI install loop. Corresponding CLI: `cyberhuatuo market-copy --username <github_username> --framework <framework> --release-tag <tag> --target-contributors <N>`.

### `record_marketplace_submission` -- record a Marketplace Submission Ledger event

Use after a real PyPI, Claude Code, Claude Desktop MCPB, Codex, GitHub Release, or agent-marketplace submission exists. The tool requires a reviewable public URL, channel, status, release tag, and appends one local Marketplace Submission Ledger row. It does not submit forms, publish packages, claim approval unless the recorded status is approved or published, or invent downloads, retention, repost counts, referrals, rewards, reviews, approvals, or fake contributors. Corresponding CLI: `cyberhuatuo record-market --username <github_username> --framework <framework> --channel <channel> --status <status> --submission-url <https-url> --release-tag <tag>`.

### `marketplace_submission_status` -- report the Marketplace Submission Ledger

Use when PyPI / Claude / Codex / GitHub Release launch work needs a channel-by-channel submission recap after `marketplace_submission_copy`. The tool reads the local Marketplace Submission Ledger, shows latest recorded status and reviewable public URL for PyPI, Claude Code, Claude Desktop MCPB, Codex, and GitHub Release, prints missing `record-market` commands, and routes back to `market-copy` / `traction-proof` without inventing approvals or adoption metrics. Corresponding CLI: `cyberhuatuo market-status --username <github_username> --framework <framework> --release-tag <tag>`.

### `soul_ring_traction_proof` -- generate the Soul Ring Traction Proof

Use when PyPI / Claude / Codex launch work is public but breakout is still unproven. The tool fetches GitHub REST API repository signals, GitHub Pull Requests API author proof, GitHub Contents API readiness for default-branch IssueOps forms/workflows, GitHub Releases API readiness for the requested tag and its `release.published` PyPI workflow trigger or protected `workflow_dispatch` fallback provenance, PyPI JSON API project metadata, PyPI package readiness against the local growth-tool version, and local activation/share ledger events, then reports Target contributor progress from real public issue authors, public PR authors, and ledger actors only. Public API fetch failures or rate limits inline the **No-Network First Public Proof Pack** so operators can open proof Issues and record created URLs without a second tool call, and the next proof commands include `cyberhuatuo market-copy` so marketplace submission copy stays attached to the proof path. PR authors count as contributor identities, but PRs stay separate from IssueOps issue counts. Stars, forks, watchers, subscribers, downloads, reposts, retention, referrals, and rewards are not contributor progress; downloads are not used. Missing remote IssueOps files and older PyPI latest versions are launch blockers; missing/draft/prerelease GitHub Releases become provenance warnings when PyPI latest-version proof is already current through the protected fallback. This read-only tool does not write snapshot history. Corresponding CLI: `cyberhuatuo traction-proof --username <github_username> --framework <framework> --release-tag <tag> --target-contributors <N>`.

### `record_soul_ring_traction_snapshot` -- record append-only traction history

Use only when the user explicitly asks to persist traction history after a real launch check. The tool runs the same GitHub REST API, GitHub Pull Requests API, GitHub Contents API IssueOps readiness, GitHub Releases API `release.published` trigger readiness, PyPI JSON API package readiness, and local activation/share ledger proof, appends one opt-in append-only JSONL snapshot, and compares velocity deltas against the previous real snapshot. It records PR author proof as its own public proof surface and does not mix PRs into IssueOps issue counts. It also stores remote IssueOps readiness, release trigger readiness, and PyPI package readiness so future recaps can distinguish closed-loop growth from blocked install/submission routes. It does not record or invent downloads, retention, repost counts, referrals, rewards, private analytics, or fake contributors. Corresponding CLI: `cyberhuatuo traction-proof --username <github_username> --framework <framework> --release-tag <tag> --target-contributors <N> --record-snapshot`.

### `soul_ring_growth_flywheel` -- generate the Soul Ring Growth Flywheel

Use when the user asks whether the Soul Ring system has a real flywheel, where growth is blocked after PyPI / Claude / Codex launch attention, or how to turn external attention into first-ring contributors without vanity metrics. The tool returns a current real-data operating snapshot across marketplace attention, the local activation ledger, first-ring activation, repeat contribution, collaboration / sect, and public sharing. It exposes the primary bottleneck, `record-return`, `activation`, `record-share`, `share-report`, `soul_ring_bounty_board` / `cyberhuatuo bounty`, next callable CLI commands, `.github/ISSUE_TEMPLATE/soul-ring-growth-flywheel.yml`, `.github/workflows/soul-ring-growth-flywheel.yml`, `.github/ISSUE_TEMPLATE/soul-ring-share-proof.yml`, `.github/workflows/soul-ring-share-proof.yml`, a public Prefilled Growth Flywheel Issue URL using issue-form field ids, and the disclosure that downloads, retention, and attribution are missing unless real data is connected. Do not add `labels`, `assignees`, or `milestone` query parameters to the public URL. Corresponding CLI: `cyberhuatuo flywheel --username <github_username> --framework <framework> --sect <sect_name> --members <members...> --top-n <N>`.

### `soul_ring_activation_funnel` -- generate the Soul Ring Activation Funnel

Use when market launch attention from PyPI / Claude / Codex / GitHub / X / Weibo needs to be checked against real recorded events. The tool reads the local JSONL activation ledger, separates external return, first-session exposure, first prescription, repeat contribution, collaboration / sect, and public share attribution, names the weakest conversion stage, routes back to `soul_ring_growth_flywheel`, and includes the `market-ready --remote --strict-remote` Launch Closure Checklist command before any public launch claim. Missing or unwritable ledger history is disclosed; downloads, retention, and attribution metrics are not invented. Corresponding CLI: `cyberhuatuo activation --username <github_username> --framework <framework> --sect <sect_name> --members <members...> --top-n <N>`.

### `record_soul_ring_external_return` -- record a reviewable external return

Use before running contribution commands for a public IssueOps or marketplace visitor. Require a reviewable public `source_url` from PyPI, Claude, Codex, GitHub, X, Weibo, Discord, or another real surface; write one `external_return` event into the local activation ledger; disclose write or URL validation failures instead of claiming activation. On success, the **Next External Contributor Invite** card routes that proof directly into `first_contributor_invite` and `first_public_proof_pack` MCP equivalents plus terminal `cyberhuatuo first-invite` / `cyberhuatuo proof-pack` commands for the next external contributor. Corresponding CLI: `cyberhuatuo record-return --username <github_username> --framework <framework> --surface "<surface>" --source-url <https-url>`.

### `record_soul_ring_first_session` -- record first-session exposure

Use when a real user opens CyberHuaTuo inside Claude, Codex, or another MCP client before submitting a first prescription. This writes a separate `first_session` event so first-session exposure is not confused with successful contribution side effects. Corresponding CLI: `cyberhuatuo record-session --username <github_username> --framework <framework> --surface "<surface>" --source-url <https-url>`.

### `record_soul_ring_share_attribution` -- record a reviewable public share URL

Use after a soul-ring card, campaign post, launch post, GitHub Discussion, X, or Weibo share is actually published. Require a reviewable public `share_url`, optionally bind the original `source_url`, write one `share_attribution` event into the local activation ledger, then route the recorded share proof through the **Next External Contributor Invite** card into `first_contributor_invite` and `first_public_proof_pack` MCP equivalents plus terminal `cyberhuatuo first-invite` / `cyberhuatuo proof-pack` commands for the next external contributor. Corresponding CLI: `cyberhuatuo record-share --username <github_username> --framework <framework> --share-url <https-url>`.

### `soul_ring_share_attribution_report` -- generate the Soul Ring Share Attribution Report

Use when public share attribution exists and the user needs to prove whether sharing is pulling contributors back into the Soul Ring loop. The tool reads the local JSONL activation ledger and summarizes contribution pull, proof URLs, source-to-share bridges, actor pull, artifact pull, the current proof bottleneck, and the next callable proof command. It explicitly refuses to invent downloads, retention, repost counts, referral conversions, or rewards. Corresponding CLI: `cyberhuatuo share-report --username <github_username> --framework <framework> --top-n <N>`.

### `soul_ring_share_proof_leaderboard` -- generate the Soul Ring Share Proof Leaderboard

Use when a market launch, campaign post, GitHub Discussion, X, Weibo, Discord, or agent-community post has real public share URLs and the user needs a ranked proof board. The tool reads the local JSONL activation ledger, ranks actors only by unique reviewable public http(s) share URLs, exposes a Prefilled Share Proof Issue URL, and refuses to invent downloads, retention, repost counts, referral conversions, rewards, or Spirit Power. Corresponding CLI: `cyberhuatuo share-leaderboard --framework <framework> --top-n <N>`.

### 🔮 `soul_ring_breakthrough_ladder` — 生成魂环突破阶梯

当用户问“下一环还差多少”“完整魂环门槛是什么”“给我突破路线图”“怎么把贡献持续刷起来”时调用。工具会基于当前真实方向贡献数生成 **Soul Ring Breakthrough Ladder**：当前魂环、下一门槛、完整 1 / 2 / 4 / 7 / 11 / 16 / 26 / 41 / 61 / 81 阈值地图、`quest` / `upload` / `campaign` / `mission` 命令和可复制突破文案。对应 CLI：`cyberhuatuo ladder <github_username> --framework <framework>`。

### `record_soul_ring_evidence` -- record reviewable high-realm gate evidence

Use when a high-realm Soul Ring gate needs public evidence instead of an internal field edit. The tool returns a **Soul Ring Evidence Card**, requires reviewable public evidence through `source_url`, appends one local append-only JSONL evidence event, reports evidence total and evidence-backed count, states whether the evidence did or did not trigger an evidence-backed breakthrough, and keeps progress, ranks, rewards, downloads, and contributors not invented. Corresponding CLI: `cyberhuatuo evidence <github_username> --framework <framework> --amount <N> --source-url <https-url>`.

### 🔮 `profile_badge_kit` — 生成 GitHub Profile 魂环徽章包

当用户问“生成我的魂环徽章”“怎么放到 GitHub Profile”“README 徽章”时调用。工具会返回可直接复制的 Shields.io Markdown 徽章，并附带真实贡献数、当前魂环、主修方向、`下一环` 目标和继续追环命令。对应 CLI：`cyberhuatuo badge <github_username>`。

### `soul_ring_visual_artifact` -- generate chat-visible Soul Ring GIF/PNG

Use when the user wants to see Soul Rings, breakthrough progress, cultivation status, or a shareable achievement moment directly inside Codex, Claude, or another agent chat. The tool writes a local animated GIF plus PNG fallback, returns Markdown image embeds, includes the current real contribution snapshot, candidate/PyPI/MCP install commands, and a `record-share` attribution command. This path is the default visual route because Markdown GIF rendering is more portable across agent clients than MCP `ui://` widgets. It does not invent ranks, downloads, retention, referrals, rewards, or fake contributors. Corresponding CLI: `cyberhuatuo visual <github_username> --framework <framework> --output-dir <dir>`.

### 🔮 `soul_ring_quest_board` — 生成追环任务板

当用户问“下一环怎么追”“给我今天的魂环任务”“我要刷魂环”时调用。工具会基于真实贡献统计选择目标框架，返回当前魂环、`下一环` 目标、真实目标仓库的 issue 淘金命令、`upload_prescription` / CLI upload 路径，以及徽章和分享卡命令。对应 CLI：`cyberhuatuo quest <github_username> --framework <framework>`。

### 🔮 `soul_ring_campaign_pack` — 生成魂环传播包

当用户问“帮我发魂环挑战”“生成传播文案”“我要把魂环发到 GitHub / X / 微博”时调用。工具会基于当前真实贡献快照返回 GitHub Profile / README、X / Weibo、GitHub Discussion / PR Comment 和 Agent Prompt 四类可复制文本，并附带 `cyberhuatuo quest`、`badge`、`card`、新手 `challenge` 命令。对应 CLI：`cyberhuatuo campaign <github_username> --framework <framework>`。

### 🔮 `soul_ring_duel_card` — 生成魂环对决邀请卡

当用户问“帮我挑战一个朋友”“生成魂环对决”“点名某人一起刷魂环”时调用。工具会基于双方当前真实贡献快照返回公开对决公式、双方真实药方数和排名、X / Weibo 文案、GitHub Discussion / PR Comment 文案，以及双方 `challenge` / `quest` / `campaign` 命令。对应 CLI：`cyberhuatuo duel <challenger_github> <rival_github> --framework <framework>`。

### 🔮 `soul_ring_mentor_pact` — 生成魂环师徒契约

当用户问“让某人带新人”“生成师徒契约”“帮徒弟点亮第一环”“创建公开带教帖”时调用。工具会基于导师和徒弟当前真实药方数生成 **Soul Ring Mentor Pact**：导师战力、徒弟基础、突破目标、导师审核职责、X / Weibo 文案、GitHub Discussion / PR Comment 文案，以及 `challenge` / `quest` / `upload` / `ladder` / `duel` / `campaign` 命令。对应 CLI：`cyberhuatuo mentor <mentor_github> <apprentice_github> --framework <framework>`。

### 🔮 `soul_ring_tournament_bracket` — 生成魂环杯赛对阵表

当用户问“生成魂环杯赛”“做一个多人魂师赛”“把几个朋友拉进公开比赛”“创建 GitHub 贡献淘汰赛”时调用。工具会基于参赛 GitHub 用户当前真实药方数生成 **Soul Ring Tournament Bracket**：种子位、当前冠军快照、下一追赶目标、首轮 `duel` 对阵、奇数轮空、X / Weibo 文案、GitHub Discussion / PR Comment 文案，以及 `challenge` / `quest` / `ladder` / `campaign` 命令。对应 CLI：`cyberhuatuo tournament <github_usernames...> --framework <framework> --event <event_name>`。

### 🔮 `soul_ring_tournament_settlement` — 生成魂环杯赛结算帖

当用户问“结算魂环杯赛”“发布当前比赛结果”“生成赛后战报”“谁当前领先”“把杯赛变成下一轮挑战帖”时调用。工具会基于参赛 GitHub 用户当前真实药方数生成 **Soul Ring Tournament Settlement**：当前胜者、第二名、领先差距或待结算状态、下一轮挑战钩子、X / Weibo 文案、GitHub Discussion / PR Comment 文案，以及 `tournament` / `duel` / `challenge` / `quest` / `ladder` / `campaign` 命令。对应 CLI：`cyberhuatuo tournament-settle <github_usernames...> --framework <framework> --event <event_name>`。

### 🔮 `soul_ring_arena_snapshot` — 生成魂环竞技场快照

当用户问“生成魂环竞技场”“发一个封神榜快照”“谁在榜上我该追谁”时调用。工具会基于当前真实排行榜返回 Top N、公开计分公式、用户当前位置、下一位追赶目标、X / Weibo 文案、GitHub Discussion / PR Comment 文案，以及 `quest` / `campaign` / `duel` 命令。对应 CLI：`cyberhuatuo arena <github_username> --top-n <N>`。

### 🔮 `soul_ring_season_board` — 生成魂环赛季榜单

当用户问“生成魂环赛季榜”“谁是当前冠军”“做一个排行榜活动帖”“把当前榜单发到 Discussion 或 PR 评论里”时调用。工具会基于当前真实排行榜返回 **Soul Ring Season Board**：当前真实计分公式、冠军、下一位追赶目标、Top N、X / Weibo 文案、GitHub Discussion / PR Comment 文案，以及 `arena` / `duel` / `quest` / `campaign` 命令。对应 CLI：`cyberhuatuo season --framework <framework> --top-n <N>`。

### 🔮 `soul_ring_sect_card` — 生成魂环宗门战队卡

当用户问“创建宗门”“生成战队卡”“把几个人组成魂师小队”“做一个团队招募贴”时调用。工具会基于列出的 GitHub 成员当前真实药方数生成宗门战力、领衔成员、成员快照、招募文案、GitHub Discussion / PR Comment 文案，以及每个成员的 `challenge` / `quest` / `campaign` 命令。对应 CLI：`cyberhuatuo sect <sect_name> <members...> --framework <framework>`。

### 🔮 `soul_ring_sect_recruitment_scroll` — 生成魂环宗门招募令

当用户问“邀请某人加入宗门”“生成入宗招募令”“做一个宗门拉新帖”“让这个战队招一个新人”时调用。工具会基于当前真实成员药方数生成 **Soul Ring Sect Recruitment Scroll**：当前宗门战力、候选人真实快照或显式开放招募占位符、入宗试炼、加入命令、X / Weibo 文案和 GitHub Discussion / PR Comment 文案。对应 CLI：`cyberhuatuo sect-recruit <sect_name> <members...> --invitee <github_username> --framework <framework>`。

### 🔮 `soul_ring_sect_quest_board` — 生成魂环宗门任务板

当用户问“宗门今天做什么”“给宗门分配任务”“让战队一起追环”“宗门招募之后怎么行动”时调用。工具会基于列出的 GitHub 成员当前真实药方数生成宗门战力、真实目标仓库、当前优先拉起成员、每个成员的 `challenge` / `quest` / `upload` / `campaign` 命令，以及可复制的宗门行动贴。对应 CLI：`cyberhuatuo sect-quest <sect_name> <members...> --framework <framework>`。

### 🔮 `soul_ring_sect_hall` — 生成魂环宗门堂口

当用户问“参考斗罗大陆宗门体系”“生成宗门职位”“创建学院 / 家族 / 宗派结构”“谁是外门、内门、核心、长老”时调用。工具会基于列出的 GitHub 成员当前真实药方数生成 Outer Disciple、Inner Disciple、Core Disciple、Hall Deacon、Sect Elder 身份、下一晋升差距、宗门招募文案、GitHub Discussion / PR Comment 文案，以及每个成员的 `challenge` / `quest` / `campaign` 命令。对应 CLI：`cyberhuatuo sect-hall <sect_name> <members...> --framework <framework>`。

### 🔮 `soul_ring_sect_duel_card` — 生成魂环宗门对决卡

当用户问“挑战另一个宗门”“生成宗门对决”“两个战队比一下”“做一个宗门战帖”时调用。工具会基于双方列出的 GitHub 成员当前真实药方数生成两边宗门战力、当前领先方、成员快照、X / Weibo 文案、GitHub Discussion / PR Comment 文案，以及双方 `sect` / `sect-quest` / 成员 `challenge` / `quest` / `campaign` 命令。对应 CLI：`cyberhuatuo sect-duel <challenger_sect> <rival_sect> --challenger-members <members...> --rival-members <members...> --framework <framework>`。

### 🔮 `soul_ring_sect_arena_snapshot` — 生成魂环宗门擂台榜

当用户问“宗门排行榜”“多宗门擂台”“几个战队排个榜”“生成宗门晒榜贴”时调用。工具会基于每个宗门列出的 GitHub 成员当前真实药方数生成多宗门公开排名、冠军宗门、下一追赶目标、成员快照、X / Weibo 文案、GitHub Discussion / PR Comment 文案，以及 `sect` / `sect-quest` / `sect-duel` / 成员 `challenge` / `quest` / `campaign` 命令。对应 CLI：`cyberhuatuo sect-arena --sect <sect_name> <members...> --sect <sect_name> <members...> --framework <framework>`。

### 📋 `my_share_card` — 生成魂环挑战分享卡

生成可复制的修为档案卡片。卡片现在包含 **魂环挑战** 传播文案：当前魂环、`下一环` 目标、仓库链接、当前 Git tag candidate install、PyPI 刷新后的标准安装命令和 `uvx --from cyberhuatuo cyberhuatuo-mcp`，方便智能体直接把贡献结果整理成社交平台帖子，同时避免把冷用户带到过期 PyPI 版本。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `github_username` | string | ✅ | GitHub 用户名 |



## 资源 (Resources)

| URI | 描述 |
|-----|------|
| `cyberhuatuo://knowledge-base/stats` | 知识库统计（病例数、框架分布） |
| `cyberhuatuo://knowledge-base/schema` | 病例 JSON Schema |

---

## 提示词模板 (Prompts)

| 名称 | 描述 | 参数 |
|------|------|------|
| `diagnose-error` | 望闻问切诊断模式 | `error_message` |
| `security-audit` | Agent 安全体检模式 | `code` |
| `contribute-case` | 贡献药方模式 | `problem`, `solution`, `framework?` |

---

## 环境配置

MCP Server 会自动读取项目根目录的 `.env` 文件配置。最小配置只需：

```bash
# .env  — 最小配置（纯搜索模式，无需 API Key）
CONTEXT7_ENABLED=true
```

如需使用 `diagnose` 和 `security_checkup` 等 LLM 功能，需配置至少一个 LLM API Key：

```bash
# 选一个即可
OPENAI_API_KEY=sk-your-key
# 或
DEEPSEEK_API_KEY=sk-your-key
# 或
GEMINI_API_KEY=AIzaSy-your-key
```

完整配置选项请参考 [`.env.example`](.env.example)。

---

## 协议

Apache-2.0 License
