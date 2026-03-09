# MIT License - Copyright (c) 2026 Flavio Takemoto
# See LICENSE file for full terms.

"""
HandNavigator — MediaPipe Hand Detector

Thin wrapper around MediaPipe Tasks Hand Landmarker API.
Manages lifecycle and exposes landmarks in a clean interface.

Uses the new MediaPipe Tasks API (0.10.25+) — no more `mp.solutions`.
"""

import os
import sys
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker,
    HandLandmarkerOptions,
    RunningMode,
)

from tracker.config import (
    DETECTION_CONFIDENCE,
    MAX_NUM_HANDS,
    MODEL_COMPLEXITY,
    TRACKING_CONFIDENCE,
)


# ─── Hand connections for drawing (hardcoded to avoid mp.solutions) ──────────

_HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),       # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),       # Index
    (0, 9), (9, 10), (10, 11), (11, 12),   # Middle
    (0, 13), (13, 14), (14, 15), (15, 16), # Ring
    (0, 17), (17, 18), (18, 19), (19, 20), # Pinky
    (5, 9), (9, 13), (13, 17),             # Palm
]


@dataclass(frozen=True)
class HandLandmarks:
    """
    Processed hand landmarks from a single frame.

    Attributes
    ----------
    landmarks : np.ndarray
        Shape (21, 3) — normalized x, y, z for each landmark.
        x, y in [0, 1] relative to image. z is depth relative to wrist.
    handedness : str
        "Left" or "Right".
    raw_landmarks : object
        Original MediaPipe landmark list for potential further use.
    """
    landmarks: np.ndarray
    handedness: str
    raw_landmarks: object


def _find_model_path() -> str:
    """Locate the hand_landmarker.task model file."""
    # When running from a PyInstaller frozen EXE, resolve from _MEIPASS
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(__file__))

    candidates = [
        os.path.join(base_dir, "..", "models", "hand_landmarker.task"),
        os.path.join(base_dir, "models", "hand_landmarker.task"),
        os.path.join(os.path.dirname(__file__), "..", "models", "hand_landmarker.task"),
        os.path.join(os.path.dirname(__file__), "hand_landmarker.task"),
        "hand_landmarker.task",
    ]
    for path in candidates:
        if os.path.exists(path):
            return os.path.abspath(path)

    # Auto-download from Google's model repository
    import urllib.request

    model_dir = os.path.join(os.path.dirname(__file__), "..", "models")
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "hand_landmarker.task")

    url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
    print(f"[HandNavigator] Downloading hand landmarker model...")
    urllib.request.urlretrieve(url, model_path)
    print(f"[HandNavigator] Model saved to {model_path}")

    return os.path.abspath(model_path)


class HandDetector:
    """
    Wraps MediaPipe Tasks Hand Landmarker for single-hand detection.

    Usage
    -----
    >>> detector = HandDetector()
    >>> result = detector.detect(frame_bgr)
    >>> if result is not None:
    ...     print(result.landmarks.shape)  # (21, 3)
    >>> detector.release()
    """

    def __init__(self) -> None:
        model_path = _find_model_path()

        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=RunningMode.IMAGE,
            num_hands=MAX_NUM_HANDS,
            min_hand_detection_confidence=DETECTION_CONFIDENCE,
            min_hand_presence_confidence=DETECTION_CONFIDENCE,
            min_tracking_confidence=TRACKING_CONFIDENCE,
        )
        self._landmarker = HandLandmarker.create_from_options(options)

    def detect(self, frame_bgr: np.ndarray) -> Optional[HandLandmarks]:
        """
        Process a BGR frame and return hand landmarks if detected.

        Parameters
        ----------
        frame_bgr : np.ndarray
            Input frame in BGR format (OpenCV default).

        Returns
        -------
        HandLandmarks or None
            Detected hand data, or None if no hand found.
        """
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        result = self._landmarker.detect(mp_image)

        if not result.hand_landmarks:
            return None

        raw_landmarks = result.hand_landmarks[0]
        handedness_label = result.handedness[0][0].category_name

        # Convert to numpy array (21, 3)
        landmarks_array = np.array(
            [(lm.x, lm.y, lm.z) for lm in raw_landmarks],
            dtype=np.float32,
        )

        return HandLandmarks(
            landmarks=landmarks_array,
            handedness=handedness_label,
            raw_landmarks=raw_landmarks,
        )

    def draw_landmarks(
        self,
        frame: np.ndarray,
        hand: HandLandmarks,
    ) -> np.ndarray:
        """Draw hand landmarks and connections on the frame (mutates in place)."""
        h, w = frame.shape[:2]

        # Draw connections
        for start_idx, end_idx in _HAND_CONNECTIONS:
            x1 = int(hand.landmarks[start_idx][0] * w)
            y1 = int(hand.landmarks[start_idx][1] * h)
            x2 = int(hand.landmarks[end_idx][0] * w)
            y2 = int(hand.landmarks[end_idx][1] * h)
            cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 128), 2)

        # Draw landmark points
        for i in range(21):
            x = int(hand.landmarks[i][0] * w)
            y = int(hand.landmarks[i][1] * h)
            color = (0, 0, 255) if i == 0 else (255, 255, 255)
            cv2.circle(frame, (x, y), 4, color, -1)

        return frame

    def release(self) -> None:
        """Release MediaPipe resources."""
        self._landmarker.close()
