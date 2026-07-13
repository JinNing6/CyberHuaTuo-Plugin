from pathlib import Path

from cyberhuatuo.indexer import scan_cases

ROOT = Path(__file__).resolve().parents[1]

WINDOWS_CASES = [
    "_nourishing/windows/system-file-repair-001.md",
    "_nourishing/windows/storage-pressure-002.md",
    "_nourishing/windows/battery-sleep-drain-003.md",
    "_nourishing/windows/defender-malware-scan-004.md",
    "_nourishing/windows/power-mode-optimization-005.md",
    "_nourishing/windows/network-diagnosis-006.md",
    "_nourishing/windows/dns-resolution-optimization-007.md",
    "_nourishing/windows/packet-loss-route-jitter-008.md",
    "_nourishing/windows/tcp-adapter-tuning-009.md",
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
        "nourishing-windows-network-diagnosis-006",
        "nourishing-windows-dns-resolution-optimization-007",
        "nourishing-windows-packet-loss-route-jitter-008",
        "nourishing-windows-tcp-adapter-tuning-009",
    }

    assert expected_ids <= set(by_id)
    for case_id in expected_ids:
        case = by_id[case_id]
        assert case["metadata"]["framework"] == "_nourishing"
        assert case["metadata"]["environment"]["os"] == "windows"
        assert case["metadata"]["case_type"] == "nourishing"
        assert "windows" in case["metadata"]["tags"]
        assert "Microsoft" in case["content"]


def test_windows_network_nourishing_cases_cover_diagnostic_keywords():
    cases = scan_cases(ROOT / "cases")
    by_id = {case["id"]: case for case in cases}

    network_cases = {
        "nourishing-windows-network-diagnosis-006": [
            "ping",
            "tracert",
            "pathping",
            "Test-NetConnection",
            "后悔药",
            "Export-Clixml",
        ],
        "nourishing-windows-dns-resolution-optimization-007": [
            "DNS",
            "Resolve-DnsName",
            "ipconfig /flushdns",
            "后悔药",
            "Set-DnsClientServerAddress",
        ],
        "nourishing-windows-packet-loss-route-jitter-008": [
            "丢包",
            "延迟",
            "pathping",
            "tracert",
            "后悔药",
        ],
        "nourishing-windows-tcp-adapter-tuning-009": [
            "netsh",
            "Get-NetAdapterAdvancedProperty",
            "Get-NetAdapterPowerManagement",
            "后悔药",
            "Set-NetAdapterAdvancedProperty",
        ],
    }

    for case_id, keywords in network_cases.items():
        content = by_id[case_id]["content"]
        for keyword in keywords:
            assert keyword in content
