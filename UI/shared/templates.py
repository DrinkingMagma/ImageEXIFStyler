from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.util import list_templates
from UI.shared.paths import TEMPLATE_IMAGE_DIR


@dataclass(frozen=True)
class TemplateSpec:
    name: str
    thumbnail_path: Path


FEATURED_TEMPLATE_ORDER = [
    "背景模糊",
    "背景模糊（自定义文字）",
    "自定义文字",
    "标准水印",
    "标准水印2",
    "背景模糊（尼康专用）",
]


def build_template_specs() -> list[TemplateSpec]:
    template_names = list_templates()
    ordered_names = [name for name in FEATURED_TEMPLATE_ORDER if name in template_names]
    ordered_names.extend(sorted(name for name in template_names if name not in ordered_names))
    return [TemplateSpec(name, TEMPLATE_IMAGE_DIR / f"{name}.jpg") for name in ordered_names]


TEMPLATE_SPECS = build_template_specs()
