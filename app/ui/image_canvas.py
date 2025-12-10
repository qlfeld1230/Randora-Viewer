"""Central image display widget."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QSizePolicy, QWidget


class ImageCanvas(QLabel):
    """Displays the currently selected image, scaled to fit."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._source: QPixmap | None = None
        self._current_path: Path | None = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(QSize(200, 200))
        # Use the window palette color so letterbox areas blend with the app background.
        self.setStyleSheet("background: palette(window); color: #888;")
        self.setText("이미지를 선택하세요")

    def show_image(self, path: Path) -> None:
        """Load image from disk and display it."""
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self.setText("이미지를 불러올 수 없습니다")
            self._source = None
            self._current_path = None
            return
        self._source = pixmap
        self._current_path = path
        self._update_scaled()

    def clear_image(self) -> None:
        self._source = None
        self._current_path = None
        self.setText("이미지가 없습니다")
        self.setPixmap(QPixmap())

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_scaled()

    def _update_scaled(self) -> None:
        if not self._source:
            return
        scaled = self._source.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,  # fit whole image; may add letterboxing
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)

    @property
    def source_size(self) -> QSize | None:
        return self._source.size() if self._source else None

    @property
    def current_path(self) -> Path | None:
        return self._current_path
