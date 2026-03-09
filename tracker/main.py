# MIT License - Copyright (c) 2026 Flavio Takemoto
# See LICENSE file for full terms.

"""
HandNavigator — Main Entry Point

The main loop that wires everything together:
  Webcam → MediaPipe → Gesture → Delta → Win32 Input

Press 'Q' in the debug window or Ctrl+C in terminal to quit.
"""

import sys
import time

import cv2
import numpy as np

from tracker.config import (
    ACTIVE_PROFILE,
    CAMERA_HEIGHT,
    CAMERA_INDEX,
    CAMERA_WIDTH,
    DEBUG_WINDOW_NAME,
    ORBIT_SENSITIVITY,
    PAN_SENSITIVITY,
    SHOW_DEBUG_WINDOW,
    SMOOTHING_POSITION,
    SMOOTHING_ROTATION,
    TARGET_FPS,
    ZOOM_SENSITIVITY,
)
from tracker.gesture_recognizer import GestureRecognizer, GestureType
from tracker.hand_detector import HandDetector
from tracker.navigation_solver import NavigationDelta, NavigationSolver
from tracker.smoothing import MultiAxisFilter

from input.input_simulator import InputSimulator
from input.profiles.cinema4d import Cinema4DProfile
from input.profiles.blender import BlenderProfile


# ─── Profile Registry ────────────────────────────────────────────────────────

PROFILE_MAP = {
    "cinema4d": Cinema4DProfile,
    "blender": BlenderProfile,
}


# ─── Gesture Colors for Debug Overlay ─────────────────────────────────────────

GESTURE_COLORS = {
    GestureType.IDLE:  (128, 128, 128),  # Gray
    GestureType.PAN:   (0, 255, 128),    # Green
    GestureType.ZOOM:  (0, 200, 255),    # Orange-yellow
    GestureType.ORBIT: (255, 100, 100),  # Blue-ish
}

GESTURE_LABELS = {
    GestureType.IDLE:  "IDLE",
    GestureType.PAN:   "PAN  (Open Hand)",
    GestureType.ZOOM:  "ZOOM (Pinch)",
    GestureType.ORBIT: "ORBIT (Fist)",
}


def _delta_to_mouse_pixels(delta: NavigationDelta) -> tuple[int, int]:
    """Convert normalized navigation delta to pixel mouse movement."""
    if delta.gesture == GestureType.PAN:
        mx = int(delta.dx * PAN_SENSITIVITY)
        my = int(delta.dy * PAN_SENSITIVITY)
        return mx, my

    elif delta.gesture == GestureType.ZOOM:
        # Zoom uses dz mapped to vertical mouse movement
        my = int(delta.dz * ZOOM_SENSITIVITY)
        return 0, my

    elif delta.gesture == GestureType.ORBIT:
        mx = int(delta.yaw * ORBIT_SENSITIVITY * 100)
        my = int(delta.pitch * ORBIT_SENSITIVITY * 100)
        return mx, my

    return 0, 0


