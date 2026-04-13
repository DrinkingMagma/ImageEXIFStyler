from __future__ import annotations

import traceback
from collections import OrderedDict
from pathlib import Path
from typing import Optional

from PIL import Image

from core.configs import load_config
from core.logger import logger
from core.util import build_export_filename, ensure_export_suffixes
from UI.batch.page import BatchProcessPage
from UI.editor.constants import SUPPORTED_FILTER, WINDOW_TITLE
from UI.editor.widgets import PreviewLabel, TemplateCardButton
from UI.settings.page import SettingsPageMixin
from UI.shared.theme import EDITOR_STYLESHEET
from UI.template_library.page import TemplateLibraryPageMixin
from UI.template_library.widgets import TemplateLibraryCard
from UI.editor.workers import ExportWorker, PreviewWorker
from UI.shared.paths import PROJECT_ROOT
from UI.shared.qt import (
    ALIGN_CENTER,
    ALIGN_LEFT,
    ALIGN_RIGHT,
    HORIZONTAL,
    KEEP_ASPECT_RATIO,
    PLAIN_TEXT,
    POINTING_HAND_CURSOR,
    QT_BINDING,
    SCROLLBAR_ALWAYS_OFF,
    SMOOTH_TRANSFORMATION,
    TEXT_SELECTABLE_BY_MOUSE,
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFont,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QImage,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPixmap,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QThread,
    QTimer,
    QVBoxLayout,
    QWidget,
)
from UI.shared.templates import TEMPLATE_SPECS, build_template_specs
from UI.shared.utils import (
    format_bytes,
    format_path_for_label,
    get_file_signature,
    refresh_widget_style,
    set_widget_font_size,
)


