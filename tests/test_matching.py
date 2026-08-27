"""Core deterministic tests for the SettleSense matching engine.

Run: cd /app && /root/.venv/bin/python -m pytest tests/ -q
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/app/backend")

import pytest  # noqa: E402
from services.matching import run_matching, DEFAULT_CONFIG, day_diff, score  # noqa: E402
from services.ingestion import parse_csv_bytes, validate_and_normalize  # noqa: E402
from services.evaluation import evaluate  # noqa: E402
from services.ai_explain import validate_output, deterministic_fallback  # noqa: E402

DATA = Path("/app/data/generated")


def order(i, payment="pay_X1", gross=100000, date="2026-05-04T10:00:00+05:30", refund=0):
    return {"source_record_id": f"order_{i:04d}", "internal_order_id": f"ORD-{i}",
            "razorpay_order_id": f"ord_X{i}", "razorpay_payment_id": payment,
            "order_date": date, "gross_amount_minor": gross, "refund_amount_minor": refund,
            "expected_net_amount_minor": gross, "currency": "INR", "status": "paid"}


def settlement(i, payment="pay_X1", gross=100000, date="2026-05-05T10:00:00+05:30",
               batch="setl_1", utr="UTRX1", adjustment="", net=None, fee=None, tax=None):
    fee = gross * 200 // 10000 if fee is None else fee
    tax = fee * 1800 // 10000 if tax is None else tax
    return {"source_record_id": f"settlement_{i:04d}", "settlement_id": batch,
            "payment_id": payment, "order_id": f"ord_X{i}", "utr": utr,
            "settlement_date": date, "gross_amount_minor": gross, "fee_minor": fee,
            "tax_minor": tax, "net_amount_minor": net if net is not None else gross - fee - tax,
            "method": "upi", "adjustment_type": adjustment or None, "currency": "INR"}


def bank(i, utr="UTRX1", credit=0, date="2026-05-05T10:00:00+05:30", narration="NEFT CR"):
    return {"source_record_id": f"bank_{i:04d}", "bank_entry_id": f"S{i}", "value_date": date,
            "utr": utr or None, "narration": narration, "credit_amount_minor": credit,
            "debit_amount_minor": 0, "account_reference": "A", "currency": "INR"}


def test_exact_payment_id_auto_match():
    s = settlement(1)
    r = run_matching([order(1)], [s], [bank(1, credit=s["net_amount_minor"])])
    line = [m for m in r["matches"] if m["plane"] == "order_settlement"]
    assert len(line) == 1 and line[0]["decision"] == "auto_matched"
    assert line[0]["confidence"] >= 0.90
    bankm = [m for m in r["matches"] if m["plane"] == "settlement_bank"]
    assert len(bankm) == 1 and bankm[0]["decision"] == "auto_matched"


def test_identifier_conflict_is_never_force_matched():
    r = run_matching([order(1, gross=100000)], [settlement(1, gross=150000)], [])
    assert not [m for m in r["matches"] if m["plane"] == "order_settlement"]
    codes = [e["exception_code"] for e in r["exceptions"]]
    assert "IDENTIFIER_CONFLICT" in codes
    assert r["stats"]["forced_match_count"] == 0


def test_duplicate_does_not_inflate_totals():
    s1, s2 = settlement(1), settlement(1)
    s2 = dict(s2, source_record_id="settlement_0002")
    b = bank(1, credit=s1["net_amount_minor"])
    r = run_matching([order(1)], [s1, s2], [b])
    assert "DUPLICATE" in [e["exception_code"] for e in r["exceptions"]]
    bankm = [m for m in r["matches"] if m["plane"] == "settlement_bank"]
    assert bankm and bankm[0]["decision"] == "auto_matched"  # batch total excludes duplicate


def test_timing_difference_within_window():
    r = run_matching([order(1, date="2026-05-04T10:00:00+05:30")],
                     [settlement(1, date="2026-05-06T10:00:00+05:30")], [])
    assert "TIMING_DIFFERENCE" in [e["exception_code"] for e in r["exceptions"]]
    line = [m for m in r["matches"] if m["plane"] == "order_settlement"]
    assert line and line[0]["decision"] == "auto_matched"


def test_fee_variance_detected():
    s = settlement(1, fee=5000)  # 5% instead of 2%
    r = run_matching([order(1)], [s], [])
    assert "FEE_VARIANCE" in [e["exception_code"] for e in r["exceptions"]]


def test_ambiguous_bank_candidates_go_to_review():
    s = settlement(1, utr="")
    amt = s["net_amount_minor"]
    b1 = bank(1, utr="", credit=amt, narration="NEFT CR MISC A")
    b2 = bank(2, utr="", credit=amt, narration="NEFT CR MISC B")
    r = run_matching([order(1)], [s], [b1, b2])
    amb = [e for e in r["exceptions"] if e["exception_code"] == "AMBIGUOUS_MATCH"]
    assert amb, "two equal candidates must create AMBIGUOUS_MATCH"
    assert not [m for m in r["matches"] if m["plane"] == "settlement_bank"]


def test_missing_bank_entry():
    r = run_matching([order(1)], [settlement(1)], [])
    assert "MISSING_BANK_ENTRY" in [e["exception_code"] for e in r["exceptions"]]


def test_missing_order():
    r = run_matching([], [settlement(1)], [])
    assert "MISSING_ORDER" in [e["exception_code"] for e in r["exceptions"]]


def test_many_to_one_aggregate_with_cited_narration():
    s1 = settlement(1, batch="setl_0001", utr="")
    s2 = settlement(2, payment="pay_X2", batch="setl_0002", utr="", gross=200000)
    o2 = order(2, payment="pay_X2", gross=200000)
    total = s1["net_amount_minor"] + s2["net_amount_minor"]
    b = bank(1, utr="", credit=total, narration="RTGS CR COMBINED SETL0001 SETL0002")
    r = run_matching([order(1), o2], [s1, s2], [b])
    agg = [m for m in r["matches"] if m["match_type"] == "many_to_one"]
    assert agg and agg[0]["decision"] == "auto_matched"
    assert set(agg[0]["evidence"]["aggregate_batches"]) == {"setl_0001", "setl_0002"}


def test_partial_refund_linked():
    o = order(1, refund=30000)
    s_pay = settlement(1)
    s_ref = settlement(2, adjustment="refund", gross=30000, fee=0, tax=0, net=-30000)
    r = run_matching([o], [s_pay, s_ref], [])
    assert "PARTIAL_REFUND" in [e["exception_code"] for e in r["exceptions"]]


def test_ingestion_reports_invalid_rows_without_losing_valid():
    csv_bytes = (b"source_record_id,settlement_id,payment_id,order_id,utr,settlement_date,"
                 b"gross_amount_minor,fee_minor,tax_minor,net_amount_minor,method,adjustment_type,currency\n"
                 b"s1,b1,p1,o1,U1,2026-05-05T10:00:00+05:30,1000,20,4,976,upi,,INR\n"
                 b"s2,b1,p2,o2,U1,,1000,20,4,976,upi,,INR\n")
    valid, invalid = validate_and_normalize("settlement", parse_csv_bytes(csv_bytes))
    assert len(valid) == 1 and len(invalid) == 1
    assert "settlement_date is required" in invalid[0]["errors"][0]


def test_ai_output_validation_rejects_unknown_evidence():
    parsed = {"exception_code": "AMOUNT_MISMATCH", "summary": "x", "evidence_ids": ["ghost_001"],
              "confidence": 0.9, "recommended_action": "human_review", "abstain": False}
    assert validate_output(parsed, {"settlement_0001"}) is not None
    parsed["evidence_ids"] = ["settlement_0001"]
    assert validate_output(parsed, {"settlement_0001"}) is None


def test_ai_fallback_is_deterministic():
    exc = {"exception_code": "DUPLICATE", "record_ids": ["a"], "confidence": 0.9,
           "recommended_action": "human_review", "explanation": "dup"}
    fb = deterministic_fallback(exc, "timeout")
    assert fb["_fallback"] is True and fb["abstain"] is True


@pytest.mark.skipif(not (DATA / "ground_truth.json").exists(), reason="fixture not generated")
def test_full_fixture_precision_and_no_forced_matches():
    sett, _ = validate_and_normalize("settlement", parse_csv_bytes((DATA / "settlements.csv").read_bytes()))
    orders, _ = validate_and_normalize("internal_ledger", parse_csv_bytes((DATA / "internal_ledger.csv").read_bytes()))
    bank_rows, _ = validate_and_normalize("bank_statement", parse_csv_bytes((DATA / "bank_statement.csv").read_bytes()))
    gt = json.loads((DATA / "ground_truth.json").read_text())
    r = run_matching(orders, sett, bank_rows)
    ev = evaluate(r["matches"], gt)
    assert ev["auto_match_precision"] >= 0.95
    assert r["stats"]["forced_match_count"] == 0
    assert len(sett) >= 100


def test_reproducibility_same_input_same_result():
    args = ([order(1)], [settlement(1)], [bank(1, credit=97540)])
    r1 = run_matching(*[[dict(x) for x in a] for a in args])
    r2 = run_matching(*[[dict(x) for x in a] for a in args])
    assert json.dumps(r1["matches"], sort_keys=True) == json.dumps(r2["matches"], sort_keys=True)


def test_date_and_score_helpers():
    assert day_diff("2026-05-04T10:00:00", "2026-05-06T09:00:00") == 2
    assert score(DEFAULT_CONFIG, 1, 1, 1) == 1.0
