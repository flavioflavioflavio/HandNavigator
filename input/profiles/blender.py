"""
HandNavigator — Blender Profile

Camera shortcuts (default keymap):
  - Orbit: Middle Mouse Button drag
  - Pan:   Shift + Middle Mouse Button drag
  - Zoom:  Scroll wheel (or Ctrl + MMB drag)
"""

from input.profiles.base_profile import BaseProfile, NavigationBinding
from input.win32_input import VK_SHIFT


class BlenderProfile(BaseProfile):
    """Navigation bindings for Blender (default keymap)."""

    @property
    def name(self) -> str:
        return "Blender"

    def get_pan_binding(self) -> NavigationBinding:
        return NavigationBinding(
            modifiers=[VK_SHIFT],
            mouse_button="middle",
        )

    def get_zoom_binding(self) -> NavigationBinding:
        return NavigationBinding(
            modifiers=[],
            mouse_button="middle",
            use_scroll=True,
        )

    def get_orbit_binding(self) -> NavigationBinding:
        return NavigationBinding(
            modifiers=[],
            mouse_button="middle",
        )
