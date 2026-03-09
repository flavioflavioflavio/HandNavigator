# MIT License - Copyright (c) 2026 Flavio Takemoto
# See LICENSE file for full terms.

"""
HandNavigator — Input Simulator (High Level)

Orchestrates Win32 input based on navigation gestures.
Manages the state machine: which modifier keys and mouse buttons
are currently held, and coordinates transitions between gestures.

Flow:
  1. Gesture starts → press modifier keys + mouse button
  2. Each frame   → send relative mouse movement (delta)
  3. Gesture ends  → release mouse button + modifier keys

All transitions go through a clean release to avoid ghost inputs.
"""

from typing import Optional

from input.profiles.base_profile import BaseProfile, NavigationBinding
from input.win32_input import (
    WHEEL_DELTA,
    send_key,
    send_mouse_button,
    send_mouse_move,
    send_mouse_scroll,
)
from tracker.gesture_recognizer import GestureType


class InputSimulator:
    """
    High-level input coordinator.

    Translates navigation gestures into Win32 keyboard+mouse input
    using the active app profile's key bindings.
    """

    def __init__(self, profile: BaseProfile) -> None:
        self._profile = profile
        self._active_binding: Optional[NavigationBinding] = None
        self._active_gesture = GestureType.IDLE

    @property
    def profile_name(self) -> str:
        return self._profile.name

    @property
    def active_gesture(self) -> GestureType:
        return self._active_gesture

    def _get_binding_for_gesture(self, gesture: GestureType) -> Optional[NavigationBinding]:
        """Look up the profile's binding for a given gesture."""
        if gesture == GestureType.PAN:
            return self._profile.get_pan_binding()
        elif gesture == GestureType.ZOOM:
            return self._profile.get_zoom_binding()
        elif gesture == GestureType.ORBIT:
            return self._profile.get_orbit_binding()
        return None

    def _press_binding(self, binding: NavigationBinding) -> None:
        """Press all modifier keys and the mouse button for a binding."""
        for vk in binding.modifiers:
            send_key(vk, down=True)
        if not binding.use_scroll:
            send_mouse_button(binding.mouse_button, down=True)

    def _release_binding(self, binding: NavigationBinding) -> None:
        """Release all modifier keys and the mouse button for a binding."""
        if not binding.use_scroll:
            send_mouse_button(binding.mouse_button, down=False)
        for vk in reversed(binding.modifiers):
            send_key(vk, down=False)

    def begin_gesture(self, gesture: GestureType) -> None:
        """
        Start a new gesture action.
        If a different gesture is already active, ends it first.
        """
        if gesture == self._active_gesture:
            return  # Already in this gesture

        # Clean release of previous gesture
        if self._active_binding is not None:
            self._release_binding(self._active_binding)
            self._active_binding = None

        self._active_gesture = gesture

        if gesture == GestureType.IDLE:
            return

        binding = self._get_binding_for_gesture(gesture)
        if binding is not None:
            self._active_binding = binding
            self._press_binding(binding)

    def update(self, dx: int, dy: int) -> None:
        """
        Send mouse movement delta while a gesture is active.

        Parameters
        ----------
        dx : int
            Horizontal mouse movement in pixels.
        dy : int
            Vertical mouse movement in pixels.
        """
        if self._active_gesture == GestureType.IDLE:
            return

        if self._active_binding and self._active_binding.use_scroll:
            # Scroll-based zoom: convert dy to scroll delta
            if dy != 0:
                scroll_amount = -dy * (WHEEL_DELTA // 10)
                send_mouse_scroll(scroll_amount)
        else:
            # Standard drag: send relative mouse movement
            if dx != 0 or dy != 0:
                send_mouse_move(dx, dy)

    def end_gesture(self) -> None:
        """Release all held keys/buttons and return to idle."""
        self.begin_gesture(GestureType.IDLE)

    def shutdown(self) -> None:
        """
        Emergency release of everything.
        Call on app exit to ensure no keys/buttons stuck.
        """
        self.end_gesture()
