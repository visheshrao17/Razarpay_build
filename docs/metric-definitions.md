# SettleSense Metric Definitions

## Evaluation Rules

Metrics must be calculated on an independently labelled dataset. The matcher must not generate its own ground truth. All metrics must include the run ID, dataset version, assumptions version, and rules version.

## Core Metrics

| Metric | Formula | Interpretation |
|---|---|---|
| Auto-match precision | Correct auto-matches ÷ all auto-matches | How trustworthy automatic matches are. |
| Auto-match recall | Correct auto-matches ÷ all ground-truth matches | How many true matches are automatically found. |
| Overall match rate | All accepted matches ÷ eligible records | Operational coverage. |
| Exception rate | Exceptions ÷ processed records | Share requiring attention. |
| Throughput | Processed records ÷ processing time | Pipeline speed. |
| Amount variance | Absolute expected amount minus reconciled amount | Remaining financial difference. |
| Review rate | Human-review records ÷ eligible records | Operational workload. |
| Reviewer resolution time | Review completion time minus review creation time | Human effort and delay. |
| Duplicate precision | Correct duplicate flags ÷ all duplicate flags | Trustworthiness of duplicate detection. |
| AI grounding accuracy | Explanations with correct evidence IDs ÷ explanations evaluated | Whether AI explanations cite actual data. |

## Match Categories

Report metrics separately for exact, tolerance, fuzzy-candidate, one-to-many, many-to-one, and human-resolved matches. A single aggregate match rate is insufficient for diagnosis.

## Financial Metrics

Report gross amount, settlement amount, bank-credit amount, matched amount, unresolved amount, adjustment amount, and residual variance. Use paise or decimal-safe values and format for display only at the final UI layer.

## Required Evaluation Output

```json
{
  "run_id": "run_001",
  "dataset_version": "seed-2026-v1",
  "rules_version": "v1.0",
  "records_processed": 120,
  "auto_match_precision": 0.97,
  "auto_match_recall": 0.82,
  "overall_match_rate": 0.91,
  "throughput_records_per_second": 35.2,
  "exception_count": 21,
  "unresolved_amount_minor": 125000,
  "amount_variance_minor": 3500,
  "forced_match_count": 0
}
```

## Baseline Comparison

Evaluate at least three systems:

1. Exact identifiers only.
2. Exact identifiers plus configured tolerance.
3. Final candidate-scoring matcher with exception handling.

The report must show whether each layer improves recall while preserving acceptable precision.

## Interpretation Rules

High match rate with low precision is not a success. A low match rate may be acceptable when the unresolved list is accurate and actionable. The target for the demo is zero force-matches and a clearly explained exception list.
