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
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = [("type", wintypes.DWORD), ("union", INPUT_UNION)]


_user32 = ctypes.windll.user32
_user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
_user32.SendInput.restype = wintypes.UINT


def _send(event: INPUT) -> None:
    sent = _user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
    if sent != 1:
        raise ctypes.WinError(ctypes.get_last_error())


def _scan_code(key: str) -> int:
    if len(key) != 1:
        raise ValueError(f"Поддерживается только одиночная клавиша: {key!r}")
    scan = _user32.MapVirtualKeyW(ord(key.upper()), MAPVK_VK_TO_VSC)
    if not scan:
        raise RuntimeError(f"Windows не нашла scan-code для {key!r}.")
    return int(scan)


def release_key(key: str) -> None:
    _send(INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(0, _scan_code(key), KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, 0, 0)))


def tap_key(key: str, hold_seconds: float = 0.09) -> None:
    scan = _scan_code(key)
    _send(INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(0, scan, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, 0, 0)))
    time.sleep(0.03)
    _send(INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(0, scan, KEYEVENTF_SCANCODE, 0, 0)))
    try:
        time.sleep(max(0.04, hold_seconds))
    finally:
        _send(INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(0, scan, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, 0, 0)))


def click_screen(x: int, y: int) -> None:
    width = max(1, _user32.GetSystemMetrics(0) - 1)
    height = max(1, _user32.GetSystemMetrics(1) - 1)
    absolute_x = round(x * 65535 / width)
    absolute_y = round(y * 65535 / height)
    _send(INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(absolute_x, absolute_y, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, 0)))
    time.sleep(0.08)
    _send(INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, 0)))
    time.sleep(0.06)
    _send(INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, 0)))
