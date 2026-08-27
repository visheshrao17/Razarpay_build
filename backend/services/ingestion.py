"""CSV parsing, validation and normalization. Raw values are preserved on every record."""
import csv
import hashlib
import io

REQUIRED_SOURCES = ["settlement", "bank_statement", "internal_ledger"]
OPTIONAL_SOURCES = ["payments"]
FIXTURE_FILES = {
    "settlement": "settlements.csv",
    "bank_statement": "bank_statement.csv",
    "internal_ledger": "internal_ledger.csv",
    "payments": "payments.csv",
}


def checksum_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def parse_csv_bytes(content: bytes):
    text = content.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def _int_field(row, field, errors, required=True, allow_negative=False):
    val = (row.get(field) or "").strip()
    if val == "":
        if required:
            errors.append(f"{field} is required")
        return 0
    try:
        n = int(val)
    except ValueError:
        errors.append(f"{field} is not an integer: '{val}'")
        return 0
    if n < 0 and not allow_negative:
        errors.append(f"{field} must not be negative: {n}")
    return n


def _date_field(row, field, errors, required=True):
    val = (row.get(field) or "").strip()
    if val == "":
        if required:
            errors.append(f"{field} is required")
        return ""
    from datetime import datetime
    try:
        datetime.fromisoformat(val.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{field} is not an ISO-8601 date: '{val}'")
        return ""
    return val


def _str_field(row, field, errors, required=True):
    val = (row.get(field) or "").strip()
    if required and val == "":
        errors.append(f"{field} is required")
    return val


def _currency(row, errors):
    cur = (row.get("currency") or "INR").strip().upper()
    if cur != "INR":
        errors.append(f"unsupported currency '{cur}' (only INR is supported in the MVP)")
    return cur


def normalize_settlement(row, idx):
    errors = []
    rec = {
        "source_record_id": _str_field(row, "source_record_id", errors) or f"settlement_upload_{idx:04d}",
        "settlement_id": _str_field(row, "settlement_id", errors),
        "payment_id": _str_field(row, "payment_id", errors, required=False) or None,
        "order_id": _str_field(row, "order_id", errors, required=False) or None,
        "utr": _str_field(row, "utr", errors, required=False) or None,
        "settlement_date": _date_field(row, "settlement_date", errors),
        "gross_amount_minor": _int_field(row, "gross_amount_minor", errors),
        "fee_minor": _int_field(row, "fee_minor", errors, required=False),
        "tax_minor": _int_field(row, "tax_minor", errors, required=False),
        "net_amount_minor": _int_field(row, "net_amount_minor", errors, allow_negative=True),
        "method": _str_field(row, "method", errors, required=False) or None,
        "adjustment_type": _str_field(row, "adjustment_type", errors, required=False) or None,
        "currency": _currency(row, errors),
        "raw": dict(row),
    }
    if rec["gross_amount_minor"] <= 0:
        errors.append("gross_amount_minor must be positive")
    if rec["net_amount_minor"] < 0 and not rec["adjustment_type"]:
        errors.append("negative net_amount_minor requires an adjustment_type")
    return rec, errors


def normalize_order(row, idx):
    errors = []
    rec = {
        "source_record_id": _str_field(row, "source_record_id", errors) or f"order_upload_{idx:04d}",
        "internal_order_id": _str_field(row, "internal_order_id", errors),
        "razorpay_order_id": _str_field(row, "razorpay_order_id", errors, required=False) or None,
        "razorpay_payment_id": _str_field(row, "razorpay_payment_id", errors, required=False) or None,
        "order_date": _date_field(row, "order_date", errors),
        "gross_amount_minor": _int_field(row, "gross_amount_minor", errors),
        "refund_amount_minor": _int_field(row, "refund_amount_minor", errors, required=False),
        "expected_net_amount_minor": _int_field(row, "expected_net_amount_minor", errors, allow_negative=True),
        "currency": _currency(row, errors),
        "status": _str_field(row, "status", errors, required=False) or "paid",
        "customer_reference": _str_field(row, "customer_reference", errors, required=False) or None,
        "raw": dict(row),
    }
    if rec["gross_amount_minor"] <= 0:
        errors.append("gross_amount_minor must be positive")
    return rec, errors


def normalize_bank(row, idx):
    errors = []
    rec = {
        "source_record_id": _str_field(row, "source_record_id", errors) or f"bank_upload_{idx:04d}",
        "bank_entry_id": _str_field(row, "bank_entry_id", errors),
        "value_date": _date_field(row, "value_date", errors),
        "utr": _str_field(row, "utr", errors, required=False) or None,
        "narration": _str_field(row, "narration", errors),
        "credit_amount_minor": _int_field(row, "credit_amount_minor", errors, required=False),
        "debit_amount_minor": _int_field(row, "debit_amount_minor", errors, required=False),
        "account_reference": _str_field(row, "account_reference", errors, required=False) or None,
        "currency": _currency(row, errors),
        "raw": dict(row),
    }
    if rec["credit_amount_minor"] == 0 and rec["debit_amount_minor"] == 0:
        errors.append("either credit_amount_minor or debit_amount_minor must be non-zero")
    return rec, errors


def normalize_payment(row, idx):
    errors = []
    rec = {
        "source_record_id": _str_field(row, "source_record_id", errors) or f"payment_upload_{idx:04d}",
        "payment_id": _str_field(row, "payment_id", errors),
        "order_id": _str_field(row, "order_id", errors, required=False) or None,
        "payment_amount_minor": _int_field(row, "payment_amount_minor", errors),
        "refund_amount_minor": _int_field(row, "refund_amount_minor", errors, required=False),
        "payment_status": _str_field(row, "payment_status", errors),
        "payment_date": _date_field(row, "payment_date", errors),
        "currency": _currency(row, errors),
        "raw": dict(row),
    }
    return rec, errors


NORMALIZERS = {
    "settlement": normalize_settlement,
    "internal_ledger": normalize_order,
    "bank_statement": normalize_bank,
    "payments": normalize_payment,
}


def validate_and_normalize(source_type, rows):
    normalizer = NORMALIZERS[source_type]
    valid, invalid = [], []
    for idx, row in enumerate(rows, start=1):
        rec, errors = normalizer(row, idx)
        if errors:
            invalid.append({"row_number": idx, "raw": dict(row), "errors": errors})
        else:
            valid.append(rec)
    return valid, invalid
