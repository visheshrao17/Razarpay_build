# SettleSense Phase-Wise LLM Development Plan

## Project

**SettleSense — Multi-Source Settlement Reconciliation Agent**

## Purpose of This File

This document replaces the previous day-by-day schedule. It instructs an LLM or development team to build SettleSense in controlled phases. Each phase has a clear objective, required Markdown files, implementation tasks, an LLM instruction prompt, validation gates, and a definition of done.

The project should not move to the next phase until the current phase passes its validation gate. The LLM may suggest improvements, but it must not expand the scope without approval. The central product rule is:

> **SettleSense must match records only when evidence is sufficient and must leave unexplained records unresolved.**

## Product Objective

Build a finance-operations system that reconciles Razorpay settlement data against a bank statement and an internal order ledger. The system must process 100–200 synthetic records, calculate match rate and precision/recall, classify unresolved exceptions, provide source-linked explanations, support human review, and generate an audit-ready close report.

## Complete Markdown File Set

### Core project files

| File | Required status | Purpose |
|---|---|---|
| `README.md` | Required | Public project overview, setup, architecture, demo, metrics, and limitations. |
| `TASK.md` | Required | Detailed implementation backlog and acceptance criteria. |
| `MILESTONES.md` | Required | This phase-wise execution plan. |
| `DOCUMENTATION_PLAN.md` | Recommended | Map of all project documentation and their intended contents. |
| `.env.example` | Required but not Markdown | Names the environment variables without exposing secrets. |

### Technical design files

| File | Required status | Purpose |
|---|---|---|
| `docs/assumptions.md` | Required | Fee, tax, settlement-cycle, date-window, amount-tolerance, and synthetic-data assumptions. |
| `docs/data-dictionary.md` | Required | Definitions for every source, match, exception, audit, and run field. |
| `docs/architecture.md` | Required | System components, data flow, adapters, state transitions, and failure handling. |
| `docs/metric-definitions.md` | Required | Definitions and formulas for every evaluation metric. |
| `docs/exception-taxonomy.md` | Required | Exception codes, detection conditions, evidence, severity, and actions. |
| `docs/matching-rules.md` | Required | Exact matching, tolerance matching, candidate generation, confidence, and aggregation. |
| `docs/api-contract.md` | Required | Backend endpoints, schemas, errors, run states, and idempotency. |
| `docs/ai-guardrails.md` | Required | AI responsibilities, prohibited actions, structured output, and fallbacks. |
| `docs/audit-log-spec.md` | Required | Append-only audit event schema and traceability rules. |
| `docs/test-plan.md` | Required | Unit, integration, data, failure, security, and evaluation tests. |

### Data and demonstration files

| File | Required status | Purpose |
|---|---|---|
| `data/README.md` | Recommended | Explains data folders, provenance, synthetic generation, and privacy. |
| `data/fixtures/README.md` | Recommended | Describes committed demo fixtures and seeded scenarios. |
| `data/evaluation/README.md` | Recommended | Explains ground truth, train/test separation, and evaluation commands. |
| `backend/README.md` | Optional | Backend-specific setup and development commands. |
| `frontend/README.md` | Optional | Frontend-specific setup and component conventions. |
| `diagrams/README.md` | Optional | Explains architecture and sequence diagrams. |
| `docs/demo-script.md` | Required | Five-minute Buildathon demo sequence and talking points. |
| `docs/limitations.md` | Required | Test Mode, synthetic data, accounting assumptions, and unsupported behavior. |

## Phase 0 — Project Charter and Scope Lock

### Objective

Define the product boundary before implementation begins. SettleSense is a reconciliation and exception-management product, not a generic finance chatbot, tax-filing product, or accounting ERP.

### LLM instruction

```text
Act as a senior fintech product architect. Define a narrow MVP for SettleSense, a multi-source settlement reconciliation agent. The system must reconcile Razorpay-style settlement data, a bank statement, and an internal order ledger. Define the primary user, user problem, in-scope features, out-of-scope features, success metrics, Test Mode limitations, and one compelling five-minute demo. Do not add unrelated features such as forecasting, autonomous accounting posting, or tax filing.
```

