# Repository Guardrails

This repository is the public Codex Plugin, MCP, and skills distribution for CyberHuaTuo.

- Keep this repository focused on the Codex plugin manifest, MCP tools, CLI entry points, the public cases knowledge base, schemas, and Codex skills.
- Do not add research-only experiment data, paper drafts, benchmark ledgers, raw model outputs, or generated paper reports.
- Forbidden paths include `data/`, `paper/`, `paper_usenix/`, `reports/`, and `cyberhuatuo/sandbox/`.
- Before release, run `python scripts/check_release_boundary.py`.
- If code changes affect packaging, run `python -m build` and inspect both wheel and sdist with the release boundary script.
