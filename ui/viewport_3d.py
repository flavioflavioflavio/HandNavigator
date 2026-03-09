# MIT License - Copyright (c) 2026 Flavio Takemoto
# See LICENSE file for full terms.

"""
HandNavigator — 3D Preview Viewport

QOpenGLWidget that renders a simple 3D scene with a procedural object,
grid floor, and lighting. The camera responds to navigation deltas
from the hand tracker, serving as a test environment.

Camera model: orbiting camera around a target point.
  - Pan:   translate target + camera in screen-local XY
  - Zoom:  change camera distance from target
  - Orbit: rotate camera around target (spherical coordinates)
"""

import math

from PyQt6.QtCore import Qt, QSize, QPoint
from PyQt6.QtGui import QColor, QMouseEvent, QWheelEvent
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

from OpenGL.GL import *
from OpenGL.GLU import *

from tracker.gesture_recognizer import GestureType


# ─── Gesture indicator colors ────────────────────────────────────────────────

_INDICATOR_COLORS = {
    GestureType.IDLE:  (0.5, 0.5, 0.5),
    GestureType.PAN:   (0.0, 0.86, 0.4),
    GestureType.ZOOM:  (1.0, 0.78, 0.0),
    GestureType.ORBIT: (0.31, 0.55, 1.0),
}


