# MIT License - Copyright (c) 2026 Flavio Takemoto
# See LICENSE file for full terms.

"""
HandNavigator — Gesture Recognizer

Classifies the current hand pose into navigation gestures:
  - PINCH (thumb+index): Pan (full 2D)
  - L-SHAPE (index+thumb extended, rest curled): Zoom
  - PINCH (thumb+middle): Orbit
  - IDLE:  no clear gesture or transition buffer

Uses a frame buffer to prevent accidental gesture switches.
"""

from enum import Enum, auto

import numpy as np

from tracker.config import (
    GESTURE_SWITCH_FRAMES,
    PINCH_THRESHOLD,
)


class GestureType(Enum):
    IDLE = auto()
    PAN = auto()      # Thumb + Index pinch → full 2D pan
    ZOOM = auto()     # L-shape (index+thumb extended) → zoom only
    ORBIT = auto()    # Thumb + Middle pinch → orbit


# ─── MediaPipe landmark indices ──────────────────────────────────────────────

_WRIST = 0
_THUMB_TIP = 4
_INDEX_TIP = 8
_MIDDLE_TIP = 12
_RING_TIP = 16
_PINKY_TIP = 20

_THUMB_MCP = 2
_THUMB_IP = 3
_INDEX_MCP = 5
_MIDDLE_MCP = 9
_RING_MCP = 13
_PINKY_MCP = 17

_INDEX_PIP = 6
_MIDDLE_PIP = 10
_RING_PIP = 14
_PINKY_PIP = 18


def _distance(a: np.ndarray, b: np.ndarray) -> float:
    """Euclidean distance between two 3D points."""
    return float(np.linalg.norm(a - b))


def _is_finger_extended(
    landmarks: np.ndarray,
    tip_idx: int,
    pip_idx: int,
    mcp_idx: int,
) -> bool:
    """
    A finger is considered extended if the tip is farther from the MCP
    than the PIP joint is, indicating it's not curled.
    """
    tip = landmarks[tip_idx]
    pip = landmarks[pip_idx]
    mcp = landmarks[mcp_idx]

    tip_dist = _distance(tip, mcp)
    pip_dist = _distance(pip, mcp)

    return tip_dist > pip_dist * 1.02  # 2% margin — permissive for stable V detection


def _is_palm_facing_camera(landmarks: np.ndarray) -> bool:
    """
    Determine if the palm is facing toward the camera.

    Uses cross product of two palm vectors:
      vec1 = index_mcp - wrist
      vec2 = pinky_mcp - wrist
    The Z-component of the cross product indicates palm direction.

    In MediaPipe coordinates (right-hand rule):
      - Z increases away from camera
      - Cross product Z < 0 → palm faces camera (right hand)
      - Cross product Z > 0 → palm faces camera (left hand)

    We accept both hands by checking the absolute magnitude.
    The sign flips for left vs right hand, so we use a simpler
    heuristic: compare the average Z of fingertips vs palm landmarks.
    If fingertips are farther from camera (larger Z) than palm,
    the palm faces toward us.
    """
    # Palm landmarks (closer to camera when palm faces us)
    palm_z = np.mean([
        landmarks[_WRIST][2],
        landmarks[_INDEX_MCP][2],
        landmarks[_MIDDLE_MCP][2],
        landmarks[_RING_MCP][2],
        landmarks[_PINKY_MCP][2],
    ])

    # Fingertip landmarks (farther from camera when palm faces us)
    tips_z = np.mean([
        landmarks[_INDEX_TIP][2],
        landmarks[_MIDDLE_TIP][2],
        landmarks[_RING_TIP][2],
        landmarks[_PINKY_TIP][2],
    ])

    # When palm faces camera, fingertips curl backward (greater Z = farther)
    # This check is simpler and orientation-agnostic
    # For extended fingers (V sign), we use cross product instead
    vec1 = landmarks[_INDEX_MCP] - landmarks[_WRIST]
    vec2 = landmarks[_PINKY_MCP] - landmarks[_WRIST]
    cross = np.cross(vec1, vec2)

    # The magnitude of cross Z indicates confidence
    # Positive cross.z = palm faces camera for standard hand orientation
    # We accept either sign with enough magnitude (covers both hands)
    return float(cross[2]) > 0


