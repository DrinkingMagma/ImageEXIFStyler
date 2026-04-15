from __future__ import annotations

import os
import sys

from core import PROJECT_ROOT

UI_ROOT = PROJECT_ROOT / "UI"
TEMPLATE_IMAGE_DIR = UI_ROOT / "template_images"
_BRAND_LOGO_CANDIDATES = (
    UI_ROOT / "logo.avg",
    UI_ROOT / "logo.svg",
    UI_ROOT / "logo.ico",
    UI_ROOT / "logo.png",
    UI_ROOT / "logo.jpg",
    UI_ROOT / "logo.jpeg",
)
BRAND_LOGO_PATH = next((path for path in _BRAND_LOGO_CANDIDATES if path.exists()), _BRAND_LOGO_CANDIDATES[0])


def configure_project_root() -> None:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    os.chdir(PROJECT_ROOT)


configure_project_root()
