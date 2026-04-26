---
name: facility-json-extraction
description: Extracts commercial loan facility documents directly from PDF/text into JSON conforming to validation/models/facility.schema.v1.0.0.json. Use for single-facility agreements, facility term sheets, and facility amendment documents; validate output with the validate_extraction Pi tool.
---

# Facility JSON Extraction

Use this skill when asked to read a commercial loan **facility-level** document and produce JSON conforming to:

```text
validation/models/facility.schema.v1.0.0.json
```

The output must include:

```json
{
  "$schema": "https://raw.githubusercontent.com/judepayne/doc-extraction/main/validation/models/facility.schema.v1.0.0.json",
  "schema_version": "1.0.0",
  "document_level": "facility",
  "core": {
    "document": {},
    "parties": {},
    "facility": {},
    "legal": {}
  },
  "optional_blocks": {},
  "source_trace": {}
}
```

## Mission

Extract directly from the source PDF/document into schema-conformant JSON. Do **not** stage through a loose intermediate blob; prior experiments showed that blob-mediated extraction loses qualifiers, aliases, clause titles and factual distinctions that cannot be recovered later.

Use validation as a feedback loop, not as a substitute for reading the document.

## Hierarchy check

Use this skill for **facility-level** documents:

```text
Deal -> Facility -> Loan instrument / drawdown
```

Examples:

- bilateral facility agreement,
- single-facility revolving or term facility agreement,
- binding facility term sheet,
- facility amendment, using `optional_blocks.amendment_overlay`.

If the document governs multiple facilities/tranches, use the deal extraction skill instead. If it is an individual drawdown, utilisation request, note or loan instrument under a facility, do not force it into the facility schema without user confirmation.

## Extraction workflow

1. Load `validation/models/facility.schema.v1.0.0.json`.
2. Read the source document directly. For PDFs, use the Pi `extract_pdf_text` tool first, preferably with an `output_path` text sidecar; do not rely on raw `%PDF` binary content returned by `read`.
3. If using `extract_pdf_text`, record the sidecar path in `source_trace.source_text_path` and, if known, the extracted character count in `source_trace.source_text_char_count`.
4. Decide whether the document is facility-level.
5. Fill `core` first: document identity, parties, facility economics, governing law.
6. Add only optional blocks supported by the source.
7. Preserve material details, qualifiers, carve-outs, defined-term aliases and clause/schedule titles.
8. Save the JSON.
9. Use the Pi `validate_extraction` tool with `entity: "facility"` and the JSON path.
10. Fix all `FAIL`, `ERROR` and `NORUN` results. Treat `WARN` results as review prompts; resolve them where possible or note why left unresolved.

## What validation checks

The facility ruleset currently includes these high-value checks:

1. **Schema conformance** — JSON must conform to the facility schema.
2. **Core business completeness** — borrower, finance party, facility ID/type/currency/amount and governing law must be present.
3. **Document subtype consistency** — term sheets need `term_sheet_terms`; amendments need `amendment_overlay`; public-body lenders should have `public_sector_terms`.
4. **Interest consistency** — fixed/floating/reference-rate terms must be internally coherent.
5. **Date and maturity sanity** — availability, maturity, termination and tenor information should be chronologically plausible.
6. **Security consistency** — secured/unsecured status, priority, assets, guarantees and perfection details must not contradict each other.
7. **Conditions precedent consistency** — regulatory and security dependencies should be reflected in CPs where extracted.
8. **Provenance** — source trace is required; material optional blocks should carry source references where possible.
9. **Source quote quality** — `source_refs[].quote` values must be exact short snippets, not ellipsis-compressed paraphrases.
10. **PDF text provenance** — `pdf_direct`/`hybrid` extractions from PDFs must record an extracted text sidecar path.

Validation catches malformed, missing or internally inconsistent JSON. It does **not** prove the extracted facts are correct against the PDF.

## Core extraction guidance

### `core.document`

Capture:

- `document_type`, e.g. `facility_agreement`, `loan_facility_term_sheet`, `credit_agreement_amendment`;
- source file;
- agreement/effective/document date where stated;
- execution status;
- binding status if obvious;
- hierarchy note when classification may be questioned.

### `core.parties`

Use party definitions from the parties clause/signature blocks. Preserve legal names, roles, jurisdiction and registration numbers where stated.

At minimum include `borrowers[]`. Include `lenders[]`, `agents[]`, `arrangers[]`, `guarantors[]`, `obligors[]`, `security_parties[]` and `other_parties[]` where present.

### `core.facility`

Capture:

- stable `facility_id`, usually `main` for a single unnamed facility;
- facility type;
- currency;
- commitment amount in the facility currency;
- purpose and purpose restrictions;
- status/seniority/commitment status if stated.

### `core.legal`

Capture governing law and jurisdiction/court provisions. Prefer legal phrasing such as `South African law` or `New South Wales law`, not just country/place names, unless the document itself uses the country-only form.

## Optional block selection

Use optional blocks only when supported by the document. Important blocks include:

- `interest_terms`
- `availability_and_utilisation`
- `repayment_and_maturity`
- `payments_and_settlement`
- `security_and_guarantees`
- `collateral_perfection`
- `conditions_precedent`
- `covenants_and_undertakings`
- `covenant_calculation_definitions`
- `events_of_default`
- `prepayment_and_cancellation`
- `transfers_and_assignments`
- `notice_mechanics`
- `fees_and_expenses`
- `public_sector_terms`
- `term_sheet_terms`
- `amendment_overlay`
- `tax_and_withholding`
- `compliance_kyc_aml_sanctions`
- `regulatory_and_consents`
- `reporting_and_information`
- `operational_servicing_calendar`
- `clause_and_schedule_references`

