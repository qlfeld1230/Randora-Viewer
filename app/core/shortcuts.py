"""Common Keyboard Shortcut Key Utility"""

from __future__ import annotations

from typing import Callable, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QWidget


def bind_image_navigation(
    target: QWidget,
    on_prev: Callable[[], None],
    on_next: Callable[[], None],
) -> Tuple[QShortcut, QShortcut]:
    prev_sc = QShortcut(QKeySequence(Qt.Key.Key_Left), target)
    prev_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    prev_sc.activated.connect(on_prev)

    next_sc = QShortcut(QKeySequence(Qt.Key.Key_Right), target)
    next_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    next_sc.activated.connect(on_next)

    return prev_sc, next_sc


def bind_delete(
    target: QWidget,
    on_delete: Callable[[], None],
) -> QShortcut:
    sc = QShortcut(QKeySequence(Qt.Key.Key_Delete), target)
    sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    sc.activated.connect(on_delete)
    return sc
