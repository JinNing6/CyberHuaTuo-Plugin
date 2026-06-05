import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from cyberhuatuo import achievements, activation, install, submissions, traction

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_PYPI_VERSION = "0.1.0"
ISSUEOPS_CONTENT_PREFIX = "https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin/contents/"
RELEASE_TAG_PREFIX = "https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin/releases/tags/"
ISSUEOPS_CONTENT_PATHS = tuple(path for _label, path in traction.ISSUEOPS_REQUIRED_FILES)
CANDIDATE_INSTALL_V020 = (
    'python -m pip install --upgrade "cyberhuatuo @ '
    'git+https://github.com/JinNing6/CyberHuaTuo-Plugin.git@v0.2.0"'
)
REGISTRY_INSTALL = "python -m pip install --upgrade cyberhuatuo"


def _assert_candidate_install_precedes_registry(text: str) -> None:
    assert CANDIDATE_INSTALL_V020 in text
    assert REGISTRY_INSTALL in text
    assert text.index(CANDIDATE_INSTALL_V020) < text.index(REGISTRY_INSTALL)
    assert "\nInstall: pip install cyberhuatuo" not in text
    assert "\npip install cyberhuatuo\n" not in text


def test_remote_issueops_required_files_cover_full_public_acquisition_loop():
    required_paths = set(ISSUEOPS_CONTENT_PATHS)
    expected_paths = {
        ".github/ISSUE_TEMPLATE/soul-ring-prescription.yml",
        ".github/workflows/soul-ring-issue.yml",
        ".github/ISSUE_TEMPLATE/soul-ring-growth-flywheel.yml",
        ".github/workflows/soul-ring-growth-flywheel.yml",
        ".github/ISSUE_TEMPLATE/soul-ring-bounty-board.yml",
        ".github/workflows/soul-ring-bounty-board.yml",
        ".github/ISSUE_TEMPLATE/soul-ring-share-proof.yml",
        ".github/workflows/soul-ring-share-proof.yml",
        ".github/ISSUE_TEMPLATE/soul-ring-launch-campaign.yml",
        ".github/workflows/soul-ring-launch-campaign.yml",
        ".github/ISSUE_TEMPLATE/soul-ring-tournament.yml",
        ".github/workflows/soul-ring-tournament.yml",
        ".github/ISSUE_TEMPLATE/soul-ring-mentor.yml",
        ".github/workflows/soul-ring-mentor.yml",
        ".github/ISSUE_TEMPLATE/soul-ring-sect-recruit.yml",
        ".github/workflows/soul-ring-sect-recruit.yml",
        ".github/ISSUE_TEMPLATE/soul-ring-season.yml",
        ".github/workflows/soul-ring-season.yml",
    }

    assert expected_paths <= required_paths
    assert ".github/workflows/soul-ring-pr.yml" not in required_paths
    assert ".github/workflows/soul-ring-promote.yml" not in required_paths
    assert ".github/pull_request_template.md" not in required_paths


def _fake_ready_issueops_content(url: str, missing: set[str] | None = None):
    if not url.startswith(ISSUEOPS_CONTENT_PREFIX):
        return None
    path = url.removeprefix(ISSUEOPS_CONTENT_PREFIX)
    if path in (missing or set()):
        raise OSError(f"missing remote IssueOps file: {path}")
    if path in ISSUEOPS_CONTENT_PATHS:
        return {"type": "file", "path": path, "download_url": f"https://raw.githubusercontent.com/{path}"}
    return None


def _fake_ready_release(url: str, tag: str = "v0.2.0"):
    if url == f"{RELEASE_TAG_PREFIX}{tag}":
        return {
            "tag_name": tag,
            "draft": False,
            "prerelease": False,
            "html_url": f"https://github.com/JinNing6/CyberHuaTuo-Plugin/releases/tag/{tag}",
            "published_at": "2026-06-04T00:00:00Z",
        }
    return None


def test_current_install_command_uses_pypi_when_registry_is_current_and_routes_first_ring():
    def fake_fetcher(url, _headers, _timeout):
        assert url == "https://pypi.org/pypi/cyberhuatuo/json"
        return {"info": {"version": "0.2.0"}, "releases": {"0.2.0": []}, "urls": []}

    report = install.build_current_install_command(
        username="alice",
        framework="langchain",
        release_tag="v0.2.0",
        target_contributors=3,
        fetcher=fake_fetcher,
    )
    text = install.format_current_install_command(
        username="alice",
        framework="langchain",
        release_tag="v0.2.0",
        target_contributors=3,
        fetcher=fake_fetcher,
    )

    assert report["status"] == "registry-current"
    assert report["recommended_install_command"] == "python -m pip install --upgrade cyberhuatuo"
    assert "CyberHuaTuo Install Command" in text
    assert "PyPI JSON API: pass" in text
    assert "PyPI latest version: `0.2.0`" in text
    assert "Recommended install: `python -m pip install --upgrade cyberhuatuo`" in text
    assert "Git Tag Candidate Install Bridge" not in text
    assert "cyberhuatuo challenge --username alice --framework langchain" in text
    assert "cyberhuatuo proof-pack --username alice --framework langchain --release-tag v0.2.0" in text
    assert "current_install_command" in text
    assert "does not invent downloads" in text


def test_current_install_command_uses_git_tag_bridge_when_pypi_is_stale():
    def fake_fetcher(url, _headers, _timeout):
        assert url == "https://pypi.org/pypi/cyberhuatuo/json"
        return {"info": {"version": PREVIOUS_PYPI_VERSION}, "releases": {PREVIOUS_PYPI_VERSION: []}, "urls": []}

    report = install.build_current_install_command(
        username="alice",
        framework="langchain",
        release_tag="v0.2.0",
        target_contributors=3,
        fetcher=fake_fetcher,
    )
    text = install.format_current_install_command(
        username="alice",
        framework="langchain",
        release_tag="v0.2.0",
        target_contributors=3,
        fetcher=fake_fetcher,
    )

    assert report["status"] == "registry-stale"
    assert (
        report["recommended_install_command"]
        == 'python -m pip install --upgrade "cyberhuatuo @ git+https://github.com/JinNing6/CyberHuaTuo-Plugin.git@v0.2.0"'
    )
    assert "PyPI JSON API: pass" in text
    assert "PyPI latest version: `0.1.0`" in text
    assert "Canonical PyPI install: `python -m pip install --upgrade cyberhuatuo`" in text
    assert "## Git Tag Candidate Install Bridge" in text
    assert (
        'python -m pip install --upgrade "cyberhuatuo @ '
        'git+https://github.com/JinNing6/CyberHuaTuo-Plugin.git@v0.2.0"'
    ) in text
    assert "does not close the PyPI install loop" in text
    assert "cyberhuatuo market-ready --remote --strict-remote --username alice" in text
    assert "cyberhuatuo traction-proof --username alice --framework langchain --release-tag v0.2.0" in text


def test_current_install_command_falls_back_to_bridge_when_registry_cannot_be_verified():
    def fake_fetcher(_url, _headers, _timeout):
        raise OSError("network unavailable")

    text = install.format_current_install_command(
        username="alice",
        framework="langchain",
        release_tag="v0.2.0",
        target_contributors=3,
        fetcher=fake_fetcher,
    )

    assert "PyPI JSON API: fail" in text
    assert "network unavailable" in text
    assert "registry-unverified" in text
    assert "Git Tag Candidate Install Bridge" in text
    assert "Recheck PyPI latest-version proof before claiming public install readiness." in text


def test_next_soul_ring_progress_moves_from_first_to_second_ring():
    progress = achievements.get_next_soul_ring_progress(1)

    assert progress["current_ring_name"] == "一环"
    assert progress["next_ring_name"] == "黄环"
    assert progress["needed"] == 1
    assert "再贡献 1 方" in progress["hint_cn"]


def test_next_soul_ring_progress_caps_at_nine_ring_supreme():
    progress = achievements.get_next_soul_ring_progress(81)

    assert progress["is_max"] is True
    assert progress["needed"] == 0
    assert progress["next_ring_name"] == "九环至尊"
    assert "九环至尊" in progress["hint_cn"]


def test_alchemy_direction_output_includes_next_ring_prompt(monkeypatch):
    monkeypatch.setattr(
        achievements,
        "count_contributor_cases_by_framework",
        lambda _username: {"langchain": 1},
    )

    output = achievements.format_alchemy_directions("alice")

    assert "炼魂" in output
    assert "下一环" in output
    assert "再贡献 1 方" in output


def test_share_card_includes_next_ring_call_to_action(monkeypatch):
    monkeypatch.setattr(
        achievements,
        "get_cultivation_profile",
        lambda username: {
            "github": username,
            "contribution_count": 1,
            "title_emoji": "⭐",
            "title_cn": "一星炼丹师",
            "title_en": "One-Star Alchemist",
            "global_rank": 1,
            "global_total": 1,
            "percentile": 100.0,
            "is_rank_one": True,
        },
    )
    monkeypatch.setattr(
        achievements,
        "_load_streak",
        lambda _username: {"current_streak": 0},
    )
    monkeypatch.setattr(
        achievements,
        "count_contributor_cases_by_framework",
        lambda _username: {"langchain": 1},
    )

    card = achievements.generate_share_card("alice")

    assert "下一环" in card
    assert "再贡献 1 方" in card
    assert "LangChain" in card
    assert "下一环: 下一环" not in card


def test_share_card_includes_copy_ready_soul_ring_challenge(monkeypatch):
    monkeypatch.setattr(
        achievements,
        "get_cultivation_profile",
        lambda username: {
            "github": username,
            "contribution_count": 1,
            "title_emoji": "⭐",
            "title_cn": "一星炼丹师",
            "title_en": "One-Star Alchemist",
            "global_rank": 1,
            "global_total": 1,
            "percentile": 100.0,
            "is_rank_one": True,
        },
    )
    monkeypatch.setattr(
        achievements,
        "_load_streak",
        lambda _username: {"current_streak": 0},
    )
    monkeypatch.setattr(
        achievements,
        "count_contributor_cases_by_framework",
        lambda _username: {"langchain": 1},
    )

    card = achievements.generate_share_card("alice")

    assert "魂环挑战" in card
    assert "我在 CyberHuaTuo 点亮了" in card
    assert "https://github.com/JinNing6/CyberHuaTuo-Plugin" in card
    _assert_candidate_install_precedes_registry(card)
    assert "uvx --from cyberhuatuo cyberhuatuo-mcp" in card
    assert "cyberhuatuo record-share --username alice --framework langchain --share-url <https-url>" in card
    assert "#CyberHuaTuo" in card


def test_first_soul_ring_challenge_copy_puts_candidate_install_before_pypi():
    challenge = achievements.format_first_soul_ring_challenge("alice", "langchain")

    assert "First Soul Ring Challenge" in challenge
    assert "cyberhuatuo upload" in challenge
    _assert_candidate_install_precedes_registry(challenge)


def test_activation_event_ledger_records_external_return_and_names_weakest_stage(tmp_path, monkeypatch):
    ledger_path = tmp_path / "activation-events.jsonl"
    monkeypatch.setenv("CYBERHUATUO_ACTIVATION_LEDGER", str(ledger_path))

    record = activation.format_record_external_return(
        "alice",
        "langchain",
        "PyPI release",
        "https://example.com/pypi-post",
    )

    assert "External return recorded" in record
    assert f"Ledger: `{ledger_path}`" in record
    assert ledger_path.is_file()
    event = json.loads(ledger_path.read_text(encoding="utf-8").splitlines()[0])
    assert event["event_type"] == "external_return"
    assert event["username"] == "alice"
    assert event["framework"] == "langchain"
    assert event["source_url"] == "https://example.com/pypi-post"

    funnel = activation.format_activation_funnel("alice", "langchain", "CyberHuaTuo-Sect", ["alice"], 5)

    assert "Soul Ring Activation Funnel" in funnel
    assert "External return | 1" in funnel
    assert "First-session exposure | 0" in funnel
    assert "Weakest Conversion Stage: First-session exposure" in funnel
    assert "cyberhuatuo record-session --username alice --framework langchain" in funnel
    assert "cyberhuatuo flywheel --username alice --framework langchain" in funnel
    assert "No downloads, retention, or attribution metrics are invented" in funnel


def test_activation_ledger_reader_accepts_utf8_bom_without_losing_first_proof(tmp_path, monkeypatch):
    ledger_path = tmp_path / "activation-events.jsonl"
    monkeypatch.setenv("CYBERHUATUO_ACTIVATION_LEDGER", str(ledger_path))
    event = {
        "schema_version": 1,
        "event_id": "bom-proof",
        "timestamp_utc": "2026-06-05T00:00:00Z",
        "username": "alice",
        "framework": "langchain",
        "event_type": "external_return",
        "surface": "PyPI launch proof",
        "source_url": "https://example.com/created-growth-issue",
        "share_url": "",
        "note": "",
    }
    ledger_path.write_text(json.dumps(event, sort_keys=True) + "\n", encoding="utf-8-sig")

    funnel = activation.format_activation_funnel("alice", "langchain")

    assert "External return | 1" in funnel
    assert "Weakest Conversion Stage: First-session exposure" in funnel
    assert "line 1 is not valid JSON" not in funnel


def test_share_attribution_event_requires_reviewable_public_url(tmp_path, monkeypatch):
    ledger_path = tmp_path / "activation-events.jsonl"
    monkeypatch.setenv("CYBERHUATUO_ACTIVATION_LEDGER", str(ledger_path))

    invalid = activation.format_record_share_attribution("alice", "langchain", "not-a-url")
    assert "Share attribution not recorded" in invalid
    assert not ledger_path.exists()

    recorded = activation.format_record_share_attribution(
        "alice",
        "langchain",
        "https://example.com/share",
        source_url="https://example.com/pypi-post",
    )

    assert "Share attribution recorded" in recorded
    event = json.loads(ledger_path.read_text(encoding="utf-8").splitlines()[0])
    assert event["event_type"] == "share_attribution"
    assert event["share_url"] == "https://example.com/share"
    assert event["source_url"] == "https://example.com/pypi-post"


def test_share_attribution_report_summarizes_real_proofs_and_bottleneck(tmp_path, monkeypatch):
    ledger_path = tmp_path / "activation-events.jsonl"
    monkeypatch.setenv("CYBERHUATUO_ACTIVATION_LEDGER", str(ledger_path))

    activation.format_record_external_return(
        "alice",
        "langchain",
        "PyPI release",
        "https://example.com/pypi-post",
    )
    activation.format_record_share_attribution(
        "alice",
        "langchain",
        "https://example.com/share",
        source_url="https://example.com/pypi-post",
        surface="X launch post",
    )

    report = activation.format_share_attribution_report("alice", "langchain", top_n=5)

    assert "Soul Ring Share Attribution Report" in report
    assert "Share proof events: 1" in report
    assert "https://example.com/share" in report
    assert "https://example.com/pypi-post" in report
    assert "Source-to-share bridges: 1 / 1" in report
    assert "Actor Pull" in report
    assert "Artifact Pull" in report
    assert "Current Proof Bottleneck" in report
    assert "cyberhuatuo share-report --username alice --framework langchain --top-n 5" in report
    assert "cyberhuatuo record-share --username alice --framework langchain --share-url <https-url>" in report
    assert "cyberhuatuo activation --username alice --framework langchain" in report
    assert "cyberhuatuo flywheel --username alice --framework langchain" in report
    assert "No downloads, retention, repost counts, referral conversions, or rewards are invented" in report
    assert "1000 users" not in report
    assert "simulated" not in report.lower()


def test_share_attribution_report_empty_ledger_recruits_first_proof_without_fake_metrics(tmp_path, monkeypatch):
    ledger_path = tmp_path / "activation-events.jsonl"
    monkeypatch.setenv("CYBERHUATUO_ACTIVATION_LEDGER", str(ledger_path))

    report = activation.format_share_attribution_report("alice", "langchain", top_n=5)

    assert "Soul Ring Share Attribution Report" in report
    assert "Share proof events: 0" in report
    assert "Current Proof Bottleneck: No public share proof recorded" in report
    assert "cyberhuatuo record-share --username alice --framework langchain --share-url <https-url>" in report
    assert "No downloads, retention, repost counts, referral conversions, or rewards are invented" in report
    assert "1000 users" not in report
    assert "fake" not in report.lower()
    assert "simulated" not in report.lower()


def test_share_proof_leaderboard_ranks_only_reviewable_public_http_share_urls(tmp_path, monkeypatch):
    ledger_path = tmp_path / "activation-events.jsonl"
    monkeypatch.setenv("CYBERHUATUO_ACTIVATION_LEDGER", str(ledger_path))

    activation.format_record_external_return(
        "alice",
        "langchain",
        "PyPI release",
        "https://example.com/pypi-post",
    )
    activation.format_record_share_attribution(
        "alice",
        "langchain",
        "https://example.com/alice-1",
        source_url="https://example.com/pypi-post",
        surface="X launch post",
    )
    activation.format_record_share_attribution(
        "alice",
        "langchain",
        "https://example.com/alice-1",
        surface="Duplicate proof",
    )
    activation.format_record_share_attribution(
        "alice",
        "langchain",
        "https://example.com/alice-2",
        surface="GitHub Discussion",
    )
    activation.format_record_share_attribution(
        "bob",
        "langchain",
        "https://example.com/bob-1",
        surface="Weibo",
    )
    with ledger_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps({
            "event_type": "share_attribution",
            "framework": "langchain",
            "username": "charlie",
            "share_url": "ftp://example.com/not-reviewable",
            "timestamp_utc": "2026-06-03T00:00:00Z",
        }, sort_keys=True) + "\n")

    leaderboard = activation.format_share_proof_leaderboard("langchain", top_n=5)

    assert "Soul Ring Share Proof Leaderboard" in leaderboard
    assert "Target Framework: `langchain`" in leaderboard
    assert "Share proof events: 4" in leaderboard
    assert "Reviewable unique share URLs: 3" in leaderboard
    assert "Scoring Formula: share proof score = count of unique reviewable public http(s) share URLs recorded as share_attribution events." in leaderboard
    assert "| 1 | @alice | 2 |" in leaderboard
    assert "| 2 | @bob | 1 |" in leaderboard
    assert "@charlie" not in leaderboard
    assert "https://example.com/alice-1" in leaderboard
    assert "https://example.com/alice-2" in leaderboard
    assert "cyberhuatuo record-share --username <github-username> --framework langchain --share-url <https-url>" in leaderboard
    assert "cyberhuatuo share-report --username <github-username> --framework langchain --top-n 5" in leaderboard
    assert "cyberhuatuo share-leaderboard --framework langchain --top-n 5" in leaderboard
    assert "Prefilled Share Proof Issue:" in leaderboard
    assert "soul-ring-share-proof.yml" in leaderboard
    assert "No downloads, retention, repost counts, referral conversions, rewards, or Spirit Power are invented" in leaderboard
    assert "1000 users" not in leaderboard
    assert "simulated" not in leaderboard.lower()


