# Soul Ring Growth Loop Design

## Goal

Turn the existing Soul Land-inspired soul ring system from a visual theme into a growth loop: contributors should immediately understand how to earn the first ring, what their next ring requires, and why the result is worth sharing.

## Growth Loop

1. A developer sees the soul ring ladder in the README or an MCP/CLI output.
2. They can run `cyberhuatuo mission` or call `soul_ring_mission_hall` to see the Issue, PR, personal ring, and sect/team paths in one screen.
3. They understand that every prescription in a technical direction upgrades a visible combat resume.
4. They submit or upload a prescription.
5. The CLI/MCP output shows rank, current rings, next-ring gap, and a share card.
6. The share card points others back to the repository and contribution flow.

## First Implementation Slice

- Add a reusable next-ring progress helper to `cyberhuatuo.achievements`.
- Add a reusable Soul Ring Mission Hall entry that joins the GitHub Issue form, PR settlement, personal soul-ring actions, MCP install path, and sect/team actions.
- Show next-ring progress in alchemy direction output and share cards.
- Strengthen README and README_CN copy around the first-ring loop.
- Add tests for ring thresholds, next-ring gaps, direction mapping, and share-card CTA text.

## Sect Growth Extension

- Treat a sect/team as an explicit list of real GitHub members, not as a persisted or invented organization.
- Generate sect cards, quest boards, duel cards, and arena snapshots from current real prescription counts.
- Generate a sect hall snapshot that maps current real member prescription counts into a Douluo-style sect / academy / clan ladder: Outer Disciple, Inner Disciple, Core Disciple, Hall Deacon, and Sect Elder.
- Disclose the formula in every competitive output: sect power is the sum of current real prescription counts from listed members.
- Make every public artifact copy-ready for GitHub comments, X/Weibo, and agent chat, with direct `sect`, `sect-quest`, `sect-hall`, `sect-duel`, `challenge`, `quest`, and `campaign` commands.
- Keep arena output as a current snapshot only; do not invent wins, season history, hidden scores, or simulated adoption.

## GitHub Conversion Surface

- Add a GitHub Issue Form for the first soul ring so new visitors can enter through the repository UI before learning the CLI.
- Add `.github/ISSUE_TEMPLATE/config.yml` so the New Issue chooser behaves like a Soul Ring Mission Hall: blank issues are disabled for normal contributors, and the chooser points to First Soul Ring, MCP install, and sect/team paths.
- Require real GitHub username, framework, symptom/reproduction, root cause, prescription, and verification evidence.
- Include a real-data pledge in the form so public soul-ring rankings remain grounded in real fixes.
- Point README and README_CN at the form path and name so the web-first path sits beside CLI/MCP onboarding.
- Add a minimal-permission issue workflow that comments on new `first-soul-ring` issues with copy-ready `challenge`, `upload`, `ranking`, `card`, and `campaign` commands.
- Keep the workflow comment deterministic and avoid executing or shell-interpolating issue body content.
- Add a pull request template that turns a real fix review into a Soul Ring PR Settlement with contributor, framework, linked issue, verification evidence, and copy-ready settlement commands.
- Add a minimal-permission PR workflow that comments on opened ready PRs with Soul Ring PR Settlement commands, without checking out, building, or running untrusted PR code.

## Non-goals

- No new web app or heavy visual redesign in this slice.
- No fabricated contributor data.
- No fabricated sect wins, season history, hidden ranking sources, or simulated team adoption.
- No weakening existing diagnosis, MCP, CLI, or packaging behavior.

## Verification

- `python -m pytest -q`
- `python -m ruff check .`
- Representative CLI command still works: `python -m cyberhuatuo search "ImportError cannot import ChatOpenAI" --framework langchain --top-k 1`