### Markdown files to create or update

- [ ] `README.md`
- [ ] `TASK.md`
- [ ] `docs/assumptions.md`
- [ ] `docs/limitations.md`

### Implementation outputs

- One-line product pitch.
- Primary user definition.
- Problem statement.
- MVP scope and non-goals.
- Buildathon track mapping.
- Test Mode and synthetic-data disclosure.
- Initial success criteria.

### Validation gate

The scope must fit in a 24–48 hour MVP. Every feature must support reconciliation, explanation, exception handling, auditability, or evaluation. Remove any feature that does not contribute to those outcomes.

### Definition of done

A reviewer can understand what SettleSense does, who uses it, what it does not do, and how success will be measured by reading only `README.md` and `TASK.md`.

## Phase 1 — Documentation Contract and Data Model

### Objective

Define the data contract before writing matching code. Every future implementation decision must map to a documented field, state, or exception.

### LLM instruction

```text
Act as a data architect for a financial reconciliation system. Design typed schemas for internal orders, Razorpay settlement reconciliation records, bank statement rows, payments, refunds, match decisions, exceptions, audit events, and reconciliation runs. Include required fields, data types, identifiers, privacy classification, example values, and relationships. Use decimal-safe money representation and ISO-8601 timestamps. Do not invent undocumented Razorpay fields; label demo-only fields explicitly.
```

### Markdown files to create or update

- [ ] `docs/data-dictionary.md`
- [ ] `docs/assumptions.md`
- [ ] `docs/exception-taxonomy.md`
- [ ] `docs/audit-log-spec.md`
- [ ] `data/README.md`
- [ ] `data/fixtures/README.md`
- [ ] `data/evaluation/README.md`

### Implementation outputs

- Database table plan.
- JSON or TypeScript schemas.
- Stable source identifiers.
- Run ID and versioning strategy.
- Exception taxonomy.
- Audit event schema.
- Privacy and synthetic-data rules.

### Validation gate

No schema may use a display label as its only identifier. Money must use safe decimal or minor-unit representation. Every exception must have a code, evidence reference, severity, and resolution state.

### Definition of done

The team can create database migrations and fixture files directly from `docs/data-dictionary.md` without making undocumented field decisions.

## Phase 2 — Synthetic Data and Ground Truth

### Objective

Create a reproducible dataset that tests both easy and difficult reconciliation cases. Ground truth must be independent from the matcher.

### LLM instruction

```text
Act as a financial data quality engineer. Generate a deterministic synthetic dataset for settlement reconciliation containing settlement lines, internal orders, bank statement entries, payments, and refunds. Include exact matches, date offsets, amount differences, fee or tax differences, partial refunds, duplicates, missing records, ambiguous narrations, one-to-many matches, many-to-one matches, and deliberately unresolved records. Create independent ground-truth relationships. Document all synthetic assumptions and do not claim that the dataset represents real Indian merchant behavior.
```

### Markdown files to create or update

- [ ] `data/README.md`
- [ ] `data/fixtures/README.md`
- [ ] `data/evaluation/README.md`
- [ ] `docs/assumptions.md`
- [ ] `docs/metric-definitions.md`

### Implementation outputs

- Deterministic dataset generator.
- At least 100 settlement records.
- At least 100 internal ledger records.
- Bank statement records with realistic timing offsets.
- Independently stored ground truth.
- Fixture cases for every exception type.
- Data-generation command documented in `README.md`.

### Validation gate

The same seed must regenerate the same dataset. The ground-truth file must not be created by calling the final matcher. Every difficult case must have an expected outcome.

### Definition of done

A clean environment can generate and inspect the complete dataset with one documented command, and the team can explain the expected match or exception for every seeded case.

## Phase 3 — Ingestion and Normalization

### Objective

Load all source types into a common internal representation while preserving raw records and source provenance.

### LLM instruction

```text
Act as a backend engineer building a reliable data-ingestion pipeline. Implement source adapters for settlement data, bank statements, internal order ledgers, payments, and refunds. Normalize dates, amounts, currencies, identifiers, and narrations without destroying raw values. Validate required fields, detect duplicates, assign a reconciliation run ID, and report invalid rows without losing valid rows. Make the pipeline deterministic and idempotent.
```

