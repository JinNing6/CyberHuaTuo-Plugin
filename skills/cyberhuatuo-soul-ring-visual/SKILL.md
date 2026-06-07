---
name: cyberhuatuo-soul-ring-visual
description: Use when a user asks about CyberHuaTuo level, rank, badge, card, soul ring, cultivation status, breakthrough progress, visual display, animation, 等级, 魂环, 排名, 徽章, 卡片, 展示, or 动图 in Codex, Claude, or another agent chat.
---

# CyberHuaTuo Soul Ring Visual

## Core Rule

Show the user's current real CyberHuaTuo contribution state as a chat-visible Soul Ring artifact whenever the request includes level, rank, badge, card, soul ring, cultivation status, breakthrough progress, visual display, animation, 等级, 魂环, 排名, 徽章, 卡片, 展示, or 动图.

## Routing

1. Require a real GitHub username. If the username is missing or ambiguous, ask for it before generating anything.
2. Use the requested framework when the user names one. Otherwise use the user's known dominant framework only if available from current context; if not, use `langchain` as the public first-ring onramp and say so.
3. Prefer the MCP tool `soul_ring_visual_artifact` when available.
4. If MCP is unavailable, run the CLI:

```bash
cyberhuatuo visual <github_username> --framework <framework> --output-dir tmp/soul-ring-visuals
```

5. Return the generated Markdown GIF first and the PNG fallback second. In Codex App, local media paths must be absolute paths so the animation can render directly in the conversation.

## Output Contract

Include:

- Markdown GIF preview from the artifact.
- PNG fallback from the artifact.
- Current real CyberHuaTuo contribution data shown by the artifact.
- The install/MCP commands returned by the artifact when relevant.
- The `record-share` command when the user is preparing a public post.

## Non-Fabrication

Use only current real CyberHuaTuo contribution data. If the user has zero prescriptions, show zero. The visual does not invent ranks, downloads, retention, referrals, rewards, or fake contributors.

## Common Mistakes

- Do not rely on MCP `ui://` widgets for the primary visual path; Markdown GIF plus PNG fallback is the portable route.
- Do not answer a visual request with only text when `soul_ring_visual_artifact` or `cyberhuatuo visual` is available.
- Do not call leaderboard or ranking tools alone when the user asks to show or animate a level state; generate the visual artifact too.
- Do not fabricate a username, contribution count, rank, or promotion gate.
