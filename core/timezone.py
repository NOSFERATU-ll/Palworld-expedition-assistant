from __future__ import annotations

import ctypes
import subprocess
from datetime import datetime

HWND_BROADCAST = 0xFFFF
WM_TIMECHANGE = 0x001E
SMTO_ABORTIFHUNG = 0x0002


class TimezoneError(RuntimeError):
    pass


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


def local_clock_text() -> str:
    current = datetime.now().astimezone()
    return current.strftime("%H:%M:%S  UTC%z")


def set_timezone(timezone_id: str) -> None:
    _run_tzutil("/s", timezone_id)
    actual = get_current_timezone()
    if actual.casefold() != timezone_id.casefold():
        raise TimezoneError(f"Windows оставила пояс {actual!r} вместо {timezone_id!r}.")
    _broadcast_time_change()
