from __future__ import annotations

from pathlib import Path
from typing import Optional

from UI.shared.qt import (
    ALIGN_CENTER,
    ALIGN_LEFT,
    ALIGN_RIGHT,
    KEEP_ASPECT_RATIO,
    LEFT_MOUSE_BUTTON,
    NO_PEN,
    POINTING_HAND_CURSOR,
    ROUND_CAP,
    SMOOTH_TRANSFORMATION,
    TOOL_BUTTON_TEXT_UNDER_ICON,
    QColor,
    QFrame,
    QHBoxLayout,
    QIcon,
    QLabel,
    QPainter,
    QPen,
    QPixmap,
    QSize,
    QSizePolicy,
    QTimer,
    QToolButton,
    QVBoxLayout,
    QWidget,
    Signal,
)
from UI.shared.templates import TemplateSpec
from UI.shared.utils import px_to_pt, refresh_widget_style, set_widget_font_size


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
        self.setToolTip(spec.name)
        self.setToolButtonStyle(TOOL_BUTTON_TEXT_UNDER_ICON)
        self.setIconSize(QSize(108, 78))
        self.setFixedSize(126, 128)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        set_widget_font_size(self, 10)
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
                padding: 7px;
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

