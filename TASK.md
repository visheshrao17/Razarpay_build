# Multi-Source Settlement Reconciliation Agent

## Project Goal

Build an AI-assisted finance operations system that reconciles Razorpay settlement data against a bank statement and an internal order ledger. The system must process at least **100 synthetic settlement records**, automatically match records where evidence is sufficient, classify unresolved exceptions, explain every decision using source-linked evidence, and generate an audit-ready close report.

The project is intended for **Razorpay AI Buildathon — Track 4: AI Finance Controller**. The official track requires closing one finance-operations loop across a batch of 50 or more synthetic records and reporting throughput, measured accuracy, match rate, and unresolved exceptions. [1]

## Product Name

**SettleSense**

### One-line pitch

> SettleSense explains where every rupee went by reconciling Razorpay settlements, bank credits, and internal orders while refusing to force-match unexplained differences.

## Primary User

The primary user is a merchant finance operator or controller who needs to close a settlement period and understand differences between the internal order ledger, Razorpay settlement reconciliation report, and bank statement.

## Core Outcome

At the end of a successful run, the user must be able to answer:

1. Which internal orders were paid?
2. Which orders were included in a Razorpay settlement?
3. Which bank credit corresponds to each settlement?
4. How did gross order value become net settlement value?
5. Which fees, taxes, refunds, disputes, timing differences, duplicates, or missing records explain the difference?
6. Which records remain unresolved and require human review?

## Scope Definition

### In scope

- Razorpay settlement records.
- Razorpay settlement reconciliation fields such as settlement ID, UTR, amount, fee, tax, order ID, payment ID, method, and dates where available. [2]
- Internal order ledger.
- Bank statement records.
- Payment and refund cross-references.
- Exact, tolerance-based, and controlled fuzzy matching.
- AI-assisted exception classification and evidence-grounded explanations.
- Confidence bands and human review queue.
- Batch-level evaluation on 100–200 synthetic records.
- Audit log and signed close report.
- Razorpay Test Mode or a clearly separated Razorpay data adapter.

### Out of scope

- Automatic accounting posting to a production ERP.
- Tax filing or legal/tax advice.
- Live-money operations.
- Automatic force-matching of low-confidence records.
- A generic finance chatbot without reconciliation logic.
- Full multi-tenant enterprise permissions.
- Complex machine-learning models that cannot be explained within the hackathon timeframe.

## Verified Platform Constraints

Razorpay documents settlement APIs for fetching settlements and settlement reconciliation details. The official API documentation also lists payments, orders, refunds, invoices, subscriptions, and other financial resources. [2]

Razorpay’s webhook documentation describes asynchronous notifications for payment and settlement-related events. Test Mode webhooks receive test transactions, and critical flows may require API verification in addition to webhook processing. [3]

The project must use Test Mode or synthetic data. Never put live API keys in the repository. Any limitation of Test Mode must be written in the README and stated in the demo.

## Recommended Technology Stack

| Layer | Recommended choice | Responsibility |
|---|---|---|
| Frontend | React + TypeScript + Tailwind CSS | Upload, reconciliation run, exception queue, audit report, metrics. |
| Backend | FastAPI + Python | Data ingestion, matching, metrics, AI orchestration, APIs. |
| Database | PostgreSQL | Source records, matches, exceptions, audit events, runs. |
| Data processing | pandas or Polars | Normalization, joins, aggregations, report generation. |
| Matching | Python rules plus rapidfuzz | Exact matching, tolerances, controlled fuzzy matching. |
| AI | Structured-output LLM | Exception classification and evidence-grounded explanation only. |
| File storage | Local storage for MVP or S3-compatible bucket | Uploaded CSVs and generated reports. |
| Authentication | Simple demo login or no auth for local MVP | Keep scope small. |
| Deployment | Public HTTPS host | Needed if webhooks are demonstrated; Razorpay webhook URLs require ports 80 or 443. [3] |
| Testing | pytest + seeded fixtures | Unit, integration, property, and evaluation tests. |

## High-Level Architecture

```text
Razorpay Settlement/Reconciliation Data
                 |
Bank Statement + Internal Order Ledger
                 |
          Source Adapters
                 |
       Raw Data Store + Run ID
                 |
       Normalization and Validation
                 |
           Matching Pipeline
      /          |             \
Exact Match  Tolerance Match  Fuzzy Candidate Match
      \          |             /
             Match Scoring
                 |
       Exception Classification
                 |
   AI Explanation + Evidence Retrieval
                 |
       Human Review and Resolution
                 |
     Reconciliation Report + Audit Log
```

## Suggested Repository Structure

