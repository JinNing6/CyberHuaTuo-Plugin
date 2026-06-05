# Marketplace Release Plan

Last verified against official docs: 2026-06-04.

CyberHuaTuo should ship through three channels in this order: PyPI first, Claude second, Codex third. PyPI gives every agent a stable `uvx` install target. Claude and Codex then reuse the same MCP entrypoint and the same soul ring contribution loop.

## Current Channel Truth

- PyPI project already exists: `https://pypi.org/project/cyberhuatuo/`.
- `0.1.0 was uploaded on 2026-03-12` from the older `JinNing6/CyberHuaTuo` release pipeline.
- Do not try to re-upload `0.1.0`. PyPI files are immutable by version; the plugin repository release train starts at `0.2.0`.
- The current repository is `JinNing6/CyberHuaTuo-Plugin`. To publish this repository to the existing PyPI project, add it as an additional Trusted Publisher on PyPI.
- The Claude path splits into two surfaces:
  - Claude Code plugin marketplace: `.claude-plugin/marketplace.json` plus `.claude-plugin/plugin.json`, then submit to `claude-community` if public review is desired.
  - Claude Desktop / Claude Connectors Directory: `claude-desktop/manifest.json` packaged as `.mcpb`, plus privacy policy, tool annotations, and reviewer-ready examples.
- The Codex path is a plugin marketplace/catalog path: `.agents/plugins/marketplace.json` points to the plugin root, and `.codex-plugin/plugin.json` points to `./skills/` plus `./.mcp.json`.
- No public channel claim is considered launched until the install command has been tested from a clean environment and the result is recorded back into the activation ledger.

## Marketplace Readiness Gate

Before any public push, run the local release gate:

```bash
cyberhuatuo install-command --username <maintainer-github> --framework langchain --release-tag v0.2.0 --target-contributors 3
cyberhuatuo market-ready --no-remote
cyberhuatuo launch-assets --username <maintainer-github> --framework langchain --release-tag v0.2.0 --target-contributors 3
cyberhuatuo proof-pack --username <maintainer-github> --framework langchain --release-tag v0.2.0 --target-contributors 3
python -m cyberhuatuo candidate-install-smoke --username <maintainer-github> --framework langchain --release-tag v0.2.0 --target-contributors 3
cyberhuatuo first-invite --username <maintainer-github> --invitee <external-contributor-github> --framework langchain --release-tag v0.2.0 --target-contributors 3 --source-url <created Growth Issue URL>
python scripts/check_marketplace_release.py --no-remote
```

The first command prints a **CyberHuaTuo Install Command**. It fetches real **PyPI JSON API** latest-version proof and recommends `python -m pip install --upgrade cyberhuatuo` only when the registry is current. If PyPI is stale or cannot be verified, it prints the bounded **Git Tag Candidate Install Bridge**, states that the bridge does not close the PyPI install loop, and routes straight to `challenge`, `proof-pack`, `market-copy`, and `traction-proof`. The Git tag bridge must pass the **Candidate Install Smoke Gate** before it is sent to outside contributors. That gate creates a disposable virtual environment, installs the exact public tag with pip Direct URL syntax, verifies the installed version, console command, Install Decision Surface, and proof/invite route, cleans up on success, and retains the temp directory on failure. It is not run automatically inside lightweight CI because it intentionally uses the public network. The same install decision surface is available to Claude/Codex through MCP tool `current_install_command`.

This checks the PyPI Trusted Publishing workflow, Claude Code plugin catalog, Claude Desktop MCPB assets, Codex plugin catalog, shared MCP entrypoint, version sync, and local full public acquisition IssueOps files: First Soul Ring, Growth Flywheel, Bounty Board, Share Proof, Launch Campaign, Tournament, Mentor Pact, Sect Recruitment, and Season Board.

After the default branch and PyPI release are public, run the strict remote gate:

```bash
cyberhuatuo market-ready --remote --strict-remote --username <maintainer-github> --framework langchain --release-tag v0.2.0 --target-contributors 3
python scripts/check_marketplace_release.py --remote --strict-remote --username <maintainer-github> --framework langchain --release-tag v0.2.0 --target-contributors 3
```

Strict remote mode fails if GitHub Contents API cannot see the default-branch IssueOps files or if PyPI still serves an older version than the local growth tools. GitHub Release proof is the preferred public provenance for the `release.published` path; if PyPI latest-version proof is already current, a missing Release becomes a provenance warning because the protected manual `workflow_dispatch` `release_tag` fallback can close the registry path without `PYPI_TOKEN`. This keeps PyPI, Claude, and Codex launch claims tied to real install and acquisition-loop evidence instead of marketplace copy.

When GitHub public API rate limits block remote verification, set `GITHUB_TOKEN` or `GH_TOKEN` to a token with read access and re-run the strict gate. The token is used only as an Authorization header for GitHub REST API reads and is not printed.

