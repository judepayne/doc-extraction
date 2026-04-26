"""
Rule facility 009 v1: Source quote quality.

Hard-gates source_ref.quote values that look like stitched or abbreviated
paraphrases rather than exact short source snippets.
"""

import re
from pathlib import Path
from typing import Any, Tuple

from rules.base import ValidationRule


ELLIPSIS_MARKERS = ("...", "…")


def _normalize_path(value: str) -> str:
    return value[1:] if value.startswith("@") else value


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def _walk(value: Any, path: str = ""):
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            yield from _walk(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


class Rule(ValidationRule):
    """Checks that quoted source refs are not ellipsis-compressed."""

    def validates(self) -> str:
        """Return entity type this rule validates."""
        return "facility"

    def required_data(self) -> list[str]:
        """Return required external data vocabulary terms."""
        return []

    def description(self) -> str:
        """Return plain English description of rule."""
        return "Facility source_ref quotes must be exact snippets, not ellipsis-compressed paraphrases"

    def set_required_data(self, data: dict) -> None:
        """Receive required data before execution."""
        pass

    def run(self) -> Tuple[str, str]:
        """Execute source quote quality checks."""
        errors = []
        source_text = ""
        source_text_path = (
            (self.entity._data.get("source_trace") or {}).get("source_text_path") or ""
        ).strip()
        if source_text_path:
            source_path = Path(_normalize_path(source_text_path))
            if not source_path.is_absolute():
                source_path = Path.cwd() / source_path
            if source_path.exists() and source_path.is_file():
                try:
                    source_text = _normalize_text(source_path.read_text(encoding="utf-8"))
                except UnicodeDecodeError:
                    source_text = ""

        for path, node in _walk(self.entity._data):
            if not isinstance(node, dict) or "quote" not in node:
                continue
            quote = node.get("quote")
            if not isinstance(quote, str):
                continue
            if any(marker in quote for marker in ELLIPSIS_MARKERS):
                errors.append(f"{path}.quote contains an ellipsis; use exact short quotes or split into multiple source_refs")
            elif source_text and _normalize_text(quote) not in source_text:
                errors.append(f"{path}.quote is not found in source_trace.source_text_path after whitespace normalization")

        if errors:
            return ("FAIL", "; ".join(errors))
        return ("PASS", "")
