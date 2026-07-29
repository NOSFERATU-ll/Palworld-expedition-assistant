from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes
from typing import Callable

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_NOREPEAT = 0x4000
VK_F6 = 0x75
VK_F8 = 0x77

HotkeyCallback = Callable[[str], None]
ErrorCallback = Callable[[str], None]


class GlobalHotkeys:
    def __init__(self, callback: HotkeyCallback, on_error: ErrorCallback) -> None:
        self.callback = callback
        self.on_error = on_error
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._ready = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._ready.clear()
        self._thread = threading.Thread(target=self._run, name="global-hotkeys", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=2.0)

    def stop(self) -> None:
        if self._thread_id:
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _run(self) -> None:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self._thread_id = int(kernel32.GetCurrentThreadId())
        registered: list[int] = []
        try:
            if not user32.RegisterHotKey(None, 1, MOD_NOREPEAT, VK_F6):
                raise ctypes.WinError(ctypes.get_last_error())
            registered.append(1)
            if not user32.RegisterHotKey(None, 2, MOD_NOREPEAT, VK_F8):
                raise ctypes.WinError(ctypes.get_last_error())
            registered.append(2)
            self._ready.set()

            message = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                if message.message == WM_HOTKEY:
                    if message.wParam == 1:
                        self.callback("start")
                    elif message.wParam == 2:
                        self.callback("stop")
        except Exception as exc:
            self._ready.set()
            self.on_error(f"Не удалось зарегистрировать F6/F8: {exc}")
        finally:
            for hotkey_id in registered:
                user32.UnregisterHotKey(None, hotkey_id)
            self._thread_id = None