```text
settlesense/
├── README.md
├── .env.example
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── api/
│   │   ├── services/
│   │   │   ├── ingestion.py
│   │   │   ├── normalization.py
│   │   │   ├── matching.py
│   │   │   ├── exceptions.py
│   │   │   ├── explanations.py
│   │   │   ├── reconciliation.py
│   │   │   └── audit.py
│   │   └── adapters/
│   │       ├── razorpay.py
│   │       └── synthetic.py
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── api/
├── data/
│   ├── raw/
│   ├── generated/
│   ├── fixtures/
│   └── evaluation/
├── scripts/
│   ├── generate_dataset.py
│   ├── run_reconciliation.py
│   ├── evaluate.py
│   └── create_demo_report.py
├── docs/
│   ├── architecture.md
│   ├── assumptions.md
│   ├── metric-definitions.md
│   └── threat-model.md
└── diagrams/
    └── architecture.mmd
```

## Data Model

### Common identifiers

Every source record must have a stable `source_system`, `source_record_id`, `created_at`, `amount`, `currency`, and `run_id`. Never match on a display label alone.

### Internal order ledger

| Field | Type | Description |
|---|---|---|
| `internal_order_id` | string | Merchant’s internal order identifier. |
| `razorpay_order_id` | string | Razorpay order reference when available. |
| `razorpay_payment_id` | string | Payment reference when available. |
| `order_date` | datetime | Order creation or payment date. |
| `gross_amount` | decimal | Original customer amount. |
| `refund_amount` | decimal | Refunds associated with the order. |
| `expected_net_amount` | decimal | Expected amount after configured assumptions. |
| `customer_reference` | string | Sanitized customer or invoice reference. |
| `status` | enum | Paid, refunded, partially refunded, disputed, cancelled. |

### Razorpay settlement record

| Field | Type | Description |
|---|---|---|
| `settlement_id` | string | Settlement batch identifier. |
| `utr` | string | Bank transfer reference where available. |
| `settlement_date` | datetime | Settlement date. |
| `order_id` | string | Razorpay order reference. |
| `payment_id` | string | Razorpay payment reference. |
| `gross_amount` | decimal | Transaction amount. |
| `fee` | decimal | Fee recorded in the source report. |
| `tax` | decimal | Tax recorded in the source report. |
| `net_amount` | decimal | Net transaction or settlement amount. |
| `method` | string | Payment method. |
| `adjustment_type` | string | Refund, dispute, chargeback, fee, or other adjustment. |

### Bank statement record

| Field | Type | Description |
|---|---|---|
| `bank_entry_id` | string | Unique statement row ID. |
| `value_date` | datetime | Bank value date. |
| `utr` | string | Bank UTR. |
| `narration` | string | Sanitized bank narration. |
| `credit_amount` | decimal | Credit amount. |
| `debit_amount` | decimal | Debit amount. |
| `account_reference` | string | Sanitized account reference. |

### Match record

| Field | Type | Description |
|---|---|---|
| `match_id` | string | Unique match decision. |
| `source_a_id` | string | First source record. |
| `source_b_id` | string | Second source record. |
| `match_type` | enum | Exact, tolerance, fuzzy, one-to-many, many-to-one. |
| `confidence` | decimal | Calibrated confidence from 0 to 1. |
| `evidence` | JSON | Matching fields and values used. |
| `decision` | enum | Auto-matched, review, rejected. |
| `reviewer_id` | string | Human reviewer when applicable. |
| `reviewed_at` | datetime | Review timestamp. |

## Synthetic Dataset Requirements

Generate at least 100 settlement lines, 100 corresponding internal ledger lines, and 20–40 bank statement lines. Use deterministic seeds so the dataset can be recreated from a single command.

The data must include both clean and messy cases:

| Case type | Minimum target |
|---|---:|
| Exact settlement-to-order match | 40 |
| Exact settlement-to-bank UTR match | 15 |
| Date offset or settlement timing difference | 10 |
| Fee or tax variance | 10 |
| Partial refund | 8 |
| Duplicate statement or settlement row | 5 |
| Missing internal order | 5 |
| Missing bank credit | 5 |
| Ambiguous narration or reference | 5 |
| One-to-many or many-to-one aggregation | 5 |
| Deliberately unresolved records | 5 |

The generator must write a data dictionary and state which values are real API-shaped fields and which are demo assumptions. Do not claim that the synthetic fee, GST, TDS, or settlement-cycle rules are universal.

## Matching Pipeline

### Pass 0 — Validation

Validate required fields, currency, decimal precision, dates, duplicate source IDs, and impossible negative or zero values. Invalid records should be reported before matching.

### Pass 1 — Exact identifiers

Match using the strongest identifiers in this order:

1. `payment_id` plus amount.
2. `order_id` plus amount.
3. `utr` plus amount.
4. Stable internal reference plus amount.

