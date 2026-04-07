from __future__ import annotations

import json
import os
import sys
import traceback
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

try:
    from PySide6.QtCore import QObject, QSize, Qt, QThread, QTimer, Signal
    from PySide6.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPen, QPixmap
    from PySide6.QtWidgets import (
        QApplication,
        QButtonGroup,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QStackedWidget,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )

    QT_BINDING = "PySide6"
except ImportError:
    from PyQt5.QtCore import QObject, QSize, Qt, QThread, QTimer, pyqtSignal as Signal
    from PyQt5.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPen, QPixmap
    from PyQt5.QtWidgets import (
        QApplication,
        QButtonGroup,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QStackedWidget,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )

    QT_BINDING = "PyQt5"

from PIL import Image
from UI.batch_process_page import BatchProcessPage

import processor  # noqa: F401  # 触发处理器自动注册
from core.configs import load_config
from core.logger import init_from_config, logger
from core.util import get_exif, get_template, get_template_path
from processor.core import start_process
from processor import ensure_processors_registered

if hasattr(Qt, "AlignmentFlag"):
    ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
    ALIGN_LEFT = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    ALIGN_RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    KEEP_ASPECT_RATIO = Qt.AspectRatioMode.KeepAspectRatio
    SMOOTH_TRANSFORMATION = Qt.TransformationMode.SmoothTransformation
    TOOL_BUTTON_TEXT_UNDER_ICON = Qt.ToolButtonStyle.ToolButtonTextUnderIcon
    POINTING_HAND_CURSOR = Qt.CursorShape.PointingHandCursor
    LEFT_MOUSE_BUTTON = Qt.MouseButton.LeftButton
    NO_PEN = Qt.PenStyle.NoPen
    ROUND_CAP = Qt.PenCapStyle.RoundCap
    TEXT_SELECTABLE_BY_MOUSE = Qt.TextInteractionFlag.TextSelectableByMouse
    PLAIN_TEXT = Qt.TextFormat.PlainText
else:
    ALIGN_CENTER = Qt.AlignCenter
    ALIGN_LEFT = Qt.AlignLeft | Qt.AlignVCenter
    ALIGN_RIGHT = Qt.AlignRight | Qt.AlignVCenter
    KEEP_ASPECT_RATIO = Qt.KeepAspectRatio
    SMOOTH_TRANSFORMATION = Qt.SmoothTransformation
    TOOL_BUTTON_TEXT_UNDER_ICON = Qt.ToolButtonTextUnderIcon
    POINTING_HAND_CURSOR = Qt.PointingHandCursor
    LEFT_MOUSE_BUTTON = Qt.LeftButton
    NO_PEN = Qt.NoPen
    ROUND_CAP = Qt.RoundCap
    TEXT_SELECTABLE_BY_MOUSE = Qt.TextSelectableByMouse
    PLAIN_TEXT = Qt.PlainText

WINDOW_TITLE = "Photo EXIF Frame Tool"
HEIC_AVAILABLE = getattr(processor, "pillow_heif", None) is not None
SUPPORTED_FILTER = "Images (*.jpg *.jpeg *.png *.heic)" if HEIC_AVAILABLE else "Images (*.jpg *.jpeg *.png)"


@dataclass(frozen=True)
class TemplateSpec:
    name: str
    thumbnail_path: Path


TEMPLATE_SPECS = [
    TemplateSpec("背景模糊", PROJECT_ROOT / "UI" / "template_images" / "背景模糊.jpg"),
    TemplateSpec("标准水印", PROJECT_ROOT / "UI" / "template_images" / "标准水印.jpg"),
    TemplateSpec("标准水印2", PROJECT_ROOT / "UI" / "template_images" / "标准水印2.jpg"),
    TemplateSpec("尼康专用背景模糊", PROJECT_ROOT / "UI" / "template_images" / "尼康专用背景模糊.jpg"),
]


def format_bytes(size: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f}{unit}" if unit != "B" else f"{int(value)}B"
        value /= 1024
    return f"{size}B"


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
    return get_exif(resolved_path)


@lru_cache(maxsize=16)
def get_cached_template(template_name: str, modified_ns: int):
    return get_template(template_name)


def pil_to_qimage(image: Image.Image) -> QImage:
    rgb_image = image.convert("RGB")
    data = rgb_image.tobytes("raw", "RGB")
    qimage = QImage(data, rgb_image.width, rgb_image.height, rgb_image.width * 3, QImage.Format_RGB888)
    return qimage.copy()


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

    def render_preview(self, input_path: str, template_name: str, exif_data: Optional[dict] = None) -> Image.Image:
        exif = exif_data if exif_data is not None else self.get_exif_data(input_path)
        pipeline = self.render_pipeline(input_path, template_name, exif_data=exif)
        image = start_process(pipeline, input_path=input_path, exif_data=exif)
        return image.copy()

    def export_image(
        self,
        input_path: str,
        template_name: str,
        output_path: str,
        quality: Optional[int] = None,
        subsampling: Optional[int] = None,
    ) -> str:
        exif = self.get_exif_data(input_path)
        pipeline = self.render_pipeline(input_path, template_name, exif_data=exif)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        save_options = {}
        if quality is not None:
            save_options["quality"] = quality
        if subsampling is not None:
            save_options["subsampling"] = subsampling
        start_process(
            pipeline,
            input_path=input_path,
            output_path=str(output),
            exif_data=exif,
            save_options=save_options or None,
        )
        return str(output)