The same preflight is exposed to Claude/Codex as the MCP tool `marketplace_readiness_gate`. Every run must first include a **Flywheel Closure Verdict**: exactly `closed`, `not closed`, or `unverified`, with **Ready gates** / total gate counts, real evidence basis, blocking gates, and the non-fabrication rule. Every run must also include a **Launch Closure Checklist** in this order: remote acquisition routes, PyPI Trusted Publisher, GitHub `release.published` trigger or protected fallback readiness, registry latest-version proof, first public proof, and recheck commands. Do not claim the market push is complete until the verdict is `closed` and every row is verified from real public state or explicitly closed by the protected PyPI fallback.

Every preflight must also print a **First Public Proof Kit**. It includes the Prefilled Growth Flywheel Issue, Prefilled Share Proof Issue, and Prefilled Bounty Board Issue form URLs, but those `issues/new?...` URLs are entrypoints only. After submission, copy the created public URL into `Created Growth Issue URL`, `Created Share Proof Issue URL`, or `Created Bounty Board Issue URL`, then run the kit's Growth and Bounty `cyberhuatuo record-return` ledger commands plus the Share `cyberhuatuo record-share` attribution command. The kit also includes a **Community Challenge Pack** with Prefilled Tournament Cup Issue, Prefilled Mentor Pact Issue, Prefilled Sect Recruitment Issue, Prefilled Season Board Issue, created-Issue placeholders, and public `tournament`, `mentor`, `sect-recruit`, and `season` commands so first proof can become a public event loop. It also includes a **Protected Publish Fallback** command (`gh workflow run publish-pypi.yml -f release_tag=v0.2.0`) plus **GitHub Web Release**, **GitHub Actions workflow page**, PyPI Trusted Publisher settings links, and a **Git Tag Candidate Install Bridge** for stale PyPI recovery after the public `v*` tag exists. The bridge keeps `python -m pip install --upgrade cyberhuatuo` visible, may print `python -m pip install --upgrade "cyberhuatuo @ git+https://github.com/JinNing6/CyberHuaTuo-Plugin.git@v0.2.0"`, must be verified with `python -m cyberhuatuo candidate-install-smoke`, does not close the PyPI install loop, and requires rechecking PyPI latest-version proof before claiming public install readiness. The kit also includes an **Install Decision Surface** using `cyberhuatuo install-command` / MCP `current_install_command` before any PyPI, Claude, Codex, or MCP marketplace invite, plus an **External Contributor Path** with pasted Recommended Install, first-session command, first contribution command, First Soul Ring Prescription Issue, Share Proof Issue URL, created-Issue proof rule, contributor-counting rule, `cyberhuatuo market-copy` submission copy routing, recheck commands, and a **Copy-ready public proof post** that explicitly avoids downloads, retention, repost counts, referrals, rewards, and fake contributors.

When GitHub/PyPI public APIs are rate-limited or marketplace review is still pending, run `cyberhuatuo proof-pack` or the MCP tool `first_public_proof_pack` to generate the **No-Network First Public Proof Pack**. It prints the same Growth/Share/Bounty issue-form entrypoints, Created Growth Issue URL, Created Share Proof Issue URL, and Created Bounty Board Issue URL placeholders, a **Community Challenge Pack** with Tournament/Mentor/Sect/Season issue-form entrypoints and copy-ready public event commands, a Protected Publish Fallback block with `gh workflow run publish-pypi.yml -f release_tag=<tag>`, `gh run list --workflow publish-pypi.yml --limit 5`, **GitHub Web Release**, **GitHub Actions workflow page**, PyPI Trusted Publisher settings links, a Git Tag Candidate Install Bridge, Candidate Install Smoke Gate, Install Decision Surface, terminal Growth and Bounty `record-return` CLI ledger commands, Share `record-share` attribution, External Contributor Path with pasted Recommended Install, recheck commands, and copy-ready proof text without fetching public metrics, writing ledger events, creating issues, publishing releases, uploading to PyPI by itself, closing the PyPI install loop, or inventing traction. The fallback still requires the PyPI Trusted Publisher to match this repository, workflow file, and `pypi` environment; no `PYPI_TOKEN` fallback is allowed.

When a market pulse needs to target one real external developer, run `cyberhuatuo first-invite --username <maintainer> --invitee <github> --framework <framework> --release-tag <tag> --target-contributors <N> --source-url <created Growth Issue URL>` or the MCP tool `first_contributor_invite`. It generates the **First Contributor Invite Pack** with a local Candidate Snapshot, First Soul Ring Prescription Issue URL, Share Proof Issue URL, `record-session` command, `challenge` command, proof-pack / market-copy / traction-proof recheck commands, contributor-counting rule, and copy-ready direct invite. This path is for first external contributor recruitment; it does not fetch public metrics, write ledger events, create issues, publish releases, upload to PyPI, submit marketplace forms, and does not invent downloads, retention, repost counts, referrals, rewards, reviews, or fake contributors.

