# Agent 行医护栏：60 秒快速上手

适用版本：CyberHuaTuo `0.2.3+`，Python `3.10+`。

## 1. 安装并做零风险自检

```bash
python -m pip install --upgrade "cyberhuatuo>=0.2.3"
cyberhuatuo guard --self-test --workspace-root .
```

正确结果必须包含：

```text
ALLOW  git status --short
ASK    rm -rf ./build
BLOCK  rm -rf /
No command was executed.
SELF-TEST PASSED
```

自检只把三条字符串送进规则引擎，不会执行、改写或批准其中任何命令。

在源码仓库中开发或验证候选版本时，使用仓库虚拟环境：

```powershell
.\.venv\Scripts\python.exe -m cyberhuatuo guard --self-test --workspace-root .
```

## 2. 接入 Codex

```bash
codex plugin marketplace add JinNing6/CyberHuaTuo-Plugin
```

1. 在 Codex 输入 `/plugins`，安装并启用 `cyberhuatuo-plugin`。
2. 新建一个会话，让插件技能、MCP 和 Hook 重新加载。
3. 输入 `/hooks`，检查来源和命令后信任 CyberHuaTuo Hook。

用下面的提示验证 MCP 审查入口，不要要求 Agent 执行命令：

```text
Call agent_action_guard to review `rm -rf ./build` for this workspace. Do not execute it.
```

预期是 `ASK`；Codex 的 `PreToolUse` 暂不支持交互式 `ask`，真实 Hook 会将其转为 `deny`。

## 3. 接入 Claude Code

```bash
claude plugin marketplace add JinNing6/CyberHuaTuo-Plugin
claude plugin install cyberhuatuo-plugin@cyberhuatuo
```

新建会话，打开 `/hooks` 检查并信任 Hook。使用同一条只审查、不执行的提示验证 `agent_action_guard`；Claude Code 可保留 `ASK` 供用户确认。

## 4. 手动审查任意命令

```bash
cyberhuatuo guard "<Agent 提议的精确命令>" --cwd . --workspace-root .
```

- `ALLOW` 返回码为 `0`。
- `ASK` 返回码为 `2`，必须停止并让用户确认精确目标。
- `BLOCK` 返回码为 `3`，不得换一种语法绕过同一危险效果。
- 自动化系统只想读取报告时，可加 `--json --exit-zero`。

## 5. 把真实判定变成脱敏病例

`self-test` 只证明规则引擎 Ready。至少审查一条真实、未执行的命令，才算 Manual activation：

```bash
cyberhuatuo guard "<Agent 提议的精确命令>" --cwd . --workspace-root . --expected BLOCK --report reports/guard-report.md
```

报告流程固定为：

1. 只在内存中判定原始命令，不执行命令。
2. 脱敏 token、URL authority、主机/用户身份、工作区/主目录与绝对路径。
3. 在终端展示完整脱敏预览。
4. 用户确认后才写入；默认不覆盖已有文件，不联网、不上传。
5. 私有项目名或业务词使用可重复的 `--redact <literal>` 补充处理。

非交互环境必须在人工检查预览后显式增加 `--confirm-report`。如果报告含疑似私钥或已知 token 仍无法安全处理，CLI 会拒绝生成；操作失败返回 `4`，即使使用 `--exit-zero` 也不会伪装成功。

普通误报、普通漏报和集成缺口分别使用：

- [Guard False Positive](https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/new?template=guard-false-positive.yml)
- [Guard False Negative](https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/new?template=guard-false-negative.yml)
- [Guard Integration Gap](https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/new?template=guard-integration-gap.yml)

能稳定绕过 Hook、解析器、包装器、协议或执行控制的安全问题使用[私密漏洞报告](https://github.com/JinNing6/CyberHuaTuo-Plugin/security/advisories/new)，不要先公开复现细节。

## 6. 三个常见问题

**找不到 `cyberhuatuo`**

```bash
python -m cyberhuatuo guard --self-test --workspace-root .
```

如果模块也不存在，确认安装命令使用的 Python 与当前终端是同一个环境。

**插件已安装但 Hook 没运行**

重新开始会话并打开 `/hooks`。未审查或 Hook 文件发生变化后，Codex 会跳过该 Hook，直到用户再次信任当前定义。

**已经通过自检，是否等于所有命令都受保护**

不是。自检证明当前规则引擎可用；Hook 只能拦截宿主实际发出的 `PreToolUse` 路径。它不是操作系统 sandbox，也不能为永久删除制造后悔药。

## 完成标准

用户完成上手的最低证据是：

1. **Ready**：本地自检显示 `SELF-TEST PASSED`。
2. **Manual activation**：CLI 或 MCP 审查一条真实、未执行的命令，并确认预期/实际判定。
3. **Enforced activation**：插件在 `/plugins` 中启用，Hook 在 `/hooks` 中已检查并信任，宿主真实发出并执行 `PreToolUse` 决策。
4. **Contribution**：脱敏病例经维护者复现并进入回归测试；只有此时才计入 WEC、署名、药方和魂环。

官方宿主说明：[Codex Plugins](https://developers.openai.com/codex/plugins)、[Codex Hooks](https://developers.openai.com/codex/hooks)、[Claude Code Hooks](https://docs.anthropic.com/en/docs/claude-code/hooks)。
