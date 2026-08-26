# SettleSense Exception Taxonomy

| Code | Trigger | Severity | Required evidence | Default action |
|---|---|---|---|---|
| `MISSING_BANK_ENTRY` | Settlement has no matching bank credit. | High | Settlement ID, date, amount, candidate bank rows. | Human review. |
| `MISSING_ORDER` | Settlement or payment has no internal order. | High | Settlement/payment identifiers and ledger search result. | Unresolved. |
| `AMOUNT_MISMATCH` | Candidate amounts differ beyond configured tolerance. | High | Gross, fee, tax, refund, net, and bank amounts. | Human review. |
| `FEE_VARIANCE` | Fee differs from source or configured assumption. | Medium | Source fee, expected fee, assumption version. | Human review. |
| `TAX_VARIANCE` | Tax differs from source or configured assumption. | High | Source tax, expected tax, assumption version. | Human review. |
| `DUPLICATE` | Source record or transaction appears more than once. | High | Duplicate source IDs and matching fields. | Exclude duplicate; review. |
| `TIMING_DIFFERENCE` | Dates differ within a configured settlement window. | Low | Settlement date, bank value date, configured window. | Probable match or review. |
| `PARTIAL_REFUND` | Refund changes expected net amount. | Medium | Payment, refund, order, and settlement IDs. | Explain and match components. |
| `DISPUTE_ADJUSTMENT` | Dispute or adjustment affects the settlement. | High | Adjustment source, settlement, payment, and amount. | Human review. |
| `AMBIGUOUS_MATCH` | Multiple candidates have similar confidence. | Medium | All candidates and comparative scores. | Unresolved or human review. |
| `IDENTIFIER_CONFLICT` | Same ID appears with conflicting amounts or sources. | Critical | Conflicting source rows and values. | Reject auto-match. |
| `INVALID_SOURCE` | Required field, type, currency, or date is invalid. | Medium | Raw row and validation error. | Reject row; report. |
| `UNEXPECTED_ADJUSTMENT` | Net amount contains an unexplained component. | High | Amount waterfall and source components. | Human review. |
| `API_DATA_GAP` | External adapter cannot supply a required field. | Medium | Adapter response and missing field. | Use fixture or unresolved. |

## Exception Lifecycle

```text
OPEN → IN_REVIEW → RESOLVED
  └──────────────→ REJECTED
  └──────────────→ UNRESOLVED
```

A resolved exception requires a reviewer action or a documented deterministic rule. The system must preserve the previous state in the audit log.

## Severity Rules

Critical exceptions involve identifier conflicts, duplicate financial entries, or material unexplained amounts. High exceptions can affect the close or create a missing-money explanation. Medium exceptions need review but may not block the complete run. Low exceptions are explainable timing or formatting issues.

## Human Actions

Reviewers may approve a proposed match, reject a proposed match, split an aggregate match, merge compatible rows, request missing data, or leave an item unresolved. Each action must include a note and create an audit event.
