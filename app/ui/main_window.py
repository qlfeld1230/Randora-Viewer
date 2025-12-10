"""Main application window."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QFontMetrics, QIcon
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QGraphicsOpacityEffect,
    QSizePolicy,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.services import settings
from app.services.fs_service import list_images
from app.ui.image_canvas import ImageCanvas


class MainWindow(QMainWindow):
    """Main viewer window with toolbar, navigation controls, and image canvas."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Randora Viewer")
        self._icons_dir = Path(__file__).resolve(
        ).parent.parent / "resources" / "icons"
        self.canvas = ImageCanvas(self)
        self.nav_container = NavigationContainer(self.canvas, self._icons_dir)
        self._last_folder: Path | None = settings.get_last_folder()
        self._info_font_size = 10
        self._status_icon_size = 18  # temporary, recalculated in _create_statusbar
        self._statusbar_height = 45
        self._images: list[Path] = []
        self._current_index: int = 0

        self._create_actions()
        self._create_toolbar()
        self._create_statusbar()
        self._init_layout()
        # Set a generous default viewer size to minimize letterboxing on load.
        self.resize(2560, 1440)

        self.nav_container.request_prev.connect(self._show_prev_image)
        self.nav_container.request_next.connect(self._show_next_image)

    def _create_actions(self) -> None:
        folder_icon = QIcon(str(self._icon_path("folder icon.png")))
        self.open_folder_action = QAction(folder_icon, "open", self)
        self.open_folder_action.triggered.connect(self._on_open_folder)

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("Main Toolbar", self)
        self.toolbar = toolbar
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toolbar.setIconSize(QSize(14, 14))
        toolbar.setStyleSheet(
            """
            QToolBar { border: 0px; background: transparent; spacing: 4px; }
            QToolButton {
                min-height: 0px;
                padding: 2px 4px;
                qproperty-iconSize: 14px 14px;
            }
            """
        )
        spacer = QWidget(self)
        spacer.setFixedWidth(6)  # manual left gap
        spacer.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        toolbar.addWidget(spacer)
        toolbar.addAction(self.open_folder_action)
        self.addToolBar(toolbar)

    def _create_statusbar(self) -> None:
        status = QStatusBar(self)
        status.setSizeGripEnabled(False)
        status.setStyleSheet(
            "QStatusBar { background: #282727; } QStatusBar::item { border: 0px; }")

        self.info_label = QLabel("", self)
        font = QFont()
        font.setPointSize(self._info_font_size)
        self.info_label.setFont(font)
        metrics = QFontMetrics(font)
        self._status_icon_size = min(max(metrics.height(), 16), 20)
        scaled_icon_size = int(self._status_icon_size * 1.5)
        self._statusbar_height = max(45, scaled_icon_size + 12)
        status.setMinimumHeight(self._statusbar_height)

        self.info_label.setStyleSheet("color: #bbb;")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setTextFormat(Qt.TextFormat.RichText)
        status.addPermanentWidget(self.info_label, 1)
        self._set_info_placeholder()

        icon_size = QSize(self._status_icon_size, self._status_icon_size)
        pad = int(6 * 1.5)
        sep_container = QWidget(self)
        sep_layout = QVBoxLayout(sep_container)
        sep_layout.setContentsMargins(pad, 0, pad, 0)
        sep_layout.setSpacing(0)
        self.fullscreen_separator = QLabel("|", sep_container)
        self.fullscreen_separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.fullscreen_separator.setStyleSheet(
            f"color: #555; font-size: {scaled_icon_size}px;"
        )
        sep_layout.addStretch(1)
        sep_layout.addWidget(self.fullscreen_separator,
                             alignment=Qt.AlignmentFlag.AlignCenter)
        sep_layout.addStretch(2)
        status.addPermanentWidget(sep_container)

        fullscreen_size = QSize(scaled_icon_size, scaled_icon_size)
        self.fullscreen_icon = ClickableIcon(self._icon_path(
            "full screen icon.png"), fullscreen_size, self)
        self.fullscreen_icon.setToolTip("전체화면")
        self.fullscreen_icon.clicked.connect(self.toggle_fullscreen)
        status.addPermanentWidget(self.fullscreen_icon)
        spacer = QLabel(" ", self)
        spacer.setMinimumWidth(6)
        status.addPermanentWidget(spacer)

        self.setStatusBar(status)

    def _init_layout(self) -> None:
        self.setCentralWidget(self.nav_container)

    def _on_open_folder(self) -> None:
        start_dir = str(self._last_folder) if self._last_folder else ""

        dialog = QFileDialog(self, "폴더 또는 이미지 선택", start_dir)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        dialog.setNameFilters(
            ["이미지 파일 (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff)", "모든 파일 (*)"])

        if not dialog.exec():
            return

        selected = dialog.selectedFiles()
        if not selected:
            return

        first = Path(selected[0])
        selected_image: Path | None = None
        if first.is_dir():
            folder = first
        else:
            folder = first.parent
            selected_image = first

        try:
            images = list_images(folder, recursive=True)
        except Exception as exc:  # pragma: no cover - UI path
            self._show_status(f"폴더를 읽을 수 없습니다: {exc}")
            return

        if not images:
            self._images = []
            self.canvas.clear_image()
            self._set_info_placeholder()
            self._update_nav_buttons()
            self._show_status("이미지가 없습니다")
            return

        target = None
        if selected_image:
            selected_resolved = selected_image.resolve()
            for idx, img in enumerate(images):
                if img.resolve() == selected_resolved:
                    target = img
                    self._current_index = idx
                    break
        if target is None:
            target = images[0]
            self._current_index = 0

        self._images = images
        self._show_image_at_index(self._current_index)
        self._last_folder = folder
        settings.set_last_folder(self._last_folder)
        self._show_status(f"{len(images)}개 이미지 로드")

    def _show_image_at_index(self, index: int) -> None:
        if not self._images:
            return
        index = max(0, min(index, len(self._images) - 1))
        self._current_index = index
        path = self._images[self._current_index]
        self.canvas.show_image(path)
        self._update_image_info(path)
        self._update_nav_buttons()

    def _show_prev_image(self) -> None:
        if self._current_index > 0:
            self._show_image_at_index(self._current_index - 1)

    def _show_next_image(self) -> None:
        if self._images and self._current_index < len(self._images) - 1:
            self._show_image_at_index(self._current_index + 1)

    def _update_nav_buttons(self) -> None:
        has_prev = self._current_index > 0
        has_next = self._images and self._current_index < len(self._images) - 1
        self.nav_container.set_enabled(has_prev, has_next)

    def _show_status(self, text: str) -> None:
        status: QStatusBar | None = self.statusBar()
        if status:
            status.showMessage(text, 3000)
        else:
            print(text)

    def _update_image_info(self, path: Path) -> None:
        size = self.canvas.source_size
        if not size:
            self._set_info_placeholder()
            return
        resolution = f"{size.width()} x {size.height()}"
        file_size = self._format_size(path.stat().st_size)
        self.info_label.setText(self._info_html(resolution, file_size))

    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            if hasattr(self, "toolbar"):
                self.toolbar.show()
            self.fullscreen_icon.setToolTip("전체화면")
        else:
            self.showFullScreen()
            if hasattr(self, "toolbar"):
                self.toolbar.hide()
            self.fullscreen_icon.setToolTip("전체화면 해제")

    def _set_info_placeholder(self) -> None:
        self.info_label.setText(self._info_html("0000 x 0000", "0B"))

    def _info_html(self, resolution: str, file_size: str) -> str:
        size = max(int(self._status_icon_size / 1.5), 12)
        res_icon = self._icon_path("resolution icon.png")
        file_icon = self._icon_path("file icon.png")
        return (
            f'<img src="{res_icon}" width="{size}" height="{size}" />&nbsp;{resolution}'
            f'&nbsp;&nbsp;<img src="{file_icon}" width="{size}" height="{size}" />&nbsp;{file_size}'
        )

    def _icon_path(self, name: str) -> Path:
        return self._icons_dir / name

    @staticmethod
    def _format_size(num_bytes: int) -> str:
        step = 1024
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(num_bytes)
        for unit in units:
            if size < step:
                return f"{size:.2f}{unit}" if unit != "B" else f"{int(size)}B"
            size /= step
        return f"{size:.2f}PB"


