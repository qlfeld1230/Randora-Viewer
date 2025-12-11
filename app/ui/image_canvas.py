"""Central image display widget."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QMouseEvent
from PyQt6.QtWidgets import (
    QLabel,
    QSizePolicy,
    QWidget,
    QStyle,
    QStyleOption,
    QStylePainter,
)


class ImageCanvas(QLabel):
    """Displays the currently selected image, scaled to fit."""

    request_open = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._source: QPixmap | None = None
        self._scaled: QPixmap | None = None
        self._current_path: Path | None = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(QSize(200, 200))
        # Use the window palette color so letterbox areas blend with the app background.
        self.setStyleSheet("background: palette(window); color: #888;")
        self.setText("이미지를 선택하세요")
        self.setContentsMargins(0, 0, 0, 0)
        self.setMargin(0)

    def show_image(self, path: Path) -> None:
        """Load image from disk and display it."""
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self.setText("이미지를 불러올 수 없습니다")
            self._source = None
            self._scaled = None
            self._current_path = None
            self.update()
            return
        self._source = pixmap
        self._current_path = path
        self._update_scaled()

    def clear_image(self) -> None:
        self._source = None
        self._scaled = None
        self._current_path = None
        self.setText("이미지가 없습니다")
        self.update()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if (
            isinstance(event, QMouseEvent)
            and event.button() == Qt.MouseButton.LeftButton
            and self._source is None
        ):
            self.request_open.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_scaled()

    def _update_scaled(self) -> None:
        if not self._source:
            return
        available = self.contentsRect().size()
        if available.width() <= 0 or available.height() <= 0:
            return
        self._scaled = self._source.scaled(
            available,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setText("")
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QStylePainter(self)
        painter.drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt)

        if self._scaled:
            rect = self.contentsRect()
            x = rect.x() + (rect.width() - self._scaled.width()) // 2
            y = rect.y() + (rect.height() - self._scaled.height()) // 2
            painter.drawPixmap(x, y, self._scaled)
            return

        super().paintEvent(event)

    @property
    def source_size(self) -> QSize | None:
        return self._source.size() if self._source else None

    @property
    def current_path(self) -> Path | None:
        return self._current_path
