# MIT License - Copyright (c) 2026 Flavio Takemoto
# See LICENSE file for full terms.

"""
HandNavigator — Win32 Input (Low Level)

Direct interface to Windows SendInput API via ctypes.
Provides mouse movement, button press/release, and keyboard key simulation.

Uses relative mouse movement (no MOUSEEVENTF_ABSOLUTE) so the cursor
moves by delta pixels from its current position — exactly how 3D apps
interpret mouse drag for camera navigation.

Reference: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput
"""

import ctypes
from ctypes import Structure, Union, c_int, c_long, c_short, c_uint, c_ulong, pointer

# ─── Win32 Constants ──────────────────────────────────────────────────────────

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

# Mouse event flags (relative movement by default — no ABSOLUTE flag)
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800

# Keyboard event flags
KEYEVENTF_KEYDOWN = 0x0000
KEYEVENTF_KEYUP = 0x0002

# Virtual key codes
VK_MENU = 0x12     # Alt
VK_SHIFT = 0x10    # Shift
VK_CONTROL = 0x11  # Ctrl

# Wheel delta (standard Windows scroll increment)
WHEEL_DELTA = 120


# ─── Win32 Structures ────────────────────────────────────────────────────────

class MOUSEINPUT(Structure):
    _fields_ = [
        ("dx", c_long),
        ("dy", c_long),
        ("mouseData", c_ulong),
        ("dwFlags", c_ulong),
        ("time", c_ulong),
        ("dwExtraInfo", ctypes.POINTER(c_ulong)),
    ]


class KEYBDINPUT(Structure):
    _fields_ = [
        ("wVk", c_short),
        ("wScan", c_short),
        ("dwFlags", c_ulong),
        ("time", c_ulong),
        ("dwExtraInfo", ctypes.POINTER(c_ulong)),
    ]


class HARDWAREINPUT(Structure):
    _fields_ = [
        ("uMsg", c_ulong),
        ("wParamL", c_short),
        ("wParamH", c_short),
    ]


class _InputUnion(Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(Structure):
    _fields_ = [
        ("type", c_ulong),
        ("union", _InputUnion),
    ]


# ─── SendInput function pointer ──────────────────────────────────────────────

_send_input = ctypes.windll.user32.SendInput
_send_input.argtypes = [c_uint, ctypes.POINTER(INPUT), c_int]
_send_input.restype = c_uint


# ─── Mouse Button Mappings ───────────────────────────────────────────────────

MOUSE_BUTTON_DOWN = {
    "left": MOUSEEVENTF_LEFTDOWN,
    "middle": MOUSEEVENTF_MIDDLEDOWN,
    "right": MOUSEEVENTF_RIGHTDOWN,
}

MOUSE_BUTTON_UP = {
    "left": MOUSEEVENTF_LEFTUP,
    "middle": MOUSEEVENTF_MIDDLEUP,
    "right": MOUSEEVENTF_RIGHTUP,
}


# ─── Public API ───────────────────────────────────────────────────────────────

def _make_extra_info():
    """Create a null pointer for dwExtraInfo."""
    return ctypes.POINTER(c_ulong)()


def send_mouse_move(dx: int, dy: int) -> None:
    """
    Move the mouse cursor by (dx, dy) pixels relative to current position.

    Parameters
    ----------
    dx : int
        Horizontal displacement (positive = right).
    dy : int
        Vertical displacement (positive = down).
    """
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.union.mi.dx = dx
    inp.union.mi.dy = dy
    inp.union.mi.mouseData = 0
    inp.union.mi.dwFlags = MOUSEEVENTF_MOVE
    inp.union.mi.time = 0
    inp.union.mi.dwExtraInfo = _make_extra_info()
    _send_input(1, pointer(inp), ctypes.sizeof(INPUT))


def send_mouse_button(button: str, down: bool) -> None:
    """
    Press or release a mouse button.

    Parameters
    ----------
    button : str
        "left", "middle", or "right".
    down : bool
        True = press, False = release.
    """
    flags = MOUSE_BUTTON_DOWN[button] if down else MOUSE_BUTTON_UP[button]

    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.union.mi.dx = 0
    inp.union.mi.dy = 0
    inp.union.mi.mouseData = 0
    inp.union.mi.dwFlags = flags
    inp.union.mi.time = 0
    inp.union.mi.dwExtraInfo = _make_extra_info()
    _send_input(1, pointer(inp), ctypes.sizeof(INPUT))


def send_mouse_scroll(delta: int) -> None:
    """
    Send mouse wheel scroll.

    Parameters
    ----------
    delta : int
        Positive = scroll up (zoom in), negative = scroll down (zoom out).
        Typically multiples of WHEEL_DELTA (120).
    """
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.union.mi.dx = 0
    inp.union.mi.dy = 0
    inp.union.mi.mouseData = delta
    inp.union.mi.dwFlags = MOUSEEVENTF_WHEEL
    inp.union.mi.time = 0
    inp.union.mi.dwExtraInfo = _make_extra_info()
    _send_input(1, pointer(inp), ctypes.sizeof(INPUT))


def send_key(vk_code: int, down: bool) -> None:
    """
    Press or release a keyboard key.

    Parameters
    ----------
    vk_code : int
        Virtual key code (e.g., VK_MENU for Alt).
    down : bool
        True = key down, False = key up.
    """
    flags = KEYEVENTF_KEYDOWN if down else KEYEVENTF_KEYUP

    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wVk = vk_code
    inp.union.ki.wScan = 0
    inp.union.ki.dwFlags = flags
    inp.union.ki.time = 0
    inp.union.ki.dwExtraInfo = _make_extra_info()
    _send_input(1, pointer(inp), ctypes.sizeof(INPUT))
