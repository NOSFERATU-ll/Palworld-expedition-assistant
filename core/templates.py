from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TemplateSpec:
    filename: str
    threshold: float


TEMPLATES: dict[str, TemplateSpec] = {
    "menu_header": TemplateSpec("menu_header.b64", 0.88),
    "expedition_title": TemplateSpec("expedition_title.b64", 0.88),
    "auto_button": TemplateSpec("auto_button.b64", 0.88),
    "start_button": TemplateSpec("start_button.b64", 0.84),
    "completed": TemplateSpec("completed.b64", 0.86),
    "reward_header": TemplateSpec("reward_header.b64", 0.88),
    "take_all": TemplateSpec("take_all.b64", 0.88),
}
