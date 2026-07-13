"""Plugin entry point for the CyberHuaTuo PreToolUse guard."""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

run_hook = import_module("cyberhuatuo.agent_hook").run_hook


if __name__ == "__main__":
    raise SystemExit(run_hook())