Do not invent optional blocks just because the schema supports them.

## High-level gotchas

### Preserve qualifiers and carve-outs

Do not compress away meaningful exclusions, attributions or materiality qualifiers.

Bad:

```json
"purpose": "working capital and lender costs"
```

Better:

```json
"purpose": "Short-term working capital funding for ordinary-course business expenditures and lender costs associated with preparation of the Facility and associated securities."
```

### Absence is not false

Do not set booleans to `false` merely because a provision is absent. Use `false` only when the document clearly excludes the feature.

### Preserve defined-term aliases

If the document says `Elsburg Gold Mining Joint Venture (Elsburg JV)`, include the alias. Downstream legal users care about defined terms.

### Use facility currency

Record commitments in the facility's own currency. If a document also gives a base-currency cap/equivalent, keep it separate rather than replacing the facility-currency amount.

### Keep legal concepts distinct

Do not confuse:

- Event of Default vs mandatory prepayment trigger;
- security package vs collateral perfection steps;
- lender vs arranger vs agent vs security trustee;
- amendment delta vs standalone facility term;
- reference rate benchmark vs compounding mechanism.

### Clause references should include titles

Prefer `Schedule 3 (Conditions Precedent To Initial Utilisation)` over just `Schedule 3` when the title is available.

### Exact quotes only

If you populate `source_refs[].quote`, use a short exact snippet copied from the extracted source text. Do not use `...` or `…` to stitch distant words together. If support requires multiple snippets, create multiple `source_refs`; if you need to summarise, put the summary in the field value or description, not in `quote`.

### Per-request limits are not outstanding limits

Do not confuse limits such as “only one Loan may be requested in each Utilisation Request” with limits on loans outstanding. Populate `max_loans_outstanding` only when the source actually limits concurrent/outstanding loans.

### Transfer clauses deserve their own block

If the document contains assignment, transfer, novation, participation or lender-substitution mechanics, use `optional_blocks.transfers_and_assignments`. Do not leave them only in generic clause references.

### Negative pledge is not security collateral

A restriction on creating security, asset disposals, or negative pledge provisions does not itself make the facility secured and should not be entered as collateral assets. Use `negative_pledge`/undertaking fields for restrictions, and reserve `assets`/`perfection_steps` for actual security packages.

### Interest labels should be specific

Prefer canonical specific rates such as `SONIA`, `SOFR`, `EURIBOR`, `BBSW`, `Prime rate` where identifiable. Use generic RFR terms for mechanics, not as a substitute for the underlying benchmark.

## PDF text extraction guardrail

When the source is a PDF, call `extract_pdf_text` before extracting. If it returns little/no readable text, or only raw PDF internals, stop and report that the PDF is not text-extractable with the available tools. Do not infer parties, amounts or clauses from the filename, metadata, schema examples or prior extractions.

For long PDFs, write the full extracted text to a `.txt` sidecar with `output_path` and read page ranges from that sidecar as needed. Preserve page markers such as `===== PAGE 3 =====` in source references where useful.

For `pdf_direct` or `hybrid` extraction from a `.pdf`, `source_trace` should include:

```json
{
  "source_document": "docs/example.pdf",
  "source_text_path": "data/example.json.source.txt",
  "source_text_char_count": 12345,
  "extraction_method": "pdf_direct"
}
```

Validation now fails PDF-direct/hybrid extractions that omit `source_text_path`.

## Things validation cannot easily catch

Python validation only sees the JSON. It cannot reliably prove:

- that a value is faithful to the PDF;
- that no qualifier, carve-out or alias was omitted;
- that a plausible clause reference points to the right clause;
- that a summary captures all legal nuance;
- that an optional block was omitted because the document was silent rather than because the extractor missed it;
- that a source quote or source reference is genuinely correct, unless source-aware validation is added later.

For these, rely on direct close reading and source references.

## Source references

Use `source_refs` for material fields and optional blocks where practical:

```json
"source_refs": [
  {
    "location_type": "clause",
    "reference": "Clause 10",
    "title": "Termination",
    "quote": "short exact quote supporting the field"
  }
]
```

Prioritise source references for parties, facility amount/currency, purpose, interest, maturity/termination, governing law, security, CPs, EoDs, covenants, transfer restrictions and ambiguous extraction choices.

## Final checklist

Before finalising:

- Is this truly facility-level?
- Did you extract directly from the source document?
- If the source was a PDF, did you use `extract_pdf_text` and avoid raw `%PDF` content?
- If extraction was `pdf_direct`/`hybrid`, did `source_trace.source_text_path` point to the extracted text sidecar?
- Are all populated `source_refs[].quote` values exact snippets with no ellipses?
- Are `$schema`, `schema_version`, `document_level` and `core` present?
- Are borrower, finance party, facility economics and governing law captured?
- Are optional blocks source-supported rather than invented?
- Are qualifiers, aliases, carve-outs and clause titles preserved?
- Did `validate_extraction` run?
- Are all `FAIL`, `ERROR` and `NORUN` results fixed?
- Are remaining `WARN` results either fixed or explicitly noted?
