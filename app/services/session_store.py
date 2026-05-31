"""Save Session State/Load Utilities"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict


class SessionState(TypedDict, total=False):
    last_folder: str
    open_path: str
    sort_mode: str
    sort_ascending: bool
    last_keyword: str
    batch_path: str


_STATE_FILE = Path(__file__).resolve().parent.parent / "resources" / "session.json"

_DEFAULT: SessionState = {
    "last_folder": "",
    "open_path": "",
    "sort_mode": "date",
    "sort_ascending": False,
    "last_keyword": "",
    "batch_path": "",
}


def load_session() -> SessionState:
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not _STATE_FILE.exists():
            _STATE_FILE.write_text(json.dumps(_DEFAULT, ensure_ascii=False, indent=2), encoding="utf-8")
            return dict(_DEFAULT)
        data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return dict(_DEFAULT)
        state: SessionState = dict(_DEFAULT)
        state.update({k: v for k, v in data.items() if k in _DEFAULT})
        return state
    except Exception:
        return dict(_DEFAULT)


def save_session(state: SessionState) -> None:
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        merged: SessionState = dict(_DEFAULT)
        merged.update({k: v for k, v in state.items() if k in _DEFAULT})
        _STATE_FILE.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