def test_share_proof_leaderboard_empty_ledger_recruits_first_share_without_fake_metrics(tmp_path, monkeypatch):
    ledger_path = tmp_path / "activation-events.jsonl"
    monkeypatch.setenv("CYBERHUATUO_ACTIVATION_LEDGER", str(ledger_path))

    leaderboard = activation.format_share_proof_leaderboard("langchain", top_n=5)

    assert "Soul Ring Share Proof Leaderboard" in leaderboard
    assert "Share proof events: 0" in leaderboard
    assert "No public share proof recorded yet" in leaderboard
    assert "cyberhuatuo record-share --username <github-username> --framework langchain --share-url <https-url>" in leaderboard
    assert "not treated as proven zero propagation" in leaderboard
    assert "fake" not in leaderboard.lower()
    assert "simulated" not in leaderboard.lower()


def test_growth_settlement_turns_upload_into_next_ring_chase(monkeypatch):
    monkeypatch.setattr(
        achievements,
        "count_contributor_cases_by_framework",
        lambda _username: {"langchain": 1},
    )

    settlement = achievements.format_growth_settlement("alice", "langchain")

    assert "即时追环" in settlement
    assert "@alice" in settlement
    assert "炼魂" in settlement
    assert "LangChain" in settlement
    assert "⚪ 一环" in settlement
    assert "下一环: 黄环" in settlement
    assert "再贡献 1 方" in settlement
    assert "`cyberhuatuo card alice`" in settlement


def test_growth_settlement_skips_anonymous_contributors():
    assert achievements.format_growth_settlement("anonymous", "langchain") == ""
    assert achievements.format_growth_settlement("", "langchain") == ""


def test_first_soul_ring_challenge_gives_one_command_onramp():
    challenge = achievements.format_first_soul_ring_challenge("alice", "langchain")

    assert "第一魂环挑战" in challenge
    assert "cyberhuatuo upload" in challenge
    assert "--framework langchain" in challenge
    assert "--contributor alice" in challenge
    assert "cyberhuatuo ranking alice" in challenge
    assert "cyberhuatuo card alice" in challenge
    assert "cyberhuatuo proof-pack --username alice --framework langchain" in challenge
    assert "下一环" in challenge
    assert "https://github.com/JinNing6/CyberHuaTuo-Plugin" in challenge
    assert "模拟" not in challenge


def test_soul_ring_mission_hall_routes_install_web_pr_and_sect_actions(monkeypatch):
    profile = {
        "github": "alice",
        "contribution_count": 2,
        "title_emoji": "*",
        "title_cn": "Apprentice",
        "title_en": "Apprentice",
        "global_rank": 3,
        "global_total": 10,
        "percentile": 70.0,
        "is_rank_one": False,
    }

    monkeypatch.setattr(achievements, "get_cultivation_profile", lambda username: profile)
    monkeypatch.setattr(achievements, "count_contributor_cases_by_framework", lambda _username: {"langchain": 2})

    hall = achievements.format_soul_ring_mission_hall(
        "alice",
        "langchain",
        "Azure Sect",
        ["alice", "bob"],
    )

    assert "Soul Ring Mission Hall" in hall
    assert "GitHub: @alice" in hall
    assert "Current Snapshot Formula: current real CyberHuaTuo knowledge-base counts" in hall
    assert "Real prescriptions: 2 real prescriptions" in hall
    assert "Global Rank: #3 / 10" in hall
    assert "Mission 1: First Soul Ring Prescription" in hall
    assert "issues/new?template=soul-ring-prescription.yml" in hall
    assert "Mission 2: PR Settlement" in hall
    assert ".github/pull_request_template.md" in hall
    assert ".github/workflows/soul-ring-pr.yml" in hall
    assert "Mission 3: Personal Soul Ring" in hall
    assert "cyberhuatuo challenge --username alice --framework langchain" in hall
    assert "cyberhuatuo ranking alice" in hall
    assert "cyberhuatuo card alice" in hall
    assert "cyberhuatuo campaign alice --framework langchain" in hall
    assert "Mission 4: Sect / Team Growth" in hall
    assert "cyberhuatuo sect-hall Azure-Sect alice bob --framework langchain" in hall
    assert "cyberhuatuo sect-quest Azure-Sect alice bob --framework langchain" in hall
    assert "Agent Prompt" in hall
    _assert_candidate_install_precedes_registry(hall)
    assert "MCP: uvx --from cyberhuatuo cyberhuatuo-mcp" in hall
    assert "not invented" in hall
    assert "simulated" not in hall.lower()


def test_soul_ring_mission_hall_handles_new_user_without_invented_progress(monkeypatch):
    profile = {
        "github": "newcomer",
        "contribution_count": 0,
        "title_emoji": "*",
        "title_cn": "Intern Apprentice",
        "title_en": "Intern Apprentice",
        "global_rank": 0,
        "global_total": 0,
        "percentile": 0.0,
        "is_rank_one": False,
    }

    monkeypatch.setattr(achievements, "get_cultivation_profile", lambda username: profile)
    monkeypatch.setattr(achievements, "count_contributor_cases_by_framework", lambda _username: {})

    hall = achievements.format_soul_ring_mission_hall("newcomer")

    assert "Soul Ring Mission Hall" in hall
    assert "GitHub: @newcomer" in hall
    assert "Real prescriptions: 0 real prescriptions" in hall
    assert "Global Rank: not ranked yet" in hall
    assert "First real prescription unlocks the first visible soul ring" in hall
    assert "cyberhuatuo challenge --username newcomer --framework langchain" in hall
    assert "cyberhuatuo sect-hall CyberHuaTuo-Sect newcomer --framework langchain" in hall
    assert "#0" not in hall
    assert "simulated" not in hall.lower()
    assert "fake" not in hall.lower()


def test_soul_ring_bounty_board_ranks_real_framework_gaps_without_fake_rewards(tmp_path, monkeypatch):
    cases_dir = tmp_path / "cases"
    (cases_dir / "langchain" / "community").mkdir(parents=True)
    (cases_dir / "crewai").mkdir(parents=True)
    (cases_dir / "langchain" / "community" / "case-1.md").write_text("# case 1", encoding="utf-8")
    (cases_dir / "langchain" / "community" / "case-2.md").write_text("# case 2", encoding="utf-8")
    (cases_dir / "crewai" / "case-1.md").write_text("# case 1", encoding="utf-8")
    monkeypatch.setattr(achievements.config, "CASES_DIR", cases_dir)

    board = achievements.format_soul_ring_bounty_board(
        "alice",
        "auto",
        top_n=5,
        release_tag="v0.2.0",
        target_contributors=3,
    )

    assert "# Soul Ring Bounty Board" in board
    assert "Coverage Gap Formula: target case floor minus current real local case count" in board
    assert "| autogen | AutoGen | agent | 0 | 3 | 3 |" in board
    assert "| dspy | DSPy | agent | 0 | 3 | 3 |" in board
    assert "issues/new?template=soul-ring-prescription.yml" in board
    assert "framework=autogen" in board
    assert "cyberhuatuo challenge --username alice --framework autogen" in board
    assert "cyberhuatuo first-invite --username alice --invitee <external-contributor-github-username> --framework autogen --release-tag v0.2.0 --target-contributors 3 --source-url <created Growth Issue URL after submission>" in board
    assert "cyberhuatuo bounty --username alice --framework auto --top-n 5 --release-tag v0.2.0 --target-contributors 3" in board
    assert "No downloads, retention, repost counts, referrals, rewards, or fake contributors are invented" in board
    assert "simulated" not in board.lower()


def test_soul_ring_bounty_board_can_focus_one_framework(tmp_path, monkeypatch):
    cases_dir = tmp_path / "cases"
    (cases_dir / "langchain").mkdir(parents=True)
    (cases_dir / "langchain" / "case-1.md").write_text("# case 1", encoding="utf-8")
    (cases_dir / "langchain" / "case-2.md").write_text("# case 2", encoding="utf-8")
    monkeypatch.setattr(achievements.config, "CASES_DIR", cases_dir)

    board = achievements.format_soul_ring_bounty_board("alice", "langchain", top_n=3)

    assert "| langchain | LangChain | agent | 2 | 3 | 1 |" in board
    assert "Current target framework only: `langchain`" in board
    assert "AutoGen" not in board


def test_soul_ring_launch_scroll_turns_marketplaces_into_first_ring_funnel():
    launch = achievements.format_soul_ring_launch_scroll(
        "alice",
        "langchain",
        "v0.2.0",
    )

    assert "Soul Ring Launch Scroll" in launch
    assert "Launch Asset Formula: current repository release assets and public commands" in launch
    assert "PyPI: `cyberhuatuo`" in launch
    _assert_candidate_install_precedes_registry(launch)
    assert "uvx --from cyberhuatuo cyberhuatuo-mcp" in launch
    assert "Claude Code: `.claude-plugin/plugin.json`" in launch
    assert "Claude Desktop MCPB: `claude-desktop/manifest.json`" in launch
    assert "mcpb validate claude-desktop" in launch
    assert "mcpb pack claude-desktop dist/cyberhuatuo-claude-desktop.mcpb" in launch
    assert "Codex: `.codex-plugin/plugin.json`" in launch
    assert "codex mcp add cyberhuatuo -- uvx --from cyberhuatuo cyberhuatuo-mcp" in launch
    assert "First Soul Ring Prescription" in launch
    assert "issues/new?template=soul-ring-prescription.yml" in launch
    assert ".github/workflows/soul-ring-promote.yml" in launch
    assert "accepted-prescription" in launch
    assert "cyberhuatuo challenge --username alice --framework langchain" in launch
    assert "cyberhuatuo mission --username alice --framework langchain" in launch
    assert "cyberhuatuo campaign alice --framework langchain" in launch
    assert "GitHub Discussion / Release Post" in launch
    assert "X / Weibo" in launch
    assert "Agent Prompt" in launch
    assert "No adoption numbers, fake champions, or historical seasons are invented" in launch
    assert "1000 users" not in launch
    assert "simulated" not in launch.lower()


def test_soul_ring_launch_campaign_turns_cold_launch_into_targeted_public_loop(monkeypatch):
    monkeypatch.setattr(
        achievements,
        "get_cultivation_profile",
        lambda username: {
            "github": username,
            "contribution_count": 1,
            "title_emoji": "*",
            "title_cn": "Apprentice",
            "title_en": "Apprentice",
            "global_rank": 2,
            "global_total": 3,
            "percentile": 50.0,
            "is_rank_one": False,
        },
    )
    monkeypatch.setattr(achievements, "count_contributor_cases_by_framework", lambda _username: {"langchain": 1})
    monkeypatch.setattr(achievements, "get_global_ranking_stats", lambda: {"alice": 1, "bob": 2})

    campaign = achievements.format_soul_ring_launch_campaign(
        "alice",
        "langchain",
        "v0.2.0",
        target_contributors=7,
        surface="PyPI / Claude / Codex launch",
    )

    assert "Soul Ring Launch Campaign" in campaign
    assert "Release: `v0.2.0`" in campaign
    assert "Campaign Target: 7 first-ring contributors" in campaign
    assert "Current real ranked contributors: 2" in campaign
    assert "## Campaign Recap And Next Sprint" in campaign
    assert "Observed real contributors: 2 / 7" in campaign
    assert "Campaign shortfall: 5 first-ring contributor(s)" in campaign
    assert (
        "Next target rule: if observed contributors reach the current target, next target = min(current target + max(3, current target), 100); otherwise keep the current target and recruit the shortfall."
        in campaign
    )
    assert "Next sprint target: 7 first-ring contributors" in campaign
    assert "Next growth_campaign command: `cyberhuatuo launch-campaign --username alice --framework langchain --release-tag v0.2.0 --target-contributors 7`" in campaign
    assert "No-network proof pack command: `cyberhuatuo proof-pack --username alice --framework langchain --release-tag v0.2.0 --target-contributors 7`" in campaign
    assert "Proof recording command: `cyberhuatuo traction-proof --username alice --framework langchain --release-tag v0.2.0 --target-contributors 7 --record-snapshot`" in campaign
    assert "Recap copy:" in campaign
    assert "CyberHuaTuo v0.2.0 Soul Ring Launch Campaign recap: 2 / 7 real first-ring contributors observed; shortfall 5." in campaign
    assert "Campaign-specific conversions: missing until record-return / record-session / record-share events exist" in campaign
    assert "Prefilled Growth Flywheel Issue:" in campaign
    assert "soul-ring-growth-flywheel.yml" in campaign
    assert "Prefilled Share Proof Issue:" in campaign
    assert "soul-ring-share-proof.yml" in campaign
    assert "cyberhuatuo launch-campaign --username alice --framework langchain --release-tag v0.2.0 --target-contributors 7" in campaign
    assert "cyberhuatuo proof-pack --username alice --framework langchain --release-tag v0.2.0 --target-contributors 7" in campaign
    assert "cyberhuatuo market-copy --username alice --framework langchain --release-tag v0.2.0 --target-contributors 7" in campaign
    assert "cyberhuatuo market-ready --remote --strict-remote --username alice --framework langchain --release-tag v0.2.0 --target-contributors 7" in campaign
    assert "Launch Closure Checklist" in campaign
    assert "cyberhuatuo traction-proof --username alice --framework langchain --release-tag v0.2.0 --target-contributors 7 --record-snapshot" in campaign
    assert "cyberhuatuo record-return --username alice --framework langchain" in campaign
    assert "cyberhuatuo record-session --username alice --framework langchain" in campaign
    assert "cyberhuatuo activation --username alice --framework langchain" in campaign
    assert "cyberhuatuo flywheel --username alice --framework langchain" in campaign
    assert "cyberhuatuo challenge --username alice --framework langchain" in campaign
    assert "cyberhuatuo mission --username alice --framework langchain" in campaign
    assert "cyberhuatuo record-share --username alice --framework langchain --share-url <https-url>" in campaign
    assert "cyberhuatuo share-report --username alice --framework langchain --top-n 10" in campaign
    assert "cyberhuatuo share-leaderboard --framework langchain --top-n 10" in campaign
    _assert_candidate_install_precedes_registry(campaign)
    assert "GitHub Discussion / Release Post" in campaign
    assert "X / Weibo" in campaign
    assert "Agent Prompt" in campaign
    assert "No downloads, retention, repost counts, referrals, rewards, or Spirit Power are invented" in campaign
    assert "1000 users" not in campaign
    assert "simulated" not in campaign.lower()


def test_soul_ring_launch_campaign_sanitizes_target_contributors_without_fake_progress(monkeypatch):
    monkeypatch.setattr(
        achievements,
        "get_cultivation_profile",
        lambda username: {
            "github": username,
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        },
    )
    monkeypatch.setattr(achievements, "count_contributor_cases_by_framework", lambda _username: {})
    monkeypatch.setattr(achievements, "get_global_ranking_stats", lambda: {})

    campaign = achievements.format_soul_ring_launch_campaign("newcomer", "mcp", target_contributors=-5)

    assert "Campaign Target: 3 first-ring contributors" in campaign
    assert "Current real ranked contributors: 0" in campaign
    assert "Observed real contributors: 0 / 3" in campaign
    assert "Campaign shortfall: 3 first-ring contributor(s)" in campaign
    assert "Next sprint target: 3 first-ring contributors" in campaign
    assert "campaign-specific conversions are not inferred from downloads or stars" in campaign
    assert "fake" not in campaign.lower()
    assert "simulated" not in campaign.lower()


def test_soul_ring_traction_proof_compares_public_api_signals_with_local_ledger_without_fake_metrics(
    tmp_path,
    monkeypatch,
):
    ledger_path = tmp_path / "activation-events.jsonl"
    monkeypatch.setenv("CYBERHUATUO_ACTIVATION_LEDGER", str(ledger_path))
    activation.format_record_external_return(
        "alice",
        "langchain",
        "PyPI release",
        "https://pypi.org/project/cyberhuatuo/",
    )
    activation.format_record_share_attribution(
        "carol",
        "langchain",
        "https://example.com/cyberhuatuo-share",
        source_url="https://pypi.org/project/cyberhuatuo/",
    )

    def fake_fetcher(url, _headers=None, _timeout=10):
        release = _fake_ready_release(url)
        if release is not None:
            return release
        issueops_content = _fake_ready_issueops_content(url)
        if issueops_content is not None:
            return issueops_content
        if url == "https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin":
            return {
                "full_name": "JinNing6/CyberHuaTuo-Plugin",
                "html_url": "https://github.com/JinNing6/CyberHuaTuo-Plugin",
                "stargazers_count": 42,
                "forks_count": 5,
                "watchers_count": 42,
                "subscribers_count": 3,
                "open_issues_count": 8,
            }
        if url == "https://pypi.org/pypi/cyberhuatuo/json":
            return {
                "info": {
                    "version": "0.2.0",
                    "project_urls": {"Homepage": "https://github.com/JinNing6/CyberHuaTuo-Plugin"},
                    "downloads": {"last_month": -1},
                },
                "releases": {"0.1.0": [{}], "0.2.0": [{}]},
                "urls": [{"filename": "cyberhuatuo-0.2.0-py3-none-any.whl"}],
            }
        if url == "https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin/pulls?state=all&per_page=100":
            return [
                {"user": {"login": "dave"}, "html_url": "https://github.com/JinNing6/CyberHuaTuo-Plugin/pull/1"},
                {"user": {"login": "alice"}, "html_url": "https://github.com/JinNing6/CyberHuaTuo-Plugin/pull/2"},
                {"user": {"login": ""}, "html_url": "https://github.com/JinNing6/CyberHuaTuo-Plugin/pull/3"},
            ]
        if "labels=soul-ring-share-proof" in url:
            return [
                {"user": {"login": "carol"}},
                {"user": {"login": "ci"}, "pull_request": {"url": "https://api.github.com/pr/1"}},
            ]
        if "labels=accepted-prescription" in url:
            return [{"user": {"login": "alice"}}]
        if "labels=soul-ring" in url:
            return [
                {"user": {"login": "alice"}},
                {"user": {"login": "bob"}},
                {"user": {"login": "bot"}, "pull_request": {"url": "https://api.github.com/pr/2"}},
            ]
        if "labels=soul-ring-launch-campaign" in url:
            return [{"user": {"login": "maintainer"}}]
        raise AssertionError(url)

    proof = traction.format_soul_ring_traction_proof(
        "alice",
        "langchain",
        release_tag="v0.2.0",
        target_contributors=4,
        fetcher=fake_fetcher,
    )

    assert "Soul Ring Traction Proof" in proof
    assert "GitHub Repository API: fetched" in proof
    assert "GitHub Pull Requests API: fetched" in proof
    assert "PyPI JSON API: fetched" in proof
    assert "GitHub Release readiness: ready" in proof
    assert "Release Trigger Readiness" in proof
    assert "Release proof: GitHub Release `v0.2.0` is published and can trigger the PyPI release workflow." in proof
    assert "PyPI version: `0.2.0`" in proof
    assert "PyPI package readiness: ready" in proof
    assert "Remote IssueOps readiness: ready" in proof
    assert "Growth Flywheel Issue Form: ready" in proof
    assert "GitHub Contents API on the repository default branch" in proof
    assert "Public IssueOps proof: soul-ring issues 2, accepted prescriptions 1, share-proof issues 1" in proof
    assert "Public Pull Request proof: PR authors 2, pull requests 3" in proof
    assert "PR authors are contributor identities, but PRs stay separate from IssueOps issue counts" in proof
    assert "Local ledger proof: external returns 1, first sessions 0, share attributions 1" in proof
    assert "Target contributor progress: 4 / 4 real contributor identities" in proof
    assert "@alice, @bob, @carol, @dave" in proof
    assert "Stars/forks/watchers are attention signals, not contributor progress" in proof
    assert "Weakest external proof bridge: first-session proof missing after public attention" in proof
    assert "cyberhuatuo traction-proof --username alice --framework langchain --release-tag v0.2.0 --target-contributors 4" in proof
    assert "cyberhuatuo launch-campaign --username alice --framework langchain --release-tag v0.2.0 --target-contributors 4" in proof
    assert "cyberhuatuo activation --username alice --framework langchain" in proof
    assert "cyberhuatuo flywheel --username alice --framework langchain" in proof
    assert "cyberhuatuo record-return --username alice --framework langchain" in proof
    assert "cyberhuatuo record-share --username alice --framework langchain" in proof
    assert "cyberhuatuo share-leaderboard --framework langchain" in proof
    assert "downloads are not used" in proof
    assert "1000 users" not in proof
    assert "referral conversions are not inferred" in proof
    assert "simulated" not in proof.lower()
    assert "Spirit Power" not in proof


