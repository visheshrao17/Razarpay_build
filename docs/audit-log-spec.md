# SettleSense Audit Log Specification

## Purpose

The audit log proves what the system did, which records it used, which rules or model version produced the decision, and whether a human reviewed it.

## Append-Only Rule

Audit events must never be updated or deleted through the application. Corrections create new events. Raw source data and previous match decisions remain available.

## Event Schema

```json
{
  "audit_event_id": "audit_0001",
  "timestamp": "2026-08-24T10:00:00Z",
  "run_id": "run_001",
  "actor": "system|matcher|ai|reviewer",
  "step": "ingestion|normalization|candidate_generation|match_decision|explanation|review|report",
  "source_record_ids": ["settlement_001", "bank_002"],
  "exception_id": "exception_001",
  "match_id": "match_001",
  "rules_version": "v1.0",
  "assumptions_version": "v1.0",
  "model_version": "none",
  "decision": "auto_matched|review|unresolved|resolved|rejected",
  "confidence": 0.94,
  "human_gate": false,
  "evidence": [
    {"field": "utr", "source_record_id": "settlement_001", "value_hash": "..."},
    {"field": "amount_minor", "source_record_id": "bank_002", "value_hash": "..."}
  ],
  "outcome": "Matched by UTR and amount.",
  "previous_event_hash": "...",
  "event_hash": "..."
}
```

## Required Events

- Run created.
- Source registered.
- Source validated.
- Normalization completed.
- Match candidate generated.
- Match decision created.
- Exception created.
- AI explanation generated or rejected.
- Human review started.
- Human decision recorded.
- Report generated.
- Run closed or failed.

## Evidence Rules

Evidence must reference source record IDs and fields. For privacy, use value hashes or redacted values in long-lived logs where raw values are not necessary. The user-facing detail view may show synthetic values for the demo.

## Hash Chain

Each event should include the previous event hash and its own hash over the canonical JSON representation. This provides a simple tamper-evidence mechanism for the demo close report.

## Human Review Event

A human decision must include reviewer ID, action, note, previous status, new status, selected match or candidates, and timestamp. A reviewer cannot remove the original automated decision.

## Report Traceability

The final report must include the run ID, source checksums, rules version, assumptions version, metric version, audit event range, and report hash.
