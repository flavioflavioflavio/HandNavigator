# MIT License - Copyright (c) 2026 Flavio Takemoto
# See LICENSE file for full terms.

"""
HandNavigator — One-Euro Smoothing Filter

Adaptive low-pass filter that balances smoothness vs responsiveness.
When the hand moves slowly → heavy smoothing (removes jitter).
When the hand moves fast → light smoothing (preserves responsiveness).

Reference: https://cristal.univ-lille.fr/~casiez/1euro/
"""

import math
import time


class LowPassFilter:
    """Simple exponential smoothing (first-order IIR low-pass)."""

    __slots__ = ("_y", "_s", "_initialized")

    def __init__(self) -> None:
        self._y: float = 0.0
        self._s: float = 0.0
        self._initialized = False

    @property
    def last_value(self) -> float:
        return self._s

    def apply(self, value: float, alpha: float) -> float:
        if self._initialized:
            self._s = alpha * value + (1.0 - alpha) * self._s
        else:
            self._s = value
            self._initialized = True
        return self._s

    def reset(self) -> None:
        self._initialized = False


class OneEuroFilter:
    """
    One-Euro Filter for a single scalar value.

    Parameters
    ----------
    min_cutoff : float
        Minimum cutoff frequency (Hz). Lower = smoother at rest.
    beta : float
        Speed coefficient. Higher = more responsive to fast changes.
    d_cutoff : float
        Derivative cutoff frequency. Usually leave at 1.0.
    """

    __slots__ = (
        "_min_cutoff", "_beta", "_d_cutoff",
        "_x_filter", "_dx_filter",
        "_last_time", "_frequency",
    )

    def __init__(
        self,
        min_cutoff: float = 1.0,
        beta: float = 0.007,
        d_cutoff: float = 1.0,
    ) -> None:
        self._min_cutoff = min_cutoff
        self._beta = beta
        self._d_cutoff = d_cutoff
        self._x_filter = LowPassFilter()
        self._dx_filter = LowPassFilter()
        self._last_time: float | None = None
        self._frequency = 30.0  # initial estimate

    @staticmethod
    def _smoothing_factor(cutoff: float, rate: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        te = 1.0 / rate
        return 1.0 / (1.0 + tau / te)

    def apply(self, value: float, timestamp: float | None = None) -> float:
        """Filter a new sample and return the smoothed value."""
        now = timestamp if timestamp is not None else time.perf_counter()

        if self._last_time is not None:
            dt = now - self._last_time
            if dt > 0:
                self._frequency = 1.0 / dt

        self._last_time = now

        # Estimate derivative (speed of change)
        prev = self._x_filter.last_value
        dx = (value - prev) * self._frequency if self._x_filter._initialized else 0.0

        # Smooth the derivative
        alpha_d = self._smoothing_factor(self._d_cutoff, self._frequency)
        edx = self._dx_filter.apply(dx, alpha_d)

        # Adaptive cutoff: faster movement → higher cutoff → less smoothing
        cutoff = self._min_cutoff + self._beta * abs(edx)
        alpha = self._smoothing_factor(cutoff, self._frequency)

        return self._x_filter.apply(value, alpha)

    def reset(self) -> None:
        """Reset filter state (e.g. when hand is lost and redetected)."""
        self._x_filter.reset()
        self._dx_filter.reset()
        self._last_time = None


class MultiAxisFilter:
    """
    Applies independent One-Euro Filters to multiple axes.
    Useful for smoothing (x, y, z) positions or (yaw, pitch) rotations.
    """

    __slots__ = ("_filters",)

    def __init__(
        self,
        axes: int,
        min_cutoff: float = 1.0,
        beta: float = 0.007,
        d_cutoff: float = 1.0,
    ) -> None:
        self._filters = tuple(
            OneEuroFilter(min_cutoff, beta, d_cutoff)
            for _ in range(axes)
        )

    def apply(
        self,
        values: tuple[float, ...],
        timestamp: float | None = None,
    ) -> tuple[float, ...]:
        return tuple(
            f.apply(v, timestamp)
            for f, v in zip(self._filters, values)
        )

    def reset(self) -> None:
        for f in self._filters:
            f.reset()
