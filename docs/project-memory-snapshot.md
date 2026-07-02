# Project Memory Snapshot

Updated: 2026-07-02

## Current Decision

CyberHuaTuo should use a dual-entry positioning strategy:

1. Engineering conversion entry: prioritize a narrow first-touch promise before broader worldbuilding.
2. China launch narrative entry: use the HuaTuo / cyber clinic / soul-ring mythology as the emotional spread hook, then route every interested user into the emergency diagnosis demo.

> AI Agent Error Doctor: paste any MCP / LangChain / CrewAI / OpenAI SDK traceback, get root cause and exact fix in seconds.

The public README, package copy, marketplace copy, and first demo flow should lead with the emergency diagnosis workflow. HuaTuo worldbuilding, soul rings, leaderboards, pharmacy, and growth loops remain part of the product, but they should appear after a user understands the immediate debugging value.

Domestic China promotion should not discard the grand narrative. The strategic hypothesis from the maintainer is that Chinese AI-community emotion plus the HuaTuo IP can provide a strong launch spark once publicly promoted. Treat that as a campaign-layer hypothesis to test through staged public promotion, not as a reason to make the GitHub first screen diffuse.

## Runtime / Deployment State

- This repository is the public Codex Plugin, MCP, CLI, skills, schemas, and public cases distribution for CyberHuaTuo.
- Package name is `cyberhuatuo`; console scripts are `cyberhuatuo` and `cyberhuatuo-mcp`.
- Current version in `pyproject.toml` is `0.2.1`.
- Marketplace release direction is documented in `docs/MARKETPLACE_RELEASE.md`: PyPI first, Claude second, Codex third.
- The maintainer is considering Google Play as an additional public entry surface by first creating a draft Android app listing. No Android, Flutter, Gradle, or mobile app project exists in this repository as of the 2026-07-02 scan.
- Google Play draft package/application ID decision: use `com.cyberhuatuo` for the flagship Android entry if Play Console accepts it. The `cyberhuatuo.com` domain is a brand-control target, not yet recorded here as owned.

## Verified Facts

- `README.md` currently places the CyberHuaTuo clinic/worldbuilding visuals and soul-ring narrative before the concrete emergency diagnosis flow.
- The strongest existing user-facing promise appears later in the README: paste an error and get a cure in seconds.
- `.agents/skills/cyberhuatuo-rescue/SKILL.md` defines the core practical use case as self-rescue and diagnosis for AI systems, Agent frameworks, and coding-project failures.
- `.agents/skills/cyberhuatuo-soul-ring-visual/SKILL.md` defines the soul-ring visual loop as contribution/rank display, not the primary debugging entrypoint.
- Public GitHub API check on 2026-07-02 showed:
  - `Unclecheng-li/VulnClaw`: 1638 stars / 224 forks.
  - `JinNing6/CyberHuaTuo`: 9 stars / 0 forks.
  - `JinNing6/CyberHuaTuo-Plugin`: 1 star / 0 forks.
  - `JinNing6/Noosphere`: 15 stars / 1 fork.
- Public README comparison showed VulnClaw leads with a direct natural-language-to-result workflow for penetration testing, while CyberHuaTuo leads with a richer but more diffuse clinic/worldbuilding narrative.
- Public web search on 2026-07-02 showed VulnClaw appearing on GitHub Trending with a direct AI penetration-testing workflow and 132 stars today in the search result snippet.
- The maintainer stated on 2026-07-02 that CyberHuaTuo has not yet been publicly promoted in China and that the original macro-narrative strategy was designed for domestic AI-community emotional resonance around HuaTuo and Chinese IP.
- On 2026-07-02, the README first screen was updated without deleting existing worldbuilding: `README.md` now adds "Emergency Room: Paste The Traceback First" and `README_CN.md` now adds "急诊入口：先粘贴报错" before the visual/worldbuilding sections.
- On 2026-07-02, a real CLI demo was recorded from this repository using the LangChain `ChatOpenAI` import traceback. Assets: `assets/cli_emergency_diagnosis_demo.cast` and `assets/cli_emergency_diagnosis_demo.gif`.
- On 2026-07-02, `cyberhuatuo/report.py` was updated so `diagnose` still shows a knowledge-base prescription when no LLM API key is configured but a matching case exists.
- On 2026-07-02, unreadable old local release artifacts under `dist/` were moved to ignored backup directory `tmp/dist-permission-backup-20260702151002`, then `python -m build --sdist --wheel` regenerated a clean default `dist/`.
- On 2026-07-02, repository search found no existing Android application module, Flutter project, Gradle build, `AndroidManifest.xml`, or mobile store configuration in this repository.
- On 2026-07-02, the maintainer stated that the Google Play package name `com.cyberhuatuo` is available in Play Console and approved using it before buying the matching domain.
- On 2026-07-02, package and plugin marketplace copy was realigned around the first-touch promise: paste an AI-agent traceback, get root cause, exact fix, and verification steps. The First Soul Ring loop remains present as the post-cure contribution path.

