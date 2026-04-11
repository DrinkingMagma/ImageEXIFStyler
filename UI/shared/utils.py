from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import Image

from UI.shared.paths import configure_project_root

configure_project_root()

from core.util import get_exif, get_template
from UI.shared.qt import QImage, QPoint, QWidget


def format_bytes(size: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f}{unit}" if unit != "B" else f"{int(value)}B"
        value /= 1024
    return f"{size}B"


def format_duration(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    minutes, remaining = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{remaining:02d}"
    return f"{minutes:02d}:{remaining:02d}"


def px_to_pt(pixels: float) -> float:
    return round(pixels * 0.75, 2)


def set_widget_font_size(widget: QWidget, pixel_size: float):
    font = widget.font()
    font.setPointSizeF(px_to_pt(pixel_size))
    widget.setFont(font)


def refresh_widget_style(widget: QWidget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def event_global_pos(event) -> QPoint:
    if hasattr(event, "globalPosition"):
        return event.globalPosition().toPoint()
    return event.globalPos()


def format_path_for_label(path: str | Path) -> tuple[str, str]:
    resolved_path = str(Path(path).resolve())
    display_path = resolved_path.replace("\\", "/")
    return resolved_path, display_path


def get_file_signature(path: str | Path) -> tuple[str, int, int]:
    resolved_path = Path(path).resolve()
    stat = resolved_path.stat()
    return str(resolved_path), stat.st_mtime_ns, stat.st_size


@lru_cache(maxsize=32)
def get_cached_exif(resolved_path: str, modified_ns: int, file_size: int) -> dict:
    del modified_ns, file_size
    return get_exif(resolved_path)


@lru_cache(maxsize=16)
def get_cached_template(template_name: str, modified_ns: int):
    del modified_ns
    return get_template(template_name)


def pil_to_qimage(image: Image.Image) -> QImage:
    rgb_image = image.convert("RGB")
    data = rgb_image.tobytes("raw", "RGB")
    qimage = QImage(
        data,
        rgb_image.width,
        rgb_image.height,
        rgb_image.width * 3,
        QImage.Format_RGB888,
    )
    return qimage.copy()
