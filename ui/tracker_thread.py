# MIT License - Copyright (c) 2026 Flavio Takemoto
# See LICENSE file for full terms.

"""
HandNavigator — Tracker Thread

QThread that runs the webcam + MediaPipe hand tracking loop
and emits Qt signals with processed data (frame, gesture, delta).

This keeps the UI responsive while tracking runs at full speed
on a separate thread.
"""

import time
from typing import Optional

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from tracker.config import (
    CAMERA_HEIGHT,
    CAMERA_INDEX,
    CAMERA_WIDTH,
    SMOOTHING_POSITION,
    SMOOTHING_ROTATION,
    TARGET_FPS,
    PAN_SENSITIVITY,
    ZOOM_SENSITIVITY,
    ORBIT_SENSITIVITY,
)
from tracker.gesture_recognizer import GestureRecognizer, GestureType
from tracker.hand_detector import HandDetector, HandLandmarks
from tracker.navigation_solver import NavigationDelta, NavigationSolver
from tracker.smoothing import MultiAxisFilter

# Number of hand landmarks from MediaPipe
_NUM_LANDMARKS = 21


class TrackerThread(QThread):
    """
    Background thread that captures webcam frames, detects hand
    landmarks, classifies gestures, and computes navigation deltas.

    Signals
    -------
    frame_ready(np.ndarray, GestureType)
        Emitted each frame with the annotated BGR image and current gesture.
    navigation_ready(NavigationDelta, int, int)
        Emitted each frame with the navigation delta and mouse pixel values.
    gesture_changed(GestureType)
        Emitted only when the stable gesture switches to a new type.
    """

    frame_ready = pyqtSignal(np.ndarray, object)
    navigation_ready = pyqtSignal(object, int, int)
    gesture_changed = pyqtSignal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._running = False

    def stop(self) -> None:
        """Signal the thread to stop gracefully."""
        self._running = False

    def run(self) -> None:
        """Main tracking loop — runs on the background thread."""
        self._running = True

        detector = HandDetector()
        recognizer = GestureRecognizer()
        solver = NavigationSolver()

        pos_filter = MultiAxisFilter(
            axes=3,
            min_cutoff=SMOOTHING_POSITION.min_cutoff,
            beta=SMOOTHING_POSITION.beta,
            d_cutoff=SMOOTHING_POSITION.d_cutoff,
        )
        rot_filter = MultiAxisFilter(
            axes=2,
            min_cutoff=SMOOTHING_ROTATION.min_cutoff,
            beta=SMOOTHING_ROTATION.beta,
            d_cutoff=SMOOTHING_ROTATION.d_cutoff,
        )

        # Per-landmark smoothing filters to stabilize gesture detection
        landmark_filters: list[MultiAxisFilter] = [
            MultiAxisFilter(axes=3, min_cutoff=1.0, beta=0.01, d_cutoff=1.0)
            for _ in range(_NUM_LANDMARKS)
        ]

        cap = cv2.VideoCapture(CAMERA_INDEX)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, TARGET_FPS)

        if not cap.isOpened():
            return

        prev_gesture = GestureType.IDLE

        try:
            while self._running:
                ret, frame = cap.read()
                if not ret:
                    continue

                frame = cv2.flip(frame, 1)
                hand = detector.detect(frame)

                if hand is None:
                    if prev_gesture != GestureType.IDLE:
                        recognizer.reset()
                        solver.reset()
                        pos_filter.reset()
                        rot_filter.reset()
                        for lf in landmark_filters:
                            lf.reset()
                        prev_gesture = GestureType.IDLE
                        self.gesture_changed.emit(GestureType.IDLE)

                    delta = NavigationDelta(gesture=GestureType.IDLE)
                    self.frame_ready.emit(frame, GestureType.IDLE)
                    self.navigation_ready.emit(delta, 0, 0)
                else:
                    now = time.perf_counter()

                    # Smooth ALL landmarks to prevent gesture flicker
                    # (especially V-sign finger jitter → orbit snap)
                    smoothed = hand.landmarks.copy()
                    for i in range(_NUM_LANDMARKS):
                        smoothed[i] = np.array(
                            landmark_filters[i].apply(
                                tuple(smoothed[i]), timestamp=now,
                            ),
                            dtype=np.float32,
                        )

                    gesture = recognizer.update(smoothed)

                    if gesture != prev_gesture:
                        solver.reset()
                        prev_gesture = gesture
                        self.gesture_changed.emit(gesture)

                    delta = solver.compute(smoothed, gesture)
                    mx, my = self._delta_to_pixels(delta)

                    # Draw landmarks on frame for PIP display
                    detector.draw_landmarks(frame, hand)

                    self.frame_ready.emit(frame, gesture)
                    self.navigation_ready.emit(delta, mx, my)

                # Limit frame rate to avoid excessive CPU usage
                time.sleep(0.001)

        finally:
            detector.release()
            cap.release()

    @staticmethod
    def _delta_to_pixels(delta: NavigationDelta) -> tuple[int, int]:
        """Convert navigation delta to pixel mouse displacement."""
        if delta.gesture == GestureType.PAN:
            return int(delta.dx * PAN_SENSITIVITY), int(delta.dy * PAN_SENSITIVITY)
        elif delta.gesture == GestureType.ZOOM:
            # L-shape: zoom only (vertical)
            return (0, int(delta.dz * ZOOM_SENSITIVITY))
        elif delta.gesture == GestureType.ORBIT:
            return (
                int(delta.yaw * ORBIT_SENSITIVITY * 50),
                int(delta.pitch * ORBIT_SENSITIVITY * 50),
            )
        return 0, 0