class EditorWindow(TemplateLibraryPageMixin, SettingsPageMixin, QMainWindow):
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
        self.displayed_preview_template: Optional[str] = None
        self._pending_footer_meta = ("--", "--", "--")
        self.output_dir_setting = str((PROJECT_ROOT / config.get("DEFAULT", "output_folder", fallback="./output")).resolve())
        self.export_quality_setting = config.getint("DEFAULT", "quality", fallback=90)
        self.export_subsampling_setting = config.getint("DEFAULT", "subsampling", fallback=2)
        self.logo_enabled_setting = config.getboolean("DEFAULT", "enable_logo", fallback=True)
        self.hardware_acceleration_setting = config.getboolean(
            "DEFAULT", "hardware_acceleration", fallback=False
        )
        if config.has_option("DEFAULT", "override_existing"):
            self.override_existing_setting = config.getboolean("DEFAULT", "override_existing", fallback=False)
        else:
            self.override_existing_setting = config.getboolean("DEFAULT", "override_existed", fallback=False)

        self.preview_debounce = QTimer(self)
        self.preview_debounce.setSingleShot(True)
        self.preview_debounce.timeout.connect(self._render_preview)

        self.template_specs = TEMPLATE_SPECS or build_template_specs()
        self.template_buttons: dict[str, TemplateCardButton] = {}
        self.template_library_cards: dict[str, TemplateLibraryCard] = {}
        self.nav_buttons: dict[str, QPushButton] = {}
        fallback_template = self.template_specs[0].name if self.template_specs else ""
        self.selected_template = config.get("render", "template_name", fallback=fallback_template)
        if self.selected_template not in self._template_names():
            self.selected_template = fallback_template
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
        self.page_stack.addWidget(self._build_template_library_page())
        self.page_stack.addWidget(self._build_settings_page())
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
            ("templates", "模板库", True),
            ("settings", "设置", True),
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

        divider = QFrame()
        divider.setObjectName("sidebarDivider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)

        utility_items = ["语言设置", "检查更新", "关于"]
        for text in utility_items:
            button = QPushButton(text)
            button.setProperty("sidebarUtility", True)
            button.setEnabled(False)
            set_widget_font_size(button, 12)
            layout.addWidget(button)
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
        page = BatchProcessPage(
            [spec.name for spec in self.template_specs],
            self.selected_template,
            self.output_dir_setting,
            self.export_quality_setting,
            self.export_subsampling_setting,
            self.override_existing_setting,
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

        body_scroll = QScrollArea()
        body_scroll.setWidgetResizable(True)
        body_scroll.setFrameShape(QFrame.NoFrame)
        body_scroll.setObjectName("rightPanelScroll")
        body_scroll.setHorizontalScrollBarPolicy(SCROLLBAR_ALWAYS_OFF)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(20, 22, 20, 22)
        body_layout.setSpacing(16)

        section_label = QLabel("模板选择")
        section_label.setObjectName("metaLabel")
        set_widget_font_size(section_label, 10)
        body_layout.addWidget(section_label)

        self.template_grid = QGridLayout()
        self.template_grid.setHorizontalSpacing(10)
        self.template_grid.setVerticalSpacing(10)

        self.template_group = QButtonGroup(self)
        self.template_group.setExclusive(True)

        self._populate_editor_template_grid()
        body_layout.addLayout(self.template_grid)

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

        body_scroll.setWidget(body)
        layout.addWidget(body_scroll, 1)

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
        self._update_footer_meta(*self._pending_footer_meta)
        return footer


    def _apply_theme(self):
        self.setFont(QFont("Microsoft YaHei UI", 10))
        self.setStyleSheet(EDITOR_STYLESHEET)

    def _template_names(self) -> list[str]:
        return [spec.name for spec in self.template_specs]

    def _clear_grid_layout(self, layout: QGridLayout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _populate_editor_template_grid(self):
        self._clear_grid_layout(self.template_grid)
        for button in list(self.template_group.buttons()):
            self.template_group.removeButton(button)
        self.template_buttons = {}

        for index, spec in enumerate(self.template_specs):
            button = TemplateCardButton(spec)
            button.clicked.connect(lambda checked, name=spec.name: self._on_template_selected(name, checked))
            self.template_group.addButton(button)
            self.template_buttons[spec.name] = button
            if spec.name == self.selected_template:
                button.setChecked(True)
            self.template_grid.addWidget(button, index // 2, index % 2)


    def _sync_batch_template_names(self):
        if self.batch_page is None:
            return
        template_names = self._template_names()
        self.batch_page.template_names = template_names
        self.batch_page.template_combo.blockSignals(True)
        self.batch_page.template_combo.clear()
        self.batch_page.template_combo.addItems(template_names)
        if self.selected_template:
            self.batch_page.template_combo.setCurrentText(self.selected_template)
        self.batch_page.template_combo.blockSignals(False)
        self.batch_page.set_selected_template(self.selected_template)

    def _reload_template_specs(self, select_template: Optional[str] = None):
        self.template_specs = build_template_specs()
        template_names = self._template_names()
        if select_template in template_names:
            self.selected_template = select_template
        elif self.selected_template not in template_names and template_names:
            self.selected_template = template_names[0]
        elif not template_names:
            self.selected_template = ""

        self._populate_editor_template_grid()
        self._populate_template_library_grid()
        self._sync_batch_template_names()
        self._sync_settings_template_names()
        self._sync_editor_template_buttons(self.selected_template)
        self._sync_library_template_cards(self.selected_template)




    def _set_mode(self, mode: str):
        page_indexes = {"editor": 0, "batch": 1, "templates": 2, "settings": 3}
        mode_titles = {
            "editor": "EDITOR",
            "batch": "BATCH PROCESS",
            "templates": "TEMPLATE LIBRARY",
            "settings": "SETTINGS",
        }

        if mode not in page_indexes:
            return

        self.current_mode = mode
        self.page_stack.setCurrentIndex(page_indexes[mode])
        self.top_hint_label.setText(mode_titles[mode])

        for button_mode, button in self.nav_buttons.items():
            button.setProperty("navActive", button_mode == mode)
            refresh_widget_style(button)

        preview_scheduled = False
        if mode == "batch" and self.batch_page is not None:
            self.batch_page.set_selected_template(self.selected_template)
            self.batch_page.sync_footer()
        elif mode == "templates":
            self._sync_library_template_cards(self.selected_template)
            self._update_template_library_meta()
            self._update_footer_meta(f"{len(self.template_specs)} templates", "--", self.selected_template or "--")
        elif mode == "settings":
            self._sync_settings_template_names()
            self._update_settings_output_label()
            self._set_export_quality(self.export_quality_setting, persist=False)
            self._update_footer_meta(
                self.selected_template or "--",
                Path(self.output_dir_setting).name or "--",
                f"JPEG {self.export_quality_setting}%",
            )
        else:
            self._refresh_file_metadata()
            if self.input_path and self.displayed_preview_template != self.selected_template:
                self.schedule_preview()
                preview_scheduled = True

        batch_busy = self.batch_page is not None and self.batch_page.batch_thread is not None
        if self.export_thread is None and not batch_busy:
            if mode == "editor":
                if not preview_scheduled:
                    self._update_status("状态：单图编辑就绪")
            elif mode == "batch":
                queue_size = len(self.batch_page.batch_items) if self.batch_page is not None else 0
                if queue_size:
                    self._update_status(f"状态：批量队列已就绪 | 共 {queue_size} 张")
                else:
                    self._update_status("状态：批量队列为空")
            elif mode == "settings":
                self._update_status("状态：设置页就绪")
            else:
                self._update_status(f"状态：模板库就绪 | 当前模板：{self.selected_template or '--'}")

    def _sync_editor_template_buttons(self, template_name: str):
        for button_name, button in self.template_buttons.items():
            should_check = button_name == template_name
            if button.isChecked() == should_check:
                continue
            button.blockSignals(True)
            button.setChecked(should_check)
            button.blockSignals(False)

    def _apply_selected_template(self, template_name: str, source: str):
        if template_name not in self._template_names():
            return

        template_changed = template_name != self.selected_template
        self.selected_template = template_name
        self._save_config_value("render", "template_name", template_name)

        if source != "editor":
            self._sync_editor_template_buttons(template_name)
        if source != "batch" and self.batch_page is not None:
            self.batch_page.set_selected_template(template_name)
        self._sync_library_template_cards(template_name)
        if source != "settings":
            self._sync_settings_template_names()

        if self.current_mode == "editor" and template_changed and self.input_path:
            self._refresh_file_metadata()
            self.schedule_preview()
        elif self.current_mode == "editor":
            self._refresh_file_metadata()
        elif self.current_mode == "batch" and self.batch_page is not None:
            self.batch_page.sync_footer()
        elif self.current_mode == "settings":
            self._update_footer_meta(
                self.selected_template or "--",
                Path(self.output_dir_setting).name or "--",
                f"JPEG {self.export_quality_setting}%",
            )
        elif self.current_mode == "templates":
            self._update_template_library_meta()
            self._update_footer_meta(f"{len(self.template_specs)} templates", "--", self.selected_template or "--")

    def _handle_batch_template_selected(self, template_name: str):
        self._apply_selected_template(template_name, source="batch")


    def _update_footer_meta(self, resolution: str, file_size: str, format_text: str):
        self._pending_footer_meta = (resolution, file_size, format_text)
        if not hasattr(self, "resolution_label"):
            return
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
        self.displayed_preview_template = None
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
            self.displayed_preview_template = None
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
            self.displayed_preview_template = meta["template"]
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
        self.displayed_preview_template = meta["template"]
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

        output_dir = Path(self.output_dir_setting).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        export_quality = self.export_quality_setting
        default_name = build_export_filename(
            Path(self.input_path),
            self.selected_template,
            quality=export_quality,
            extension=".jpg",
        )

        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出图像",
            str(output_dir / default_name),
            "JPEG (*.jpg *.jpeg);;PNG (*.png)",
        )
        if not output_path:
            return
        output_path = str(ensure_export_suffixes(output_path, self.selected_template, export_quality))

        self.export_button.setEnabled(False)
        self._update_status(f"状态：正在导出 | 模板：{self.selected_template}")

        thread = QThread(self)
        worker = ExportWorker(
            self.input_path,
            self.selected_template,
            output_path,
            quality=export_quality,
            subsampling=self.export_subsampling_setting,
        )
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
