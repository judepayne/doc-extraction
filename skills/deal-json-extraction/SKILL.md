---
name: deal-json-extraction
description: Extracts multi-facility commercial loan deal documents directly from PDF/text into JSON conforming to validation/models/deal.schema.v1.0.0.json. Use for senior facilities agreements, syndicated facilities and other deal-level documents; validate output with the validate_extraction Pi tool.
---

# Deal JSON Extraction

Use this skill when asked to read a commercial loan **deal-level** document and produce JSON conforming to:

```text
validation/models/deal.schema.v1.0.0.json
```

The output must include:

```json
{
  "$schema": "https://raw.githubusercontent.com/judepayne/doc-extraction/main/validation/models/deal.schema.v1.0.0.json",
  "schema_version": "1.0.0",
  "document_level": "deal",
  "core": {
    "document": {},
    "deal_summary": {},
    "obligor_group": {},
    "finance_parties": {},
    "facilities": [],
    "legal": {}
  },
  "optional_blocks": {},
  "source_trace": {}
}
```

## Mission

Extract directly from the source PDF/document into schema-conformant JSON. The output should be useful to front office, syndicate, agency, operations, credit, legal, compliance and portfolio teams.

Do **not** stage through a loose intermediate blob. Prior experiments showed that blob-mediated extraction loses qualifiers, defined-term aliases, clause titles, currency distinctions and other facts that cannot be reconstructed later.

Use validation as a feedback loop, not as a substitute for reading the document.

## Hierarchy check

Use this skill for **deal-level** documents:

```text
Deal -> Facility -> Loan instrument / drawdown
```

Examples:

- senior facilities agreements with multiple facilities/tranches,
- syndicated facility agreements,
- multicurrency facilities agreements,
- leveraged/acquisition finance packages,
- common terms documents that govern multiple facilities.

If the document governs a single facility only, use the facility extraction skill. If it is an individual drawdown/utilisation/loan note, do not force it into the deal schema without user confirmation.

## Extraction workflow

1. Load `validation/models/deal.schema.v1.0.0.json`.
2. Read the source document directly. For PDFs, use the Pi `extract_pdf_text` tool first, preferably with an `output_path` text sidecar; do not rely on raw `%PDF` binary content returned by `read`.
3. If using `extract_pdf_text`, record the sidecar path in `source_trace.source_text_path` and, if known, the extracted character count in `source_trace.source_text_char_count`.
4. Confirm the document governs multiple facilities/tranches or otherwise sits at deal level.
5. Fill `core` first: document identity, deal summary, obligor group, finance parties, facilities, governing law.
6. Use document-native facility IDs such as `Facility A`, `Facility B2`, or `Original Revolving Facility`, and reuse those IDs consistently in optional blocks.
7. Extract lender commitments with `commitments_by_facility` keyed by the exact facility IDs.
8. Add only optional blocks supported by the source.
9. Preserve material details, qualifiers, carve-outs, defined-term aliases and clause/schedule titles.
10. Save the JSON.
11. Use the Pi `validate_extraction` tool with `entity: "deal"` and the JSON path.
12. Fix all `FAIL`, `ERROR` and `NORUN` results. Treat `WARN` results as review prompts; resolve them where possible or note why left unresolved.

## What validation checks

The deal ruleset currently includes these high-value checks:

1. **Schema conformance** — JSON must conform to the deal schema.
2. **Core business completeness** — obligor group, agent, facilities and governing law must be present.
3. **Facility portfolio consistency** — facility IDs must be unique; currencies and summary totals should be coherent.
4. **Lender commitment reconciliation** — lender commitments should use known facility IDs and reconcile to facility totals where data is present.
5. **Facility economics/date sanity** — margins, reference-rate fields and facility dates should be plausible.
6. **Security/intercreditor/collateral consistency** — secured/unsecured status, security agents, collateral perfection and intercreditor mechanics must not contradict each other.
7. **Voting/amendment/transfer consistency** — detailed mechanics should not be empty or internally contradictory when captured.
8. **Provenance** — source trace is required; facilities and material optional blocks should carry source references where possible.
9. **Source quote quality** — `source_refs[].quote` values must be exact short snippets, not ellipsis-compressed paraphrases.
10. **PDF text provenance** — `pdf_direct`/`hybrid` extractions from PDFs must record an extracted text sidecar path.

