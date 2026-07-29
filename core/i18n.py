from __future__ import annotations

import inspect
from typing import Any

SUPPORTED_LANGUAGES = ("ru", "en")

_TRANSLATIONS: dict[str, dict[str, str]] = {
    "ru": {
        "app_kicker": "PALWORLD  •  ЭКСПЕДИЦИИ",
        "app_heading": "Expedition Assistant",
        "select_expedition": "Выбери экспедицию",
        "select_help": "Настрой один раз. Потом запускай из игры клавишей F6.",
        "parameters": "Параметры",
        "timezone_jump": "Сдвиг часового пояса",
        "cycles": "Повторений",
        "post_start_delay": "Пауза после старта",
        "hotkey_start": "F6  Запустить",
        "hotkey_stop": "F8  Остановить",
        "test_timezone": "Проверить автоматический сдвиг времени",
        "ready": "Готова • F6 работает даже когда окно программы свёрнуто",
        "log": "Журнал",
        "log_intro": "Оставь программу запущенной, вернись в Palworld и нажми F6 перед Центром экспедиций.",
        "log_language_reset": "Язык изменён. Старый журнал очищен; новые записи будут на русском.",
        "start_now": "▶  Запустить сейчас",
        "stop_button": "■  Остановить (F8)",
        "checking_system": "Проверяю систему…",
        "scale": "масштаб",
        "invalid_settings": "Проверь повторения и паузу",
        "global_f6": "Получен глобальный F6.",
        "timezone_test_ok": "Автоматический сдвиг времени работает",
        "timezone_test_failed": "Сдвиг времени не сработал",
        "timezone_test_log": "Тест времени: {before} → {after} → {restored}; выбран пояс {zone}; исходная зона восстановлена.",
        "timezone_unavailable": "Windows не нашла пояс для сдвига с UTC{current} до UTC{target}.",
        "stopping": "Останавливаю после безопасного шага…",
        "emergency_stop": "Аварийная остановка F8",
        "stopped_user": "Остановлено пользователем.",
        "focus_error": "Pal не получил фокус; ввод отменён, чтобы не нажимать в другое окно.",
        "recognized": "Распознано {name}: {score:.3f}, масштаб {scale:.2f}, центр {center}.",
        "opening_center": "Открываю Центр экспедиций — попытка {attempt}/3",
        "menu_failed": "Меню экспедиций не открылось после трёх нажатий F.",
        "expedition_locked": "Экспедиция «{name}» пока заблокирована.",
        "finding_expedition": "Ищу «{name}»",
        "row_found": "Строка {index}/{total} найдена: центр {center}.",
        "wait_pal_screen": "Жду экран набора Палов",
        "click_auto": "Нажимаю «Авто»",
        "wait_start": "Жду активную кнопку «Начать»",
        "click_start": "Нажимаю «Начать»",
        "shift_forward": "Переключаю часовой пояс вперёд",
        "timezone_resolved": "Автоматически выбран пояс {zone}: UTC{current} → UTC{target}.",
        "windows_time_change": "Время Windows: {before} → {after}; пояс: {zone}",
        "restore_zone": "Возвращаю исходный часовой пояс",
        "windows_restore": "Возврат Windows: {before} → {after}; пояс: {zone}",
        "wait_completion": "Жду завершения экспедиции",
        "completion_found": "Метка «Завершено» найдена — сразу открываю награду.",
        "completion_fallback": "Метка «Завершено» не найдена за 4 секунды; пробую открыть награду клавишей F.",
        "collect_reward": "Забираю награду",
        "close_reward": "Закрываю окно награды крестиком",
        "red_close_found": "Красный крестик найден: центр {center}, размер {width}×{height}.",
        "reward_closed": "Окно награды закрыто кликом по крестику; Esc не используется.",
        "screenshot_size": "Размер снимка экрана для распознавания: {width}×{height}.",
        "original_zone": "Исходный пояс: {zone}; время: {time}",
        "selector_mode": "Список экспедиций выбирается распознаванием строк и проверенной прокруткой колесом.",
        "cycle_status": "Цикл {cycle}/{total}",
        "cycle_done": "Цикл {cycle} завершён.",
        "final_done": "Готово: выполнено циклов — {cycles}",
        "error_prefix": "Ошибка: {error}",
        "emergency_zone_restored": "Исходный часовой пояс восстановлен аварийно.",
        "emergency_zone_failed": "ВАЖНО: не удалось восстановить часовой пояс: {error}",
    },
    "en": {
        "app_kicker": "PALWORLD  •  EXPEDITIONS",
        "app_heading": "Expedition Assistant",
        "select_expedition": "Choose an expedition",
        "select_help": "Configure it once, then press F6 from inside the game.",
        "parameters": "Settings",
        "timezone_jump": "Time-zone jump",
        "cycles": "Repeats",
        "post_start_delay": "Delay after start",
        "hotkey_start": "F6  Start",
        "hotkey_stop": "F8  Stop",
        "test_timezone": "Test automatic time jump",
        "ready": "Ready • F6 works while this window is minimized",
        "log": "Log",
        "log_intro": "Keep the app running, return to Palworld, stand by the Expedition Station, and press F6.",
        "log_language_reset": "Language changed. Previous log cleared; new entries will be in English.",
        "start_now": "▶  Start now",
        "stop_button": "■  Stop (F8)",
        "checking_system": "Checking system…",
        "scale": "scale",
        "invalid_settings": "Check the repeat count and delay",
        "global_f6": "Global F6 received.",
        "timezone_test_ok": "Automatic time jump works",
        "timezone_test_failed": "Time jump failed",
        "timezone_test_log": "Time test: {before} → {after} → {restored}; selected zone {zone}; original zone restored.",
        "timezone_unavailable": "Windows could not find a time zone for a jump from UTC{current} to UTC{target}.",
        "stopping": "Stopping after the current safe step…",
        "emergency_stop": "Emergency stop F8",
        "stopped_user": "Stopped by user.",
        "focus_error": "Pal did not receive focus; input was cancelled to protect other windows.",
        "recognized": "Detected {name}: {score:.3f}, scale {scale:.2f}, center {center}.",
        "opening_center": "Opening the Expedition Station — attempt {attempt}/3",
        "menu_failed": "The expedition menu did not open after three F presses.",
        "expedition_locked": "Expedition “{name}” is still locked.",
        "finding_expedition": "Finding “{name}”",
        "row_found": "Row {index}/{total} found: center {center}.",
        "wait_pal_screen": "Waiting for the Pal assignment screen",
        "click_auto": "Clicking Auto",
        "wait_start": "Waiting for the active Start button",
        "click_start": "Clicking Start",
        "shift_forward": "Moving the time zone forward",
        "timezone_resolved": "Automatically selected {zone}: UTC{current} → UTC{target}.",
        "windows_time_change": "Windows time: {before} → {after}; zone: {zone}",
        "restore_zone": "Restoring the original time zone",
        "windows_restore": "Windows restored: {before} → {after}; zone: {zone}",
        "wait_completion": "Waiting for expedition completion",
        "completion_found": "Completed marker found — opening the reward immediately.",
        "completion_fallback": "Completed marker was not found within 4 seconds; trying F to open the reward.",
        "collect_reward": "Collecting the reward",
        "close_reward": "Closing the reward window with its X button",
        "red_close_found": "Red close button found: center {center}, size {width}×{height}.",
        "reward_closed": "Reward window closed with its X button; Escape is not used.",
        "screenshot_size": "Recognition screenshot size: {width}×{height}.",
        "original_zone": "Original zone: {zone}; time: {time}",
        "selector_mode": "Expeditions are selected through row recognition and verified mouse-wheel scrolling.",
        "cycle_status": "Cycle {cycle}/{total}",
        "cycle_done": "Cycle {cycle} completed.",
        "final_done": "Done: {cycles} cycle(s) completed",
        "error_prefix": "Error: {error}",
        "emergency_zone_restored": "Original time zone restored after interruption.",
        "emergency_zone_failed": "IMPORTANT: failed to restore the original time zone: {error}",
    },
}