def test_soul_ring_traction_proof_blocks_when_remote_issueops_files_are_missing(
    tmp_path,
    monkeypatch,
):
    ledger_path = tmp_path / "activation-events.jsonl"
    monkeypatch.setenv("CYBERHUATUO_ACTIVATION_LEDGER", str(ledger_path))
    activation.format_record_external_return(
        "alice",
        "langchain",
        "PyPI release",
        "https://pypi.org/project/cyberhuatuo/",
    )
    activation.format_record_first_session(
        "alice",
        "langchain",
        "Claude Desktop MCPB install",
        "https://example.com/claude-session",
    )
    activation.format_record_share_attribution(
        "alice",
        "langchain",
        "https://example.com/share",
        source_url="https://pypi.org/project/cyberhuatuo/",
    )

    missing = {".github/workflows/soul-ring-share-proof.yml"}

    def fake_fetcher(url, _headers=None, _timeout=10):
        release = _fake_ready_release(url, tag=f"v{traction.__version__}")
        if release is not None:
            return release
        issueops_content = _fake_ready_issueops_content(url, missing=missing)
        if issueops_content is not None:
            return issueops_content
        if url == "https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin":
            return {"stargazers_count": 1, "forks_count": 0, "watchers_count": 1, "subscribers_count": 0, "open_issues_count": 1}
        if url == "https://pypi.org/pypi/cyberhuatuo/json":
            return {
                "info": {"version": traction.__version__, "downloads": {"last_month": -1}},
                "releases": {traction.__version__: [{}]},
                "urls": [{"filename": f"cyberhuatuo-{traction.__version__}-py3-none-any.whl"}],
            }
        if url == "https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin/pulls?state=all&per_page=100":
            return []
        if "labels=soul-ring-share-proof" in url:
            return [{"user": {"login": "alice"}}]
        if "labels=accepted-prescription" in url:
            return []
        if "labels=soul-ring" in url:
            return [{"user": {"login": "alice"}}]
        if "labels=soul-ring-launch-campaign" in url:
            return [{"user": {"login": "maintainer"}}]
        raise AssertionError(url)

    proof = traction.format_soul_ring_traction_proof(
        "alice",
        "langchain",
        release_tag=f"v{traction.__version__}",
        target_contributors=1,
        fetcher=fake_fetcher,
    )

    assert "Remote IssueOps readiness: blocked (1 missing/unverified)" in proof
    assert "Share Proof comment workflow: missing or unverified" in proof
    assert ".github/workflows/soul-ring-share-proof.yml" in proof
    assert "Weakest external proof bridge: remote IssueOps readiness blocker" in proof
    assert "issues/new?... links are form entrypoints, not proof URLs" in proof
    assert "Missing remote IssueOps files are public launch blockers" in proof
    assert "simulated" not in proof.lower()


def test_soul_ring_traction_proof_blocks_when_release_tag_is_missing_before_registry_check(
    tmp_path,
    monkeypatch,
):
    ledger_path = tmp_path / "activation-events.jsonl"
    monkeypatch.setenv("CYBERHUATUO_ACTIVATION_LEDGER", str(ledger_path))
    activation.format_record_external_return(
        "alice",
        "langchain",
        "PyPI release",
        "https://pypi.org/project/cyberhuatuo/",
    )

    def fake_fetcher(url, _headers=None, _timeout=10):
        if url == f"{RELEASE_TAG_PREFIX}v{traction.__version__}":
            raise OSError("HTTP 404: Not Found")
        if url.startswith(RELEASE_TAG_PREFIX):
            tag = url.removeprefix(RELEASE_TAG_PREFIX)
            return {
                "tag_name": tag,
                "draft": False,
                "prerelease": False,
                "html_url": f"https://github.com/JinNing6/CyberHuaTuo-Plugin/releases/tag/{tag}",
                "published_at": "2026-06-04T00:00:00Z",
            }
        issueops_content = _fake_ready_issueops_content(url)
        if issueops_content is not None:
            return issueops_content
        if url == "https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin":
            return {"stargazers_count": 1, "forks_count": 0, "watchers_count": 1, "subscribers_count": 0, "open_issues_count": 1}
        if url == "https://pypi.org/pypi/cyberhuatuo/json":
            return {
                "info": {"version": "0.1.0", "downloads": {"last_month": -1}},
                "releases": {"0.1.0": [{}]},
                "urls": [{"filename": "cyberhuatuo-0.1.0-py3-none-any.whl"}],
            }
        if url == "https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin/pulls?state=all&per_page=100":
            return []
        if "labels=soul-ring-share-proof" in url:
            return []
        if "labels=accepted-prescription" in url:
            return []
        if "labels=soul-ring" in url:
            return []
        if "labels=soul-ring-launch-campaign" in url:
            return []
        raise AssertionError(url)

    proof = traction.format_soul_ring_traction_proof(
        "alice",
        "langchain",
        release_tag=f"v{traction.__version__}",
        target_contributors=1,
        fetcher=fake_fetcher,
    )

    assert "GitHub Release readiness: blocked" in proof
    assert f"Release tag: `v{traction.__version__}`" in proof
    assert "release-trigger launch blocker" in proof
    assert "GitHub Releases API" in proof
    assert "Weakest external proof bridge: release trigger or protected manual publish fallback blocker" in proof
    assert "PyPI package readiness: blocked" in proof
    assert ".github/workflows/publish-pypi.yml" in proof
    assert "simulated" not in proof.lower()


def test_soul_ring_traction_proof_blocks_when_pypi_latest_lags_local_growth_tools(
    tmp_path,
    monkeypatch,
):
    ledger_path = tmp_path / "activation-events.jsonl"
    monkeypatch.setenv("CYBERHUATUO_ACTIVATION_LEDGER", str(ledger_path))
    activation.format_record_external_return(
        "alice",
        "langchain",
        "PyPI release",
        "https://pypi.org/project/cyberhuatuo/",
    )
    activation.format_record_first_session(
        "alice",
        "langchain",
        "Codex first install",
        "https://example.com/codex-session",
    )
    activation.format_record_share_attribution(
        "alice",
        "langchain",
        "https://example.com/share",
        source_url="https://pypi.org/project/cyberhuatuo/",
    )

    def fake_fetcher(url, _headers=None, _timeout=10):
        release = _fake_ready_release(url, tag=f"v{traction.__version__}")
        if release is not None:
            return release
        issueops_content = _fake_ready_issueops_content(url)
        if issueops_content is not None:
            return issueops_content
        if url == "https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin":
            return {"stargazers_count": 1, "forks_count": 0, "watchers_count": 1, "subscribers_count": 0, "open_issues_count": 1}
        if url == "https://pypi.org/pypi/cyberhuatuo/json":
            return {
                "info": {"version": "0.1.0", "downloads": {"last_month": -1}},
                "releases": {"0.1.0": [{}]},
                "urls": [{"filename": "cyberhuatuo-0.1.0-py3-none-any.whl"}],
            }
        if url == "https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin/pulls?state=all&per_page=100":
            return []
        if "labels=soul-ring-share-proof" in url:
            return [{"user": {"login": "alice"}}]
        if "labels=accepted-prescription" in url:
            return []
        if "labels=soul-ring" in url:
            return [{"user": {"login": "alice"}}]
        if "labels=soul-ring-launch-campaign" in url:
            return [{"user": {"login": "maintainer"}}]
        raise AssertionError(url)

    proof = traction.format_soul_ring_traction_proof(
        "alice",
        "langchain",
        release_tag=f"v{traction.__version__}",
        target_contributors=1,
        fetcher=fake_fetcher,
    )

    assert "PyPI package readiness: blocked" in proof
    assert "GitHub Release readiness: ready" in proof
    assert "PyPI latest version: `0.1.0`" in proof
    assert f"Local growth-tool version: `{traction.__version__}`" in proof
    assert "install-loop launch blocker" in proof
    assert "Weakest external proof bridge: package registry launch blocker" in proof
    assert ".github/workflows/publish-pypi.yml" in proof
    assert "PyPI Trusted Publishing" in proof
    assert "python -m build --sdist --wheel" in proof
    assert "simulated" not in proof.lower()


