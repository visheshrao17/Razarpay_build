# SettleSense Data Dictionary

## Conventions

All records include `run_id`, `source_system`, `source_record_id`, and ingestion timestamps. Money must use integer minor units or decimal-safe types. Timestamps must be timezone-aware ISO-8601 values.

## Internal Order Ledger

| Field | Type | Required | Description |
|---|---|---:|---|
| `internal_order_id` | string | Yes | Merchant’s internal order identifier. |
| `razorpay_order_id` | string | No | Razorpay order reference. |
| `razorpay_payment_id` | string | No | Razorpay payment reference. |
| `order_date` | datetime | Yes | Internal order or payment date. |
| `gross_amount_minor` | integer | Yes | Gross amount in paise. |
| `refund_amount_minor` | integer | Yes | Refund amount in paise. |
| `expected_net_amount_minor` | integer | Yes | Expected net amount under configured assumptions. |
| `currency` | string | Yes | ISO currency code, normally INR. |
| `status` | enum | Yes | Paid, refunded, partially_refunded, disputed, cancelled. |
| `customer_reference` | string | No | Sanitized customer or invoice reference. |

## Razorpay Settlement Record

| Field | Type | Required | Description |
|---|---|---:|---|
| `settlement_id` | string | Yes | Settlement batch identifier. |
| `payment_id` | string | No | Payment identifier. |
| `order_id` | string | No | Order identifier. |
| `utr` | string | No | Bank transfer reference. |
| `settlement_date` | datetime | Yes | Settlement date. |
| `gross_amount_minor` | integer | Yes | Gross amount in paise. |
| `fee_minor` | integer | No | Fee recorded by source. |
| `tax_minor` | integer | No | Tax recorded by source. |
| `net_amount_minor` | integer | Yes | Net amount in paise. |
| `method` | string | No | Payment method. |
| `adjustment_type` | string | No | Refund, dispute, chargeback, fee, or other adjustment. |

## Bank Statement Record

| Field | Type | Required | Description |
|---|---|---:|---|
| `bank_entry_id` | string | Yes | Unique bank statement row ID. |
| `value_date` | datetime | Yes | Bank value date. |
| `utr` | string | No | Bank UTR. |
| `narration` | string | Yes | Sanitized statement narration. |
| `credit_amount_minor` | integer | Yes | Credit amount in paise. |
| `debit_amount_minor` | integer | Yes | Debit amount in paise. |
| `account_reference` | string | No | Sanitized account reference. |

## Payment and Refund Record

| Field | Type | Required | Description |
|---|---|---:|---|
| `payment_id` | string | Yes | Payment identifier. |
| `order_id` | string | No | Associated order. |
| `payment_amount_minor` | integer | Yes | Payment amount in paise. |
| `refund_amount_minor` | integer | Yes | Total refund in paise. |
| `payment_status` | string | Yes | Captured, failed, refunded, partially_refunded. |
| `payment_date` | datetime | Yes | Payment timestamp. |

## Match Decision

| Field | Type | Required | Description |
|---|---|---:|---|
| `match_id` | string | Yes | Unique match decision ID. |
| `source_a_id` | string | Yes | First source record. |
| `source_b_id` | string | Yes | Second source record. |
| `match_type` | enum | Yes | Exact, tolerance, fuzzy, one_to_many, many_to_one. |
| `confidence` | decimal | Yes | Score from 0 to 1. |
| `evidence` | JSON | Yes | Fields and values supporting the match. |
| `decision` | enum | Yes | Auto-matched, review, rejected, unresolved. |
| `rules_version` | string | Yes | Version of matching policy. |

## Exception

| Field | Type | Required | Description |
|---|---|---:|---|
| `exception_id` | string | Yes | Unique exception ID. |
| `exception_code` | string | Yes | Stable taxonomy code. |
| `severity` | enum | Yes | Low, medium, high, critical. |
| `record_ids` | JSON array | Yes | Related source records. |
| `amount_at_risk_minor` | integer | No | Related amount in paise. |
| `confidence` | decimal | Yes | Confidence in classification. |
| `status` | enum | Yes | Open, in_review, resolved, rejected, unresolved. |
| `recommended_action` | string | Yes | Next action for reviewer. |
| `explanation` | string | No | Evidence-grounded explanation. |

## Audit Event

| Field | Type | Required | Description |
|---|---|---:|---|
| `audit_event_id` | string | Yes | Unique event ID. |
| `timestamp` | datetime | Yes | Event timestamp. |
| `run_id` | string | Yes | Reconciliation run. |
| `actor` | enum | Yes | System, matcher, AI, reviewer. |
| `step` | string | Yes | Pipeline step. |
| `source_record_ids` | JSON array | Yes | Referenced records. |
| `decision` | string | Yes | Decision taken. |
| `evidence` | JSON | Yes | Evidence summary. |
| `model_version` | string | No | AI model version. |
| `rules_version` | string | Yes | Rules version. |
| `human_gate` | boolean | Yes | Whether human review was required. |
| `outcome` | string | Yes | Result of the event. |

## Reconciliation Run

| Field | Type | Required | Description |
|---|---|---:|---|
| `run_id` | string | Yes | Unique run identifier. |
| `status` | enum | Yes | Created, ingesting, ready, running, completed, reviewing, closed, failed. |
| `created_at` | datetime | Yes | Run creation time. |
| `completed_at` | datetime | No | Run completion time. |
| `rules_version` | string | Yes | Matching-rules version. |
| `assumptions_version` | string | Yes | Assumptions version. |
| `source_checksums` | JSON | Yes | Checksums of input sources. |
| `summary_metrics` | JSON | No | Metrics generated by the run. |
