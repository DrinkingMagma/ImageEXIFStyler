from __future__ import annotations

import sys
from pathlib import Path


def _resolve_project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


PROJECT_ROOT = _resolve_project_root()
CONFIG_PATH = PROJECT_ROOT / "config" / "config.ini"