def test_soul_ring_traction_proof_fetch_failures_are_recovery_surface_without_fake_success(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("CYBERHUATUO_ACTIVATION_LEDGER", str(tmp_path / "missing-events.jsonl"))

    def failing_fetcher(url, _headers=None, _timeout=10):
        raise OSError(f"blocked: {url}")

    proof = traction.format_soul_ring_traction_proof(
        "newcomer",
        "mcp",
        target_contributors=-9,
        fetcher=failing_fetcher,
    )

    assert "Soul Ring Traction Proof" in proof
    assert "GitHub Repository API: fetch failed" in proof
    assert "GitHub Pull Requests API: fetch failed" in proof
    assert "PyPI JSON API: fetch failed" in proof
    assert "Target contributor progress: 0 / 3 real contributor identities" in proof
    assert "Fetch failures are recovery surfaces, not zero traction claims" in proof
    assert "cyberhuatuo traction-proof --username newcomer --framework mcp --target-contributors 3" in proof
    assert "cyberhuatuo proof-pack --username newcomer --framework mcp" in proof
    assert "cyberhuatuo market-copy --username newcomer --framework mcp" in proof
    assert "cyberhuatuo market-ready --remote --strict-remote --username newcomer --framework mcp" in proof
    assert "Launch Closure Checklist" in proof
    assert "## No-Network First Public Proof Pack" in proof
    assert "Prefilled Growth Flywheel Issue:" in proof
    assert "Created Growth Issue URL: <created Growth Issue URL after submission>" in proof
    assert "Prefilled Share Proof Issue:" in proof
    assert "Created Share Proof Issue URL: <created Share Proof Issue URL after submission>" in proof
    assert "## External Contributor Path" in proof
    assert "First Soul Ring Prescription Issue:" in proof
    assert "Created-issue proof rule:" in proof
    assert "Contributor-counting rule:" in proof
    assert "Copy-ready external contributor invite" in proof
    assert "cyberhuatuo record-return --username newcomer --framework mcp" in proof
    assert "cyberhuatuo launch-campaign --username newcomer --framework mcp" in proof
    assert "1000 users" not in proof
    assert "simulated" not in proof.lower()
    assert "rewards are not invented" in proof


def test_soul_ring_traction_proof_snapshot_history_is_opt_in_append_only_and_delta_based(
    tmp_path,
    monkeypatch,
):
    activation_ledger = tmp_path / "activation-events.jsonl"
    snapshot_ledger = tmp_path / "traction-snapshots.jsonl"
    monkeypatch.setenv("CYBERHUATUO_ACTIVATION_LEDGER", str(activation_ledger))
    monkeypatch.setenv("CYBERHUATUO_TRACTION_SNAPSHOT_LEDGER", str(snapshot_ledger))

    activation.format_record_external_return(
        "alice",
        "langchain",
        "PyPI release",
        "https://pypi.org/project/cyberhuatuo/",
    )

    metrics = {
        "stars": 10,
        "forks": 1,
        "watchers": 10,
        "subscribers": 2,
        "open_issues": 3,
        "pypi_releases": {"0.2.0": [{}]},
        "latest_files": [{"filename": "cyberhuatuo-0.2.0-py3-none-any.whl"}],
        "pull_request_authors": [],
        "soul_ring_authors": ["alice"],
        "accepted_authors": [],
        "share_authors": [],
    }

    def fake_fetcher(url, _headers=None, _timeout=10):
        issueops_content = _fake_ready_issueops_content(url)
        if issueops_content is not None:
            return issueops_content
        if url == "https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin":
            return {
                "stargazers_count": metrics["stars"],
                "forks_count": metrics["forks"],
                "watchers_count": metrics["watchers"],
                "subscribers_count": metrics["subscribers"],
                "open_issues_count": metrics["open_issues"],
            }
        if url == "https://pypi.org/pypi/cyberhuatuo/json":
            return {
                "info": {"version": "0.2.0", "downloads": {"last_month": -1}},
                "releases": metrics["pypi_releases"],
                "urls": metrics["latest_files"],
            }
        if url == "https://api.github.com/repos/JinNing6/CyberHuaTuo-Plugin/pulls?state=all&per_page=100":
            return [{"user": {"login": actor}} for actor in metrics["pull_request_authors"]]
        if "labels=soul-ring-share-proof" in url:
            return [{"user": {"login": actor}} for actor in metrics["share_authors"]]
        if "labels=accepted-prescription" in url:
            return [{"user": {"login": actor}} for actor in metrics["accepted_authors"]]
        if "labels=soul-ring" in url:
            return [{"user": {"login": actor}} for actor in metrics["soul_ring_authors"]]
        if "labels=soul-ring-launch-campaign" in url:
            return [{"user": {"login": "maintainer"}}]
        raise AssertionError(url)

    dry_report = traction.format_soul_ring_traction_proof(
        "alice",
        "langchain",
        release_tag="v0.2.0",
        target_contributors=4,
        fetcher=fake_fetcher,
    )

    assert "Snapshot History: not recorded" in dry_report
    assert "Use `--record-snapshot` to append a reviewable real snapshot" in dry_report
    assert not snapshot_ledger.exists()

    first_report = traction.format_soul_ring_traction_proof(
        "alice",
        "langchain",
        release_tag="v0.2.0",
        target_contributors=4,
        record_snapshot=True,
        snapshot_note="PyPI launch baseline",
        fetcher=fake_fetcher,
    )

    assert "Snapshot History" in first_report
    assert f"Snapshot ledger: `{snapshot_ledger}`" in first_report
    assert "Snapshot recorded: yes" in first_report
    assert "Previous snapshot: none yet" in first_report
    assert "Velocity deltas require at least two recorded real snapshots" in first_report
    assert snapshot_ledger.is_file()
    first_lines = snapshot_ledger.read_text(encoding="utf-8").splitlines()
    assert len(first_lines) == 1
    first_event = json.loads(first_lines[0])
    assert first_event["schema_version"] == 1
    assert first_event["snapshot_type"] == "soul_ring_traction"
    assert first_event["append_only_notice"] == "append-only reviewable real snapshot"
    assert first_event["username"] == "alice"
    assert first_event["framework"] == "langchain"
    assert first_event["repo_metrics"]["stars"] == 10
    assert first_event["pull_request_metrics"]["authors"] == 0
    assert first_event["pull_request_metrics"]["pull_requests"] == 0
    assert first_event["ledger_counts"]["external_return"] == 1
    assert first_event["target_progress"]["contributors"] == 1
    assert first_event["note"] == "PyPI launch baseline"
    assert first_event["non_fabrication"] == "downloads, retention, repost counts, referrals, rewards, and private analytics are not recorded"

    activation.format_record_first_session(
        "bob",
        "langchain",
        "Claude Desktop MCPB install",
        "https://example.com/claude-first-session",
    )
    activation.format_record_share_attribution(
        "carol",
        "langchain",
        "https://example.com/cyberhuatuo-share",
        source_url="https://pypi.org/project/cyberhuatuo/",
    )
    metrics.update({
        "stars": 15,
        "forks": 2,
        "watchers": 15,
        "subscribers": 4,
        "open_issues": 5,
        "pypi_releases": {"0.2.0": [{}], "0.2.1": [{}]},
        "latest_files": [
            {"filename": "cyberhuatuo-0.2.1-py3-none-any.whl"},
            {"filename": "cyberhuatuo-0.2.1.tar.gz"},
        ],
        "pull_request_authors": ["dave"],
        "soul_ring_authors": ["alice", "bob"],
        "accepted_authors": ["alice"],
        "share_authors": ["carol"],
    })

    second_report = traction.format_soul_ring_traction_proof(
        "alice",
        "langchain",
        release_tag="v0.2.1",
        target_contributors=4,
        record_snapshot=True,
        snapshot_note="Post Claude/Codex launch proof",
        fetcher=fake_fetcher,
    )

    assert "Snapshot recorded: yes" in second_report
    assert "Compared against previous real snapshot" in second_report
    assert "stars +5" in second_report
    assert "forks +1" in second_report
    assert "subscribers +2" in second_report
    assert "open issues +2" in second_report
    assert "pull request authors +1" in second_report
    assert "soul-ring issues +1" in second_report
    assert "accepted prescriptions +1" in second_report
    assert "share-proof issues +1" in second_report
    assert "external returns +0" in second_report
    assert "first sessions +1" in second_report
    assert "share attributions +1" in second_report
    assert "target contributors +3" in second_report
    assert "deltas are from append-only real snapshots" in second_report
    assert "downloads are not used" in second_report
    assert "simulated" not in second_report.lower()

    lines = snapshot_ledger.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    second_event = json.loads(lines[1])
    assert second_event["pull_request_metrics"]["authors"] == 1
    assert second_event["target_progress"]["contributors"] == 4
    assert second_event["previous_snapshot_id"] == first_event["snapshot_id"]
    assert second_event["note"] == "Post Claude/Codex launch proof"


def test_traction_snapshot_reader_accepts_utf8_bom_without_losing_velocity_baseline(tmp_path):
    snapshot_ledger = tmp_path / "traction-snapshots.jsonl"
    snapshot = {
        "schema_version": 1,
        "snapshot_id": "bom-baseline",
        "snapshot_type": "soul_ring_traction",
        "timestamp_utc": "2026-06-05T00:00:00Z",
        "username": "alice",
        "framework": "langchain",
        "release": "v0.2.0",
        "repo": "JinNing6/CyberHuaTuo-Plugin",
        "pypi_project": "cyberhuatuo",
        "repo_metrics": {"stars": 1},
        "pypi_metrics": {"release_count": 1},
        "pull_request_metrics": {"authors": 0},
        "issue_counts": {"soul-ring": 1},
        "ledger_counts": {"external_return": 1},
        "target_progress": {"contributors": 1, "target": 3, "actors": ["alice"]},
    }
    snapshot_ledger.write_text(json.dumps(snapshot, sort_keys=True) + "\n", encoding="utf-8-sig")

    snapshots, warnings = traction.load_traction_snapshots(
        username="alice",
        framework="langchain",
        repo="JinNing6/CyberHuaTuo-Plugin",
        pypi_project="cyberhuatuo",
        path=snapshot_ledger,
    )

    assert [item["snapshot_id"] for item in snapshots] == ["bom-baseline"]
    assert "line 1 is not valid JSON" not in "\n".join(warnings)


def test_soul_ring_growth_flywheel_snapshot_finds_collaboration_bottleneck(monkeypatch):
    profiles = {
        "alice": {
            "github": "alice",
            "contribution_count": 2,
            "title_emoji": "*",
            "title_cn": "Apprentice",
            "title_en": "Apprentice",
            "global_rank": 2,
            "global_total": 3,
            "percentile": 50.0,
            "is_rank_one": False,
        },
        "bob": {
            "github": "bob",
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        },
    }

    monkeypatch.setattr(achievements, "get_cultivation_profile", lambda username: profiles[username])
    monkeypatch.setattr(
        achievements,
        "count_contributor_cases_by_framework",
        lambda username: {"alice": {"langchain": 2}, "bob": {}}.get(username, {}),
    )
    monkeypatch.setattr(
        achievements,
        "get_global_ranking_stats",
        lambda: {"alice": 2, "carol": 3, "dave": 1},
    )

    flywheel = achievements.format_soul_ring_growth_flywheel(
        "alice",
        "langchain",
        "Azure Sect",
        ["alice", "bob"],
        top_n=5,
    )

    assert "Soul Ring Growth Flywheel" in flywheel
    assert "Snapshot Formula: current real CyberHuaTuo contribution records" in flywheel
    assert "External Metrics Disclosure" in flywheel
    assert "downloads: missing" in flywheel
    assert "retention: missing" in flywheel
    assert "attribution: missing" in flywheel
    assert "Activation Ledger" in flywheel
    assert "cyberhuatuo record-return --username alice --framework langchain" in flywheel
    assert "cyberhuatuo activation --username alice --framework langchain --sect Azure-Sect --members alice bob --top-n 5" in flywheel
    assert "cyberhuatuo market-ready --remote --strict-remote --username alice --framework langchain" in flywheel
    assert "Launch Closure Checklist" in flywheel
    assert "cyberhuatuo record-share --username alice --framework langchain --share-url <https-url>" in flywheel
    assert "Stage | Current Real Signal | Bottleneck | Next Command" in flywheel
    assert "Marketplace attention -> First Soul Ring" in flywheel
    assert "First-ring activation" in flywheel
    assert "Repeat contribution" in flywheel
    assert "Collaboration / sect" in flywheel
    assert "Public sharing" in flywheel
    assert "Primary Bottleneck: Collaboration / sect" in flywheel
    assert "1 / 2 activated members" in flywheel
    assert "Prefilled Growth Flywheel Issue" in flywheel
    assert "campaign_hook=" in flywheel
    assert "cyberhuatuo flywheel --username alice --framework langchain --sect Azure-Sect --members alice bob --top-n 5" in flywheel
    assert "cyberhuatuo leaderboard --top-n 5" in flywheel
    assert "cyberhuatuo quest alice --framework langchain" in flywheel
    assert "cyberhuatuo season --framework langchain --top-n 5" in flywheel
    assert "cyberhuatuo sect-arena --sect Azure-Sect alice bob --framework langchain" in flywheel
    assert "GitHub Discussion / PR Comment" in flywheel
    assert "X / Weibo" in flywheel
    assert "Agent Prompt" in flywheel
    assert "No downloads, retention, or attribution metrics are invented" in flywheel
    assert "1000 users" not in flywheel
    assert "simulated" not in flywheel.lower()


def test_soul_ring_growth_flywheel_feeds_real_share_proof_ledger_into_public_sharing_stage(tmp_path, monkeypatch):
    ledger_path = tmp_path / "activation-events.jsonl"
    monkeypatch.setenv("CYBERHUATUO_ACTIVATION_LEDGER", str(ledger_path))
    activation.format_record_share_attribution(
        "alice",
        "langchain",
        "https://example.com/alice-share",
        surface="GitHub Discussion",
    )

    monkeypatch.setattr(
        achievements,
        "get_cultivation_profile",
        lambda username: {
            "github": username,
            "contribution_count": 2,
            "title_emoji": "*",
            "title_cn": "Apprentice",
            "title_en": "Apprentice",
            "global_rank": 2,
            "global_total": 3,
            "percentile": 50.0,
            "is_rank_one": False,
        },
    )
    monkeypatch.setattr(achievements, "count_contributor_cases_by_framework", lambda _username: {"langchain": 2})
    monkeypatch.setattr(achievements, "get_global_ranking_stats", lambda: {"alice": 2, "carol": 3})

    flywheel = achievements.format_soul_ring_growth_flywheel(
        "alice",
        "langchain",
        "Azure Sect",
        ["alice"],
        top_n=5,
    )

    assert "Public share proof: 1 reviewable share URL(s); @alice share proof score 1" in flywheel
    assert "cyberhuatuo share-leaderboard --framework langchain --top-n 5" in flywheel
    assert "cyberhuatuo share-report --username alice --framework langchain --top-n 5" in flywheel
    assert "https://example.com/alice-share" in flywheel
    assert "not treated as proven zero propagation" not in flywheel
    assert "No downloads, retention, or attribution metrics are invented" in flywheel


def test_soul_ring_growth_flywheel_prefills_public_issue_form_without_privileged_params(monkeypatch):
    monkeypatch.setattr(
        achievements,
        "get_cultivation_profile",
        lambda username: {
            "github": username,
            "contribution_count": 2,
            "title_emoji": "*",
            "title_cn": "Apprentice",
            "title_en": "Apprentice",
            "global_rank": 2,
            "global_total": 3,
            "percentile": 50.0,
            "is_rank_one": False,
        },
    )
    monkeypatch.setattr(achievements, "count_contributor_cases_by_framework", lambda _username: {"langchain": 2})
    monkeypatch.setattr(achievements, "get_global_ranking_stats", lambda: {"alice": 2, "carol": 3})

    flywheel = achievements.format_soul_ring_growth_flywheel(
        "alice",
        "langchain",
        "Azure Sect",
        ["alice"],
        top_n=5,
    )
    issue_line = next(line for line in flywheel.splitlines() if "Prefilled Growth Flywheel Issue:" in line)
    url = issue_line.split(": ", 1)[1]
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert parsed.path.endswith("/JinNing6/CyberHuaTuo-Plugin/issues/new")
    assert query["template"] == ["soul-ring-growth-flywheel.yml"]
    assert query["title"] == ["[Soul Ring Growth] Repeat contribution for alice"]
    assert query["github_username"] == ["alice"]
    assert query["framework"] == ["langchain"]
    assert query["growth_surface"] == ["Agent community prompt"]
    assert "Primary bottleneck: Repeat contribution" in query["bottleneck_guess"][0]
    assert "campaign hook" in query["campaign_hook"][0].lower()
    assert "current real CyberHuaTuo contribution records" in query["real_signal"][0]
    assert "labels" not in query
    assert "assignees" not in query
    assert "milestone" not in query


def test_soul_ring_growth_flywheel_handles_cold_start_without_fake_metrics(monkeypatch):
    monkeypatch.setattr(
        achievements,
        "get_cultivation_profile",
        lambda username: {
            "github": username,
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        },
    )
    monkeypatch.setattr(achievements, "count_contributor_cases_by_framework", lambda _username: {})
    monkeypatch.setattr(achievements, "get_global_ranking_stats", lambda: {})

    flywheel = achievements.format_soul_ring_growth_flywheel("newcomer", "mcp")

    assert "Soul Ring Growth Flywheel" in flywheel
    assert "Primary Bottleneck: First-ring activation" in flywheel
    assert "0 / 1 first-ring prescriptions" in flywheel
    assert "Global leaderboard: empty current snapshot" in flywheel
    assert "First real prescription unlocks every downstream loop" in flywheel
    assert "issues/new?template=soul-ring-prescription.yml" in flywheel
    assert "cyberhuatuo challenge --username newcomer --framework mcp" in flywheel
    assert "cyberhuatuo flywheel --username newcomer --framework mcp" in flywheel
    assert "cyberhuatuo record-return --username newcomer --framework mcp" in flywheel
    assert "#0" not in flywheel
    assert "fake" not in flywheel.lower()
    assert "simulated" not in flywheel.lower()


def test_soul_ring_breakthrough_ladder_shows_next_real_gate(monkeypatch):
    monkeypatch.setattr(
        achievements,
        "count_contributor_cases_by_framework",
        lambda _username: {"langchain": 3},
    )

    ladder = achievements.format_soul_ring_breakthrough_ladder("alice", "langchain")

    assert "Soul Ring Breakthrough Ladder" in ladder
    assert "GitHub: @alice" in ladder
    assert "Target Framework: LangChain (`langchain`)" in ladder
    assert "Breakthrough Formula: current real prescription count in the target alchemy direction" in ladder
    assert "Current Direction Count: 3 real prescriptions" in ladder
    assert "Next Gate: 4 real prescriptions" in ladder
    assert "Needed: 1 real prescription" in ladder
    assert "| 4 |" in ladder
    assert "NEXT" in ladder
    assert "cyberhuatuo quest alice --framework langchain" in ladder
    assert "cyberhuatuo upload" in ladder
    assert "cyberhuatuo campaign alice --framework langchain" in ladder
    assert "cyberhuatuo mission --username alice --framework langchain" in ladder
    _assert_candidate_install_precedes_registry(ladder)
    assert "MCP: uvx --from cyberhuatuo cyberhuatuo-mcp" in ladder
    assert "not invented" in ladder
    assert "simulated" not in ladder.lower()


def test_soul_ring_evidence_submission_records_public_source_and_updates_ladder(
    tmp_path,
    monkeypatch,
):
    evidence_ledger = tmp_path / "soul-ring-evidence.jsonl"
    monkeypatch.setenv("CYBERHUATUO_EVIDENCE_LEDGER", str(evidence_ledger))
    monkeypatch.setattr(
        achievements,
        "count_contributor_cases_by_framework",
        lambda _username: {"langchain": 3},
    )

    card = achievements.format_soul_ring_evidence_submission(
        "alice",
        "langchain",
        amount=1,
        source_url="https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/42",
        note="accepted public fix awaiting case import",
    )

    assert "Soul Ring Evidence Card" in card
    assert "Evidence recorded: yes" in card
    assert "GitHub: @alice" in card
    assert "Framework: LangChain (`langchain`)" in card
    assert "Reviewable Source URL: https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/42" in card
    assert "Evidence amount: 1" in card
    assert "Evidence total: 1" in card
    assert "Base Direction Count: 3 real prescriptions" in card
    assert "Evidence-backed Count: 4" in card
    assert "Next Gate Before Evidence: 4 real prescriptions" in card
    assert "Breakthrough: triggered by reviewable public evidence" in card
    assert "cyberhuatuo ladder alice --framework langchain" in card
    assert "not invented" in card

    events = [json.loads(line) for line in evidence_ledger.read_text(encoding="utf-8").splitlines()]
    assert len(events) == 1
    assert events[0]["event_type"] == "soul_ring_evidence"
    assert events[0]["username"] == "alice"
    assert events[0]["framework"] == "langchain"
    assert events[0]["amount"] == 1
    assert events[0]["source_url"] == "https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/42"
    assert events[0]["note"] == "accepted public fix awaiting case import"

    ladder = achievements.format_soul_ring_breakthrough_ladder("alice", "langchain")

    assert "Public Evidence Progress: 1 reviewable evidence-backed prescription" in ladder
    assert "Evidence-backed Count: 4" in ladder
    assert "Evidence Submission Command:" in ladder
    assert "cyberhuatuo evidence alice --framework langchain --amount 1 --source-url <reviewable-http-url>" in ladder
    assert "Evidence entries are append-only and reviewable" in ladder


def test_soul_ring_evidence_submission_rejects_non_reviewable_source_without_fake_breakthrough(
    tmp_path,
    monkeypatch,
):
    evidence_ledger = tmp_path / "soul-ring-evidence.jsonl"
    monkeypatch.setenv("CYBERHUATUO_EVIDENCE_LEDGER", str(evidence_ledger))
    monkeypatch.setattr(
        achievements,
        "count_contributor_cases_by_framework",
        lambda _username: {"langchain": 3},
    )

    card = achievements.format_soul_ring_evidence_submission(
        "alice",
        "langchain",
        amount=1,
        source_url="not-a-url",
    )

    assert "Soul Ring Evidence Card" in card
    assert "Evidence recorded: no" in card
    assert "source_url must be a reviewable http(s) URL" in card
    assert "Breakthrough: not triggered" in card
    assert not evidence_ledger.exists()
    assert "fake" not in card.lower()


def test_soul_ring_breakthrough_ladder_handles_new_user_without_fake_progress(monkeypatch):
    monkeypatch.setattr(achievements, "count_contributor_cases_by_framework", lambda _username: {})

    ladder = achievements.format_soul_ring_breakthrough_ladder("newcomer", "mcp")

    assert "Soul Ring Breakthrough Ladder" in ladder
    assert "GitHub: @newcomer" in ladder
    assert "Target Framework: MCP (`mcp`)" in ladder
    assert "Current Direction Count: 0 real prescriptions" in ladder
    assert "Current Ring: not lit yet" in ladder
    assert "Next Gate: 1 real prescription" in ladder
    assert "Needed: 1 real prescription" in ladder
    assert "cyberhuatuo challenge --username newcomer --framework mcp" in ladder
    assert "cyberhuatuo mission --username newcomer --framework mcp" in ladder
    assert "#0" not in ladder
    assert "fake" not in ladder.lower()
    assert "simulated" not in ladder.lower()


def test_profile_badge_kit_generates_copy_ready_markdown_from_real_profile(monkeypatch):
    monkeypatch.setattr(
        achievements,
        "get_cultivation_profile",
        lambda username: {
            "github": username,
            "contribution_count": 3,
            "title_emoji": "⭐",
            "title_cn": "一星炼丹师",
            "title_en": "One-Star Alchemist",
            "global_rank": 2,
            "global_total": 8,
            "percentile": 85.7,
            "is_rank_one": False,
        },
    )
    monkeypatch.setattr(
        achievements,
        "count_contributor_cases_by_framework",
        lambda _username: {"langchain": 3},
    )

    kit = achievements.format_profile_badge_kit("alice")

    assert "GitHub Profile Badge Kit" in kit
    assert "img.shields.io/badge/CyberHuaTuo-One--Star_Alchemist" in kit
    assert "style=for-the-badge" in kit
    assert "labelColor=0A0E1A" in kit
    assert "[![CyberHuaTuo Soul Ring]" in kit
    assert "https://github.com/JinNing6/CyberHuaTuo-Plugin" in kit
    assert "3 prescriptions" in kit
    assert "LangChain" in kit
    assert "下一环" in kit
    assert "cyberhuatuo challenge --username alice" in kit
    assert "模拟" not in kit


def test_profile_badge_kit_handles_no_contributions_without_fake_rank(monkeypatch):
    monkeypatch.setattr(
        achievements,
        "get_cultivation_profile",
        lambda username: {
            "github": username,
            "contribution_count": 0,
            "title_emoji": "🌱",
            "title_cn": "实习药童",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        },
    )
    monkeypatch.setattr(
        achievements,
        "count_contributor_cases_by_framework",
        lambda _username: {},
    )

    kit = achievements.format_profile_badge_kit("newcomer")

    assert "Intern Apprentice" in kit
    assert "0 prescriptions" in kit
    assert "尚未点亮魂环" in kit
    assert "#0" not in kit
    assert "cyberhuatuo challenge --username newcomer" in kit


def test_soul_ring_quest_board_turns_next_ring_into_real_actions(monkeypatch):
    monkeypatch.setattr(
        achievements,
        "get_cultivation_profile",
        lambda username: {
            "github": username,
            "contribution_count": 3,
            "title_emoji": "⭐",
            "title_cn": "一星炼丹师",
            "title_en": "One-Star Alchemist",
            "global_rank": 2,
            "global_total": 8,
            "percentile": 85.7,
            "is_rank_one": False,
        },
    )
    monkeypatch.setattr(
        achievements,
        "count_contributor_cases_by_framework",
        lambda _username: {"langchain": 3},
    )

    board = achievements.format_soul_ring_quest_board("alice", "langchain")

    assert "追环任务板" in board
    assert "@alice" in board
    assert "LangChain" in board
    assert "langchain-ai/langchain" in board
    assert "cyberhuatuo mine search --repo langchain-ai/langchain" in board
    assert "cyberhuatuo upload" in board
    assert "--framework langchain" in board
    assert "cyberhuatuo badge alice" in board
    assert "cyberhuatuo card alice" in board
    assert "下一环" in board
    assert "再贡献 1 方" in board
    assert "模拟" not in board


def test_soul_ring_quest_board_gives_starter_quest_without_fake_progress(monkeypatch):
    monkeypatch.setattr(
        achievements,
        "get_cultivation_profile",
        lambda username: {
            "github": username,
            "contribution_count": 0,
            "title_emoji": "🌱",
            "title_cn": "实习药童",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        },
    )
    monkeypatch.setattr(
        achievements,
        "count_contributor_cases_by_framework",
        lambda _username: {},
    )

    board = achievements.format_soul_ring_quest_board("newcomer")

    assert "追环任务板" in board
    assert "尚未点亮魂环" in board
    assert "第一魂环" in board
    assert "cyberhuatuo challenge --username newcomer --framework langchain" in board
    assert "cyberhuatuo mine search --repo langchain-ai/langchain" in board
    assert "#0" not in board
    assert "模拟" not in board


def test_soul_ring_campaign_pack_generates_multi_channel_share_copy(monkeypatch):
    monkeypatch.setattr(
        achievements,
        "get_cultivation_profile",
        lambda username: {
            "github": username,
            "contribution_count": 3,
            "title_emoji": "*",
            "title_cn": "One-Star Alchemist",
            "title_en": "One-Star Alchemist",
            "global_rank": 2,
            "global_total": 8,
            "percentile": 85.7,
            "is_rank_one": False,
        },
    )
    monkeypatch.setattr(
        achievements,
        "count_contributor_cases_by_framework",
        lambda _username: {"langchain": 3},
    )

    pack = achievements.format_soul_ring_campaign_pack("alice", "langchain")

    assert "Soul Ring Campaign Pack" in pack
    assert "@alice" in pack
    assert "One-Star Alchemist" in pack
    assert "3 prescriptions" in pack
    assert "Global Rank: #2 / 8" in pack
    assert "LangChain" in pack
    assert "GitHub Profile / README" in pack
    assert "X / Weibo" in pack
    assert "GitHub Discussion / PR Comment" in pack
    assert "Agent Prompt" in pack
    discussion = pack.split("## GitHub Discussion / PR Comment", 1)[1].split("## Agent Prompt", 1)[0]
    assert "````markdown" in discussion
    assert "```bash" in discussion
    assert "cyberhuatuo quest alice --framework langchain" in pack
    assert "cyberhuatuo badge alice" in pack
    assert "cyberhuatuo card alice" in pack
    assert "https://github.com/JinNing6/CyberHuaTuo-Plugin" in pack
    _assert_candidate_install_precedes_registry(pack)
    assert "uvx --from cyberhuatuo cyberhuatuo-mcp" in pack
    assert "#CyberHuaTuo" in pack
    assert "simulated" not in pack.lower()


def test_soul_ring_campaign_pack_handles_newcomers_without_fake_rank(monkeypatch):
    monkeypatch.setattr(
        achievements,
        "get_cultivation_profile",
        lambda username: {
            "github": username,
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        },
    )
    monkeypatch.setattr(
        achievements,
        "count_contributor_cases_by_framework",
        lambda _username: {},
    )

    pack = achievements.format_soul_ring_campaign_pack("newcomer")

    assert "Soul Ring Campaign Pack" in pack
    assert "0 prescriptions" in pack
    assert "Global Rank: not ranked yet" in pack
    assert "not lit yet" in pack
    assert "cyberhuatuo challenge --username newcomer --framework langchain" in pack
    assert "#0" not in pack
    assert "simulated" not in pack.lower()


def test_soul_ring_duel_card_invites_rival_with_real_snapshot(monkeypatch):
    profiles = {
        "alice": {
            "github": "alice",
            "contribution_count": 3,
            "title_emoji": "*",
            "title_cn": "One-Star Alchemist",
            "title_en": "One-Star Alchemist",
            "global_rank": 2,
            "global_total": 8,
            "percentile": 85.7,
            "is_rank_one": False,
        },
        "bob": {
            "github": "bob",
            "contribution_count": 1,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 4,
            "global_total": 8,
            "percentile": 42.8,
            "is_rank_one": False,
        },
    }
    framework_counts = {
        "alice": {"langchain": 3},
        "bob": {"langchain": 1},
    }
    monkeypatch.setattr(achievements, "get_cultivation_profile", lambda username: profiles[username])
    monkeypatch.setattr(
        achievements,
        "count_contributor_cases_by_framework",
        lambda username: framework_counts[username],
    )

    card = achievements.format_soul_ring_duel_card("alice", "bob", "langchain")

    assert "Soul Ring Duel Card" in card
    assert "@alice" in card
    assert "@bob" in card
    assert "Duel Snapshot Formula: real prescription count" in card
    assert "Current Lead: @alice by 2 real prescriptions" in card
    assert "Global Rank: #2 / 8" in card
    assert "Global Rank: #4 / 8" in card
    assert "LangChain" in card
    assert "X / Weibo" in card
    assert "GitHub Discussion / PR Comment" in card
    assert "cyberhuatuo quest alice --framework langchain" in card
    assert "cyberhuatuo quest bob --framework langchain" in card
    assert "cyberhuatuo challenge --username bob --framework langchain" in card
    assert "cyberhuatuo campaign alice --framework langchain" in card
    assert "https://github.com/JinNing6/CyberHuaTuo-Plugin" in card
    assert "#0" not in card
    assert "simulated" not in card.lower()


def test_soul_ring_duel_card_handles_two_newcomers_without_fake_rank(monkeypatch):
    profiles = {
        "alice": {
            "github": "alice",
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        },
        "bob": {
            "github": "bob",
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        },
    }
    monkeypatch.setattr(achievements, "get_cultivation_profile", lambda username: profiles[username])
    monkeypatch.setattr(achievements, "count_contributor_cases_by_framework", lambda _username: {})

    card = achievements.format_soul_ring_duel_card("alice", "bob")

    assert "Soul Ring Duel Card" in card
    assert "Open Duel: first real prescription lights the first soul ring" in card
    assert "Global Rank: not ranked yet" in card
    assert "not lit yet" in card
    assert "cyberhuatuo challenge --username alice --framework langchain" in card
    assert "cyberhuatuo challenge --username bob --framework langchain" in card
    assert "#0" not in card
    assert "simulated" not in card.lower()


def test_soul_ring_mentor_pact_turns_senior_into_newcomer_growth_node(monkeypatch):
    profiles = {
        "alice": {
            "github": "alice",
            "contribution_count": 5,
            "title_emoji": "*",
            "title_cn": "Three-Star Alchemist",
            "title_en": "Three-Star Alchemist",
            "global_rank": 1,
            "global_total": 8,
            "percentile": 100.0,
            "is_rank_one": True,
        },
        "bob": {
            "github": "bob",
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 8,
            "percentile": 0.0,
            "is_rank_one": False,
        },
    }
    framework_counts = {
        "alice": {"langchain": 5},
        "bob": {},
    }
    monkeypatch.setattr(achievements, "get_cultivation_profile", lambda username: profiles[username])
    monkeypatch.setattr(
        achievements,
        "count_contributor_cases_by_framework",
        lambda username: framework_counts[username],
    )

    pact = achievements.format_soul_ring_mentor_pact("alice", "bob", "langchain")

    assert "Soul Ring Mentor Pact" in pact
    assert "Mentor: @alice" in pact
    assert "Apprentice: @bob" in pact
    assert "Pact Formula: mentor and apprentice snapshots use current real prescription counts" in pact
    assert "Mentor Power: 5 prescriptions" in pact
    assert "Apprentice Foundation: 0 prescriptions" in pact
    assert "Breakthrough Target: @bob lights first LangChain soul ring with 1 real prescription" in pact
    assert "Mentor Duty: review one real prescription and publish the pact update" in pact
    assert "cyberhuatuo challenge --username bob --framework langchain" in pact
    assert "cyberhuatuo quest bob --framework langchain" in pact
    assert 'cyberhuatuo upload --title "Fix real LangChain issue"' in pact
    assert "cyberhuatuo ladder bob --framework langchain" in pact
    assert "cyberhuatuo duel bob alice --framework langchain" in pact
    assert "cyberhuatuo campaign bob --framework langchain" in pact
    assert "X / Weibo" in pact
    assert "GitHub Discussion / PR Comment" in pact
    assert "not invented" in pact
    assert "fake" not in pact.lower()
    assert "simulated" not in pact.lower()


def test_soul_ring_mentor_pact_handles_two_new_users_without_fake_seniority(monkeypatch):
    profiles = {
        "alice": {
            "github": "alice",
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        },
        "bob": {
            "github": "bob",
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        },
    }
    monkeypatch.setattr(achievements, "get_cultivation_profile", lambda username: profiles[username])
    monkeypatch.setattr(achievements, "count_contributor_cases_by_framework", lambda _username: {})

    pact = achievements.format_soul_ring_mentor_pact("alice", "bob")

    assert "Soul Ring Mentor Pact" in pact
    assert "Open Mentor Pact: first real apprentice prescription lights the pact" in pact
    assert "Mentor Power: 0 prescriptions" in pact
    assert "Apprentice Foundation: 0 prescriptions" in pact
    assert "Global Rank: not ranked yet" in pact
    assert "cyberhuatuo challenge --username bob --framework langchain" in pact
    assert "#0" not in pact
    assert "fake" not in pact.lower()
    assert "simulated" not in pact.lower()


def test_soul_ring_tournament_bracket_seeds_multi_user_event_from_real_counts(monkeypatch):
    profiles = {
        "alice": {
            "github": "alice",
            "contribution_count": 5,
            "title_emoji": "*",
            "title_cn": "Five-Star Alchemist",
            "title_en": "Five-Star Alchemist",
            "global_rank": 1,
            "global_total": 4,
            "percentile": 100.0,
            "is_rank_one": True,
        },
        "bob": {
            "github": "bob",
            "contribution_count": 2,
            "title_emoji": "*",
            "title_cn": "Two-Star Alchemist",
            "title_en": "Two-Star Alchemist",
            "global_rank": 2,
            "global_total": 4,
            "percentile": 75.0,
            "is_rank_one": False,
        },
        "carol": {
            "github": "carol",
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        },
        "dave": {
            "github": "dave",
            "contribution_count": 1,
            "title_emoji": "*",
            "title_cn": "One-Star Alchemist",
            "title_en": "One-Star Alchemist",
            "global_rank": 3,
            "global_total": 4,
            "percentile": 50.0,
            "is_rank_one": False,
        },
    }
    framework_counts = {
        "alice": {"langchain": 5},
        "bob": {"langchain": 2},
        "carol": {},
        "dave": {"langchain": 1},
    }
    monkeypatch.setattr(achievements, "get_cultivation_profile", lambda username: profiles[username])
    monkeypatch.setattr(
        achievements,
        "count_contributor_cases_by_framework",
        lambda username: framework_counts[username],
    )

    bracket = achievements.format_soul_ring_tournament_bracket(
        ["bob", "alice", "carol", "dave"],
        "langchain",
        "Agent Soul Cup",
    )

    assert "Soul Ring Tournament Bracket" in bracket
    assert "Event: Agent Soul Cup" in bracket
    assert "Tournament Formula: seeds use current real CyberHuaTuo prescription counts" in bracket
    assert "Current Champion: @alice with 5 prescriptions" in bracket
    assert "Next Chase: @bob needs 3 real prescriptions to catch @alice" in bracket
    assert "Round 1" in bracket
    assert "#1 @alice vs #4 @carol" in bracket
    assert "#2 @bob vs #3 @dave" in bracket
    assert "Seed #4" in bracket
    assert "Global Rank: not ranked yet" in bracket
    assert "X / Weibo" in bracket
    assert "GitHub Discussion / PR Comment" in bracket
    assert "cyberhuatuo duel alice carol --framework langchain" in bracket
    assert "cyberhuatuo duel bob dave --framework langchain" in bracket
    assert "cyberhuatuo challenge --username carol --framework langchain" in bracket
    assert "cyberhuatuo quest alice --framework langchain" in bracket
    assert "cyberhuatuo campaign bob --framework langchain" in bracket
    assert "not invented" in bracket
    assert "fake" not in bracket.lower()
    assert "simulated" not in bracket.lower()


def test_soul_ring_tournament_bracket_handles_empty_odd_bracket_without_fake_champion(monkeypatch):
    profiles = {
        username: {
            "github": username,
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        }
        for username in ("alice", "bob", "carol")
    }
    monkeypatch.setattr(achievements, "get_cultivation_profile", lambda username: profiles[username])
    monkeypatch.setattr(achievements, "count_contributor_cases_by_framework", lambda _username: {})

    bracket = achievements.format_soul_ring_tournament_bracket(["alice", "bob", "carol"])

    assert "Soul Ring Tournament Bracket" in bracket
    assert "Current Champion: not claimed yet" in bracket
    assert "Open Tournament: first real prescription claims the first bracket seed" in bracket
    assert "Bye: @alice waits for a real challenger" in bracket
    assert "#2 @bob vs #3 @carol" in bracket
    assert "Global Rank: not ranked yet" in bracket
    assert "cyberhuatuo challenge --username alice --framework langchain" in bracket
    assert "#0" not in bracket
    assert "fake" not in bracket.lower()
    assert "simulated" not in bracket.lower()


def test_soul_ring_tournament_settlement_turns_current_results_into_next_round_share(monkeypatch):
    profiles = {
        "alice": {
            "github": "alice",
            "contribution_count": 6,
            "title_emoji": "*",
            "title_cn": "Six-Star Alchemist",
            "title_en": "Six-Star Alchemist",
            "global_rank": 1,
            "global_total": 4,
            "percentile": 100.0,
            "is_rank_one": True,
        },
        "bob": {
            "github": "bob",
            "contribution_count": 4,
            "title_emoji": "*",
            "title_cn": "Four-Star Alchemist",
            "title_en": "Four-Star Alchemist",
            "global_rank": 2,
            "global_total": 4,
            "percentile": 75.0,
            "is_rank_one": False,
        },
        "carol": {
            "github": "carol",
            "contribution_count": 1,
            "title_emoji": "*",
            "title_cn": "One-Star Alchemist",
            "title_en": "One-Star Alchemist",
            "global_rank": 3,
            "global_total": 4,
            "percentile": 50.0,
            "is_rank_one": False,
        },
    }
    framework_counts = {
        "alice": {"langchain": 6},
        "bob": {"langchain": 4},
        "carol": {"langchain": 1},
    }
    monkeypatch.setattr(achievements, "get_cultivation_profile", lambda username: profiles[username])
    monkeypatch.setattr(
        achievements,
        "count_contributor_cases_by_framework",
        lambda username: framework_counts[username],
    )

    settlement = achievements.format_soul_ring_tournament_settlement(
        ["carol", "alice", "bob"],
        "langchain",
        "Agent Soul Cup",
    )

    assert "Soul Ring Tournament Settlement" in settlement
    assert "Event: Agent Soul Cup" in settlement
    assert "Settlement Formula: current real CyberHuaTuo prescription counts" in settlement
    assert "Current Victor: @alice with 6 prescriptions" in settlement
    assert "Runner-Up: @bob with 4 prescriptions" in settlement
    assert "Victory Gap: @alice leads @bob by 2 real prescriptions" in settlement
    assert "Next Round Hook: @bob challenges @alice for the next real prescription swing" in settlement
    assert "X / Weibo" in settlement
    assert "GitHub Discussion / PR Comment" in settlement
    assert "cyberhuatuo tournament carol alice bob --framework langchain --event \"Agent Soul Cup\"" in settlement
    assert "cyberhuatuo duel bob alice --framework langchain" in settlement
    assert "cyberhuatuo quest alice --framework langchain" in settlement
    assert "cyberhuatuo campaign bob --framework langchain" in settlement
    assert "not invented" in settlement
    assert "fake" not in settlement.lower()
    assert "simulated" not in settlement.lower()


def test_soul_ring_tournament_settlement_handles_zero_result_without_fake_winner(monkeypatch):
    profiles = {
        username: {
            "github": username,
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        }
        for username in ("alice", "bob")
    }
    monkeypatch.setattr(achievements, "get_cultivation_profile", lambda username: profiles[username])
    monkeypatch.setattr(achievements, "count_contributor_cases_by_framework", lambda _username: {})

    settlement = achievements.format_soul_ring_tournament_settlement(["alice", "bob"])

    assert "Soul Ring Tournament Settlement" in settlement
    assert "Current Victor: not claimed yet" in settlement
    assert "Settlement Pending: first real prescription claims the settlement" in settlement
    assert "Global Rank: not ranked yet" in settlement
    assert "cyberhuatuo challenge --username alice --framework langchain" in settlement
    assert "cyberhuatuo challenge --username bob --framework langchain" in settlement
    assert "#0" not in settlement
    assert "fake" not in settlement.lower()
    assert "simulated" not in settlement.lower()


def test_soul_ring_arena_snapshot_turns_leaderboard_into_shareable_chase(monkeypatch):
    monkeypatch.setattr(
        achievements,
        "get_global_ranking_stats",
        lambda: {"alice": 5, "bob": 3, "carol": 1},
    )

    arena = achievements.format_soul_ring_arena_snapshot("bob", top_n=3)

    assert "Soul Ring Arena Snapshot" in arena
    assert "Arena Snapshot Formula: real prescription count" in arena
    assert "Top 3" in arena
    assert "#1 @alice" in arena
    assert "5 prescriptions" in arena
    assert "#2 @bob" in arena
    assert "Your Position: #2 / 3" in arena
    assert "Next Rival: @alice" in arena
    assert "cyberhuatuo duel bob alice --framework langchain" in arena
    assert "cyberhuatuo quest bob --framework langchain" in arena
    assert "cyberhuatuo campaign bob --framework langchain" in arena
    assert "GitHub Discussion / PR Comment" in arena
    assert "X / Weibo" in arena
    assert "#0" not in arena
    assert "simulated" not in arena.lower()


def test_soul_ring_arena_snapshot_handles_empty_board_without_fake_rank(monkeypatch):
    monkeypatch.setattr(achievements, "get_global_ranking_stats", lambda: {})

    arena = achievements.format_soul_ring_arena_snapshot("newcomer", top_n=5)

    assert "Soul Ring Arena Snapshot" in arena
    assert "Arena is empty" in arena
    assert "Global Rank: not ranked yet" in arena
    assert "cyberhuatuo challenge --username newcomer --framework langchain" in arena
    assert "#0" not in arena
    assert "simulated" not in arena.lower()


def test_soul_ring_season_board_turns_leaderboard_into_public_event(monkeypatch):
    monkeypatch.setattr(
        achievements,
        "get_global_ranking_stats",
        lambda: {"alice": 5, "bob": 3, "carol": 1},
    )

    board = achievements.format_soul_ring_season_board("langchain", top_n=3)

    assert "Soul Ring Season Board" in board
    assert "Target Framework: LangChain (`langchain`)" in board
    assert "Season Snapshot Formula: current real prescription count" in board
    assert "Top 3" in board
    assert "Champion: @alice" in board
    assert "#1 @alice" in board
    assert "5 prescriptions" in board
    assert "#2 @bob" in board
    assert "Next Chase: @bob challenges @alice" in board
    assert "cyberhuatuo arena alice --top-n 3 --framework langchain" in board
    assert "cyberhuatuo duel bob alice --framework langchain" in board
    assert "cyberhuatuo quest alice --framework langchain" in board
    assert "cyberhuatuo campaign alice --framework langchain" in board
    assert "GitHub Discussion / PR Comment" in board
    assert "X / Weibo" in board
    assert "not invented" in board
    assert "simulated" not in board.lower()


def test_soul_ring_season_board_handles_empty_board_without_fake_champion(monkeypatch):
    monkeypatch.setattr(achievements, "get_global_ranking_stats", lambda: {})

    board = achievements.format_soul_ring_season_board("mcp", top_n=5)

    assert "Soul Ring Season Board" in board
    assert "Target Framework: MCP (`mcp`)" in board
    assert "Season board is empty" in board
    assert "Champion: not claimed yet" in board
    assert "cyberhuatuo challenge --username your-github-username --framework mcp" in board
    assert "cyberhuatuo mission --username your-github-username --framework mcp" in board
    assert "#0" not in board
    assert "fake" not in board.lower()
    assert "simulated" not in board.lower()


def test_soul_ring_sect_card_sums_real_member_power(monkeypatch):
    profiles = {
        "alice": {
            "github": "alice",
            "contribution_count": 3,
            "title_emoji": "*",
            "title_cn": "One-Star Alchemist",
            "title_en": "One-Star Alchemist",
            "global_rank": 2,
            "global_total": 8,
            "percentile": 75.0,
            "is_rank_one": False,
        },
        "bob": {
            "github": "bob",
            "contribution_count": 1,
            "title_emoji": "*",
            "title_cn": "Apprentice",
            "title_en": "Apprentice",
            "global_rank": 4,
            "global_total": 8,
            "percentile": 50.0,
            "is_rank_one": False,
        },
    }

    def fake_framework_counts(username):
        return {"langchain": profiles[username]["contribution_count"]}

    monkeypatch.setattr(achievements, "get_cultivation_profile", lambda username: profiles[username])
    monkeypatch.setattr(achievements, "count_contributor_cases_by_framework", fake_framework_counts)

    card = achievements.format_soul_ring_sect_card("Azure Sect", ["alice", "bob"], "langchain")

    assert "Soul Ring Sect Card" in card
    assert "Sect: Azure Sect" in card
    assert "Sect Power Formula: sum of current real prescription counts" in card
    assert "Sect Power: 4 real prescriptions" in card
    assert "Leading Member: @alice" in card
    assert "@alice" in card
    assert "@bob" in card
    assert "Global Rank: #2 / 8" in card
    assert "Global Rank: #4 / 8" in card
    assert "LangChain" in card
    assert "Recruitment Post" in card
    assert "GitHub Discussion / PR Comment" in card
    assert "cyberhuatuo quest alice --framework langchain" in card
    assert "cyberhuatuo quest bob --framework langchain" in card
    assert "cyberhuatuo campaign alice --framework langchain" in card
    assert "cyberhuatuo arena alice --top-n 10 --framework langchain" in card
    assert "cyberhuatuo duel alice bob --framework langchain" in card
    assert "#0" not in card
    assert "simulated" not in card.lower()


def test_soul_ring_sect_card_handles_unranked_members_without_fake_power(monkeypatch):
    profiles = {
        "alice": {
            "github": "alice",
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        },
        "bob": {
            "github": "bob",
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        },
    }
    monkeypatch.setattr(achievements, "get_cultivation_profile", lambda username: profiles[username])
    monkeypatch.setattr(achievements, "count_contributor_cases_by_framework", lambda _username: {})

    card = achievements.format_soul_ring_sect_card("New Sect", "alice,bob")

    assert "Soul Ring Sect Card" in card
    assert "Sect: New Sect" in card
    assert "Sect Power: 0 real prescriptions" in card
    assert "Sect is unranked: first real prescription lights the sect banner" in card
    assert "Global Rank: not ranked yet" in card
    assert "cyberhuatuo challenge --username alice --framework langchain" in card
    assert "cyberhuatuo challenge --username bob --framework langchain" in card
    assert "#0" not in card
    assert "simulated" not in card.lower()


def test_soul_ring_sect_recruitment_scroll_invites_candidate_with_real_snapshot(monkeypatch):
    profiles = {
        "alice": {
            "github": "alice",
            "contribution_count": 3,
            "title_emoji": "*",
            "title_cn": "One-Star Alchemist",
            "title_en": "One-Star Alchemist",
            "global_rank": 2,
            "global_total": 8,
            "percentile": 75.0,
            "is_rank_one": False,
        },
        "bob": {
            "github": "bob",
            "contribution_count": 1,
            "title_emoji": "*",
            "title_cn": "Apprentice",
            "title_en": "Apprentice",
            "global_rank": 4,
            "global_total": 8,
            "percentile": 50.0,
            "is_rank_one": False,
        },
        "carol": {
            "github": "carol",
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 8,
            "percentile": 0.0,
            "is_rank_one": False,
        },
    }

    def fake_framework_counts(username):
        return {"langchain": profiles[username]["contribution_count"]}

    monkeypatch.setattr(achievements, "get_cultivation_profile", lambda username: profiles[username])
    monkeypatch.setattr(achievements, "count_contributor_cases_by_framework", fake_framework_counts)

    scroll = achievements.format_soul_ring_sect_recruitment_scroll(
        "Azure Sect",
        ["alice", "bob"],
        "carol",
        "langchain",
    )

    assert "Soul Ring Sect Recruitment Scroll" in scroll
    assert "Sect: Azure Sect" in scroll
    assert "Invitee: @carol" in scroll
    assert "Recruitment Formula: current sect power is the sum of current real prescription counts" in scroll
    assert "Current Sect Power: 4 real prescriptions" in scroll
    assert "Candidate Snapshot: @carol has 0 prescriptions" in scroll
    assert "Admission Trial: fix one real LangChain issue" in scroll
    assert "Join Command: cyberhuatuo sect Azure-Sect alice bob carol --framework langchain" in scroll
    assert "cyberhuatuo challenge --username carol --framework langchain" in scroll
    assert "cyberhuatuo quest carol --framework langchain" in scroll
    assert "cyberhuatuo sect-quest Azure-Sect alice bob carol --framework langchain" in scroll
    assert "X / Weibo" in scroll
    assert "GitHub Discussion / PR Comment" in scroll
    assert "not invented" in scroll
    assert "fake" not in scroll.lower()
    assert "simulated" not in scroll.lower()


def test_soul_ring_sect_recruitment_scroll_marks_open_invite_placeholder(monkeypatch):
    profiles = {
        "alice": {
            "github": "alice",
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        }
    }
    monkeypatch.setattr(achievements, "get_cultivation_profile", lambda username: profiles[username])
    monkeypatch.setattr(achievements, "count_contributor_cases_by_framework", lambda _username: {})

    scroll = achievements.format_soul_ring_sect_recruitment_scroll("New Sect", "alice")

    assert "Soul Ring Sect Recruitment Scroll" in scroll
    assert "Invitee: @new-member-github (placeholder)" in scroll
    assert "Replace `new-member-github` with a real GitHub username before posting." in scroll
    assert "Current Sect Power: 0 real prescriptions" in scroll
    assert "cyberhuatuo sect New-Sect alice new-member-github --framework langchain" in scroll
    assert "cyberhuatuo challenge --username new-member-github --framework langchain" in scroll
    assert "fake" not in scroll.lower()
    assert "simulated" not in scroll.lower()


def test_soul_ring_sect_quest_board_assigns_real_team_next_actions(monkeypatch):
    profiles = {
        "alice": {
            "github": "alice",
            "contribution_count": 3,
            "title_emoji": "*",
            "title_cn": "One-Star Alchemist",
            "title_en": "One-Star Alchemist",
            "global_rank": 2,
            "global_total": 8,
            "percentile": 75.0,
            "is_rank_one": False,
        },
        "bob": {
            "github": "bob",
            "contribution_count": 1,
            "title_emoji": "*",
            "title_cn": "Apprentice",
            "title_en": "Apprentice",
            "global_rank": 4,
            "global_total": 8,
            "percentile": 50.0,
            "is_rank_one": False,
        },
    }

    def fake_framework_counts(username):
        return {"langchain": profiles[username]["contribution_count"]}

    monkeypatch.setattr(achievements, "get_cultivation_profile", lambda username: profiles[username])
    monkeypatch.setattr(achievements, "count_contributor_cases_by_framework", fake_framework_counts)

    board = achievements.format_soul_ring_sect_quest_board("Azure Sect", ["alice", "bob"], "langchain")

    assert "Soul Ring Sect Quest Board" in board
    assert "Sect: Azure Sect" in board
    assert "Sect Quest Formula: per-member next actions from current real prescription counts" in board
    assert "Sect Power: 4 real prescriptions" in board
    assert "Target Repo: langchain-ai/langchain" in board
    assert "Priority Member: @bob" in board
    assert "cyberhuatuo mine search --repo langchain-ai/langchain --limit 5" in board
    assert "cyberhuatuo quest alice --framework langchain" in board
    assert "cyberhuatuo quest bob --framework langchain" in board
    assert "--contributor alice" in board
    assert "--contributor bob" in board
    assert "cyberhuatuo campaign alice --framework langchain" in board
    assert "cyberhuatuo campaign bob --framework langchain" in board
    assert "Sect Rally Post" in board
    assert "GitHub Discussion / PR Comment" in board
    assert "#0" not in board
    assert "simulated" not in board.lower()


def test_soul_ring_sect_quest_board_handles_new_sect_without_fake_progress(monkeypatch):
    profiles = {
        "alice": {
            "github": "alice",
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        },
        "bob": {
            "github": "bob",
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        },
    }
    monkeypatch.setattr(achievements, "get_cultivation_profile", lambda username: profiles[username])
    monkeypatch.setattr(achievements, "count_contributor_cases_by_framework", lambda _username: {})

    board = achievements.format_soul_ring_sect_quest_board("New Sect", "alice,bob")

    assert "Soul Ring Sect Quest Board" in board
    assert "Sect: New Sect" in board
    assert "Sect Power: 0 real prescriptions" in board
    assert "Sect Objective: first real prescription lights the sect banner" in board
    assert "Priority Member: @alice" in board
    assert "Global Rank: not ranked yet" in board
    assert "cyberhuatuo challenge --username alice --framework langchain" in board
    assert "cyberhuatuo challenge --username bob --framework langchain" in board
    assert "#0" not in board
    assert "simulated" not in board.lower()


def test_soul_ring_sect_hall_assigns_posts_from_real_member_counts(monkeypatch):
    profiles = {
        "alice": {
            "github": "alice",
            "contribution_count": 5,
            "title_emoji": "*",
            "title_cn": "Two-Star Alchemist",
            "title_en": "Two-Star Alchemist",
            "global_rank": 1,
            "global_total": 8,
            "percentile": 87.5,
            "is_rank_one": True,
        },
        "bob": {
            "github": "bob",
            "contribution_count": 3,
            "title_emoji": "*",
            "title_cn": "One-Star Alchemist",
            "title_en": "One-Star Alchemist",
            "global_rank": 2,
            "global_total": 8,
            "percentile": 75.0,
            "is_rank_one": False,
        },
        "carol": {
            "github": "carol",
            "contribution_count": 1,
            "title_emoji": "*",
            "title_cn": "Apprentice",
            "title_en": "Apprentice",
            "global_rank": 4,
            "global_total": 8,
            "percentile": 50.0,
            "is_rank_one": False,
        },
        "dave": {
            "github": "dave",
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        },
    }

    def fake_framework_counts(username):
        return {"langchain": profiles[username]["contribution_count"]}

    monkeypatch.setattr(achievements, "get_cultivation_profile", lambda username: profiles[username])
    monkeypatch.setattr(achievements, "count_contributor_cases_by_framework", fake_framework_counts)

    hall = achievements.format_soul_ring_sect_hall(
        "Azure Sect",
        ["alice", "bob", "carol", "dave"],
        "langchain",
    )

    assert "Soul Ring Sect Hall" in hall
    assert "Sect: Azure Sect" in hall
    assert "Sect Hall Formula: member posts are assigned from current real prescription counts" in hall
    assert "Sect Hierarchy: Outer Disciple -> Inner Disciple -> Core Disciple -> Hall Deacon -> Sect Elder" in hall
    assert "Sect Power: 9 real prescriptions" in hall
    assert "Senior Member: @alice" in hall
    assert "| @alice | Hall Deacon | 5 real prescriptions | Sect Elder needs 5 real prescriptions |" in hall
    assert "| @bob | Core Disciple | 3 real prescriptions | Hall Deacon needs 2 real prescriptions |" in hall
    assert "| @carol | Inner Disciple | 1 real prescription | Core Disciple needs 2 real prescriptions |" in hall
    assert "| @dave | Outer Disciple | 0 real prescriptions | Inner Disciple needs 1 real prescription |" in hall
    assert "Admission Priority: @dave" in hall
    assert "cyberhuatuo sect-hall Azure-Sect alice bob carol dave --framework langchain" in hall
    assert "cyberhuatuo sect-quest Azure-Sect alice bob carol dave --framework langchain" in hall
    assert "cyberhuatuo challenge --username dave --framework langchain" in hall
    assert "GitHub Discussion / PR Comment" in hall
    assert "X / Weibo" in hall
    assert "#0" not in hall
    assert "simulated" not in hall.lower()
    assert "fake" not in hall.lower()


def test_soul_ring_sect_hall_handles_new_members_without_invented_posts(monkeypatch):
    profiles = {
        "alice": {
            "github": "alice",
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        },
        "bob": {
            "github": "bob",
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        },
    }
    monkeypatch.setattr(achievements, "get_cultivation_profile", lambda username: profiles[username])
    monkeypatch.setattr(achievements, "count_contributor_cases_by_framework", lambda _username: {})

    hall = achievements.format_soul_ring_sect_hall("New Sect", "alice,bob")

    assert "Soul Ring Sect Hall" in hall
    assert "Sect: New Sect" in hall
    assert "Sect Power: 0 real prescriptions" in hall
    assert "Sect Hall is open: first real prescription promotes an Outer Disciple to Inner Disciple" in hall
    assert "| @alice | Outer Disciple | 0 real prescriptions | Inner Disciple needs 1 real prescription |" in hall
    assert "| @bob | Outer Disciple | 0 real prescriptions | Inner Disciple needs 1 real prescription |" in hall
    assert "Global Rank: not ranked yet" in hall
    assert "cyberhuatuo challenge --username alice --framework langchain" in hall
    assert "cyberhuatuo challenge --username bob --framework langchain" in hall
    assert "#0" not in hall
    assert "simulated" not in hall.lower()
    assert "fake" not in hall.lower()


def test_soul_ring_sect_duel_card_compares_two_real_team_snapshots(monkeypatch):
    profiles = {
        "alice": {
            "github": "alice",
            "contribution_count": 3,
            "title_emoji": "*",
            "title_cn": "One-Star Alchemist",
            "title_en": "One-Star Alchemist",
            "global_rank": 2,
            "global_total": 8,
            "percentile": 75.0,
            "is_rank_one": False,
        },
        "bob": {
            "github": "bob",
            "contribution_count": 1,
            "title_emoji": "*",
            "title_cn": "Apprentice",
            "title_en": "Apprentice",
            "global_rank": 4,
            "global_total": 8,
            "percentile": 50.0,
            "is_rank_one": False,
        },
        "carol": {
            "github": "carol",
            "contribution_count": 2,
            "title_emoji": "*",
            "title_cn": "Apprentice",
            "title_en": "Apprentice",
            "global_rank": 3,
            "global_total": 8,
            "percentile": 62.5,
            "is_rank_one": False,
        },
        "dave": {
            "github": "dave",
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        },
    }

    def fake_framework_counts(username):
        return {"langchain": profiles[username]["contribution_count"]}

    monkeypatch.setattr(achievements, "get_cultivation_profile", lambda username: profiles[username])
    monkeypatch.setattr(achievements, "count_contributor_cases_by_framework", fake_framework_counts)

    card = achievements.format_soul_ring_sect_duel_card(
        "Azure Sect",
        ["alice", "bob"],
        "Shadow Sect",
        ["carol", "dave"],
        "langchain",
    )

    assert "Soul Ring Sect Duel Card" in card
    assert "Challenger Sect: Azure Sect" in card
    assert "Rival Sect: Shadow Sect" in card
    assert "Sect Duel Formula: sum of current real prescription counts" in card
    assert "Azure Sect Power: 4 real prescriptions" in card
    assert "Shadow Sect Power: 2 real prescriptions" in card
    assert "Current Lead: Azure Sect by 2 real prescriptions" in card
    assert "@alice" in card
    assert "@bob" in card
    assert "@carol" in card
    assert "@dave" in card
    assert "Global Rank: #2 / 8" in card
    assert "Global Rank: not ranked yet" in card
    assert "cyberhuatuo sect Azure-Sect alice bob --framework langchain" in card
    assert "cyberhuatuo sect-quest Shadow-Sect carol dave --framework langchain" in card
    assert "cyberhuatuo campaign alice --framework langchain" in card
    assert "cyberhuatuo campaign carol --framework langchain" in card
    assert "GitHub Discussion / PR Comment" in card
    assert "X / Weibo" in card
    assert "#0" not in card
    assert "simulated" not in card.lower()


def test_soul_ring_sect_duel_card_handles_two_new_sects_without_fake_wins(monkeypatch):
    profiles = {
        "alice": {
            "github": "alice",
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        },
        "bob": {
            "github": "bob",
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        },
    }
    monkeypatch.setattr(achievements, "get_cultivation_profile", lambda username: profiles[username])
    monkeypatch.setattr(achievements, "count_contributor_cases_by_framework", lambda _username: {})

    card = achievements.format_soul_ring_sect_duel_card("New Sect", "alice", "Fresh Sect", "bob")

    assert "Soul Ring Sect Duel Card" in card
    assert "New Sect Power: 0 real prescriptions" in card
    assert "Fresh Sect Power: 0 real prescriptions" in card
    assert "Open Sect Duel: first real prescription lights a sect banner" in card
    assert "Global Rank: not ranked yet" in card
    assert "cyberhuatuo challenge --username alice --framework langchain" in card
    assert "cyberhuatuo challenge --username bob --framework langchain" in card
    assert "#0" not in card
    assert "simulated" not in card.lower()
    assert "fake" not in card.lower()


def test_soul_ring_sect_arena_snapshot_ranks_multiple_real_sects(monkeypatch):
    profiles = {
        "alice": {
            "github": "alice",
            "contribution_count": 3,
            "title_emoji": "*",
            "title_cn": "One-Star Alchemist",
            "title_en": "One-Star Alchemist",
            "global_rank": 2,
            "global_total": 8,
            "percentile": 75.0,
            "is_rank_one": False,
        },
        "bob": {
            "github": "bob",
            "contribution_count": 1,
            "title_emoji": "*",
            "title_cn": "Apprentice",
            "title_en": "Apprentice",
            "global_rank": 4,
            "global_total": 8,
            "percentile": 50.0,
            "is_rank_one": False,
        },
        "carol": {
            "github": "carol",
            "contribution_count": 2,
            "title_emoji": "*",
            "title_cn": "Apprentice",
            "title_en": "Apprentice",
            "global_rank": 3,
            "global_total": 8,
            "percentile": 62.5,
            "is_rank_one": False,
        },
        "dave": {
            "github": "dave",
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        },
        "erin": {
            "github": "erin",
            "contribution_count": 5,
            "title_emoji": "*",
            "title_cn": "Two-Star Alchemist",
            "title_en": "Two-Star Alchemist",
            "global_rank": 1,
            "global_total": 8,
            "percentile": 87.5,
            "is_rank_one": True,
        },
    }

    def fake_framework_counts(username):
        return {"langchain": profiles[username]["contribution_count"]}

    monkeypatch.setattr(achievements, "get_cultivation_profile", lambda username: profiles[username])
    monkeypatch.setattr(achievements, "count_contributor_cases_by_framework", fake_framework_counts)

    arena = achievements.format_soul_ring_sect_arena_snapshot(
        [
            ("Azure Sect", ["alice", "bob"]),
            ("Shadow Sect", ["carol", "dave"]),
            ("Ember Sect", ["erin"]),
        ],
        "langchain",
    )

    assert "Soul Ring Sect Arena Snapshot" in arena
    assert "Sect Arena Formula: sum of current real prescription counts" in arena
    assert "#1 Ember Sect - 5 real prescriptions" in arena
    assert "#2 Azure Sect - 4 real prescriptions" in arena
    assert "#3 Shadow Sect - 2 real prescriptions" in arena
    assert "Champion Sect: Ember Sect" in arena
    assert "Next Chase: Azure Sect needs 1 real prescription to catch Ember Sect" in arena
    assert "cyberhuatuo sect Ember-Sect erin --framework langchain" in arena
    assert "cyberhuatuo sect-quest Azure-Sect alice bob --framework langchain" in arena
    assert "cyberhuatuo sect-duel Azure-Sect Ember-Sect --challenger-members alice bob --rival-members erin --framework langchain" in arena
    assert "GitHub Discussion / PR Comment" in arena
    assert "X / Weibo" in arena
    assert "#0" not in arena
    assert "simulated" not in arena.lower()
    assert "fake" not in arena.lower()


def test_soul_ring_sect_arena_snapshot_handles_empty_sects_without_invented_rank(monkeypatch):
    profiles = {
        "alice": {
            "github": "alice",
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        },
        "bob": {
            "github": "bob",
            "contribution_count": 0,
            "title_emoji": "*",
            "title_cn": "Intern Apprentice",
            "title_en": "Intern Apprentice",
            "global_rank": 0,
            "global_total": 0,
            "percentile": 0.0,
            "is_rank_one": False,
        },
    }
    monkeypatch.setattr(achievements, "get_cultivation_profile", lambda username: profiles[username])
    monkeypatch.setattr(achievements, "count_contributor_cases_by_framework", lambda _username: {})

    arena = achievements.format_soul_ring_sect_arena_snapshot(
        "New Sect:alice; Fresh Sect:bob",
        "langchain",
    )

    assert "Soul Ring Sect Arena Snapshot" in arena
    assert "#1 New Sect - 0 real prescriptions" in arena
    assert "#2 Fresh Sect - 0 real prescriptions" in arena
    assert "Sect Arena is open: first real prescription claims the first sect banner" in arena
    assert "Global Rank: not ranked yet" in arena
    assert "cyberhuatuo challenge --username alice --framework langchain" in arena
    assert "cyberhuatuo challenge --username bob --framework langchain" in arena
    assert "#0" not in arena
    assert "simulated" not in arena.lower()
    assert "fake" not in arena.lower()


def test_cli_challenge_prints_first_soul_ring_onramp():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "challenge",
            "--username",
            "alice",
            "--framework",
            "langchain",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "第一魂环挑战" in result.stdout
    assert "--framework langchain" in result.stdout
    assert "--contributor alice" in result.stdout
    assert "cyberhuatuo card alice" in result.stdout


def test_cli_badge_prints_profile_badge_kit():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "badge",
            "alice",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "GitHub Profile Badge Kit" in result.stdout
    assert "img.shields.io/badge/CyberHuaTuo" in result.stdout
    assert "cyberhuatuo challenge --username alice" in result.stdout


def test_cli_quest_prints_soul_ring_quest_board():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "quest",
            "alice",
            "--framework",
            "langchain",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "追环任务板" in result.stdout
    assert "cyberhuatuo mine search --repo langchain-ai/langchain" in result.stdout
    assert "cyberhuatuo badge alice" in result.stdout


def test_cli_campaign_prints_soul_ring_campaign_pack():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "campaign",
            "alice",
            "--framework",
            "langchain",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Soul Ring Campaign Pack" in result.stdout
    assert "GitHub Discussion / PR Comment" in result.stdout
    assert "cyberhuatuo quest alice --framework langchain" in result.stdout


def test_cli_duel_prints_soul_ring_duel_card():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "duel",
            "alice",
            "bob",
            "--framework",
            "langchain",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Soul Ring Duel Card" in result.stdout
    assert "cyberhuatuo quest alice --framework langchain" in result.stdout
    assert "cyberhuatuo challenge --username bob --framework langchain" in result.stdout


def test_cli_mentor_prints_soul_ring_mentor_pact():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "mentor",
            "alice",
            "bob",
            "--framework",
            "langchain",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Soul Ring Mentor Pact" in result.stdout
    assert "Mentor: @alice" in result.stdout
    assert "Apprentice: @bob" in result.stdout
    assert "cyberhuatuo challenge --username bob --framework langchain" in result.stdout


def test_cli_tournament_prints_soul_ring_tournament_bracket():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "tournament",
            "alice",
            "bob",
            "carol",
            "--framework",
            "langchain",
            "--event",
            "Agent-Cup",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Soul Ring Tournament Bracket" in result.stdout
    assert "Event: Agent-Cup" in result.stdout
    assert "cyberhuatuo duel" in result.stdout
    assert "cyberhuatuo quest alice --framework langchain" in result.stdout


def test_cli_tournament_settle_prints_soul_ring_tournament_settlement():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "tournament-settle",
            "alice",
            "bob",
            "--framework",
            "langchain",
            "--event",
            "Agent-Cup",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Soul Ring Tournament Settlement" in result.stdout
    assert "Event: Agent-Cup" in result.stdout
    assert "cyberhuatuo tournament alice bob --framework langchain --event Agent-Cup" in result.stdout


def test_cli_arena_prints_soul_ring_arena_snapshot():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "arena",
            "alice",
            "--top-n",
            "3",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Soul Ring Arena Snapshot" in result.stdout
    assert "Arena Snapshot Formula: real prescription count" in result.stdout


def test_cli_season_prints_soul_ring_season_board():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "season",
            "--framework",
            "langchain",
            "--top-n",
            "3",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Soul Ring Season Board" in result.stdout
    assert "Season Snapshot Formula: current real prescription count" in result.stdout


def test_cli_mission_prints_soul_ring_mission_hall():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "mission",
            "--username",
            "alice",
            "--framework",
            "langchain",
            "--sect",
            "Azure-Sect",
            "--members",
            "alice",
            "bob",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Soul Ring Mission Hall" in result.stdout
    assert "GitHub: @alice" in result.stdout
    assert "cyberhuatuo sect-hall Azure-Sect alice bob --framework langchain" in result.stdout


def test_cli_launch_prints_soul_ring_launch_scroll():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "launch",
            "--username",
            "alice",
            "--framework",
            "langchain",
            "--release-tag",
            "v0.2.0",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Soul Ring Launch Scroll" in result.stdout
    assert "PyPI: `cyberhuatuo`" in result.stdout
    assert "Claude Desktop MCPB: `claude-desktop/manifest.json`" in result.stdout
    assert "Codex: `.codex-plugin/plugin.json`" in result.stdout
    assert "cyberhuatuo challenge --username alice --framework langchain" in result.stdout


def test_cli_launch_campaign_prints_soul_ring_launch_campaign():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "launch-campaign",
            "--username",
            "alice",
            "--framework",
            "langchain",
            "--release-tag",
            "v0.2.0",
            "--target-contributors",
            "6",
            "--surface",
            "PyPI release",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Soul Ring Launch Campaign" in result.stdout
    assert "Campaign Target: 6 first-ring contributors" in result.stdout
    assert "Campaign shortfall:" in result.stdout
    assert "Next growth_campaign command:" in result.stdout
    assert "cyberhuatuo launch-campaign --username alice --framework langchain --release-tag v0.2.0 --target-contributors 6" in result.stdout
    assert "cyberhuatuo traction-proof --username alice --framework langchain --release-tag v0.2.0 --target-contributors 6 --record-snapshot" in result.stdout
    assert "cyberhuatuo share-leaderboard --framework langchain --top-n 10" in result.stdout


def test_cli_launch_assets_accepts_release_context_for_exact_default_branch_handoff():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "launch-assets",
            "--username",
            "alice",
            "--framework",
            "langchain",
            "--release-tag",
            "v0.2.0",
            "--target-contributors",
            "6",
            "--repo",
            "JinNing6/CyberHuaTuo-Plugin",
            "--pypi-project",
            "cyberhuatuo",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Local Launch Asset Audit" in result.stdout
    assert "Public Release Operator Runbook" in result.stdout
    assert "Release tag: `v0.2.0`" in result.stdout
    assert "Package version: `0.2.0`" in result.stdout
    assert 'git commit -m "Release CyberHuaTuo v0.2.0 public growth loop"' in result.stdout
    assert "git tag -a v0.2.0 -m \"CyberHuaTuo v0.2.0\"" in result.stdout
    assert (
        "python -m cyberhuatuo launch-assets --username alice --framework langchain "
        "--release-tag v0.2.0 --target-contributors 6 --repo JinNing6/CyberHuaTuo-Plugin "
        "--pypi-project cyberhuatuo"
    ) in result.stdout
    assert (
        "cyberhuatuo market-ready --remote --strict-remote --username alice "
        "--framework langchain --release-tag v0.2.0 --target-contributors 6"
    ) in result.stdout
    assert "<release-tag>" not in result.stdout
    assert "<version>" not in result.stdout


def test_cli_traction_proof_prints_public_recovery_surface_without_fake_success(tmp_path, monkeypatch):
    monkeypatch.setenv("CYBERHUATUO_ACTIVATION_LEDGER", str(tmp_path / "events.jsonl"))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "traction-proof",
            "--username",
            "alice",
            "--framework",
            "langchain",
            "--target-contributors",
            "5",
            "--timeout",
            "1",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Soul Ring Traction Proof" in result.stdout
    assert "Target contributor progress:" in result.stdout
    assert "cyberhuatuo traction-proof --username alice --framework langchain --target-contributors 5" in result.stdout
    assert "cyberhuatuo launch-campaign --username alice --framework langchain" in result.stdout
    assert "downloads are not used" in result.stdout
    assert "simulated" not in result.stdout.lower()


def test_cli_traction_proof_record_snapshot_is_explicit_and_append_only(tmp_path, monkeypatch):
    monkeypatch.setenv("CYBERHUATUO_ACTIVATION_LEDGER", str(tmp_path / "events.jsonl"))
    snapshot_ledger = tmp_path / "traction-snapshots.jsonl"
    monkeypatch.setenv("CYBERHUATUO_TRACTION_SNAPSHOT_LEDGER", str(snapshot_ledger))

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "traction-proof",
            "--username",
            "alice",
            "--framework",
            "langchain",
            "--target-contributors",
            "5",
            "--record-snapshot",
            "--snapshot-note",
            "local release smoke test",
            "--timeout",
            "1",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Snapshot History" in result.stdout
    assert "Snapshot recorded: yes" in result.stdout
    assert f"Snapshot ledger: `{snapshot_ledger}`" in result.stdout
    assert "cyberhuatuo traction-proof --username alice --framework langchain --target-contributors 5 --record-snapshot" in result.stdout
    assert snapshot_ledger.is_file()
    lines = snapshot_ledger.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert event["snapshot_type"] == "soul_ring_traction"
    assert event["note"] == "local release smoke test"
    assert "simulated" not in result.stdout.lower()


def test_marketplace_submission_ledger_requires_reviewable_public_url_and_reports_channel_status(tmp_path, monkeypatch):
    ledger_path = tmp_path / "marketplace-submissions.jsonl"
    monkeypatch.setenv("CYBERHUATUO_MARKETPLACE_SUBMISSION_LEDGER", str(ledger_path))

    invalid = submissions.format_record_marketplace_submission(
        username="alice",
        framework="langchain",
        channel="pypi",
        status="submitted",
        submission_url="not-a-url",
        release_tag="v0.2.0",
    )

    assert "Marketplace submission not recorded" in invalid
    assert not ledger_path.exists()

    pypi = submissions.format_record_marketplace_submission(
        username="alice",
        framework="langchain",
        channel="pypi",
        status="approved",
        submission_url="https://pypi.org/project/cyberhuatuo/",
        release_tag="v0.2.0",
        note="PyPI project page is live",
    )
    claude = submissions.format_record_marketplace_submission(
        username="alice",
        framework="langchain",
        channel="claude-code",
        status="submitted",
        submission_url="https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/claude-market",
        release_tag="v0.2.0",
    )

    assert "Marketplace submission recorded" in pypi
    assert "cyberhuatuo market-status --username alice --framework langchain --release-tag v0.2.0" in pypi
    assert "cyberhuatuo traction-proof --username alice --framework langchain --release-tag v0.2.0 --target-contributors 3 --record-snapshot" in pypi
    assert "Marketplace submission recorded" in claude
    assert ledger_path.is_file()
    events = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]
    assert [event["channel"] for event in events] == ["pypi", "claude-code"]
    assert events[0]["status"] == "approved"
    assert events[0]["submission_url"] == "https://pypi.org/project/cyberhuatuo/"

    status = submissions.format_marketplace_submission_status(
        username="alice",
        framework="langchain",
        release_tag="v0.2.0",
    )

    assert "Marketplace Submission Ledger" in status
    assert f"Ledger: `{ledger_path}`" in status
    assert "Approved or published channels: 1 / 5" in status
    assert "pypi | approved | https://pypi.org/project/cyberhuatuo/" in status
    assert "claude-code | submitted | https://github.com/JinNing6/CyberHuaTuo-Plugin/issues/claude-market" in status
    assert "claude-desktop | missing" in status
    assert "cyberhuatuo record-market --username alice --framework langchain --channel claude-desktop" in status
    assert "cyberhuatuo market-copy --username alice --framework langchain --release-tag v0.2.0" in status
    assert "cyberhuatuo traction-proof --username alice --framework langchain --release-tag v0.2.0 --target-contributors 3" in status
    assert "No downloads, retention, repost counts, referrals, rewards, reviews, or fake contributors are invented" in status


