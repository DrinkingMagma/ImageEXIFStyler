from __future__ import annotations

import traceback

from core.logger import logger
from core.template_inputs import (
    format_template_display_name,
    get_template_input_specs,
    get_template_inputs,
    save_template_inputs,
    validate_template_input,
)
from core.util import create_template, get_template_content
from UI.shared.dialogs import prompt_text, show_error, show_info, show_warning
from UI.shared.qt import (
    ALIGN_RIGHT,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from UI.shared.utils import set_widget_font_size
from UI.template_library.widgets import CreateTemplateCard, TemplateLibraryCard


class TemplateLibraryPageMixin:
    def _refresh_library_template_titles(self):
        for card in getattr(self, "template_library_cards", {}).values():
            card.refresh_title()
        self._update_template_library_meta()

    def _edit_template_inputs(self, template_name: str) -> bool:
        specs = get_template_input_specs(template_name)
        if not specs:
            return True

        values = get_template_inputs(template_name)
        for spec in specs:
            while True:
                text, accepted = prompt_text(
                    self,
                    spec.dialog_title,
                    spec.dialog_prompt,
                    values.get(spec.key, spec.default),
                )
                if not accepted:
                    return False

                normalized = text.strip()
                is_valid, error_message = validate_template_input(spec, normalized)
                if not is_valid:
                    show_warning(self, "输入无效", error_message)
                    continue

                values[spec.key] = normalized
                break

        save_template_inputs(template_name, values)
        if hasattr(self, "preview_cache"):
            self.preview_cache.clear()
        if hasattr(self, "displayed_preview_template"):
            self.displayed_preview_template = None
        self._refresh_library_template_titles()
        return True

    def _build_template_library_page(self) -> QWidget:
        page = QFrame()
        page.setObjectName("templateLibraryPage")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("templateLibraryScroll")

        container = QWidget()
        container.setObjectName("templateLibraryContent")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(42, 38, 42, 58)
        container_layout.setSpacing(34)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(24)

        title_column = QVBoxLayout()
        title_column.setContentsMargins(0, 0, 0, 0)
        title_column.setSpacing(10)

        title = QLabel("模板库")
        title.setObjectName("templateLibraryHeading")
        set_widget_font_size(title, 32)
        title_column.addWidget(title)

        subtitle = QLabel("选择专业的 EXIF 边框模板，也可以直接从这里创建自定义模板。")
        subtitle.setObjectName("templateLibrarySubtitle")
        set_widget_font_size(subtitle, 13)
        title_column.addWidget(subtitle)
        header_layout.addLayout(title_column, 1)

        self.template_library_meta_label = QLabel()
        self.template_library_meta_label.setObjectName("templateLibraryMeta")
        self.template_library_meta_label.setAlignment(ALIGN_RIGHT)
        set_widget_font_size(self.template_library_meta_label, 12)
        header_layout.addWidget(self.template_library_meta_label, 0, ALIGN_RIGHT)
        container_layout.addWidget(header)

        self.template_library_grid = QGridLayout()
        self.template_library_grid.setContentsMargins(0, 0, 0, 0)
        self.template_library_grid.setHorizontalSpacing(32)
        self.template_library_grid.setVerticalSpacing(34)
        self._populate_template_library_grid()
        container_layout.addLayout(self.template_library_grid)
        container_layout.addStretch(1)

        scroll.setWidget(container)
        layout.addWidget(scroll)
        self._update_template_library_meta()
        return page

    def _populate_template_library_grid(self):
        self._clear_grid_layout(self.template_library_grid)
        self.template_library_cards = {}

        for index, spec in enumerate(self.template_specs):
            card = TemplateLibraryCard(spec)
            card.clicked.connect(self._on_library_template_selected)
            card.edit_requested.connect(self._on_library_template_edit_requested)
            card.set_selected(spec.name == self.selected_template)
            self.template_library_cards[spec.name] = card
            self.template_library_grid.addWidget(card, index // 2, index % 2)

        create_card = CreateTemplateCard()
        create_card.clicked.connect(self._create_custom_template)
        create_row = (len(self.template_specs) + 1) // 2
        self.template_library_grid.addWidget(create_card, create_row, 0, 1, 2)
        self.create_template_card = create_card

    def _sync_library_template_cards(self, template_name: str):
        for card_name, card in self.template_library_cards.items():
            card.refresh_title()
            card.set_selected(card_name == template_name)
        self._update_template_library_meta()

    def _update_template_library_meta(self):
        if not hasattr(self, "template_library_meta_label"):
            return
        template_count = len(self.template_specs)
        current_text = format_template_display_name(self.selected_template) if self.selected_template else "无可用模板"
        self.template_library_meta_label.setText(f"共 {template_count} 个模板\n当前：{current_text}")

    def _normalize_template_name(self, raw_name: str) -> str:
        template_name = raw_name.strip()
        if template_name.lower().endswith(".json"):
            template_name = template_name[:-5].strip()
        return template_name

    def _is_valid_template_name(self, template_name: str) -> bool:
        invalid_chars = set('\\/:*?"<>|')
        return bool(template_name) and template_name not in {".", ".."} and not any(
            char in invalid_chars for char in template_name
        )

    def _create_custom_template(self):
        if not self.selected_template:
            show_warning(self, "无法创建模板", "当前没有可复制的模板。")
            return

        base_template = self.selected_template
        default_name = f"{base_template} 副本"
        template_name, accepted = prompt_text(
            self,
            "创建自定义模板",
            "新模板名称（将基于当前模板复制）：",
            default_name,
        )
        if not accepted:
            return

        template_name = self._normalize_template_name(template_name)
        if not self._is_valid_template_name(template_name):
            show_warning(self, "模板名称无效", "模板名称不能为空，且不能包含 \\ / : * ? \" < > |。")
            return

        try:
            base_content = get_template_content(base_template)
            create_template(template_name, base_content)
        except FileExistsError:
            show_warning(self, "模板已存在", f"模板“{template_name}”已经存在。")
            return
        except Exception as exc:
            logger.error(traceback.format_exc())
            show_error(self, "创建失败", str(exc))
            return

        self._reload_template_specs(select_template=template_name)
        self._update_status(f"状态：已创建自定义模板 | {template_name}")
        show_info(self, "创建完成", f"已基于“{base_template}”创建“{template_name}”。")

    def _on_library_template_edit_requested(self, template_name: str):
        if not self._edit_template_inputs(template_name):
            self._update_status(f"状态：已取消自定义文字修改 | {template_name}")
            return
        self._update_status(f"状态：已更新自定义文字 | {format_template_display_name(template_name)}")

    def _on_library_template_selected(self, template_name: str):
        self._apply_selected_template(template_name, source="templates")
        self._update_status(f"状态：已选择模板 | {format_template_display_name(template_name)}")