When the release artifacts are ready but the PyPI / Claude / Codex forms need final text, run `cyberhuatuo market-copy` or the MCP tool `marketplace_submission_copy` to generate the **Marketplace Submission Copy Pack**. It returns **PyPI listing copy**, **Claude MCPB listing copy**, **Codex plugin listing copy**, a GitHub Release post with **GitHub Web Release** and **GitHub Actions workflow page** links, project URLs, install and validation commands, a **Submission Portals And Evidence URLs** section with PyPI Trusted Publisher settings, Claude Code plugin submit, Claude Connectors Directory submission guide, and Codex plugin evidence, public proof CTA commands with Created Bounty Board Issue URL and Bounty `record-return`, the **Community Challenge Pack** for Tournament, Mentor Pact, Sect Recruitment, and Season Board routes, a Git Tag Candidate Install Bridge plus Candidate Install Smoke Gate for stale PyPI recovery, a **Marketplace Submission Ledger** block with `cyberhuatuo record-market` / `cyberhuatuo market-status`, and a copy-ready maintainer announcement. Submission portal anchors: PyPI Trusted Publisher settings: https://pypi.org/manage/project/cyberhuatuo/settings/publishing/; Claude Code plugin submit: https://claude.ai/settings/plugins/submit; Claude Connectors Directory submission guide: https://claude.com/docs/connectors/building/submission; Codex plugin evidence: `codex plugin marketplace add JinNing6/CyberHuaTuo-Plugin`. This is submission copy, not traction evidence: it does not fetch public metrics, write ledger events, publish releases, upload to PyPI, submit marketplace forms, invent downloads, retention, repost counts, referrals, rewards, reviews, fake contributors, or close the PyPI install loop.

After each real PyPI, Claude Code, Claude Desktop MCPB, Codex, GitHub Release, or agent-marketplace submission exists, run `cyberhuatuo record-market --username <maintainer-github> --framework langchain --channel <channel> --status submitted --submission-url <reviewable public URL> --release-tag v0.2.0` or the MCP tool `record_marketplace_submission`. Then run `cyberhuatuo market-status --username <maintainer-github> --framework langchain --release-tag v0.2.0` or the MCP tool `marketplace_submission_status`. The **Marketplace Submission Ledger** records reviewable public URL evidence only; it does not invent downloads, retention, repost counts, referrals, rewards, reviews, approvals, or fake contributors.

Every preflight and `cyberhuatuo launch-assets` audit also prints a **Public Release Operator Runbook**. It is read-only and gives the exact non-mutating command checklist that release operators should review: local gates, full-bundle staging, `git push origin HEAD:main`, tag creation, **GitHub Web Release**, **GitHub Actions workflow page**, preferred `gh release create <tag> ... --verify-tag --notes-from-tag`, protected `gh workflow run publish-pypi.yml -f release_tag=<tag>` fallback, `cyberhuatuo market-copy`, PyPI/latest-version recheck, candidate install smoke, and traction proof recheck. `workflow_dispatch` requires `.github/workflows/publish-pypi.yml` to be present on the default branch, so the default-branch handoff remains a hard launch boundary before manual fallback can work.

Every preflight must also print a **Local Launch Asset Audit**. Run `cyberhuatuo launch-assets --username <maintainer-github> --framework langchain --release-tag v0.2.0 --target-contributors 3` directly when the remote default branch is missing IssueOps files or before opening a release PR, so the Public Release Operator Runbook keeps the same release/user/target context. The bare `cyberhuatuo launch-assets` command remains valid for source-default CI and local smoke checks. The audit validates local Issue Forms, comment-only workflows, package metadata, plugin manifests, Trusted Publishing workflow, Claude MCPB assets, and shared MCP entrypoints, then prints exact minimal `git add` commands plus a **Full Public Growth Release Bundle** for docs, package metadata, Issue Forms, workflows, public growth modules, scripts, and tests. Its **Dirty Worktree Release Coverage** uses read-only `git status --porcelain` to show which changed files are covered by the full release bundle and which need separate review. It is read-only and does not stage files, publish releases, upload to PyPI, mutate remotes, or claim traction.

CI and the PyPI Trusted Publishing workflow must run `python -m cyberhuatuo launch-assets` after lint/tests and before `python -m build --sdist --wheel`. The release boundary script then inspects the current version's wheel and sdist, not only the source tree: the wheel must contain the public growth modules, console-script entry points, PyPI metadata, and README-derived launch commands; the sdist must contain the IssueOps forms/workflows, plugin manifests, Claude Desktop MCPB metadata, privacy/release docs, and CI/publish workflow steps.

## Release Positioning

One sentence:

> CyberHuaTuo is an MCP and agent-skill clinic for AI-agent failures, with a public soul ring contribution system that turns real fixes into ranked, shareable prescriptions.

Public promise:

