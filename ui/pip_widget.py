# MIT License — Copyright (c) 2026 Flávio Takemoto
# See LICENSE file for full terms.

"""
HandNavigator — PIP Webcam Preview

A frameless, always-on-top, resizable picture-in-picture window
that displays the webcam feed with hand landmark overlay.

Features:
  - Drag to move (click anywhere on the frame)
  - Resize via corner drag handle
  - Double-click to hide (restore via tray)
  - Shows current gesture label and color indicator
"""

import cv2
import numpy as np
from PyQt6.QtCore import Qt, QPoint, QSize, QRect
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QFont, QPen, QBrush
from PyQt6.QtWidgets import QWidget, QSizePolicy

from tracker.gesture_recognizer import GestureType
from ui.i18n import t


# Gesture display metadata
_GESTURE_COLORS = {
    GestureType.IDLE:  QColor(128, 128, 128),
    GestureType.PAN:   QColor(0, 220, 100),
    GestureType.ZOOM:  QColor(255, 200, 0),
    GestureType.ORBIT: QColor(80, 140, 255),
}

_GESTURE_LABEL_KEYS = {
    GestureType.IDLE:  "gesture_idle_label",
    GestureType.PAN:   "gesture_pan_label",
    GestureType.ZOOM:  "gesture_zoom_label",
    GestureType.ORBIT: "gesture_orbit_label",
}

_RESIZE_HANDLE_SIZE = 16
_MIN_SIZE = QSize(160, 120)
_DEFAULT_SIZE = QSize(320, 240)


class PipWidget(QWidget):
    """
    Picture-in-Picture webcam overlay.

    Frameless, always-on-top, draggable, resizable.
    Renders BGR frames from the tracker thread as a pixmap.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # Hides from taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumSize(_MIN_SIZE)
        self.resize(_DEFAULT_SIZE)

        self._pixmap: QPixmap | None = None
        self._gesture = GestureType.IDLE
        self._dragging = False
        self._resizing = False
        self._drag_offset = QPoint()
        self._opacity = 1.0

        # Start in bottom-right area of primary screen
        self.move(100, 100)

    # ─── Public API ──────────────────────────────────────────────────────

    def update_frame(self, frame_bgr: np.ndarray, gesture: GestureType) -> None:
        """Update the displayed frame and gesture indicator."""
        self._gesture = gesture

        # Convert BGR numpy array to QPixmap
        h, w, ch = frame_bgr.shape
        bytes_per_line = ch * w
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        q_image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self._pixmap = QPixmap.fromImage(q_image)

        self.update()  # Trigger repaint

    def set_opacity(self, value: float) -> None:
        """Set window opacity (0.0 to 1.0)."""
        self._opacity = max(0.1, min(1.0, value))
        self.setWindowOpacity(self._opacity)

    # ─── Painting ────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()

        # Draw background / webcam frame
        if self._pixmap:
            scaled = self._pixmap.scaled(
                rect.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            # Center crop
            x_off = (scaled.width() - rect.width()) // 2
            y_off = (scaled.height() - rect.height()) // 2
            painter.drawPixmap(rect, scaled, QRect(x_off, y_off, rect.width(), rect.height()))
        else:
            painter.fillRect(rect, QColor(30, 30, 40))

        # Gesture indicator bar at top
        label = t(_GESTURE_LABEL_KEYS[self._gesture])
        color = _GESTURE_COLORS[self._gesture]
        bar_height = 28
        painter.fillRect(0, 0, rect.width(), bar_height, QColor(0, 0, 0, 160))

        # Gesture dot
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(8, 6, 16, 16)

        # Gesture text
        painter.setPen(QPen(QColor(255, 255, 255)))
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(30, 19, label)

        # Border
        border_color = QColor(color.red(), color.green(), color.blue(), 180)
        painter.setPen(QPen(border_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect.adjusted(1, 1, -1, -1))

        # Resize handle (bottom-right corner triangle)
        painter.setBrush(QBrush(QColor(255, 255, 255, 80)))
        painter.setPen(Qt.PenStyle.NoPen)
        s = _RESIZE_HANDLE_SIZE
        points = [
            QPoint(rect.right(), rect.bottom() - s),
            QPoint(rect.right() - s, rect.bottom()),
            QPoint(rect.right(), rect.bottom()),
        ]
        painter.drawPolygon(points)

        painter.end()

    # ─── Mouse Interaction ───────────────────────────────────────────────

    def _in_resize_zone(self, pos: QPoint) -> bool:
        """Check if position is in the bottom-right resize handle."""
        s = _RESIZE_HANDLE_SIZE
        r = self.rect()
        return (
            pos.x() >= r.right() - s
            and pos.y() >= r.bottom() - s
        )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self._in_resize_zone(event.position().toPoint()):
                self._resizing = True
            else:
                self._dragging = True
                self._drag_offset = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event) -> None:
        if self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
        elif self._resizing:
            global_pos = event.globalPosition().toPoint()
            new_w = max(_MIN_SIZE.width(), global_pos.x() - self.x())
            new_h = max(_MIN_SIZE.height(), global_pos.y() - self.y())
            self.resize(new_w, new_h)

    def mouseReleaseEvent(self, event) -> None:
        self._dragging = False
        self._resizing = False

    def mouseDoubleClickEvent(self, event) -> None:
        """Double-click to hide (restore via tray menu)."""
        self.hide()
