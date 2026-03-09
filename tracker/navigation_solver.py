# MIT License - Copyright (c) 2026 Flavio Takemoto
# See LICENSE file for full terms.

"""
HandNavigator — Navigation Solver

Converts raw hand landmarks into navigation deltas (dx, dy, yaw, pitch).
Each gesture type extracts its relevant movement data:
  - PAN:   wrist XY displacement between frames
  - ZOOM:  wrist Z displacement (depth) between frames
  - ORBIT: hand rotation angle change between frames
"""

from dataclasses import dataclass
from typing import Optional

import math
import numpy as np

from tracker.config import DEAD_ZONE_ROTATION, DEAD_ZONE_TRANSLATION
from tracker.gesture_recognizer import GestureType


@dataclass(frozen=True)
class NavigationDelta:
    """
    Navigation output for a single frame.

    Attributes
    ----------
    gesture : GestureType
        Active gesture.
    dx, dy : float
        Horizontal/vertical delta (for Pan). Normalized ~[-1, 1].
    dz : float
        Depth delta (for Zoom). Positive = forward = zoom in.
    yaw, pitch : float
        Rotation deltas in radians (for Orbit).
    """
    gesture: GestureType
    dx: float = 0.0
    dy: float = 0.0
    dz: float = 0.0
    yaw: float = 0.0
    pitch: float = 0.0


# Landmark indices
_WRIST = 0
_INDEX_MCP = 5
_MIDDLE_MCP = 9
_RING_MCP = 13


def _hand_direction_angle(landmarks: np.ndarray) -> tuple[float, float]:
    """
    Compute the hand's orientation as (yaw, pitch) angles.
    Uses vector from wrist to middle finger MCP as the primary axis.
    """
    wrist = landmarks[_WRIST]
    middle_mcp = landmarks[_MIDDLE_MCP]

    direction = middle_mcp - wrist

    # Yaw: rotation in XY plane (left-right tilt)
    yaw = math.atan2(direction[0], direction[1])

    # Pitch: rotation in YZ plane (forward-back tilt)
    horizontal_dist = math.sqrt(direction[0] ** 2 + direction[1] ** 2)
    pitch = math.atan2(direction[2], horizontal_dist)

    return yaw, pitch


class NavigationSolver:
    """
    Stateful solver that computes frame-to-frame navigation deltas.

    Tracks previous frame's wrist position and hand orientation
    to compute relative movement.
    """

    def __init__(self) -> None:
        self._prev_wrist: Optional[np.ndarray] = None
        self._prev_yaw: Optional[float] = None
        self._prev_pitch: Optional[float] = None
        self._prev_gesture: GestureType = GestureType.IDLE

    def compute(
        self,
        landmarks: np.ndarray,
        gesture: GestureType,
    ) -> NavigationDelta:
        """
        Compute navigation delta based on current landmarks and gesture.

        On the first frame after a gesture change, stores the reference
        position and returns zero delta (avoids jump artifacts).

        Parameters
        ----------
        landmarks : np.ndarray
            Shape (21, 3) hand landmarks.
        gesture : GestureType
            Current active gesture.

        Returns
        -------
        NavigationDelta
            The computed delta for this frame.
        """
        if gesture == GestureType.IDLE:
            self.reset()
            return NavigationDelta(gesture=GestureType.IDLE)

        # Reset reference on gesture change to prevent snap/jump
        if gesture != self._prev_gesture:
            self._prev_wrist = None
            self._prev_gesture = gesture

        wrist = landmarks[_WRIST].copy()
        yaw, pitch = _hand_direction_angle(landmarks)

        # First frame after gesture start → store reference, no delta yet
        if self._prev_wrist is None:
            self._prev_wrist = wrist
            self._prev_yaw = yaw
            self._prev_pitch = pitch
            return NavigationDelta(gesture=gesture)

        delta = NavigationDelta(gesture=gesture)

        if gesture == GestureType.PAN:
            dx = float(wrist[0] - self._prev_wrist[0])
            dy = float(wrist[1] - self._prev_wrist[1])
            # Apply dead zone
            dx = dx if abs(dx) > DEAD_ZONE_TRANSLATION else 0.0
            dy = dy if abs(dy) > DEAD_ZONE_TRANSLATION else 0.0
            delta = NavigationDelta(gesture=gesture, dx=dx, dy=dy)

        elif gesture == GestureType.ZOOM:
            # L-shape = zoom only (vertical wrist movement)
            dz = float(self._prev_wrist[1] - wrist[1])  # inverted: up = zoom in
            dz = dz if abs(dz) > DEAD_ZONE_TRANSLATION else 0.0
            delta = NavigationDelta(gesture=gesture, dz=dz)

        elif gesture == GestureType.ORBIT:
            # Use wrist XY drag for orbit (more reliable than rotation angles)
            d_yaw = float(wrist[0] - self._prev_wrist[0])
            d_pitch = float(wrist[1] - self._prev_wrist[1])
            # Apply dead zone
            d_yaw = d_yaw if abs(d_yaw) > DEAD_ZONE_TRANSLATION else 0.0
            d_pitch = d_pitch if abs(d_pitch) > DEAD_ZONE_TRANSLATION else 0.0
            delta = NavigationDelta(gesture=gesture, yaw=d_yaw, pitch=d_pitch)

        # Update previous state
        self._prev_wrist = wrist
        self._prev_yaw = yaw
        self._prev_pitch = pitch

        return delta

    def reset(self) -> None:
        """Clear stored state (called on gesture loss or change)."""
        self._prev_wrist = None
        self._prev_yaw = None
        self._prev_pitch = None