Validation catches malformed, missing or internally inconsistent JSON. It does **not** prove the extracted facts are correct against the PDF.

## Core extraction guidance

### `core.document`

Capture document type, title, source file and execution status. Many deal documents are titled “Facility Agreement” even though they sit at deal level because they govern multiple tranches.

### `core.deal_summary`

Capture agreement date, deal name, transaction type, total facility amount, base currency, deal currencies and purpose where stated. If multiple facility currencies are present, do not pretend the base currency is the facility currency.

### `core.obligor_group`

Preserve the document's role structure:

- `company`
- `borrower`
- `borrowers`
- `original_borrowers`
- `guarantors`
- `original_guarantors`
- `additional_obligors`
- `target_group`
- `sponsor`

Do not flatten borrower group structure into a single party string.

### `core.finance_parties`

Distinguish arrangers, mandated lead arrangers, bookrunners, underwriters, agent, facility agent, security agent/trustee, issuing banks, swingline lenders, original lenders and other finance parties. One institution may have multiple capacities.

### `core.facilities[]`

Each tranche/facility needs:

- `facility_id`, using the source document label;
- facility type;
- facility currency;
- commitment amount in that facility's currency;
- margin/reference rate/availability/termination/repayment profile where stated.

### `core.legal`

Capture governing law and jurisdiction/courts/process agent where stated. Prefer legal phrasing, e.g. `English law`, not just geography.

## Optional block selection

Use optional blocks only when supported by the document. Important blocks include:

- `transaction_context`
- `syndication_and_allocations`
- `lender_commitments`
- `lender_classes_and_voting`
- `trading_transfers_and_assignments`
- `amendments_and_waivers`
- `agency_payments_and_settlement`
- `cash_waterfalls`
- `security_and_guarantees`
- `intercreditor_and_subordination`
- `collateral_perfection_timetable`
- `financial_covenants`
- `covenant_calculation_definitions`
- `repayment_and_amortisation`
- `interest_and_benchmark_terms`
- `prepayment_and_cancellation`
- `additional_facility_and_accordion_mechanics`
- `ancillary_and_letter_of_credit`
- `conditions_precedent`
- `representations_undertakings_events`
- `tax_and_withholding`
- `tax_gross_up_and_indemnities`
- `notice_mechanics`
- `operational_servicing_calendar`
- `schedules_and_references`

Do not invent optional blocks just because the schema supports them.

## High-level gotchas

### Use facility currency, not base-currency caps

For each facility, `total_commitment` should be in that facility's own currency. Use `base_currency_equivalent` for translated caps or equivalents. If the agreement defines Base Currency separately for each facility, do not populate a single deal-level `base_currency` unless there is a true global base currency.

Bad for an NZD facility:

```json
{
  "facility_id": "Facility B2",
  "currency": "NZD",
  "total_commitment": 50000000
}
```

if `50,000,000` is an AUD cap and the NZD face amount is `30,000,000`.

Better:

```json
{
  "facility_id": "Facility B2",
  "currency": "NZD",
  "total_commitment": 30000000,
  "base_currency_equivalent": 50000000,
  "base_currency": "AUD"
}
```

### Preserve source facility IDs

Use `Facility A`, `Facility B1`, `Facility B2`, `Original Revolving Facility`, etc. Do not replace them with generic array positions. These IDs are the join keys for lender commitments, repayment profiles and interest terms.

### Preserve jurisdiction precision

For US, Canadian and Australian entities, include state/province where stated. `Delaware, USA` is materially better than `USA` when the document gives Delaware.

### Classify facility type from repayment mechanics

A term facility with interim amortisation plus a balloon is `term_loan_amortising`, not `term_loan_bullet`, even if the label is generic.

### Keep legal concepts distinct

Do not confuse:

