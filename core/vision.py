from __future__ import annotations

import base64
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import ImageGrab

from core.templates import TEMPLATES
from core.window import get_client_screen_rect


class VisionError(RuntimeError):
    pass


@dataclass(frozen=True)
class Match:
    name: str
    score: float
    left: int
    top: int
    width: int
    height: int

    @property
    def center(self) -> tuple[int, int]:
        return self.left + self.width // 2, self.top + self.height // 2


_TEMPLATE_CACHE: dict[str, np.ndarray] = {}


def _template(name: str) -> np.ndarray:
    cached = _TEMPLATE_CACHE.get(name)
    if cached is not None:
        return cached
    spec = TEMPLATES[name]
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    raw = base64.b64decode((base / "assets" / spec.filename).read_text(encoding="ascii"))
    decoded = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if decoded is None:
        raise VisionError(f"Не удалось загрузить шаблон {name!r}.")
    _TEMPLATE_CACHE[name] = decoded
    return decoded


def capture_client(hwnd: int) -> tuple[np.ndarray, tuple[int, int]]:
    left, top, right, bottom = get_client_screen_rect(hwnd)
    image = ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)
    frame = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2GRAY)
    return frame, (left, top)


def locate(hwnd: int, name: str, threshold: float | None = None) -> Match | None:
    frame, origin = capture_client(hwnd)
    template = _template(name)
    if frame.shape[0] < template.shape[0] or frame.shape[1] < template.shape[1]:
        return None
    result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
    _, score, _, location = cv2.minMaxLoc(result)
    required = TEMPLATES[name].threshold if threshold is None else threshold
    if score < required:
        return None
    x, y = location
    h, w = template.shape[:2]
    return Match(name, float(score), origin[0] + x, origin[1] + y, w, h)


def wait_for(hwnd: int, name: str, timeout: float, poll: float = 0.18) -> Match:
    deadline = time.monotonic() + timeout
    best = 0.0
    while time.monotonic() < deadline:
        frame, origin = capture_client(hwnd)
        template = _template(name)
        result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        _, score, _, location = cv2.minMaxLoc(result)
        best = max(best, float(score))
        if score >= TEMPLATES[name].threshold:
            x, y = location
            h, w = template.shape[:2]
            return Match(name, float(score), origin[0] + x, origin[1] + y, w, h)
        time.sleep(poll)
    raise VisionError(f"Не найден элемент {name!r} за {timeout:.1f} с. Лучшее совпадение: {best:.3f}.")


def wait_until_gone(hwnd: int, name: str, timeout: float, poll: float = 0.2) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if locate(hwnd, name) is None:
            return
        time.sleep(poll)
    raise VisionError(f"Элемент {name!r} не исчез за {timeout:.1f} с.")