An exact identifier with a conflicting amount must not be auto-matched. It should become a conflict exception.

### Pass 2 — Controlled tolerance matching

Use configured date windows and amount tolerances. The tolerance must be visible in the UI and stored in the run configuration. Do not silently modify tolerance values to increase match rate.

### Pass 3 — Candidate generation

For unmatched records, generate at most five candidates using amount, date proximity, normalized narration, reference tokens, and settlement batch. Candidate generation must be deterministic.

### Pass 4 — Confidence scoring

A recommended initial score is:

```text
score = 0.40 * identifier_evidence
      + 0.25 * amount_evidence
      + 0.20 * date_evidence
      + 0.10 * narration_evidence
      + 0.05 * batch_evidence
```

These weights are demo assumptions and must be configurable. The model should use three states:

| Confidence | Action |
|---:|---|
| ≥ 0.90 | Auto-match if no conflicts exist. |
| 0.60–0.89 | Send to human review with candidates. |
| < 0.60 | Leave unresolved; do not force-match. |

### Pass 5 — Aggregate matching

Support one-to-many and many-to-one only when the aggregate amount, dates, and identifiers satisfy explicit rules. Every aggregate match must show the component rows in the audit view.

## Exception Taxonomy

| Code | Exception | Required response |
|---|---|---|
| `MISSING_BANK_ENTRY` | Settlement has no corresponding bank credit. | Review timing, account, or missing statement. |
| `MISSING_ORDER` | Settlement references no internal order. | Review source ingestion or order mapping. |
| `AMOUNT_MISMATCH` | Amounts differ beyond tolerance. | Show difference and likely components. |
| `FEE_VARIANCE` | Fee differs from configured assumption or source. | Do not auto-post; flag for review. |
| `TAX_VARIANCE` | Tax line differs from assumption or source. | Show source values and assumption version. |
| `DUPLICATE` | Same source or transaction appears multiple times. | Exclude duplicate from totals until resolved. |
| `TIMING_DIFFERENCE` | Dates differ within a configured settlement window. | Mark probable match with date evidence. |
| `PARTIAL_REFUND` | Refund changes expected net value. | Link payment, refund, and settlement records. |
| `DISPUTE_ADJUSTMENT` | Dispute or adjustment affects settlement. | Show adjustment source; require review. |
| `AMBIGUOUS_MATCH` | Multiple plausible candidates exist. | Send to human review. |
| `INVALID_SOURCE` | Required or structurally valid data is missing. | Reject record from matching and report it. |

## AI Responsibilities

The AI should perform only tasks where language or contextual reasoning adds value:

- Classify the exception type from structured evidence.
- Explain the likely cause in plain language.
- Summarize which source records support the explanation.
- Suggest the next review action.
- Answer a constrained question about a reconciliation run using citations to source rows.

The AI must not:

- Invent a settlement line, payment, fee, tax, refund, or bank credit.
- Change an amount.
- Override a confidence threshold.
- Force-match a record.
- Mark an exception resolved without a reviewer or deterministic rule.
- Reveal raw secrets or unnecessary customer PII.

Use structured output such as:

```json
{
  "exception_code": "AMOUNT_MISMATCH",
  "summary": "The bank credit is lower than the expected settlement by 236.00.",
  "evidence_ids": ["settlement_0042", "bank_0018", "order_0091"],
  "possible_causes": ["fee_or_tax_difference", "partial_refund"],
  "confidence": 0.82,
  "recommended_action": "human_review",
  "unsupported_claims": []
}
```

## Audit Log

Every reconciliation decision must append an audit event containing:

```json
{
  "timestamp": "ISO-8601",
  "run_id": "run_2026_001",
  "actor": "matcher|llm|reviewer|system",
  "step": "candidate_generation|match_decision|explanation|review",
  "source_record_ids": ["..."],
  "rules_version": "v1.0",
  "model_version": "model-name-or-none",
  "confidence": 0.94,
  "decision": "auto_matched|review|unresolved|resolved",
  "evidence": [{"field": "utr", "value": "redacted-or-demo-value"}],
  "human_gate": false,
  "outcome": "..."
}
```

The UI must allow a reviewer to trace a final match back to the exact source rows and rule version that produced it.

## Metrics and Acceptance Criteria

### Required metrics

- Total records processed.
- Processing throughput in records per second or records per minute.
- Auto-match rate.
- Auto-match precision on labelled ground truth.
- Auto-match recall on labelled ground truth.
- Overall match rate.
- Exception count by category.
- Human-review rate.
- Reviewer resolution time.
- Amount difference remaining after reconciliation.
- Number of forced matches. Target: zero.

### Minimum acceptance criteria