class PreviewWorker(QObject):
    finished = Signal(int, object, object)
    failed = Signal(int, str)

    def __init__(self, token: int, input_path: str, template_name: str):
        super().__init__()
        self.token = token
        self.input_path = input_path
        self.template_name = template_name

    def run(self):
        try:
            service = TemplateRenderService()
            exif_data = service.get_exif_data(self.input_path)
            image = service.render_preview(self.input_path, self.template_name, exif_data=exif_data)
            meta = {
                "template": self.template_name,
                "resolution": f"{image.width}x{image.height}",
            }
            self.finished.emit(self.token, pil_to_qimage(image), meta)
        except Exception as exc:
            logger.error(traceback.format_exc())
            self.failed.emit(self.token, str(exc))


class ExportWorker(QObject):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        input_path: str,
        template_name: str,
        output_path: str,
        quality: Optional[int] = None,
        subsampling: Optional[int] = None,
    ):
        super().__init__()
        self.input_path = input_path
        self.template_name = template_name
        self.output_path = output_path
        self.quality = quality
        self.subsampling = subsampling

    def run(self):
        try:
            service = TemplateRenderService()
            output_path = service.export_image(
                self.input_path,
                self.template_name,
                self.output_path,
                quality=self.quality,
                subsampling=self.subsampling,
            )
            self.finished.emit(output_path)
        except Exception as exc:
            logger.error(traceback.format_exc())
            self.failed.emit(str(exc))


class PreviewLabel(QLabel):
    clicked = Signal()

    def __init__(self):
        super().__init__("导入照片后开始预览")
        self._pixmap: Optional[QPixmap] = None
        self._loading = False
        self._loading_text = "正在生成预览"
        self._spinner_angle = 0
        self._spinner_timer = QTimer(self)
        self._spinner_timer.setInterval(16)
        self._spinner_timer.timeout.connect(self._advance_spinner)
        self.setAlignment(ALIGN_CENTER)
        self.setMinimumSize(720, 480)
        self.setWordWrap(True)
        self.setCursor(POINTING_HAND_CURSOR)
        self.setToolTip("点击选择图片")
        set_widget_font_size(self, 16)
        self.setStyleSheet(
            """
            QLabel {
                color: #a3c9ff;
                border: 1px dashed rgba(163, 201, 255, 0.16);
                border-radius: 18px;
                background: rgba(10, 10, 10, 0.42);
                padding: 32px;
            }
            """
        )

    def set_preview(self, pixmap: Optional[QPixmap], placeholder: Optional[str] = None):
        self._pixmap = pixmap
        self._loading = False
        self._spinner_timer.stop()
        if pixmap is None:
            self.setPixmap(QPixmap())
            self.setText(placeholder or "导入照片后开始预览")
            self.update()
            return
        self.setText("")
        self._apply_scaled_pixmap()
        self.update()

    def set_loading(self, loading: bool, text: Optional[str] = None):
        self._loading = loading
        if text:
            self._loading_text = text
        if loading:
            if not self._spinner_timer.isActive():
                self._spinner_timer.start()
        else:
            self._spinner_timer.stop()
        self.update()

    def mousePressEvent(self, event):
        if event.button() == LEFT_MOUSE_BUTTON:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap is not None:
            self._apply_scaled_pixmap()

    def _apply_scaled_pixmap(self):
        if self._pixmap is None:
            return
        target_size = self.contentsRect().size()
        if target_size.width() <= 0 or target_size.height() <= 0:
            target_size = self.size()
        scaled = self._pixmap.scaled(target_size, KEEP_ASPECT_RATIO, SMOOTH_TRANSFORMATION)
        self.setPixmap(scaled)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._loading:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        overlay_rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setPen(NO_PEN)
        painter.setBrush(QColor(5, 5, 5, 150))
        painter.drawRoundedRect(overlay_rect, 18, 18)

        badge_width = min(260, max(200, overlay_rect.width() - 80))
        badge_height = 120
        badge_x = overlay_rect.center().x() - badge_width / 2
        badge_y = overlay_rect.center().y() - badge_height / 2
        painter.setBrush(QColor(17, 18, 20, 232))
        painter.drawRoundedRect(int(badge_x), int(badge_y), int(badge_width), badge_height, 18, 18)

        spinner_size = 30
        spinner_x = overlay_rect.center().x() - spinner_size / 2
        spinner_y = int(badge_y) + 24
        track_pen = QPen(QColor(71, 72, 72, 180), 3)
        track_pen.setCapStyle(ROUND_CAP)
        painter.setPen(track_pen)
        painter.drawArc(int(spinner_x), spinner_y, spinner_size, spinner_size, 0, 360 * 16)

        accent_pen = QPen(QColor("#a3c9ff"), 4)
        accent_pen.setCapStyle(ROUND_CAP)
        painter.setPen(accent_pen)
        painter.drawArc(int(spinner_x), spinner_y, spinner_size, spinner_size, self._spinner_angle * 16, 110 * 16)

        text_font = self.font()
        text_font.setPointSizeF(px_to_pt(13))
        painter.setFont(text_font)
        painter.setPen(QColor("#e7e5e5"))
        painter.drawText(
            int(badge_x) + 18,
            spinner_y + spinner_size + 16,
            int(badge_width) - 36,
            32,
            int(ALIGN_CENTER),
            self._loading_text,
        )

    def _advance_spinner(self):
        self._spinner_angle = (self._spinner_angle - 12) % 360
        self.update()


