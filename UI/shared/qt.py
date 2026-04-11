from __future__ import annotations

try:
    from PySide6.QtCore import QEvent, QObject, QPoint, QSize, Qt, QThread, QTimer, Signal
    from PySide6.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPen, QPixmap
    from PySide6.QtWidgets import (
        QApplication,
        QButtonGroup,
        QComboBox,
        QDialog,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QInputDialog,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QSlider,
        QSizePolicy,
        QStackedWidget,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )

    QT_BINDING = "PySide6"
except ImportError:
    from PyQt5.QtCore import QEvent, QObject, QPoint, QSize, Qt, QThread, QTimer, pyqtSignal as Signal
    from PyQt5.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPen, QPixmap
    from PyQt5.QtWidgets import (
        QApplication,
        QButtonGroup,
        QComboBox,
        QDialog,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QInputDialog,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QSlider,
        QSizePolicy,
        QStackedWidget,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )

    QT_BINDING = "PyQt5"

if hasattr(Qt, "AlignmentFlag"):
    ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
    ALIGN_LEFT = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    ALIGN_RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    ALIGN_TOP = Qt.AlignmentFlag.AlignTop
    KEEP_ASPECT_RATIO = Qt.AspectRatioMode.KeepAspectRatio
    SMOOTH_TRANSFORMATION = Qt.TransformationMode.SmoothTransformation
    TOOL_BUTTON_TEXT_UNDER_ICON = Qt.ToolButtonStyle.ToolButtonTextUnderIcon
    POINTING_HAND_CURSOR = Qt.CursorShape.PointingHandCursor
    LEFT_MOUSE_BUTTON = Qt.MouseButton.LeftButton
    NO_PEN = Qt.PenStyle.NoPen
    ROUND_CAP = Qt.PenCapStyle.RoundCap
    TEXT_SELECTABLE_BY_MOUSE = Qt.TextInteractionFlag.TextSelectableByMouse
    PLAIN_TEXT = Qt.TextFormat.PlainText
    SCROLLBAR_ALWAYS_OFF = Qt.ScrollBarPolicy.ScrollBarAlwaysOff
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
    TOOL_BUTTON_TEXT_UNDER_ICON = Qt.ToolButtonTextUnderIcon
    POINTING_HAND_CURSOR = Qt.PointingHandCursor
    LEFT_MOUSE_BUTTON = Qt.LeftButton
    NO_PEN = Qt.NoPen
    ROUND_CAP = Qt.RoundCap
    TEXT_SELECTABLE_BY_MOUSE = Qt.TextSelectableByMouse
    PLAIN_TEXT = Qt.PlainText
    SCROLLBAR_ALWAYS_OFF = Qt.ScrollBarAlwaysOff
    HORIZONTAL = Qt.Horizontal
    FRAMELESS_WINDOW_HINT = Qt.FramelessWindowHint
    DIALOG_WINDOW_TYPE = Qt.Dialog
    TRANSLUCENT_BACKGROUND = Qt.WA_TranslucentBackground
