from __future__ import annotations

import ctypes
import threading
import time
from collections.abc import Callable

VK_F6 = 0x75
VK_F8 = 0x77


class GlobalHotkeyPoller:
    """Global F6/F8 detector without low-level keyboard hooks."""

    def __init__(
        self,
        on_f6: Callable[[], None],
        on_f8: Callable[[], None],
        poll_interval: float = 0.025,
    ) -> None:
        self.on_f6 = on_f6
        self.on_f8 = on_f8
        self.poll_interval = poll_interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._down = {VK_F6: False, VK_F8: False}

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="global-hotkey-poller",
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        user32 = ctypes.windll.user32
        while not self._stop.is_set():
            for key, callback in ((VK_F6, self.on_f6), (VK_F8, self.on_f8)):
                pressed = bool(user32.GetAsyncKeyState(key) & 0x8000)
                if pressed and not self._down[key]:
                    try:
                        callback()
                    except Exception:
                        pass
                self._down[key] = pressed
            time.sleep(self.poll_interval)
