from __future__ import annotations

import time

import win32con
import win32gui


class GameWindowError(RuntimeError):
    pass


def find_window(title_fragment: str) -> int:
    exact_matches: list[int] = []
    partial_matches: list[tuple[int, str]] = []
    wanted = title_fragment.strip().casefold()

    def callback(hwnd: int, _extra: object) -> None:
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd).strip()
        folded = title.casefold()
        if folded == wanted:
            exact_matches.append(hwnd)
        elif wanted in folded:
            partial_matches.append((hwnd, title))

    win32gui.EnumWindows(callback, None)
    if exact_matches:
        return exact_matches[0]
    if partial_matches:
        # У самой игры обычно самое короткое название. Это не даёт выбрать окно Steam
        # с названием вроде «Palworld — Steam» раньше игрового окна.
        partial_matches.sort(key=lambda item: len(item[1]))
        return partial_matches[0][0]
    raise GameWindowError(f"Окно с названием «{title_fragment}» не найдено.")


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
