# SettleSense Documentation Plan

## Required Markdown Files

These files are sufficient to organize and build the MVP.

| File | Purpose | When to create |
|---|---|---|
| `README.md` | Explains the product, problem, setup, architecture, demo, and limitations. | Day 1 and update daily. |
| `TASK.md` | Tracks the complete implementation backlog and acceptance criteria. | Already created; use throughout the build. |
| `MILESTONES.md` | Tracks the day-by-day schedule and definition of done. | Already created; update progress daily. |
| `docs/assumptions.md` | Records fee, tax, date-window, amount-tolerance, settlement-cycle, and synthetic-data assumptions. | Day 1. |
| `docs/data-dictionary.md` | Defines every field in the settlement, bank, order, match, exception, and audit tables. | Day 1. |
| `docs/architecture.md` | Describes source adapters, normalization, matching engine, AI explanation layer, review queue, and report generation. | Day 1–2. |
| `docs/metric-definitions.md` | Defines precision, recall, match rate, throughput, exception rate, reviewer time, and amount variance. | Day 1–2. |
| `docs/exception-taxonomy.md` | Lists every exception type, detection rule, explanation, and required action. | Day 2–3. |
| `docs/api-contract.md` | Documents backend endpoints, request/response formats, error states, and run lifecycle. | Day 3–4. |
| `docs/matching-rules.md` | Documents exact matching, tolerance matching, candidate generation, confidence bands, and aggregate matching. | Day 3. |
| `docs/ai-guardrails.md` | Defines what the AI may do, what it must never do, structured output, abstention, and evidence citation rules. | Day 4. |
| `docs/audit-log-spec.md` | Defines the append-only audit event structure and traceability requirements. | Day 4. |
| `docs/test-plan.md` | Documents unit, integration, failure, security, and evaluation tests. | Day 4–6. |
| `docs/demo-script.md` | Provides the exact five-minute Buildathon demonstration sequence. | Day 6–7. |
| `docs/limitations.md` | Discloses Test Mode limits, synthetic-data boundaries, unsupported API operations, and future work. | Day 7. |

## Recommended Repository Layout

```text
settlesense/
├── README.md
├── TASK.md
├── MILESTONES.md
├── DOCUMENTATION_PLAN.md
├── .env.example
├── docs/
│   ├── assumptions.md
│   ├── data-dictionary.md
│   ├── architecture.md
│   ├── metric-definitions.md
│   ├── exception-taxonomy.md
│   ├── api-contract.md
│   ├── matching-rules.md
│   ├── ai-guardrails.md
│   ├── audit-log-spec.md
│   ├── test-plan.md
│   ├── demo-script.md
│   └── limitations.md
├── data/
│   ├── README.md
│   ├── fixtures/README.md
│   └── evaluation/README.md
├── backend/
│   └── README.md
├── frontend/
│   └── README.md
└── diagrams/
    ├── README.md
    └── architecture.mmd
```

## `README.md` Required Sections

The root README should include the following sections:

1. Project title and one-line pitch.
2. Problem statement.
3. Product workflow.
4. Features.
5. Architecture diagram.
6. Technology stack.
7. Quick-start instructions.
8. Environment variables.
9. Synthetic dataset generation.
10. Reconciliation execution command.
11. Evaluation command.
12. Metrics and sample results.
13. Screenshots or demo link.
14. Razorpay Test Mode integration details.
15. AI responsibilities and guardrails.
16. Known limitations.
17. Security disclosure.
18. Buildathon submission information.

## `docs/assumptions.md` Required Sections

Document that settlement dates, bank value dates, fee rules, tax rules, refund behavior, currency, amount tolerance, date tolerance, and synthetic identifiers are demo assumptions. Every assumption should have an owner, version, and reason.

Example:

```markdown
| Assumption | Value | Version | Reason |
|---|---:|---|---|
| Currency | INR | v1 | Buildathon demo scope |
| Date tolerance | 2 calendar days | v1 | Settlement timing simulation |
| Amount tolerance | ₹1.00 | v1 | Rounding tolerance |
| Auto-match threshold | 0.90 | v1 | High-confidence-only policy |
```

## `docs/data-dictionary.md` Required Tables

Define fields for:

- Internal order ledger.
- Razorpay settlement reconciliation record.
- Bank statement record.
- Payment and refund record.
- Match decision.
- Exception.
- Audit event.
- Reconciliation run.

Each field needs a name, type, required status, source, example, and privacy classification.

## `docs/architecture.md` Required Sections

Explain the flow:

