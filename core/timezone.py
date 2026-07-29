from __future__ import annotations

import ctypes
import subprocess


class TimezoneError(RuntimeError):
    pass


HWND_BROADCAST = 0xFFFF
WM_TIMECHANGE = 0x001E
SMTO_ABORTIFHUNG = 0x0002


def _run_tzutil(*args: str) -> str:
    completed = subprocess.run(
        ["tzutil", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip() or "неизвестная ошибка"
        raise TimezoneError(f"tzutil завершился с ошибкой: {details}")
    return completed.stdout.strip()


def _broadcast_time_change() -> None:
    """Сообщает запущенным приложениям, что системное время/зона изменились."""

    result = ctypes.c_size_t()
    ctypes.windll.user32.SendMessageTimeoutW(
        HWND_BROADCAST,
        WM_TIMECHANGE,
        0,
        0,
        SMTO_ABORTIFHUNG,
        1500,
        ctypes.byref(result),
    )


def get_current_timezone() -> str:
    timezone_id = _run_tzutil("/g")
    if not timezone_id:
        raise TimezoneError("Windows не вернула текущий часовой пояс.")
    return timezone_id


def set_timezone(timezone_id: str) -> None:
    _run_tzutil("/s", timezone_id)
    _broadcast_time_change()