def test_marketplace_submission_ledger_reader_accepts_utf8_bom_without_losing_first_channel(
    tmp_path,
    monkeypatch,
):
    ledger_path = tmp_path / "marketplace-submissions.jsonl"
    monkeypatch.setenv("CYBERHUATUO_MARKETPLACE_SUBMISSION_LEDGER", str(ledger_path))
    event = {
        "schema_version": 1,
        "event_id": "bom-market",
        "timestamp_utc": "2026-06-05T00:00:00Z",
        "username": "alice",
        "framework": "langchain",
        "channel": "pypi",
        "status": "submitted",
        "submission_url": "https://pypi.org/project/cyberhuatuo/",
        "release_tag": "v0.2.0",
        "repo": "JinNing6/CyberHuaTuo-Plugin",
        "pypi_project": "cyberhuatuo",
        "note": "PyPI page submitted",
    }
    ledger_path.write_text(json.dumps(event, sort_keys=True) + "\n", encoding="utf-8-sig")

    status = submissions.format_marketplace_submission_status(
        username="alice",
        framework="langchain",
        release_tag="v0.2.0",
    )

    assert "Marketplace Submission Ledger" in status
    assert "Approved or published channels: 0 / 5" in status
    assert "Event count: 1" in status
    assert "pypi | submitted | https://pypi.org/project/cyberhuatuo/" in status
    assert "line 1 is not valid JSON" not in status


