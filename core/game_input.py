from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_WHEEL = 0x0800
WHEEL_DELTA = 120
MAPVK_VK_TO_VSC = 0

ULONG_PTR = wintypes.WPARAM

_SPECIAL_SCAN_CODES = {
    "esc": 0x01,
    "escape": 0x01,
}


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _anonymous_ = ("data",)
    _fields_ = [("type", wintypes.DWORD), ("data", INPUT_UNION)]


_user32 = ctypes.WinDLL("user32", use_last_error=True)
_user32.MapVirtualKeyW.argtypes = (wintypes.UINT, wintypes.UINT)
_user32.MapVirtualKeyW.restype = wintypes.UINT
_user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
_user32.SendInput.restype = wintypes.UINT


def _send(event: INPUT) -> None:
    sent = _user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
    if sent != 1:
        raise ctypes.WinError(ctypes.get_last_error())


def _scan_code(key: str) -> int:
    normalized = key.casefold()
    if normalized in _SPECIAL_SCAN_CODES:
        return _SPECIAL_SCAN_CODES[normalized]
    if len(key) != 1:
        raise ValueError(f"Неизвестная клавиша: {key!r}")
    virtual_key = ord(key.upper())
    scan = _user32.MapVirtualKeyW(virtual_key, MAPVK_VK_TO_VSC)
    if not scan:
        raise RuntimeError(f"Windows не нашла scan-code для клавиши {key!r}.")
    return int(scan)


def _send_scan(scan: int, *, key_up: bool) -> None:
    flags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if key_up else 0)
    event = INPUT(
        type=INPUT_KEYBOARD,
        data=INPUT_UNION(
            ki=KEYBDINPUT(
                wVk=0,
                wScan=scan,
                dwFlags=flags,
                time=0,
                dwExtraInfo=0,
            )
        ),
    )
    _send(event)


def release_key(key: str) -> None:
    _send_scan(_scan_code(key), key_up=True)


def tap_key(key: str, hold_seconds: float = 0.075) -> None:
    scan = _scan_code(key)
    _send_scan(scan, key_up=True)
    time.sleep(0.025)
    _send_scan(scan, key_up=False)
    try:
        time.sleep(max(0.03, hold_seconds))
    finally:
        _send_scan(scan, key_up=True)


def _absolute_point(x: int, y: int) -> tuple[int, int]:
    width = max(1, _user32.GetSystemMetrics(0) - 1)
    height = max(1, _user32.GetSystemMetrics(1) - 1)
    return round(x * 65535 / width), round(y * 65535 / height)


def move_screen(x: int, y: int) -> None:
    absolute_x, absolute_y = _absolute_point(x, y)
    _send(
        INPUT(
            type=INPUT_MOUSE,
            data=INPUT_UNION(
                mi=MOUSEINPUT(
                    absolute_x,
                    absolute_y,
                    0,
                    MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE,
                    0,
                    0,
                )
            ),
        )
    )


def click_screen(x: int, y: int) -> None:
    """Move and click using physical Windows screen coordinates."""
    move_screen(x, y)
    time.sleep(0.10)
    _send(
        INPUT(
            type=INPUT_MOUSE,
            data=INPUT_UNION(mi=MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, 0)),
        )
    )
    time.sleep(0.06)
    _send(
        INPUT(
            type=INPUT_MOUSE,
            data=INPUT_UNION(mi=MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, 0)),
        )
    )


def scroll_screen(
    x: int,
    y: int,
    notches: int,
    *,
    interval: float = 0.045,
) -> None:
    """Turn the mouse wheel over one screen point.

    Positive notches scroll upward; negative notches scroll downward. Events are
    sent one notch at a time because Pal can ignore a large combined wheel delta.
    """
    if notches == 0:
        return
    move_screen(x, y)
    time.sleep(0.06)
    delta = WHEEL_DELTA if notches > 0 else -WHEEL_DELTA
    wheel_data = ctypes.c_uint32(delta).value
    for _ in range(abs(notches)):
        _send(
            INPUT(
                type=INPUT_MOUSE,
                data=INPUT_UNION(
                    mi=MOUSEINPUT(0, 0, wheel_data, MOUSEEVENTF_WHEEL, 0, 0)
                ),
            )
        )
        time.sleep(max(0.015, interval))


def drag_screen(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    *,
    duration: float = 0.45,
    steps: int = 18,
) -> None:
    """Drag between physical screen points with a real held left mouse button."""
    move_screen(start_x, start_y)
    time.sleep(0.10)
    _send(
        INPUT(
            type=INPUT_MOUSE,
            data=INPUT_UNION(mi=MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, 0)),
        )
    )
    try:
        for step in range(1, max(2, steps) + 1):
            fraction = step / max(2, steps)
            x = round(start_x + (end_x - start_x) * fraction)
            y = round(start_y + (end_y - start_y) * fraction)
            move_screen(x, y)
            time.sleep(max(0.01, duration / max(2, steps)))
    finally:
        _send(
            INPUT(
                type=INPUT_MOUSE,
                data=INPUT_UNION(mi=MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, 0)),
            )
        )
    time.sleep(0.08)
