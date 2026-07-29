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
    template_name: str
    enabled: bool = False


EXPEDITIONS = [
    Expedition(
        key="grassland_cave",
        name="Пещера на равнине",
        duration="00:30:00",
        danger="Низкая опасность",
        template_name="expedition_title",
        enabled=True,
    ),
    Expedition("uncharted_forest", "Неизведанные чертоги леса", "—", "Низкая опасность", "", False),
    Expedition("volcano_cave", "Раскалённая пещера на вулкане", "—", "Средняя опасность", "", False),
    Expedition("desert_ruins", "Скрытые руины в пустыне", "—", "Средняя опасность", "", False),
    Expedition("snowy_cave", "Ледяная пещера на заснеженной горе", "—", "Высокая опасность", "", False),
    Expedition("sakuradajima", "Пещера призрачных цветов на Сакурадзиме", "—", "Высокая опасность", "", False),
]

TIMEZONE_PRESETS = {
    "Афины  •  +1 час от Праги": "GTB Standard Time",
}