def test_cli_record_market_and_market_status_round_trip(tmp_path):
    env = os.environ.copy()
    ledger_path = tmp_path / "marketplace-submissions.jsonl"
    env["CYBERHUATUO_MARKETPLACE_SUBMISSION_LEDGER"] = str(ledger_path)

    recorded = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "record-market",
            "--username",
            "alice",
            "--framework",
            "langchain",
            "--channel",
            "codex",
            "--status",
            "submitted",
            "--submission-url",
            "https://example.com/codex-submission",
            "--release-tag",
            "v0.2.0",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert recorded.returncode == 0, recorded.stdout + recorded.stderr
    assert "Marketplace submission recorded" in recorded.stdout
    assert ledger_path.is_file()

    status = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "market-status",
            "--username",
            "alice",
            "--framework",
            "langchain",
            "--release-tag",
            "v0.2.0",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert status.returncode == 0, status.stdout + status.stderr
    assert "Marketplace Submission Ledger" in status.stdout
    assert "codex | submitted | https://example.com/codex-submission" in status.stdout
    assert "pypi | missing" in status.stdout
    assert "cyberhuatuo record-market --username alice --framework langchain --channel pypi" in status.stdout


def test_cli_flywheel_prints_soul_ring_growth_flywheel():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "flywheel",
            "--username",
            "alice",
            "--framework",
            "langchain",
            "--sect",
            "Azure-Sect",
            "--members",
            "alice",
            "bob",
            "--top-n",
            "5",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Soul Ring Growth Flywheel" in result.stdout
    assert "Primary Bottleneck" in result.stdout
    assert "cyberhuatuo leaderboard --top-n 5" in result.stdout
    assert "cyberhuatuo sect-arena --sect Azure-Sect alice bob --framework langchain" in result.stdout
    assert "cyberhuatuo activation --username alice --framework langchain" in result.stdout


