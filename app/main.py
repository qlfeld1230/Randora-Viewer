from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QIcon, QColor, QPalette
from PyQt6.QtWidgets import QApplication, QMainWindow

APP_BACKGROUND = "#2f2d2d"

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

def _apply_base_palette(app: QApplication) -> None:
    """Force a consistent dark background slightly lighter than the status bar."""
    base = QColor(APP_BACKGROUND)
    text = QColor("#f2f2f2")
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, base)
    palette.setColor(QPalette.ColorRole.Base, base)
    palette.setColor(QPalette.ColorRole.AlternateBase, base)
    palette.setColor(QPalette.ColorRole.Button, base)
    palette.setColor(QPalette.ColorRole.WindowText, text)
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.ButtonText, text)
    app.setPalette(palette)


def create_window() -> QMainWindow:
    """Create the main window, falling back to a simple placeholder."""
    from app.ui.main_window import MainWindow  # type: ignore
    window = MainWindow()
    window.resize(1200, 800)
    return window


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Randora Viewer")
    app.setOrganizationName("Randora")
    _set_app_user_model_id("Randora.Viewer")
    _apply_base_palette(app)
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
