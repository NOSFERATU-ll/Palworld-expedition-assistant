from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from core.config import EXPEDITIONS, PALWORLD_WINDOW_TITLE, Expedition
from core.expedition_selector import position_expedition_row
from core.game_input import click_screen, release_key, tap_key
from core.i18n import format_utc_offset, tr
from core.reward_close import wait_for_reward_close
from core.timezone import (
    ResolvedTimezone,
    TimezoneResolutionError,
    get_current_timezone,
    get_local_time_text,
    resolve_timezone_for_jump,
    set_timezone,
)
from core.vision import VisionError, capture_screen, locate, wait_for, wait_until_gone
from core.window import focus_hwnd, focus_window, is_foreground

StatusCallback = Callable[[str], None]
LogCallback = Callable[[str], None]
FinishedCallback = Callable[[bool, str], None]


@dataclass(frozen=True)
class AutomationSettings:
    expedition: Expedition
    timezone_jump_minutes: int
    cycles: int = 1
    post_start_delay: float = 3.0
    language: str = "ru"


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
        self._language = "ru"

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def _t(self, key: str, **kwargs: object) -> str:
        return tr(self._language, key, **kwargs)

    def start(self, settings: AutomationSettings) -> None:
        if self.running:
            return
        self._language = settings.language
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
        for key in ("f", "x"):
            try:
                release_key(key)
            except Exception:
                pass

    def _check_stop(self) -> None:
        if self._stop_event.is_set():
            raise AutomationStopped(self._t("stopped_user"))

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

    def _ensure_game_foreground(self, hwnd: int) -> None:
        self._check_stop()
        if not is_foreground(hwnd):
            focus_hwnd(hwnd)
        if not is_foreground(hwnd):
            raise RuntimeError(self._t("focus_error"))

    def _tap_game_key(self, hwnd: int, key: str) -> None:
        self._ensure_game_foreground(hwnd)
        tap_key(key, hold_seconds=0.075)

    def _click_match(self, hwnd: int, name: str, timeout: float = 8.0) -> None:
        self._ensure_game_foreground(hwnd)
        match = wait_for(name, timeout, stop_check=self._check_stop)
        self._log(
            self._t(
                "recognized",
                name=name,
                score=match.score,
                scale=match.scale,
                center=match.center,
            )
        )
        self._ensure_game_foreground(hwnd)
        click_screen(*match.center)

    def _open_menu(self, hwnd: int) -> None:
        if locate("menu_header") is not None:
            return
        for attempt in range(1, 4):
            self._status(self._t("opening_center", attempt=attempt))
            self._tap_game_key(hwnd, "f")
            try:
                wait_for("menu_header", 3.5, stop_check=self._check_stop)
                return
            except VisionError:
                self._sleep(0.4)
        raise VisionError(self._t("menu_failed"))

    def _start_expedition(self, hwnd: int, expedition: Expedition) -> None:
        expedition_name = expedition.name_for(self._language)
        if not expedition.enabled:
            raise VisionError(self._t("expedition_locked", name=expedition_name))

        self._status(self._t("finding_expedition", name=expedition_name))
        self._ensure_game_foreground(hwnd)
        row = position_expedition_row(
            expedition.list_index,
            len(EXPEDITIONS),
            stop_check=self._check_stop,
        )
        self._log(
            self._t(
                "row_found",
                index=expedition.list_index + 1,
                total=len(EXPEDITIONS),
                center=row.center,
            )
        )
        self._ensure_game_foreground(hwnd)
        click_screen(*row.center)

        self._status(self._t("wait_pal_screen"))
        wait_for("auto_button", 8.0, stop_check=self._check_stop)

        self._status(self._t("click_auto"))
        self._click_match(hwnd, "auto_button", timeout=4.0)

        self._status(self._t("wait_start"))
        wait_for("start_button", 8.0, stop_check=self._check_stop)
        self._status(self._t("click_start"))
        self._click_match(hwnd, "start_button", timeout=4.0)
        wait_until_gone("start_button", 6.0, stop_check=self._check_stop)

    def _jump_time(self, target: ResolvedTimezone, original_timezone: str) -> None:
        self._status(self._t("shift_forward"))
        before = get_local_time_text()
        set_timezone(target.timezone_id)
        after = get_local_time_text()
        self._log(
            self._t(
                "windows_time_change",
                before=before,
                after=after,
                zone=get_current_timezone(),
            )
        )
        self._sleep(2.5)

        self._status(self._t("restore_zone"))
        before_restore = get_local_time_text()
        set_timezone(original_timezone)
        after_restore = get_local_time_text()
        self._log(
            self._t(
                "windows_restore",
                before=before_restore,
                after=after_restore,
                zone=get_current_timezone(),
            )
        )
        self._sleep(0.7)

    def _collect_reward(self, hwnd: int) -> None:
        self._status(self._t("wait_completion"))
        try:
            wait_for("completed", 4.0, stop_check=self._check_stop)
            self._log(self._t("completion_found"))
        except VisionError:
            self._log(self._t("completion_fallback"))

        self._tap_game_key(hwnd, "f")
        wait_for("reward_header", 6.0, stop_check=self._check_stop)

        self._status(self._t("collect_reward"))
        self._tap_game_key(hwnd, "x")
        self._sleep(0.35)

        self._status(self._t("close_reward"))
        close_button = wait_for_reward_close(3.0, stop_check=self._check_stop)
        self._log(
            self._t(
                "red_close_found",
                center=close_button.center,
                width=close_button.width,
                height=close_button.height,
            )
        )
        self._ensure_game_foreground(hwnd)
        click_screen(*close_button.center)
        wait_until_gone("reward_header", 2.5, stop_check=self._check_stop)
        self._log(self._t("reward_closed"))
        self._sleep(0.25)

    def _run(self, settings: AutomationSettings) -> None:
        original_timezone: str | None = None
        success = False
        final_message = self._t("final_done", cycles=0)
        try:
            frame, _origin = capture_screen()
            self._log(
                self._t(
                    "screenshot_size",
                    width=frame.shape[1],
                    height=frame.shape[0],
                )
            )
            original_timezone = get_current_timezone()
            self._log(
                self._t(
                    "original_zone",
                    zone=original_timezone,
                    time=get_local_time_text(),
                )
            )
            target = resolve_timezone_for_jump(settings.timezone_jump_minutes)
            self._log(
                self._t(
                    "timezone_resolved",
                    zone=target.timezone_id,
                    current=format_utc_offset(target.current_offset_minutes),
                    target=format_utc_offset(target.target_offset_minutes),
                )
            )
            self._log(self._t("selector_mode"))

            for cycle in range(1, settings.cycles + 1):
                self._check_stop()
                self._status(self._t("cycle_status", cycle=cycle, total=settings.cycles))
                hwnd = focus_window(PALWORLD_WINDOW_TITLE)
                self._open_menu(hwnd)
                self._start_expedition(hwnd, settings.expedition)
                self._sleep(settings.post_start_delay)
                self._jump_time(target, original_timezone)
                self._collect_reward(hwnd)
                self._log(self._t("cycle_done", cycle=cycle))

            success = True
            final_message = self._t("final_done", cycles=settings.cycles)
        except TimezoneResolutionError as exc:
            final_message = self._t(
                "timezone_unavailable",
                current=format_utc_offset(exc.current_offset_minutes),
                target=format_utc_offset(exc.target_offset_minutes),
            )
            self._log(final_message)
        except AutomationStopped as exc:
            final_message = str(exc)
            self._log(final_message)
        except Exception as exc:
            final_message = self._t("error_prefix", error=exc)
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
                        self._log(self._t("emergency_zone_restored"))
                except Exception as exc:
                    self._log(self._t("emergency_zone_failed", error=exc))
            self.on_finished(success, final_message)
