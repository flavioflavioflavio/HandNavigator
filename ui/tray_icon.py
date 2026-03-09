# MIT License — Copyright (c) 2026 Flávio Takemoto
# See LICENSE file for full terms.

"""
HandNavigator — System Tray Icon

Animated tray icon that changes appearance based on the active gesture.
Provides a context menu for mode switching, profile selection, and controls.

Icons are generated programmatically — no external image files needed.
"""

from PyQt6.QtCore import Qt, QSize
import sys
from pathlib import Path

from PyQt6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QIcon,
    QImage,
    QPainter,
    QPen,
    QBrush,
    QPixmap,
    QFont,
)
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

from tracker.gesture_recognizer import GestureType
from ui.i18n import t


# ─── Gesture icon colors ─────────────────────────────────────────────────────

_GESTURE_COLORS = {
    GestureType.IDLE:  QColor(120, 120, 130),
    GestureType.PAN:   QColor(0, 220, 100),
    GestureType.ZOOM:  QColor(255, 200, 0),
    GestureType.ORBIT: QColor(80, 140, 255),
}

_GESTURE_SYMBOLS = {
    GestureType.IDLE:  "✋",
    GestureType.PAN:   "↔",
    GestureType.ZOOM:  "🔍",
    GestureType.ORBIT: "⟳",
}

_ICON_SIZE = 64


