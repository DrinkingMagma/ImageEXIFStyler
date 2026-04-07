from __future__ import annotations

import json
import os
import time
import traceback
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

try:
    from PySide6.QtCore import QEvent, QObject, QPoint, QSize, Qt, QThread, Signal
    from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
    from PySide6.QtWidgets import (
        QComboBox,
        QDialog,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSlider,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    from PyQt5.QtCore import QEvent, QObject, QPoint, QSize, Qt, QThread, pyqtSignal as Signal
    from PyQt5.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
    from PyQt5.QtWidgets import (
        QComboBox,
        QDialog,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSlider,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )

from PIL import Image, ImageOps

from core.configs import load_config
from core.logger import init_from_config, logger
from core.util import get_exif, get_template, get_template_path
from processor import ensure_processors_registered
from processor.core import start_process

if hasattr(Qt, "AlignmentFlag"):
    ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
    ALIGN_LEFT = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    ALIGN_RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    ALIGN_TOP = Qt.AlignmentFlag.AlignTop
    KEEP_ASPECT_RATIO = Qt.AspectRatioMode.KeepAspectRatio
    SMOOTH_TRANSFORMATION = Qt.TransformationMode.SmoothTransformation
    POINTING_HAND_CURSOR = Qt.CursorShape.PointingHandCursor
    LEFT_MOUSE_BUTTON = Qt.MouseButton.LeftButton
    TEXT_SELECTABLE_BY_MOUSE = Qt.TextInteractionFlag.TextSelectableByMouse
    HORIZONTAL = Qt.Orientation.Horizontal
    FRAMELESS_WINDOW_HINT = Qt.WindowType.FramelessWindowHint
    DIALOG_WINDOW_TYPE = Qt.WindowType.Dialog
    TRANSLUCENT_BACKGROUND = Qt.WidgetAttribute.WA_TranslucentBackground
else:
    ALIGN_CENTER = Qt.AlignCenter
    ALIGN_LEFT = Qt.AlignLeft | Qt.AlignVCenter
    ALIGN_RIGHT = Qt.AlignRight | Qt.AlignVCenter
    ALIGN_TOP = Qt.AlignTop
    KEEP_ASPECT_RATIO = Qt.KeepAspectRatio
    SMOOTH_TRANSFORMATION = Qt.SmoothTransformation
    POINTING_HAND_CURSOR = Qt.PointingHandCursor
    LEFT_MOUSE_BUTTON = Qt.LeftButton
    TEXT_SELECTABLE_BY_MOUSE = Qt.TextSelectableByMouse
    HORIZONTAL = Qt.Horizontal
    FRAMELESS_WINDOW_HINT = Qt.FramelessWindowHint
    DIALOG_WINDOW_TYPE = Qt.Dialog
    TRANSLUCENT_BACKGROUND = Qt.WA_TranslucentBackground

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


def build_batch_output_filename(source: Path, template_name: str, extension: str = ".jpg") -> str:
    return f"{source.stem}_{template_name}{extension}"


class TemplateRenderService:
    _logging_ready = False

    def __init__(self):
        self.config = load_config()
        ensure_processors_registered()
        if not TemplateRenderService._logging_ready:
            init_from_config(self.config)
            TemplateRenderService._logging_ready = True

    def get_exif_data(self, input_path: str | Path) -> dict:
        resolved_path, modified_ns, file_size = get_file_signature(input_path)
        return deepcopy(get_cached_exif(resolved_path, modified_ns, file_size))

    def get_template(self, template_name: str):
        template_path = get_template_path(template_name)
        return get_cached_template(template_name, template_path.stat().st_mtime_ns)

    def build_context(self, input_path: str, exif_data: Optional[dict] = None) -> dict:
        path = Path(input_path).resolve()
        return {
            "exif": exif_data if exif_data is not None else self.get_exif_data(path),
            "filename": path.stem,
            "file_dir": str(path.parent).replace("\\", "/"),
            "file_path": str(path).replace("\\", "/"),
            "files": [str(path)],
        }

    def render_pipeline(self, input_path: str, template_name: str, exif_data: Optional[dict] = None) -> list[dict]:
        ensure_processors_registered()
        template = self.get_template(template_name)
        rendered = template.render(self.build_context(input_path, exif_data=exif_data))
        return json.loads(rendered)


class BatchProcessWorker(QObject):
    item_progress = Signal(int, int, str)
    item_complete = Signal(int, str, str, int)
    item_skipped = Signal(int, str)
    item_failed = Signal(int, str)
    overall_progress = Signal(int, int, int, str)
    status_message = Signal(str)
    finished = Signal(dict)

    def __init__(
        self,
        input_paths: list[str],
        template_name: str,
        output_root: str,
        quality: int,
        subsampling: int,
        override_existing: bool,
        common_root: Optional[Path],
    ):
        super().__init__()
        self.input_paths = input_paths
        self.template_name = template_name
        self.output_root = output_root
        self.quality = quality
        self.subsampling = subsampling
        self.override_existing = override_existing
        self.common_root = common_root

    def _eta_text(self, started_at: float, processed: int, total: int) -> str:
        if processed <= 0 or processed >= total:
            return "00:00"
        elapsed = time.perf_counter() - started_at
        average = elapsed / processed
        return format_duration(average * (total - processed))

    def run(self):
        total = len(self.input_paths)
        success_count = 0
        skipped_count = 0
        failure_count = 0
        started_at = time.perf_counter()
        service = TemplateRenderService()

        self.status_message.emit(f"状态：批量处理中 | 模板：{self.template_name}")

        for index, input_path in enumerate(self.input_paths):
            current_display_index = index + 1
            output_path = build_batch_output_path(input_path, self.output_root, self.common_root)
            output_path = output_path.with_name(build_batch_output_filename(output_path, self.template_name))
            self.item_progress.emit(index, 6, "准备处理")

            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                if output_path.exists() and not self.override_existing:
                    skipped_count += 1
                    self.item_skipped.emit(index, str(output_path))
                else:
                    exif_data = service.get_exif_data(input_path)
                    self.item_progress.emit(index, 28, "读取 EXIF")
                    pipeline = service.render_pipeline(input_path, self.template_name, exif_data=exif_data)
                    self.item_progress.emit(index, 58, "渲染模板")
                    start_process(
                        pipeline,
                        input_path=input_path,
                        output_path=str(output_path),
                        exif_data=exif_data,
                        save_options={
                            "quality": self.quality,
                            "subsampling": self.subsampling,
                        },
                    )
                    self.item_progress.emit(index, 88, "写入文件")
                    with Image.open(output_path) as rendered_image:
                        resolution = f"{rendered_image.width}x{rendered_image.height}"
                    output_size = output_path.stat().st_size
                    success_count += 1
                    self.item_complete.emit(index, str(output_path), resolution, output_size)
            except Exception as exc:
                logger.error(traceback.format_exc())
                failure_count += 1
                self.item_failed.emit(index, str(exc))

            processed = success_count + skipped_count + failure_count
            next_index = min(processed + 1, total) if processed < total else total
            self.overall_progress.emit(
                processed,
                total,
                max(next_index, current_display_index if processed < total else total),
                self._eta_text(started_at, processed, total),
            )

        self.finished.emit(
            {
                "total": total,
                "success": success_count,
                "skipped": skipped_count,
                "failed": failure_count,
                "elapsed": time.perf_counter() - started_at,
            }
        )


class BatchCardWidget(QFrame):
    clicked = Signal(int)
    remove_requested = Signal(int)

    def __init__(self, index: int, item: BatchQueueItem):
        super().__init__()
        self.index = index
        self.item = item
        self._thumbnail = item.thumbnail
        self.setObjectName("batchCard")
        self.setCursor(POINTING_HAND_CURSOR)
        self.setFixedWidth(BATCH_CARD_WIDTH)
        self.setMinimumHeight(220)
        self.setProperty("cardSelected", False)
        self.setProperty("batchState", item.status)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.addStretch(1)

        self.remove_button = QToolButton()
        self.remove_button.setObjectName("batchRemoveButton")
        self.remove_button.setAutoRaise(False)
        self.remove_button.setCursor(POINTING_HAND_CURSOR)
        self.remove_button.setToolTip("移除图片")
        self.remove_button.setFixedSize(24, 24)
        self.remove_button.setText("×")
        remove_font = self.remove_button.font()
        remove_font.setPointSizeF(px_to_pt(14))
        remove_font.setBold(True)
        self.remove_button.setFont(remove_font)
        self.remove_button.clicked.connect(lambda checked=False: self.remove_requested.emit(self.index))
        top_row.addWidget(self.remove_button, 0, ALIGN_RIGHT)
        root_layout.addLayout(top_row)

        self.preview_frame = QFrame()
        self.preview_frame.setObjectName("batchPreviewFrame")
        preview_layout = QVBoxLayout(self.preview_frame)
        preview_layout.setContentsMargins(8, 8, 8, 8)
        preview_layout.setSpacing(0)

        self.thumbnail_label = QLabel()
        self.thumbnail_label.setObjectName("batchThumbnail")
        self.thumbnail_label.setAlignment(ALIGN_CENTER)
        self.thumbnail_label.setMinimumHeight(110)
        preview_layout.addWidget(self.thumbnail_label, 1)
        root_layout.addWidget(self.preview_frame)

        self.file_name_label = QLabel()
        self.file_name_label.setObjectName("batchFileName")
        self.file_name_label.setWordWrap(True)
        set_widget_font_size(self.file_name_label, 11)
        root_layout.addWidget(self.file_name_label)

        self.meta_label = QLabel()
        self.meta_label.setObjectName("batchMeta")
        self.meta_label.setWordWrap(True)
        set_widget_font_size(self.meta_label, 10)
        root_layout.addWidget(self.meta_label)

        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(0, 0, 0, 0)
        footer_row.setSpacing(8)

        self.status_label = QLabel()
        set_widget_font_size(self.status_label, 10)
        footer_row.addWidget(self.status_label, 1, ALIGN_LEFT)

        self.progress_label = QLabel()
        set_widget_font_size(self.progress_label, 10)
        footer_row.addWidget(self.progress_label, 0, ALIGN_RIGHT)

        root_layout.addLayout(footer_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        root_layout.addWidget(self.progress_bar)

        self.update_from_item(item)

    def mousePressEvent(self, event):
        if event.button() == LEFT_MOUSE_BUTTON:
            self.clicked.emit(self.index)
            event.accept()
            return
        super().mousePressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_thumbnail()

    def set_selected(self, selected: bool):
        self.setProperty("cardSelected", selected)
        refresh_widget_style(self)

    def update_index(self, index: int):
        self.index = index

    def set_remove_enabled(self, enabled: bool):
        self.remove_button.setEnabled(enabled)

    def update_from_item(self, item: BatchQueueItem):
        self.item = item
        self._thumbnail = item.thumbnail
        self.setProperty("batchState", item.status)
        self.file_name_label.setText(item.file_name)
        self.meta_label.setText(item.exif_summary or item.resolution or "--")
        self._apply_thumbnail()

        styles = {
            "pending": ("准备就绪", "#7f848d", "", 0, False),
            "processing": (item.status_text or "处理中", "#83fff6", f"{item.progress}%", item.progress, True),
            "success": ("已完成", "#83fff6", "100%", 100, True),
            "skipped": ("已跳过", "#9f9d9d", "", 100, True),
            "failed": ("处理失败", "#ee7d77", "", max(item.progress, 2), True),
        }
        status_text, color, progress_text, progress_value, show_progress = styles[item.status]
        self.status_label.setText(status_text)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: 700;")
        self.progress_label.setText(progress_text)
        self.progress_label.setStyleSheet(f"color: {color}; font-weight: 700;")
        self.progress_bar.setVisible(show_progress)
        self.progress_bar.setValue(progress_value)
        self._apply_progress_style(item.status)

        tooltip_parts = [item.path]
        if item.output_path:
            tooltip_parts.append(f"输出：{item.output_path}")
        if item.error_message:
            tooltip_parts.append(f"错误：{item.error_message}")
        self.setToolTip("\n".join(tooltip_parts))
        refresh_widget_style(self)

    def _apply_thumbnail(self):
        if self._thumbnail.isNull():
            return
        available = self.preview_frame.contentsRect().adjusted(8, 8, -8, -8).size()
        if available.width() <= 0 or available.height() <= 0:
            available = QSize(148, 112)
        scaled = self._thumbnail.scaled(available, KEEP_ASPECT_RATIO, SMOOTH_TRANSFORMATION)
        self.thumbnail_label.setPixmap(scaled)

    def _apply_progress_style(self, state: str):
        colors = {
            "pending": "#474848",
            "processing": "#83fff6",
            "success": "#a3c9ff",
            "skipped": "#7f848d",
            "failed": "#ee7d77",
        }
        chunk_color = colors.get(state, "#a3c9ff")
        self.progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                background: rgba(71, 72, 72, 0.35);
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background: {chunk_color};
                border-radius: 2px;
            }}
            """
        )


class BatchCompletionDialog(QDialog):
    def __init__(self, summary: dict, template_name: str, output_dir: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.summary = summary
        self.template_name = template_name
        self.output_dir = str(Path(output_dir).resolve())
        self._drag_offset: Optional[QPoint] = None

        self.setObjectName("batchCompletionDialog")
        self.setWindowTitle("批量处理完成")
        self.setModal(True)
        self.setAttribute(TRANSLUCENT_BACKGROUND, True)
        self.setWindowFlags(DIALOG_WINDOW_TYPE | FRAMELESS_WINDOW_HINT)
        self.setMinimumWidth(520)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(0)

        panel = QFrame()
        panel.setObjectName("batchCompletionPanel")
        panel.installEventFilter(self)
        root_layout.addWidget(panel)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(18)

        stats_grid = QGridLayout()
        stats_grid.setContentsMargins(0, 0, 0, 0)
        stats_grid.setHorizontalSpacing(12)
        stats_grid.setVerticalSpacing(12)
        stat_specs = [
            ("总数", str(summary["total"]), "#f4f4f5"),
            ("成功", str(summary["success"]), "#83fff6"),
            ("跳过", str(summary["skipped"]), "#9f9d9d"),
            ("失败", str(summary["failed"]), "#ee7d77"),
        ]
        for index, (label_text, value_text, color) in enumerate(stat_specs):
            card = QFrame()
            card.setObjectName("batchCompletionStatCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 14, 16, 14)
            card_layout.setSpacing(6)

            label = QLabel(label_text)
            label.setObjectName("batchCompletionStatLabel")
            set_widget_font_size(label, 10)
            card_layout.addWidget(label)

            value = QLabel(value_text)
            value.setObjectName("batchCompletionStatValue")
            value.setStyleSheet(f"color: {color};")
            set_widget_font_size(value, 22)
            card_layout.addWidget(value)

            stats_grid.addWidget(card, index // 2, index % 2)
        layout.addLayout(stats_grid)

        meta_card = QFrame()
        meta_card.setObjectName("batchCompletionMetaCard")
        meta_layout = QVBoxLayout(meta_card)
        meta_layout.setContentsMargins(16, 16, 16, 16)
        meta_layout.setSpacing(12)
        for label_text, value_text in [
            ("当前模板", self.template_name),
            ("输出目录", self.output_dir),
            ("总耗时", format_duration(summary["elapsed"])),
        ]:
            row = QFrame()
            row.setObjectName("batchCompletionMetaRow")
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(4)

            label = QLabel(label_text)
            label.setObjectName("batchCompletionMetaLabel")
            set_widget_font_size(label, 10)
            row_layout.addWidget(label)

            value = QLabel(value_text)
            value.setObjectName("batchCompletionMetaValue")
            value.setWordWrap(True)
            value.setTextInteractionFlags(TEXT_SELECTABLE_BY_MOUSE)
            set_widget_font_size(value, 11)
            row_layout.addWidget(value)

            meta_layout.addWidget(row)
        layout.addWidget(meta_card)

        footer = QFrame()
        footer.setObjectName("batchCompletionFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 16, 16, 16)
        footer_layout.setSpacing(14)

        title_column = QVBoxLayout()
        title_column.setContentsMargins(0, 0, 0, 0)
        title_column.setSpacing(4)

        title = QLabel("批量处理完成")
        title.setObjectName("batchCompletionTitle")
        set_widget_font_size(title, 16)
        title_column.addWidget(title)

        subtitle = QLabel(
            f"成功 {summary['success']} | 跳过 {summary['skipped']} | 失败 {summary['failed']}"
        )
        subtitle.setObjectName("batchCompletionSubtitle")
        set_widget_font_size(subtitle, 11)
        title_column.addWidget(subtitle)
        footer_layout.addLayout(title_column, 1)

        self.close_button = QPushButton("关闭")
        self.close_button.setObjectName("batchCompletionCloseButton")
        set_widget_font_size(self.close_button, 12)
        self.close_button.setCursor(POINTING_HAND_CURSOR)
        self.close_button.setDefault(True)
        self.close_button.clicked.connect(self.accept)
        footer_layout.addWidget(self.close_button, 0, ALIGN_RIGHT)

        layout.addWidget(footer)
        self._install_drag_targets(panel)

        self.setStyleSheet(
            """
            QDialog#batchCompletionDialog {
                background: transparent;
            }
            QFrame#batchCompletionPanel {
                background: #0f1011;
                border: 1px solid rgba(71, 72, 72, 0.24);
                border-radius: 12px;
            }
            QFrame#batchCompletionStatCard,
            QFrame#batchCompletionMetaCard,
            QFrame#batchCompletionFooter {
                background: #151515;
                border: 1px solid rgba(71, 72, 72, 0.18);
                border-radius: 8px;
            }
            QLabel#batchCompletionStatLabel,
            QLabel#batchCompletionMetaLabel {
                color: #8f959c;
                font-weight: 700;
            }
            QLabel#batchCompletionStatValue,
            QLabel#batchCompletionTitle,
            QLabel#batchCompletionMetaValue {
                color: #f4f4f5;
                font-weight: 800;
            }
            QLabel#batchCompletionSubtitle {
                color: #8f959c;
            }
            QPushButton#batchCompletionCloseButton {
                min-height: 42px;
                min-width: 104px;
                padding: 0 18px;
                border-radius: 8px;
                border: none;
                background: #252626;
                color: #f4f4f5;
                font-weight: 800;
            }
            QPushButton#batchCompletionCloseButton:hover {
                background: #2f3031;
            }
            QPushButton#batchCompletionCloseButton:pressed {
                background: #1f2021;
            }
            """
        )

    def showEvent(self, event):
        super().showEvent(event)
        self.adjustSize()
        parent = self.parentWidget()
        if parent is None:
            return
        target = parent.window() if hasattr(parent, "window") else parent
        geometry = self.frameGeometry()
        geometry.moveCenter(target.frameGeometry().center())
        self.move(geometry.topLeft())

    def eventFilter(self, watched, event):
        if watched is getattr(self, "close_button", None):
            return super().eventFilter(watched, event)

        event_type = event.type()
        if event_type == QEvent.MouseButtonPress and event.button() == LEFT_MOUSE_BUTTON:
            self._drag_offset = event_global_pos(event) - self.frameGeometry().topLeft()
            event.accept()
            return True
        if event_type == QEvent.MouseMove and self._drag_offset is not None:
            self.move(event_global_pos(event) - self._drag_offset)
            event.accept()
            return True
        if event_type == QEvent.MouseButtonRelease and self._drag_offset is not None:
            self._drag_offset = None
            event.accept()
            return True
        return super().eventFilter(watched, event)

    def _install_drag_targets(self, widget: QWidget):
        widget.installEventFilter(self)
        for child in widget.findChildren(QWidget):
            if child is self.close_button:
                continue
            child.installEventFilter(self)

    def exec_modal(self):
        if hasattr(self, "exec"):
            return self.exec()
        return self.exec_()


class BatchProcessPage(QWidget):
    template_selected = Signal(str)
    status_changed = Signal(str)
    footer_meta_changed = Signal(str, str, str)

    def __init__(
        self,
        template_names: list[str],
        selected_template: str,
        output_dir: str,
        quality: int,
        subsampling: int,
        override_existing: bool,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.template_names = template_names
        self.selected_template = selected_template
        self.output_dir = output_dir
        self.quality = quality
        self.subsampling = subsampling
        self.override_existing = override_existing

        self.batch_items: list[BatchQueueItem] = []
        self.batch_cards: list[BatchCardWidget] = []
        self.selected_index: Optional[int] = None
        self.batch_thread: Optional[tuple[QThread, BatchProcessWorker]] = None
        self.grid_columns = 0

        self._build_ui()
        self.set_selected_template(self.selected_template)
        self._update_output_label()
        self._set_quality(self.quality)
        self._update_summary()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_workspace(), 1)
        layout.addWidget(self._build_settings_panel())

    def _build_workspace(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("batchWorkspace")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(16)

        title_column = QVBoxLayout()
        title_column.setContentsMargins(0, 0, 0, 0)
        title_column.setSpacing(4)

        eyebrow = QLabel("队列概览")
        eyebrow.setObjectName("batchEyebrow")
        set_widget_font_size(eyebrow, 10)
        title_column.addWidget(eyebrow)

        title = QLabel("批量处理工作区")
        title.setObjectName("sectionTitle")
        set_widget_font_size(title, 16)
        title_column.addWidget(title)

        self.summary_label = QLabel("还没有加入图片")
        self.summary_label.setObjectName("sectionSubtitle")
        set_widget_font_size(self.summary_label, 12)
        title_column.addWidget(self.summary_label)
        header_layout.addLayout(title_column, 1)

        self.add_button = QPushButton("添加图片")
        self.add_button.setObjectName("secondaryButton")
        set_widget_font_size(self.add_button, 12)
        self.add_button.clicked.connect(self._choose_images)
        header_layout.addWidget(self.add_button)

        self.clear_button = QPushButton("全部清空")
        self.clear_button.setObjectName("dangerButton")
        set_widget_font_size(self.clear_button, 12)
        self.clear_button.clicked.connect(self.clear_items)
        header_layout.addWidget(self.clear_button)

        layout.addWidget(header)

        self.cards_scroll = QScrollArea()
        self.cards_scroll.setWidgetResizable(True)
        self.cards_scroll.setFrameShape(QFrame.NoFrame)
        self.cards_scroll.setObjectName("batchCardsScroll")

        self.cards_container = QWidget()
        self.cards_grid = QGridLayout(self.cards_container)
        self.cards_grid.setContentsMargins(0, 0, 0, 0)
        self.cards_grid.setHorizontalSpacing(18)
        self.cards_grid.setVerticalSpacing(18)
        self.cards_grid.setAlignment(ALIGN_TOP)

        self.empty_label = QLabel("添加图片后开始批量处理")
        self.empty_label.setObjectName("batchEmptyLabel")
        self.empty_label.setAlignment(ALIGN_CENTER)
        self.empty_label.setMinimumHeight(320)
        set_widget_font_size(self.empty_label, 16)
        self.cards_grid.addWidget(self.empty_label, 0, 0, 1, 1)

        self.cards_scroll.setWidget(self.cards_container)
        layout.addWidget(self.cards_scroll, 1)
        return panel

    def _build_settings_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("batchRightPanel")
        panel.setFixedWidth(340)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(20)

        title = QLabel("全局参数设置")
        title.setObjectName("panelTitle")
        set_widget_font_size(title, 14)
        layout.addWidget(title)

        template_label = QLabel("主模板")
        template_label.setObjectName("metaLabel")
        set_widget_font_size(template_label, 10)
        layout.addWidget(template_label)

        self.template_combo = QComboBox()
        self.template_combo.setObjectName("batchCombo")
        self.template_combo.addItems(self.template_names)
        self.template_combo.currentTextChanged.connect(self._on_template_changed)
        set_widget_font_size(self.template_combo, 12)
        layout.addWidget(self.template_combo)

        output_label = QLabel("输出目录")
        output_label.setObjectName("metaLabel")
        set_widget_font_size(output_label, 10)
        layout.addWidget(output_label)

        output_row = QHBoxLayout()
        output_row.setContentsMargins(0, 0, 0, 0)
        output_row.setSpacing(8)

        output_box = QFrame()
        output_box.setObjectName("pathBox")
        output_box_layout = QVBoxLayout(output_box)
        output_box_layout.setContentsMargins(12, 10, 12, 10)
        output_box_layout.setSpacing(0)

        self.output_label = QLabel()
        self.output_label.setObjectName("pathBoxLabel")
        self.output_label.setWordWrap(True)
        self.output_label.setTextInteractionFlags(TEXT_SELECTABLE_BY_MOUSE)
        set_widget_font_size(self.output_label, 11)
        output_box_layout.addWidget(self.output_label)
        output_row.addWidget(output_box, 1)

        self.choose_output_button = QPushButton("浏览")
        self.choose_output_button.setObjectName("secondaryButton")
        set_widget_font_size(self.choose_output_button, 11)
        self.choose_output_button.clicked.connect(self._choose_output_dir)
        output_row.addWidget(self.choose_output_button)
        layout.addLayout(output_row)

        quality_row = QHBoxLayout()
        quality_row.setContentsMargins(0, 0, 0, 0)
        quality_row.setSpacing(8)
        quality_label = QLabel("导出质量")
        quality_label.setObjectName("metaLabel")
        set_widget_font_size(quality_label, 10)
        quality_row.addWidget(quality_label, 1, ALIGN_LEFT)

        self.quality_value_label = QLabel()
        self.quality_value_label.setObjectName("qualityValue")
        set_widget_font_size(self.quality_value_label, 12)
        quality_row.addWidget(self.quality_value_label, 0, ALIGN_RIGHT)
        layout.addLayout(quality_row)

        self.quality_slider = QSlider(HORIZONTAL)
        self.quality_slider.setRange(60, 100)
        self.quality_slider.valueChanged.connect(self._set_quality)
        self.quality_slider.setObjectName("qualitySlider")
        layout.addWidget(self.quality_slider)

        slider_hint = QHBoxLayout()
        slider_hint.setContentsMargins(0, 0, 0, 0)
        low_label = QLabel("低")
        high_label = QLabel("打印")
        low_label.setObjectName("sliderHint")
        high_label.setObjectName("sliderHint")
        set_widget_font_size(low_label, 10)
        set_widget_font_size(high_label, 10)
        slider_hint.addWidget(low_label, 0, ALIGN_LEFT)
        slider_hint.addStretch(1)
        slider_hint.addWidget(high_label, 0, ALIGN_RIGHT)
        layout.addLayout(slider_hint)

        layout.addStretch(1)

        progress_card = QFrame()
        progress_card.setObjectName("batchProgressCard")
        progress_layout = QVBoxLayout(progress_card)
        progress_layout.setContentsMargins(16, 16, 16, 16)
        progress_layout.setSpacing(10)

        progress_title_row = QHBoxLayout()
        progress_title_row.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel("处理进度")
        title_label.setObjectName("imageSectionTitle")
        set_widget_font_size(title_label, 12)
        progress_title_row.addWidget(title_label, 1, ALIGN_LEFT)

        self.progress_counter_label = QLabel("第 0/0 张图片")
        self.progress_counter_label.setObjectName("progressCounter")
        set_widget_font_size(self.progress_counter_label, 11)
        progress_title_row.addWidget(self.progress_counter_label, 0, ALIGN_RIGHT)
        progress_layout.addLayout(progress_title_row)

        self.overall_progress = QProgressBar()
        self.overall_progress.setRange(0, 100)
        self.overall_progress.setValue(0)
        self.overall_progress.setTextVisible(False)
        self.overall_progress.setObjectName("batchOverallProgress")
        progress_layout.addWidget(self.overall_progress)

        self.start_button = QPushButton("开始全量处理")
        self.start_button.setObjectName("primaryButton")
        set_widget_font_size(self.start_button, 13)
        self.start_button.clicked.connect(self.start_processing)
        progress_layout.addWidget(self.start_button)

        self.detail_label = QLabel("选择图片后开始批量处理")
        self.detail_label.setObjectName("batchDetailLabel")
        self.detail_label.setWordWrap(True)
        set_widget_font_size(self.detail_label, 10)
        progress_layout.addWidget(self.detail_label)

        layout.addWidget(progress_card)
        return panel

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout_cards()

    def set_selected_template(self, template_name: str):
        if template_name not in self.template_names:
            return
        self.selected_template = template_name
        if self.template_combo.currentText() != template_name:
            self.template_combo.blockSignals(True)
            self.template_combo.setCurrentText(template_name)
            self.template_combo.blockSignals(False)
        self._emit_footer_meta()

    def _on_template_changed(self, template_name: str):
        self.selected_template = template_name
        self.template_selected.emit(template_name)
        self._emit_footer_meta()

    def _update_output_label(self):
        resolved, display_text = format_path_for_label(self.output_dir)
        self.output_label.setText(display_text)
        self.output_label.setToolTip(resolved)

    def _set_quality(self, value: int):
        self.quality = int(value)
        self.quality_slider.blockSignals(True)
        self.quality_slider.setValue(self.quality)
        self.quality_slider.blockSignals(False)
        self.quality_value_label.setText(f"{self.quality}%")
        self._emit_footer_meta()

    def _choose_output_dir(self):
        chosen_dir = QFileDialog.getExistingDirectory(self, "选择输出目录", self.output_dir)
        if not chosen_dir:
            return
        self.output_dir = str(Path(chosen_dir).resolve())
        self._update_output_label()
        self._emit_footer_meta()

    def _choose_images(self):
        config = load_config()
        start_dir = str(Path(config.get("DEFAULT", "input_folder", fallback="./input")).resolve())
        paths, _ = QFileDialog.getOpenFileNames(self, "添加图片", start_dir, "Images (*.jpg *.jpeg *.png *.heic)")
        if paths:
            self.add_files(paths)

    def add_files(self, paths: list[str]):
        existing_paths = {item.path for item in self.batch_items}
        new_paths = []
        for path in paths:
            resolved = str(Path(path).resolve())
            if resolved not in existing_paths:
                existing_paths.add(resolved)
                new_paths.append(resolved)
        if not new_paths:
            QMessageBox.information(self, "没有新图片", "所选图片已经在批量队列中。")
            return
        for path in new_paths:
            item = self._build_queue_item(path)
            self.batch_items.append(item)
            card = BatchCardWidget(len(self.batch_cards), item)
            card.clicked.connect(self.select_item)
            card.remove_requested.connect(self.remove_item)
            self.batch_cards.append(card)
        if self.selected_index is None and self.batch_items:
            self.selected_index = 0
        self._relayout_cards(force=True)
        self.select_item(self.selected_index if self.selected_index is not None else 0)
        self._update_summary()
        self.status_changed.emit(f"状态：已加入 {len(new_paths)} 张图片到批量队列")

    def _build_queue_item(self, path: str) -> BatchQueueItem:
        resolved_path, modified_ns, file_size = get_file_signature(path)
        thumbnail, resolution = make_thumbnail(resolved_path)
        exif_data = deepcopy(get_cached_exif(resolved_path, modified_ns, file_size))
        exif_summary = format_exif_summary(exif_data)
        return BatchQueueItem(
            path=resolved_path,
            file_name=Path(resolved_path).name,
            thumbnail=thumbnail,
            exif_summary=exif_summary or resolution,
            resolution=resolution,
            file_size=file_size,
        )

    def clear_items(self):
        if self.batch_thread is not None:
            QMessageBox.information(self, "处理中", "批量处理尚未完成，暂时不能清空队列。")
            return
        self.batch_items.clear()
        for card in self.batch_cards:
            card.deleteLater()
        self.batch_cards.clear()
        self.selected_index = None
        self.grid_columns = 0
        self._relayout_cards(force=True)
        self._update_summary()
        self._emit_footer_meta()
        self.status_changed.emit("状态：批量队列已清空")

    def remove_item(self, index: int):
        if self.batch_thread is not None:
            QMessageBox.information(self, "处理中", "批量处理尚未完成，暂时不能移除图片。")
            return
        if index < 0 or index >= len(self.batch_items):
            return

        removed_item = self.batch_items.pop(index)
        removed_card = self.batch_cards.pop(index)
        self.cards_grid.removeWidget(removed_card)
        removed_card.hide()
        removed_card.deleteLater()

        if not self.batch_items:
            self.selected_index = None
        elif self.selected_index is None:
            self.selected_index = 0
        elif index < self.selected_index:
            self.selected_index -= 1
        elif index == self.selected_index:
            self.selected_index = min(index, len(self.batch_items) - 1)

        self._relayout_cards(force=True)
        if self.selected_index is not None:
            self.select_item(self.selected_index)
        else:
            self._emit_footer_meta()
        self._update_summary()
        self.status_changed.emit(f"状态：已从批量队列移除 {removed_item.file_name}")

    def select_item(self, index: int):
        if index is None or index < 0 or index >= len(self.batch_cards):
            return
        self.selected_index = index
        for card_index, card in enumerate(self.batch_cards):
            card.set_selected(card_index == index)
        self._emit_footer_meta()

    def _relayout_cards(self, force: bool = False):
        while self.cards_grid.count():
            layout_item = self.cards_grid.takeAt(0)
            widget = layout_item.widget()
            if widget is not None:
                self.cards_grid.removeWidget(widget)
        if not self.batch_cards:
            self.cards_grid.addWidget(self.empty_label, 0, 0, 1, 1)
            self.empty_label.show()
            return
        self.empty_label.hide()
        viewport_width = self.cards_scroll.viewport().width()
        columns = max(1, min(4, viewport_width // (BATCH_CARD_WIDTH + 20)))
        if not force and columns == self.grid_columns:
            columns = self.grid_columns or columns
        self.grid_columns = columns
        for index, card in enumerate(self.batch_cards):
            row = index // columns
            column = index % columns
            card.update_index(index)
            self.cards_grid.addWidget(card, row, column, 1, 1, ALIGN_TOP)

    def _update_summary(self):
        total = len(self.batch_items)
        if total == 0:
            self.summary_label.setText("还没有加入图片")
            self.detail_label.setText("选择图片后开始批量处理")
            self.progress_counter_label.setText("第 0/0 张图片")
            self.overall_progress.setValue(0)
            return
        status_counts = {"pending": 0, "processing": 0, "success": 0, "skipped": 0, "failed": 0}
        for item in self.batch_items:
            status_counts[item.status] += 1
        self.summary_label.setText(
            f"共 {total} 张图片 | 就绪 {status_counts['pending']} | 完成 {status_counts['success']} | 失败 {status_counts['failed']}"
        )

    def _set_controls_enabled(self, enabled: bool):
        self.add_button.setEnabled(enabled)
        self.clear_button.setEnabled(enabled)
        self.start_button.setEnabled(enabled)
        self.template_combo.setEnabled(enabled)
        self.quality_slider.setEnabled(enabled)
        self.choose_output_button.setEnabled(enabled)
        for card in self.batch_cards:
            card.set_remove_enabled(enabled)

    def _reset_item_states(self):
        for index, item in enumerate(self.batch_items):
            item.status = "pending"
            item.progress = 0
            item.status_text = "准备就绪"
            item.output_path = None
            item.output_resolution = None
            item.output_size = None
            item.error_message = None
            self.batch_cards[index].update_from_item(item)

    def start_processing(self):
        if self.batch_thread is not None:
            QMessageBox.information(self, "处理中", "批量处理任务正在运行，请等待完成。")
            return
        if not self.batch_items:
            QMessageBox.information(self, "批量处理", "请先添加至少一张图片。")
            return
        output_dir = Path(self.output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        self._reset_item_states()
        self.overall_progress.setValue(0)
        self.progress_counter_label.setText(f"第 1/{len(self.batch_items)} 张图片")
        self.detail_label.setText(f"正在准备批量任务\n模板：{self.selected_template} | 输出质量：{self.quality}%")
        self._set_controls_enabled(False)
        self.status_changed.emit(f"状态：开始批量处理 | 共 {len(self.batch_items)} 张")

        common_root = compute_common_root([item.path for item in self.batch_items])
        thread = QThread(self)
        worker = BatchProcessWorker(
            [item.path for item in self.batch_items],
            self.selected_template,
            self.output_dir,
            self.quality,
            self.subsampling,
            self.override_existing,
            common_root,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.item_progress.connect(self._on_item_progress)
        worker.item_complete.connect(self._on_item_complete)
        worker.item_skipped.connect(self._on_item_skipped)
        worker.item_failed.connect(self._on_item_failed)
        worker.overall_progress.connect(self._on_overall_progress)
        worker.status_message.connect(self.status_changed)
        worker.finished.connect(self._on_finished)
        worker.finished.connect(lambda *_: thread.quit())
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_thread)
        self.batch_thread = (thread, worker)
        thread.start()

    def _on_item_progress(self, index: int, progress: int, status_text: str):
        if index >= len(self.batch_items):
            return
        item = self.batch_items[index]
        item.status = "processing"
        item.progress = progress
        item.status_text = status_text
        self.batch_cards[index].update_from_item(item)
        self.select_item(index)
        self.status_changed.emit(f"状态：正在处理第 {index + 1} 张 | {item.file_name}")

    def _on_item_complete(self, index: int, output_path: str, resolution: str, file_size: int):
        if index >= len(self.batch_items):
            return
        item = self.batch_items[index]
        item.status = "success"
        item.progress = 100
        item.status_text = "已完成"
        item.output_path = output_path
        item.output_resolution = resolution
        item.output_size = file_size
        item.error_message = None
        self.batch_cards[index].update_from_item(item)
        self.select_item(index)

    def _on_item_skipped(self, index: int, output_path: str):
        if index >= len(self.batch_items):
            return
        item = self.batch_items[index]
        item.status = "skipped"
        item.progress = 100
        item.status_text = "已跳过"
        item.output_path = output_path
        item.error_message = None
        self.batch_cards[index].update_from_item(item)
        self.select_item(index)

    def _on_item_failed(self, index: int, error_message: str):
        if index >= len(self.batch_items):
            return
        item = self.batch_items[index]
        item.status = "failed"
        item.progress = max(item.progress, 8)
        item.status_text = "处理失败"
        item.error_message = error_message
        self.batch_cards[index].update_from_item(item)
        self.select_item(index)

    def _on_overall_progress(self, processed: int, total: int, current_index: int, eta_text: str):
        progress = int(round((processed / total) * 100)) if total else 0
        self.overall_progress.setValue(progress)
        self.progress_counter_label.setText(f"第 {min(current_index, total)}/{total} 张图片")
        self.detail_label.setText(
            f"预计剩余时间：{eta_text}\n当前模板：{self.selected_template} | 目标目录：{Path(self.output_dir).name}"
        )
        self._update_summary()

    def _on_finished(self, summary: dict):
        self._set_controls_enabled(True)
        total = summary["total"]
        self.overall_progress.setValue(100 if total else 0)
        self.progress_counter_label.setText(f"第 {total}/{total} 张图片" if total else "第 0/0 张图片")
        self.detail_label.setText(
            f"完成：{summary['success']} | 跳过：{summary['skipped']} | 失败：{summary['failed']}\n"
            f"耗时：{format_duration(summary['elapsed'])} | 输出目录：{Path(self.output_dir).name}"
        )
        self._update_summary()
        self.status_changed.emit(
            f"状态：批量处理完成 | 成功 {summary['success']} | 跳过 {summary['skipped']} | 失败 {summary['failed']}"
        )
        self._emit_footer_meta()
        BatchCompletionDialog(summary, self.selected_template, self.output_dir, self).exec_modal()

    def _clear_thread(self):
        self.batch_thread = None

    def _emit_footer_meta(self):
        if self.selected_index is None or self.selected_index >= len(self.batch_items):
            self.footer_meta_changed.emit("--", "--", f"JPEG {self.quality}%")
            return
        item = self.batch_items[self.selected_index]
        resolution = item.output_resolution or item.resolution or "--"
        size_value = item.output_size if item.output_size is not None else item.file_size
        self.footer_meta_changed.emit(resolution, format_bytes(size_value), f"JPEG {self.quality}%")

    def sync_footer(self):
        self._emit_footer_meta()
