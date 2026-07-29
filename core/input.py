from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
MAPVK_VK_TO_VSC = 0

ULONG_PTR = wintypes.WPARAM


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
    _anonymous_ = ("union",)
    _fields_ = [("type", wintypes.DWORD), ("union", INPUT_UNION)]


_user32 = ctypes.windll.user32
_user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
_user32.SendInput.restype = wintypes.UINT


def _scan_code(key: str) -> int:
    if len(key) != 1:
        raise ValueError(f"Поддерживается только одиночная клавиша, получено: {key!r}")
    virtual_key = ord(key.upper())
    scan = _user32.MapVirtualKeyW(virtual_key, MAPVK_VK_TO_VSC)
    if not scan:
        raise RuntimeError(f"Windows не нашла scan-code для клавиши {key!r}.")
    return int(scan)


def _send_scan(scan: int, key_up: bool) -> None:
    flags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if key_up else 0)
    event = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(0, scan, flags, 0, 0))
    sent = _user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
    if sent != 1:
        raise ctypes.WinError(ctypes.get_last_error())


def release_key(key: str) -> None:
    _send_scan(_scan_code(key), key_up=True)


def tap_key(key: str, hold_seconds: float = 0.075) -> None:
    """Надёжный короткий DirectInput-совместимый клик клавиши.

    Сначала отправляется key-up, чтобы снять возможное зависшее состояние,
    а в finally key-up отправляется повторно даже при ошибке.
    """

    scan = _scan_code(key)
    _send_scan(scan, key_up=True)
    time.sleep(0.025)
    _send_scan(scan, key_up=False)
    try:
        time.sleep(max(0.03, hold_seconds))
    finally:
        _send_scan(scan, key_up=True)
