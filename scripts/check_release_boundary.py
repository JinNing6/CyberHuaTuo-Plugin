"""Verify that public release artifacts do not contain research-only files."""

from __future__ import annotations

import sys
import tarfile
import zipfile
from pathlib import Path


FORBIDDEN_PREFIXES = (
    "data/",
    "paper/",
    "paper_usenix/",
    "reports/",
    "cyberhuatuo/sandbox/",
)

FORBIDDEN_NAMES = {
    "academic_benchmark_report.md",
    "benchmark_report.md",
    "EPIDEMIC_REPORT.md",
    "py_files.txt",
}


def _normalize_archive_name(name: str) -> str:
    name = name.replace("\\", "/").lstrip("./")
    parts = name.split("/")
    if parts and parts[0].startswith("cyberhuatuo-"):
        return "/".join(parts[1:])
    return name


def _iter_archive_names(path: Path) -> list[str]:
    if path.suffix == ".whl" or path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            return archive.namelist()
    if path.suffixes[-2:] == [".tar", ".gz"] or path.suffix == ".tgz":
        with tarfile.open(path, "r:gz") as archive:
            return archive.getnames()
    raise ValueError(f"Unsupported archive type: {path}")


def _find_forbidden(names: list[str]) -> list[str]:
    violations: list[str] = []
    for raw_name in names:
        name = _normalize_archive_name(raw_name)
        filename = Path(name).name
        if filename in FORBIDDEN_NAMES or any(name.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
            violations.append(raw_name)
    return violations


def main() -> int:
    dist_dir = Path("dist")
    archives = sorted(dist_dir.glob("*.whl")) + sorted(dist_dir.glob("*.tar.gz"))
    if not archives:
        print("No release archives found under dist/. Run `python -m build` first.")
        return 1

    failed = False
    for archive in archives:
        violations = _find_forbidden(_iter_archive_names(archive))
        if violations:
            failed = True
            print(f"[FAIL] {archive} contains forbidden release files:")
            for item in violations:
                print(f"  - {item}")
        else:
            print(f"[OK] {archive} has no forbidden research-only files.")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
