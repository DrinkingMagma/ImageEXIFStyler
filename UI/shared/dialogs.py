from __future__ import annotations

from typing import Optional

from UI.shared.qt import (
    ALIGN_LEFT,
    ALIGN_RIGHT,
    DIALOG_WINDOW_TYPE,
    FRAMELESS_WINDOW_HINT,
    LEFT_MOUSE_BUTTON,
    POINTING_HAND_CURSOR,
    TRANSLUCENT_BACKGROUND,
    QDialog,
    QEvent,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPoint,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from UI.shared.utils import event_global_pos, set_widget_font_size


def _dialog_accepted_value() -> int:
    dialog_code = getattr(QDialog, "DialogCode", None)
    if dialog_code is not None and hasattr(dialog_code, "Accepted"):
        return int(dialog_code.Accepted)
    return int(QDialog.Accepted)


class AppDialog(QDialog):
    _STYLESHEET = """
        QDialog#appDialog {
            background: transparent;
        }
        QFrame#appDialogPanel {
            background: #0f1011;
            border: 1px solid rgba(71, 72, 72, 0.24);
            border-radius: 12px;
        }
        QFrame#appDialogHeader {
            background: transparent;
            border: none;
        }
        QLabel#appDialogTitle {
            color: #f4f4f5;
            font-weight: 800;
        }
        QPushButton#appDialogCloseButton {
            min-width: 28px;
            max-width: 28px;
            min-height: 28px;
            max-height: 28px;
            border: none;
            border-radius: 8px;
            background: transparent;
            color: #8f959c;
            font-weight: 800;
        }
        QPushButton#appDialogCloseButton:hover {
            background: #241717;
            color: #ffe6e5;
        }
        QPushButton#appDialogCloseButton:pressed {
            background: #491719;
        }
        QLabel#appDialogBadge {
            padding: 4px 10px;
            border-radius: 999px;
            font-weight: 800;
            letter-spacing: 1px;
        }
        QLabel#appDialogBadge[kind="info"] {
            background: rgba(163, 201, 255, 0.12);
            color: #a3c9ff;
        }
        QLabel#appDialogBadge[kind="warning"] {
            background: rgba(255, 211, 127, 0.12);
            color: #ffd37f;
        }
        QLabel#appDialogBadge[kind="error"] {
            background: rgba(238, 125, 119, 0.12);
            color: #ee7d77;
        }
        QLabel#appDialogText,
        QLabel#appDialogPrompt {
            color: #b7bcc3;
            line-height: 1.45;
        }
        QLineEdit#appDialogInput {
            min-height: 42px;
            border-radius: 8px;
            padding: 0 14px;
            background: #141515;
            color: #f4f4f5;
            border: 1px solid rgba(163, 201, 255, 0.35);
            selection-background-color: #3c628a;
        }
        QLineEdit#appDialogInput:focus {
            border: 1px solid rgba(163, 201, 255, 0.7);
        }
        QPushButton#appDialogSecondaryButton,
        QPushButton#appDialogPrimaryButton {
            min-height: 40px;
            border-radius: 8px;
            border: none;
            padding: 0 16px;
            font-weight: 800;
        }
        QPushButton#appDialogSecondaryButton {
            background: #252626;
            color: #e7e5e5;
        }
        QPushButton#appDialogSecondaryButton:hover {
            background: #2b2c2c;
        }
        QPushButton#appDialogSecondaryButton:pressed {
            background: #1f2020;
        }
        QPushButton#appDialogPrimaryButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #a3c9ff, stop:1 #004883);
            color: #e7f1ff;
        }
        QPushButton#appDialogPrimaryButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #bcd6ff, stop:1 #0a5ea8);
        }
        QPushButton#appDialogPrimaryButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #86b8ff, stop:1 #07497f);
        }
    """

    def __init__(self, title: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._drag_offset: Optional[QPoint] = None

        self.setObjectName("appDialog")
        self.setModal(True)
        self.setAttribute(TRANSLUCENT_BACKGROUND, True)
        self.setWindowFlags(DIALOG_WINDOW_TYPE | FRAMELESS_WINDOW_HINT)
        self.setMinimumWidth(420)
        self.setStyleSheet(self._STYLESHEET)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(0)

        self.panel = QFrame()
        self.panel.setObjectName("appDialogPanel")
        root_layout.addWidget(self.panel)

        self.panel_layout = QVBoxLayout(self.panel)
        self.panel_layout.setContentsMargins(20, 18, 20, 18)
        self.panel_layout.setSpacing(16)

        self.header = QFrame()
        self.header.setObjectName("appDialogHeader")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("appDialogTitle")
        set_widget_font_size(self.title_label, 15)
        header_layout.addWidget(self.title_label, 1, ALIGN_LEFT)

        self.close_button = QPushButton("X")
        self.close_button.setObjectName("appDialogCloseButton")
        self.close_button.setCursor(POINTING_HAND_CURSOR)
        self.close_button.clicked.connect(self.reject)
        header_layout.addWidget(self.close_button, 0, ALIGN_RIGHT)
        self.panel_layout.addWidget(self.header)

        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(14)
        self.panel_layout.addLayout(self.body)

        self.footer = QHBoxLayout()
        self.footer.setContentsMargins(0, 0, 0, 0)
        self.footer.setSpacing(10)
        self.footer.addStretch(1)
        self.panel_layout.addLayout(self.footer)

        self.header.installEventFilter(self)
        self.title_label.installEventFilter(self)

    def add_button(self, text: str, *, primary: bool, on_click):
        button = QPushButton(text)
        button.setObjectName("appDialogPrimaryButton" if primary else "appDialogSecondaryButton")
        button.setCursor(POINTING_HAND_CURSOR)
        set_widget_font_size(button, 12)
        button.clicked.connect(on_click)
        self.footer.addWidget(button, 0, ALIGN_RIGHT)
        return button

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
        if watched not in {self.header, self.title_label}:
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

    def exec_modal(self) -> int:
        if hasattr(self, "exec"):
            return int(self.exec())
        return int(self.exec_())


class AppMessageDialog(AppDialog):
    def __init__(self, title: str, message: str, kind: str, parent: Optional[QWidget] = None):
        super().__init__(title, parent)

        badge = QLabel(kind.upper())
        badge.setObjectName("appDialogBadge")
        badge.setProperty("kind", kind)
        set_widget_font_size(badge, 10)
        self.body.addWidget(badge, 0, ALIGN_LEFT)

        message_label = QLabel(message)
        message_label.setObjectName("appDialogText")
        message_label.setWordWrap(True)
        set_widget_font_size(message_label, 11)
        self.body.addWidget(message_label)

        ok_button = self.add_button("确定", primary=True, on_click=self.accept)
        ok_button.setDefault(True)


class AppTextInputDialog(AppDialog):
    def __init__(
        self,
        title: str,
        prompt: str,
        text: str = "",
        parent: Optional[QWidget] = None,
        accept_text: str = "确定",
        cancel_text: str = "取消",
    ):
        super().__init__(title, parent)

        prompt_label = QLabel(prompt)
        prompt_label.setObjectName("appDialogPrompt")
        prompt_label.setWordWrap(True)
        set_widget_font_size(prompt_label, 11)
        self.body.addWidget(prompt_label)

        self.input = QLineEdit(text)
        self.input.setObjectName("appDialogInput")
        set_widget_font_size(self.input, 12)
        self.input.selectAll()
        self.input.returnPressed.connect(self.accept)
        self.body.addWidget(self.input)

        self.cancel_button = self.add_button(cancel_text, primary=False, on_click=self.reject)
        self.confirm_button = self.add_button(accept_text, primary=True, on_click=self.accept)
        self.confirm_button.setDefault(True)

    def text_value(self) -> str:
        return self.input.text()


def show_info(parent: Optional[QWidget], title: str, message: str) -> None:
    AppMessageDialog(title, message, "info", parent).exec_modal()


def show_warning(parent: Optional[QWidget], title: str, message: str) -> None:
    AppMessageDialog(title, message, "warning", parent).exec_modal()


def show_error(parent: Optional[QWidget], title: str, message: str) -> None:
    AppMessageDialog(title, message, "error", parent).exec_modal()


def prompt_text(
    parent: Optional[QWidget],
    title: str,
    prompt: str,
    text: str = "",
    *,
    accept_text: str = "确定",
    cancel_text: str = "取消",
) -> tuple[str, bool]:
    dialog = AppTextInputDialog(
        title,
        prompt,
        text=text,
        parent=parent,
        accept_text=accept_text,
        cancel_text=cancel_text,
    )
    accepted = dialog.exec_modal() == _dialog_accepted_value()
    return dialog.text_value(), accepted