### Markdown files to create or update

- [ ] `docs/architecture.md`
- [ ] `docs/api-contract.md`
- [ ] `docs/data-dictionary.md`
- [ ] `docs/test-plan.md`
- [ ] `backend/README.md`

### Implementation outputs

- File-upload or fixture-loading endpoint.
- Raw and normalized data tables.
- Validation report.
- Source adapters.
- Run lifecycle: created, ingesting, ready, running, completed, failed.
- Duplicate source-record detection.
- Idempotent repeated ingestion.

### Validation gate

Invalid input cannot corrupt valid records. Raw values remain available for audit. A repeated upload does not duplicate source records. Every normalized row links to its source and run ID.

### Definition of done

The system can load the three primary sources, display row counts and validation errors, and produce a normalized dataset ready for matching.

## Phase 4 — Deterministic Matching Engine

### Objective

Build the financial matching engine before adding AI. The baseline must be understandable and measurable.

### LLM instruction

```text
Act as a reconciliation-engine specialist. Implement matching in ordered passes: payment ID plus amount, order ID plus amount, UTR plus amount, stable internal reference, date and amount tolerance, candidate generation, and controlled aggregate matching. Detect conflicts, duplicates, and ambiguity. Store evidence for every decision. Never force-match a conflicting or unexplained record. Make all tolerances configurable and visible.
```

### Markdown files to create or update

- [ ] `docs/matching-rules.md`
- [ ] `docs/exception-taxonomy.md`
- [ ] `docs/metric-definitions.md`
- [ ] `docs/test-plan.md`
- [ ] `docs/architecture.md`

### Implementation outputs

- Exact matcher.
- Date and amount tolerance matcher.
- Candidate generator.
- Confidence scorer.
- One-to-many and many-to-one matcher.
- Duplicate and conflict detector.
- Match-evidence records.
- Baseline evaluation script.

### Validation gate

The matcher must not force-match an identifier conflict, duplicate, or ambiguous candidate. Any tolerance must be recorded in the run configuration. Baseline precision, recall, match rate, and unresolved count must be available.

### Definition of done

The full synthetic dataset can be processed without crashing, and every result is classified as auto-matched, review, rejected, or unresolved with evidence.

## Phase 5 — Exception Intelligence and AI Explanation

### Objective

Use the LLM where it adds value: exception classification, evidence-grounded explanation, and recommended next action. The LLM must not control the financial truth.

### LLM instruction

```text
Act as a cautious financial-operations assistant. Given only structured evidence from a reconciliation run, classify the exception, explain the likely cause, cite exact source record IDs, and recommend human-review actions. Return strict JSON matching the provided schema. Never invent records, amounts, fees, taxes, refunds, or causes. If the evidence is insufficient, return an abstention state with confidence below the review threshold.
```

### Markdown files to create or update

- [ ] `docs/ai-guardrails.md`
- [ ] `docs/audit-log-spec.md`
- [ ] `docs/exception-taxonomy.md`
- [ ] `docs/test-plan.md`
- [ ] `README.md`

### Implementation outputs

- Structured AI output schema.
- Evidence-only prompt construction.
- JSON validation.
- Source-record citations.
- AI timeout fallback.
- Invalid-output fallback.
- Abstention behavior.
- Model and prompt version logging.

### Validation gate

The AI cannot modify amounts, identifiers, matching thresholds, or final status without a deterministic rule or human review. Every explanation cites source rows. If the model is unavailable, the reconciliation still completes.

### Definition of done

The system can explain an amount mismatch, timing difference, partial refund, duplicate, and ambiguous match using only source-linked evidence.

## Phase 6 — Razorpay Integration and External Data Adapter

### Objective

Connect the same internal pipeline to Razorpay Test Mode where available without making the project dependent on credentials.

### LLM instruction

