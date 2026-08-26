# SettleSense API Contract

## API Conventions

- Base path: `/api`.
- JSON responses use ISO-8601 timestamps.
- Monetary values use integer minor units such as paise.
- Every reconciliation response includes `run_id` where relevant.
- Errors use stable `code`, human-readable `message`, and optional `details`.
- Mutating operations must be idempotent where repeated requests could duplicate effects.

## Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/runs` | Create a reconciliation run. |
| `GET` | `/api/runs/{run_id}` | Fetch run status and metadata. |
| `POST` | `/api/runs/{run_id}/sources` | Upload or register a source. |
| `POST` | `/api/runs/{run_id}/execute` | Start reconciliation. |
| `GET` | `/api/runs/{run_id}/summary` | Fetch metrics and financial totals. |
| `GET` | `/api/runs/{run_id}/matches` | List match decisions. |
| `GET` | `/api/runs/{run_id}/exceptions` | List exceptions with filters. |
| `GET` | `/api/exceptions/{exception_id}` | Fetch exception detail and evidence. |
| `POST` | `/api/exceptions/{exception_id}/resolve` | Record human resolution. |
| `GET` | `/api/runs/{run_id}/audit` | Fetch audit events. |
| `GET` | `/api/runs/{run_id}/report` | Generate or download close report. |
| `POST` | `/api/webhooks/razorpay` | Receive optional external webhook events. |
| `GET` | `/api/health` | Health check. |

## Create Run

### Request

```json
{
  "name": "March settlement close",
  "currency": "INR",
  "rules_version": "v1.0",
  "assumptions_version": "v1.0"
}
```

### Response

```json
{
  "run_id": "run_001",
  "status": "CREATED",
  "created_at": "2026-08-24T10:00:00Z",
  "rules_version": "v1.0",
  "assumptions_version": "v1.0"
}
```

## Register Source

Accept a multipart file or a fixture reference. Required source types are `settlement`, `bank_statement`, and `internal_ledger`. Optional types are `payments` and `refunds`.

The response must contain source ID, source type, file checksum, row count, validation error count, and status.

## Execute Run

A run can be executed only when required sources are loaded. The operation must return a job or run status and must not create duplicate results when repeated with the same idempotency key.

## Summary Response

```json
{
  "run_id": "run_001",
  "status": "COMPLETED",
  "records_processed": 120,
  "matched_records": 99,
  "unresolved_records": 21,
  "overall_match_rate": 0.825,
  "auto_match_precision": 0.97,
  "auto_match_recall": 0.82,
  "throughput_records_per_second": 35.2,
  "gross_amount_minor": 24000000,
  "matched_amount_minor": 21500000,
  "unresolved_amount_minor": 2500000,
  "exception_counts": {
    "AMOUNT_MISMATCH": 6,
    "DUPLICATE": 4,
    "AMBIGUOUS_MATCH": 5
  }
}
```

## Exception Resolution

### Request

```json
{
  "action": "approve_match",
  "match_id": "match_0042",
  "note": "Confirmed from bank advice document."
}
```

Allowed actions are `approve_match`, `reject_match`, `split_match`, `merge_match`, `request_data`, and `leave_unresolved`.

### Response

Return exception ID, previous status, new status, reviewer ID, timestamp, audit event ID, and any updated match/report values.

## Error Contract

```json
{
  "error": {
    "code": "AMBIGUOUS_MATCH",
    "message": "Multiple candidate records have similar confidence.",
    "details": {
      "candidate_ids": ["bank_001", "bank_002"]
    },
    "request_id": "req_001"
  }
}
```

## Webhook Contract

Webhook handling must verify signatures when enabled, persist the raw event, deduplicate by event ID, update the relevant state, and append an audit event. A duplicate webhook may not duplicate a match or transaction.

## Report Contract

The report endpoint must include summary metrics, source checksums, assumptions, matched records, unresolved exceptions, reviewer actions, audit references, generation timestamp, and report hash.