## Open Blockers

- Any concrete speed claim such as "30 seconds" should be backed by repeatable local measurements before becoming public copy.
- A broad domestic launch before the conversion surface is ready could spend the strongest narrative moment while leaking attention at the install/demo step.
- The local positioning fixes must be committed and pushed before public GitHub visitors can see them.

## Next Actions

1. Commit and push the README, CLI report fallback, demo asset, and marketplace-copy positioning fixes to `origin/main`.
2. Prepare a domestic China seed-launch pack that leads with the HuaTuo narrative but immediately shows one real rescued traceback, one command, and one GitHub star/contribution call to action.
3. Run a staged domestic launch: first 20-50 technical seed users or communities, then one public article/thread/video after the demo surface converts, then broader reposting.
4. Create the Google Play draft with package/application ID `com.cyberhuatuo`, then buy/control the matching `cyberhuatuo.com` domain before broad public promotion to reduce brand-squatting risk.
5. If creating a Google Play draft entry, use it as a real mobile utility doorway rather than a non-functional placeholder.
6. Keep the README emergency-entry and marketplace first-touch regression tests in `tests/test_diagnosis_report.py` whenever public positioning changes.

## Verification Results

- `python -m cyberhuatuo diagnose "Traceback ... from langchain import ChatOpenAI ..." --framework langchain --top-k 3` returned a knowledge-base cure including `pip install langchain-openai` and `from langchain_openai import ChatOpenAI`.
- `python -m pytest tests/test_diagnosis_report.py -q`: 2 passed.
- `python -m ruff check .`: passed.
- `python -m pytest -q`: 214 passed.
- `python -m build --sdist --wheel --outdir tmp/release-check-dist-20260702142744`: passed.
- Fresh artifacts in `tmp/release-check-dist-20260702142744` passed `_find_forbidden` and marketplace release contract checks from `scripts/check_release_boundary.py`.
- `python -m build --sdist --wheel`: passed after replacing the unreadable local `dist/` directory.
- `python scripts/check_release_boundary.py`: passed against the regenerated default `dist/cyberhuatuo-0.2.1-py3-none-any.whl` and `dist/cyberhuatuo-0.2.1.tar.gz`.
- `python -m pytest tests/test_diagnosis_report.py -q`: 3 passed after adding marketplace-copy first-touch regression coverage.
- `python -m ruff check cyberhuatuo/marketplace.py tests/test_diagnosis_report.py`: passed.
- `python -m ruff check .`: passed after the README, plugin manifest, marketplace copy, and package metadata alignment.
- `python -m pytest -q`: 215 passed after the README, plugin manifest, marketplace copy, and package metadata alignment.
- `python -m build --sdist --wheel`: passed after the package metadata alignment.
- `python scripts/check_release_boundary.py`: passed after the regenerated wheel and sdist were rebuilt with the aligned metadata.

## Guardrails

- Do not delete completed CyberHuaTuo features to simplify positioning. Reorder the story first; remove only with explicit maintainer instruction.
- Do not claim adoption, downloads, retention, reposts, rewards, or fake contributors without verified public evidence.
- Do not present stars or forks as proof of product quality; use them only as public attention signals.
- Keep public copy concrete: input, supported frameworks, diagnosis output, exact fix, verification command.
- Keep the worldbuilding as a retention and contribution layer after the user sees the emergency debugging result.
- In China-facing campaign copy, the macro HuaTuo narrative may lead the post, but every post must reach the concrete emergency diagnosis demo within the first screen.
