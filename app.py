from __future__ import annotations

import ctypes
import os
import queue
import sys
from pathlib import Path

import customtkinter as ctk

from core.automation import AutomationController, AutomationSettings
from core.config import APP_NAME, EXPEDITIONS, TIMEZONE_PRESETS
from core.hotkeys import GlobalHotkeys


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _relaunch_as_admin() -> None:
    if getattr(sys, "frozen", False):
        executable = sys.executable
        params = " ".join(f'\"{arg}\"' for arg in sys.argv[1:])
    else:
        executable = sys.executable
        script = str(Path(__file__).resolve())
        params = " ".join([f'\"{script}\"', *[f'\"{arg}\"' for arg in sys.argv[1:]]])
    result = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, os.getcwd(), 1)
    if result <= 32:
        raise RuntimeError("Windows отклонила запуск с правами администратора.")
    raise SystemExit(0)


class ExpeditionAssistantApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry("980x650")
        self.minsize(900, 600)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.controller = AutomationController(
            on_status=self._threadsafe_status,
            on_log=self._threadsafe_log,
            on_finished=self._threadsafe_finished,
        )
        self._hotkey_events: queue.SimpleQueue[str] = queue.SimpleQueue()
        self.hotkeys = GlobalHotkeys(
            callback=self._queue_hotkey,
            on_error=lambda text: self._hotkey_events.put(f"error:{text}"),
        )

        self._build_ui()
        self.hotkeys.start()
        self.after(50, self._poll_hotkeys)
        self.after(250, self._refresh_environment)

    def _queue_hotkey(self, action: str) -> None:
        self._hotkey_events.put(action)

    def _poll_hotkeys(self) -> None:
        while True:
            try:
                event = self._hotkey_events.get_nowait()
            except queue.Empty:
                break
            if event == "start":
                self._start()
            elif event == "stop":
                self._emergency_stop()
            elif event.startswith("error:"):
                self._append_log(event.removeprefix("error:"))
                self._set_status("Горячие клавиши не зарегистрированы", error=True)
        self.after(50, self._poll_hotkeys)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, corner_radius=0, fg_color="#0d1c24")
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="PALWORLD  •  ЭКСПЕДИЦИИ", font=ctk.CTkFont(size=13, weight="bold"), text_color="#63d8ee").grid(row=0, column=0, padx=28, pady=(18, 2), sticky="w")
        ctk.CTkLabel(header, text="Expedition Assistant", font=ctk.CTkFont(size=30, weight="bold")).grid(row=1, column=0, padx=28, pady=(0, 18), sticky="w")
        self.env_label = ctk.CTkLabel(header, text="Проверяю экран…", text_color="#a9bdc6")
        self.env_label.grid(row=0, column=1, rowspan=2, padx=28, sticky="e")

        left = ctk.CTkFrame(self, corner_radius=18, fg_color="#10252e")
        left.grid(row=1, column=0, padx=(22, 10), pady=20, sticky="nsew")
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(left, text="Выбери экспедицию", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=22, pady=(22, 5), sticky="w")
        ctk.CTkLabel(left, text="Настрой один раз и запускай из игры клавишей F6.", text_color="#91a9b3").grid(row=1, column=0, padx=22, pady=(0, 14), sticky="w")
        box = ctk.CTkScrollableFrame(left, fg_color="transparent")
        box.grid(row=2, column=0, padx=14, pady=(0, 12), sticky="nsew")
        box.grid_columnconfigure(0, weight=1)
        self.expedition_var = ctk.StringVar(value=EXPEDITIONS[0].key)
        for index, expedition in enumerate(EXPEDITIONS):
            enabled = expedition.enabled
            card = ctk.CTkRadioButton(
                box,
                variable=self.expedition_var,
                value=expedition.key,
                text=f"{expedition.name}\n{expedition.duration}  •  {expedition.danger}",
                font=ctk.CTkFont(size=15, weight="bold"),
                text_color="#e6f2f5" if enabled else "#657981",
                fg_color="#14b8d4",
                hover_color="#0b91ab",
                state="normal" if enabled else "disabled",
                height=64,
            )
            card.grid(row=index, column=0, padx=8, pady=7, sticky="ew")

        right = ctk.CTkFrame(self, corner_radius=18, fg_color="#10252e")
        right.grid(row=1, column=1, padx=(10, 22), pady=20, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(7, weight=1)
        ctk.CTkLabel(right, text="Параметры запуска", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=22, pady=(22, 15), sticky="w")
        ctk.CTkLabel(right, text="Часовой пояс для прыжка", text_color="#9fb2ba").grid(row=1, column=0, padx=22, sticky="w")
        timezone_names = list(TIMEZONE_PRESETS)
        self.timezone_var = ctk.StringVar(value=timezone_names[0])
        ctk.CTkOptionMenu(right, variable=self.timezone_var, values=timezone_names, height=38).grid(row=2, column=0, padx=22, pady=(6, 14), sticky="ew")

        self.cycles_var = ctk.StringVar(value="1")
        ctk.CTkLabel(right, text="Повторений", text_color="#9fb2ba").grid(row=3, column=0, padx=22, sticky="w")
        ctk.CTkEntry(right, textvariable=self.cycles_var, height=38).grid(row=4, column=0, padx=22, pady=(6, 12), sticky="ew")

        hotkeys = ctk.CTkFrame(right, corner_radius=10, fg_color="#0b1b22")
        hotkeys.grid(row=5, column=0, padx=22, pady=(2, 10), sticky="ew")
        hotkeys.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(hotkeys, text="F6  Запустить", font=ctk.CTkFont(size=13, weight="bold"), text_color="#63d8ee").grid(row=0, column=0, padx=12, pady=10, sticky="w")
        ctk.CTkLabel(hotkeys, text="F8  Остановить", font=ctk.CTkFont(size=13, weight="bold"), text_color="#ff8a98").grid(row=0, column=1, padx=12, pady=10, sticky="e")

        self.status_label = ctk.CTkLabel(right, text="Готова • F6 работает глобально", anchor="w", corner_radius=10, fg_color="#0b1b22", text_color="#6fe1b6", height=44)
        self.status_label.grid(row=6, column=0, padx=22, pady=(2, 12), sticky="ew")
        self.log_box = ctk.CTkTextbox(right, corner_radius=10, fg_color="#09171d", text_color="#b9ced6", font=ctk.CTkFont(family="Consolas", size=12))
        self.log_box.grid(row=7, column=0, padx=22, pady=(6, 12), sticky="nsew")
        self.log_box.insert("end", "Оставь программу запущенной, встань перед Центром экспедиций и нажми F6.\n")
        self.log_box.configure(state="disabled")

        buttons = ctk.CTkFrame(right, fg_color="transparent")
        buttons.grid(row=8, column=0, padx=22, pady=(0, 22), sticky="ew")
        buttons.grid_columnconfigure((0, 1), weight=1)
        self.start_button = ctk.CTkButton(buttons, text="▶  Запустить сейчас", height=46, font=ctk.CTkFont(size=15, weight="bold"), command=self._start)
        self.start_button.grid(row=0, column=0, padx=(0, 6), sticky="ew")
        self.stop_button = ctk.CTkButton(buttons, text="■  Остановить (F8)", height=46, fg_color="#8d3441", hover_color="#a74150", state="disabled", command=self._stop)
        self.stop_button.grid(row=0, column=1, padx=(6, 0), sticky="ew")

    def _refresh_environment(self) -> None:
        width, height = self.winfo_screenwidth(), self.winfo_screenheight()
        try:
            dpi = ctypes.windll.user32.GetDpiForSystem()
        except Exception:
            dpi = 96
        scale = round(dpi / 96 * 100)
        ok = width == 1920 and height == 1080 and scale == 100
        self.env_label.configure(text=f"{'✓' if ok else '⚠'}  {width}×{height}  •  {scale}%", text_color="#6fe1b6" if ok else "#ffbd69")

    def _start(self) -> None:
        if self.controller.running:
            return
        try:
            cycles = int(self.cycles_var.get())
            if not 1 <= cycles <= 999:
                raise ValueError
        except ValueError:
            self._set_status("Проверь число повторений", error=True)
            return
        expedition = next(item for item in EXPEDITIONS if item.key == self.expedition_var.get())
        settings = AutomationSettings(expedition, TIMEZONE_PRESETS[self.timezone_var.get()], cycles)
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self._append_log("—" * 42)
        self.controller.start(settings)

    def _stop(self) -> None:
        self.controller.stop()
        self._set_status("Останавливаю…")

    def _emergency_stop(self) -> None:
        self.controller.stop()
        self._set_status("Аварийная остановка F8", error=True)

    def _threadsafe_status(self, text: str) -> None:
        self.after(0, lambda: self._set_status(text))

    def _threadsafe_log(self, text: str) -> None:
        self.after(0, lambda: self._append_log(text))

    def _threadsafe_finished(self, success: bool, message: str) -> None:
        self.after(0, lambda: self._finish_ui(success, message))

    def _set_status(self, text: str, error: bool = False) -> None:
        self.status_label.configure(text=f"  {text}", text_color="#ff8a98" if error else "#6fe1b6")

    def _append_log(self, text: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{text}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _finish_ui(self, success: bool, message: str) -> None:
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self._set_status(message, error=not success)

    def _on_close(self) -> None:
        self.controller.stop()
        self.hotkeys.stop()
        self.destroy()


if __name__ == "__main__":
    if os.name != "nt":
        raise SystemExit("Приложение работает только в Windows.")
    ctypes.windll.user32.SetProcessDPIAware()
    if not _is_admin():
        _relaunch_as_admin()
    ExpeditionAssistantApp().mainloop()
