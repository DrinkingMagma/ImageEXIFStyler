from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from core import PROJECT_ROOT


TEMPLATE_INPUTS_PATH = PROJECT_ROOT / "config" / "template_inputs.json"


@dataclass(frozen=True)
class TemplateInputSpec:
    key: str
    label: str
    dialog_title: str
    dialog_prompt: str
    default: str = ""
    ascii_only: bool = False
    allow_empty: bool = True


TEMPLATE_INPUT_SPECS: dict[str, tuple[TemplateInputSpec, ...]] = {
    "背景模糊（自定义文字）": (
        TemplateInputSpec(
            key="custom_text",
            label="自定义文字",
            dialog_title="设置自定义文字",
            dialog_prompt="请输入自定义文字（英文）",
            default="Hello World!",
            ascii_only=True,
            allow_empty=False,
        ),
    ),
}


def get_template_input_specs(template_name: str) -> list[TemplateInputSpec]:
    return list(TEMPLATE_INPUT_SPECS.get(template_name, ()))


def _normalize_template_values(values: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in values.items():
        if not isinstance(key, str):
            continue
        normalized[key] = "" if value is None else str(value)
    return normalized


def load_template_inputs() -> dict[str, dict[str, str]]:
    if not TEMPLATE_INPUTS_PATH.exists():
        return {}

    try:
        data = json.loads(TEMPLATE_INPUTS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(data, dict):
        return {}

    result: dict[str, dict[str, str]] = {}
    for template_name, values in data.items():
        if not isinstance(template_name, str) or not isinstance(values, dict):
            continue
        result[template_name] = _normalize_template_values(values)
    return result


def get_template_inputs(template_name: str) -> dict[str, str]:
    stored = load_template_inputs().get(template_name, {})
    merged = {spec.key: spec.default for spec in get_template_input_specs(template_name)}
    merged.update(stored)
    return merged


def format_template_display_name(template_name: str) -> str:
    specs = get_template_input_specs(template_name)
    if not specs:
        return template_name

    values = get_template_inputs(template_name)
    suffixes = [values.get(spec.key, "").strip() for spec in specs]
    suffixes = [suffix for suffix in suffixes if suffix]
    if not suffixes:
        return template_name
    return f"{template_name} - {' / '.join(suffixes)}"


def validate_template_input(spec: TemplateInputSpec, value: str) -> tuple[bool, str]:
    normalized = value.strip()
    if not spec.allow_empty and not normalized:
        return False, f"{spec.label}不能为空。"

    if spec.ascii_only and any(ord(char) > 127 for char in normalized):
        return False, f"{spec.label}仅允许使用英文、数字、空格和半角符号。"

    return True, ""


def save_template_inputs(template_name: str, values: dict[str, Any]) -> None:
    store = load_template_inputs()
    store[template_name] = _normalize_template_values(values)

    TEMPLATE_INPUTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATE_INPUTS_PATH.write_text(
        json.dumps(store, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
