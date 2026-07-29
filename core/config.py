from __future__ import annotations

from dataclasses import dataclass

APP_VERSION = "0.5.1"
APP_NAME = f"Expedition Assistant v{APP_VERSION}"
PALWORLD_WINDOW_TITLE = "Pal"
EXPECTED_RESOLUTION = (1920, 1080)


@dataclass(frozen=True)
class Expedition:
    key: str
    name_ru: str
    name_en: str
    duration: str
    danger_ru: str
    danger_en: str
    list_index: int
    enabled: bool = True

    def name_for(self, language: str) -> str:
        return self.name_en if language == "en" else self.name_ru

    def danger_for(self, language: str) -> str:
        return self.danger_en if language == "en" else self.danger_ru

    @property
    def name(self) -> str:
        return self.name_ru

    @property
    def danger(self) -> str:
        return self.danger_ru


EXPEDITIONS = [
    Expedition(
        "grassland_cave",
        "Пещера на равнине",
        "Grassland Cave",
        "00:45:00",
        "Низкая опасность",
        "Low danger",
        0,
    ),
    Expedition(
        "uncharted_forest",
        "Неизведанные чертоги леса",
        "Uncharted Forest Chambers",
        "00:45:00",
        "Низкая опасность",
        "Low danger",
        1,
    ),
    Expedition(
        "volcano_cave",
        "Раскалённая пещера на вулкане",
        "Scorching Volcano Cave",
        "00:45:00",
        "Средняя опасность",
        "Medium danger",
        2,
    ),
    Expedition(
        "desert_ruins",
        "Скрытые руины в пустыне",
        "Hidden Desert Ruins",
        "00:45:00",
        "Средняя опасность",
        "Medium danger",
        3,
    ),
    Expedition(
        "snowy_cave",
        "Ледяная пещера на заснеженной горе",
        "Icy Cave on the Snowy Mountain",
        "01:00:00",
        "Высокая опасность",
        "High danger",
        4,
    ),
    Expedition(
        "sakuradajima",
        "Пещера призрачных цветов на Сакурадзиме",
        "Ghost Flower Cave on Sakurajima",
        "01:00:00",
        "Высокая опасность",
        "High danger",
        5,
    ),
    Expedition(
        "tenraku_lair",
        "Логово Тэнраку",
        "Tenraku's Lair",
        "01:00:00",
        "Высокая опасность",
        "High danger",
        6,
    ),
    Expedition(
        "after_covenant_tower",
        "После победы: Башня Завета",
        "After victory: Covenant Tower",
        "—",
        "Слот будущей экспедиции",
        "Future expedition slot",
        7,
    ),
    Expedition(
        "after_sealed_realm",
        "После победы: Зал печати",
        "After victory: Sealed Realm",
        "—",
        "Слот будущей экспедиции",
        "Future expedition slot",
        8,
    ),
    Expedition(
        "after_rayne_tower_hard",
        "После сложной Башни Отряда Браконьеров Рейн",
        "After hard Rayne Syndicate Tower",
        "—",
        "Слот будущей экспедиции",
        "Future expedition slot",
        9,
    ),
    Expedition(
        "after_pidf_tower_hard",
        "После сложной Башни Организации по Защите Палов",
        "After hard PIDF Tower",
        "—",
        "Слот будущей экспедиции",
        "Future expedition slot",
        10,
    ),
    Expedition(
        "after_eternal_flame_tower_hard",
        "После сложной Башни Братства Вечного Пламени",
        "After hard Brothers of the Eternal Pyre Tower",
        "—",
        "Слот будущей экспедиции",
        "Future expedition slot",
        11,
    ),
    Expedition(
        "after_vigilante_tower_hard",
        "После сложной Башни Вигилантов",
        "After hard Vigilante Tower",
        "—",
        "Слот будущей экспедиции",
        "Future expedition slot",
        12,
    ),
    Expedition(
        "after_genetic_research_tower_hard",
        "После сложной Башни Генетических Исследований",
        "After hard Pal Genetic Research Unit Tower",
        "—",
        "Слот будущей экспедиции",
        "Future expedition slot",
        13,
    ),
    Expedition(
        "after_moonflower_tower_hard",
        "После сложной Башни Лунных Цветов",
        "After hard Moonflower Tower",
        "—",
        "Слот будущей экспедиции",
        "Future expedition slot",
        14,
    ),
    Expedition(
        "after_tenraku_tower_hard",
        "После сложной Башни Тэнраку",
        "After hard Tenraku Tower",
        "—",
        "Слот будущей экспедиции",
        "Future expedition slot",
        15,
    ),
]

# Relative jumps are resolved at runtime from the user's actual current zone.
# This keeps the same preset useful in Prague, Kyiv, Moscow, Almaty, or elsewhere.
TIMEZONE_JUMP_MINUTES = (60, 120, 180, 240, 300, 360, 480, 600, 720)
DEFAULT_TIMEZONE_JUMP_MINUTES = 120