- Start with `cyberhuatuo install-command` or MCP `current_install_command`, then paste its Recommended Install; use `uvx --from cyberhuatuo cyberhuatuo-mcp` for MCP clients after registry proof is current.
- Use the MCP tools from Codex, Claude, Cursor, VS Code, Gemini CLI, and other MCP clients.
- Submit a real fix through the First Soul Ring issue route.
- Maintainers add `accepted-prescription`; `.github/workflows/soul-ring-promote.yml` promotes it into a case PR.
- The contributor gets a real soul ring ladder, badge, card, campaign copy, ranking, and next action.
- High-realm gates use `cyberhuatuo evidence` / `record_soul_ring_evidence` instead of internal field edits. The **Soul Ring Evidence Card** requires reviewable public evidence, writes an append-only local JSONL event, reports evidence-backed count, and keeps progress, ranks, rewards, downloads, and contributors not invented.
- Launch attention is converted into a target first-ring contributor campaign with `cyberhuatuo launch-campaign`, the Soul Ring Launch Campaign IssueOps form, the Growth Flywheel Issue, and the Share Proof Issue. Each launch campaign must produce a **Campaign Recap And Next Sprint** with observed real contributors, reached-vs-target, shortfall, the next-target rule, copy-ready recap text, the next `growth_campaign` command, and `traction-proof --record-snapshot` proof recording.
- Marketplace submissions are recorded with the **Marketplace Submission Ledger**: `cyberhuatuo record-market` requires a reviewable public URL for PyPI, Claude Code, Claude Desktop MCPB, Codex, GitHub Release, or agent-marketplace submission evidence, and `cyberhuatuo market-status` reports missing channels without inventing approvals or adoption metrics.
- Public breakout is checked with `cyberhuatuo traction-proof`, which reads GitHub REST API, GitHub Pull Requests API, GitHub Contents API, GitHub Releases API, PyPI JSON API, and the local activation/share ledger to calculate **Target contributor progress** from real contributor identities only.
- Public API fetch failures or rate limits must inline the **No-Network First Public Proof Pack** inside `cyberhuatuo traction-proof`, so launch operators can open proof Issues and record created URLs without a second command. The same proof path must print `cyberhuatuo market-copy` so marketplace submission copy stays tied to the verified release/proof loop.
- Every public first-touch comment workflow for First Soul Ring issues, Tournament, Mentor Pact, Sect Recruitment, Season Board, Share Proof, Launch Campaign, Bounty Board, Growth Flywheel, and ready pull requests must include the launch preflight/proof-pack route before the gameplay commands: `cyberhuatuo proof-pack`, `cyberhuatuo market-copy`, `cyberhuatuo market-ready --remote --strict-remote`, and a reviewable `cyberhuatuo record-return` or `record-share` command bound to the created Issue/PR URL where applicable. Comment-only IssueOps workflows must not checkout code or run repository scripts.
- When target progress is below the campaign goal, operators should use `cyberhuatuo first-invite` / `first_contributor_invite` to turn one market exposure or Growth Issue into a direct first external contributor invite instead of relying only on broad announcements.
- Traction proof must also verify **PyPI package readiness**, **Release Trigger / Protected Fallback Readiness**, and **Remote IssueOps Readiness**: PyPI latest version must not lag the local growth-tool version; the requested GitHub Release should be non-draft/non-prerelease and visible through GitHub Releases API for public provenance, but a current PyPI version can prove the protected manual `workflow_dispatch` `release_tag` fallback closed the registry path; default-branch Growth Flywheel / Share Proof / Launch Campaign issue forms plus comment-only workflows must exist before `issues/new?...` links are treated as live acquisition loops.
- Public traction velocity is recorded only with explicit `cyberhuatuo traction-proof --record-snapshot`, which appends an append-only real JSONL snapshot and compares deltas with the previous real snapshot.
- External launch attention is recorded with `cyberhuatuo record-return`, whose success card now prints **Next External Contributor Invite** with terminal `cyberhuatuo first-invite` / `cyberhuatuo proof-pack` and MCP `first_contributor_invite(...)` / `first_public_proof_pack(...)` equivalents before the activation and flywheel rechecks.
- Public launch shares are recorded with `cyberhuatuo record-share`; its success card uses the recorded share URL as proof for the same next external-contributor invite path, then `cyberhuatuo share-report` plus `cyberhuatuo share-leaderboard` inspect attribution before any claim is made.

Do not claim adoption numbers, historical seasons, fake champions, fake users, or fake prescription counts.

## PyPI

Goal: make `cyberhuatuo` the stable public installation target for every MCP host.

Status in this repository:

- Package name: `cyberhuatuo`
- Console scripts: `cyberhuatuo` and `cyberhuatuo-mcp`
- MCP install command: `uvx --from cyberhuatuo cyberhuatuo-mcp`
- Release workflow: `.github/workflows/publish-pypi.yml`
- Publishing mode: PyPI Trusted Publishing through `pypa/gh-action-pypi-publish@release/v1`
- Protected fallback: `workflow_dispatch` with required `release_tag`; it checks out the existing `v*` tag, fetches `origin/main`, verifies the tag commit is reachable from `origin/main`, verifies `pyproject.toml` version equals the tag, reruns all gates, and still publishes through OIDC without `PYPI_TOKEN`.
- Current blocker: the existing PyPI project trusts the older `JinNing6/CyberHuaTuo` workflow, so `JinNing6/CyberHuaTuo-Plugin` must be added as an additional Trusted Publisher before this workflow can publish.

One-time PyPI setup:

1. Log in as a maintainer of the existing PyPI project `cyberhuatuo`.
2. Add an additional Trusted Publisher for:
   - owner/repository: `JinNing6/CyberHuaTuo-Plugin`
   - workflow: `.github/workflows/publish-pypi.yml`
   - environment: `pypi`
   - package: `cyberhuatuo`
3. Keep the older `JinNing6/CyberHuaTuo` publisher only if it still needs to release the legacy application. Otherwise, remove or freeze it to avoid split-brain package ownership.
4. Protect the GitHub `pypi` environment with maintainer approval.
5. Confirm the next release version is greater than the existing PyPI release. For this repository, do not publish `0.1.0` again.

