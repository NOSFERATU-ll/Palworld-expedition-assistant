from __future__ import annotations

from dataclasses import dataclass

APP_NAME = "Palworld Expedition Assistant"
PALWORLD_WINDOW_TITLE = "Palworld"
EXPECTED_RESOLUTION = (1920, 1080)


@dataclass(frozen=True)
class Expedition:
    key: str
    name: str
    duration: str
    danger: str
    list_click: tuple[int, int]
    enabled: bool = False


# Координаты сняты с видео: 1920×1080, масштаб Windows 100%, окно без рамки.
EXPEDITIONS = [
    Expedition(
        key="grassland_cave",
        name="Пещера на равнине",
        duration="00:30:00",
        danger="Низкая опасность",
        list_click=(600, 220),
        enabled=True,
    ),
    Expedition("uncharted_forest", "Неизведанные чертоги леса", "—", "Низкая опасность", (600, 325)),
    Expedition("volcano_cave", "Раскалённая пещера на вулкане", "—", "Средняя опасность", (600, 445)),
    Expedition("desert_ruins", "Скрытые руины в пустыне", "—", "Средняя опасность", (600, 570)),
    Expedition("snowy_cave", "Ледяная пещера на заснеженной горе", "—", "Высокая опасность", (600, 695)),
    Expedition("sakuradajima", "Пещера призрачных цветов на Сакурадзиме", "—", "Высокая опасность", (600, 820)),
]

TIMEZONE_PRESETS = {
    "Афины  •  +1 час от Праги": "GTB Standard Time",
}


@dataclass(frozen=True)
class ScreenCoordinates:
    auto_button: tuple[int, int] = (460, 790)
    start_button: tuple[int, int] = (955, 895)
    reward_close_button: tuple[int, int] = (1716, 195)


COORDS = ScreenCoordinates()