def _is_victory_shape(landmarks: np.ndarray) -> bool:
    """
    Victory / peace sign: index + middle extended, ring + pinky curled.
    Palm orientation check disabled for debugging.
    """
    index_extended = _is_finger_extended(
        landmarks, _INDEX_TIP, _INDEX_PIP, _INDEX_MCP,
    )
    middle_extended = _is_finger_extended(
        landmarks, _MIDDLE_TIP, _MIDDLE_PIP, _MIDDLE_MCP,
    )
    ring_curled = not _is_finger_extended(
        landmarks, _RING_TIP, _RING_PIP, _RING_MCP,
    )
    pinky_curled = not _is_finger_extended(
        landmarks, _PINKY_TIP, _PINKY_PIP, _PINKY_MCP,
    )

    return index_extended and middle_extended and ring_curled and pinky_curled


def _is_l_shape(landmarks: np.ndarray) -> bool:
    """
    L-shape: index finger extended, middle/ring/pinky curled.
    Thumb and index must NOT be pinching (far apart).
    Thumb check is skipped — its joint mechanics are too different.
    """
    index_extended = _is_finger_extended(
        landmarks, _INDEX_TIP, _INDEX_PIP, _INDEX_MCP,
    )
    middle_curled = not _is_finger_extended(
        landmarks, _MIDDLE_TIP, _MIDDLE_PIP, _MIDDLE_MCP,
    )
    ring_curled = not _is_finger_extended(
        landmarks, _RING_TIP, _RING_PIP, _RING_MCP,
    )
    pinky_curled = not _is_finger_extended(
        landmarks, _PINKY_TIP, _PINKY_PIP, _PINKY_MCP,
    )
    # Ensure NOT pinching (thumb and index far apart)
    not_pinching = _distance(landmarks[_THUMB_TIP], landmarks[_INDEX_TIP]) > PINCH_THRESHOLD

    return index_extended and not_pinching and middle_curled and ring_curled and pinky_curled


def _classify_raw_gesture(landmarks: np.ndarray) -> GestureType:
    """
    Classify the raw gesture from a single frame of landmarks.

    Gesture scheme (three-pinch model):
      - Thumb + Index pinch  → PAN (full 2D)
      - Thumb + Middle pinch → ORBIT
      - Thumb + Ring pinch   → ZOOM

    Checked in order: index → middle → ring.
    """
    thumb_tip = landmarks[_THUMB_TIP]

    # 1. Thumb + Index pinch → PAN
    index_dist = _distance(thumb_tip, landmarks[_INDEX_TIP])
    if index_dist < PINCH_THRESHOLD:
        return GestureType.PAN

    # 2. Thumb + Middle pinch → ORBIT
    middle_dist = _distance(thumb_tip, landmarks[_MIDDLE_TIP])
    if middle_dist < PINCH_THRESHOLD:
        return GestureType.ORBIT

    # 3. Thumb + Ring pinch → ZOOM
    ring_dist = _distance(thumb_tip, landmarks[_RING_TIP])
    if ring_dist < PINCH_THRESHOLD:
        return GestureType.ZOOM

    return GestureType.IDLE


class GestureRecognizer:
    """
    Stateful gesture recognizer with transition buffering.

    Requires N consecutive frames of the same new gesture before
    switching from the current gesture. This prevents flickering
    during ambiguous hand poses.
    """

    def __init__(self) -> None:
        self._current_gesture = GestureType.IDLE
        self._candidate_gesture = GestureType.IDLE
        self._candidate_frames = 0

    @property
    def current_gesture(self) -> GestureType:
        return self._current_gesture

    def update(self, landmarks: np.ndarray) -> GestureType:
        """
        Process a new frame's landmarks and return the stable gesture.

        Parameters
        ----------
        landmarks : np.ndarray
            Shape (21, 3) hand landmarks.

        Returns
        -------
        GestureType
            The current stable gesture (only changes after N consistent frames).
        """
        raw_gesture = _classify_raw_gesture(landmarks)

        if raw_gesture == self._current_gesture:
            self._candidate_gesture = raw_gesture
            self._candidate_frames = 0
            return self._current_gesture

        if raw_gesture == self._candidate_gesture:
            self._candidate_frames += 1
            if self._candidate_frames >= GESTURE_SWITCH_FRAMES:
                self._current_gesture = raw_gesture
                self._candidate_frames = 0
        else:
            self._candidate_gesture = raw_gesture
            self._candidate_frames = 1

        return self._current_gesture

    def reset(self) -> None:
        """Reset to idle (e.g. when hand is lost)."""
        self._current_gesture = GestureType.IDLE
        self._candidate_gesture = GestureType.IDLE
        self._candidate_frames = 0
