# CyberHuaTuo Claude Desktop Extension

This folder builds the Claude Desktop `.mcpb` package for CyberHuaTuo.

## Install And Test

```bash
npm install -g @anthropic-ai/mcpb
mcpb validate claude-desktop
mcpb pack claude-desktop dist/cyberhuatuo-claude-desktop.mcpb
```

Install the generated `.mcpb` in Claude Desktop by double-clicking it, dragging it into Claude Desktop, or using Settings > Extensions > Advanced settings > Install Extension.

## Runtime

The extension uses MCPB `server.type = "uv"` and depends on the published `cyberhuatuo` PyPI package. Keep `pyproject.toml`, `manifest.json`, `.codex-plugin/plugin.json`, and `.claude-plugin/plugin.json` versions aligned for each release.

## Privacy Policy

CyberHuaTuo's privacy policy is maintained at `docs/PRIVACY.md` and linked from `manifest.json`.
