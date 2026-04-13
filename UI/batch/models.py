from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image, ImageOps

from core.util import build_export_filename
from UI.shared.qt import ALIGN_CENTER, QColor, QPainter, QPixmap, QSize
from UI.shared.utils import pil_to_qimage, px_to_pt


BATCH_CARD_WIDTH = 188


@dataclass
class BatchQueueItem:
    path: str
    file_name: str
    thumbnail: QPixmap
    exif_summary: str
    resolution: str
    file_size: int
    status: str = "pending"
    progress: int = 0
    status_text: str = "准备就绪"
    output_path: Optional[str] = None
    output_resolution: Optional[str] = None
    output_size: Optional[int] = None
    error_message: Optional[str] = None


def make_placeholder_thumbnail(size: QSize, text: str = "Preview") -> QPixmap:
    pixmap = QPixmap(size)
    pixmap.fill(QColor("#f4f4f5"))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(QColor("#8c9198"))
    font = painter.font()
    font.setPointSizeF(px_to_pt(12))
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), int(ALIGN_CENTER), text)
    painter.end()
    return pixmap


def make_thumbnail(path: str | Path, max_size: tuple[int, int] = (148, 112)) -> tuple[QPixmap, str]:
    resolved = str(Path(path).resolve())
    try:
        with Image.open(resolved) as image:
            image = ImageOps.exif_transpose(image)
            resolution = f"{image.width}x{image.height}"
            preview = image.convert("RGB")
            preview.thumbnail(max_size)
            canvas = Image.new("RGB", max_size, "#f4f4f5")
            offset = ((canvas.width - preview.width) // 2, (canvas.height - preview.height) // 2)
            canvas.paste(preview, offset)
            return QPixmap.fromImage(pil_to_qimage(canvas)), resolution
    except Exception:
        return make_placeholder_thumbnail(QSize(*max_size)), "--"


def normalize_aperture(value: object) -> str:
    text = str(value).strip()
    if not text:
        return ""
    if text.upper().startswith("F"):
        return f"f/{text[1:]}"
    if text.lower().startswith("f/"):
        return text
    return text


def normalize_exposure(value: object) -> str:
    text = str(value).strip()
    if not text:
        return ""
    return text if text.endswith("s") else f"{text}s"


def format_exif_summary(exif_data: dict) -> str:
    if not exif_data:
        return ""
    focal_length = str(
        exif_data.get("FocalLength")
        or exif_data.get("FocalLengthIn35mmFormat")
        or ""
    ).strip()
    aperture = normalize_aperture(exif_data.get("FNumber", ""))
    exposure = normalize_exposure(exif_data.get("ExposureTime") or exif_data.get("ShutterSpeed", ""))
    parts = [part for part in [focal_length, aperture, exposure] if part]
    return "  |  ".join(parts)


def compute_common_root(paths: list[str]) -> Optional[Path]:
    if not paths:
        return None
    try:
        parents = [str(Path(path).resolve().parent) for path in paths]
        return Path(os.path.commonpath(parents))
    except (OSError, ValueError):
        return None


def build_batch_output_path(input_path: str, output_root: str, common_root: Optional[Path]) -> Path:
    source = Path(input_path).resolve()
    destination_root = Path(output_root).resolve()
    if common_root is not None:
        try:
            relative_path = source.relative_to(common_root)
        except ValueError:
            relative_path = Path(source.name)
    else:
        relative_path = Path(source.name)
    return destination_root / relative_path


def build_batch_output_filename(
    source: Path,
    template_name: str,
    quality: int,
    extension: str = ".jpg",
) -> str:
    return build_export_filename(source, template_name, quality=quality, extension=extension)