Release process:

1. Update the version in `pyproject.toml`, `.codex-plugin/plugin.json`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `claude-desktop/manifest.json`, and `claude-desktop/pyproject.toml`.
2. In `claude-desktop/pyproject.toml`, update the pinned dependency to the exact same PyPI version.
3. Run:

   ```bash
   python -m pip install -e ".[dev]"
   python -m ruff check .
   python -m pytest -q
   python -m build --sdist --wheel
   python scripts/check_release_boundary.py
   python scripts/check_marketplace_release.py --no-remote
   ```

4. Inspect that both wheel and sdist exclude forbidden paths: `data/`, `paper/`, `paper_usenix/`, `reports/`, and `cyberhuatuo/sandbox/`.
5. Create the GitHub release `v0.2.0` and let `release.published` trigger `Publish PyPI`.
6. If release publication is blocked by UI/API access but the tag already exists and is reachable from `origin/main`, use the **GitHub Actions workflow page** for `.github/workflows/publish-pypi.yml` and click **Run workflow** with `release_tag=v0.2.0`, or run `gh workflow run publish-pypi.yml -f release_tag=v0.2.0`, then inspect it with `gh run list --workflow publish-pypi.yml --limit 5`. If GitHub CLI is unavailable, use the **GitHub Web Release** form URL with the `tag` query parameter to publish the release in the browser. This is a protected fallback, not a token upload: it still checks tag format, tag reachability from `origin/main`, package version equality, launch-assets/lint/tests/build/release-boundary, and OIDC Trusted Publishing without `PYPI_TOKEN`.
7. The `Publish PyPI` workflow builds, checks, and publishes without `PYPI_TOKEN`.
8. Verify from a clean virtual environment:

   ```bash
   pip install --upgrade cyberhuatuo
   cyberhuatuo --help
   uvx --from cyberhuatuo cyberhuatuo-mcp
   ```
9. Verify the strict public marketplace gate:

   ```bash
   python scripts/check_marketplace_release.py --remote --strict-remote --username <maintainer-github> --framework langchain --release-tag v0.2.0 --target-contributors 3
   cyberhuatuo market-ready --remote --strict-remote --username <maintainer-github> --framework langchain --release-tag v0.2.0 --target-contributors 3
   ```
10. Record the PyPI page as a real launch-return source:

   ```bash
   cyberhuatuo record-return --username <maintainer-github> --framework langchain --surface "PyPI release" --source-url https://pypi.org/project/cyberhuatuo/
   ```
11. Start the public cold-start campaign with an explicit target count:

   ```bash
   cyberhuatuo launch-campaign --username <maintainer-github> --framework langchain --release-tag v0.2.0 --target-contributors 3 --surface "PyPI release"
   ```

   The output must include **Campaign Recap And Next Sprint**: observed real contributors, shortfall, disclosed next-target rule, copy-ready recap, next `growth_campaign` / `cyberhuatuo launch-campaign` command, and `cyberhuatuo traction-proof --record-snapshot`. Do not count stars, downloads, reposts, or private claims as reached contributors.
12. Check public traction proof before claiming breakout:

   ```bash
   cyberhuatuo record-market --username <maintainer-github> --framework langchain --channel pypi --status submitted --submission-url <reviewable public URL> --release-tag v0.2.0
   cyberhuatuo market-status --username <maintainer-github> --framework langchain --release-tag v0.2.0
   ```

   The Marketplace Submission Ledger must contain only reviewable public URL evidence. It is valid to record `submitted`, `pending`, or `needs-review` while marketplace review is ongoing, but do not claim a channel is live unless the recorded status is `approved` or `published`.

   ```bash
   cyberhuatuo traction-proof --username <maintainer-github> --framework langchain --release-tag v0.2.0 --target-contributors 3
   ```

   This report reads GitHub REST API, GitHub Pull Requests API, GitHub Contents API, GitHub Releases API, PyPI JSON API, and the local activation/share ledger. It checks release trigger readiness by verifying that the requested GitHub Release tag is visible, non-draft, non-prerelease, and able to trigger `.github/workflows/publish-pypi.yml` on `release.published`; if PyPI JSON already serves the current local version, a missing GitHub Release is reported as a public provenance warning because the protected manual `workflow_dispatch` `release_tag` fallback can also close the registry path. It checks PyPI package readiness by comparing PyPI JSON API `info.version` with the local package version; if the registry install would deliver an older build, treat it as an install-loop launch blocker and publish through PyPI Trusted Publishing before claiming breakout. It also checks remote IssueOps readiness through GitHub Contents API on the repository default branch; missing Growth Flywheel, Share Proof, or Launch Campaign forms/workflows are public launch blockers, and `issues/new?...` URLs remain form entrypoints rather than proof URLs until a created public Issue/PR/Discussion URL exists. Target contributor progress comes from real public issue authors, public PR authors, and local ledger actors only. PR authors count as contributor identities, but PRs stay separate from IssueOps issue counts. stars, forks, watchers, subscribers, and downloads are not used as contributor progress; downloads are not used because PyPI JSON API `downloads` is deprecated and not a proof source.
