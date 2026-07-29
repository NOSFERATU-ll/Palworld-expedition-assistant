from __future__ import annotations

import ctypes
import os
import queue
import sys
from pathlib import Path

import customtkinter as ctk

from core.automation import AutomationController, AutomationSettings
from core.config import (
    APP_NAME,
    DEFAULT_TIMEZONE_JUMP_MINUTES,
    EXPEDITIONS,
    TIMEZONE_JUMP_MINUTES,
)
from core.hotkeys import GlobalHotkeyPoller
from core.i18n import format_utc_offset, timezone_jump_label, tr
from core.timezone import (
    TimezoneResolutionError,
    get_current_timezone,
    get_local_time_text,
    resolve_timezone_for_jump,
    set_timezone_verified,
)


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _relaunch_as_admin() -> None:
    if getattr(sys, "frozen", False):
        executable = sys.executable
        params = " ".join(f'"{arg}"' for arg in sys.argv[1:])
    else:
        executable = sys.executable
        script = str(Path(__file__).resolve())
        params = " ".join([f'"{script}"', *[f'"{arg}"' for arg in sys.argv[1:]]])

    result = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", executable, params, os.getcwd(), 1
    )
    if result <= 32:
        raise RuntimeError("Windows declined the administrator request.")
    raise SystemExit(0)


class ExpeditionAssistantApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1080x710")
        self.minsize(960, 640)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.language = "ru"
        self.timezone_jump_minutes = DEFAULT_TIMEZONE_JUMP_MINUTES
        self._log_history: list[str] = []
        self._events: queue.SimpleQueue[str] = queue.SimpleQueue()

        self.controller = AutomationController(
            on_status=self._threadsafe_status,
            on_log=self._threadsafe_log,
            on_finished=self._threadsafe_finished,
        )
        self.hotkeys = GlobalHotkeyPoller(
            on_f6=lambda: self._events.put("start"),
            on_f8=lambda: self._events.put("stop"),
        )

        self._build_ui()
        self.hotkeys.start()
        self.after(40, self._poll_events)
        self.after(300, self._refresh_environment)

    def _t(self, key: str, **kwargs: object) -> str:
        return tr(self.language, key, **kwargs)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, corner_radius=0, fg_color="#0d1c24")
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text=self._t("app_kicker"),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#63d8ee",
        ).grid(row=0, column=0, padx=28, pady=(18, 2), sticky="w")
        ctk.CTkLabel(
            header,
            text=self._t("app_heading"),
            font=ctk.CTkFont(size=30, weight="bold"),
        ).grid(row=1, column=0, padx=28, pady=(0, 18), sticky="w")

        self.env_label = ctk.CTkLabel(
            header,
            text=self._t("checking_system"),
            font=ctk.CTkFont(size=12),
            text_color="#a9bdc6",
        )
        self.env_label.grid(row=0, column=1, padx=(10, 12), pady=(12, 0), sticky="e")

        self.language_button = ctk.CTkButton(
            header,
            text="EN" if self.language == "ru" else "RU",
            width=56,
            height=30,
            fg_color="#294b5a",
            hover_color="#356374",
            command=self._toggle_language,
        )
        self.language_button.grid(row=1, column=1, padx=(10, 28), pady=(0, 14), sticky="e")

        left = ctk.CTkFrame(self, corner_radius=18, fg_color="#10252e")
        left.grid(row=1, column=0, padx=(22, 10), pady=20, sticky="nsew")
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            left,
            text=self._t("select_expedition"),
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, padx=22, pady=(22, 5), sticky="w")
        ctk.CTkLabel(
            left,
            text=self._t("select_help"),
            text_color="#91a9b3",
        ).grid(row=1, column=0, padx=22, pady=(0, 14), sticky="w")

        expedition_box = ctk.CTkScrollableFrame(left, fg_color="transparent")
        expedition_box.grid(row=2, column=0, padx=14, pady=(0, 12), sticky="nsew")
        expedition_box.grid_columnconfigure(0, weight=1)

        self.expedition_var = ctk.StringVar(value=EXPEDITIONS[0].key)
        for index, expedition in enumerate(EXPEDITIONS):
            card = ctk.CTkRadioButton(
                expedition_box,
                variable=self.expedition_var,
                value=expedition.key,
                text=(
                    f"{expedition.name_for(self.language)}\n"
                    f"{expedition.duration}  •  {expedition.danger_for(self.language)}"
                ),
                font=ctk.CTkFont(size=15, weight="bold"),
                text_color="#e6f2f5",
                fg_color="#14b8d4",
                hover_color="#0b91ab",
                state="normal",
                height=64,
            )
            card.grid(row=index, column=0, padx=8, pady=7, sticky="ew")

        right = ctk.CTkFrame(self, corner_radius=18, fg_color="#10252e")
        right.grid(row=1, column=1, padx=(10, 22), pady=20, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(8, weight=1)

        ctk.CTkLabel(
            right,
            text=self._t("parameters"),
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, padx=22, pady=(22, 15), sticky="w")

        ctk.CTkLabel(
            right,
            text=self._t("timezone_jump"),
            text_color="#9fb2ba",
        ).grid(row=1, column=0, padx=22, sticky="w")

        self._timezone_label_to_minutes = {
            timezone_jump_label(self.language, minutes): minutes
            for minutes in TIMEZONE_JUMP_MINUTES
        }
        current_timezone_label = timezone_jump_label(
            self.language, self.timezone_jump_minutes
        )
        self.timezone_var = ctk.StringVar(value=current_timezone_label)
        self.timezone_menu = ctk.CTkOptionMenu(
            right,
            variable=self.timezone_var,
            values=list(self._timezone_label_to_minutes),
            height=38,
            command=self._on_timezone_selected,
        )
        self.timezone_menu.grid(row=2, column=0, padx=22, pady=(6, 14), sticky="ew")

        controls = ctk.CTkFrame(right, fg_color="transparent")
        controls.grid(row=3, column=0, padx=22, sticky="ew")
        controls.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            controls,
            text=self._t("cycles"),
            text_color="#9fb2ba",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            controls,
            text=self._t("post_start_delay"),
            text_color="#9fb2ba",
        ).grid(row=0, column=1, padx=(12, 0), sticky="w")

        self.cycles_var = ctk.StringVar(value="1")
        ctk.CTkEntry(controls, textvariable=self.cycles_var, height=38).grid(
            row=1, column=0, pady=(6, 14), sticky="ew"
        )
        self.delay_var = ctk.StringVar(value="3")
        ctk.CTkEntry(controls, textvariable=self.delay_var, height=38).grid(
            row=1, column=1, padx=(12, 0), pady=(6, 14), sticky="ew"
        )

        hotkeys = ctk.CTkFrame(right, corner_radius=10, fg_color="#0b1b22")
        hotkeys.grid(row=4, column=0, padx=22, pady=(2, 10), sticky="ew")
        hotkeys.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(
            hotkeys,
            text=self._t("hotkey_start"),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#63d8ee",
        ).grid(row=0, column=0, padx=12, pady=10, sticky="w")
        ctk.CTkLabel(
            hotkeys,
            text=self._t("hotkey_stop"),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ff8a98",
        ).grid(row=0, column=1, padx=12, pady=10, sticky="e")

        self.time_test_button = ctk.CTkButton(
            right,
            text=self._t("test_timezone"),
            height=36,
            fg_color="#294b5a",
            hover_color="#356374",
            command=self._test_timezone,
        )
        self.time_test_button.grid(row=5, column=0, padx=22, pady=(0, 10), sticky="ew")

        self.status_label = ctk.CTkLabel(
            right,
            text=self._t("ready"),
            anchor="w",
            corner_radius=10,
            fg_color="#0b1b22",
            text_color="#6fe1b6",
            height=44,
        )
        self.status_label.grid(row=6, column=0, padx=22, pady=(2, 12), sticky="ew")

        ctk.CTkLabel(
            right,
            text=self._t("log"),
            text_color="#9fb2ba",
        ).grid(row=7, column=0, padx=22, sticky="w")

        self.log_box = ctk.CTkTextbox(
            right,
            corner_radius=10,
            fg_color="#09171d",
            text_color="#b9ced6",
            font=ctk.CTkFont(family="Consolas", size=12),
        )
        self.log_box.grid(row=8, column=0, padx=22, pady=(6, 12), sticky="nsew")
        self.log_box.insert("end", self._t("log_intro") + "\n")
        for line in self._log_history:
            self.log_box.insert("end", line + "\n")
        self.log_box.configure(state="disabled")

        buttons = ctk.CTkFrame(right, fg_color="transparent")
        buttons.grid(row=9, column=0, padx=22, pady=(0, 22), sticky="ew")
        buttons.grid_columnconfigure((0, 1), weight=1)

        self.start_button = ctk.CTkButton(
            buttons,
            text=self._t("start_now"),
            height=46,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._start,
        )
        self.start_button.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self.stop_button = ctk.CTkButton(
            buttons,
            text=self._t("stop_button"),
            height=46,
            fg_color="#8d3441",
            hover_color="#a74150",
            state="disabled",
            command=self._stop,
        )
        self.stop_button.grid(row=0, column=1, padx=(6, 0), sticky="ew")

    def _toggle_language(self) -> None:
        if self.controller.running:
            return
        selected_expedition = self.expedition_var.get()
        cycles = self.cycles_var.get()
        delay = self.delay_var.get()
        self.language = "en" if self.language == "ru" else "ru"

        for child in self.winfo_children():
            child.destroy()
        self._build_ui()
        self.expedition_var.set(selected_expedition)
        self.cycles_var.set(cycles)
        self.delay_var.set(delay)
        self._refresh_environment()

    def _on_timezone_selected(self, label: str) -> None:
        self.timezone_jump_minutes = self._timezone_label_to_minutes[label]

    def _refresh_environment(self) -> None:
        width = self.winfo_screenwidth()
        height = self.winfo_screenheight()
        try:
            dpi = ctypes.windll.user32.GetDpiForSystem()
        except Exception:
            dpi = 96
        scale = round(dpi / 96 * 100)
        ok = width == 1920 and height == 1080 and scale == 100
        self.env_label.configure(
            text=f"{'✓' if ok else '⚠'}  {width}×{height}  •  {self._t('scale')} {scale}%",
            text_color="#6fe1b6" if ok else "#ffbd69",
        )

    def _poll_events(self) -> None:
        while True:
            try:
                event = self._events.get_nowait()
            except queue.Empty:
                break
            if event == "start":
                self._start(from_hotkey=True)
            elif event == "stop":
                self._emergency_stop()
        self.after(40, self._poll_events)

    def _build_settings(self) -> AutomationSettings | None:
        try:
            cycles = int(self.cycles_var.get())
            delay = float(self.delay_var.get().replace(",", "."))
            if not 1 <= cycles <= 999 or not 1 <= delay <= 30:
                raise ValueError
        except ValueError:
            self._set_status(self._t("invalid_settings"), error=True)
            return None

        expedition = next(
            item for item in EXPEDITIONS if item.key == self.expedition_var.get()
        )
        return AutomationSettings(
            expedition=expedition,
            timezone_jump_minutes=self.timezone_jump_minutes,
            cycles=cycles,
            post_start_delay=delay,
            language=self.language,
        )

    def _start(self, from_hotkey: bool = False) -> None:
        if self.controller.running:
            return
        settings = self._build_settings()
        if settings is None:
            return

        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.time_test_button.configure(state="disabled")
        self.language_button.configure(state="disabled")
        self._append_log("—" * 46)
        if from_hotkey:
            self._append_log(self._t("global_f6"))
        self.iconify()
        self.controller.start(settings)

    def _test_timezone(self) -> None:
        if self.controller.running:
            return
        original = get_current_timezone()
        try:
            resolved = resolve_timezone_for_jump(self.timezone_jump_minutes)
            before = get_local_time_text()
            set_timezone_verified(resolved.timezone_id)
            after = get_local_time_text()
            set_timezone_verified(original)
            restored = get_local_time_text()
            self._append_log(
                self._t(
                    "timezone_test_log",
                    before=before,
                    after=after,
                    restored=restored,
                    zone=resolved.timezone_id,
                )
            )
            self._set_status(self._t("timezone_test_ok"))
        except TimezoneResolutionError as exc:
            self._append_log(
                self._t(
                    "timezone_unavailable",
                    current=format_utc_offset(exc.current_offset_minutes),
                    target=format_utc_offset(exc.target_offset_minutes),
                )
            )
            self._set_status(self._t("timezone_test_failed"), error=True)
        except Exception as exc:
            self._append_log(f"{self._t('timezone_test_failed')}: {exc}")
            self._set_status(self._t("timezone_test_failed"), error=True)
        finally:
            try:
                if get_current_timezone().casefold() != original.casefold():
                    set_timezone_verified(original)
            except Exception as exc:
                self._append_log(str(exc))

    def _stop(self) -> None:
        self.controller.stop()
        self._set_status(self._t("stopping"))

    def _emergency_stop(self) -> None:
        self.controller.stop()
        self._set_status(self._t("emergency_stop"), error=True)

    def _threadsafe_status(self, text: str) -> None:
        self.after(0, lambda: self._set_status(text))

    def _threadsafe_log(self, text: str) -> None:
        self.after(0, lambda: self._append_log(text))

    def _threadsafe_finished(self, success: bool, message: str) -> None:
        self.after(0, lambda: self._finish_ui(success, message))

    def _set_status(self, text: str, error: bool = False) -> None:
        self.status_label.configure(
            text=f"  {text}",
            text_color="#ff8a98" if error else "#6fe1b6",
        )

    def _append_log(self, text: str) -> None:
        self._log_history.append(text)
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{text}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _finish_ui(self, success: bool, message: str) -> None:
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.time_test_button.configure(state="normal")
        self.language_button.configure(state="normal")
        self._set_status(message, error=not success)

    def _on_close(self) -> None:
        self.controller.stop()
        self.hotkeys.stop()
        self.destroy()


if __name__ == "__main__":
    if os.name != "nt":
        raise SystemExit("This application only runs on Windows.")
    ctypes.windll.user32.SetProcessDPIAware()
    if not _is_admin():
        _relaunch_as_admin()
    ExpeditionAssistantApp().mainloop()