def test_cli_record_return_and_activation_funnel_use_real_ledger(tmp_path):
    env = os.environ.copy()
    ledger_path = tmp_path / "activation-events.jsonl"
    env["CYBERHUATUO_ACTIVATION_LEDGER"] = str(ledger_path)

    recorded = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "record-return",
            "--username",
            "alice",
            "--framework",
            "langchain",
            "--surface",
            "PyPI release",
            "--source-url",
            "https://example.com/pypi-post",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert recorded.returncode == 0, recorded.stdout + recorded.stderr
    assert "External return recorded" in recorded.stdout
    assert "Next External Contributor Invite" in recorded.stdout
    assert (
        "cyberhuatuo first-invite --username alice --invitee external-contributor-github-username "
        "--framework langchain --release-tag v0.2.0 --target-contributors 3 "
        "--source-url https://example.com/pypi-post"
    ) in recorded.stdout
    assert (
        "cyberhuatuo proof-pack --username alice --framework langchain "
        "--release-tag v0.2.0 --target-contributors 3"
    ) in recorded.stdout
    assert (
        'first_public_proof_pack(github_username="alice", framework="langchain", '
        'release_tag="v0.2.0", target_contributors=3)'
    ) in recorded.stdout
    assert (
        'first_contributor_invite(github_username="alice", '
        'invitee="external-contributor-github-username", framework="langchain", '
        'release_tag="v0.2.0", target_contributors=3, source_url="https://example.com/pypi-post")'
    ) in recorded.stdout
    assert ledger_path.is_file()

    funnel = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "activation",
            "--username",
            "alice",
            "--framework",
            "langchain",
            "--sect",
            "CyberHuaTuo-Sect",
            "--members",
            "alice",
            "--top-n",
            "5",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert funnel.returncode == 0, funnel.stdout + funnel.stderr
    assert "Soul Ring Activation Funnel" in funnel.stdout
    assert "External return | 1" in funnel.stdout
    assert "cyberhuatuo market-ready --remote --strict-remote --username alice --framework langchain" in funnel.stdout
    assert "cyberhuatuo proof-pack --username alice --framework langchain" in funnel.stdout
    assert "Launch Closure Checklist" in funnel.stdout
    assert "Weakest Conversion Stage: First-session exposure" in funnel.stdout


def test_cli_record_share_writes_share_attribution_event(tmp_path):
    env = os.environ.copy()
    ledger_path = tmp_path / "activation-events.jsonl"
    env["CYBERHUATUO_ACTIVATION_LEDGER"] = str(ledger_path)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "record-share",
            "--username",
            "alice",
            "--framework",
            "langchain",
            "--share-url",
            "https://example.com/share",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Share attribution recorded" in result.stdout
    assert "Next External Contributor Invite" in result.stdout
    assert (
        "cyberhuatuo first-invite --username alice --invitee external-contributor-github-username "
        "--framework langchain --release-tag v0.2.0 --target-contributors 3 "
        "--source-url https://example.com/share"
    ) in result.stdout
    assert (
        'first_contributor_invite(github_username="alice", '
        'invitee="external-contributor-github-username", framework="langchain", '
        'release_tag="v0.2.0", target_contributors=3, source_url="https://example.com/share")'
    ) in result.stdout
    event = json.loads(ledger_path.read_text(encoding="utf-8").splitlines()[0])
    assert event["event_type"] == "share_attribution"


def test_cli_share_report_prints_share_attribution_report(tmp_path):
    env = os.environ.copy()
    ledger_path = tmp_path / "activation-events.jsonl"
    env["CYBERHUATUO_ACTIVATION_LEDGER"] = str(ledger_path)

    record_return = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "record-return",
            "--username",
            "alice",
            "--framework",
            "langchain",
            "--surface",
            "PyPI release",
            "--source-url",
            "https://example.com/pypi-post",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )
    assert record_return.returncode == 0, record_return.stdout + record_return.stderr

    record_share = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "record-share",
            "--username",
            "alice",
            "--framework",
            "langchain",
            "--share-url",
            "https://example.com/share",
            "--source-url",
            "https://example.com/pypi-post",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )
    assert record_share.returncode == 0, record_share.stdout + record_share.stderr

    report = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "share-report",
            "--username",
            "alice",
            "--framework",
            "langchain",
            "--top-n",
            "5",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert report.returncode == 0, report.stdout + report.stderr
    assert "Soul Ring Share Attribution Report" in report.stdout
    assert "Share proof events: 1" in report.stdout
    assert "https://example.com/share" in report.stdout
    assert "Source-to-share bridges: 1 / 1" in report.stdout


