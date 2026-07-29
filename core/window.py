from __future__ import annotations

import ctypes
import os
import time

import win32api
import win32con
import win32gui
import win32process


class GameWindowError(RuntimeError):
    pass


def _window_process_id(hwnd: int) -> int:
    _thread_id, process_id = win32process.GetWindowThreadProcessId(hwnd)
    return int(process_id)


def _is_probable_unreal_window(hwnd: int) -> bool:
    try:
        return win32gui.GetClassName(hwnd).casefold() == "unrealwindow"
    except Exception:
        return False


def find_window(title_fragment: str) -> int:
    unreal_matches: list[tuple[int, str]] = []
    exact_matches: list[int] = []
    partial_matches: list[tuple[int, str]] = []
    wanted = title_fragment.strip().casefold()
    own_process_id = os.getpid()

    def callback(hwnd: int, _extra: object) -> None:
        if not win32gui.IsWindowVisible(hwnd):
            return

        # Критически важно: GUI помощника раньше тоже содержала слово
        # "Palworld" и могла быть ошибочно выбрана вместо игры.
        try:
            if _window_process_id(hwnd) == own_process_id:
                return
        except Exception:
            return

        title = win32gui.GetWindowText(hwnd).strip()
        folded = title.casefold()
        if not title or wanted not in folded:
            return

        if _is_probable_unreal_window(hwnd):
            unreal_matches.append((hwnd, title))
        elif folded == wanted:
            exact_matches.append(hwnd)
        else:
            partial_matches.append((hwnd, title))

    win32gui.EnumWindows(callback, None)

    # UnrealWindow почти наверняка является самой игрой, а не браузером,
    # проводником или окном нашего помощника.
    if unreal_matches:
        unreal_matches.sort(key=lambda item: len(item[1]))
        return unreal_matches[0][0]
    if exact_matches:
        return exact_matches[0]
    if partial_matches:
        partial_matches.sort(key=lambda item: len(item[1]))
        return partial_matches[0][0]
    raise GameWindowError(f"Окно с названием «{title_fragment}» не найдено.")


def is_foreground(hwnd: int) -> bool:
    return win32gui.GetForegroundWindow() == hwnd


def focus_hwnd(hwnd: int) -> int:
    if not win32gui.IsWindow(hwnd):
        raise GameWindowError("Окно Palworld больше не существует.")
    if is_foreground(hwnd):
        return hwnd

    foreground = win32gui.GetForegroundWindow()
    current_thread = win32api.GetCurrentThreadId()
    target_thread, _ = win32process.GetWindowThreadProcessId(hwnd)
    foreground_thread = 0
    if foreground:
        foreground_thread, _ = win32process.GetWindowThreadProcessId(foreground)

    attached_target = False
    attached_foreground = False
    try:
        if target_thread and target_thread != current_thread:
            attached_target = bool(
                ctypes.windll.user32.AttachThreadInput(current_thread, target_thread, True)
            )
        if foreground_thread and foreground_thread != current_thread:
            attached_foreground = bool(
                ctypes.windll.user32.AttachThreadInput(current_thread, foreground_thread, True)
            )

        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

        win32gui.BringWindowToTop(hwnd)
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOPMOST,
            0,
            0,
            0,
            0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW,
        )
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_NOTOPMOST,
            0,
            0,
            0,
            0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW,
        )
        try:
            win32gui.SetForegroundWindow(hwnd)
            win32gui.SetActiveWindow(hwnd)
            win32gui.SetFocus(hwnd)
        except Exception:
            pass
    finally:
        if attached_foreground:
            ctypes.windll.user32.AttachThreadInput(current_thread, foreground_thread, False)
        if attached_target:
            ctypes.windll.user32.AttachThreadInput(current_thread, target_thread, False)

    deadline = time.monotonic() + 2.5
    while time.monotonic() < deadline:
        if is_foreground(hwnd):
            time.sleep(0.20)
            return hwnd
        time.sleep(0.05)
    raise GameWindowError("Не удалось передать фокус Palworld.")


def focus_window(title_fragment: str) -> int:
    return focus_hwnd(find_window(title_fragment))


def minimize_window(hwnd: int) -> None:
    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
    time.sleep(0.7)


def restore_and_focus(hwnd: int, title_fragment: str) -> int:
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    time.sleep(0.5)
    try:
        return focus_hwnd(hwnd)
    except GameWindowError:
        return focus_window(title_fragment)


def client_bounds(hwnd: int) -> tuple[int, int, int, int]:
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    width = right - left
    height = bottom - top
    if width <= 0 or height <= 0:
        raise GameWindowError("Не удалось определить размер окна Palworld.")
    origin_x, origin_y = win32gui.ClientToScreen(hwnd, (0, 0))
    return origin_x, origin_y, width, height


def client_point_to_screen(hwnd: int, normalized_point: tuple[float, float]) -> tuple[int, int]:
    origin_x, origin_y, width, height = client_bounds(hwnd)
    x = origin_x + round(normalized_point[0] * width)
    y = origin_y + round(normalized_point[1] * height)
    return x, y
