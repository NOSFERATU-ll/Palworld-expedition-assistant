from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from core.config import EXPECTED_RESOLUTION, PALWORLD_WINDOW_TITLE, Expedition
from core.game_input import click_screen, release_key, tap_key
from core.timezone import get_current_timezone, local_clock_text, set_timezone
from core.vision import VisionError, locate, wait_for, wait_until_gone
from core.window import focus_window, get_client_screen_rect, refresh_game_focus

StatusCallback = Callable[[str], None]
LogCallback = Callable[[str], None]
FinishedCallback = Callable[[bool, str], None]


@dataclass(frozen=True)
class AutomationSettings:
    expedition: Expedition
    target_timezone_id: str
    cycles: int = 1


class AutomationStopped(RuntimeError):
    pass


class AutomationController:
    def __init__(self, on_status: StatusCallback, on_log: LogCallback, on_finished: FinishedCallback) -> None:
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
        self._thread = threading.Thread(target=self._run, args=(settings,), daemon=True, name="expedition-automation")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        for key in ("f", "x"):
            try:
                release_key(key)
            except Exception:
                pass

    def _check_stop(self) -> None:
        if self._stop_event.is_set():
            raise AutomationStopped("Остановлено пользователем.")

    def _sleep(self, seconds: float) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self._check_stop()
            time.sleep(min(0.1, deadline - time.monotonic()))

    def _log(self, text: str) -> None:
        self.on_log(f"[{datetime.now():%H:%M:%S}] {text}")

    def _status(self, text: str) -> None:
        self.on_status(text)
        self._log(text)

    def _validate_game_size(self, hwnd: int) -> None:
        left, top, right, bottom = get_client_screen_rect(hwnd)
        size = (right - left, bottom - top)
        if size != EXPECTED_RESOLUTION:
            raise RuntimeError(
                f"Клиент Palworld должен быть {EXPECTED_RESOLUTION[0]}×{EXPECTED_RESOLUTION[1]}, сейчас {size[0]}×{size[1]}."
            )

    def _click_match(self, match_name: str, hwnd: int, timeout: float = 8.0) -> None:
        match = wait_for(hwnd, match_name, timeout)
        self._log(f"Нашла {match_name}: совпадение {match.score:.3f}, точка {match.center}.")
        click_screen(*match.center)

    def _open_menu(self, hwnd: int) -> None:
        if locate(hwnd, "menu_header") is not None:
            return
        for attempt in range(1, 4):
            self._status(f"Открываю Центр экспедиций — попытка {attempt}/3")
            focus_window(PALWORLD_WINDOW_TITLE)
            tap_key("f")
            try:
                wait_for(hwnd, "menu_header", 3.0)
                return
            except VisionError:
                self._sleep(0.4)
        raise VisionError("Центр экспедиций не открылся после трёх нажатий F.")

    def _jump_time(self, hwnd: int, target_timezone: str, original_timezone: str) -> None:
        self._status(f"Ставлю часовой пояс {target_timezone}")
        before = local_clock_text()
        set_timezone(target_timezone)
        after = local_clock_text()
        self._log(f"Проверка Windows: {before} → {after}; активный пояс: {get_current_timezone()}")
        refresh_game_focus(hwnd)
        self._sleep(2.0)

        self._status(f"Возвращаю часовой пояс {original_timezone}")
        before_restore = local_clock_text()
        set_timezone(original_timezone)
        after_restore = local_clock_text()
        self._log(
            f"Проверка возврата: {before_restore} → {after_restore}; активный пояс: {get_current_timezone()}"
        )
        refresh_game_focus(hwnd)
        self._sleep(2.0)

    def _collect_reward(self, hwnd: int) -> None:
        self._status("Жду статус «Завершено»")
        try:
            wait_for(hwnd, "completed", 12.0)
        except VisionError:
            self._log("Статус не появился сразу — делаю ещё один цикл фокуса игры.")
            refresh_game_focus(hwnd)
            wait_for(hwnd, "completed", 10.0)

        self._status("Открываю награду")
        tap_key("f")
        wait_for(hwnd, "reward_header", 5.0)
        wait_for(hwnd, "take_all", 3.0)
        self._status("Забираю всё")
        tap_key("x")
        self._sleep(1.2)
        tap_key("f")
        self._sleep(1.0)

    def _run(self, settings: AutomationSettings) -> None:
        original_timezone: str | None = None
        success = False
        final_message = "Готово"
        try:
            hwnd = focus_window(PALWORLD_WINDOW_TITLE)
            self._validate_game_size(hwnd)
            original_timezone = get_current_timezone()
            self._log(f"Исходный пояс: {original_timezone}; локальное время: {local_clock_text()}")
            self._log("Наведение теперь выполняется распознаванием интерфейса, а не координатами.")

            for cycle in range(1, settings.cycles + 1):
                self._check_stop()
                self._status(f"Цикл {cycle}/{settings.cycles}")
                hwnd = focus_window(PALWORLD_WINDOW_TITLE)
                self._open_menu(hwnd)

                self._status(f"Выбираю «{settings.expedition.name}»")
                self._click_match(settings.expedition.template_name, hwnd)
                self._sleep(1.0)

                self._status("Нажимаю «Авто»")
                self._click_match("auto_button", hwnd)
                self._sleep(1.4)

                self._status("Нажимаю «Начать»")
                self._click_match("start_button", hwnd)
                wait_until_gone(hwnd, "menu_header", 5.0)
                self._sleep(1.0)

                self._jump_time(hwnd, settings.target_timezone_id, original_timezone)
                self._collect_reward(hwnd)
                self._log(f"Цикл {cycle} завершён.")

            success = True
            final_message = f"Готово: выполнено циклов — {settings.cycles}"
        except AutomationStopped as exc:
            final_message = str(exc)
            self._log(final_message)
        except Exception as exc:
            final_message = f"Ошибка: {exc}"
            self._log(final_message)
        finally:
            for key in ("f", "x"):
                try:
                    release_key(key)
                except Exception:
                    pass
            if original_timezone:
                try:
                    if get_current_timezone().casefold() != original_timezone.casefold():
                        set_timezone(original_timezone)
                        self._log("Исходный часовой пояс восстановлен аварийно.")
                except Exception as exc:
                    self._log(f"ВАЖНО: не удалось восстановить часовой пояс: {exc}")
            self.on_finished(success, final_message)
