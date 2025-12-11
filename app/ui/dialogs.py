"""Dialog utilities for keyword management and batch edits."""

from __future__ import annotations

from typing import Iterable

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class KeywordDialog(QDialog):
    """키워드 추가/삭제 다이얼로그."""

    keyword_added = pyqtSignal(str)
    keyword_deleted = pyqtSignal(str)

    def __init__(self, keywords: Iterable[str] | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("키워드 추가")
        self.setMinimumSize(420, 320)
        self._keywords: set[str] = set()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        header = QWidget(self)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        self.list_label = QLabel("현재 키워드", self)
        header_layout.addWidget(self.list_label, 1)
        self.delete_btn = QPushButton("삭제", self)
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._on_delete)
        header_layout.addWidget(self.delete_btn, 0)
        main_layout.addWidget(header)

        self.list_widget = QListWidget(self)
        self.list_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        main_layout.addWidget(self.list_widget, 1)

        input_container = QWidget(self)
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(8)

        self.input = QLineEdit(self)
        self.input.setMinimumHeight(36)
        self.input.setPlaceholderText("키워드를 입력해주세요")
        self.input.textChanged.connect(self._validate_input)
        input_layout.addWidget(self.input, 3)

        self.add_btn = QPushButton("추가", self)
        self.add_btn.setMinimumHeight(36)
        self.add_btn.setEnabled(False)
        self.add_btn.clicked.connect(self._on_add)
        input_layout.addWidget(self.add_btn, 1)

        main_layout.addWidget(input_container)

        self.set_keywords(keywords or [])

    def set_keywords(self, keywords: Iterable[str]) -> None:
        self.list_widget.clear()
        self._keywords = set()
        self.list_widget.addItem("None")
        for kw in keywords:
            cleaned = kw.strip()
            if not cleaned or cleaned.lower() == "none":
                continue
            if cleaned in self._keywords:
                continue
            self._keywords.add(cleaned)
            self.list_widget.addItem(cleaned)
        self._on_selection_changed()

    def _validate_input(self, text: str) -> None:
        stripped = text.strip()
        valid = (
            0 < len(stripped) <= 40
            and stripped.lower() != "none"
            and stripped not in self._keywords
        )
        self.add_btn.setEnabled(valid)

    def _on_add(self) -> None:
        text = self.input.text().strip()
        if (
            not text
            or len(text) > 40
            or text.lower() == "none"
            or text in self._keywords
        ):
            return
        self.keyword_added.emit(text)
        self.list_widget.addItem(text)
        self._keywords.add(text)
        self.input.clear()
        self.add_btn.setEnabled(False)
        self._on_selection_changed()

    def _on_selection_changed(self) -> None:
        item = self.list_widget.currentItem()
        self.delete_btn.setEnabled(bool(item) and item.text() not in ("(키워드 없음)", "None"))

    def _on_delete(self) -> None:
        item = self.list_widget.currentItem()
        if not item:
            return
        text = item.text().strip()
        if not text or text.lower() == "none":
            return
        if text in self._keywords:
            self._keywords.remove(text)
        self.keyword_deleted.emit(text)
        row = self.list_widget.row(item)
        self.list_widget.takeItem(row)
        self._on_selection_changed()


class BatchEditDialog(QDialog):
    """일괄 수정 다이얼로그(UI만)."""

    path_changed = pyqtSignal(str)
    edit_requested = pyqtSignal(str, str)

    def __init__(self, initial_path: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("일괄 수정")
        self.setMinimumSize(460, 200)
        self._current_path = initial_path

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        path_container = QWidget(self)
        path_layout = QHBoxLayout(path_container)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.setSpacing(8)
        self.path_display = QLineEdit(self)
        self.path_display.setReadOnly(True)
        self.path_display.setPlaceholderText("경로를 선택하세요")
        if initial_path:
            self.path_display.setText(initial_path)
        path_layout.addWidget(self.path_display, 1)
        self.path_btn = QPushButton("경로 선택", self)
        self.path_btn.clicked.connect(self._choose_path)
        path_layout.addWidget(self.path_btn, 0)
        layout.addWidget(path_container)

        input_container = QWidget(self)
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(8)

        self.input = QLineEdit(self)
        self.input.setMinimumHeight(36)
        self.input.setPlaceholderText("키워드를 입력해주세요")
        self.input.textChanged.connect(self._validate_input)
        input_layout.addWidget(self.input, 1)

        self.edit_btn = QPushButton("수정", self)
        self.edit_btn.setMinimumHeight(36)
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self._on_edit)
        input_layout.addWidget(self.edit_btn, 0)

        layout.addWidget(input_container)
        self._validate_input("")

    def _choose_path(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "경로 선택", self._current_path or ""
        )
        if directory:
            self._current_path = directory
            self.path_display.setText(directory)
            self.path_changed.emit(directory)
        self._validate_input(self.input.text())

    def _validate_input(self, text: str) -> None:
        stripped = text.strip()
        valid_kw = 0 < len(stripped) <= 40 and stripped.lower() != "none"
        self.edit_btn.setEnabled(valid_kw and bool(self._current_path))

    def _on_edit(self) -> None:
        if not self.edit_btn.isEnabled():
            return
        keyword = self.input.text().strip()
        if not keyword:
            return
        self.edit_requested.emit(keyword, self._current_path)
        self.accept()
