from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def indent_block(value: Any, spaces: int = 4) -> str:
    prefix = " " * spaces
    text = "" if value is None else str(value).rstrip()
    if not text:
        return f"{prefix}<empty>"
    return "\n".join(f"{prefix}{line}" if line else prefix for line in text.splitlines())


def format_log_message(
    title: str,
    fields: Mapping[str, Any],
    blocks: Mapping[str, Any] | None = None,
) -> str:
    lines = [title]
    for key, value in fields.items():
        lines.append(f"  {key}: {value}")
    for key, value in (blocks or {}).items():
        lines.append(f"  {key}:")
        lines.append(indent_block(value, spaces=4))
    return "\n".join(lines)
