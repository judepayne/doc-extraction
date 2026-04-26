#!/usr/bin/env python3
"""Extract text from a PDF for Pi agents.

This helper is intentionally small and deterministic. It gives the Pi extension a
PDF-aware read path without giving the child agent shell access.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

try:
    from pypdf import PdfReader
except ImportError as exc:  # pragma: no cover - exercised in integration only
    raise SystemExit(
        "Missing dependency 'pypdf'. Install project dependencies with: python3 -m pip install -e ."
    ) from exc


def parse_page_spec(spec: str | None, page_count: int) -> list[int]:
    """Parse a 1-based page spec like '1-3,7' into zero-based indexes."""
    if not spec:
        return list(range(page_count))

    pages: set[int] = set()
    for raw_part in spec.split(","):
        part = raw_part.strip()
        if not part:
            continue
        if "-" in part:
            start_raw, end_raw = part.split("-", 1)
            start = int(start_raw.strip())
            end = int(end_raw.strip())
            if start > end:
                raise ValueError(f"Invalid page range '{part}': start is after end")
            pages.update(range(start, end + 1))
        else:
            pages.add(int(part))

    invalid = sorted(page for page in pages if page < 1 or page > page_count)
    if invalid:
        raise ValueError(
            f"Page(s) out of range for {page_count}-page PDF: "
            + ", ".join(str(page) for page in invalid)
        )

    return [page - 1 for page in sorted(pages)]


def load_reader(pdf_path: Path) -> PdfReader:
    """Open a PDF reader, handling empty-password encrypted PDFs."""
    reader = PdfReader(str(pdf_path))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:  # pragma: no cover - depends on encrypted fixture
            raise RuntimeError("PDF is encrypted and could not be opened with an empty password") from exc
    return reader


def extract_pages(pdf_path: Path, page_indexes: Iterable[int]) -> tuple[int, list[dict]]:
    reader = load_reader(pdf_path)

    extracted = []
    for index in page_indexes:
        page = reader.pages[index]
        text = page.extract_text() or ""
        extracted.append({"page": index + 1, "text": text})
    return len(reader.pages), extracted


def render_text(pages: list[dict], include_page_markers: bool) -> str:
    chunks = []
    for page in pages:
        text = page["text"].strip("\n")
        if include_page_markers:
            chunks.append(f"===== PAGE {page['page']} =====\n{text}")
        else:
            chunks.append(text)
    return "\n\n".join(chunks).strip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract text from a PDF as JSON.")
    parser.add_argument("pdf_path", help="Path to the PDF file.")
    parser.add_argument("--pages", help="Optional 1-based page selection, e.g. '1-3,7'.")
    parser.add_argument("--output", help="Optional path to write the full extracted text.")
    parser.add_argument(
        "--max-chars",
        type=int,
        default=50_000,
        help="Maximum text characters to include in JSON stdout. Full text is still written to --output.",
    )
    parser.add_argument(
        "--no-page-markers",
        action="store_true",
        help="Do not include '===== PAGE N =====' separators in rendered text.",
    )
    args = parser.parse_args(argv)

    pdf_path = Path(args.pdf_path).expanduser().resolve()
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")
    if not pdf_path.is_file():
        raise SystemExit(f"PDF path is not a file: {pdf_path}")

    reader = load_reader(pdf_path)
    page_count = len(reader.pages)
    page_indexes = parse_page_spec(args.pages, page_count)

    page_count, pages = extract_pages(pdf_path, page_indexes)
    full_text = render_text(pages, include_page_markers=not args.no_page_markers)

    output_path = None
    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        workspace = Path.cwd().resolve()
        try:
            output_path.relative_to(workspace)
        except ValueError as exc:
            raise SystemExit(f"Output path must be inside the current project directory: {output_path}") from exc
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(full_text, encoding="utf-8")

    max_chars = max(args.max_chars, 0)
    truncated = len(full_text) > max_chars
    stdout_text = full_text[:max_chars]

    result = {
        "source_pdf": str(pdf_path),
        "output_path": str(output_path) if output_path else None,
        "page_count": page_count,
        "pages_extracted": [page["page"] for page in pages],
        "char_count": len(full_text),
        "returned_char_count": len(stdout_text),
        "truncated": truncated,
        "text": stdout_text,
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
