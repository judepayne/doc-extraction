# doc-extraction

AI-powered extraction of commercial loan documents into structured JSON, supported by deterministic validation.

This project is built to run commercial loan extraction as a **headless Pi subprocess**: give it a PDF and an output path, let the agent extract and validate JSON, then inspect the generated artifact and validation results.

The core workflow is:

```text
commercial loan PDF
  -> headless Pi extraction run
  -> extract_pdf_text sidecar
  -> facility/deal JSON
  -> validate_extraction rules
  -> validated structured representation
```

The central design split is:

- **LLMs** do source reading, legal/commercial judgement, schema mapping and iterative repair.
- **Validation rules** catch deterministic problems: schema failures, missing core data, inconsistent economics, bad provenance, invalid commitments, and similar issues.

---
## How I built this

This is the only human written section of the README. The rest is agent generated.

This is a POC project that I built in a very AI intensive way, with the following steps.

0. [Working within the Pi coding agent (an agentic coding TUI, similar to Claude code, Codex etc)..]
1. (Ask Opus 5.7 High to) research a number of real deal and facility commercial legal agreements from across the web.
2. ( " ) to produce a facility schema by reading across the example facility docs, and same for deal.
3. (Ask gpt-5.5 xHigh) to attempt to extract from one facility doc into the schema, then manually metriculously compare output vs document.
4. ( " ) With the lessons learned, decide what rule should best be a hard validation rule vs skill and formulate as validation rules or in the facility skill
5. (with ") Keep iterating across other example docs tweaking the schema (keeping it generic) and building up additonal validation rules and deepening the skill
6. Same process for the Deal side
7. In the process of doing this, wrote a tool wrapper to my existing validation-lib (python). The form of this is a Pi 'extension' and makes it easy for any Pi agent to call. I also found that the agent needed a way to get text from the pdf, so wrote that as well. I say 'wrote', but of course the agent wrote both wrappers.

> Note: It was a non-goal to start from paper document scans e.g. images.

> Note: the pdf tool could be a source of inaccuracy in the overall conversion process. Needs careful testing.

Now switch to a headless agent run. Pi is an agentic framework (Openclaw is built on top of) similarly to Langchain but less clunky/ heavyweight to work this.
I knew that with Pi you can fire off a 'one shot agent' with a simple command line call. I wanted to have the doc extraction agent be a command line tool, as gives us the greatest flexibility of deployment. The below call can easily be replicated in code working with the Pi framework (which is Typescript, so javascript easy).

You'll find the command line call documentated and explained below.
I had the TUI agent build up and run the command on different docs several times, inspect the output and fix any issues. This formed the basis of further iterations to find tune both the skill and the validation rules. Did the same thing for the Deal.

> Note: the schemas that were built up have not been human inspected, but are based on a core set of fields and then optional blocks addressing different concerns, e.g. collateral block.

Total time for POC project: 2.5 years
Tokens used: ~600-800k
Equivalent api cost: ~ $80. (but I don't use Opus, Gpt api. Have subscriptions instead).


---
## Quickstart: run a headless extraction

### 1. Install system dependencies

You need Node/npm, Python, Git and GitHub/Pi credentials.

```bash
node --version
npm --version
python3 --version
git --version
```

Install Pi:

```bash
npm install -g @mariozechner/pi-coding-agent
```

Authenticate Pi with a supported provider. For the examples below, Pi must be able to use:

```text
openai-codex/gpt-5.5
```

For example, set the relevant API key or authenticate interactively:

```bash
export OPENAI_API_KEY=...
# or start pi once and use /login if your provider supports it
pi
```

### 2. Clone this project

```bash
git clone https://github.com/judepayne/doc-extraction.git
cd doc-extraction
```

### 3. Install Python dependencies

A virtual environment is recommended:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e .
```

This installs:

- `pypdf` for PDF text extraction;
- the pinned `validation-lib` engine dependency;
- validation runtime dependencies such as `jsonschema`, `pyyaml`, and `requests`.

### 4. Run a deal extraction headlessly

This command runs Pi as a subprocess in JSONL mode. The child agent has no `bash` tool; it reads PDFs through `extract_pdf_text`, writes JSON, and validates through `validate_extraction`.

```bash
mkdir -p .pi/headless-runs .pi/headless-sessions

nohup pi \
  --mode json \
  --model openai-codex/gpt-5.5 \
  --thinking medium \
  --session-dir .pi/headless-sessions \
  --no-extensions \
  --extension ./extensions/validation/index.ts \
  --extension ./extensions/pdf/index.ts \
  --no-skills \
  --skill ./skills/deal-json-extraction \
  --no-prompt-templates \
  --prompt-template .pi/prompts/extract-deal.md \
  --tools read,edit,write,grep,find,ls,extract_pdf_text,validate_extraction \
  "/extract-deal docs/07_deal_ultra_group_senior_facilities.pdf data/07_deal_ultra_group_senior_facilities.json" \
  > .pi/headless-runs/extract-07-deal.jsonl \
  2> .pi/headless-runs/extract-07-deal.stderr &

echo $! > .pi/headless-runs/extract-07-deal.pid
```

What this does:

- loads only the two project extensions needed for extraction;
- loads only the deal extraction skill;
- loads the parameterized prompt template `.pi/prompts/extract-deal.md`;
- asks the agent to extract `docs/07_deal_ultra_group_senior_facilities.pdf` into `data/07_deal_ultra_group_senior_facilities.json`;
- writes the full Pi JSONL event stream to `.pi/headless-runs/extract-07-deal.jsonl`;
- writes process stderr to `.pi/headless-runs/extract-07-deal.stderr`;
- stores the background process id in `.pi/headless-runs/extract-07-deal.pid`.

### 5. Monitor the run

Check whether the process is still running:

```bash
ps -p "$(cat .pi/headless-runs/extract-07-deal.pid)" -o pid,etime,stat,command
```

Watch process-level errors:

```bash
tail -f .pi/headless-runs/extract-07-deal.stderr
```

Watch high-level tool activity from the JSONL stream:

```bash
tail -f .pi/headless-runs/extract-07-deal.jsonl \
  | grep --line-buffered -E '"tool_execution_start"|"tool_execution_end"|"agent_end"'
```

The JSONL log can be large for long agreements. It is ignored by Git.

### 6. Check that JSON was produced

After the process exits, check the expected files:

```bash
ls -lh \
  data/07_deal_ultra_group_senior_facilities.json \
  data/07_deal_ultra_group_senior_facilities.json.source.txt
```

The `.source.txt` sidecar is the text extracted from the PDF. The JSON should record it in `source_trace.source_text_path` and pass validation.

Validate manually:

```bash
python3 tools/validate_extraction.py \
  --entity deal \
  data/07_deal_ultra_group_senior_facilities.json
```

You should see JSON rule results. Any `FAIL`, `ERROR`, or `NORUN` means the extraction needs repair. `WARN` means review is needed.

Check JSON syntax/shape quickly:

```bash
python3 -m json.tool data/07_deal_ultra_group_senior_facilities.json >/tmp/deal.json
```

### 7. Facility extraction variant

Use the facility prompt template and facility skill:

```bash
mkdir -p .pi/headless-runs .pi/headless-sessions

nohup pi \
  --mode json \
  --model openai-codex/gpt-5.5 \
  --thinking medium \
  --session-dir .pi/headless-sessions \
  --no-extensions \
  --extension ./extensions/validation/index.ts \
  --extension ./extensions/pdf/index.ts \
  --no-skills \
  --skill ./skills/facility-json-extraction \
  --no-prompt-templates \
  --prompt-template .pi/prompts/extract-facility.md \
  --tools read,edit,write,grep,find,ls,extract_pdf_text,validate_extraction \
  "/extract-facility docs/04_facility_uk_gov_dft_facility_agreement.pdf data/04_facility_uk_gov_dft_facility_agreement.json" \
  > .pi/headless-runs/extract-04-facility.jsonl \
  2> .pi/headless-runs/extract-04-facility.stderr &

echo $! > .pi/headless-runs/extract-04-facility.pid
```

---

## Repository layout

```text
doc-extraction/
├── docs/                         # Source loan PDFs
├── data/                         # Extracted JSON instances and selected source text sidecars
├── validation/
│   ├── business-config.yaml      # Local ruleset/schema/helper wiring
│   ├── models/                   # Facility/deal JSON Schemas
│   ├── entity_helpers/           # Logical-field mappings for validation rules
│   ├── rules/                    # Python validation rules
│   └── schema_helpers/           # Schema loading helpers
├── skills/
│   ├── facility-json-extraction/ # Pi skill for facility extraction
│   └── deal-json-extraction/     # Pi skill for deal extraction
├── extensions/
│   ├── pdf/                      # Pi extension registering extract_pdf_text
│   └── validation/               # Pi extension registering validate_extraction
├── tools/
│   ├── extract_pdf_text.py       # Python PDF text helper used by the extension
│   └── validate_extraction.py    # Python validation wrapper used by the extension
├── .pi/
│   ├── prompts/                  # Headless prompt templates
│   └── settings.json             # Optional Pi project settings for interactive use
├── pyproject.toml
└── README.md
```

---

## Headless prompt templates

Prompt templates provide the stable subprocess interface.

### Deal

```text
/extract-deal <input-pdf> <output-json>
```

Template file:

```text
.pi/prompts/extract-deal.md
```

### Facility

```text
/extract-facility <input-pdf> <output-json>
```

Template file:

```text
.pi/prompts/extract-facility.md
```

Both templates instruct the agent to:

- use the relevant extraction skill;
- call `extract_pdf_text` before reading PDF content;
- write a full source text sidecar at `<output-json>.source.txt`;
- populate `source_trace.source_text_path` and `source_trace.source_text_char_count`;
- write schema-conformant JSON;
- run `validate_extraction`;
- iterate until there are no `FAIL`, `ERROR`, or `NORUN` validation results.

---

## Pi tools exposed by extensions

### `extract_pdf_text`

Registered by:

```text
extensions/pdf/index.ts
```

It extracts readable text from a PDF using `tools/extract_pdf_text.py` and `pypdf`.

Typical parameters:

```json
{
  "pdf_path": "docs/04_facility_uk_gov_dft_facility_agreement.pdf",
  "output_path": "data/04_facility_uk_gov_dft_facility_agreement.json.source.txt",
  "max_chars": 50000
}
```

If a PDF produces little/no readable text, the extractor should stop rather than infer content from filenames, schema examples, metadata, or prior samples.

### `validate_extraction`

Registered by:

```text
extensions/validation/index.ts
```

Typical parameters:

```json
{
  "entity": "deal",
  "json_path": "data/07_deal_ultra_group_senior_facilities.json"
}
```

or:

```json
{
  "entity": "facility",
  "json_path": "data/04_facility_uk_gov_dft_facility_agreement.json"
}
```

The extension calls `tools/validate_extraction.py`, which uses `validation-lib` with this repository's local validation logic.

---

## Schemas

Canonical schemas live in:

```text
validation/models/facility.schema.v1.0.0.json
validation/models/deal.schema.v1.0.0.json
```

Facility JSON must include:

```json
"$schema": "https://raw.githubusercontent.com/judepayne/doc-extraction/main/validation/models/facility.schema.v1.0.0.json",
"schema_version": "1.0.0",
"document_level": "facility"
```

Deal JSON must include:

```json
"$schema": "https://raw.githubusercontent.com/judepayne/doc-extraction/main/validation/models/deal.schema.v1.0.0.json",
"schema_version": "1.0.0",
"document_level": "deal"
```

The schema URL selects the helper mapping and ruleset in `validation/business-config.yaml`.

---

## Validation rules

Validation runs schema conformance first. Business rules run as child rules only if schema validation passes.

### Facility rules

| Rule | Purpose |
|---|---|
| `rule_facility_001_v1` | JSON Schema conformance |
| `rule_facility_002_v1` | Core business completeness |
| `rule_facility_003_v1` | Document subtype consistency |
| `rule_facility_004_v1` | Interest terms consistency |
| `rule_facility_005_v1` | Date and maturity sanity |
| `rule_facility_006_v1` | Security and guarantee consistency |
| `rule_facility_007_v1` | Conditions precedent / regulatory / security consistency |
| `rule_facility_008_v1` | Provenance and source trace |
| `rule_facility_009_v1` | Source quote quality |
| `rule_facility_010_v1` | PDF source text provenance |

### Deal rules

| Rule | Purpose |
|---|---|
| `rule_deal_001_v1` | JSON Schema conformance |
| `rule_deal_002_v1` | Core business completeness |
| `rule_deal_003_v1` | Facility portfolio consistency |
| `rule_deal_004_v1` | Lender commitment reconciliation |
| `rule_deal_005_v1` | Facility economics and date sanity |
| `rule_deal_006_v1` | Security / intercreditor / collateral consistency |
| `rule_deal_007_v1` | Voting / amendment / transfer mechanics consistency |
| `rule_deal_008_v1` | Provenance and source trace |
| `rule_deal_009_v1` | Source quote quality |
| `rule_deal_010_v1` | PDF source text provenance |

Current sample extractions:

```text
data/04_facility_uk_gov_dft_facility_agreement.json
data/07_deal_ultra_group_senior_facilities.json
data/09_facility_term_sheet_loan_facility_sec.json
```

---

## What belongs in extraction skill vs validation rule

### Skills are for judgement

Skills tell the agent how to read the document and make extraction decisions:

- classify facility vs deal;
- identify parties and legal roles;
- preserve qualifiers, carve-outs, aliases and defined terms;
- choose optional blocks;
- avoid over-inference;
- use exact source snippets;
- validate and iterate.

### Rules are for deterministic checks

Rules should check objective properties of completed JSON:

- schema conformance;
- required core fields;
- positive amounts;
- unique facility IDs;
- lender commitment reconciliation;
- date ordering;
- interest consistency;
- security/guarantee contradictions;
- provenance and source text sidecar presence;
- quote-quality guardrails.

Validation cannot fully prove that the JSON is faithful to the PDF. Human/legal review remains necessary for high-value or production use.

---

## Optional interactive Pi usage

The headless mode above is the preferred workflow. You can also run Pi interactively from the project root:

```bash
pi
```

Pi can discover project resources from `.pi/settings.json`, or you can explicitly use the same skills/tools as the headless command. If Pi is already open after changing extensions, prompts or skills, run:

```text
/reload
```

Interactive example:

```text
/extract-facility docs/04_facility_uk_gov_dft_facility_agreement.pdf data/04_facility_uk_gov_dft_facility_agreement.json
```

---

## Development commands

Validate the deal sample:

```bash
python3 tools/validate_extraction.py --entity deal data/07_deal_ultra_group_senior_facilities.json
```

Validate the facility sample:

```bash
python3 tools/validate_extraction.py --entity facility data/04_facility_uk_gov_dft_facility_agreement.json
```

Compile/check Python syntax:

```bash
python3 -m compileall tools validation/rules validation/entity_helpers validation/schema_helpers
find validation tools -type d -name __pycache__ -prune -exec rm -rf {} +
```

Check JSON/YAML/TOML syntax:

```bash
python3 - <<'PY'
import json, tomllib, yaml
from pathlib import Path
for path in Path('validation').rglob('*.json'):
    json.loads(path.read_text())
for path in Path('data').glob('*.json'):
    json.loads(path.read_text())
yaml.safe_load(Path('validation/business-config.yaml').read_text())
with Path('pyproject.toml').open('rb') as f:
    tomllib.load(f)
print('OK')
PY
```

---

## Dependency philosophy

This repository owns:

- facility/deal schemas;
- facility/deal extraction skills;
- headless prompt templates;
- project-specific validation rules;
- project-specific validation config.

It depends on:

- Pi for agent execution and custom tools;
- `validation-lib` for validation engine mechanics;
- `pypdf` for text extraction from readable PDFs.

It does **not** vendor `validation-lib` or depend on a generic validation-logic repository for the facility/deal schemas and rules.

```text
doc-extraction owns the extraction domain and rules.
validation-lib owns the generic validation engine.
Pi provides the agent harness and tool surface.
```
