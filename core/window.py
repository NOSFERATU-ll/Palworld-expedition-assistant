from __future__ import annotations

import time

import win32con
import win32gui


class GameWindowError(RuntimeError):
    pass


def find_window(title_fragment: str) -> int:
    matches: list[int] = []

    def callback(hwnd: int, _extra: object) -> None:
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if title_fragment.casefold() in title.casefold():
            matches.append(hwnd)

    win32gui.EnumWindows(callback, None)
    if not matches:
        raise GameWindowError(f"Окно с названием «{title_fragment}» не найдено.")
    return matches[0]


def focus_window(title_fragment: str) -> int:
    hwnd = find_window(title_fragment)
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    else:
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
    win32gui.BringWindowToTop(hwnd)
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass
    time.sleep(0.8)
    return hwnd
