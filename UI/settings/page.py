from __future__ import annotations

from pathlib import Path

from core.configs import load_config, logos_dir, save_config
from UI.shared.paths import PROJECT_ROOT
from UI.shared.qt import (
    ALIGN_CENTER,
    ALIGN_LEFT,
    ALIGN_RIGHT,
    HORIZONTAL,
    KEEP_ASPECT_RATIO,
    POINTING_HAND_CURSOR,
    SMOOTH_TRANSFORMATION,
    TEXT_SELECTABLE_BY_MOUSE,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPixmap,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
    QComboBox,
)
from UI.shared.utils import format_path_for_label, set_widget_font_size


class SettingsPageMixin:
    def _build_settings_page(self) -> QWidget:
        page = QFrame()
        page.setObjectName("settingsPage")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("settingsScroll")

        container = QWidget()
        container.setObjectName("settingsContent")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(42, 38, 42, 58)
        container_layout.setSpacing(28)

        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        title = QLabel("设置")
        title.setObjectName("settingsHeading")
        set_widget_font_size(title, 32)
        header_layout.addWidget(title)

        subtitle = QLabel("管理默认模板、导出路径、输出质量和自动 Logo 偏好。")
        subtitle.setObjectName("settingsSubtitle")
        subtitle.setWordWrap(True)
        set_widget_font_size(subtitle, 13)
        header_layout.addWidget(subtitle)
        container_layout.addWidget(header)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(24)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.addWidget(self._build_settings_defaults_card(), 0, 0)
        grid.addWidget(self._build_settings_export_card(), 0, 1)
        grid.addWidget(self._build_settings_logo_card(), 1, 0, 1, 2)
        container_layout.addLayout(grid)
        container_layout.addStretch(1)

        scroll.setWidget(container)
        layout.addWidget(scroll)
        return page

    def _build_settings_defaults_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("settingsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        title = QLabel("全局默认值")
        title.setObjectName("settingsCardTitle")
        set_widget_font_size(title, 18)
        layout.addWidget(title)

        hint = QLabel("这里的配置会作为启动默认值，同时立即同步到当前工作区。")
        hint.setObjectName("settingsHint")
        hint.setWordWrap(True)
        set_widget_font_size(hint, 11)
        layout.addWidget(hint)

        template_label = QLabel("默认模板")
        template_label.setObjectName("metaLabel")
        set_widget_font_size(template_label, 10)
        layout.addWidget(template_label)

        self.settings_template_combo = QComboBox()
        self.settings_template_combo.setObjectName("batchCombo")
        self.settings_template_combo.addItems(self._template_names())
        self.settings_template_combo.currentTextChanged.connect(self._on_settings_template_changed)
        set_widget_font_size(self.settings_template_combo, 12)
        layout.addWidget(self.settings_template_combo)

        self.logo_toggle_button = self._create_settings_toggle(self.logo_enabled_setting)
        self.logo_toggle_button.toggled.connect(self._on_logo_toggle_changed)
        layout.addWidget(
            self._build_settings_toggle_row(
                "默认开启 Logo",
                "关闭后，使用 auto_logo 的模板将不再自动注入品牌 Logo。",
                self.logo_toggle_button,
            )
        )

        self.hardware_toggle_button = self._create_settings_toggle(self.hardware_acceleration_setting)
        self.hardware_toggle_button.toggled.connect(self._on_hardware_acceleration_changed)
        layout.addWidget(
            self._build_settings_toggle_row(
                "硬件加速",
                "当前版本仅保存开关状态，暂不启用硬件加速渲染流程。",
                self.hardware_toggle_button,
            )
        )

        layout.addStretch(1)
        self._sync_settings_template_names()
        return card

    def _build_settings_export_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("settingsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        title = QLabel("导出设置")
        title.setObjectName("settingsCardTitle")
        set_widget_font_size(title, 18)
        layout.addWidget(title)

        hint = QLabel("导出目录和质量会同时影响单图导出，以及后续新发起的批量任务。")
        hint.setObjectName("settingsHint")
        hint.setWordWrap(True)
        set_widget_font_size(hint, 11)
        layout.addWidget(hint)

        output_label = QLabel("导出路径")
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

        self.settings_output_label = QLabel()
        self.settings_output_label.setObjectName("pathBoxLabel")
        self.settings_output_label.setWordWrap(True)
        self.settings_output_label.setTextInteractionFlags(TEXT_SELECTABLE_BY_MOUSE)
        set_widget_font_size(self.settings_output_label, 11)
        output_box_layout.addWidget(self.settings_output_label)
        output_row.addWidget(output_box, 1)

        self.settings_output_button = QPushButton("浏览")
        self.settings_output_button.setObjectName("secondaryButton")
        self.settings_output_button.clicked.connect(self._choose_settings_output_dir)
        set_widget_font_size(self.settings_output_button, 11)
        output_row.addWidget(self.settings_output_button)
        layout.addLayout(output_row)

        quality_row = QHBoxLayout()
        quality_row.setContentsMargins(0, 0, 0, 0)
        quality_row.setSpacing(8)

        quality_label = QLabel("导出质量")
        quality_label.setObjectName("metaLabel")
        set_widget_font_size(quality_label, 10)
        quality_row.addWidget(quality_label, 1, ALIGN_LEFT)

        self.settings_quality_value_label = QLabel()
        self.settings_quality_value_label.setObjectName("qualityValue")
        set_widget_font_size(self.settings_quality_value_label, 12)
        quality_row.addWidget(self.settings_quality_value_label, 0, ALIGN_RIGHT)
        layout.addLayout(quality_row)

        self.settings_quality_slider = QSlider(HORIZONTAL)
        self.settings_quality_slider.setRange(60, 100)
        self.settings_quality_slider.setObjectName("qualitySlider")
        self.settings_quality_slider.valueChanged.connect(self._on_settings_quality_changed)
        layout.addWidget(self.settings_quality_slider)

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

        export_name_hint = QLabel("导出文件名会自动附加模板后缀和质量后缀，例如：IMG_0001_标准水印_Q95.jpg")
        export_name_hint.setObjectName("settingsHint")
        export_name_hint.setWordWrap(True)
        set_widget_font_size(export_name_hint, 11)
        layout.addWidget(export_name_hint)

        layout.addStretch(1)
        self._update_settings_output_label()
        self._set_export_quality(self.export_quality_setting, persist=False)
        return card

    def _build_settings_logo_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("settingsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        title = QLabel("Logo 资源")
        title.setObjectName("settingsCardTitle")
        set_widget_font_size(title, 18)
        layout.addWidget(title)

        hint = QLabel("当前自动 Logo 识别会优先从这些本地资源中匹配相机品牌。")
        hint.setObjectName("settingsHint")
        hint.setWordWrap(True)
        set_widget_font_size(hint, 11)
        layout.addWidget(hint)

        logos_grid = QGridLayout()
        logos_grid.setContentsMargins(0, 0, 0, 0)
        logos_grid.setHorizontalSpacing(14)
        logos_grid.setVerticalSpacing(14)

        logo_files = []
        if logos_dir.exists():
            logo_files = [
                logo_path
                for logo_path in sorted(logos_dir.iterdir(), key=lambda item: item.name.lower())
                if logo_path.suffix.lower() in {".png", ".jpg", ".jpeg"}
            ]
        if not logo_files:
            empty_label = QLabel("未检测到可用 Logo 资源。")
            empty_label.setObjectName("settingsHint")
            set_widget_font_size(empty_label, 11)
            layout.addWidget(empty_label)
            return card

        for index, logo_path in enumerate(logo_files):
            logo_card = QFrame()
            logo_card.setObjectName("settingsLogoCard")
            logo_layout = QVBoxLayout(logo_card)
            logo_layout.setContentsMargins(14, 14, 14, 14)
            logo_layout.setSpacing(12)

            preview = QLabel()
            preview.setObjectName("settingsLogoPreview")
            preview.setAlignment(ALIGN_CENTER)
            preview.setMinimumHeight(52)
            pixmap = QPixmap(str(logo_path))
            if pixmap.isNull():
                preview.setText(logo_path.stem)
            else:
                preview.setPixmap(pixmap.scaled(92, 44, KEEP_ASPECT_RATIO, SMOOTH_TRANSFORMATION))
            logo_layout.addWidget(preview)

            name_label = QLabel(logo_path.stem.replace("_", " "))
            name_label.setObjectName("settingsLogoName")
            name_label.setAlignment(ALIGN_CENTER)
            set_widget_font_size(name_label, 11)
            logo_layout.addWidget(name_label)

            logos_grid.addWidget(logo_card, index // 5, index % 5)

        layout.addLayout(logos_grid)
        return card

    def _build_settings_toggle_row(self, title_text: str, description_text: str, button: QPushButton) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        text_column = QVBoxLayout()
        text_column.setContentsMargins(0, 0, 0, 0)
        text_column.setSpacing(4)

        title = QLabel(title_text)
        title.setObjectName("settingsToggleTitle")
        set_widget_font_size(title, 12)
        text_column.addWidget(title)

        description = QLabel(description_text)
        description.setObjectName("settingsHint")
        description.setWordWrap(True)
        set_widget_font_size(description, 10)
        text_column.addWidget(description)

        layout.addLayout(text_column, 1)
        layout.addWidget(button, 0, ALIGN_RIGHT)
        return row

    def _create_settings_toggle(self, checked: bool) -> QPushButton:
        button = QPushButton()
        button.setObjectName("settingsToggle")
        button.setCheckable(True)
        button.setCursor(POINTING_HAND_CURSOR)
        button.setFixedSize(78, 32)
        button.setChecked(checked)
        button.toggled.connect(lambda state, target=button: self._sync_settings_toggle_text(target, state))
        self._sync_settings_toggle_text(button, checked)
        return button

    def _sync_settings_toggle_text(self, button: QPushButton, checked: bool):
        button.setText("启用" if checked else "关闭")

    def _config_path_value(self, path: str | Path) -> str:
        resolved_path = Path(path).resolve()
        try:
            relative_path = resolved_path.relative_to(PROJECT_ROOT)
            return f"./{relative_path.as_posix()}"
        except ValueError:
            return resolved_path.as_posix()

    def _save_config_value(self, section: str, option: str, value: str):
        config = load_config()
        if section != config.default_section and not config.has_section(section):
            config.add_section(section)
        config.set(section, option, value)
        save_config(config)

    def _update_settings_output_label(self):
        if not hasattr(self, "settings_output_label"):
            return
        resolved, display_text = format_path_for_label(self.output_dir_setting)
        self.settings_output_label.setText(display_text)
        self.settings_output_label.setToolTip(resolved)

    def _set_export_quality(self, value: int, persist: bool = True):
        self.export_quality_setting = int(value)
        if hasattr(self, "settings_quality_slider"):
            self.settings_quality_slider.blockSignals(True)
            self.settings_quality_slider.setValue(self.export_quality_setting)
            self.settings_quality_slider.blockSignals(False)
        if hasattr(self, "settings_quality_value_label"):
            self.settings_quality_value_label.setText(f"{self.export_quality_setting}%")

        if persist:
            self._save_config_value("DEFAULT", "quality", str(self.export_quality_setting))

        if self.batch_page is not None and self.batch_page.batch_thread is None:
            self.batch_page.set_quality(self.export_quality_setting)

        if self.current_mode == "settings":
            self._update_footer_meta(
                self.selected_template or "--",
                Path(self.output_dir_setting).name or "--",
                f"JPEG {self.export_quality_setting}%",
            )

    def _sync_settings_template_names(self):
        if not hasattr(self, "settings_template_combo"):
            return
        template_names = self._template_names()
        self.settings_template_combo.blockSignals(True)
        self.settings_template_combo.clear()
        self.settings_template_combo.addItems(template_names)
        self.settings_template_combo.setEnabled(bool(template_names))
        if self.selected_template in template_names:
            self.settings_template_combo.setCurrentText(self.selected_template)
        self.settings_template_combo.blockSignals(False)

    def _on_settings_template_changed(self, template_name: str):
        if not template_name:
            return
        self._apply_selected_template(template_name, source="settings")
        self._update_status(f"状态：已保存设置 | 默认模板：{template_name}")

    def _on_logo_toggle_changed(self, checked: bool):
        self.logo_enabled_setting = bool(checked)
        self._save_config_value("DEFAULT", "enable_logo", str(self.logo_enabled_setting))
        self.preview_cache.clear()
        if self.current_mode == "settings":
            self._update_footer_meta(
                self.selected_template or "--",
                Path(self.output_dir_setting).name or "--",
                f"JPEG {self.export_quality_setting}%",
            )
        if self.input_path and self.current_mode == "editor":
            self.schedule_preview()
        self._update_status(f"状态：已保存设置 | 自动 Logo：{'启用' if checked else '关闭'}")

    def _on_hardware_acceleration_changed(self, checked: bool):
        self.hardware_acceleration_setting = bool(checked)
        self._save_config_value("DEFAULT", "hardware_acceleration", str(self.hardware_acceleration_setting))
        self._update_status(f"状态：已保存设置 | 硬件加速：{'启用' if checked else '关闭'}（预留）")

    def _on_settings_quality_changed(self, value: int):
        self._set_export_quality(value, persist=True)
        self._update_status(f"状态：已保存设置 | 导出质量：{self.export_quality_setting}%")

    def _choose_settings_output_dir(self):
        chosen_dir = QFileDialog.getExistingDirectory(self, "选择导出目录", self.output_dir_setting)
        if not chosen_dir:
            return

        self.output_dir_setting = str(Path(chosen_dir).resolve())
        self._update_settings_output_label()
        self._save_config_value("DEFAULT", "output_folder", self._config_path_value(self.output_dir_setting))

        if self.batch_page is not None and self.batch_page.batch_thread is None:
            self.batch_page.set_output_dir(self.output_dir_setting)

        if self.current_mode == "settings":
            self._update_footer_meta(
                self.selected_template or "--",
                Path(self.output_dir_setting).name or "--",
                f"JPEG {self.export_quality_setting}%",
            )
        self._update_status(f"状态：已保存设置 | 导出目录：{Path(self.output_dir_setting).name}")

