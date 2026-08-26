# SettleSense Architecture

## Architecture Goal

Separate financial truth and deterministic reconciliation from AI-generated explanations. The system must work in synthetic mode without external credentials and optionally accept Razorpay Test Mode data through a backend adapter.

## Components

| Component | Responsibility |
|---|---|
| Frontend | Run setup, metrics, match detail, exception review, audit view, report export. |
| API server | Run lifecycle, source uploads, reconciliation commands, review actions, reports. |
| Source adapters | Load synthetic fixtures, uploaded CSVs, or Razorpay data. |
| Raw data store | Preserve source rows exactly as received. |
| Normalization service | Convert dates, amounts, identifiers, and narrations to common types. |
| Matching engine | Apply deterministic match rules and create evidence. |
| Exception service | Classify unmatched, conflicting, duplicate, timing, fee, tax, and refund cases. |
| AI explanation service | Generate structured, source-grounded explanations. |
| Review service | Record human decisions without overwriting history. |
| Audit service | Append immutable events for material decisions. |
| Report service | Generate close report, metrics, assumptions, and unresolved list. |

## Data Flow

```text
Settlement source ─┐
Bank statement ────┼──> Raw records ─> Normalized records
Order ledger ──────┘                         |
                                             v
                                      Matching pipeline
                                             |
                              Matches + exceptions + evidence
                                             |
                              AI explanation and review queue
                                             |
                                  Final report and audit log
```

## Source Adapter Contract

Every adapter must expose:

```python
load_source(source_type: str, location: str, run_id: str) -> LoadResult
```

`LoadResult` must contain raw records, normalized records or normalization errors, source metadata, row counts, and a source checksum. The Razorpay adapter must be optional and must not be required for synthetic mode.

## Reconciliation Run State Machine

```text
CREATED → INGESTING → READY → RUNNING → COMPLETED
                         └──────────────→ FAILED
COMPLETED → REVIEWING → CLOSED
```

A completed run may enter reviewing when unresolved or low-confidence records exist. It may enter closed only after the operator exports or acknowledges the final report. Previous decisions must remain available in the audit trail.

## Database Boundaries

Store raw source data separately from normalized records. Store match decisions separately from reviewer decisions. Do not mutate raw data after ingestion. Use a run ID on every table that participates in a reconciliation.

## Failure Handling

| Failure | Expected behavior |
|---|---|
| Invalid CSV | Report invalid rows and continue with valid rows. |
| Missing field | Create `INVALID_SOURCE` exception. |
| Duplicate webhook or event | Ignore duplicate effect but retain audit event. |
| Razorpay API timeout | Retry with backoff, then fall back to recorded fixture or show integration error. |
| AI timeout | Complete deterministic matching and mark explanation unavailable. |
| Invalid AI JSON | Reject output and use deterministic exception explanation. |
| Database error | Mark run failed and preserve any committed audit events. |
| Ambiguous candidate | Send to review or unresolved; never force-match. |

## Security Boundaries

Razorpay credentials are accepted only by the backend. The frontend receives derived data, not secrets. Logs must redact credentials and unnecessary personal information. Synthetic mode must remain the default for local development.

## Observability

Log run ID, source type, stage, duration, rows processed, errors, and status. Do not log API secrets, raw authentication headers, or unnecessary customer data.

## Deployment Modes

### Synthetic mode

Runs entirely on committed fixtures and is required for evaluation and reproducibility.

### Razorpay Test Mode

Uses backend environment variables to fetch or normalize data where available. The adapter is isolated from the matching engine, and any missing fields are disclosed.

## Technology Recommendation

Use React and TypeScript for the frontend, FastAPI and Python for the backend, PostgreSQL for persistence, pandas or Polars for data processing, pytest for tests, and a structured-output LLM for exception explanations.