```text
Act as a secure Razorpay integration engineer. Build a server-side adapter for settlement and reconciliation retrieval using Test Mode credentials from environment variables. Keep the adapter optional and separate from the synthetic adapter. Normalize external responses into the internal data contract. Add retries, error handling, rate-limit handling, logging without secrets, and a clear fallback to fixtures. Do not expose credentials to the frontend or commit them to the repository.
```

### Markdown files to create or update

- [ ] `docs/architecture.md`
- [ ] `docs/api-contract.md`
- [ ] `docs/limitations.md`
- [ ] `docs/test-plan.md`
- [ ] `README.md`

### Implementation outputs

- Razorpay adapter interface.
- Synthetic adapter interface.
- Environment-variable configuration.
- API response normalization.
- Test Mode setup instructions.
- External-integration error states.
- Fixture fallback.

### Validation gate

The application works without Razorpay credentials. Live or production credentials are never requested for the demo. Any field unavailable from the Test Mode account is represented using synthetic fixtures and disclosed clearly.

### Definition of done

The same reconciliation pipeline can run in synthetic mode and, when correctly configured, accept data from the Razorpay Test Mode adapter without changing matching logic.

## Phase 7 — Human Review, Audit Trail, and Report Generation

### Objective

Make the product operationally useful by allowing reviewers to resolve exceptions and export a traceable close report.

### LLM instruction

```text
Act as a finance-controls product engineer. Implement a review queue for low-confidence, conflicting, missing, duplicate, fee, tax, timing, refund, and ambiguous exceptions. Show source records side by side. Allow approve, reject, split, and request-data decisions. Record every action in an append-only audit log. Generate a close report containing assumptions, metrics, matched records, unresolved exceptions, and reviewer actions. Never allow silent changes.
```

### Markdown files to create or update

- [ ] `docs/audit-log-spec.md`
- [ ] `docs/api-contract.md`
- [ ] `docs/exception-taxonomy.md`
- [ ] `docs/demo-script.md`
- [ ] `docs/limitations.md`

### Implementation outputs

- Exception queue.
- Match detail view.
- Human resolution actions.
- Audit timeline.
- Run summary.
- Markdown, JSON, or CSV report export.
- Report hash or signature.
- Source-linked evidence view.

### Validation gate

Every reviewer action is logged with actor, timestamp, evidence, prior status, and new status. A report can be regenerated from database records. Unresolved exceptions remain visible after export.

### Definition of done

A reviewer can inspect and resolve an exception without using the database directly, and the resulting close report shows exactly what changed and why.

## Phase 8 — Evaluation, Testing, and Hardening

### Objective

Prove the system works on a batch and behaves safely under failure.

### LLM instruction

```text
Act as an independent QA and evaluation lead. Test SettleSense against an independently labelled holdout dataset. Compare an exact-match baseline, exact-plus-tolerance matcher, and final candidate-scoring matcher. Report precision, recall, match rate, throughput, exception rate, reviewer time, and amount variance. Test duplicate inputs, conflicting identifiers, missing fields, ambiguous candidates, repeated events, model timeout, invalid model output, and database errors. Do not hide weak results.
```

### Markdown files to create or update

- [ ] `docs/test-plan.md`
- [ ] `docs/metric-definitions.md`
- [ ] `docs/limitations.md`
- [ ] `README.md`
- [ ] `data/evaluation/README.md`

### Implementation outputs

- Unit-test suite.
- Integration-test suite.
- Failure-injection tests.
- Security checks.
- Baseline comparison.
- Final evaluation report.
- Reproducible evaluation command.
- Known-issues list.

### Validation gate

The reported metrics must come from committed data and reproducible commands. The final system must not force-match unexplained rows. Weak precision or recall must be shown honestly rather than removed from the report.

### Definition of done

The project passes its critical tests, publishes a reproducible evaluation, and explains all remaining limitations.

## Phase 9 — Demo and Buildathon Submission

### Objective

Convert the working product into a clear five-minute submission that demonstrates real utility rather than only technical components.

### LLM instruction

```text
Act as a Buildathon pitch director. Write a five-minute demo script for SettleSense. The story must begin with a merchant finance problem, run a 100+ record reconciliation, show one exact match, one fee or timing exception, one ambiguous record that is not force-matched, one human resolution, and the final audit report. Include metrics, architecture, AI boundaries, Test Mode disclosure, and limitations. Keep the demo truthful and reproducible.
```