def _draw_debug_overlay(
    frame: np.ndarray,
    gesture: GestureType,
    delta: NavigationDelta,
    fps: float,
    profile_name: str,
) -> np.ndarray:
    """Draw status information on the debug frame."""
    color = GESTURE_COLORS[gesture]
    label = GESTURE_LABELS[gesture]

    # Background bar at top
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 80), (20, 20, 20), -1)

    # Gesture label
    cv2.putText(
        frame, label, (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2,
    )

    # Delta values
    delta_text = f"dx:{delta.dx:+.4f}  dy:{delta.dy:+.4f}  dz:{delta.dz:+.4f}"
    cv2.putText(
        frame, delta_text, (10, 55),
        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1,
    )

    # FPS + Profile
    info_text = f"FPS: {fps:.0f}  |  Profile: {profile_name}"
    cv2.putText(
        frame, info_text, (10, 75),
        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1,
    )

    # Gesture indicator circle
    cv2.circle(frame, (frame.shape[1] - 40, 40), 20, color, -1)

    return frame


def main() -> None:
    """Main application loop."""
    # ─── Initialize Profile ──────────────────────────────────────────────
    profile_cls = PROFILE_MAP.get(ACTIVE_PROFILE)
    if profile_cls is None:
        print(f"[ERROR] Unknown profile: '{ACTIVE_PROFILE}'")
        print(f"Available: {list(PROFILE_MAP.keys())}")
        sys.exit(1)

    profile = profile_cls()
    simulator = InputSimulator(profile)
    print(f"[HandNavigator] Profile: {profile.name}")

    # ─── Initialize Tracker ──────────────────────────────────────────────
    detector = HandDetector()
    recognizer = GestureRecognizer()
    solver = NavigationSolver()

    # Smoothing filters for position (3 axes) and rotation (2 axes)
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

    # ─── Open Webcam ─────────────────────────────────────────────────────
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, TARGET_FPS)

    if not cap.isOpened():
        print("[ERROR] Could not open webcam")
        sys.exit(1)

    print(f"[HandNavigator] Webcam opened ({CAMERA_WIDTH}x{CAMERA_HEIGHT} @ {TARGET_FPS}fps)")
    print("[HandNavigator] Show your hand to start navigating. Press 'Q' to quit.")

    frame_time = time.perf_counter()
    fps = 0.0
    prev_gesture = GestureType.IDLE

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Flip horizontally for mirror-like interaction
            frame = cv2.flip(frame, 1)

            # ─── Detect Hand ─────────────────────────────────────────
            hand = detector.detect(frame)

            if hand is None:
                # No hand → stop any active gesture
                if prev_gesture != GestureType.IDLE:
                    simulator.end_gesture()
                    recognizer.reset()
                    solver.reset()
                    pos_filter.reset()
                    rot_filter.reset()
                    prev_gesture = GestureType.IDLE

                delta = NavigationDelta(gesture=GestureType.IDLE)
            else:
                # ─── Smooth Landmarks ────────────────────────────────
                now = time.perf_counter()
                smoothed_landmarks = hand.landmarks.copy()

                # Smooth wrist position (landmark 0)
                wrist_smooth = pos_filter.apply(
                    tuple(hand.landmarks[0]), timestamp=now,
                )
                smoothed_landmarks[0] = np.array(wrist_smooth, dtype=np.float32)

                # ─── Classify Gesture ────────────────────────────────
                gesture = recognizer.update(smoothed_landmarks)

                # ─── Handle Gesture Transitions ──────────────────────
                if gesture != prev_gesture:
                    solver.reset()
                    simulator.begin_gesture(gesture)
                    prev_gesture = gesture

                # ─── Compute Delta ───────────────────────────────────
                delta = solver.compute(smoothed_landmarks, gesture)

                # ─── Send Input ──────────────────────────────────────
                mx, my = _delta_to_mouse_pixels(delta)
                simulator.update(mx, my)

                # ─── Draw landmarks on debug frame ───────────────────
                if SHOW_DEBUG_WINDOW:
                    detector.draw_landmarks(frame, hand)

            # ─── FPS Calculation ─────────────────────────────────────
            now = time.perf_counter()
            dt = now - frame_time
            fps = 1.0 / dt if dt > 0 else 0
            frame_time = now

            # ─── Debug Window ────────────────────────────────────────
            if SHOW_DEBUG_WINDOW:
                frame = _draw_debug_overlay(
                    frame, prev_gesture, delta, fps, simulator.profile_name,
                )
                cv2.imshow(DEBUG_WINDOW_NAME, frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord("q") or key == ord("Q"):
                    break
            else:
                # Without debug window, use minimal delay
                time.sleep(0.001)

    except KeyboardInterrupt:
        print("\n[HandNavigator] Interrupted by user")
    finally:
        # ─── Cleanup ─────────────────────────────────────────────────
        simulator.shutdown()
        detector.release()
        cap.release()
        if SHOW_DEBUG_WINDOW:
            cv2.destroyAllWindows()
        print("[HandNavigator] Shutdown complete")


if __name__ == "__main__":
    main()