- mandatory prepayment trigger vs Event of Default;
- amendment/waiver threshold vs voting class;
- final lender commitment vs syndication allocation/underwriting hold;
- security package vs collateral perfection timetable;
- ranking/security summary vs intercreditor enforcement mechanics;
- reference rate benchmark vs RFR compounding mechanics.

### Original lender commitments must reconcile where possible

Use `optional_blocks.lender_commitments.original_lenders[].commitments_by_facility` keyed by exact facility IDs. If the schedule gives both facility-currency commitments and base-currency equivalents, keep them separate.

### Reference rate labels should be specific

Prefer canonical specific benchmarks such as `SONIA`, `SOFR`, `EURIBOR`, `BBSW`, `BBSY`, `CDOR` where identifiable. Use generic compounded-rate language for mechanics, not as a substitute for the underlying benchmark.

### Clause/schedule references should include titles

Prefer `Schedule 1 (Original Lenders)` over just `Schedule 1` when the title is available.

### Exact quotes only

If you populate `source_refs[].quote`, use a short exact snippet copied from the extracted source text. Do not use `...` or `…` to stitch distant words together. If support requires multiple snippets, create multiple `source_refs`; if you need to summarise, put the summary in the field value or description, not in `quote`.

## PDF text extraction guardrail

When the source is a PDF, call `extract_pdf_text` before extracting. If it returns little/no readable text, or only raw PDF internals, stop and report that the PDF is not text-extractable with the available tools. Do not infer parties, amounts, facilities, lender commitments or clauses from the filename, metadata, schema examples or prior extractions.

For long PDFs, write the full extracted text to a `.txt` sidecar with `output_path` and use targeted `grep`/page-range reads from that sidecar. Preserve page markers such as `===== PAGE 3 =====` in source references where useful.

For `pdf_direct` or `hybrid` extraction from a `.pdf`, `source_trace` should include:

```json
{
  "source_document": "docs/example.pdf",
  "source_text_path": "data/example.json.source.txt",
  "source_text_char_count": 12345,
  "extraction_method": "pdf_direct"
}
```

Validation now fails PDF-direct/hybrid deal extractions that omit `source_text_path`.

## Things validation cannot easily catch

Python validation only sees the JSON. It cannot reliably prove:

- that a value is faithful to the PDF;
- that no facility, lender, qualifier, alias or carve-out was omitted;
- that a plausible clause reference points to the correct clause;
- that a security/intercreditor summary captures all legal nuance;
- that lender allocations were correctly distinguished from legal commitments unless both are represented;
- that an optional block was omitted because the document was silent rather than because the extractor missed it;
- that source quotes are genuine, unless source-aware validation is added later.

For these, rely on direct close reading and source references.

## Source references

Use `source_refs` for material fields and optional blocks where practical:

```json
"source_refs": [
  {
    "location_type": "schedule",
    "reference": "Schedule 1",
    "title": "Original Lenders",
    "quote": "short exact quote supporting the field"
  }
]
```

Prioritise source references for facility IDs, currencies, commitments, original lender commitments, obligor roles, finance-party roles, purpose, interest, repayment, security, covenants, EoDs, voting thresholds, transfer restrictions, intercreditor terms and governing law.

## Final checklist

Before finalising:

- Is this truly deal-level?
- Did you extract directly from the source document?
- If the source was a PDF, did you use `extract_pdf_text` and avoid raw `%PDF` content?
- If extraction was `pdf_direct`/`hybrid`, did `source_trace.source_text_path` point to the extracted text sidecar?
- Are all populated `source_refs[].quote` values exact snippets with no ellipses?
- Are `$schema`, `schema_version`, `document_level` and `core` present?
- Are obligor group, agent, facilities and governing law captured?
- Are facility IDs document-native and reused consistently?
- Are facility amounts in facility currency?
- Are original lender commitments keyed by facility ID?
- Are optional blocks source-supported rather than invented?
- Are qualifiers, aliases, carve-outs and clause titles preserved?
- Did `validate_extraction` run?
- Are all `FAIL`, `ERROR` and `NORUN` results fixed?
- Are remaining `WARN` results either fixed or explicitly noted?
