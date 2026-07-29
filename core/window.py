from __future__ import annotations

import time

import win32con
import win32gui


class GameWindowError(RuntimeError):
    pass


def find_window(title_fragment: str) -> int:
    exact: list[int] = []
    partial: list[tuple[int, str]] = []
    wanted = title_fragment.strip().casefold()

    def callback(hwnd: int, _extra: object) -> None:
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd).strip()
        folded = title.casefold()
        if folded == wanted:
            exact.append(hwnd)
        elif wanted in folded:
            partial.append((hwnd, title))

    win32gui.EnumWindows(callback, None)
    if exact:
        return exact[0]
    if partial:
        partial.sort(key=lambda item: len(item[1]))
        return partial[0][0]
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

    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        if win32gui.GetForegroundWindow() == hwnd:
            time.sleep(0.25)
            return hwnd
        time.sleep(0.05)
    raise GameWindowError("Не удалось передать фокус окну Palworld.")


def get_client_screen_rect(hwnd: int) -> tuple[int, int, int, int]:
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    width = right - left
    height = bottom - top
    if width <= 0 or height <= 0:
        raise GameWindowError("Не удалось определить размер окна Palworld.")
    origin_x, origin_y = win32gui.ClientToScreen(hwnd, (0, 0))
    return origin_x, origin_y, origin_x + width, origin_y + height


def refresh_game_focus(hwnd: int) -> None:
    """Заставляет игру перечитать системное время без ручного Alt+Tab."""
    shell = win32gui.GetShellWindow()
    switched = False
    if shell:
        try:
            win32gui.SetForegroundWindow(shell)
            switched = win32gui.GetForegroundWindow() == shell
        except Exception:
            switched = False
    time.sleep(0.45)

    if not switched:
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        time.sleep(0.45)
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

    win32gui.BringWindowToTop(hwnd)
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass
    time.sleep(1.0)
