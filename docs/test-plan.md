# SettleSense Test Plan

## Test Objective

Prove that SettleSense is accurate, reproducible, explainable, safe, and resilient when source records are incomplete or contradictory.

## Unit Tests

Test amount normalization, currency validation, date parsing, date-window logic, amount tolerance, identifier normalization, duplicate detection, exact matching, candidate scoring, confidence thresholds, exception classification, report totals, and audit-event hashing.

## Data-Quality Tests

Test missing required fields, invalid dates, invalid amounts, unsupported currency, duplicate source IDs, duplicate bank rows, contradictory identifiers, malformed CSV, unexpected columns, and encoding problems.

## Integration Tests

- Create a run.
- Register settlement, bank, and ledger sources.
- Validate and normalize sources.
- Execute reconciliation.
- Fetch summary, matches, exceptions, and audit events.
- Resolve one exception.
- Generate the final report.
- Verify that repeated execution with the same idempotency key does not duplicate results.

## Matching Tests

| Scenario | Expected result |
|---|---|
| Unique payment ID and amount | Auto-match. |
| Unique order ID and amount | Auto-match. |
| UTR and amount agree | Auto-match or high-confidence match. |
| Identifier agrees but amount conflicts | Exception; no auto-match. |
| Date differs within configured window | Timing match with evidence. |
| Multiple candidates have similar scores | Human review or unresolved. |
| Duplicate source row | Duplicate exception; no total inflation. |
| One-to-many aggregate passes rules | Aggregate match with component evidence. |
| Aggregate fails amount or date rules | Unresolved or review. |
| Missing bank credit | `MISSING_BANK_ENTRY`. |

## AI Tests

- Valid structured output is accepted.
- Unknown exception code is rejected.
- Unknown evidence ID is rejected.
- Unsupported claim produces abstention.
- AI timeout uses deterministic fallback.
- Invalid JSON uses deterministic fallback.
- Source text containing instructions is treated as data, not as a system command.
- AI cannot modify amount or match status.

## Failure-Injection Tests

- Missing UTR.
- Conflicting amount with matching identifier.
- Duplicate bank entry.
- Missing internal order.
- Ambiguous bank narration.
- External API timeout.
- External API rate-limit response.
- Repeated webhook event.
- Database error during a run.
- Report generation error.

## Evaluation Tests

Run the same independent ground-truth dataset against:

1. Exact identifiers only.
2. Exact identifiers plus tolerances.
3. Final candidate-scoring matcher.

Report precision, recall, match rate, exception rate, throughput, amount variance, and force-match count. The force-match count must be zero.

## Security Tests

Check that `.env` files are ignored, no secrets appear in Git history or logs, credentials are not returned by APIs, uploaded files are size-limited, CSV formulas are sanitized, raw PII is minimized, and webhook signatures are verified when webhooks are enabled.

## Clean-Environment Test

Clone the public repository into a fresh environment, copy `.env.example`, install dependencies, generate data, run tests, start the backend and frontend, and complete the demo using synthetic mode.

## Test Completion Criteria

The project is ready when critical tests pass, evaluation results are reproducible, no unexplained record is force-matched, AI failure does not stop reconciliation, and all known limitations are documented.