class NavigationContainer(QWidget):
    """Wraps the canvas with fixed side rails; buttons reveal on hover."""

    request_prev = pyqtSignal()
    request_next = pyqtSignal()

    def __init__(self, canvas: ImageCanvas, icons_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.canvas = canvas
        self.setMouseTracking(True)
        self._side_width = 60
        self._side_padding = 17
        self._fade_duration = 200
        self._anims: list[QPropertyAnimation] = []
        self._icons_dir = icons_dir

        self.prev_btn = self._make_nav_icon(self._icons_dir / "left icon.png")
        self.next_btn = self._make_nav_icon(self._icons_dir / "right icon.png")
        self.prev_btn.clicked.connect(self.request_prev.emit)
        self.next_btn.clicked.connect(self.request_next.emit)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.prev_panel = self._make_side_panel(self.prev_btn, align_left=True)
        self.next_panel = self._make_side_panel(
            self.next_btn, align_left=False)

        layout.addWidget(self.prev_panel)
        layout.addWidget(self.canvas, 1)
        layout.addWidget(self.next_panel)

        # Initialize hidden with 0 opacity.
        self._set_buttons_visible(False, instant=True)

    def _make_nav_icon(self, icon_path: Path) -> "NavIcon":
        icon_size = QSize(40, 40)
        btn = NavIcon(icon_path, icon_size, self)
        btn.setFixedWidth(self._side_width - 2 * self._side_padding)
        return btn

    def _make_side_panel(self, button: "NavIcon", *, align_left: bool) -> QWidget:
        panel = QWidget(self)
        panel.setFixedWidth(self._side_width)
        panel.setStyleSheet("background: transparent;")
        vbox = QVBoxLayout(panel)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hbox = QHBoxLayout()
        if align_left:
            hbox.setContentsMargins(self._side_padding, 0, 0, 0)
        else:
            hbox.setContentsMargins(0, 0, self._side_padding, 0)
        hbox.setSpacing(0)
        if align_left:
            hbox.addWidget(
                button, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            hbox.addStretch(1)
        else:
            hbox.addStretch(1)
            hbox.addWidget(
                button, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        vbox.addStretch(1)
        vbox.addLayout(hbox)
        vbox.addStretch(1)
        return panel

    def set_enabled(self, has_prev: bool, has_next: bool) -> None:
        self.prev_btn.set_enabled(has_prev)
        self.next_btn.set_enabled(has_next)

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._set_buttons_visible(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._set_buttons_visible(False)
        super().leaveEvent(event)

    def _set_buttons_visible(self, visible: bool, instant: bool = False) -> None:
        if visible:
            self._fade_buttons(show=True, instant=instant)
        else:
            self._fade_buttons(show=False, instant=instant)

    def _fade_buttons(self, show: bool, instant: bool = False) -> None:
        # Clear previous animations to avoid overlapping.
        self._anims.clear()
        target_opacity = 1.0 if show else 0.0
        duration = 0 if instant else self._fade_duration

        for btn in (self.prev_btn, self.next_btn):
            effect = btn.graphicsEffect()
            if effect is None:
                effect = QGraphicsOpacityEffect(btn)
                btn.setGraphicsEffect(effect)
            if show:
                btn.setVisible(True)
            anim = QPropertyAnimation(effect, b"opacity", self)
            anim.setDuration(duration)
            anim.setStartValue(effect.opacity())
            anim.setEndValue(target_opacity)
            anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
            if not show:
                anim.finished.connect(lambda b=btn, e=effect: (
                    b.setVisible(False), e.setOpacity(e.opacity())))
            self._anims.append(anim)
            anim.start()


class ClickableIcon(QLabel):
    """A QLabel that behaves like a button for icons."""

    clicked = pyqtSignal()

    def __init__(self, path: Path, size: QSize, parent=None) -> None:
        super().__init__(parent)
        self.setPixmap(QIcon(str(path)).pixmap(size))
        self.setFixedSize(size + QSize(6, 6))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("")

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class NavIcon(ClickableIcon):
    """Clickable icon with enable/disable state for navigation."""

    def __init__(self, path: Path, size: QSize, parent=None) -> None:
        super().__init__(path, size, parent)
        self._enabled = True

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if not self.graphicsEffect():
            effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(effect)
        effect = self.graphicsEffect()
        if isinstance(effect, QGraphicsOpacityEffect):
            effect.setOpacity(1.0 if enabled else 0.35)
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if not self._enabled:
            return
        super().mousePressEvent(event)