class TemplateCardButton(QToolButton):
    def __init__(self, spec: TemplateSpec):
        super().__init__()
        self.spec = spec
        self.setText(spec.name)
        self.setCheckable(True)
        self.setCursor(POINTING_HAND_CURSOR)
        self.setToolButtonStyle(TOOL_BUTTON_TEXT_UNDER_ICON)
        self.setIconSize(QSize(120, 88))
        self.setFixedSize(136, 136)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        set_widget_font_size(self, 11)
        if spec.thumbnail_path.exists():
            self.setIcon(QIcon(str(spec.thumbnail_path)))
        self.setStyleSheet(
            """
            QToolButton {
                background: #252626;
                border: 1px solid transparent;
                border-radius: 12px;
                color: #acabab;
                font-weight: 600;
                padding: 8px;
                text-align: left;
            }
            QToolButton:hover {
                border: 1px solid #474848;
                background: #2b2c2c;
                color: #e7e5e5;
            }
            QToolButton:checked {
                border: 1px solid #a3c9ff;
                background: #1f2020;
                color: #a3c9ff;
            }
            """
        )


class EditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{WINDOW_TITLE} ({QT_BINDING})")
        self.resize(1520, 800)
        self.setMinimumSize(1520, 800)

        config = load_config()
        self.input_path: Optional[str] = None
        self.current_mode = "editor"
        self.current_preview_token = 0
        self.preview_threads: dict[int, tuple[QThread, PreviewWorker]] = {}
        self.export_thread: Optional[tuple[QThread, ExportWorker]] = None
        self.preview_cache: OrderedDict[tuple[str, int, int, str], tuple[QPixmap, dict]] = OrderedDict()

        self.preview_debounce = QTimer(self)
        self.preview_debounce.setSingleShot(True)
        self.preview_debounce.timeout.connect(self._render_preview)

        self.template_specs = TEMPLATE_SPECS
        self.template_buttons: dict[str, TemplateCardButton] = {}
        self.nav_buttons: dict[str, QPushButton] = {}
        self.selected_template = config.get("render", "template_name", fallback=self.template_specs[0].name)
        if self.selected_template not in [spec.name for spec in self.template_specs]:
            self.selected_template = self.template_specs[0].name
        self.batch_page: Optional[BatchProcessPage] = None

        self._build_ui()
        self._apply_theme()
        self._set_mode("editor")
        self._update_status("状态：就绪")

    def _build_ui(self):
        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_top_bar())

        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        content.addWidget(self._build_left_sidebar())
        self.page_stack = QStackedWidget()
        self.page_stack.setObjectName("contentStack")
        self.page_stack.addWidget(self._build_editor_page())
        self.batch_page = self._build_batch_page()
        self.page_stack.addWidget(self.batch_page)
        content.addWidget(self.page_stack, 1)
        root_layout.addLayout(content, 1)

        root_layout.addWidget(self._build_footer())
        self.setCentralWidget(central)

    def _build_top_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("topBar")
        bar.setFixedHeight(52)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 0, 24, 0)

        title = QLabel("PHOTO EXIF FRAME TOOL")
        title.setObjectName("topTitle")
        set_widget_font_size(title, 11)
        layout.addWidget(title, 0, ALIGN_LEFT)
        layout.addStretch(1)

        self.top_hint_label = QLabel("EDITOR")
        self.top_hint_label.setObjectName("topHint")
        set_widget_font_size(self.top_hint_label, 11)
        layout.addWidget(self.top_hint_label, 0, ALIGN_RIGHT)
        return bar

    def _build_left_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("leftSidebar")
        sidebar.setFixedWidth(240)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 24, 20, 24)
        layout.setSpacing(10)

        title = QLabel("LENS & FRAME")
        title.setObjectName("sidebarTitle")
        set_widget_font_size(title, 18)
        subtitle = QLabel("Professional Curator")
        subtitle.setObjectName("sidebarSubtitle")
        set_widget_font_size(subtitle, 10)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(22)

        nav_items = [
            ("editor", "编辑器", True),
            ("batch", "批量处理", True),
            ("templates", "模板库", False),
            ("settings", "设置", False),
        ]
        for mode, text, implemented in nav_items:
            button = QPushButton(text)
            button.setProperty("navActive", False)
            button.setProperty("navImplemented", implemented)
            button.setCursor(POINTING_HAND_CURSOR)
            if implemented:
                button.clicked.connect(lambda _checked=False, target_mode=mode: self._set_mode(target_mode))
                self.nav_buttons[mode] = button
            else:
                button.setEnabled(False)
            set_widget_font_size(button, 13)
            layout.addWidget(button)

        layout.addStretch(1)

        self.profile_label = QLabel()
        self.profile_label.setObjectName("profileLabel")
        set_widget_font_size(self.profile_label, 11)
        layout.addWidget(self.profile_label)
        return sidebar

    def _build_editor_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("editorPage")

        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_preview_area(), 1)
        layout.addWidget(self._build_right_panel())
        return page

    def _build_batch_page(self) -> BatchProcessPage:
        config = load_config()
        output_dir = str((PROJECT_ROOT / config.get("DEFAULT", "output_folder", fallback="./output")).resolve())
        quality = config.getint("DEFAULT", "quality", fallback=90)
        subsampling = config.getint("DEFAULT", "subsampling", fallback=2)
        override_existing = False
        if config.has_option("DEFAULT", "override_existing"):
            override_existing = config.getboolean("DEFAULT", "override_existing", fallback=False)
        else:
            override_existing = config.getboolean("DEFAULT", "override_existed", fallback=False)

        page = BatchProcessPage(
            [spec.name for spec in self.template_specs],
            self.selected_template,
            output_dir,
            quality,
            subsampling,
            override_existing,
            self,
        )
        page.template_selected.connect(self._handle_batch_template_selected)
        page.status_changed.connect(self._update_status)
        page.footer_meta_changed.connect(self._update_footer_meta)
        return page

    def _build_preview_area(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("previewPanel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        headline = QLabel("实时预览")
        headline.setObjectName("sectionTitle")
        set_widget_font_size(headline, 14)
        subline = QLabel("选择照片后，切换右侧模板会重新生成预览。")
        subline.setObjectName("sectionSubtitle")
        set_widget_font_size(subline, 12)
        layout.addWidget(headline)
        layout.addWidget(subline)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("previewScroll")

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(36, 24, 36, 24)
        container_layout.setAlignment(ALIGN_CENTER)

        self.preview_label = PreviewLabel()
        self.preview_label.clicked.connect(self._choose_input_image)
        container_layout.addWidget(self.preview_label, 0, ALIGN_CENTER)

        scroll.setWidget(container)
        layout.addWidget(scroll, 1)
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("rightPanel")
        panel.setFixedWidth(340)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("rightHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(22, 18, 22, 18)
        header_layout.setSpacing(6)

        title = QLabel("参数设置")
        title.setObjectName("panelTitle")
        set_widget_font_size(title, 14)
        header_layout.addWidget(title)

        self.file_info_label = QLabel("未选择图像")
        self.file_info_label.setObjectName("fileInfo")
        set_widget_font_size(self.file_info_label, 12)
        header_layout.addWidget(self.file_info_label)
        layout.addWidget(header)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(22, 22, 22, 22)
        body_layout.setSpacing(18)

        section_label = QLabel("模板选择")
        section_label.setObjectName("metaLabel")
        set_widget_font_size(section_label, 10)
        body_layout.addWidget(section_label)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        self.template_group = QButtonGroup(self)
        self.template_group.setExclusive(True)

        for index, spec in enumerate(self.template_specs):
            button = TemplateCardButton(spec)
            button.clicked.connect(lambda checked, name=spec.name: self._on_template_selected(name, checked))
            self.template_group.addButton(button)
            self.template_buttons[spec.name] = button
            if spec.name == self.selected_template:
                button.setChecked(True)
            grid.addWidget(button, index // 2, index % 2)

        body_layout.addLayout(grid)

        image_info_card = QFrame()
        image_info_card.setObjectName("imageInfoCard")
        image_info_layout = QVBoxLayout(image_info_card)
        image_info_layout.setContentsMargins(16, 14, 16, 14)
        image_info_layout.setSpacing(6)

        file_title = QLabel("当前图片")
        file_title.setObjectName("imageSectionTitle")
        set_widget_font_size(file_title, 12)
        image_info_layout.addWidget(file_title)

        self.path_label = QLabel("尚未导入")
        self.path_label.setObjectName("pathLabel")
        self.path_label.setWordWrap(True)
        self.path_label.setTextFormat(PLAIN_TEXT)
        self.path_label.setTextInteractionFlags(TEXT_SELECTABLE_BY_MOUSE)
        self.path_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.path_label.setMinimumWidth(0)
        set_widget_font_size(self.path_label, 11)
        image_info_layout.addWidget(self.path_label)

        body_layout.addWidget(image_info_card)

        layout.addWidget(body, 1)

        actions = QFrame()
        actions.setObjectName("actionPanel")
        actions_layout = QVBoxLayout(actions)
        actions_layout.setContentsMargins(22, 20, 22, 20)
        actions_layout.setSpacing(12)

        self.import_button = QPushButton("导入照片")
        self.import_button.setObjectName("secondaryButton")
        set_widget_font_size(self.import_button, 13)
        self.import_button.clicked.connect(self._choose_input_image)
        actions_layout.addWidget(self.import_button)

        self.export_button = QPushButton("导出图像")
        self.export_button.setObjectName("primaryButton")
        self.export_button.setEnabled(False)
        set_widget_font_size(self.export_button, 13)
        self.export_button.clicked.connect(self._export_image)
        actions_layout.addWidget(self.export_button)

        layout.addWidget(actions)
        return panel

    def _build_footer(self) -> QWidget:
        footer = QFrame()
        footer.setObjectName("footerBar")
        footer.setFixedHeight(34)

        layout = QHBoxLayout(footer)
        layout.setContentsMargins(16, 0, 16, 0)

        self.status_label = QLabel("PHOTO EXIF FRAME TOOL v1.0 | 状态：就绪")
        self.status_label.setObjectName("statusLabel")
        set_widget_font_size(self.status_label, 11)
        layout.addWidget(self.status_label, 0, ALIGN_LEFT)
        layout.addStretch(1)

        self.resolution_label = QLabel("--")
        self.filesize_label = QLabel("--")
        self.format_label = QLabel("--")
        for widget in [self.resolution_label, self.filesize_label, self.format_label]:
            widget.setObjectName("footerMeta")
            set_widget_font_size(widget, 11)
            layout.addWidget(widget)
        return footer

    def _apply_theme(self):
        self.setFont(QFont("Microsoft YaHei UI", 10))
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #0e0e0e;
                color: #e7e5e5;
            }
            QStackedWidget#contentStack, QWidget#editorPage {
                background: transparent;
            }
            QFrame#topBar, QFrame#footerBar {
                background: #050505;
                border: none;
            }
            QLabel#topTitle {
                color: #f1f5f9;
                font-weight: 800;
                letter-spacing: 2px;
            }
            QLabel#topHint {
                color: #6b7280;
                font-weight: 700;
            }
            QFrame#leftSidebar {
                background: #020202;
                border-right: 1px solid rgba(71, 72, 72, 0.18);
            }
            QLabel#sidebarTitle {
                font-weight: 800;
                color: #f4f4f5;
            }
            QLabel#sidebarSubtitle {
                color: #60a5fa;
                font-weight: 700;
                letter-spacing: 1px;
                text-transform: uppercase;
            }
            QPushButton[navActive="true"], QPushButton[navActive="false"] {
                min-height: 44px;
                border-radius: 8px;
                border: none;
                text-align: left;
                padding: 0 14px;
                font-weight: 700;
                background: transparent;
            }
            QPushButton[navActive="true"] {
                background: #1a1d22;
                color: #60a5fa;
            }
            QPushButton[navActive="false"] {
                background: transparent;
                color: #737373;
            }
            QPushButton[navActive="false"]:hover:enabled {
                background: #111214;
                color: #e7e5e5;
            }
            QPushButton[navImplemented="false"] {
                color: #4b5563;
            }
            QLabel#profileLabel {
                color: #9ca3af;
                background: #111214;
                border: 1px solid rgba(71, 72, 72, 0.18);
                border-radius: 8px;
                padding: 14px;
                line-height: 1.5;
            }
            QFrame#previewPanel {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.9, fx:0.5, fy:0.5,
                    stop:0 #191a1a, stop:1 #0a0a0a);
            }
            QLabel#sectionTitle, QLabel#panelTitle {
                font-weight: 800;
                color: #f4f4f5;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            QLabel#sectionSubtitle, QLabel#fileInfo {
                color: #a3a3a3;
            }
            QFrame#rightPanel, QFrame#batchRightPanel {
                background: #131313;
                border-left: 1px solid rgba(71, 72, 72, 0.15);
            }
            QFrame#rightHeader, QFrame#actionPanel {
                background: transparent;
                border: none;
            }
            QLabel#metaLabel, QLabel#batchEyebrow {
                color: #9f9d9d;
                font-weight: 800;
                letter-spacing: 2px;
                text-transform: uppercase;
            }
            QLabel#batchEyebrow {
                color: #848a91;
            }
            QFrame#imageInfoCard {
                background: transparent;
                border: none;
                border-radius: 0;
            }
            QLabel#imageSectionTitle {
                color: #f4f4f5;
                font-weight: 700;
            }
            QLabel#pathLabel, QLabel#pathBoxLabel {
                color: #b7bcc3;
                background: transparent;
            }
            QPushButton#secondaryButton, QPushButton#primaryButton, QPushButton#dangerButton {
                min-height: 44px;
                border-radius: 8px;
                font-weight: 800;
                border: none;
                padding: 0 16px;
            }
            QPushButton#secondaryButton {
                background: #252626;
                color: #e7e5e5;
            }
            QPushButton#secondaryButton:hover {
                background: #2b2c2c;
            }
            QPushButton#secondaryButton:disabled, QPushButton#dangerButton:disabled {
                background: #1d1d1d;
                color: #5f6368;
            }
            QPushButton#dangerButton {
                background: #241717;
                color: #ee7d77;
            }
            QPushButton#dangerButton:hover:enabled {
                background: #2f1b1b;
            }
            QPushButton#primaryButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #a3c9ff, stop:1 #004883);
                color: #e7f1ff;
            }
            QPushButton#primaryButton:hover:enabled {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #bcd6ff, stop:1 #0a5ea8);
            }
            QPushButton#primaryButton:disabled {
                background: #3b3b3b;
                color: #757575;
            }
            QLabel#statusLabel {
                color: #67e8f9;
                font-weight: 700;
            }
            QLabel#footerMeta {
                color: #737373;
                font-weight: 600;
                padding-left: 18px;
            }
            QScrollArea#previewScroll, QScrollArea#batchCardsScroll {
                border: none;
                background: transparent;
            }
            QFrame#batchWorkspace {
                background: #101010;
            }
            QFrame#batchProgressCard {
                background: #111214;
                border-radius: 8px;
                border: 1px solid rgba(71, 72, 72, 0.12);
            }
            QLabel#progressCounter, QLabel#qualityValue {
                color: #83fff6;
                font-weight: 700;
            }
            QLabel#sliderHint, QLabel#batchDetailLabel {
                color: #7f848d;
            }
            QFrame#pathBox {
                background: #0a0b0b;
                border: 1px solid rgba(71, 72, 72, 0.12);
                border-radius: 8px;
            }
            QComboBox#batchCombo {
                min-height: 42px;
                border-radius: 8px;
                padding: 0 14px;
                background: #252626;
                color: #e7e5e5;
                border: 1px solid rgba(163, 201, 255, 0.35);
            }
            QComboBox#batchCombo:hover {
                background: #2b2c2c;
            }
            QComboBox#batchCombo::drop-down {
                border: none;
                width: 28px;
            }
            QComboBox#batchCombo::down-arrow {
                image: none;
                width: 0;
                height: 0;
            }
            QSlider#qualitySlider::groove:horizontal {
                height: 4px;
                background: #252626;
                border-radius: 2px;
            }
            QSlider#qualitySlider::sub-page:horizontal {
                height: 4px;
                background: #83fff6;
                border-radius: 2px;
            }
            QSlider#qualitySlider::handle:horizontal {
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
                background: #a3c9ff;
                border: 2px solid #0e0e0e;
            }
            QProgressBar#batchOverallProgress {
                min-height: 6px;
                background: #252626;
                border: none;
                border-radius: 3px;
            }
            QProgressBar#batchOverallProgress::chunk {
                background: #a3c9ff;
                border-radius: 3px;
            }
            QLabel#batchEmptyLabel {
                color: #6f747b;
                background: #111214;
                border-radius: 8px;
                border: 1px dashed rgba(127, 132, 141, 0.25);
                padding: 28px;
            }
            QFrame#batchCard {
                background: #151515;
                border: 1px solid transparent;
                border-radius: 8px;
            }
            QFrame#batchCard:hover {
                background: #181919;
            }
            QFrame#batchCard[cardSelected="true"] {
                background: #191b1e;
                border: 1px solid rgba(163, 201, 255, 0.45);
            }
            QFrame#batchCard[batchState="processing"] {
                background: #14181a;
            }
            QFrame#batchCard[batchState="success"] {
                background: #15191a;
            }
            QFrame#batchCard[batchState="failed"] {
                background: #1a1414;
            }
            QFrame#batchPreviewFrame {
                background: #f4f4f5;
                border-radius: 6px;
            }
            QFrame#batchCard[batchState="processing"] QFrame#batchPreviewFrame {
                background: #182024;
            }
            QLabel#batchThumbnail {
                background: #f4f4f5;
                border-radius: 4px;
            }
            QToolButton#batchRemoveButton {
                background: #5b1f21;
                color: #ffe6e5;
                border: 1px solid rgba(238, 125, 119, 0.28);
                border-radius: 6px;
                padding: 0;
                font-weight: 800;
            }
            QToolButton#batchRemoveButton:hover {
                background: #6d2629;
                color: #fff2f1;
            }
            QToolButton#batchRemoveButton:pressed {
                background: #491719;
            }
            QToolButton#batchRemoveButton:disabled {
                background: #241717;
                color: #77514f;
                border: 1px solid rgba(119, 81, 79, 0.25);
            }
            QLabel#batchFileName {
                color: #f4f4f5;
                font-weight: 700;
            }
            QLabel#batchMeta {
                color: #8f959c;
            }
            """
        )

    def _set_mode(self, mode: str):
        if mode not in {"editor", "batch"}:
            return

        self.current_mode = mode
        self.page_stack.setCurrentIndex(0 if mode == "editor" else 1)
        self.top_hint_label.setText("EDITOR" if mode == "editor" else "BATCH PROCESS")
        self.profile_label.setText("当前模式\n单图编辑预览" if mode == "editor" else "当前模式\n批量处理工作区")

        for button_mode, button in self.nav_buttons.items():
            button.setProperty("navActive", button_mode == mode)
            refresh_widget_style(button)

        if mode == "batch" and self.batch_page is not None:
            self.batch_page.set_selected_template(self.selected_template)
            self.batch_page.sync_footer()
        else:
            self._refresh_file_metadata()

        batch_busy = self.batch_page is not None and self.batch_page.batch_thread is not None
        if self.export_thread is None and not batch_busy:
            if mode == "editor":
                self._update_status("状态：单图编辑就绪")
            else:
                queue_size = len(self.batch_page.batch_items) if self.batch_page is not None else 0
                if queue_size:
                    self._update_status(f"状态：批量队列已就绪 | 共 {queue_size} 张")
                else:
                    self._update_status("状态：批量队列为空")

    def _sync_editor_template_buttons(self, template_name: str):
        for button_name, button in self.template_buttons.items():
            should_check = button_name == template_name
            if button.isChecked() == should_check:
                continue
            button.blockSignals(True)
            button.setChecked(should_check)
            button.blockSignals(False)

    def _apply_selected_template(self, template_name: str, source: str):
        if template_name not in [spec.name for spec in self.template_specs]:
            return

        template_changed = template_name != self.selected_template
        self.selected_template = template_name

        if source != "editor":
            self._sync_editor_template_buttons(template_name)
        if source != "batch" and self.batch_page is not None:
            self.batch_page.set_selected_template(template_name)

        self._refresh_file_metadata()
        if self.current_mode == "editor" and template_changed and self.input_path:
            self.schedule_preview()
        elif self.current_mode == "batch" and self.batch_page is not None:
            self.batch_page.sync_footer()

    def _handle_batch_template_selected(self, template_name: str):
        self._apply_selected_template(template_name, source="batch")

    def _update_footer_meta(self, resolution: str, file_size: str, format_text: str):
        self.resolution_label.setText(resolution)
        self.filesize_label.setText(file_size)
        self.format_label.setText(format_text)

    def _choose_input_image(self):
        config = load_config()
        start_dir = str((PROJECT_ROOT / config.get("DEFAULT", "input_folder", fallback="./input")).resolve())
        file_path, _ = QFileDialog.getOpenFileName(self, "选择输入图像", start_dir, SUPPORTED_FILTER)
        if not file_path:
            return

        self.input_path = file_path
        resolved_path, display_path = format_path_for_label(file_path)
        self.path_label.setText(display_path)
        self.path_label.setToolTip(resolved_path)
        self._refresh_file_metadata()
        self.schedule_preview()

    def _refresh_file_metadata(self):
        if not self.input_path:
            self.file_info_label.setText("未选择图像")
            self._update_footer_meta("--", "--", "--")
            return

        path = Path(self.input_path)
        try:
            with Image.open(path) as image:
                resolution = f"{image.width}x{image.height}"
                format_text = image.format or path.suffix.upper().replace(".", "")
            file_size = format_bytes(path.stat().st_size)
            self._update_footer_meta(resolution, file_size, format_text)
            self.file_info_label.setText(f"{path.name} | {self.selected_template}")
        except Exception as exc:
            self.file_info_label.setText(f"{path.name} | 读取失败: {exc}")

    def _make_preview_cache_key(self) -> Optional[tuple[str, int, int, str]]:
        if not self.input_path:
            return None
        try:
            resolved_path, modified_ns, file_size = get_file_signature(self.input_path)
        except OSError:
            return None
        return resolved_path, modified_ns, file_size, self.selected_template

    def _get_cached_preview(self) -> Optional[tuple[QPixmap, dict]]:
        cache_key = self._make_preview_cache_key()
        if cache_key is None:
            return None
        cached_preview = self.preview_cache.get(cache_key)
        if cached_preview is None:
            return None
        self.preview_cache.move_to_end(cache_key)
        return cached_preview

    def _store_cached_preview(self, pixmap: QPixmap, meta: dict):
        cache_key = self._make_preview_cache_key()
        if cache_key is None:
            return
        self.preview_cache[cache_key] = (QPixmap(pixmap), dict(meta))
        self.preview_cache.move_to_end(cache_key)
        while len(self.preview_cache) > 8:
            self.preview_cache.popitem(last=False)

    def _on_template_selected(self, template_name: str, checked: bool):
        if not checked:
            return
        self._apply_selected_template(template_name, source="editor")

    def schedule_preview(self):
        if not self.input_path:
            self.preview_label.set_preview(None, "先导入照片，再切换模板查看实时预览。")
            self._update_status("状态：等待导入图像")
            self.export_button.setEnabled(False)
            return

        self.current_preview_token += 1

        cached_preview = self._get_cached_preview()
        if cached_preview is not None:
            pixmap, meta = cached_preview
            self.preview_label.set_preview(QPixmap(pixmap))
            self.preview_label.set_loading(False)
            self.export_button.setEnabled(True)
            self.file_info_label.setText(f"{Path(self.input_path).name} | {meta['template']}")
            self._update_status(f"状态：预览已更新 | 缓存命中 | 模板：{meta['template']}")
            return

        self.export_button.setEnabled(False)
        self.preview_label.set_loading(True, "正在渲染模板预览")
        self._update_status(f"状态：正在生成预览 | 模板：{self.selected_template}")
        self.preview_debounce.start(120)

    def _render_preview(self):
        if not self.input_path:
            return

        token = self.current_preview_token
        thread = QThread(self)
        worker = PreviewWorker(token, self.input_path, self.selected_template)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._handle_preview_ready)
        worker.failed.connect(self._handle_preview_failed)
        worker.finished.connect(lambda *_: thread.quit())
        worker.failed.connect(lambda *_: thread.quit())
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self.preview_threads.pop(token, None))
        self.preview_threads[token] = (thread, worker)
        thread.start()

    def _handle_preview_ready(self, token: int, image: QImage, meta: dict):
        if token != self.current_preview_token:
            return
        pixmap = QPixmap.fromImage(image)
        self._store_cached_preview(pixmap, meta)
        self.preview_label.set_preview(pixmap)
        self.preview_label.set_loading(False)
        self.export_button.setEnabled(True)
        self.file_info_label.setText(f"{Path(self.input_path).name} | {meta['template']}")
        self._update_status(f"状态：预览已更新 | 模板：{meta['template']}")

    def _handle_preview_failed(self, token: int, error_message: str):
        if token != self.current_preview_token:
            return
        self.preview_label.set_preview(None, f"预览生成失败\n{error_message}")
        self.export_button.setEnabled(False)
        self._update_status("状态：预览失败")
        QMessageBox.critical(self, "预览失败", error_message)

    def _export_image(self):
        if not self.input_path:
            return
        if self.export_thread is not None:
            QMessageBox.information(self, "导出进行中", "当前已有导出任务，请等待完成。")
            return

        config = load_config()
        output_dir = (PROJECT_ROOT / config.get("DEFAULT", "output_folder", fallback="./output")).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        input_name = Path(self.input_path).stem
        default_name = f"{input_name}_{self.selected_template}.jpg"

        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出图像",
            str(output_dir / default_name),
            "JPEG (*.jpg *.jpeg);;PNG (*.png)",
        )
        if not output_path:
            return

        self.export_button.setEnabled(False)
        self._update_status(f"状态：正在导出 | 模板：{self.selected_template}")

        thread = QThread(self)
        worker = ExportWorker(self.input_path, self.selected_template, output_path)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._handle_export_finished)
        worker.failed.connect(self._handle_export_failed)
        worker.finished.connect(lambda *_: thread.quit())
        worker.failed.connect(lambda *_: thread.quit())
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_export_thread)
        self.export_thread = (thread, worker)
        thread.start()

    def _handle_export_finished(self, output_path: str):
        self.export_button.setEnabled(True)
        self._update_status(f"状态：导出完成 | {Path(output_path).name}")
        QMessageBox.information(self, "导出完成", f"图像已导出到:\n{output_path}")

    def _handle_export_failed(self, error_message: str):
        self.export_button.setEnabled(True)
        self._update_status("状态：导出失败")
        QMessageBox.critical(self, "导出失败", error_message)

    def _clear_export_thread(self):
        self.export_thread = None

    def _update_status(self, text: str):
        self.status_label.setText(f"PHOTO EXIF FRAME TOOL v1.0 | {text}")


def main():
    if hasattr(QApplication, "setAttribute") and hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    app.setApplicationName(WINDOW_TITLE)
    app.setFont(QFont("Microsoft YaHei UI", 10))
    window = EditorWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