12. Record public traction velocity only after a real market check:

   ```bash
   cyberhuatuo traction-proof --username <maintainer-github> --framework langchain --release-tag v0.2.0 --target-contributors 3 --record-snapshot
   ```

   Snapshot history is opt-in and append-only. Each JSONL snapshot records current public repository signals, public PR author proof, IssueOps proof counts, remote IssueOps readiness, release trigger readiness, PyPI package readiness, local ledger counts, and Target contributor progress, then reports velocity deltas against the previous real snapshot. It must not record or invent downloads, retention, repost counts, referrals, rewards, private analytics, or fake contributors.

PyPI page checklist:

- Description clearly says MCP, Codex, Claude, AI-agent debugging, and soul ring contribution loop.
- Project URLs include the MCP install guide and this marketplace release plan.
- The README shows the First Soul Ring path and the `accepted-prescription` promotion path.
- The page points to `JinNing6/CyberHuaTuo-Plugin`, not the legacy application repository, once this repository becomes the package authority.

## Claude

Goal: make CyberHuaTuo usable from Claude Code immediately, then prepare for Claude Desktop and the Claude Connectors Directory without mixing the two review paths.

Current install path:

- Claude Code plugin manifest: `.claude-plugin/plugin.json`
- Claude Code marketplace catalog: `.claude-plugin/marketplace.json`
- Local validation command: `claude plugin validate .`
- Marketplace install command:

  ```bash
  claude plugin marketplace add JinNing6/CyberHuaTuo-Plugin
  claude plugin install cyberhuatuo-plugin@cyberhuatuo
  ```

- Local plugin test command:

  ```bash
  claude --plugin-dir .
  ```

Claude Code community-marketplace submission:

1. Run local validation:

   ```bash
   claude plugin validate .
   claude --plugin-dir .
   ```

2. Submit through one of Anthropic's plugin submission forms:
   - `https://claude.ai/settings/plugins/submit`
   - `https://platform.claude.com/plugins/submit`
3. Target the reviewed community marketplace, `claude-community`. Do not claim inclusion in `claude-plugins-official`; Anthropic curates that separately.
4. Keep `.claude-plugin/marketplace.json` and `.claude-plugin/plugin.json` versioned so reviewers can pin a specific commit SHA.
5. Test after approval:

   ```bash
   claude plugin marketplace add anthropics/claude-plugins-community
   claude plugin marketplace list
   claude plugin install cyberhuatuo-plugin@claude-community
   ```

Claude Desktop path:

1. Keep the PyPI MCP command stable:

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

2. Maintain the Claude Desktop MCPB assets:
   - `claude-desktop/manifest.json`
   - `claude-desktop/pyproject.toml`
   - `claude-desktop/src/server.py`
   - `claude-desktop/.mcpbignore`
   - `docs/PRIVACY.md`
   - `.github/workflows/package-claude-mcpb.yml`
3. Validate and package the MCPB:

   ```bash
   npm install -g @anthropic-ai/mcpb
   mcpb validate claude-desktop
   mcpb pack claude-desktop dist/cyberhuatuo-claude-desktop.mcpb
   ```

4. Install the generated `.mcpb` in Claude Desktop and exercise the core tools: `diagnose`, `search_knowledge_base`, `fetch_official_docs`, `upload_prescription`, `global_leaderboard`, `soul_ring_campaign_pack`, `marketplace_readiness_gate`, `soul_ring_launch_campaign`, `soul_ring_bounty_board`, `soul_ring_traction_proof`, `soul_ring_growth_flywheel`, `soul_ring_activation_funnel`, `soul_ring_share_attribution_report`, and `soul_ring_share_proof_leaderboard`.
5. Keep MCP tool annotations current. Every MCP tool must declare a title plus accurate `readOnlyHint` and `destructiveHint` semantics before directory submission.

Claude Connectors Directory path:

- Submit either a remote MCP connector or a Desktop Extension/MCPB.
- For this local Python MCP, the practical first submission target is MCPB.
- Before submission, run `claude plugin validate .`, `mcpb validate claude-desktop`, test the MCP tools in Claude, and prepare screenshots.
- Keep every tool description honest: read-only tools should not imply writes; write tools such as upload/promotion routes must disclose GitHub side effects.
- Link `docs/PRIVACY.md` from the MCPB manifest and any directory submission.
- Prepare the directory submission fields: server name, tagline, description, transport, read/write capability summary, data handling, third-party services, public documentation, support link, privacy policy, tools list with human-readable names, working examples, and tested surfaces.

Submission story:

> CyberHuaTuo helps Claude diagnose AI-agent framework failures and turns real community fixes into a soul ring ladder, making debugging knowledge reusable and publicly ranked.

## Codex

Goal: make CyberHuaTuo installable as a Codex workflow plugin and as a plain MCP server.

Current install path:

- Codex plugin manifest: `.codex-plugin/plugin.json`
- Codex marketplace catalog: `.agents/plugins/marketplace.json`
- Shared MCP config: `.mcp.json`
- PyPI MCP command: `uvx --from cyberhuatuo cyberhuatuo-mcp`

Codex MCP setup:

