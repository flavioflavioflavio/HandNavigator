"""
HandNavigator — Cinema 4D Profile

Camera shortcuts:
  - Orbit: Alt + Left Mouse Button drag
  - Pan:   Alt + Middle Mouse Button drag
  - Zoom:  Alt + Right Mouse Button drag

Also works for Maya (identical shortcuts).
"""

from input.profiles.base_profile import BaseProfile, NavigationBinding
from input.win32_input import VK_MENU


class Cinema4DProfile(BaseProfile):
    """Navigation bindings for Cinema 4D (and Maya)."""

    @property
    def name(self) -> str:
        return "Cinema 4D"

    def get_pan_binding(self) -> NavigationBinding:
        return NavigationBinding(
            modifiers=[VK_MENU],
            mouse_button="middle",
        )

    def get_zoom_binding(self) -> NavigationBinding:
        return NavigationBinding(
            modifiers=[VK_MENU],
            mouse_button="right",
        )

    def get_orbit_binding(self) -> NavigationBinding:
        return NavigationBinding(
            modifiers=[VK_MENU],
            mouse_button="left",
        )