- [ ] At least 100 settlement records are processed in one run.
- [ ] At least 50 records are evaluated against known ground truth.
- [ ] Ground-truth labels are generated independently from the matching decision.
- [ ] Auto-match precision is at least 95% on the final demo fixture.
- [ ] Auto-match recall and overall match rate are reported honestly, even if below target.
- [ ] Every unresolved record has a category and reason.
- [ ] No unexplained row is force-matched.
- [ ] Every AI explanation cites source record IDs.
- [ ] Duplicate records are detected and do not inflate totals.
- [ ] Timing differences are handled using a visible configured window.
- [ ] Fee and tax assumptions are versioned and labeled as demo assumptions.
- [ ] A signed or hash-linked close report is generated.
- [ ] The system survives a missing field, duplicate event, and ambiguous match.
- [ ] The public repository contains setup instructions and reproducible seed data.

## UI Requirements

### Reconciliation run page

The user can select source files, configure the date range, set amount and date tolerances, and start a run. The page must show the run ID and data assumptions.

### Summary page

Show total records, processed rows, match rate, auto-match precision, unresolved amount, and exceptions by category. Avoid presenting a single green “success” score without details.

### Match detail page

Show the source rows side by side, the matched fields, amount waterfall, date difference, confidence, rule version, and any AI explanation.

### Exception queue

Show unresolved and review-required items sorted by materiality and confidence. Provide actions to approve, reject, or split a match. Every manual action is recorded.

### Audit report

Export a Markdown, JSON, or CSV report containing summary metrics, assumptions, matched rows, unresolved exceptions, and audit references.

## Test Plan

### Unit tests

- Amount normalization.
- Currency validation.
- Date-window logic.
- Duplicate detection.
- Exact identifier matching.
- Tolerance matching.
- Confidence threshold behavior.
- Exception classification.
- Audit event creation.

### Integration tests

- Upload three source files and complete a run.
- Retrieve settlement data through the adapter or load a recorded fixture.
- Generate an audit report.
- Resolve an exception and verify that the report updates.

### Failure tests

- Missing UTR.
- Conflicting amount with same payment ID.
- Duplicate bank line.
- Settlement line without order.
- Multiple candidates with equal confidence.
- LLM timeout.
- Invalid structured LLM output.
- Database interruption during a run.
- Repeated webhook or event.

### Evaluation tests

Run the exact same seeded dataset against:

1. Exact-match baseline.
2. Exact-plus-tolerance matcher.
3. Final matcher with candidate scoring.

The report must show whether each additional layer improves recall without reducing precision below the acceptance threshold.

## Demo Requirements

The five-minute demo should show:

1. Upload or select three sources.
2. Start a reconciliation run over 100+ records.
3. Show the overall match rate and throughput.
4. Open one clean exact match.
5. Open one fee or tax variance and show the amount waterfall.
6. Open one ambiguous match and show that the system refuses to force-match it.
7. Resolve one exception through human review.
8. Export the audit-ready close report.

The demo must include one deliberately seeded failure. The recommended failure is an unmatched bank line with an ambiguous narration. The system should display candidate matches, explain why confidence is insufficient, and place the row in the exception queue.

## Security and Privacy Checklist

- [ ] API keys are stored only in environment variables.
- [ ] `.env` and downloaded credentials are in `.gitignore`.
- [ ] No live credentials are committed.
- [ ] Test Mode or synthetic data is used.
- [ ] Raw customer PII is minimized or replaced with synthetic IDs.
- [ ] AI prompts contain only necessary fields.
- [ ] File uploads are type-checked and size-limited.
- [ ] CSV formulas are sanitized during export.
- [ ] Webhook signatures are verified when webhooks are used.
- [ ] Logs do not contain secrets.
- [ ] Human review is required for low-confidence or financially material exceptions.

## Submission Checklist

- [ ] Public GitHub repository.
- [ ] Clear README with product pitch, problem, architecture, setup, and demo instructions.
- [ ] Five-minute pitch video.
- [ ] Architecture diagram.
- [ ] Metric definitions and evaluation script.
- [ ] Synthetic dataset generator and seed.
- [ ] Sample input files.
- [ ] Sample final reconciliation report.
- [ ] Explicit Test Mode and synthetic-data disclosure.
- [ ] List of assumptions for fee, tax, date tolerance, and settlement timing.
- [ ] Known limitations and unresolved exceptions.
- [ ] Screenshots or hosted demo link if available.

## References

[1]: https://razorpay.com/buildathon/ "Razorpay AI Buildathon — Build. Show. Get hired."

[2]: https://razorpay.com/docs/api/settlements/ "Razorpay Docs: Settlements APIs"

[3]: https://razorpay.com/docs/webhooks/ "Razorpay Docs: About Webhooks"
