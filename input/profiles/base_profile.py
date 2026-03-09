"""
HandNavigator — App Profile Base Contract

Defines the interface for application-specific navigation bindings.
Each 3D app has its own keyboard+mouse shortcuts for Pan, Zoom, Orbit.
Profiles encapsulate these differences behind a uniform contract.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class NavigationBinding:
    """
    Describes how to simulate a navigation action in a specific app.

    Attributes
    ----------
    modifiers : list[int]
        Virtual key codes to hold (e.g., [VK_MENU] for Alt).
    mouse_button : str
        Mouse button to hold during drag: "left", "middle", "right".
    use_scroll : bool
        If True, use mouse wheel instead of drag (for scroll-based zoom).
    """
    modifiers: List[int] = field(default_factory=list)
    mouse_button: str = "left"
    use_scroll: bool = False


class BaseProfile(ABC):
    """
    Abstract profile for a 3D application.
    Implement one profile per app target.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Display name of the application."""
        ...

    @abstractmethod
    def get_pan_binding(self) -> NavigationBinding:
        """Return the key+mouse combo for camera Pan."""
        ...

    @abstractmethod
    def get_zoom_binding(self) -> NavigationBinding:
        """Return the key+mouse combo for camera Zoom."""
        ...

    @abstractmethod
    def get_orbit_binding(self) -> NavigationBinding:
        """Return the key+mouse combo for camera Orbit."""
        ...