def test_cli_share_leaderboard_prints_real_ledger_ranking(tmp_path):
    env = os.environ.copy()
    ledger_path = tmp_path / "activation-events.jsonl"
    env["CYBERHUATUO_ACTIVATION_LEDGER"] = str(ledger_path)

    record_share = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "record-share",
            "--username",
            "alice",
            "--framework",
            "langchain",
            "--share-url",
            "https://example.com/share",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )
    assert record_share.returncode == 0, record_share.stdout + record_share.stderr

    leaderboard = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "share-leaderboard",
            "--framework",
            "langchain",
            "--top-n",
            "5",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert leaderboard.returncode == 0, leaderboard.stdout + leaderboard.stderr
    assert "Soul Ring Share Proof Leaderboard" in leaderboard.stdout
    assert "| 1 | @alice | 1 |" in leaderboard.stdout
    assert "cyberhuatuo share-leaderboard --framework langchain --top-n 5" in leaderboard.stdout


def test_cli_ladder_prints_soul_ring_breakthrough_ladder():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "ladder",
            "alice",
            "--framework",
            "langchain",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Soul Ring Breakthrough Ladder" in result.stdout
    assert "GitHub: @alice" in result.stdout
    assert "cyberhuatuo quest alice --framework langchain" in result.stdout


def test_cli_evidence_records_soul_ring_evidence_card(tmp_path):
    evidence_ledger = tmp_path / "soul-ring-evidence.jsonl"
    env = os.environ.copy()
    env["CYBERHUATUO_EVIDENCE_LEDGER"] = str(evidence_ledger)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "evidence",
            "alice",
            "--framework",
            "langchain",
            "--amount",
            "2",
            "--source-url",
            "https://github.com/JinNing6/CyberHuaTuo-Plugin/pull/7",
            "--note",
            "two accepted public fixes awaiting import",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Soul Ring Evidence Card" in result.stdout
    assert "Evidence recorded: yes" in result.stdout
    assert "Evidence amount: 2" in result.stdout
    assert "Reviewable Source URL: https://github.com/JinNing6/CyberHuaTuo-Plugin/pull/7" in result.stdout
    assert evidence_ledger.is_file()


def test_cli_sect_prints_soul_ring_sect_card():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "sect",
            "Azure-Sect",
            "alice",
            "bob",
            "--framework",
            "langchain",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Soul Ring Sect Card" in result.stdout
    assert "Sect: Azure-Sect" in result.stdout
    assert "cyberhuatuo quest alice --framework langchain" in result.stdout


def test_cli_sect_recruit_prints_soul_ring_sect_recruitment_scroll():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "sect-recruit",
            "Azure-Sect",
            "alice",
            "bob",
            "--invitee",
            "carol",
            "--framework",
            "langchain",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Soul Ring Sect Recruitment Scroll" in result.stdout
    assert "Sect: Azure-Sect" in result.stdout
    assert "Invitee: @carol" in result.stdout
    assert "cyberhuatuo sect Azure-Sect alice bob carol --framework langchain" in result.stdout


def test_cli_sect_quest_prints_soul_ring_sect_quest_board():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "sect-quest",
            "Azure-Sect",
            "alice",
            "bob",
            "--framework",
            "langchain",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Soul Ring Sect Quest Board" in result.stdout
    assert "Sect: Azure-Sect" in result.stdout
    assert "cyberhuatuo mine search --repo langchain-ai/langchain --limit 5" in result.stdout


def test_cli_sect_hall_prints_soul_ring_sect_hall():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "sect-hall",
            "Azure-Sect",
            "alice",
            "bob",
            "--framework",
            "langchain",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Soul Ring Sect Hall" in result.stdout
    assert "Sect: Azure-Sect" in result.stdout
    assert "Sect Hierarchy: Outer Disciple -> Inner Disciple -> Core Disciple" in result.stdout


def test_cli_sect_duel_prints_soul_ring_sect_duel_card():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "sect-duel",
            "Azure-Sect",
            "Shadow-Sect",
            "--challenger-members",
            "alice",
            "bob",
            "--rival-members",
            "carol",
            "dave",
            "--framework",
            "langchain",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Soul Ring Sect Duel Card" in result.stdout
    assert "Challenger Sect: Azure-Sect" in result.stdout
    assert "Rival Sect: Shadow-Sect" in result.stdout
    assert "cyberhuatuo sect-quest Azure-Sect alice bob --framework langchain" in result.stdout


def test_cli_sect_arena_prints_soul_ring_sect_arena_snapshot():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "sect-arena",
            "--sect",
            "Azure-Sect",
            "alice",
            "bob",
            "--sect",
            "Shadow-Sect",
            "carol",
            "dave",
            "--framework",
            "langchain",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Soul Ring Sect Arena Snapshot" in result.stdout
    assert "Sect Arena Formula: sum of current real prescription counts" in result.stdout
    assert "Azure-Sect" in result.stdout
    assert "Shadow-Sect" in result.stdout


def test_cli_bounty_prints_soul_ring_bounty_board():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "cyberhuatuo",
            "bounty",
            "--username",
            "alice",
            "--framework",
            "auto",
            "--top-n",
            "5",
            "--release-tag",
            "v0.2.0",
            "--target-contributors",
            "3",
        ],
        cwd=ROOT,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Soul Ring Bounty Board" in result.stdout
    assert "Coverage Gap Formula" in result.stdout
    assert "cyberhuatuo challenge --username alice" in result.stdout
    assert "No downloads, retention, repost counts, referrals, rewards, or fake contributors are invented" in result.stdout


def test_upload_paths_surface_growth_settlement():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")
    cli = (ROOT / "cyberhuatuo" / "cli.py").read_text(encoding="utf-8")

    assert "format_growth_settlement" in mcp_server
    assert "growth_settlement" in mcp_server
    assert "format_growth_settlement" in cli
    assert "growth_settlement" in cli


def test_mcp_exposes_first_soul_ring_challenge_tool():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_first_soul_ring_challenge" in mcp_server
    assert "def first_soul_ring_challenge" in mcp_server
    assert "第一魂环挑战" in mcp_server


def test_mcp_exposes_soul_ring_mission_hall_tool():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_soul_ring_mission_hall" in mcp_server
    assert "def soul_ring_mission_hall" in mcp_server
    assert "Soul Ring Mission Hall" in mcp_server


def test_mcp_exposes_soul_ring_bounty_board_tool():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_soul_ring_bounty_board" in mcp_server
    assert "def soul_ring_bounty_board" in mcp_server
    assert "Soul Ring Bounty Board" in mcp_server
    assert "cyberhuatuo bounty" in mcp_server


def test_mcp_exposes_soul_ring_launch_scroll_tool():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_soul_ring_launch_scroll" in mcp_server
    assert "def soul_ring_launch_scroll" in mcp_server
    assert "Soul Ring Launch Scroll" in mcp_server


def test_mcp_exposes_soul_ring_launch_campaign_tool():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_soul_ring_launch_campaign" in mcp_server
    assert "def soul_ring_launch_campaign" in mcp_server
    assert "Soul Ring Launch Campaign" in mcp_server
    assert "Campaign Recap And Next Sprint" in mcp_server
    assert "traction-proof --record-snapshot" in mcp_server


def test_mcp_exposes_soul_ring_traction_proof_tool():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_soul_ring_traction_proof" in mcp_server
    assert "def soul_ring_traction_proof" in mcp_server
    assert "def record_soul_ring_traction_snapshot" in mcp_server
    assert "GitHub Pull" in mcp_server
    assert "Soul Ring Traction Proof" in mcp_server


def test_mcp_exposes_marketplace_submission_ledger_tools():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_record_marketplace_submission" in mcp_server
    assert "format_marketplace_submission_status" in mcp_server
    assert "def record_marketplace_submission(" in mcp_server
    assert "def marketplace_submission_status(" in mcp_server
    assert "Marketplace Submission Ledger" in mcp_server
    assert "cyberhuatuo record-market" in mcp_server
    assert "cyberhuatuo market-status" in mcp_server


def test_mcp_exposes_soul_ring_growth_flywheel_tool():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_soul_ring_growth_flywheel" in mcp_server
    assert "def soul_ring_growth_flywheel" in mcp_server
    assert "Soul Ring Growth Flywheel" in mcp_server


def test_mcp_exposes_soul_ring_activation_ledger_tools():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_activation_funnel" in mcp_server
    assert "format_share_attribution_report" in mcp_server
    assert "format_record_external_return" in mcp_server
    assert "format_record_share_attribution" in mcp_server
    assert "def soul_ring_activation_funnel" in mcp_server
    assert "def soul_ring_share_attribution_report" in mcp_server
    assert "def record_soul_ring_external_return" in mcp_server
    assert "def record_soul_ring_share_attribution" in mcp_server


def test_mcp_exposes_soul_ring_breakthrough_ladder_tool():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_soul_ring_breakthrough_ladder" in mcp_server
    assert "format_soul_ring_evidence_submission" in mcp_server
    assert "def soul_ring_breakthrough_ladder" in mcp_server
    assert "def record_soul_ring_evidence" in mcp_server
    assert "Soul Ring Breakthrough Ladder" in mcp_server
    assert "Soul Ring Evidence Card" in mcp_server


def test_mcp_exposes_profile_badge_kit_tool():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_profile_badge_kit" in mcp_server
    assert "def profile_badge_kit" in mcp_server
    assert "GitHub Profile Badge Kit" in mcp_server


def test_mcp_exposes_soul_ring_quest_board_tool():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_soul_ring_quest_board" in mcp_server
    assert "def soul_ring_quest_board" in mcp_server
    assert "追环任务板" in mcp_server


def test_mcp_exposes_soul_ring_campaign_pack_tool():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_soul_ring_campaign_pack" in mcp_server
    assert "def soul_ring_campaign_pack" in mcp_server
    assert "Soul Ring Campaign Pack" in mcp_server


def test_mcp_exposes_soul_ring_duel_card_tool():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_soul_ring_duel_card" in mcp_server
    assert "def soul_ring_duel_card" in mcp_server
    assert "Soul Ring Duel Card" in mcp_server


def test_mcp_exposes_soul_ring_mentor_pact_tool():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_soul_ring_mentor_pact" in mcp_server
    assert "def soul_ring_mentor_pact" in mcp_server
    assert "Soul Ring Mentor Pact" in mcp_server


def test_mcp_exposes_soul_ring_tournament_bracket_tool():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_soul_ring_tournament_bracket" in mcp_server
    assert "def soul_ring_tournament_bracket" in mcp_server
    assert "Soul Ring Tournament Bracket" in mcp_server


def test_mcp_exposes_soul_ring_tournament_settlement_tool():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_soul_ring_tournament_settlement" in mcp_server
    assert "def soul_ring_tournament_settlement" in mcp_server
    assert "Soul Ring Tournament Settlement" in mcp_server


def test_mcp_exposes_soul_ring_arena_snapshot_tool():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_soul_ring_arena_snapshot" in mcp_server
    assert "def soul_ring_arena_snapshot" in mcp_server
    assert "Soul Ring Arena Snapshot" in mcp_server


def test_mcp_exposes_soul_ring_season_board_tool():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_soul_ring_season_board" in mcp_server
    assert "def soul_ring_season_board" in mcp_server
    assert "Soul Ring Season Board" in mcp_server


def test_mcp_exposes_soul_ring_sect_card_tool():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_soul_ring_sect_card" in mcp_server
    assert "def soul_ring_sect_card" in mcp_server
    assert "Soul Ring Sect Card" in mcp_server


def test_mcp_exposes_soul_ring_sect_recruitment_scroll_tool():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_soul_ring_sect_recruitment_scroll" in mcp_server
    assert "def soul_ring_sect_recruitment_scroll" in mcp_server
    assert "Soul Ring Sect Recruitment Scroll" in mcp_server


def test_mcp_exposes_soul_ring_sect_quest_board_tool():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_soul_ring_sect_quest_board" in mcp_server
    assert "def soul_ring_sect_quest_board" in mcp_server
    assert "Soul Ring Sect Quest Board" in mcp_server


def test_mcp_exposes_soul_ring_sect_hall_tool():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_soul_ring_sect_hall" in mcp_server
    assert "def soul_ring_sect_hall" in mcp_server
    assert "Soul Ring Sect Hall" in mcp_server


def test_mcp_exposes_soul_ring_sect_duel_card_tool():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_soul_ring_sect_duel_card" in mcp_server
    assert "def soul_ring_sect_duel_card" in mcp_server
    assert "Soul Ring Sect Duel Card" in mcp_server


def test_mcp_exposes_soul_ring_sect_arena_snapshot_tool():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_soul_ring_sect_arena_snapshot" in mcp_server
    assert "def soul_ring_sect_arena_snapshot" in mcp_server
    assert "Soul Ring Sect Arena Snapshot" in mcp_server


def test_mcp_exposes_soul_ring_share_proof_leaderboard_tool():
    mcp_server = (ROOT / "cyberhuatuo" / "mcp_server.py").read_text(encoding="utf-8")

    assert "format_share_proof_leaderboard" in mcp_server
    assert "def soul_ring_share_proof_leaderboard" in mcp_server
    assert "Soul Ring Share Proof Leaderboard" in mcp_server


def test_readmes_keep_first_ring_growth_loop_visible():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_cn = (ROOT / "README_CN.md").read_text(encoding="utf-8")
    readme_mcp = (ROOT / "README_MCP.md").read_text(encoding="utf-8")
    release_launch_assets_command = (
        "cyberhuatuo launch-assets --username your-github-username --framework langchain "
        "--release-tag v0.2.0 --target-contributors 3"
    )

    assert "cyberhuatuo challenge" in readme
    assert "cyberhuatuo mission" in readme
    assert "cyberhuatuo bounty" in readme
    assert "cyberhuatuo launch" in readme
    assert "cyberhuatuo launch-campaign" in readme
    assert "cyberhuatuo traction-proof" in readme
    assert "cyberhuatuo activation" in readme
    assert "cyberhuatuo record-return" in readme
    assert "cyberhuatuo record-share" in readme
    assert "cyberhuatuo share-report" in readme
    assert "cyberhuatuo share-leaderboard" in readme
    assert "cyberhuatuo flywheel" in readme
    assert "cyberhuatuo ladder" in readme
    assert "cyberhuatuo badge" in readme
    assert "cyberhuatuo quest" in readme
    assert "cyberhuatuo campaign" in readme
    assert "cyberhuatuo duel" in readme
    assert "cyberhuatuo mentor" in readme
    assert "cyberhuatuo tournament" in readme
    assert "cyberhuatuo tournament-settle" in readme
    assert "cyberhuatuo arena" in readme
    assert "cyberhuatuo season" in readme
    assert "cyberhuatuo sect" in readme
    assert "cyberhuatuo sect-recruit" in readme
    assert "cyberhuatuo sect-quest" in readme
    assert "cyberhuatuo sect-hall" in readme
    assert "cyberhuatuo sect-duel" in readme
    assert "cyberhuatuo sect-arena" in readme
    assert "cyberhuatuo upload" in readme
    assert "cyberhuatuo ranking" in readme
    assert "cyberhuatuo card" in readme
    assert release_launch_assets_command in readme
    assert "下一环" in readme
    assert "魂环挑战" in readme

    assert "cyberhuatuo challenge" in readme_cn
    assert "cyberhuatuo mission" in readme_cn
    assert "cyberhuatuo bounty" in readme_cn
    assert "cyberhuatuo launch" in readme_cn
    assert "cyberhuatuo launch-campaign" in readme_cn
    assert "cyberhuatuo traction-proof" in readme_cn
    assert "cyberhuatuo activation" in readme_cn
    assert "cyberhuatuo record-return" in readme_cn
    assert "cyberhuatuo record-share" in readme_cn
    assert "cyberhuatuo share-report" in readme_cn
    assert "cyberhuatuo share-leaderboard" in readme_cn
    assert "cyberhuatuo flywheel" in readme_cn
    assert "cyberhuatuo ladder" in readme_cn
    assert "cyberhuatuo badge" in readme_cn
    assert "cyberhuatuo quest" in readme_cn
    assert "cyberhuatuo campaign" in readme_cn
    assert "cyberhuatuo duel" in readme_cn
    assert "cyberhuatuo mentor" in readme_cn
    assert "cyberhuatuo tournament" in readme_cn
    assert "cyberhuatuo tournament-settle" in readme_cn
    assert "cyberhuatuo arena" in readme_cn
    assert "cyberhuatuo season" in readme_cn
    assert "cyberhuatuo sect" in readme_cn
    assert "cyberhuatuo sect-recruit" in readme_cn
    assert "cyberhuatuo sect-quest" in readme_cn
    assert "cyberhuatuo sect-hall" in readme_cn
    assert "cyberhuatuo sect-duel" in readme_cn
    assert "cyberhuatuo sect-arena" in readme_cn
    assert "cyberhuatuo upload" in readme_cn
    assert "cyberhuatuo ranking" in readme_cn
    assert "cyberhuatuo card" in readme_cn
    assert release_launch_assets_command in readme_cn
    assert "下一环" in readme_cn
    assert "魂环挑战" in readme_cn

    assert "cyberhuatuo challenge" in readme_mcp
    assert "soul_ring_mission_hall" in readme_mcp
    assert "soul_ring_bounty_board" in readme_mcp
    assert "cyberhuatuo bounty" in readme_mcp
    assert "soul_ring_launch_scroll" in readme_mcp
    assert "soul_ring_launch_campaign" in readme_mcp
    assert "soul_ring_traction_proof" in readme_mcp
    assert "record_soul_ring_traction_snapshot" in readme_mcp
    assert "soul_ring_activation_funnel" in readme_mcp
    assert "soul_ring_share_attribution_report" in readme_mcp
    assert "soul_ring_share_proof_leaderboard" in readme_mcp
    assert "record_soul_ring_external_return" in readme_mcp
    assert "record_soul_ring_share_attribution" in readme_mcp
    assert "soul_ring_growth_flywheel" in readme_mcp
    assert "soul_ring_breakthrough_ladder" in readme_mcp
    assert "profile_badge_kit" in readme_mcp
    assert "soul_ring_quest_board" in readme_mcp
    assert "soul_ring_campaign_pack" in readme_mcp
    assert "soul_ring_duel_card" in readme_mcp
    assert "soul_ring_mentor_pact" in readme_mcp
    assert "soul_ring_tournament_bracket" in readme_mcp
    assert "soul_ring_tournament_settlement" in readme_mcp
    assert "soul_ring_arena_snapshot" in readme_mcp
    assert "soul_ring_season_board" in readme_mcp
    assert "soul_ring_sect_card" in readme_mcp
    assert "soul_ring_sect_recruitment_scroll" in readme_mcp
    assert "soul_ring_sect_quest_board" in readme_mcp
    assert "soul_ring_sect_hall" in readme_mcp
    assert "soul_ring_sect_duel_card" in readme_mcp
    assert "soul_ring_sect_arena_snapshot" in readme_mcp
    assert "upload_prescription" in readme_mcp
    assert release_launch_assets_command in readme_mcp
    assert "即时追环" in readme_mcp
    assert "下一环" in readme_mcp
    assert "魂环挑战" in readme_mcp
