from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UI_ROOT = PROJECT_ROOT / "UI"
TEMPLATE_IMAGE_DIR = UI_ROOT / "template_images"


def configure_project_root() -> None:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    os.chdir(PROJECT_ROOT)


configure_project_root()
