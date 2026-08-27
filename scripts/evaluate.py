"""Offline evaluation harness: fixtures -> matcher -> metrics vs independent ground truth.

Usage: python scripts/evaluate.py [--data data/generated] [--out data/evaluation/results.json]
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "/app/backend")

from services.ingestion import parse_csv_bytes, validate_and_normalize  # noqa: E402
from services.matching import run_matching  # noqa: E402
from services.evaluation import evaluate, baseline_comparison  # noqa: E402


def load(data_dir):
    d = Path(data_dir)
    sett, sett_inv = validate_and_normalize("settlement", parse_csv_bytes((d / "settlements.csv").read_bytes()))
    orders, ord_inv = validate_and_normalize("internal_ledger", parse_csv_bytes((d / "internal_ledger.csv").read_bytes()))
    bank, bank_inv = validate_and_normalize("bank_statement", parse_csv_bytes((d / "bank_statement.csv").read_bytes()))
    gt = json.loads((d / "ground_truth.json").read_text())
    return orders, sett, bank, gt, len(sett_inv) + len(ord_inv) + len(bank_inv)


def main(data_dir, out_path):
    orders, settlements, bank, gt, invalid_count = load(data_dir)
    t0 = time.perf_counter()
    result = run_matching([dict(o) for o in orders], [dict(s) for s in settlements],
                          [dict(b) for b in bank])
    elapsed = time.perf_counter() - t0
    ev = evaluate(result["matches"], gt)
    stats = result["stats"]
    exc_counts = {}
    for e in result["exceptions"]:
        exc_counts[e["exception_code"]] = exc_counts.get(e["exception_code"], 0) + 1
    records = len(orders) + len(settlements) + len(bank) + invalid_count
    eligible = stats["eligible_settlement_lines"] + stats["eligible_bank_credits"]
    matched = stats["auto_matched_settlement_lines"] + stats["matched_credits"]
    summary = {
        "dataset_version": gt["dataset_version"],
        "records_processed": records,
        "invalid_rows": invalid_count,
        "elapsed_seconds": round(elapsed, 4),
        "throughput_records_per_second": round(records / elapsed, 1),
        "overall_match_rate": round(matched / eligible, 4),
        "forced_match_count": stats["forced_match_count"],
        "exception_counts": exc_counts,
        "evaluation": ev,
        "baseline_comparison": baseline_comparison(orders, settlements, bank, gt),
    }
    print(json.dumps(summary, indent=2))
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/generated")
    ap.add_argument("--out", default="data/evaluation/results.json")
    a = ap.parse_args()
    main(a.data, a.out)
