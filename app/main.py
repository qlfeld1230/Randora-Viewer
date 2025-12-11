# QApplication을 구성하고 메인 윈도우를 구동하는 런처 모듈

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMainWindow

# On Windows, set a custom AppUserModelID so the taskbar uses our icon.
def _set_app_user_model_id(app_id: str) -> None:
    if sys.platform.startswith("win"):
        try:
            import ctypes  # noqa: PLC0415

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            # Non-Windows or older versions can safely ignore.
            pass

def load_styles(app: QApplication) -> None:
    """Load optional QSS stylesheet if present."""
    style_path = Path(__file__).resolve().parent / "resources" / "styles.qss"
    if style_path.exists():
        app.setStyleSheet(style_path.read_text(encoding="utf-8"))


def create_window() -> QMainWindow:
    """Create the main window, falling back to a simple placeholder."""
    try:
        from app.ui.main_window import MainWindow  # type: ignore
    except Exception:
        class MainWindow(QMainWindow):
            def __init__(self) -> None:
                super().__init__()
                self.setWindowTitle("Randora Viewer (placeholder)")

    window = MainWindow()
    window.resize(1200, 800)
    return window


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Randora Viewer")
    app.setOrganizationName("Randora")
    _set_app_user_model_id("Randora.Viewer")
    icons_dir = Path(__file__).resolve().parent / "resources" / "icons"
    icon_path = icons_dir / "Randora.ico"
    if not icon_path.exists():
        icon_path = icons_dir / "Randora.png"
    app.setWindowIcon(QIcon(str(icon_path)))

    load_styles(app)
    window = create_window()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
