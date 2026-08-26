# SettleSense

> An evidence-grounded multi-source settlement reconciliation agent for merchants.

## Problem

Finance teams spend significant time comparing settlement reports, bank statements, and internal order ledgers. SettleSense identifies supported matches, explains differences, routes uncertain records to human review, and generates an audit-ready close report.

## Features

- Settlement, bank, and internal-ledger ingestion.
- Deterministic exact and tolerance matching.
- Candidate scoring and controlled aggregate matching.
- Duplicate, missing, timing, fee, tax, refund, and ambiguity exceptions.
- Source-linked AI explanations.
- Human review workflow.
- Append-only audit trail.
- Batch metrics and report export.
- Synthetic mode without external credentials.
- Optional Razorpay Test Mode adapter.

## Architecture

Read `docs/architecture.md` and include the rendered architecture diagram here.

## Quick Start

```bash
cp .env.example .env
# install dependencies
# create database
python scripts/generate_dataset.py --seed 20260824 --records 120 --output data/generated
# run migrations
# start backend and frontend
```

## Documentation

| File | Purpose |
|---|---|
| `TASK.md` | Implementation backlog and acceptance criteria. |
| `MILESTONES.md` | Phase-wise LLM build plan. |
| `PROJECT_REQUIREMENTS.md` | Product requirements. |
| `docs/assumptions.md` | Configurable demo assumptions. |
| `docs/data-dictionary.md` | Source and output fields. |
| `docs/architecture.md` | System architecture. |
| `docs/matching-rules.md` | Matching behavior. |
| `docs/metric-definitions.md` | Evaluation metrics. |
| `docs/exception-taxonomy.md` | Exception codes and actions. |
| `docs/api-contract.md` | Backend API contract. |
| `docs/ai-guardrails.md` | AI boundaries. |
| `docs/audit-log-spec.md` | Audit specification. |
| `docs/test-plan.md` | Test strategy. |
| `docs/data-generation.md` | Synthetic data generation. |
| `docs/demo-script.md` | Five-minute demo. |
| `docs/limitations.md` | Disclosures and limitations. |

## Evaluation

```bash
python scripts/evaluate.py --data data/generated --ground-truth data/generated/ground_truth.json
```

The evaluation must report precision, recall, match rate, throughput, exception count, unresolved amount, amount variance, and force-match count.

## AI Boundaries

AI classifies and explains exceptions using source-linked evidence. It cannot invent records, change amounts, override deterministic rules, force-match ambiguity, or mark an exception resolved without a valid reviewer or rule decision.

## Razorpay Test Mode

Test Mode is optional. Keep credentials in backend environment variables only. Never commit secrets. Clearly label Test Mode records and synthetic records in the UI and final report.

## Data and Privacy

All committed fixtures are synthetic. Do not commit real customer, bank, payment, or API-key data.

## Limitations

Read `docs/limitations.md` before making production or accounting claims. The project is a Buildathon prototype and its report is an operational control report, not a tax filing or audit opinion.