def _load_base_icon() -> QPixmap | None:
    """Load the custom icon PNG from assets/."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    icon_path = base / "assets" / "icon_64.png"
    if icon_path.exists():
        return QPixmap(str(icon_path))
    return None


# Cache the base icon pixmap at module level
_BASE_ICON: QPixmap | None = None


def _generate_icon(gesture: GestureType) -> QIcon:
    """Generate a tray icon: custom icon with colored gesture ring."""
    global _BASE_ICON
    if _BASE_ICON is None:
        _BASE_ICON = _load_base_icon()

    pixmap = QPixmap(_ICON_SIZE, _ICON_SIZE)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    color = _GESTURE_COLORS[gesture]

    if _BASE_ICON is not None:
        # Draw the custom icon scaled to fit inside the ring
        icon_rect = pixmap.rect().adjusted(6, 6, -6, -6)
        scaled = _BASE_ICON.scaled(
            icon_rect.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (pixmap.width() - scaled.width()) // 2
        y = (pixmap.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)

        # Colored ring around the icon (gesture indicator)
        painter.setPen(QPen(color, 4))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(2, 2, _ICON_SIZE - 4, _ICON_SIZE - 4)
    else:
        # Fallback: programmatic icon if PNG not found
        painter.setPen(QPen(color, 4))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(6, 6, 52, 52)

        inner = QColor(color.red(), color.green(), color.blue(), 180)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(inner))
        painter.drawEllipse(16, 16, 32, 32)

        painter.setPen(QPen(QColor(255, 255, 255)))
        font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        painter.setFont(font)
        label_map = {
            GestureType.IDLE:  "H",
            GestureType.PAN:   "P",
            GestureType.ZOOM:  "Z",
            GestureType.ORBIT: "O",
        }
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, label_map[gesture])

    painter.end()
    return QIcon(pixmap)


class TrayIcon(QSystemTrayIcon):
    """
    System tray icon with animated gesture state.

    Signals
    -------
    Uses callbacks (set via constructor) for:
      - toggle_pip: show/hide PIP window
      - set_mode: switch preview/live mode
      - set_profile: change app profile
      - quit_app: exit application
    """

    def __init__(
        self,
        parent: QWidget,
        on_toggle_pip=None,
        on_show_viewport=None,
        on_set_mode=None,
        on_set_profile=None,
        on_quit=None,
    ) -> None:
        super().__init__(parent)

        self._on_toggle_pip = on_toggle_pip
        self._on_show_viewport = on_show_viewport
        self._on_set_mode = on_set_mode
        self._on_set_profile = on_set_profile
        self._on_quit = on_quit

        # Pre-generate icons for each gesture
        self._icons = {
            gesture: _generate_icon(gesture)
            for gesture in GestureType
        }

        self.setIcon(self._icons[GestureType.IDLE])
        self.setToolTip(t("tray_tooltip", gesture=t("gesture_idle")))
        self._build_menu()

    def _build_menu(self) -> None:
        """Build the right-click context menu."""
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #45475a;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #45475a;
            }
            QMenu::separator {
                height: 1px;
                background: #45475a;
                margin: 4px 8px;
            }
        """)

        # ─── Window Toggles ──────────────────────────────────────────
        viewport_action = QAction("🎮 " + t("tray_show_viewport"), menu)
        viewport_action.triggered.connect(self._handle_show_viewport)
        menu.addAction(viewport_action)

        pip_action = QAction("🖼️ " + t("tray_toggle_pip"), menu)
        pip_action.triggered.connect(self._handle_toggle_pip)
        menu.addAction(pip_action)

        menu.addSeparator()

        # ─── Mode Selection ─────────────────────────────────────────
        mode_menu = menu.addMenu(t("tray_menu_mode"))
        mode_group = QActionGroup(mode_menu)

        self._preview_action = QAction("🎮 " + t("tray_mode_preview"), mode_menu)
        self._preview_action.setCheckable(True)
        self._preview_action.setChecked(True)
        self._preview_action.triggered.connect(lambda: self._handle_mode("preview"))
        mode_group.addAction(self._preview_action)
        mode_menu.addAction(self._preview_action)

        self._live_action = QAction("⌨️ " + t("tray_mode_live"), mode_menu)
        self._live_action.setCheckable(True)
        self._live_action.triggered.connect(lambda: self._handle_mode("live"))
        mode_group.addAction(self._live_action)
        mode_menu.addAction(self._live_action)

        # ─── Profile Selection ───────────────────────────────────────
        profile_menu = menu.addMenu(t("tray_menu_profile"))
        profile_group = QActionGroup(profile_menu)

        profiles = [
            ("Cinema 4D / Maya", "cinema4d"),
            ("Blender", "blender"),
        ]

        self._profile_actions = {}
        for label, key in profiles:
            action = QAction(label, profile_menu)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, k=key: self._handle_profile(k))
            profile_group.addAction(action)
            profile_menu.addAction(action)
            self._profile_actions[key] = action

        self._profile_actions["cinema4d"].setChecked(True)

        menu.addSeparator()

        # ─── Quit ────────────────────────────────────────────────────
        quit_action = QAction(t("tray_quit"), menu)
        quit_action.triggered.connect(self._handle_quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    # ─── Public API ──────────────────────────────────────────────────────

    def update_gesture(self, gesture: GestureType) -> None:
        """Update the tray icon to reflect the current gesture."""
        self.setIcon(self._icons[gesture])

        gesture_keys = {
            GestureType.IDLE:  "gesture_idle",
            GestureType.PAN:   "gesture_pan",
            GestureType.ZOOM:  "gesture_zoom",
            GestureType.ORBIT: "gesture_orbit",
        }
        self.setToolTip(t("tray_tooltip", gesture=t(gesture_keys[gesture])))

    # ─── Handlers ────────────────────────────────────────────────────────

    def _handle_show_viewport(self) -> None:
        if self._on_show_viewport:
            self._on_show_viewport()

    def _handle_toggle_pip(self) -> None:
        if self._on_toggle_pip:
            self._on_toggle_pip()

    def _handle_mode(self, mode: str) -> None:
        if mode == "preview":
            self._preview_action.setChecked(True)
        else:
            self._live_action.setChecked(True)
        if self._on_set_mode:
            self._on_set_mode(mode)

    def _handle_profile(self, profile: str) -> None:
        if self._on_set_profile:
            self._on_set_profile(profile)

    def _handle_quit(self) -> None:
        if self._on_quit:
            self._on_quit()
