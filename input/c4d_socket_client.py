# MIT License - Copyright (c) 2026 Flavio Takemoto
# See LICENSE file for full terms.

"""
HandNavigator — C4D Socket Client

Sends navigation deltas to Cinema 4D via UDP.
Replaces the Win32 mouse simulation approach with direct
camera control through the handnav_server.py C4D plugin.

Protocol: JSON over UDP to localhost:19700
"""

import json
import socket
from typing import Optional

from tracker.gesture_recognizer import GestureType
from tracker.navigation_solver import NavigationDelta


# ─── Configuration ───────────────────────────────────────────────────────────

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 19700


class C4DSocketClient:
    """
    UDP client that sends navigation deltas to the C4D plugin.

    Non-blocking, fire-and-forget. If C4D isn't listening,
    packets are silently dropped (UDP has no delivery guarantee).
    """

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
    ) -> None:
        self._host = host
        self._port = port
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Whether the socket was successfully created."""
        return self._sock is not None

    def send_navigation(self, delta: NavigationDelta) -> None:
        """
        Route a NavigationDelta to the appropriate C4D command.

        Parameters
        ----------
        delta : NavigationDelta
            The navigation delta from the tracker pipeline.
        """
        gesture = delta.gesture

        if gesture == GestureType.ZOOM:
            # L-shape: zoom only
            if abs(delta.dz) > 0.001:
                self._send({"action": "zoom", "dz": delta.dz})

        elif gesture == GestureType.ORBIT:
            if abs(delta.yaw) > 0.001 or abs(delta.pitch) > 0.001:
                self._send({
                    "action": "orbit",
                    "dx": delta.yaw,
                    "dy": delta.pitch,
                })

        elif gesture == GestureType.PAN:
            if abs(delta.dx) > 0.001 or abs(delta.dy) > 0.001:
                self._send({
                    "action": "pan",
                    "dx": delta.dx,
                    "dy": delta.dy,
                })

    def send_reset(self) -> None:
        """Send a camera reset command."""
        self._send({"action": "reset"})

    def _send(self, payload: dict) -> None:
        """Serialize and send a JSON command via UDP."""
        try:
            data = json.dumps(payload).encode("utf-8")
            self._sock.sendto(data, (self._host, self._port))
        except OSError:
            # Silently ignore send failures (C4D not running, etc.)
            pass

    def shutdown(self) -> None:
        """Close the UDP socket."""
        if self._sock:
            self._sock.close()
            self._sock = None