def _sync_interface_log_language(language: str) -> None:
    """Clear stale log text when the GUI switches between Russian and English.

    The GUI rebuilds itself on language changes while preserving `_log_history`.
    Translation calls made by the automation controller have no `_log_history`, so
    this only affects the desktop interface and cannot interrupt an active cycle.
    """
    frame = inspect.currentframe()
    caller = frame.f_back.f_back if frame and frame.f_back else None
    owner = caller.f_locals.get("self") if caller else None
    history = getattr(owner, "_log_history", None)
    if not isinstance(history, list):
        return

    selected = language if language in SUPPORTED_LANGUAGES else "en"
    previous = getattr(owner, "_log_render_language", None)
    if previous is None:
        setattr(owner, "_log_render_language", selected)
        return
    if previous == selected:
        return

    history.clear()
    history.append(_TRANSLATIONS[selected]["log_language_reset"])
    setattr(owner, "_log_render_language", selected)


def tr(language: str, key: str, **kwargs: Any) -> str:
    _sync_interface_log_language(language)
    selected = language if language in SUPPORTED_LANGUAGES else "en"
    template = _TRANSLATIONS[selected].get(key) or _TRANSLATIONS["en"].get(key) or key
    return template.format(**kwargs)


def timezone_jump_label(language: str, minutes: int) -> str:
    hours = minutes // 60
    if language == "ru":
        noun = "час" if hours == 1 else "часа" if 2 <= hours <= 4 else "часов"
        return f"Авто: +{hours} {noun} от текущего пояса"
    noun = "hour" if hours == 1 else "hours"
    return f"Auto: +{hours} {noun} from current zone"


def format_utc_offset(minutes: int) -> str:
    sign = "+" if minutes >= 0 else "−"
    absolute = abs(minutes)
    hours, remainder = divmod(absolute, 60)
    return f"{sign}{hours:02d}:{remainder:02d}"