```text
Source files or Razorpay adapter
        ↓
Raw data storage
        ↓
Normalization and validation
        ↓
Deterministic matching pipeline
        ↓
Confidence scoring
        ↓
AI exception explanation
        ↓
Human review queue
        ↓
Audit report and metrics
```

Also document failure handling, idempotency, API retries, webhook processing, database tables, and how the system behaves when the AI provider is unavailable.

## `docs/metric-definitions.md` Required Metrics

Define formulas for:

- Auto-match precision.
- Auto-match recall.
- Overall match rate.
- Candidate-match rate.
- Exception rate.
- Throughput.
- Amount variance.
- Reviewer resolution time.
- Duplicate-detection precision.
- AI explanation grounding accuracy.

The document must state the evaluation-set size and how the ground truth was produced independently of the matcher.

## `docs/exception-taxonomy.md` Required Fields

For each exception, document:

| Field | Description |
|---|---|
| Exception code | Stable identifier such as `AMOUNT_MISMATCH`. |
| Trigger | Deterministic condition that creates it. |
| Evidence | Source rows and fields used. |
| Severity | Low, medium, high, or critical. |
| Automatic action | Match, review, or unresolved. |
| Human action | Approve, reject, split, or request data. |
| Audit requirement | Event that must be recorded. |

## `docs/api-contract.md` Required Endpoints

Recommended MVP endpoints:

```text
POST   /api/runs
GET    /api/runs/{run_id}
POST   /api/runs/{run_id}/sources
POST   /api/runs/{run_id}/execute
GET    /api/runs/{run_id}/summary
GET    /api/runs/{run_id}/matches
GET    /api/runs/{run_id}/exceptions
POST   /api/exceptions/{exception_id}/resolve
GET    /api/runs/{run_id}/audit
GET    /api/runs/{run_id}/report
```

Each endpoint should document authentication, request schema, response schema, error codes, and idempotency behavior.

## `docs/matching-rules.md` Required Sections

Document the matching order:

1. Payment ID plus amount.
2. Order ID plus amount.
3. UTR plus amount.
4. Stable internal reference plus amount.
5. Date and amount tolerance.
6. Candidate generation from normalized narration and batch context.
7. Confidence band and human-review decision.
8. One-to-many and many-to-one aggregation rules.

Explicitly state that conflicting identifiers and unexplained ambiguity must never be force-matched.

## `docs/ai-guardrails.md` Required Sections

The AI may classify exceptions, summarize evidence, suggest next steps, and answer grounded questions. The AI may not change amounts, invent records, override confidence thresholds, force-match records, or mark exceptions resolved without a valid rule or reviewer decision.

Include the structured output schema and an AI-unavailable fallback.

## `docs/audit-log-spec.md` Required Fields

Every event should contain:

```json
{
  "timestamp": "ISO-8601",
  "run_id": "run_id",
  "actor": "matcher|ai|reviewer|system",
  "step": "step_name",
  "source_record_ids": [],
  "rules_version": "v1.0",
  "model_version": "none-or-version",
  "confidence": 0.94,
  "decision": "auto_matched|review|unresolved|resolved",
  "evidence": [],
  "human_gate": false,
  "outcome": "description"
}
```

## `docs/test-plan.md` Required Sections

Include unit tests, integration tests, data-quality tests, failure tests, security tests, evaluation tests, and clean-environment setup tests. The minimum failure scenarios are missing UTR, amount conflict, duplicate bank record, missing order, ambiguous candidates, AI timeout, invalid AI JSON, and repeated event processing.

## `docs/demo-script.md` Required Sections

The demo should run in five parts:

1. Upload or select the three data sources.
2. Run reconciliation on 100+ records.
3. Show summary metrics.
4. Inspect a clean match and a financial exception.
5. Resolve an ambiguous exception and export the audit report.

The demo must show that the system refuses to force-match an unexplained record.

## `docs/limitations.md` Required Disclosures

State that Test Mode and synthetic data are used, that fee/tax/settlement-cycle assumptions are configurable demo assumptions, that unsupported production behavior is not claimed, and that the output is an operational control report rather than a tax filing, accounting posting, or legal opinion.

## Build Order

Create the files in this order:

1. `README.md`
2. `docs/assumptions.md`
3. `docs/data-dictionary.md`
4. `docs/metric-definitions.md`
5. `docs/architecture.md`
6. `docs/exception-taxonomy.md`
7. `docs/matching-rules.md`
8. `docs/api-contract.md`
9. `docs/ai-guardrails.md`
10. `docs/audit-log-spec.md`
11. `docs/test-plan.md`
12. `docs/demo-script.md`
13. `docs/limitations.md`

Do not wait until the end to write documentation. The first eight documents define the system and prevent scope drift; the last five documents make the product reproducible and submission-ready.
