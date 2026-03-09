# MIT License — Copyright (c) 2026 Flávio Takemoto
# See LICENSE file for full terms.

"""
HandNavigator — Main Application

QApplication that orchestrates all UI components:
  - PIP webcam preview (pip_widget.py)
  - System tray icon (tray_icon.py)
  - 3D preview viewport (viewport_3d.py)
  - Hand tracker thread (tracker_thread.py)

Supports two modes:
  - Preview: camera in the built-in 3D viewport responds to gestures
  - Live: Win32 SendInput sends keystrokes to the active external app
"""

import sys
from pathlib import Path

import numpy as np
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from tracker.config import ACTIVE_PROFILE
from tracker.gesture_recognizer import GestureType
from tracker.navigation_solver import NavigationDelta

from input.input_simulator import InputSimulator
from input.c4d_socket_client import C4DSocketClient
from input.profiles.cinema4d import Cinema4DProfile
from input.profiles.blender import BlenderProfile

from ui.i18n import t
from ui.pip_widget import PipWidget
from ui.tray_icon import TrayIcon
from ui.tracker_thread import TrackerThread
from ui.viewport_3d import Viewport3D


# ─── Profile Registry ────────────────────────────────────────────────────────

_PROFILE_MAP = {
    "cinema4d": Cinema4DProfile,
    "blender": BlenderProfile,
}


