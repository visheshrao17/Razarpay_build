# SettleSense Generated Dataset

- Seed: `20260824` | Generator: `v1.0` | Dataset version: `seed-20260824-v1.0`
- Regenerate with: `python scripts/generate_dataset.py --seed 20260824 --records 120 --output data/generated`
- All records are SYNTHETIC. Identifiers, UTRs, narrations and amounts are generated for testing and do not
  represent real merchant, bank, Razorpay or customer behaviour.
- Fee (2% of gross) and tax (18% of fee) are versioned DEMO ASSUMPTIONS (v1.0), not universal rules.
- Ground truth (`ground_truth.json`) is written by this generator BEFORE any matching runs and never calls the matcher.

## Counts
- Settlement lines: 129 (incl. 8 refund adjustments, 5 duplicates, 1 invalid row)
- Internal orders: 110
- Bank statement rows: 21 (incl. 1 duplicate, 8 debits, 1 invalid row)
- Payments: 110

## Case mix
{
  "clean_exact": 77,
  "timing_offsets": 10,
  "fee_variance": 5,
  "tax_variance": 5,
  "partial_refunds": 8,
  "missing_orders": 5,
  "identifier_conflicts_deliberately_unresolved": 5,
  "duplicate_settlements": 5,
  "duplicate_bank_rows": 1,
  "missing_bank_credit_batches": 1,
  "ambiguous_bank_narrations": 2,
  "one_to_many": 1,
  "many_to_one": 1,
  "invalid_rows": 2,
  "unexplained_credits": 1
}

## File checksums (SHA-256)
{
  "settlements.csv": "eb06cf0941aaf7ab0b212e16d253cc65cacbb6676fe92a95ced283d872d4a368",
  "internal_ledger.csv": "294fd504a40bae93ea79bf156488004be3395d564a957ee518fa1a6ed50afb6b",
  "bank_statement.csv": "d1753d905936bad25be82161410b866025dabb4d94e5cfba199b609cc0140377",
  "payments.csv": "6e67d0f7bf664f4b142e9554dbe9e30f1b55a2078de0b122f87c2c507c7d6ab8",
  "ground_truth.json": "71f9eb73aff5b0172656da80cf7af27b85b9a1f9d5f0ae38864e666deb2c8fcf"
}