```bash
codex mcp add cyberhuatuo -- uvx --from cyberhuatuo cyberhuatuo-mcp
codex mcp list
```

Codex plugin directory path:

```bash
codex plugin marketplace add JinNing6/CyberHuaTuo-Plugin
codex plugin marketplace list
```

1. Keep `.codex-plugin/plugin.json` synced with package version, repository, license, skills, and `.mcp.json`.
2. Ensure workspace admins can review the plugin's app/MCP requirements before enabling it.
3. Keep all public skills under `skills/` and all public MCP entrypoints in `.mcp.json`.
4. Keep `.agents/plugins/marketplace.json` pointing at the repository-root plugin so GitHub marketplace installs stay one-step.
5. Use the PyPI release as the stable install target instead of requiring users to clone the repository.
6. Add, install, and run the plugin from a clean Codex workspace before broader promotion.
7. Use Codex workspace sharing only for controlled pilots. Workspace sharing is not a public Plugin Directory launch; the public path is the marketplace catalog plus the stable repository/PyPI entrypoint.

Codex marketplace copy:

> Install CyberHuaTuo in Codex to diagnose AI-agent errors, search reusable prescriptions, and join the First Soul Ring contribution ladder from inside your coding agent.

## Growth Launch Sequence

1. Add `JinNing6/CyberHuaTuo-Plugin` as an additional PyPI Trusted Publisher.
2. Bump every release version field past the already-published `0.1.0`.
3. Publish the PyPI package through `.github/workflows/publish-pypi.yml`.
4. Verify `uvx --from cyberhuatuo cyberhuatuo-mcp` from a clean machine.
5. Publish the GitHub release with a short soul ring launch post.
6. Generate the launch scroll:

   ```bash
   cyberhuatuo launch --username <maintainer-github> --framework langchain --release-tag v0.2.0
   ```

7. Generate the Soul Ring Bounty Board before public posts so external users see real claimable coverage gaps:

   ```bash
   cyberhuatuo bounty --username <maintainer-github> --framework auto --top-n 8 --release-tag v0.2.0 --target-contributors 3
   ```

   GitHub New issue path: `.github/ISSUE_TEMPLATE/soul-ring-bounty-board.yml`; comment workflow: `.github/workflows/soul-ring-bounty-board.yml`.

   The board reads local real case files and supported framework definitions, ranks framework coverage gaps, and prints First Soul Ring Issue routes plus launch preflight, `record-return --surface "Bounty Board Issue" --source-url <created Issue URL>`, `activation`, `flywheel`, `challenge`, `first-invite`, `proof-pack`, `market-copy`, and `traction-proof` commands. It does not invent downloads, retention, repost counts, referrals, rewards, reviews, or fake contributors.

   `cyberhuatuo proof-pack`, `cyberhuatuo market-ready`, and `cyberhuatuo market-copy` must expose **Prefilled Bounty Board Issue** plus `cyberhuatuo bounty --username <maintainer-github> --framework auto --top-n 8`, so public launch traffic can reach claimable framework gaps without a second discovery step.

8. Generate the launch campaign with a target first-ring contributor count:

   ```bash
   cyberhuatuo launch-campaign --username <maintainer-github> --framework langchain --release-tag v0.2.0 --target-contributors 3
   ```

   Use the generated **Campaign Recap And Next Sprint** to state reached vs shortfall, observed real contributors, the disclosed next-target rule, copy-ready recap text, the next `growth_campaign` command, and the proof-recording command before posting another launch wave.

9. Check public traction proof before claiming breakout:

   ```bash
   cyberhuatuo traction-proof --username <maintainer-github> --framework langchain --release-tag v0.2.0 --target-contributors 3
   ```

   The report must use GitHub REST API, GitHub Pull Requests API, GitHub Contents API, GitHub Releases API, PyPI JSON API, and local ledger events. It must block on missing default-branch IssueOps files and older PyPI latest versions before diagnosing local conversion. Missing/draft/prerelease release tags remain public provenance warnings when PyPI latest-version proof is already current through the protected manual `workflow_dispatch` `release_tag` fallback; they remain launch blockers when the registry is stale. **Target contributor progress** must come from real public issue authors, public PR authors, and local return/share-attribution actors only. PR authors may count as contributor identities, but PRs must remain a separate proof surface and must not be mixed into Growth/Share IssueOps issue counts. stars, forks, watchers, subscribers, downloads, reposts, retention, referral conversions, and rewards are not contributor progress; downloads are not used.

10. Record a real traction snapshot after each public launch pulse:

   ```bash
   cyberhuatuo traction-proof --username <maintainer-github> --framework langchain --release-tag v0.2.0 --target-contributors 3 --record-snapshot
   ```

   The snapshot ledger is append-only and compares velocity deltas against prior real snapshots instead of static vanity metrics. It records remote IssueOps readiness, release trigger readiness, and PyPI package readiness alongside public proof counts so campaign recaps can distinguish closed-loop growth from blocked install/submission routes. Do not record or invent downloads, retention, repost counts, referrals, rewards, private analytics, or fake contributors.

