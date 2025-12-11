"""Main application window."""

from __future__ import annotations

import sys
import ctypes
from pathlib import Path
import random

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QFontMetrics, QIcon, QMouseEvent, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QGraphicsOpacityEffect,
    QSizePolicy,
    QStatusBar,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QStyle,
    QCheckBox,
)

from app.services import settings
from app.services.fs_service import list_images
from app.core.shortcuts import bind_delete, bind_image_navigation
from app.ui.image_canvas import ImageCanvas


class MainWindow(QMainWindow):
    """Main viewer window with toolbar, navigation controls, and image canvas."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Randora Viewer")
        # 기본 타이틀바 제거 후 커스텀 타이틀바 사용.
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self._icons_dir = Path(__file__).resolve(
        ).parent.parent / "resources" / "icons"
        icon_path = self._icon_path("Randora.ico")
        if not icon_path.exists():
            icon_path = self._icon_path("Randora.png")
        self.setWindowIcon(QIcon(str(icon_path)))
        self.canvas = ImageCanvas(self)
        self.canvas.request_open.connect(self._on_open_folder)
        self.nav_container = NavigationContainer(self.canvas, self._icons_dir)
        self._last_folder: Path | None = settings.get_last_folder()
        self._info_font_size = 10
        self._status_icon_size = 18  # temporary, recalculated in _create_statusbar
        self._statusbar_height = 45
        self._has_image: bool = False
        self._images: list[Path] = []
        self._current_index: int = 0
        self._random_mode: bool = False

        self._create_actions()
        self._create_toolbar()
        self._create_statusbar()
        self._init_layout()
        self._update_nav_buttons()  # 초기 상태에서는 양쪽 네비게이션을 비활성화
        # Set a generous default viewer size to minimize letterboxing on load.
        self.resize(2560, 1440)

        self.nav_container.request_prev.connect(self._show_prev_image)
        self.nav_container.request_next.connect(self._show_next_image)
        self._update_max_button_icon()
        # 화살표/삭제 단축키 바인딩 (중앙 네비 영역 기준)
        self._image_shortcuts = bind_image_navigation(
            self.nav_container, self._show_prev_image, self._show_next_image
        )
        self._delete_shortcut = bind_delete(
            self.nav_container, self._delete_current_image
        )

    def _create_actions(self) -> None:
        folder_icon = QIcon(str(self._icon_path("folder icon.png")))
        self.open_folder_action = QAction(folder_icon, "open", self)
        self.open_folder_action.triggered.connect(self._on_open_folder)

    def _create_toolbar(self) -> None:
        toolbar = TitleToolBar("Main Toolbar", self)
        self.toolbar = toolbar
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
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
        spacer.setSizePolicy(QSizePolicy.Policy.Fixed,
                             QSizePolicy.Policy.Fixed)
        toolbar.addWidget(spacer)
        toolbar.addAction(self.open_folder_action)

        self.random_toggle = QCheckBox("Random", self)
        self.random_toggle.setChecked(False)
        self.random_toggle.setStyleSheet("color: #f2f2f2; margin-left: 6px;")
        self.random_toggle.toggled.connect(self._on_random_toggled)
        toolbar.addWidget(self.random_toggle)

        stretch_left = QWidget(self)
        stretch_left.setSizePolicy(QSizePolicy.Policy.Expanding,
                                   QSizePolicy.Policy.Expanding)
        toolbar.addWidget(stretch_left)

        self.title_label = QLabel("", self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("color: #f2f2f2; font-weight: 600;")
        self.title_label.setSizePolicy(QSizePolicy.Policy.Expanding,
                                       QSizePolicy.Policy.Preferred)
        self.title_label.setMinimumWidth(260)
        toolbar.addWidget(self.title_label)

        stretch_right = QWidget(self)
        stretch_right.setSizePolicy(QSizePolicy.Policy.Expanding,
                                    QSizePolicy.Policy.Expanding)
        toolbar.addWidget(stretch_right)

        # 창 제어 버튼 왼쪽 구분선 (길이 20px)
        divider = QFrame(self)
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setFrameShadow(QFrame.Shadow.Plain)
        divider.setStyleSheet("color: rgba(255,255,255,0.25);")
        divider.setFixedHeight(20)
        toolbar.addWidget(divider)

        # 창 제어 버튼(밝은 커스텀 아이콘)
        controls = QWidget(self)
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(0)

        self.min_btn = self._make_window_button(
            self._window_control_icon("min"),
            self.showMinimized,
        )
        self.max_btn = self._make_window_button(
            self._window_control_icon("max"),
            self._toggle_max_restore,
        )
        self.close_btn = self._make_window_button(
            self._window_control_icon("close"),
            self.close,
        )

        for btn in (self.min_btn, self.max_btn, self.close_btn):
            controls_layout.addWidget(btn)

        toolbar.addWidget(controls)
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
        self.info_label.setVisible(False)
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
        if self._random_mode:
            self._shuffle_keep_current(target)
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
        self._update_title_label(path)
        self._update_nav_buttons()
        # 이미지 전환 시 포커스를 네비게이션 컨테이너로 줘서 단축키가 즉시 동작하도록.
        self.nav_container.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def _show_prev_image(self) -> None:
        if self._current_index > 0:
            self._show_image_at_index(self._current_index - 1)

    def _show_next_image(self) -> None:
        if self._images and self._current_index < len(self._images) - 1:
            self._show_image_at_index(self._current_index + 1)

    def _on_random_toggled(self, checked: bool) -> None:
        self._random_mode = checked
        if not self._images:
            return
        current = self._images[self._current_index]
        if checked:
            self._shuffle_keep_current(current)
            self._current_index = 0
            self._show_image_at_index(self._current_index)
            self._show_status("랜덤 순서로 전환")
        else:
            self._images = sorted(self._images)
            self._current_index = self._find_index(current)
            self._show_image_at_index(self._current_index)
            self._show_status("순차 순서로 전환")

    def _delete_current_image(self) -> None:
        if not self._images:
            return
        path = self._images[self._current_index]
        try:
            self._send_to_trash(path)
        except Exception as exc:
            self._show_status(f"삭제 실패: {exc}")
            return

        del self._images[self._current_index]
        if self._current_index >= len(self._images):
            self._current_index = max(0, len(self._images) - 1)

        if self._images:
            self._show_image_at_index(self._current_index)
            self._show_status("이미지를 삭제했습니다")
        else:
            self.canvas.clear_image()
            self._set_info_placeholder()
            self._show_status("모든 이미지가 삭제되었습니다")

    def _shuffle_keep_current(self, current: Path) -> None:
        """현재 이미지는 유지하고 나머지를 랜덤 섞기."""
        resolved = current.resolve()
        rest = [p for p in self._images if p.resolve() != resolved]
        random.shuffle(rest)
        self._images = [current] + rest

    def _find_index(self, path: Path) -> int:
        resolved = path.resolve()
        for idx, p in enumerate(self._images):
            if p.resolve() == resolved:
                return idx
        return 0

    def _toggle_max_restore(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self._update_max_button_icon()

    def _update_max_button_icon(self) -> None:
        if not hasattr(self, "max_btn"):
            return
        icon = self._window_control_icon(
            "restore" if self.isMaximized() else "max")
        self.max_btn.setIcon(icon)

    def _update_nav_buttons(self) -> None:
        has_prev = self._current_index > 0
        has_next = bool(self._images) and self._current_index < len(
            self._images) - 1
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
        self._has_image = True
        resolution = f"{size.width()} x {size.height()}"
        file_size = self._format_size(path.stat().st_size)
        self.info_label.setVisible(True)
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
        self._has_image = False
        self.info_label.clear()
        self.info_label.setVisible(False)
        self._update_title_label(None)

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

    def _update_title_label(self, path: Path | None) -> None:
        if not hasattr(self, "title_label"):
            return
        self.title_label.setText(path.name if path else "")

    def _make_window_button(self, icon: QIcon, slot) -> QToolButton:
        btn = QToolButton(self)
        btn.setIcon(icon)
        btn.setAutoRaise(True)
        btn.setCursor(Qt.CursorShape.ArrowCursor)
        btn.clicked.connect(slot)
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        btn.setFixedSize(QSize(28, 24))
        btn.setStyleSheet(
            """
            QToolButton {
                background: transparent;
                border: none;
                color: #ffffff;
            }
            QToolButton:hover {
                background: rgba(255, 255, 255, 0.28);
            }
            QToolButton:pressed {
                background: rgba(255, 255, 255, 0.36);
            }
            """
        )
        return btn

    def _window_control_icon(self, kind: str) -> QIcon:
        size = 14
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(Qt.GlobalColor.white)
        pen.setWidth(2)
        painter.setPen(pen)

        if kind == "min":
            y = size // 2
            painter.drawLine(3, y, size - 3, y)
        elif kind == "max":
            painter.drawRect(2, 2, size - 5, size - 5)
        elif kind == "restore":
            painter.drawRect(4, 4, size - 6, size - 6)
            painter.drawRect(1, 1, size - 6, size - 6)
        elif kind == "close":
            painter.drawLine(3, 3, size - 3, size - 3)
            painter.drawLine(size - 3, 3, 3, size - 3)

        painter.end()
        return QIcon(pm)

    def _send_to_trash(self, path: Path) -> None:
        """Delete 파일을 휴지통으로 보낸다(Windows), 그 외 OS는 즉시 삭제."""
        if sys.platform.startswith("win"):
            # SHFileOperationW 사용
            FO_DELETE = 3
            FOF_ALLOWUNDO = 0x40
            FOF_NOCONFIRMATION = 0x10
            FOF_SILENT = 0x4

            class SHFILEOPSTRUCT(ctypes.Structure):
                _fields_ = [
                    ("hwnd", ctypes.c_void_p),
                    ("wFunc", ctypes.c_uint),
                    ("pFrom", ctypes.c_wchar_p),
                    ("pTo", ctypes.c_wchar_p),
                    ("fFlags", ctypes.c_uint),
                    ("fAnyOperationsAborted", ctypes.c_bool),
                    ("hNameMappings", ctypes.c_void_p),
                    ("lpszProgressTitle", ctypes.c_wchar_p),
                ]

            # SHFileOperationW expects double-null-terminated list.
            p_from = str(path) + "\0\0"
            op = SHFILEOPSTRUCT(
                hwnd=int(self.winId()),
                wFunc=FO_DELETE,
                pFrom=p_from,
                pTo=None,
                fFlags=FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT,
                fAnyOperationsAborted=False,
                hNameMappings=None,
                lpszProgressTitle=None,
            )
            res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
            if res != 0:
                raise OSError(f"SHFileOperation failed with code {res}")
        else:
            path.unlink(missing_ok=True)

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


class TitleToolBar(QToolBar):
    """Frameless 창에서 타이틀바 역할을 하는 툴바."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(title, parent)
        self._drag_pos = None
        self._win_start = None
        self.setMouseTracking(True)

    def _is_interactive_hit(self, pos) -> bool:
        widget = self.childAt(pos)
        return isinstance(widget, QToolButton)

    def _try_system_move(self) -> bool:
        window = self.window()
        if window and window.windowHandle():
            handle = window.windowHandle()
            try:
                return bool(handle.startSystemMove())
            except Exception:
                return False
        return False

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if isinstance(event, QMouseEvent) and event.button() == Qt.MouseButton.LeftButton:
            if not self._is_interactive_hit(event.pos()):
                if not self._try_system_move():
                    self._drag_pos = event.globalPosition().toPoint()
                    self._win_start = self.window().frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._drag_pos and isinstance(event, QMouseEvent):
            delta = event.globalPosition().toPoint() - self._drag_pos
            if self._win_start:
                self.window().move(self._win_start + delta)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        self._drag_pos = None
        self._win_start = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[override]
        if isinstance(event, QMouseEvent) and event.button() == Qt.MouseButton.LeftButton:
            if not self._is_interactive_hit(event.pos()):
                window = self.window()
                if hasattr(window, "_toggle_max_restore"):
                    window._toggle_max_restore()  # type: ignore[attr-defined]
                event.accept()
                return
        super().mouseDoubleClickEvent(event)


class NavigationContainer(QWidget):
    """Wraps the canvas with fixed side rails; buttons reveal on hover."""

    request_prev = pyqtSignal()
    request_next = pyqtSignal()

    def __init__(self, canvas: ImageCanvas, icons_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.canvas = canvas
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
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
        self.prev_btn.setVisible(has_prev)
        self.prev_btn.setEnabled(has_prev)
        self.next_btn.setVisible(has_next)
        self.next_btn.setEnabled(has_next)

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._set_buttons_visible(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._set_buttons_visible(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        # 포커스를 받아 단축키가 동작하도록 한다.
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        super().mousePressEvent(event)

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
            if show:
                # 비활성 버튼은 그대로 숨김 유지.
                if not btn.isEnabled():
                    btn.setVisible(False)
                    continue
                btn.setVisible(True)
            elif not btn.isVisible():
                continue
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
