"""Thin wrapper around QSettings for app preferences"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSettings


def _settings() -> QSettings:
    return QSettings()


def get_last_folder() -> Path | None:
    value = _settings().value("last_folder", "", str)
    if value:
        return Path(value)
    return None


def set_last_folder(path: Path) -> None:
    _settings().setValue("last_folder", str(path))


def get_last_keyword() -> str:
    return _settings().value("last_keyword", "", str)


def set_last_keyword(keyword: str) -> None:
    _settings().setValue("last_keyword", keyword)
