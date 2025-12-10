"""Sidebar widget that lists image files and emits selection changes."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QVBoxLayout, QWidget


class Sidebar(QWidget):
    """Simple list of images in the selected folder."""

    image_selected = pyqtSignal(Path)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._list = QListWidget(self)
        self._list.itemSelectionChanged.connect(self._emit_selection)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self._list)

    def set_images(self, images: Iterable[Path]) -> None:
        """Populate the list with image paths."""
        self._list.clear()
        for path in images:
            item = QListWidgetItem(path.name)
            item.setData(256, path)  # Qt.UserRole
            self._list.addItem(item)
        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    def _emit_selection(self) -> None:
        item = self._list.currentItem()
        if item:
            path = item.data(256)
            if isinstance(path, Path):
                self.image_selected.emit(path)
