from __future__ import annotations

import os
import sys
from pathlib import Path

from core import PROJECT_ROOT

REQUIRED_CONDA_ENV = "ies"
_PROJECT_ROOT = PROJECT_ROOT
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
os.chdir(_PROJECT_ROOT)


def _is_required_conda_env() -> bool:
    if getattr(sys, "frozen", False):
        return True
    expected = REQUIRED_CONDA_ENV.lower()
    conda_env = os.environ.get("CONDA_DEFAULT_ENV", "").lower()
    if conda_env == expected:
        return True
    return Path(sys.prefix).name.lower() == expected


def _ensure_required_conda_env():
    if _is_required_conda_env():
        return
    sys.stderr.write(
        f"当前项目需要先激活 Conda 环境：conda activate {REQUIRED_CONDA_ENV}\n"
        f"当前环境：{os.environ.get('CONDA_DEFAULT_ENV') or Path(sys.prefix).name or 'unknown'}\n"
    )
    raise SystemExit(1)


_ensure_required_conda_env()

import processor  # noqa: F401  # Register processors.
from UI.editor.constants import HEIC_AVAILABLE, PREVIEW_MAX_DIMENSION, SUPPORTED_FILTER, WINDOW_TITLE
from UI.editor.widgets import PreviewLabel, TemplateCardButton
from UI.editor.window import EditorWindow
from UI.editor.workers import ExportWorker, PreviewWorker
from UI.shared.qt import QApplication, QFont, QIcon, QT_BINDING, Qt
from UI.shared.paths import BRAND_LOGO_PATH, configure_project_root
from UI.template_library.widgets import (
    CreateTemplateCard,
    TemplateLibraryCard,
    TemplateThumbnailLabel,
)

configure_project_root()


def main():
    if QT_BINDING == "PyQt5" and hasattr(QApplication, "setAttribute") and hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    app.setApplicationName(WINDOW_TITLE)
    if BRAND_LOGO_PATH.exists():
        app.setWindowIcon(QIcon(str(BRAND_LOGO_PATH)))
    app.setFont(QFont("Microsoft YaHei UI", 10))
    window = EditorWindow()
    window.show()
    return app.exec()


__all__ = [
    "CreateTemplateCard",
    "EditorWindow",
    "ExportWorker",
    "HEIC_AVAILABLE",
    "PREVIEW_MAX_DIMENSION",
    "PreviewLabel",
    "PreviewWorker",
    "SUPPORTED_FILTER",
    "TemplateCardButton",
    "TemplateLibraryCard",
    "TemplateThumbnailLabel",
    "WINDOW_TITLE",
    "main",
]


if __name__ == "__main__":
    sys.exit(main())
