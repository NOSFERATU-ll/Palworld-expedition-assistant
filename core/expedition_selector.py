from __future__ import annotations

import time
from collections.abc import Callable

import cv2
import numpy as np

from core.game_input import move_screen, scroll_screen
from core.vision import Match, VisionError, capture_screen

# Geometry measured from the user's 1920x1080 borderless Pal window.
_SCROLL_X = 0.6095
_TRACK_TOP = 0.251
_TRACK_BOTTOM = 0.829
_FIRST_ROW_CENTER = 0.298
_ROW_PITCH = 0.10185
_VISIBLE_ROWS = 5.85
_LIST_CURSOR_X = 0.36
_LIST_CURSOR_Y = 0.52


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


def _find_scroll_thumb(frame: np.ndarray) -> Match | None:
    height, width = frame.shape[:2]
    x1, x2 = int(width * 0.604), int(width * 0.615)
    y1, y2 = int(height * 0.20), int(height * 0.86)
    region = frame[y1:y2, x1:x2]
    if region.size == 0:
        return None

    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)

    blue = cv2.inRange(
        hsv,
        np.array([84, 70, 70]),
        np.array([116, 255, 255]),
    )
    neutral = cv2.bitwise_and(
        cv2.inRange(gray, 145, 255),
        cv2.inRange(hsv[:, :, 1], 0, 90),
    )
    mask = cv2.bitwise_or(blue, neutral)
    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        np.ones((11, 3), np.uint8),
        iterations=2,
    )

    candidates: list[tuple[float, tuple[int, int, int, int]]] = []
    for x, y, bar_width, bar_height in _contours(mask, (x1, y1)):
        if (
            1 <= bar_width <= 20
            and height * 0.12 <= bar_height <= height * 0.32
        ):
            center_x = x + bar_width / 2
            distance = abs(center_x - width * _SCROLL_X)
            candidates.append((distance, (x, y, bar_width, bar_height)))

    if not candidates:
        return None
    distance, (x, y, bar_width, bar_height) = min(candidates, key=lambda item: item[0])
    return Match(
        "expedition_scroll_thumb",
        max(0.0, 1.0 - distance / 20),
        x,
        y,
        bar_width,
        bar_height,
    )


def _wait_for_scroll_thumb(
    timeout: float,
    *,
    stop_check: Callable[[], None] | None = None,
) -> Match:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if stop_check is not None:
            stop_check()
        frame, _origin = capture_screen()
        match = _find_scroll_thumb(frame)
        if match is not None:
            return match
        time.sleep(0.12)
    raise VisionError("Не найден ползунок списка экспедиций.")


def _row_candidates(frame: np.ndarray) -> list[Match]:
    """Detect visible expedition cards from their long horizontal borders."""
    height, width = frame.shape[:2]
    x1, x2 = int(width * 0.12), int(width * 0.60)
    y1, y2 = int(height * 0.20), int(height * 0.84)
    region = frame[y1:y2, x1:x2]
    if region.size == 0:
        return []

    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    horizontal_score = (edges > 0).sum(axis=1).astype(np.float32)
    smooth = np.convolve(horizontal_score, np.ones(3, dtype=np.float32) / 3, mode="same")

    threshold = (x2 - x1) * 0.38
    active = np.flatnonzero(smooth >= threshold)
    if active.size == 0:
        return []

    groups: list[list[int]] = []
    for index in active.tolist():
        if not groups or index - groups[-1][-1] > 16:
            groups.append([index])
        else:
            groups[-1].append(index)

    boundaries: list[int] = []
    for group in groups:
        indexes = np.asarray(group, dtype=np.int32)
        weights = smooth[indexes]
        if float(weights.sum()) <= 0:
            local_y = int(round(float(indexes.mean())))
        else:
            local_y = int(round(float((indexes * weights).sum() / weights.sum())))
        boundaries.append(local_y + y1)

    rows: list[Match] = []
    for top_line, bottom_line in zip(boundaries, boundaries[1:]):
        gap = bottom_line - top_line
        if not height * 0.06 <= gap <= height * 0.14:
            continue
        top = top_line + 2
        bottom = bottom_line - 2
        rows.append(
            Match(
                "expedition_row",
                1.0,
                x1,
                top,
                x2 - x1,
                max(1, bottom - top),
            )
        )
    rows.sort(key=lambda item: item.top)
    return rows


def _thumb_ratio(thumb: Match, height: int) -> float:
    track_top = int(height * _TRACK_TOP)
    track_bottom = int(height * _TRACK_BOTTOM)
    travel = max(1, track_bottom - track_top - thumb.height)
    return min(1.0, max(0.0, (thumb.top - track_top) / travel))


