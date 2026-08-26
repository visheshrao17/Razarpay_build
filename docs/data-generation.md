# SettleSense Synthetic Data Generation

## Purpose

Create deterministic fixtures for development, evaluation, and demo. The synthetic data is not production data and must not be presented as evidence of actual Indian merchant behavior.

## Required Sources

Generate:

- `settlements.csv` with at least 100 settlement lines.
- `internal_ledger.csv` with at least 100 internal order records.
- `bank_statement.csv` with bank credits, debits, UTRs, narrations, and timing offsets.
- `payments.csv` with payment and refund references.
- `ground_truth.json` containing expected match relationships and exception labels.

## Required Case Mix

| Case | Minimum |
|---|---:|
| Exact matches | 40 |
| Date offsets | 10 |
| Fee or tax variances | 10 |
| Partial refunds | 8 |
| Duplicates | 5 |
| Missing orders | 5 |
| Missing bank credits | 5 |
| Ambiguous narrations | 5 |
| One-to-many or many-to-one cases | 5 |
| Deliberately unresolved cases | 5 |

## Reproducibility

Use a fixed random seed and version the generator. The same command must recreate the same files. Store a checksum for each output file.

Recommended command:

```bash
python scripts/generate_dataset.py --seed 20260824 --records 120 --output data/generated
```

## Ground Truth

Generate ground truth before running the matcher. Store expected relationships, duplicate labels, exception labels, and aggregate components separately. The ground-truth file must not call or import the final matching function.

## Data Safety

Use synthetic names, identifiers, account numbers, UTRs, and amounts. Do not copy real customer or bank information. Keep values realistic enough to exercise parsing and matching but clearly synthetic.

## Data Dictionary

Write a generated `data/generated/README.md` containing record counts, seed, generator version, case mix, field definitions, and assumptions.