class HandNavigatorApp(QMainWindow):
    """
    Main window hosting the 3D viewport and managing all components.
    """

    def __init__(self) -> None:
        super().__init__()

        self._mode = "preview"  # "preview" or "live"
        self._current_gesture = GestureType.IDLE

        # ─── Input (for Live mode) ────────────────────────────────────
        profile_cls = _PROFILE_MAP.get(ACTIVE_PROFILE, Cinema4DProfile)
        self._simulator = InputSimulator(profile_cls())
        self._c4d_client = C4DSocketClient()

        # ─── Window Setup ────────────────────────────────────────────
        self.setWindowTitle(t("window_title"))
        self.setMinimumSize(800, 600)
        self.resize(1100, 750)

        # App icon (from assets/)
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
        icon_path = base / "assets" / "icon_256.png"
        if icon_path.exists():
            app_icon = QIcon(str(icon_path))
            self.setWindowIcon(app_icon)
            QApplication.instance().setWindowIcon(app_icon)

        self._setup_style()

        # ─── Central Widget ──────────────────────────────────────────
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 3D Viewport
        self._viewport = Viewport3D()
        layout.addWidget(self._viewport, stretch=1)

        # Status bar at bottom
        self._status_bar = self._create_status_bar()
        layout.addWidget(self._status_bar)

        # ─── Keyboard Shortcuts ──────────────────────────────────────
        reset_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        reset_shortcut.activated.connect(self._viewport.reset_camera)

        # ─── PIP Widget ──────────────────────────────────────────────
        self._pip = PipWidget()
        self._pip.show()

        # ─── Tray Icon ───────────────────────────────────────────────
        self._tray = TrayIcon(
            parent=self,
            on_toggle_pip=self._toggle_pip,
            on_show_viewport=self._show_viewport,
            on_set_mode=self._set_mode,
            on_set_profile=self._set_profile,
            on_quit=self._quit_app,
        )
        self._tray.show()

        # ─── Tracker Thread ──────────────────────────────────────────
        self._tracker = TrackerThread()
        self._tracker.frame_ready.connect(self._on_frame)
        self._tracker.navigation_ready.connect(self._on_navigation)
        self._tracker.gesture_changed.connect(self._on_gesture_changed)
        self._tracker.start()

        # ─── Auto-refresh viewport for idle animation ────────────────
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._viewport.update)
        self._refresh_timer.start(33)  # ~30fps

    def _setup_style(self) -> None:
        """Apply dark theme styling."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0a0a0f;
            }
            QWidget {
                color: #cdd6f4;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                color: #a6adc8;
            }
        """)

    def _create_status_bar(self) -> QWidget:
        """Create the bottom status bar widget."""
        bar = QWidget()
        bar.setFixedHeight(36)
        bar.setStyleSheet("""
            QWidget {
                background-color: #11111b;
                border-top: 1px solid #1e1e2e;
            }
        """)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 0, 12, 0)

        self._gesture_label = QLabel(t("gesture_idle_label"))
        self._gesture_label.setStyleSheet("color: #6c7086; font-weight: bold;")
        layout.addWidget(self._gesture_label)

        layout.addStretch()

        # Reset camera button
        reset_btn = QPushButton("⟳ " + t("reset_camera"))
        reset_btn.setFixedHeight(26)
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e1e2e;
                color: #a6adc8;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 0 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #313244;
                color: #cdd6f4;
            }
            QPushButton:pressed {
                background-color: #45475a;
            }
        """)
        reset_btn.setToolTip(t("reset_camera_tip"))
        reset_btn.clicked.connect(self._reset_camera)
        layout.addWidget(reset_btn)

        self._mode_label = QLabel(t("mode_preview"))
        self._mode_label.setStyleSheet("color: #585b70; margin-left: 16px;")
        layout.addWidget(self._mode_label)

        self._profile_label = QLabel(t("profile_label", name=self._simulator.profile_name))
        self._profile_label.setStyleSheet("color: #585b70; margin-left: 16px;")
        layout.addWidget(self._profile_label)

        return bar

    # ─── Signal Handlers ─────────────────────────────────────────────────

    def _on_frame(self, frame: np.ndarray, gesture: GestureType) -> None:
        """Handle new webcam frame from tracker thread."""
        self._pip.update_frame(frame, gesture)

    def _on_navigation(self, delta: NavigationDelta, mx: int, my: int) -> None:
        """Handle navigation delta from tracker thread."""
        if self._mode == "preview":
            # Route to internal 3D viewport
            self._viewport.apply_navigation(delta.gesture, mx, my)
        else:
            # Route raw deltas via UDP to C4D plugin
            self._c4d_client.send_navigation(delta)

    def _on_gesture_changed(self, gesture: GestureType) -> None:
        """Handle gesture state transitions."""
        self._current_gesture = gesture
        self._tray.update_gesture(gesture)

        # UI label updates
        gesture_info = {
            GestureType.IDLE:  (t("gesture_idle_label"),  "#6c7086"),
            GestureType.PAN:   (t("gesture_pan_label"),   "#00dc64"),
            GestureType.ZOOM:  (t("gesture_zoom_label"),  "#ffc800"),
            GestureType.ORBIT: (t("gesture_orbit_label"), "#508cff"),
        }
        label, color = gesture_info[gesture]
        self._gesture_label.setText(label)
        self._gesture_label.setStyleSheet(f"color: {color}; font-weight: bold;")

        # In live mode, gesture state is implicit in delta routing
        # (C4D socket client handles it per-packet)

    # ─── Tray Menu Callbacks ─────────────────────────────────────────────

    def _reset_camera(self) -> None:
        """Reset the 3D viewport camera to default position."""
        self._viewport.reset_camera()

    def _show_viewport(self) -> None:
        """Restore the main window (3D viewport)."""
        self.show()
        self.raise_()
        self.activateWindow()

    def _toggle_pip(self) -> None:
        if self._pip.isVisible():
            self._pip.hide()
        else:
            self._pip.show()

    def _set_mode(self, mode: str) -> None:
        """Switch between preview and live modes."""
        if mode == self._mode:
            return

        # Clean up previous mode
        if self._mode == "live":
            self._simulator.end_gesture()

        self._mode = mode
        mode_key = "mode_preview" if mode == "preview" else "mode_live"
        self._mode_label.setText(t(mode_key))

    def _set_profile(self, profile_key: str) -> None:
        """Switch the active app profile."""
        profile_cls = _PROFILE_MAP.get(profile_key)
        if profile_cls is None:
            return

        # End current gesture before switching
        if self._mode == "live":
            self._simulator.end_gesture()

        self._simulator = InputSimulator(profile_cls())
        self._profile_label.setText(t("profile_label", name=self._simulator.profile_name))

    def _quit_app(self) -> None:
        """Clean shutdown."""
        self._tracker.stop()
        self._tracker.wait(2000)
        self._simulator.shutdown()
        self._tray.hide()
        QApplication.quit()

    # ─── Window Events ───────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        """Intercept close → minimize to tray instead."""
        event.ignore()
        self.hide()
        self._tray.showMessage(
            t("app_name"),
            t("tray_minimized"),
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )


def main() -> None:
    """Launch the HandNavigator application."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running in tray
    app.setApplicationName(t("app_name"))

    window = HandNavigatorApp()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
