# SettleSense Matching Rules

## Principle

Matching is a controlled financial decision. The system must prefer an honest unresolved record over an unsupported match.

## Matching Precedence

Apply rules in the following order:

1. Payment ID plus amount.
2. Order ID plus amount.
3. UTR plus amount.
4. Stable internal reference plus amount.
5. Date and amount tolerance.
6. Candidate generation using normalized narration and batch context.
7. Controlled one-to-many or many-to-one aggregation.

A stronger rule must not be silently overridden by a weaker rule.

## Validation Before Matching

Reject or classify records with missing required fields, invalid currency, invalid amounts, impossible dates, duplicate source IDs, or contradictory identifiers. Preserve the original raw value for review.

## Exact Matching

An exact match requires a unique identifier agreement and a compatible amount. If the identifier agrees but the amount conflicts, create `AMOUNT_MISMATCH` or `IDENTIFIER_CONFLICT`; do not auto-match.

## Tolerance Matching

Use the configured amount and date tolerances from `docs/assumptions.md`. The UI and audit log must show the values used for each run. Tolerances may handle rounding and settlement timing but must not hide material differences.

## Candidate Generation

For unmatched records, generate no more than five candidates using:

- Normalized payment or order identifiers.
- UTR tokens.
- Amount proximity.
- Date proximity.
- Normalized narration tokens.
- Settlement batch context.
- Refund or adjustment context.

Candidate generation must be deterministic and reproducible.

## Confidence Score

Use a configurable score:

```text
score = 0.40 * identifier_evidence
      + 0.25 * amount_evidence
      + 0.20 * date_evidence
      + 0.10 * narration_evidence
      + 0.05 * batch_evidence
```

The weights are demo assumptions, not universal financial rules.

| Score | Decision |
|---:|---|
| 0.90–1.00 | Auto-match only when no conflicts exist. |
| 0.60–0.89 | Human review with candidate evidence. |
| Below 0.60 | Unresolved. Do not force-match. |

## Aggregate Matching

One-to-many and many-to-one matches are allowed only when the aggregate amount, date window, identifiers, and source context pass explicit rules. Show every component row in the match detail view and audit log.

## Duplicate Handling

A duplicate must not inflate the reconciled total. Mark duplicate source records separately and retain the original records. A duplicate candidate must not become a second valid match.

## Refunds and Adjustments

Refunds, disputes, fees, taxes, and other adjustments must be represented as separate components in the amount waterfall. Never hide an adjustment inside an unexplained amount difference.

## Review Actions

A reviewer may approve, reject, split, merge, or request more data. Every action creates a new audit event. No prior decision is deleted.

## Prohibited Behavior

The matcher must never widen tolerances automatically, choose a candidate only because it produces a higher match rate, overwrite raw data, or mark a record resolved solely because an AI explanation sounds plausible.
