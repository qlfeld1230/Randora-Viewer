"""설정/정보/다이얼로그 UI 모음 (UI 스켈레톤만)."""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton


class SettingsDialog(QDialog):
    """설정 다이얼로그: 키워드 추가/일괄 수정 버튼만 포함(UI 스켈레톤)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        layout = QVBoxLayout(self)
        self.add_keyword_btn = QPushButton("키워드 추가", self)
        self.batch_edit_btn = QPushButton("일괄 수정", self)
        layout.addWidget(self.add_keyword_btn)
        layout.addWidget(self.batch_edit_btn)
