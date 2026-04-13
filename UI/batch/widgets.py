from __future__ import annotations

from pathlib import Path
from typing import Optional

from UI.batch.models import BATCH_CARD_WIDTH, BatchQueueItem
from UI.shared.qt import (
    ALIGN_CENTER,
    ALIGN_LEFT,
    ALIGN_RIGHT,
    DIALOG_WINDOW_TYPE,
    FRAMELESS_WINDOW_HINT,
    KEEP_ASPECT_RATIO,
    LEFT_MOUSE_BUTTON,
    POINTING_HAND_CURSOR,
    SMOOTH_TRANSFORMATION,
    TEXT_SELECTABLE_BY_MOUSE,
    TRANSLUCENT_BACKGROUND,
    QDialog,
    QEvent,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPoint,
    QProgressBar,
    QPushButton,
    QSize,
    QToolButton,
    QVBoxLayout,
    QWidget,
    Signal,
)
from UI.shared.utils import (
    event_global_pos,
    format_duration,
    px_to_pt,
    refresh_widget_style,
    set_widget_font_size,
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
