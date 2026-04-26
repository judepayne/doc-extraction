"""
Rule facility 010 v1: PDF source text extraction gate.

Requires PDF-direct facility extractions to record a text-extraction sidecar so
agents cannot silently ground JSON in raw PDF binary content.
"""

from pathlib import Path
from typing import Tuple

from rules.base import ValidationRule


def _normalize_path(value: str) -> str:
    return value[1:] if value.startswith("@") else value


class Rule(ValidationRule):
    """Checks that PDF-direct extractions identify extracted text provenance."""

    def validates(self) -> str:
        """Return entity type this rule validates."""
        return "facility"

    def required_data(self) -> list[str]:
        """Return required external data vocabulary terms."""
        return []

    def description(self) -> str:
        """Return plain English description of rule."""
        return "PDF-direct facility extractions must record extracted text provenance"

    def set_required_data(self, data: dict) -> None:
        """Receive required data before execution."""
        pass

    def run(self) -> Tuple[str, str]:
        """Execute PDF source text provenance checks."""
        source_trace = self.entity._data.get("source_trace") or {}
        source_document = _normalize_path((source_trace.get("source_document") or "").strip())
        extraction_method = source_trace.get("extraction_method") or ""
        source_text_path = _normalize_path((source_trace.get("source_text_path") or "").strip())
        source_text_char_count = source_trace.get("source_text_char_count")
        errors = []

        pdf_source = isinstance(source_document, str) and source_document.lower().endswith(".pdf")
        if not pdf_source:
            return ("PASS", "")

        if extraction_method == "manual" and not source_text_path:
            return (
                "WARN",
                "manual PDF extraction lacks source_trace.source_text_path; headless/pdf_direct extractions must include extracted text provenance",
            )

        if not source_text_path:
            errors.append("source_trace.source_text_path is required for pdf_direct/hybrid PDF extractions")
        elif source_text_path.lower().endswith(".pdf"):
            errors.append("source_trace.source_text_path must point to extracted text, not a PDF")
        else:
            source_text = Path(source_text_path)
            if not source_text.is_absolute():
                source_text = Path.cwd() / source_text
            source_doc = Path(source_document)
            if not source_doc.is_absolute():
                source_doc = Path.cwd() / source_doc

            if source_text.resolve(strict=False) == source_doc.resolve(strict=False):
                errors.append("source_trace.source_text_path must point to extracted text, not the original PDF")
            if not source_text.exists():
                errors.append(f"source_trace.source_text_path does not exist: {source_text_path}")
            elif not source_text.is_file():
                errors.append(f"source_trace.source_text_path is not a file: {source_text_path}")
            else:
                try:
                    actual_char_count = len(source_text.read_text(encoding="utf-8"))
                    if actual_char_count <= 0:
                        errors.append("source_trace.source_text_path points to an empty text file")
                    if isinstance(source_text_char_count, int) and source_text_char_count != actual_char_count:
                        errors.append(
                            "source_trace.source_text_char_count does not match extracted text file length"
                        )
                except UnicodeDecodeError:
                    errors.append("source_trace.source_text_path is not readable UTF-8 text")

        if not isinstance(source_text_char_count, int) or source_text_char_count <= 0:
            errors.append("source_trace.source_text_char_count is required and must be a positive integer for PDF text extractions")

        if errors:
            return ("FAIL", "; ".join(errors))
        return ("PASS", "")