def _reset_list_to_top(
    width: int,
    height: int,
    *,
    stop_check: Callable[[], None] | None = None,
) -> Match:
    """Return the list to the first row with wheel-up events and verify it."""
    cursor_x = round(width * _LIST_CURSOR_X)
    cursor_y = round(height * _LIST_CURSOR_Y)
    move_screen(cursor_x, cursor_y)

    # More notches than the entire current list needs. Extra upward events are
    # harmless once the top is reached and avoid relying on the previous state.
    scroll_screen(cursor_x, cursor_y, 24, interval=0.025)
    time.sleep(0.22)
    thumb = _wait_for_scroll_thumb(2.0, stop_check=stop_check)

    # Some wheel events can be dropped by Unreal. Repeat in smaller batches
    # until the thumb no longer moves or it is visibly at the top.
    track_top = int(height * _TRACK_TOP)
    for _ in range(4):
        if stop_check is not None:
            stop_check()
        if thumb.top <= track_top + 4:
            return thumb
        before = thumb.top
        scroll_screen(cursor_x, cursor_y, 6, interval=0.035)
        time.sleep(0.16)
        frame, _origin = capture_screen()
        next_thumb = _find_scroll_thumb(frame)
        if next_thumb is None:
            continue
        thumb = next_thumb
        if abs(thumb.top - before) <= 1:
            return thumb
    return thumb


def _wheel_to_ratio(
    desired_ratio: float,
    width: int,
    height: int,
    thumb: Match,
    *,
    stop_check: Callable[[], None] | None = None,
) -> Match:
    """Move the list with the wheel, checking that every step really moved it."""
    cursor_x = round(width * _LIST_CURSOR_X)
    cursor_y = round(height * _LIST_CURSOR_Y)
    stalled = 0

    for _ in range(48):
        if stop_check is not None:
            stop_check()
        current_ratio = _thumb_ratio(thumb, height)
        error = desired_ratio - current_ratio
        if abs(error) <= 0.035:
            return thumb

        distance = abs(error)
        batch = 3 if distance > 0.22 else 2 if distance > 0.09 else 1
        # Positive wheel goes up; negative wheel goes down.
        notches = -batch if error > 0 else batch
        before = thumb.top
        scroll_screen(cursor_x, cursor_y, notches, interval=0.035)
        time.sleep(0.12)

        frame, _origin = capture_screen()
        next_thumb = _find_scroll_thumb(frame)
        if next_thumb is None:
            next_thumb = _wait_for_scroll_thumb(0.8, stop_check=stop_check)

        if abs(next_thumb.top - before) <= 1:
            stalled += 1
            # Reposition the pointer slightly inside the list and retry. This
            # handles the occasional wheel event swallowed by the hovered card.
            move_screen(cursor_x - 20 + stalled * 4, cursor_y)
            if stalled >= 5:
                raise VisionError(
                    "Колесо мыши пять раз подряд не сдвинуло список экспедиций."
                )
        else:
            stalled = 0
        thumb = next_thumb

    raise VisionError("Не удалось докрутить список до выбранной экспедиции.")


def _safe_click_match(row: Match, width: int) -> Match:
    safe_x = round(width * 0.36)
    return Match(
        "expedition_row",
        row.score,
        safe_x - 12,
        row.center[1] - 12,
        24,
        24,
    )


def position_expedition_row(
    list_index: int,
    total_items: int,
    *,
    stop_check: Callable[[], None] | None = None,
) -> Match:
    """Return the selected Pal expedition row using verified wheel scrolling."""
    if not 0 <= list_index < total_items:
        raise VisionError(f"Неверный номер экспедиции: {list_index}.")

    frame, _origin = capture_screen()
    height, width = frame.shape[:2]
    thumb = _reset_list_to_top(width, height, stop_check=stop_check)

    # Most currently unlocked expeditions are already visible at the top. Do
    # not scroll them at all: click the actual detected card by its order.
    frame, _origin = capture_screen()
    top_rows = _row_candidates(frame)
    if list_index < len(top_rows):
        return _safe_click_match(top_rows[list_index], width)

    max_scroll_rows = max(0.1, total_items - _VISIBLE_ROWS)
    desired_top_row = min(max(list_index - 2.5, 0.0), max_scroll_rows)
    desired_ratio = desired_top_row / max_scroll_rows
    thumb = _wheel_to_ratio(
        desired_ratio,
        width,
        height,
        thumb,
        stop_check=stop_check,
    )

    if stop_check is not None:
        stop_check()
    time.sleep(0.12)
    frame, _origin = capture_screen()
    thumb = _find_scroll_thumb(frame) or thumb
    actual_ratio = _thumb_ratio(thumb, height)
    top_row_float = actual_ratio * max_scroll_rows
    expected_y = round(
        height * _FIRST_ROW_CENTER
        + (list_index - top_row_float) * height * _ROW_PITCH
    )

    rows = _row_candidates(frame)
    if not rows:
        raise VisionError("После прокрутки не удалось распознать строки экспедиций.")

    row = min(rows, key=lambda item: abs(item.center[1] - expected_y))
    if abs(row.center[1] - expected_y) > height * 0.075:
        visible_centers = ", ".join(str(item.center[1]) for item in rows)
        raise VisionError(
            f"Не удалось сопоставить строку экспедиции {list_index + 1}: "
            f"ожидалась около Y={expected_y}; видимые центры: {visible_centers}."
        )
    return _safe_click_match(row, width)
