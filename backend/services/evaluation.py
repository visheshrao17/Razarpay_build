"""Evaluation against independent ground truth + baseline comparison."""
from services.matching import run_matching


def canonical_pairs(matches, decisions=("auto_matched",)):
    pairs = set()
    for m in matches:
        if m["decision"] not in decisions:
            continue
        if m["plane"] in ("order_settlement", "refund"):
            pairs.add((m["plane"], m["source_a_ids"][0], m["source_b_ids"][0]))
        elif m["plane"] == "settlement_bank":
            banks = frozenset(m["source_b_ids"])
            batch_ids = m["evidence"].get("aggregate_batches") or [m["evidence"].get("batch_id")]
            for b in batch_ids:
                if b:
                    pairs.add(("settlement_bank", b, banks))
    return pairs


def gt_pairs(ground_truth):
    all_pairs, auto_pairs = set(), set()
    for p in ground_truth.get("order_settlement_matches", []):
        pair = ("order_settlement", p["settlement"], p["order"])
        all_pairs.add(pair)
        if p.get("expected_decision") == "auto":
            auto_pairs.add(pair)
    for p in ground_truth.get("refund_matches", []):
        pair = ("refund", p["settlement"], p["order"])
        all_pairs.add(pair)
        if p.get("expected_decision") == "auto":
            auto_pairs.add(pair)
    for p in ground_truth.get("settlement_bank_matches", []):
        pair = ("settlement_bank", p["batch"], frozenset(p["bank"]))
        all_pairs.add(pair)
        if p.get("expected_decision") == "auto":
            auto_pairs.add(pair)
    return all_pairs, auto_pairs


def evaluate(matches, ground_truth):
    auto = canonical_pairs(matches, decisions=("auto_matched",))
    all_gt, auto_gt = gt_pairs(ground_truth)
    correct_auto = auto & all_gt
    precision = round(len(correct_auto) / len(auto), 4) if auto else None
    recall = round(len(auto & auto_gt) / len(auto_gt), 4) if auto_gt else None
    return {
        "dataset_version": ground_truth.get("dataset_version"),
        "auto_matches": len(auto),
        "ground_truth_pairs": len(all_gt),
        "ground_truth_auto_pairs": len(auto_gt),
        "correct_auto_matches": len(correct_auto),
        "incorrect_auto_matches": sorted([list(map(str, p)) for p in (auto - all_gt)]),
        "auto_match_precision": precision,
        "auto_match_recall": recall,
    }


BASELINES = {
    "exact_only": {"enable_tolerance": False, "enable_candidates": False, "enable_aggregate": False},
    "exact_plus_tolerance": {"enable_tolerance": True, "enable_candidates": False, "enable_aggregate": False},
    "final_candidate_scoring": {"enable_tolerance": True, "enable_candidates": True, "enable_aggregate": True},
}


def baseline_comparison(orders, settlements, bank_entries, ground_truth, base_config=None):
    results = {}
    for name, flags in BASELINES.items():
        cfg = dict(base_config or {})
        cfg.update(flags)
        for r in orders + settlements + bank_entries:
            r.pop("_matched_order", None)
        result = run_matching([dict(o) for o in orders], [dict(s) for s in settlements],
                              [dict(b) for b in bank_entries], cfg)
        ev = evaluate(result["matches"], ground_truth)
        stats = result["stats"]
        eligible = stats["eligible_settlement_lines"] + stats["eligible_bank_credits"]
        matched = stats["auto_matched_settlement_lines"] + stats["matched_credits"]
        results[name] = {
            "auto_match_precision": ev["auto_match_precision"],
            "auto_match_recall": ev["auto_match_recall"],
            "auto_matches": ev["auto_matches"],
            "overall_match_rate": round(matched / eligible, 4) if eligible else None,
            "exception_count": len(result["exceptions"]),
            "forced_match_count": stats["forced_match_count"],
        }
    return results
