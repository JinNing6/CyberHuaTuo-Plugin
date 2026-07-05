from pathlib import Path

from cyberhuatuo.indexer import scan_cases

ROOT = Path(__file__).resolve().parents[1]

WINDOWS_CASES = [
    "_nourishing/windows/system-file-repair-001.md",
    "_nourishing/windows/storage-pressure-002.md",
    "_nourishing/windows/battery-sleep-drain-003.md",
    "_nourishing/windows/defender-malware-scan-004.md",
    "_nourishing/windows/power-mode-optimization-005.md",
]


def test_windows_nourishing_cases_are_published_and_packaged():
    for rel_path in WINDOWS_CASES:
        public_case = ROOT / "cases" / rel_path
        packaged_case = ROOT / "cyberhuatuo" / "cases" / rel_path

        assert public_case.is_file(), rel_path
        assert packaged_case.is_file(), rel_path
        assert public_case.read_text(encoding="utf-8") == packaged_case.read_text(encoding="utf-8")


def test_windows_nourishing_cases_are_parseable_by_indexer():
    cases = scan_cases(ROOT / "cases")
    by_id = {case["id"]: case for case in cases}

    expected_ids = {
        "nourishing-windows-system-file-repair-001",
        "nourishing-windows-storage-pressure-002",
        "nourishing-windows-battery-sleep-drain-003",
        "nourishing-windows-defender-malware-scan-004",
        "nourishing-windows-power-mode-optimization-005",
    }

    assert expected_ids <= set(by_id)
    for case_id in expected_ids:
        case = by_id[case_id]
        assert case["metadata"]["framework"] == "_nourishing"
        assert case["metadata"]["environment"]["os"] == "windows"
        assert case["metadata"]["case_type"] == "nourishing"
        assert "windows" in case["metadata"]["tags"]
        assert "Microsoft" in case["content"]
