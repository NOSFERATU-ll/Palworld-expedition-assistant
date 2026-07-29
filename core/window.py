from __future__ import annotations

import time

import win32con
import win32gui

from core.config import EXPECTED_RESOLUTION


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

    deadline = time.monotonic() + 1.5
    while time.monotonic() < deadline:
        if win32gui.GetForegroundWindow() == hwnd:
            time.sleep(0.25)
            return hwnd
        time.sleep(0.05)

    raise GameWindowError("Не удалось передать фокус окну Palworld — ввод отменён.")


def is_game_foreground(title_fragment: str) -> bool:
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return False
    title = win32gui.GetWindowText(hwnd).strip().casefold()
    return title == title_fragment.strip().casefold()


def client_point_to_screen(
    hwnd: int,
    design_point: tuple[int, int],
    design_size: tuple[int, int] = EXPECTED_RESOLUTION,
) -> tuple[int, int]:
    """Переводит координату макета 1920×1080 в координату окна Palworld.

    Координаты больше не привязаны к левому верхнему углу монитора: они
    масштабируются относительно клиентской области найденного окна игры.
    """

    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    width = right - left
    height = bottom - top
    if width <= 0 or height <= 0:
        raise GameWindowError("Не удалось определить размер окна Palworld.")

    origin_x, origin_y = win32gui.ClientToScreen(hwnd, (0, 0))
    design_width, design_height = design_size
    x = origin_x + round(design_point[0] * width / design_width)
    y = origin_y + round(design_point[1] * height / design_height)
    return x, y
