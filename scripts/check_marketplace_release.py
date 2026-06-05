"""Check CyberHuaTuo marketplace release readiness."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check PyPI, Claude, Codex, and IssueOps marketplace readiness.")
    parser.add_argument("--remote", action="store_true", default=False, help="Check public PyPI/GitHub API readiness.")
    parser.add_argument("--no-remote", action="store_false", dest="remote", help="Skip public API readiness checks.")
    parser.add_argument("--strict-remote", action="store_true", help="Fail when public PyPI/GitHub readiness is blocked.")
    parser.add_argument("--repo", default="JinNing6/CyberHuaTuo-Plugin", help="GitHub repo slug, owner/name.")
    parser.add_argument("--pypi-project", default="cyberhuatuo", help="PyPI project name.")
    parser.add_argument("--username", default="your-github-username", help="GitHub username for traction proof context.")
    parser.add_argument("--framework", default="langchain", help="Framework for traction proof context.")
    parser.add_argument("--release-tag", default="", help="Release tag, e.g. v0.2.0.")
    parser.add_argument("--target-contributors", type=int, default=3, help="Target first-ring contributor count.")
    parser.add_argument("--timeout", type=int, default=10, help="Public API timeout in seconds.")
    return parser


def main(argv: list[str] | None = None) -> int:
    from cyberhuatuo.marketplace import build_marketplace_readiness, format_marketplace_readiness

    parser = _build_parser()
    args = parser.parse_args(argv)
    report = build_marketplace_readiness(
        ROOT,
        remote=args.remote,
        strict_remote=args.strict_remote,
        repo=args.repo,
        pypi_project=args.pypi_project,
        username=args.username,
        framework=args.framework,
        release_tag=args.release_tag,
        target_contributors=args.target_contributors,
        timeout=args.timeout,
    )
    print(format_marketplace_readiness(report))
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
