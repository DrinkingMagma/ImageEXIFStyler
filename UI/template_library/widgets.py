from __future__ import annotations

from pathlib import Path
from typing import Optional

from UI.shared.qt import (
    ALIGN_CENTER,
    ALIGN_LEFT,
    ALIGN_RIGHT,
    KEEP_ASPECT_RATIO,
    LEFT_MOUSE_BUTTON,
    POINTING_HAND_CURSOR,
    SMOOTH_TRANSFORMATION,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPixmap,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    Signal,
)
from UI.shared.templates import TemplateSpec
from UI.shared.utils import refresh_widget_style, set_widget_font_size


class TemplateThumbnailLabel(QLabel):
    def __init__(self, placeholder: str = "无预览图"):
        super().__init__(placeholder)
        self._source_pixmap: Optional[QPixmap] = None
        self._placeholder = placeholder
        self.setAlignment(ALIGN_CENTER)
        self.setMinimumHeight(190)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setWordWrap(True)

    def set_source_path(self, path: Path):
        pixmap = QPixmap(str(path)) if path.exists() else QPixmap()
        if pixmap.isNull():
            self._source_pixmap = None
            self.setPixmap(QPixmap())
            self.setText(self._placeholder)
            return
        self._source_pixmap = pixmap
        self.setText("")
        self._apply_scaled_pixmap()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_scaled_pixmap()

    def _apply_scaled_pixmap(self):
        if self._source_pixmap is None or self._source_pixmap.isNull():
            return
        target_size = self.contentsRect().size()
        if target_size.width() <= 0 or target_size.height() <= 0:
            target_size = self.size()
        scaled = self._source_pixmap.scaled(target_size, KEEP_ASPECT_RATIO, SMOOTH_TRANSFORMATION)
        self.setPixmap(scaled)


class TemplateLibraryCard(QFrame):
    clicked = Signal(str)

    def __init__(self, spec: TemplateSpec):
        super().__init__()
        self.spec = spec
        self.setObjectName("templateLibraryCard")
        self.setProperty("cardSelected", False)
        self.setCursor(POINTING_HAND_CURSOR)
        self.setMinimumWidth(360)
        self.setMinimumHeight(318)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.preview_frame = QFrame()
        self.preview_frame.setObjectName("templateLibraryPreviewFrame")
        self.preview_frame.setMinimumHeight(260)
        self.preview_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        preview_layout = QVBoxLayout(self.preview_frame)
        preview_layout.setContentsMargins(16, 16, 16, 16)

        self.thumbnail = TemplateThumbnailLabel()
        self.thumbnail.setObjectName("templateLibraryThumbnail")
        self.thumbnail.set_source_path(spec.thumbnail_path)
        preview_layout.addWidget(self.thumbnail)
        layout.addWidget(self.preview_frame)

        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(4, 0, 4, 0)
        footer_layout.setSpacing(10)

        self.title_label = QLabel(spec.name)
        self.title_label.setObjectName("templateLibraryTitle")
        set_widget_font_size(self.title_label, 13)
        footer_layout.addWidget(self.title_label, 1, ALIGN_LEFT)

        self.badge_label = QLabel("当前")
        self.badge_label.setObjectName("templateLibraryBadge")
        self.badge_label.setVisible(False)
        set_widget_font_size(self.badge_label, 11)
        footer_layout.addWidget(self.badge_label, 0, ALIGN_RIGHT)
        layout.addWidget(footer)

    def set_selected(self, selected: bool):
        self.setProperty("cardSelected", selected)
        self.badge_label.setVisible(selected)
        for widget in [self, self.preview_frame, self.title_label, self.badge_label]:
            refresh_widget_style(widget)

    def mousePressEvent(self, event):
        if event.button() == LEFT_MOUSE_BUTTON:
            self.clicked.emit(self.spec.name)
            event.accept()
            return
        super().mousePressEvent(event)


class CreateTemplateCard(QFrame):
    clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("createTemplateCard")
        self.setCursor(POINTING_HAND_CURSOR)
        self.setMinimumHeight(260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.setAlignment(ALIGN_CENTER)

        plus_label = QLabel("+")
        plus_label.setObjectName("createTemplatePlus")
        plus_label.setAlignment(ALIGN_CENTER)
        set_widget_font_size(plus_label, 34)
        layout.addWidget(plus_label, 0, ALIGN_CENTER)

        text_label = QLabel("创建自定义模板")
        text_label.setObjectName("createTemplateText")
        text_label.setAlignment(ALIGN_CENTER)
        set_widget_font_size(text_label, 12)
        layout.addWidget(text_label, 0, ALIGN_CENTER)

        hint_label = QLabel("基于当前模板复制")
        hint_label.setObjectName("createTemplateHint")
        hint_label.setAlignment(ALIGN_CENTER)
        set_widget_font_size(hint_label, 10)
        layout.addWidget(hint_label, 0, ALIGN_CENTER)

    def mousePressEvent(self, event):
        if event.button() == LEFT_MOUSE_BUTTON:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)

