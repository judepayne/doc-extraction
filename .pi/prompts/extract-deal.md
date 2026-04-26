---
description: Extract one deal-level loan PDF into validated deal JSON
argument-hint: "<input-pdf> <output-json>"
---
First read and follow `skills/deal-json-extraction/SKILL.md`.

Extract the deal-level commercial loan document:

$1

Produce a valid deal JSON instance at:

$2

Use your judgement and the deal-json-extraction skill. Read the PDF/source document directly. If the source is a PDF, first call `extract_pdf_text` on `$1` and write the full extracted text to `$2.source.txt`; do not rely on raw `%PDF` binary content returned by `read`. If `extract_pdf_text` returns little or no readable text, stop and report that the PDF is not text-extractable with the available tools.

Load and conform to:

validation/models/deal.schema.v1.0.0.json

The JSON must include the canonical deal `$schema` URL, `schema_version`, `document_level`, `core`, appropriate `optional_blocks`, and `source_trace`. For PDF-direct extraction, include `source_trace.source_text_path` set to `$2.source.txt` and include `source_trace.source_text_char_count` if the tool reports it.

Use the `validate_extraction` Pi tool after writing the JSON:

entity: deal
json_path: $2

Iterate on the JSON until validation has no `FAIL`, `ERROR`, or `NORUN` results. Review `WARN` results; fix them where possible, otherwise explain briefly why any remaining warning is acceptable.

Be careful not to invent unsupported terms. Preserve qualifiers, carve-outs, defined-term aliases, clause/schedule references, dates, amounts, currencies, facility IDs, lender commitments, interest mechanics, repayment mechanics, security/intercreditor details, conditions precedent, regulatory conditions, transfer/voting mechanics, and `source_refs` where available. Use exact short snippets for `source_refs[].quote`; do not use ellipses (`...` or `…`) inside quote strings.
