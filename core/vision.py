from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import ImageGrab


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
    scale: float = 1.0

    @property
    def center(self) -> tuple[int, int]:
        return self.left + self.width // 2, self.top + self.height // 2


def capture_screen() -> tuple[np.ndarray, tuple[int, int]]:
    image = ImageGrab.grab(all_screens=False)
    frame = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    return frame, (0, 0)


def _contours(
    mask: np.ndarray,
    offset: tuple[int, int] = (0, 0),
    *,
    mode: int = cv2.RETR_EXTERNAL,
) -> list[tuple[int, int, int, int]]:
    contours, _ = cv2.findContours(mask, mode, cv2.CHAIN_APPROX_SIMPLE)
    ox, oy = offset
    return [
        (x + ox, y + oy, width, height)
        for contour in contours
        for x, y, width, height in [cv2.boundingRect(contour)]
    ]


def _row_candidates(frame: np.ndarray) -> list[tuple[int, int, int, int]]:
    height, width = frame.shape[:2]
    x1, y1 = int(width * 0.05), int(height * 0.15)
    x2, y2 = int(width * 0.68), int(height * 0.90)
    gray = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)

    rows: list[tuple[int, int, int, int]] = []
    for x, y, row_width, row_height in _contours(
        edges,
        (x1, y1),
        mode=cv2.RETR_LIST,
    ):
        if (
            row_width >= width * 0.35
            and height * 0.055 <= row_height <= height * 0.14
            and row_width / max(row_height, 1) >= 5
        ):
            rows.append((x, y, row_width, row_height))

    rows.sort(key=lambda item: (item[1], -item[2]))
    unique: list[tuple[int, int, int, int]] = []
    for row in rows:
        if not any(
            abs(row[1] - old[1]) < 8 and abs(row[2] - old[2]) < 35
            for old in unique
        ):
            unique.append(row)
    return unique


def _find_auto(frame: np.ndarray) -> Match | None:
    height, width = frame.shape[:2]
    x1, y1 = int(width * 0.05), int(height * 0.58)
    x2, y2 = int(width * 0.40), int(height * 0.88)
    hsv = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([0, 0, 55]), np.array([179, 50, 190]))
    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        np.ones((3, 3), np.uint8),
        iterations=2,
    )

    candidates: list[tuple[float, tuple[int, int, int, int]]] = []
    for x, y, button_width, button_height in _contours(mask, (x1, y1)):
        center_x = x + button_width / 2
        center_y = y + button_height / 2
        if (
            width * 0.08 < button_width < width * 0.18
            and height * 0.02 < button_height < height * 0.07
            and 3.5 < button_width / max(button_height, 1) < 12
            and width * 0.16 < center_x < width * 0.36
        ):
            distance = (
                ((center_x - width * 0.24) / width) ** 2
                + ((center_y - height * 0.73) / height) ** 2
            )
            candidates.append(
                (distance, (x, y, button_width, button_height))
            )

    if not candidates:
        return None
    distance, (x, y, button_width, button_height) = min(
        candidates,
        key=lambda item: item[0],
    )
    return Match(
        "auto_button",
        max(0.0, 1.0 - distance * 20),
        x,
        y,
        button_width,
        button_height,
    )


def _find_start(frame: np.ndarray) -> Match | None:
    height, width = frame.shape[:2]
    x1, y1 = int(width * 0.30), int(height * 0.65)
    x2, y2 = int(width * 0.72), int(height * 0.95)
    hsv = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(
        hsv,
        np.array([95, 150, 120]),
        np.array([115, 255, 255]),
    )
    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        np.ones((3, 7), np.uint8),
        iterations=1,
    )

    candidates: list[tuple[float, tuple[int, int, int, int]]] = []
    for x, y, button_width, button_height in _contours(mask, (x1, y1)):
        center_x = x + button_width / 2
        center_y = y + button_height / 2
        if (
            width * 0.10 < button_width < width * 0.25
            and height * 0.02 < button_height < height * 0.07
            and button_width / max(button_height, 1) > 4
            and height * 0.72 < center_y < height * 0.90
        ):
            distance = (
                ((center_x - width * 0.50) / width) ** 2
                + ((center_y - height * 0.825) / height) ** 2
            )
            candidates.append(
                (distance, (x, y, button_width, button_height))
            )

    if not candidates:
        return None
    distance, (x, y, button_width, button_height) = min(
        candidates,
        key=lambda item: item[0],
    )
    return Match(
        "start_button",
        max(0.0, 1.0 - distance * 20),
        x,
        y,
        button_width,
        button_height,
    )


