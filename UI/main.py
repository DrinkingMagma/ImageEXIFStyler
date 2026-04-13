from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
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
