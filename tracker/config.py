# MIT License - Copyright (c) 2026 Flavio Takemoto
# See LICENSE file for full terms.

"""
HandNavigator — Configuration Constants

All tunable parameters for the virtual 3D mouse.
Adjust sensitivity, smoothing, and gesture thresholds here.
"""

from dataclasses import dataclass


# ─── Webcam ───────────────────────────────────────────────────────────────────

CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
TARGET_FPS = 30


# ─── MediaPipe ────────────────────────────────────────────────────────────────

DETECTION_CONFIDENCE = 0.7
TRACKING_CONFIDENCE = 0.7
MODEL_COMPLEXITY = 1  # 0 = fast, 1 = balanced, 2 = precise
MAX_NUM_HANDS = 1


# ─── Sensitivity (pixels of mouse movement per unit of hand delta) ────────────

PAN_SENSITIVITY = 800.0
ZOOM_SENSITIVITY = 1200.0
ORBIT_SENSITIVITY = 80.0      # Low — orbit needs fine control


# ─── Dead Zones (ignore micro-movements below threshold) ─────────────────────

DEAD_ZONE_TRANSLATION = 0.003
DEAD_ZONE_ROTATION = 0.015


# ─── Gesture Detection ───────────────────────────────────────────────────────

PINCH_THRESHOLD = 0.07        # Max thumb-index tip distance to count as pinch
GESTURE_SWITCH_FRAMES = 3     # Consecutive frames to confirm gesture switch


# ─── One-Euro Smoothing Filter ───────────────────────────────────────────────

@dataclass(frozen=True)
class SmoothingConfig:
    """
    One-Euro Filter tuning.
    - min_cutoff: lower = smoother when hand is still
    - beta: higher = more responsive to fast movements
    - d_cutoff: derivative cutoff frequency (usually 1.0)
    """
    min_cutoff: float = 1.0
    beta: float = 0.007
    d_cutoff: float = 1.0


SMOOTHING_POSITION = SmoothingConfig(min_cutoff=1.0, beta=0.007)
SMOOTHING_ROTATION = SmoothingConfig(min_cutoff=0.8, beta=0.01)


# ─── Active App Profile ──────────────────────────────────────────────────────

ACTIVE_PROFILE = "cinema4d"  # "cinema4d" | "blender"


# ─── Debug / Visualization ────────────────────────────────────────────────────

SHOW_DEBUG_WINDOW = True
DEBUG_WINDOW_NAME = "HandNavigator"
