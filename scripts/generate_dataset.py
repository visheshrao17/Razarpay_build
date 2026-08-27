"""Deterministic synthetic dataset generator for SettleSense.

Usage: python scripts/generate_dataset.py --seed 20260824 --records 120 --output data/generated

All data is synthetic. Fee = 2% of gross, tax = 18% of fee are DEMO ASSUMPTIONS (v1.0),
not universal Razorpay/GST rules. Ground truth is written independently of the matcher.
"""
import argparse
import csv
import hashlib
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

GENERATOR_VERSION = "v1.0"
FEE_RATE_BPS = 200
TAX_ON_FEE_BPS = 1800
BASE_DATE = datetime(2026, 5, 4, 10, 0, 0)

# scenario bands over payment-line indices 1..120
CLEAN = list(range(1, 53)) + list(range(96, 121))
TIMING = list(range(53, 63))
FEE_VAR = list(range(63, 68))
TAX_VAR = list(range(68, 73))
REFUND = list(range(73, 81))
MISSING_ORDER = list(range(81, 86))
CONFLICT = list(range(86, 91))
DUPLICATE = list(range(91, 96))  # duplicates of lines 1..5


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S+05:30")


def batch_of(i):
    return (i - 1) // 12 + 1


def main(seed, records, output):
    rng = random.Random(seed)
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)

    gross = {}
    for i in range(1, 121):
        if i in TAX_VAR:
            gross[i] = rng.randrange(2000, 25000) * 100
        else:
            gross[i] = rng.randrange(500, 25000) * 100

    orders, settlements, banks, payments = [], [], [], []
    gt_pairs, gt_bank_pairs, gt_exceptions = [], [], []
    batch_lines = {}

    def expected_fee(g):
        return g * FEE_RATE_BPS // 10000

    def expected_tax(f):
        return f * TAX_ON_FEE_BPS // 10000

    for i in range(1, 121):
        sid = f"settlement_{i:04d}"
        if i in DUPLICATE:
            src = i - 90
            orig = next(s for s in settlements if s["source_record_id"] == f"settlement_{src:04d}")
            dup = dict(orig)
            dup["source_record_id"] = sid
            settlements.append(dup)
            gt_exceptions.append({"code": "DUPLICATE", "record_ids": [orig["source_record_id"], sid]})
            continue

        b = batch_of(i)
        order_day = BASE_DATE + timedelta(days=(i - 1) // 12)
        settle_offset = 2 if i in TIMING else 1
        settle_day = order_day + timedelta(days=settle_offset)
        g = gross[i]
        order_g = g - (5000 + i * 10) if i in CONFLICT else g
        fee = g * 300 // 10000 if i in FEE_VAR else expected_fee(g)
        tax = fee * 2800 // 10000 if i in TAX_VAR else expected_tax(fee)
        net = g - fee - tax
        refund_amt = (g * 30 // 100) if i in REFUND else 0

        settlements.append({
            "source_record_id": sid, "settlement_id": f"setl_{b:04d}",
            "payment_id": f"pay_JX{i:05d}" if i not in MISSING_ORDER else f"pay_MISSING{i:03d}",
            "order_id": f"order_JX{i:05d}" if i not in MISSING_ORDER else f"order_MISSING{i:03d}",
            "utr": f"UTR2026{b:04d}", "settlement_date": iso(settle_day),
            "gross_amount_minor": g, "fee_minor": fee, "tax_minor": tax,
            "net_amount_minor": net, "method": rng.choice(["upi", "card", "netbanking"]),
            "adjustment_type": "", "currency": "INR",
        })
        batch_lines.setdefault(b, []).append({"id": sid, "net": net, "date": settle_day})

        if i not in MISSING_ORDER:
            oid = f"order_{i:04d}"
            exp_net = order_g - expected_fee(order_g) - expected_tax(expected_fee(order_g)) - refund_amt
            orders.append({
                "source_record_id": oid, "internal_order_id": f"ORD-2026-{1000 + i}",
                "razorpay_order_id": f"order_JX{i:05d}", "razorpay_payment_id": f"pay_JX{i:05d}",
                "order_date": iso(order_day), "gross_amount_minor": order_g,
                "refund_amount_minor": refund_amt, "expected_net_amount_minor": exp_net,
                "currency": "INR",
                "status": "partially_refunded" if i in REFUND else "paid",
                "customer_reference": f"INV-{7000 + i}",
            })
            payments.append({
                "source_record_id": f"payment_{i:04d}", "payment_id": f"pay_JX{i:05d}",
                "order_id": f"order_JX{i:05d}", "payment_amount_minor": order_g,
                "refund_amount_minor": refund_amt,
                "payment_status": "partially_refunded" if i in REFUND else "captured",
                "payment_date": iso(order_day), "currency": "INR",
            })
            if i in CONFLICT:
                gt_exceptions.append({"code": "IDENTIFIER_CONFLICT", "record_ids": [sid, oid]})
            else:
                gt_pairs.append({"plane": "order_settlement", "settlement": sid, "order": oid,
                                 "expected_decision": "auto"})
            if i in TIMING:
                gt_exceptions.append({"code": "TIMING_DIFFERENCE", "record_ids": [sid, oid]})
            if i in FEE_VAR:
                gt_exceptions.append({"code": "FEE_VARIANCE", "record_ids": [sid, oid]})
            if i in TAX_VAR:
                gt_exceptions.append({"code": "TAX_VARIANCE", "record_ids": [sid, oid]})
        else:
            gt_exceptions.append({"code": "MISSING_ORDER", "record_ids": [sid]})

    # refund adjustment lines 121..128 (same batch as their payment line)
    for j, i in enumerate(REFUND):
        sid = f"settlement_{121 + j:04d}"
        b = batch_of(i)
        refund_amt = gross[i] * 30 // 100
        settle_day = BASE_DATE + timedelta(days=(i - 1) // 12 + 1)
        settlements.append({
            "source_record_id": sid, "settlement_id": f"setl_{b:04d}",
            "payment_id": f"pay_JX{i:05d}", "order_id": f"order_JX{i:05d}",
            "utr": f"UTR2026{b:04d}", "settlement_date": iso(settle_day),
            "gross_amount_minor": refund_amt, "fee_minor": 0, "tax_minor": 0,
            "net_amount_minor": -refund_amt, "method": "refund",
            "adjustment_type": "refund", "currency": "INR",
        })
        batch_lines[b].append({"id": sid, "net": -refund_amt, "date": settle_day})
        gt_pairs.append({"plane": "refund", "settlement": sid, "order": f"order_{i:04d}",
                         "expected_decision": "auto"})
        gt_exceptions.append({"code": "PARTIAL_REFUND", "record_ids": [sid, f"order_{i:04d}"]})

    # invalid settlement row (missing settlement_date)
    settlements.append({
        "source_record_id": "settlement_0129", "settlement_id": "setl_0003",
        "payment_id": "pay_JXBROKEN", "order_id": "", "utr": "UTR20260003",
        "settlement_date": "", "gross_amount_minor": 120000, "fee_minor": 2400,
        "tax_minor": 432, "net_amount_minor": 117168, "method": "upi",
        "adjustment_type": "", "currency": "INR",
    })
    gt_exceptions.append({"code": "INVALID_SOURCE", "record_ids": ["settlement_0129"]})

    # ---- bank statement ----
    bank_n = 0

    def add_bank(value_date, utr, narration, credit, debit=0, ref="ACC-XX9147"):
        nonlocal bank_n
        bank_n += 1
        row = {"source_record_id": f"bank_{bank_n:04d}", "bank_entry_id": f"STMT-{bank_n:04d}",
               "value_date": iso(value_date), "utr": utr, "narration": narration,
               "credit_amount_minor": credit, "debit_amount_minor": debit,
               "account_reference": ref, "currency": "INR"}
        banks.append(row)
        return row

    def batch_total(b):
        return sum(l["net"] for l in batch_lines[b])

    def batch_date(b):
        return max(l["date"] for l in batch_lines[b])

    def batch_line_ids(b):
        return [l["id"] for l in batch_lines[b]]

    for b in range(1, 6):
        extra = timedelta(days=1) if b == 4 else timedelta(0)
        row = add_bank(batch_date(b) + extra, f"UTR2026{b:04d}",
                       f"NEFT CR RAZORPAY SOFTWARE PVT LTD SETL{b:04d} UTR2026{b:04d}", batch_total(b))
        gt_bank_pairs.append({"batch": f"setl_{b:04d}", "bank": [row["source_record_id"]],
                              "expected_decision": "auto", "match_type": "exact"})
    # duplicate of batch 2 credit
    dup_src = banks[1]
    dup_row = add_bank(datetime.fromisoformat(dup_src["value_date"]), dup_src["utr"],
                       dup_src["narration"], dup_src["credit_amount_minor"])
    gt_exceptions.append({"code": "DUPLICATE", "record_ids": [dup_src["source_record_id"],
                                                              dup_row["source_record_id"]]})
    # batch 6: ambiguous — real credit without UTR + decoy with same amount
    real6 = add_bank(batch_date(6), "", "NEFT CR RAZORPAY SETTLEMENT MAY WEEK", batch_total(6))
    decoy6 = add_bank(batch_date(6) + timedelta(days=1), "", "NEFT CR RAZORPAY SETTLEMENT ADJ",
                      batch_total(6))
    gt_exceptions.append({"code": "AMBIGUOUS_MATCH",
                          "record_ids": [real6["source_record_id"], decoy6["source_record_id"]],
                          "note": "deliberate graceful failure: two plausible credits for setl_0006"})
    # batch 7: split into two rows (one_to_many)
    t7 = batch_total(7)
    part1 = t7 * 60 // 100
    r1 = add_bank(batch_date(7), "UTR20260007",
                  "NEFT CR RAZORPAY SETL0007 PART 1 OF 2 UTR20260007", part1)
    r2 = add_bank(batch_date(7), "UTR20260007",
                  "NEFT CR RAZORPAY SETL0007 PART 2 OF 2 UTR20260007", t7 - part1)
    gt_bank_pairs.append({"batch": "setl_0007", "bank": [r1["source_record_id"], r2["source_record_id"]],
                          "expected_decision": "auto", "match_type": "one_to_many"})
    # batch 8: missing bank credit
    gt_exceptions.append({"code": "MISSING_BANK_ENTRY", "record_ids": batch_line_ids(8)})
    # batches 9+10: one combined credit (many_to_one)
    comb = add_bank(max(batch_date(9), batch_date(10)), "",
                    "RTGS CR RAZORPAY COMBINED SETL0009 SETL0010",
                    batch_total(9) + batch_total(10))
    for b in (9, 10):
        gt_bank_pairs.append({"batch": f"setl_{b:04d}", "bank": [comb["source_record_id"]],
                              "expected_decision": "auto", "match_type": "many_to_one"})
    # unexplained credit
    extra_cr = add_bank(BASE_DATE + timedelta(days=6), "", "NEFT CR INTEREST CREDIT Q1", 843100)
    gt_exceptions.append({"code": "UNEXPECTED_ADJUSTMENT", "record_ids": [extra_cr["source_record_id"]]})
    # misc debits (excluded from matching)
    debit_narrations = ["ACH DR OFFICE RENT MAY", "NEFT DR VENDOR ALPHA SUPPLIES",
                        "IMPS DR COURIER PARTNER", "DR BANK CHARGES GST", "NEFT DR PAYROLL BATCH 1",
                        "NEFT DR PAYROLL BATCH 2", "DR CARD ANNUAL FEE", "IMPS DR UTILITIES ELECTRICITY"]
    for k, narr in enumerate(debit_narrations):
        add_bank(BASE_DATE + timedelta(days=k + 1), "", narr, 0, rng.randrange(500, 90000) * 100)
    # invalid bank row
    bank_n += 1
    banks.append({"source_record_id": f"bank_{bank_n:04d}", "bank_entry_id": f"STMT-{bank_n:04d}",
                  "value_date": iso(BASE_DATE + timedelta(days=3)), "utr": "",
                  "narration": "NEFT CR MALFORMED ROW", "credit_amount_minor": "notanumber",
                  "debit_amount_minor": 0, "account_reference": "ACC-XX9147", "currency": "INR"})
    gt_exceptions.append({"code": "INVALID_SOURCE", "record_ids": [f"bank_{bank_n:04d}"]})

    files = {
        "settlements.csv": settlements, "internal_ledger.csv": orders,
        "bank_statement.csv": banks, "payments.csv": payments,
    }
    checksums = {}
    for name, rows in files.items():
        path = out / name
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        checksums[name] = hashlib.sha256(path.read_bytes()).hexdigest()

    ground_truth = {
        "dataset_version": f"seed-{seed}-{GENERATOR_VERSION}",
        "seed": seed, "generator_version": GENERATOR_VERSION,
        "generated_independently_of_matcher": True,
        "order_settlement_matches": [p for p in gt_pairs if p["plane"] == "order_settlement"],
        "refund_matches": [p for p in gt_pairs if p["plane"] == "refund"],
        "settlement_bank_matches": gt_bank_pairs,
        "expected_exceptions": gt_exceptions,
        "case_mix": {
            "clean_exact": len(CLEAN), "timing_offsets": len(TIMING),
            "fee_variance": len(FEE_VAR), "tax_variance": len(TAX_VAR),
            "partial_refunds": len(REFUND), "missing_orders": len(MISSING_ORDER),
            "identifier_conflicts_deliberately_unresolved": len(CONFLICT),
            "duplicate_settlements": len(DUPLICATE), "duplicate_bank_rows": 1,
            "missing_bank_credit_batches": 1, "ambiguous_bank_narrations": 2,
            "one_to_many": 1, "many_to_one": 1, "invalid_rows": 2, "unexplained_credits": 1,
        },
    }
    gt_path = out / "ground_truth.json"
    gt_path.write_text(json.dumps(ground_truth, indent=2))
    checksums["ground_truth.json"] = hashlib.sha256(gt_path.read_bytes()).hexdigest()
    (out / "checksums.json").write_text(json.dumps(checksums, indent=2))

    (out / "README.md").write_text(f"""# SettleSense Generated Dataset

- Seed: `{seed}` | Generator: `{GENERATOR_VERSION}` | Dataset version: `seed-{seed}-{GENERATOR_VERSION}`
- Regenerate with: `python scripts/generate_dataset.py --seed {seed} --records {records} --output data/generated`
- All records are SYNTHETIC. Identifiers, UTRs, narrations and amounts are generated for testing and do not
  represent real merchant, bank, Razorpay or customer behaviour.
- Fee (2% of gross) and tax (18% of fee) are versioned DEMO ASSUMPTIONS (v1.0), not universal rules.
- Ground truth (`ground_truth.json`) is written by this generator BEFORE any matching runs and never calls the matcher.

## Counts
- Settlement lines: {len(settlements)} (incl. {len(REFUND)} refund adjustments, {len(DUPLICATE)} duplicates, 1 invalid row)
- Internal orders: {len(orders)}
- Bank statement rows: {len(banks)} (incl. 1 duplicate, 8 debits, 1 invalid row)
- Payments: {len(payments)}

## Case mix
{json.dumps(ground_truth["case_mix"], indent=2)}

## File checksums (SHA-256)
{json.dumps(checksums, indent=2)}
""")
    print(f"Generated {len(settlements)} settlements, {len(orders)} orders, "
          f"{len(banks)} bank rows, {len(payments)} payments -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260824)
    ap.add_argument("--records", type=int, default=120)
    ap.add_argument("--output", default="data/generated")
    a = ap.parse_args()
    main(a.seed, a.records, a.output)