10. Open the **Soul Ring Launch Campaign** IssueOps form at `.github/ISSUE_TEMPLATE/soul-ring-launch-campaign.yml`. The `.github/workflows/soul-ring-launch-campaign.yml` workflow must comment safe commands only, sanitize the target contributor count as a positive integer, route to Growth Flywheel and Share Proof issue routes, and avoid checkout, repository scripts, point awards, downloads, retention, repost counts, referrals, rewards, or Spirit Power claims.

11. Record the first reviewable external return into the local activation ledger:

   ```bash
   cyberhuatuo record-return --username <maintainer-github> --framework langchain --surface "PyPI release" --source-url <https-url>
   ```

12. Inspect the activation funnel before claiming a closed loop:

   ```bash
   cyberhuatuo activation --username <maintainer-github> --framework langchain --sect CyberHuaTuo-Sect --members <maintainer-github> --top-n 10
   ```

13. Generate the growth flywheel snapshot and disclose missing external metrics:

   ```bash
   cyberhuatuo flywheel --username <maintainer-github> --framework langchain --sect CyberHuaTuo-Sect --members <maintainer-github> --top-n 10
   ```

14. Open the generated Prefilled Growth Flywheel Issue URL. It should prefill the template, title, user, framework, growth surface, real signal, bottleneck, and campaign hook without privileged `labels`, `assignees`, or `milestone` query parameters.
15. Seed three real First Soul Ring issues from actual bugs.
16. Label accepted fixes with `accepted-prescription` so the promotion workflow creates public case PRs.
17. Post the generated launch/flywheel/ladder/card/campaign copy in GitHub Discussions, X, Weibo, Discord, and agent communities.
18. Record the public share attribution after posting:

   ```bash
   cyberhuatuo record-share --username <maintainer-github> --framework langchain --share-url <https-url>
   ```

19. Inspect the share attribution report before claiming a public proof loop:

   ```bash
   cyberhuatuo share-report --username <maintainer-github> --framework langchain --top-n 10
   cyberhuatuo share-leaderboard --framework langchain --top-n 10
   ```

20. Submit the Claude Code plugin to `claude-community` after `claude plugin validate .`.
21. Submit Claude MCPB or remote connector after local Claude Desktop validation.
22. Submit or circulate the Codex plugin package after PyPI and `.codex-plugin/plugin.json` are stable.

## Source Notes

- Official PyPI / PyPA references checked on 2026-06-04:
  - `https://docs.pypi.org/trusted-publishers/using-a-publisher/`
  - `https://docs.pypi.org/project_metadata/`
  - `https://docs.pypi.org/api/json/`
  - `https://packaging.pypa.io/en/stable/version.html`
  - `https://packaging.python.org/en/latest/flow/`
  - `https://build.pypa.io/en/latest/`
- Official GitHub references checked on 2026-06-03:
  - `https://docs.github.com/en/rest/repos`
  - `https://docs.github.com/en/rest/repos/contents`
  - `https://docs.github.com/en/rest/releases/releases#get-a-release-by-tag-name`
  - `https://docs.github.com/en/rest/issues`
  - `https://docs.github.com/en/rest/pulls/pulls`
- Official Anthropic references checked on 2026-06-04:
  - `https://claude.com/docs/connectors/building/mcpb`
  - `https://claude.com/docs/connectors/building/submission`
  - `https://claude.com/docs/plugins/submit`
- Official OpenAI references checked on 2026-06-04:
  - `https://openai.com/academy/codex-plugins-and-skills/`
  - `https://help.openai.com/en/articles/20001256/`
- PyPI Trusted Publishing uses GitHub Actions OIDC and avoids long-lived PyPI tokens. For GitHub Actions publishers, PyPI requires the repository owner, repository name, authorized workflow filename, and optionally an environment name.
- Python package releases should build both wheel and sdist before upload.
- PyPI package readiness in traction proof compares PyPI JSON API `info.version` with local package metadata using Python packaging version ordering; an older PyPI latest version is an install-loop blocker that routes back to the Trusted Publishing workflow.
- GitHub Releases API checks `releases/tags/{tag}` so a release-triggered PyPI workflow has a real, matching, non-draft, non-prerelease `release.published` event source before registry freshness is blamed; if PyPI latest-version proof is already current, the missing release is disclosed as provenance debt because the protected manual `workflow_dispatch` `release_tag` fallback can also close the registry path.
- GitHub Contents API checks default-branch IssueOps forms/workflows for Growth Flywheel, Share Proof, and Launch Campaign before generated `issues/new?...` form URLs are treated as live acquisition loops.
- GitHub Pull Requests API can provide public PR author identities for target-contributor proof, but PR counts remain separate from IssueOps issue counts.
- Claude Code plugin marketplaces are Git-backed catalogs; third-party plugins can be submitted to `claude-community` through Anthropic's forms after `claude plugin validate`.
- Claude Desktop Extensions are distributed as MCPB bundles; the Claude Connectors Directory reviews remote MCPs, MCPB desktop extensions, and MCP Apps.
- Codex plugins package reusable workflow capability and may include skills plus MCP/app-backed capabilities. Codex can read repo-scoped marketplace files from `$REPO_ROOT/.agents/plugins/marketplace.json`, and `codex plugin marketplace add owner/repo` installs and tracks a marketplace source.
