from __future__ import annotations

import processor  # noqa: F401  # Register processors.

WINDOW_TITLE = "Photo EXIF Frame Tool"
HEIC_AVAILABLE = getattr(processor, "pillow_heif", None) is not None
SUPPORTED_FILTER = "Images (*.jpg *.jpeg *.png *.heic)" if HEIC_AVAILABLE else "Images (*.jpg *.jpeg *.png)"
PREVIEW_MAX_DIMENSION = 1600
