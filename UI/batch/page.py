from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Optional

from core.configs import load_config
from UI.batch.models import (
    BATCH_CARD_WIDTH,
    BatchQueueItem,
    compute_common_root,
    format_exif_summary,
    make_thumbnail,
)
from UI.batch.worker import BatchProcessWorker
from UI.batch.widgets import BatchCardWidget, BatchCompletionDialog
from UI.shared.qt import (
    ALIGN_CENTER,
    ALIGN_LEFT,
    ALIGN_RIGHT,
    ALIGN_TOP,
    HORIZONTAL,
    TEXT_SELECTABLE_BY_MOUSE,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QThread,
    QVBoxLayout,
    QWidget,
    Signal,
)
from UI.shared.utils import (
    format_bytes,
    format_duration,
    format_path_for_label,
    get_cached_exif,
    get_file_signature,
    set_widget_font_size,
)


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

    def set_output_dir(self, output_dir: str):
        self.output_dir = str(Path(output_dir).resolve())
        self._update_output_label()
        self._emit_footer_meta()

    def set_quality(self, quality: int):
        self._set_quality(int(quality))

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
        worker_count = BatchProcessWorker.recommended_worker_count(len(self.batch_items))
        self.progress_counter_label.setText(f"第 1/{len(self.batch_items)} 张图片")
        self.detail_label.setText(
            f"正在准备批量任务\n模板：{self.selected_template} | 输出质量：{self.quality}% | 并发：{worker_count} 线程"
        )
        self._set_controls_enabled(False)
        self.status_changed.emit(f"状态：开始批量处理 | 共 {len(self.batch_items)} 张 | 并发 {worker_count} 线程")

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
            worker_count,
            ".jpg",
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
            f"耗时：{format_duration(summary['elapsed'])} | 并发：{summary.get('workers', 1)} 线程 | 输出目录：{Path(self.output_dir).name}"
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