### Markdown files to create or update

- [ ] `README.md`
- [ ] `docs/demo-script.md`
- [ ] `docs/limitations.md`
- [ ] `docs/architecture.md`
- [ ] `docs/test-plan.md`
- [ ] `diagrams/README.md`

### Implementation outputs

- Public repository.
- Complete README.
- Architecture diagram.
- Five-minute demo video.
- Sample input files.
- Sample reconciliation report.
- Evaluation results.
- Test Mode and synthetic-data disclosure.
- Clean setup instructions.

### Validation gate

A clean environment can run the documented demo. The video numbers match the committed fixture output. No secrets or unnecessary personal data are present. The demo clearly shows the system refusing to force-match an unexplained row.

### Definition of done

SettleSense is ready for submission only when the product, documentation, evaluation, and demo tell the same story.

## Phase Dependencies

```text
Phase 0: Scope lock
        ↓
Phase 1: Documentation contract and data model
        ↓
Phase 2: Synthetic data and ground truth
        ↓
Phase 3: Ingestion and normalization
        ↓
Phase 4: Deterministic matching
        ↓
Phase 5: AI exception intelligence
        ↓
Phase 6: Razorpay adapter
        ↓
Phase 7: Human review and reports
        ↓
Phase 8: Evaluation and hardening
        ↓
Phase 9: Demo and submission
```

Phases 2–4 should be completed before meaningful AI work begins. Phase 6 is optional for the first working demo because the synthetic adapter must remain functional. Phases 7–9 are mandatory for a competition-ready project.

## Master Completion Checklist

### Product

- [ ] SettleSense reconciles settlement, bank, and internal ledger records.
- [ ] The system processes at least 100 records in one run.
- [ ] Exact, tolerance, candidate, duplicate, and aggregate logic exists.
- [ ] Every decision has evidence.
- [ ] Ambiguous records remain unresolved.
- [ ] Human review is available.
- [ ] An audit-ready report is generated.

### AI

- [ ] AI explanations use structured output.
- [ ] AI explanations cite exact source records.
- [ ] AI cannot modify financial values.
- [ ] AI timeout and invalid-output fallbacks work.
- [ ] Unsupported explanations produce abstention.

### Evaluation

- [ ] Ground truth is independent of the matcher.
- [ ] Precision is reported.
- [ ] Recall is reported.
- [ ] Overall match rate is reported.
- [ ] Throughput is reported.
- [ ] Exception categories are reported.
- [ ] Unresolved amount is reported.
- [ ] Baseline comparison is available.

### Documentation

- [ ] `README.md`
- [ ] `TASK.md`
- [ ] `MILESTONES.md`
- [ ] `DOCUMENTATION_PLAN.md`
- [ ] `docs/assumptions.md`
- [ ] `docs/data-dictionary.md`
- [ ] `docs/architecture.md`
- [ ] `docs/metric-definitions.md`
- [ ] `docs/exception-taxonomy.md`
- [ ] `docs/matching-rules.md`
- [ ] `docs/api-contract.md`
- [ ] `docs/ai-guardrails.md`
- [ ] `docs/audit-log-spec.md`
- [ ] `docs/test-plan.md`
- [ ] `docs/demo-script.md`
- [ ] `docs/limitations.md`
- [ ] `data/README.md`
- [ ] `data/fixtures/README.md`
- [ ] `data/evaluation/README.md`

## Final LLM Operating Prompt

Use this prompt at the start of every implementation phase:

```text
You are the implementation lead for SettleSense, a multi-source settlement reconciliation agent. Follow the current phase in MILESTONES.md and do not work on later phases prematurely. Preserve the documented data contract and assumptions. Prefer deterministic rules for money, identifiers, matching, thresholds, and audit decisions. Use AI only for evidence-grounded classification and explanation. Never invent records or force-match ambiguity. Before finishing the phase, run the phase validation gate, update the relevant Markdown files, list completed tasks, list unresolved risks, and provide the exact command needed to verify the result.
```
