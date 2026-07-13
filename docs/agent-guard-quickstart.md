# Agent 行医护栏：60 秒快速上手

适用版本：CyberHuaTuo `0.2.2+`，Python `3.10+`。

## 1. 安装并做零风险自检

```bash
python -m pip install --upgrade "cyberhuatuo>=0.2.2"
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

如果 `0.2.2` 尚未发布到 PyPI，可在当前源码目录验证发布候选：

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

## 5. 三个常见问题

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

1. 本地自检显示 `SELF-TEST PASSED`。
2. 插件在 `/plugins` 中启用。
3. Hook 在 `/hooks` 中已检查并信任。
4. `agent_action_guard` 对示例命令返回预期 `ASK`，且没有执行该命令。

官方宿主说明：[Codex Plugins](https://developers.openai.com/codex/plugins)、[Codex Hooks](https://developers.openai.com/codex/hooks)、[Claude Code Hooks](https://docs.anthropic.com/en/docs/claude-code/hooks)。