class Viewport3D(QOpenGLWidget):
    """
    OpenGL 3D viewport with orbiting camera.

    Renders a procedural shape (torus + cube composition),
    a ground grid, and ambient/diffuse lighting.
    Camera is controlled via apply_navigation().
    """

    # Default camera position
    _DEFAULT_AZIMUTH = 45.0
    _DEFAULT_ELEVATION = 25.0
    _DEFAULT_DISTANCE = 6.0
    _DEFAULT_TARGET = [0.0, 0.8, 0.0]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        # Camera state (spherical coordinates)
        self._cam_azimuth = self._DEFAULT_AZIMUTH
        self._cam_elevation = self._DEFAULT_ELEVATION
        self._cam_distance = self._DEFAULT_DISTANCE
        self._cam_target = list(self._DEFAULT_TARGET)

        self._gesture = GestureType.IDLE
        self._rotation_angle = 0.0  # Slow auto-rotation for idle display

        # Mouse interaction state (Blender-style controls)
        self._mouse_last_pos: QPoint | None = None
        self._mouse_orbit = False    # MMB drag
        self._mouse_pan = False      # Shift+MMB drag

        self.setMinimumSize(QSize(400, 300))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # ─── Public API ──────────────────────────────────────────────────────

    def reset_camera(self) -> None:
        """Reset camera to default position."""
        self._cam_azimuth = self._DEFAULT_AZIMUTH
        self._cam_elevation = self._DEFAULT_ELEVATION
        self._cam_distance = self._DEFAULT_DISTANCE
        self._cam_target = list(self._DEFAULT_TARGET)
        self.update()

    def apply_navigation(self, gesture: GestureType, dx: int, dy: int) -> None:
        """
        Apply navigation delta from hand tracker.

        Parameters
        ----------
        gesture : GestureType
            Current active gesture.
        dx, dy : int
            Mouse-pixel-equivalent delta values.
        """
        self._gesture = gesture

        if gesture == GestureType.PAN:
            # Convert pixel delta to world-space pan
            sensitivity = 0.005
            azimuth_rad = math.radians(self._cam_azimuth)
            rx = math.cos(azimuth_rad)
            rz = -math.sin(azimuth_rad)
            self._cam_target[0] -= dx * sensitivity * rx
            self._cam_target[2] -= dx * sensitivity * rz
            self._cam_target[1] += dy * sensitivity

        elif gesture == GestureType.ZOOM:
            # Pinch: combined pan + zoom
            pan_sens = 0.005
            zoom_sens = 0.01
            azimuth_rad = math.radians(self._cam_azimuth)
            rx = math.cos(azimuth_rad)
            rz = -math.sin(azimuth_rad)
            self._cam_target[0] -= dx * pan_sens * rx
            self._cam_target[2] -= dx * pan_sens * rz
            self._cam_distance += dy * zoom_sens
            self._cam_distance = max(1.5, min(30.0, self._cam_distance))

        elif gesture == GestureType.ORBIT:
            # Orbit: rotate camera around target (both axes)
            sensitivity = 0.03
            self._cam_azimuth += dx * sensitivity
            self._cam_elevation -= dy * sensitivity
            self._cam_elevation = max(-85.0, min(85.0, self._cam_elevation))

        self.update()

    # ─── Mouse Controls (Blender-style) ─────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Start mouse drag: MMB=orbit, Shift+MMB=pan."""
        if event.button() == Qt.MouseButton.MiddleButton:
            self._mouse_last_pos = event.pos()
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self._mouse_pan = True
            else:
                self._mouse_orbit = True
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """End mouse drag."""
        if event.button() == Qt.MouseButton.MiddleButton:
            self._mouse_orbit = False
            self._mouse_pan = False
            self._mouse_last_pos = None
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse drag for orbit/pan."""
        if self._mouse_last_pos is None:
            return super().mouseMoveEvent(event)

        dx = event.pos().x() - self._mouse_last_pos.x()
        dy = event.pos().y() - self._mouse_last_pos.y()
        self._mouse_last_pos = event.pos()

        if self._mouse_orbit:
            self._cam_azimuth += dx * 0.5
            self._cam_elevation -= dy * 0.5
            self._cam_elevation = max(-85.0, min(85.0, self._cam_elevation))
            self.update()

        elif self._mouse_pan:
            sensitivity = 0.01
            azimuth_rad = math.radians(self._cam_azimuth)
            rx = math.cos(azimuth_rad)
            rz = -math.sin(azimuth_rad)
            self._cam_target[0] -= dx * sensitivity * rx
            self._cam_target[2] -= dx * sensitivity * rz
            self._cam_target[1] += dy * sensitivity
            self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Scroll to zoom."""
        delta = event.angleDelta().y()
        self._cam_distance -= delta * 0.005
        self._cam_distance = max(1.5, min(30.0, self._cam_distance))
        self.update()

    # ─── OpenGL Lifecycle ────────────────────────────────────────────────

    def initializeGL(self) -> None:
        glClearColor(0.08, 0.08, 0.12, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_NORMALIZE)
        glShadeModel(GL_SMOOTH)

        # Light setup
        glLightfv(GL_LIGHT0, GL_POSITION, [3.0, 8.0, 5.0, 1.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.15, 0.15, 0.2, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.9, 0.85, 0.8, 1.0])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])

        # Enable second fill light
        glEnable(GL_LIGHT1)
        glLightfv(GL_LIGHT1, GL_POSITION, [-4.0, 3.0, -2.0, 1.0])
        glLightfv(GL_LIGHT1, GL_DIFFUSE, [0.2, 0.25, 0.4, 1.0])

    def resizeGL(self, w: int, h: int) -> None:
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = w / max(h, 1)
        gluPerspective(45.0, aspect, 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self) -> None:
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # ─── Camera ─────────────────────────────────────────────────
        az_rad = math.radians(self._cam_azimuth)
        el_rad = math.radians(self._cam_elevation)

        cam_x = self._cam_target[0] + self._cam_distance * math.cos(el_rad) * math.sin(az_rad)
        cam_y = self._cam_target[1] + self._cam_distance * math.sin(el_rad)
        cam_z = self._cam_target[2] + self._cam_distance * math.cos(el_rad) * math.cos(az_rad)

        gluLookAt(
            cam_x, cam_y, cam_z,
            self._cam_target[0], self._cam_target[1], self._cam_target[2],
            0.0, 1.0, 0.0,
        )

        # ─── Ground Grid ────────────────────────────────────────────
        self._draw_grid()

        # ─── Scene Objects ───────────────────────────────────────────
        self._draw_scene()

        # ─── Gesture Indicator (corner dot) ──────────────────────────
        self._draw_gesture_indicator()

    # ─── Drawing Helpers ─────────────────────────────────────────────────

    def _draw_grid(self) -> None:
        """Draw a ground plane grid."""
        glDisable(GL_LIGHTING)
        glBegin(GL_LINES)

        grid_size = 10
        grid_step = 1.0

        for i in range(-grid_size, grid_size + 1):
            intensity = 0.15 if i % 5 != 0 else 0.3
            glColor3f(intensity, intensity, intensity + 0.05)

            # X-axis lines
            glVertex3f(i * grid_step, 0.0, -grid_size * grid_step)
            glVertex3f(i * grid_step, 0.0, grid_size * grid_step)

            # Z-axis lines
            glVertex3f(-grid_size * grid_step, 0.0, i * grid_step)
            glVertex3f(grid_size * grid_step, 0.0, i * grid_step)

        glEnd()
        glEnable(GL_LIGHTING)

    def _draw_scene(self) -> None:
        """Draw the 3D scene objects (procedural torus + supporting shapes)."""
        # ─── Main object: Torus ──────────────────────────────────────
        glPushMatrix()
        glTranslatef(0.0, 1.2, 0.0)

        # Slow idle rotation
        self._rotation_angle += 0.3
        glRotatef(self._rotation_angle, 0.0, 1.0, 0.0)

        glColor3f(0.85, 0.25, 0.35)
        glMaterialfv(GL_FRONT, GL_SPECULAR, [1.0, 0.8, 0.8, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 60.0)
        self._draw_torus(inner_radius=0.3, outer_radius=0.8, rings=32, sides=24)
        glPopMatrix()

        # ─── Pedestal: Cube ──────────────────────────────────────────
        glPushMatrix()
        glTranslatef(0.0, 0.25, 0.0)
        glColor3f(0.3, 0.3, 0.35)
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.3, 0.3, 0.4, 1.0])
        glMaterialf(GL_FRONT, GL_SHININESS, 20.0)
        self._draw_cube(0.5)
        glPopMatrix()

        # ─── Small spheres around ────────────────────────────────────
        for i in range(4):
            angle = math.radians(i * 90 + self._rotation_angle * 0.5)
            x = math.cos(angle) * 2.0
            z = math.sin(angle) * 2.0
            glPushMatrix()
            glTranslatef(x, 0.3, z)
            colors = [
                (0.2, 0.7, 0.9),
                (0.9, 0.7, 0.2),
                (0.3, 0.9, 0.4),
                (0.7, 0.3, 0.9),
            ]
            glColor3f(*colors[i])
            glMaterialfv(GL_FRONT, GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])
            glMaterialf(GL_FRONT, GL_SHININESS, 40.0)
            sphere = gluNewQuadric()
            gluSphere(sphere, 0.2, 16, 16)
            gluDeleteQuadric(sphere)
            glPopMatrix()

    def _draw_torus(
        self,
        inner_radius: float,
        outer_radius: float,
        rings: int,
        sides: int,
    ) -> None:
        """Draw a procedural torus using quad strips."""
        for i in range(rings):
            theta = 2.0 * math.pi * i / rings
            theta_next = 2.0 * math.pi * (i + 1) / rings

            glBegin(GL_QUAD_STRIP)
            for j in range(sides + 1):
                phi = 2.0 * math.pi * j / sides

                for t in (theta, theta_next):
                    cos_t = math.cos(t)
                    sin_t = math.sin(t)
                    cos_p = math.cos(phi)
                    sin_p = math.sin(phi)

                    r = outer_radius + inner_radius * cos_p

                    x = r * cos_t
                    y = inner_radius * sin_p
                    z = r * sin_t

                    # Normal
                    nx = cos_p * cos_t
                    ny = sin_p
                    nz = cos_p * sin_t

                    glNormal3f(nx, ny, nz)
                    glVertex3f(x, y, z)

            glEnd()

    def _draw_cube(self, size: float) -> None:
        """Draw a simple cube."""
        s = size

        faces = [
            # (normal, vertices)
            ((0, 1, 0), [(-s, s, -s), (-s, s, s), (s, s, s), (s, s, -s)]),
            ((0, -1, 0), [(-s, -s, -s), (s, -s, -s), (s, -s, s), (-s, -s, s)]),
            ((0, 0, 1), [(-s, -s, s), (s, -s, s), (s, s, s), (-s, s, s)]),
            ((0, 0, -1), [(-s, -s, -s), (-s, s, -s), (s, s, -s), (s, -s, -s)]),
            ((1, 0, 0), [(s, -s, -s), (s, s, -s), (s, s, s), (s, -s, s)]),
            ((-1, 0, 0), [(-s, -s, -s), (-s, -s, s), (-s, s, s), (-s, s, -s)]),
        ]

        glBegin(GL_QUADS)
        for normal, verts in faces:
            glNormal3f(*normal)
            for v in verts:
                glVertex3f(*v)
        glEnd()

    def _draw_gesture_indicator(self) -> None:
        """Draw a small colored dot in the viewport corner showing active gesture."""
        # Switch to 2D overlay
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)

        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        w, h = self.width(), self.height()
        glOrtho(0, w, h, 0, -1, 1)

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        # Draw gesture indicator circle
        color = _INDICATOR_COLORS[self._gesture]
        cx, cy, r = w - 24, 24, 10

        glColor3f(*color)
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(cx, cy)
        for i in range(33):
            angle = 2.0 * math.pi * i / 32
            glVertex2f(cx + r * math.cos(angle), cy + r * math.sin(angle))
        glEnd()

        # Restore
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
