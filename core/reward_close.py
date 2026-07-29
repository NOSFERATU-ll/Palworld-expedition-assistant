from __future__ import annotations

import time
from collections.abc import Callable

import cv2
import numpy as np

from core.vision import Match, VisionError, capture_screen


def locate_reward_close() -> Match | None:
    """Find the red square close button in the upper-right UI area."""
    frame, _origin = capture_screen()
    height, width = frame.shape[:2]

    # On the user's 1920x1080 layout the close button is near (1714, 194),
    # but search a region and identify the red square instead of hard-coding a click.
    x1, y1 = int(width * 0.82), int(height * 0.08)
    x2, y2 = int(width * 0.97), int(height * 0.28)
    region = frame[y1:y2, x1:x2]
    if region.size == 0:
        return None

    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
    low_red = cv2.inRange(hsv, np.array([0, 50, 55]), np.array([16, 255, 235]))
    high_red = cv2.inRange(hsv, np.array([168, 50, 55]), np.array([179, 255, 235]))
    mask = cv2.bitwise_or(low_red, high_red)
    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        np.ones((3, 3), np.uint8),
        iterations=1,
    )

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates: list[tuple[float, tuple[int, int, int, int]]] = []
    for contour in contours:
        x, y, box_width, box_height = cv2.boundingRect(contour)
        screen_x, screen_y = x + x1, y + y1
        center_x = screen_x + box_width / 2
        center_y = screen_y + box_height / 2
        aspect = box_width / max(box_height, 1)

        if (
            width * 0.010 <= box_width <= width * 0.030
            and height * 0.018 <= box_height <= height * 0.055
            and 0.75 <= aspect <= 1.30
        ):
            distance = (
                ((center_x - width * 0.893) / width) ** 2
                + ((center_y - height * 0.180) / height) ** 2
            )
            candidates.append((distance, (screen_x, screen_y, box_width, box_height)))

    if not candidates:
        return None

    distance, (x, y, box_width, box_height) = min(candidates, key=lambda item: item[0])
    return Match(
        "reward_close",
        max(0.0, 1.0 - distance * 50),
        x,
        y,
        box_width,
        box_height,
    )


def wait_for_reward_close(
    timeout: float,
    *,
    poll: float = 0.15,
    stop_check: Callable[[], None] | None = None,
) -> Match:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if stop_check is not None:
            stop_check()
        match = locate_reward_close()
        if match is not None:
            return match
        time.sleep(poll)
    raise VisionError(f"Не найден красный крестик окна награды за {timeout:.1f} с.")
