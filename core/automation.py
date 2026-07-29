from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

import pyautogui

from core.config import COORDS, EXPECTED_RESOLUTION, PALWORLD_WINDOW_TITLE, Expedition
from core.timezone import get_current_timezone, set_timezone
from core.window import focus_window

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.12

StatusCallback = Callable[[str], None]
LogCallback = Callable[[str], None]
FinishedCallback = Callable[[bool, str], None]


@dataclass(frozen=True)
class AutomationSettings:
    expedition: Expedition
    target_timezone_id: str
    cycles: int = 1
    post_start_delay: float = 3.0


class AutomationStopped(RuntimeError):
    pass


class AutomationController:
    def __init__(
        self,
        on_status: StatusCallback,
        on_log: LogCallback,
        on_finished: FinishedCallback,
    ) -> None:
        self.on_status = on_status
        self.on_log = on_log
        self.on_finished = on_finished
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self, settings: AutomationSettings) -> None:
        if self.running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(settings,),
            daemon=True,
            name="expedition-automation",
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _check_stop(self) -> None:
        if self._stop_event.is_set():
            raise AutomationStopped("Остановлено пользователем.")

    def _sleep(self, seconds: float) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self._check_stop()
            time.sleep(min(0.1, deadline - time.monotonic()))

    def _log(self, text: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.on_log(f"[{stamp}] {text}")

    def _status(self, text: str) -> None:
        self.on_status(text)
        self._log(text)

    def _validate_environment(self) -> None:
        size = pyautogui.size()
        if (size.width, size.height) != EXPECTED_RESOLUTION:
            raise RuntimeError(
                f"Нужен экран {EXPECTED_RESOLUTION[0]}×{EXPECTED_RESOLUTION[1]}, "
                f"сейчас {size.width}×{size.height}."
            )

    def _click(self, point: tuple[int, int], duration: float = 0.18) -> None:
        self._check_stop()
        pyautogui.moveTo(*point, duration=duration)
        pyautogui.click()

    def _run(self, settings: AutomationSettings) -> None:
        original_timezone: str | None = None
        success = False
        final_message = "Готово"
        try:
            self._validate_environment()
            original_timezone = get_current_timezone()
            self._log(f"Исходный часовой пояс: {original_timezone}")
            self._log("F8 — аварийная остановка. Угол экрана — защита PyAutoGUI.")

            for cycle in range(1, settings.cycles + 1):
                self._check_stop()
                self._status(f"Цикл {cycle}/{settings.cycles}: открываю экспедиции")
                focus_window(PALWORLD_WINDOW_TITLE)
                pyautogui.press("f")
                self._sleep(1.7)

                self._status(f"Выбираю: {settings.expedition.name}")
                self._click(settings.expedition.list_click)
                self._sleep(1.8)

                self._status("Нажимаю «Авто»")
                self._click(COORDS.auto_button)
                self._sleep(2.4)

                self._status("Запускаю экспедицию")
                self._click(COORDS.start_button)
                self._sleep(settings.post_start_delay)

                self._status("Переключаю часовой пояс вперёд")
                set_timezone(settings.target_timezone_id)
                self._sleep(2.5)

                self._status("Возвращаю исходный часовой пояс")
                set_timezone(original_timezone)
                self._sleep(4.5)

                self._status("Забираю награду")
                focus_window(PALWORLD_WINDOW_TITLE)
                self._sleep(2.0)
                pyautogui.press("x")
                self._sleep(1.8)
                self._click(COORDS.reward_close_button)
                self._sleep(1.5)

                self._log(f"Цикл {cycle} завершён.")

            success = True
            final_message = f"Готово: выполнено циклов — {settings.cycles}"
        except AutomationStopped as exc:
            final_message = str(exc)
            self._log(final_message)
        except pyautogui.FailSafeException:
            final_message = "Остановлено защитой PyAutoGUI: курсор оказался в углу экрана."
            self._log(final_message)
        except Exception as exc:
            final_message = f"Ошибка: {exc}"
            self._log(final_message)
        finally:
            if original_timezone:
                try:
                    current = get_current_timezone()
                    if current != original_timezone:
                        set_timezone(original_timezone)
                        self._log("Исходный часовой пояс восстановлен.")
                except Exception as exc:
                    self._log(f"ВАЖНО: не удалось восстановить часовой пояс: {exc}")
            self.on_finished(success, final_message)
