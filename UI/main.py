from __future__ import annotations

import sys
from pathlib import Path


def _resolve_project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


_PROJECT_ROOT = _resolve_project_root()
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from main import (
    CreateTemplateCard,
    EditorWindow,
    ExportWorker,
    HEIC_AVAILABLE,
    PREVIEW_MAX_DIMENSION,
    PreviewLabel,
    PreviewWorker,
    SUPPORTED_FILTER,
    TemplateCardButton,
    TemplateLibraryCard,
    TemplateThumbnailLabel,
    WINDOW_TITLE,
    main,
)

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
