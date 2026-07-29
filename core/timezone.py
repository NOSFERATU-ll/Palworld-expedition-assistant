from __future__ import annotations

import ctypes
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime

HWND_BROADCAST = 0xFFFF
WM_TIMECHANGE = 0x001E
SMTO_ABORTIFHUNG = 0x0002


class TimezoneError(RuntimeError):
    pass


class TimezoneResolutionError(TimezoneError):
    def __init__(self, current_offset_minutes: int, target_offset_minutes: int) -> None:
        self.current_offset_minutes = current_offset_minutes
        self.target_offset_minutes = target_offset_minutes
        super().__init__(
            "No installed Windows time zone currently matches the requested offset: "
            f"{current_offset_minutes} -> {target_offset_minutes} minutes from UTC."
        )


@dataclass(frozen=True)
class ResolvedTimezone:
    timezone_id: str
    current_offset_minutes: int
    target_offset_minutes: int


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
        details = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise TimezoneError(f"tzutil failed: {details}")
    return completed.stdout.strip()


def _run_powershell(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def _broadcast_time_change() -> None:
    result = ctypes.c_size_t()
    ctypes.windll.user32.SendMessageTimeoutW(
        HWND_BROADCAST,
        WM_TIMECHANGE,
        0,
        0,
        SMTO_ABORTIFHUNG,
        2000,
        ctypes.byref(result),
    )


def get_current_timezone() -> str:
    timezone_id = _run_tzutil("/g")
    if not timezone_id:
        raise TimezoneError("Windows did not return the current time zone.")
    return timezone_id


def get_local_time_text() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def resolve_timezone_for_jump(delta_minutes: int) -> ResolvedTimezone:
    """Find an installed Windows zone currently `delta_minutes` ahead.

    The lookup uses the current UTC instant, so daylight-saving time is included.
    It intentionally resolves a fresh target from the user's own current zone
    instead of assuming Prague, Kyiv, Moscow, or any other home location.
    """
    if delta_minutes <= 0:
        raise ValueError("Time-zone jump must be positive.")

    script = rf"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$now = [DateTime]::UtcNow
$current = Get-TimeZone
$currentInfo = [TimeZoneInfo]::FindSystemTimeZoneById($current.Id)
$currentMinutes = [int][Math]::Round($currentInfo.GetUtcOffset($now).TotalMinutes)
$targetMinutes = $currentMinutes + {int(delta_minutes)}
$candidates = [TimeZoneInfo]::GetSystemTimeZones() | Where-Object {{
    $_.Id -ne $current.Id -and
    [int][Math]::Round($_.GetUtcOffset($now).TotalMinutes) -eq $targetMinutes
}} | Sort-Object `
    @{{Expression={{ if ($_.SupportsDaylightSavingTime) {{ 1 }} else {{ 0 }} }}}}, `
    @{{Expression={{ $_.Id }}}}
$target = $candidates | Select-Object -First 1
if ($null -eq $target) {{
    Write-Output ("NO_MATCH|{{0}}|{{1}}" -f $currentMinutes, $targetMinutes)
    exit 4
}}
Write-Output ("OK|{{0}}|{{1}}|{{2}}" -f $currentMinutes, $targetMinutes, $target.Id)
"""
    completed = _run_powershell(script)
    output_lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    marker = output_lines[-1] if output_lines else ""

    if marker.startswith("NO_MATCH|"):
        _kind, current_text, target_text = marker.split("|", 2)
        raise TimezoneResolutionError(int(current_text), int(target_text))

    if completed.returncode != 0 or not marker.startswith("OK|"):
        details = completed.stderr.strip() or marker or "unknown PowerShell error"
        raise TimezoneError(f"Could not resolve a relative Windows time zone: {details}")

    _kind, current_text, target_text, timezone_id = marker.split("|", 3)
    return ResolvedTimezone(
        timezone_id=timezone_id,
        current_offset_minutes=int(current_text),
        target_offset_minutes=int(target_text),
    )


def set_timezone_verified(timezone_id: str, retries: int = 3) -> None:
    last_seen = ""
    for _attempt in range(1, retries + 1):
        _run_tzutil("/s", timezone_id)
        _broadcast_time_change()
        time.sleep(0.6)
        last_seen = get_current_timezone()
        if last_seen.casefold() == timezone_id.casefold():
            return
        time.sleep(0.6)
    raise TimezoneError(
        "Windows did not keep the requested time zone. "
        f"Requested: {timezone_id}; actual: {last_seen or 'unknown'}."
    )


set_timezone = set_timezone_verified