def _find_completed(frame: np.ndarray) -> Match | None:
    height, width = frame.shape[:2]
    x1, y1 = int(width * 0.25), int(height * 0.20)
    x2, y2 = int(width * 0.70), int(height * 0.65)
    hsv = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(
        hsv,
        np.array([70, 70, 60]),
        np.array([95, 255, 255]),
    )
    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        np.ones((3, 5), np.uint8),
        iterations=1,
    )

    candidates: list[tuple[float, tuple[int, int, int, int]]] = []
    for x, y, badge_width, badge_height in _contours(mask, (x1, y1)):
        center_x = x + badge_width / 2
        center_y = y + badge_height / 2
        if (
            width * 0.03 < badge_width < width * 0.12
            and height * 0.012 < badge_height < height * 0.05
            and badge_width / max(badge_height, 1) > 2
            and width * 0.35 < center_x < width * 0.60
            and height * 0.35 < center_y < height * 0.55
        ):
            distance = (
                ((center_x - width * 0.445) / width) ** 2
                + ((center_y - height * 0.445) / height) ** 2
            )
            candidates.append(
                (distance, (x, y, badge_width, badge_height))
            )

    if not candidates:
        return None
    distance, (x, y, badge_width, badge_height) = min(
        candidates,
        key=lambda item: item[0],
    )
    return Match(
        "completed",
        max(0.0, 1.0 - distance * 20),
        x,
        y,
        badge_width,
        badge_height,
    )


def _find_reward_header(frame: np.ndarray) -> Match | None:
    height, width = frame.shape[:2]
    x1, y1 = int(width * 0.56), int(height * 0.184)
    x2, y2 = int(width * 0.867), int(height * 0.214)
    region = frame[y1:y2, x1:x2]
    if region.size == 0:
        return None

    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
    mean = float(gray.mean())
    dark_share = float((gray < 50).mean())
    bright_share = float((gray > 170).mean())
    saturation = float(hsv[:, :, 1].mean())

    if (
        mean > 80
        and dark_share < 0.08
        and bright_share > 0.035
        and saturation < 80
    ):
        score = min(1.0, 0.75 + (mean - 80) / 100)
        return Match(
            "reward_header",
            score,
            x1,
            y1,
            x2 - x1,
            y2 - y1,
        )
    return None


def locate(name: str, threshold: float | None = None) -> Match | None:
    del threshold
    frame, origin = capture_screen()

    if name == "menu_header":
        rows = _row_candidates(frame)
        if len(rows) >= 4:
            x, y, row_width, _ = rows[0]
            return Match(
                name,
                1.0,
                x,
                max(origin[1], y - int(frame.shape[0] * 0.10)),
                row_width,
                int(frame.shape[0] * 0.04),
            )
        return None

    if name == "expedition_title":
        rows = [
            row
            for row in _row_candidates(frame)
            if row[1] > frame.shape[0] * 0.20
        ]
        if not rows:
            return None
        x, y, row_width, row_height = rows[0]
        return Match(name, 1.0, x, y, row_width, row_height)

    if name == "auto_button":
        return _find_auto(frame)
    if name == "start_button":
        return _find_start(frame)
    if name == "completed":
        return _find_completed(frame)
    if name == "reward_header":
        return _find_reward_header(frame)

    raise VisionError(f"Неизвестный визуальный элемент: {name!r}.")


def wait_for(
    name: str,
    timeout: float,
    *,
    poll: float = 0.20,
    stop_check: Callable[[], None] | None = None,
) -> Match:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if stop_check is not None:
            stop_check()
        match = locate(name)
        if match is not None:
            return match
        time.sleep(poll)
    raise VisionError(f"Не найден элемент {name!r} за {timeout:.1f} с.")


def wait_until_gone(
    name: str,
    timeout: float,
    *,
    poll: float = 0.20,
    stop_check: Callable[[], None] | None = None,
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if stop_check is not None:
            stop_check()
        if locate(name) is None:
            return
        time.sleep(poll)
    raise VisionError(f"Элемент {name!r} не исчез за {timeout:.1f} с.")


def validate_templates() -> None:
    # Оставлено для совместимости со сборочным тестом. Текущая версия ищет
    # элементы по форме и цветам живого интерфейса и не использует assets.
    return None
