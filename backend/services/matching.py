"""Deterministic matching engine. Pure functions over record dicts — no DB, no AI."""
from datetime import datetime
from itertools import combinations
import re

RULES_VERSION = "v1.0"

DEFAULT_CONFIG = {
    "rules_version": RULES_VERSION,
    "assumptions_version": "v1.0",
    "amount_tolerance_minor": 100,
    "date_window_days": 2,
    "fee_rate_bps": 200,
    "tax_on_fee_bps": 1800,
    "auto_threshold": 0.90,
    "review_threshold": 0.60,
    "ambiguity_gap": 0.10,
    "max_candidates": 5,
    "weights": {"identifier": 0.40, "amount": 0.25, "date": 0.20, "narration": 0.10, "batch": 0.05},
    "enable_tolerance": True,
    "enable_candidates": True,
    "enable_aggregate": True,
}


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def day_diff(a, b):
    da, db = parse_date(a), parse_date(b)
    if da is None or db is None:
        return 999
    return abs((da.date() - db.date()).days)


def norm_token(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def score(cfg, identifier, amount, date, narration=1.0, batch=1.0):
    w = cfg["weights"]
    return round(
        w["identifier"] * identifier + w["amount"] * amount + w["date"] * date
        + w["narration"] * narration + w["batch"] * batch, 4)


def date_evidence(dd, window):
    if dd <= window:
        return 1.0
    return max(0.0, 1.0 - (dd - window) / 5.0)


class MatchContext:
    def __init__(self):
        self.matches = []
        self.exceptions = []

    def add_match(self, plane, match_type, a_ids, b_ids, confidence, decision, evidence):
        m = {"plane": plane, "match_type": match_type, "source_a_ids": list(a_ids),
             "source_b_ids": list(b_ids), "confidence": confidence, "decision": decision,
             "evidence": evidence, "rules_version": RULES_VERSION}
        self.matches.append(m)
        return m

    def add_exception(self, code, severity, record_ids, amount_at_risk, confidence,
                      recommended_action, explanation, evidence=None, status="OPEN", match_index=None):
        e = {"exception_code": code, "severity": severity, "record_ids": list(record_ids),
             "amount_at_risk_minor": int(amount_at_risk), "confidence": confidence,
             "recommended_action": recommended_action, "explanation": explanation,
             "evidence": evidence or {}, "status": status, "match_index": match_index}
        self.exceptions.append(e)
        return e


def detect_duplicates(ctx, records, key_fn, label):
    seen = {}
    for r in records:
        key = key_fn(r)
        if key in seen:
            r["is_duplicate"] = True
            r["duplicate_of"] = seen[key]["source_record_id"]
            ctx.add_exception(
                "DUPLICATE", "high",
                [seen[key]["source_record_id"], r["source_record_id"]],
                abs(r.get("net_amount_minor") or r.get("credit_amount_minor") or r.get("gross_amount_minor") or 0),
                0.98, "human_review",
                f"{label} record {r['source_record_id']} duplicates {seen[key]['source_record_id']} on identical key fields. "
                f"The duplicate is excluded from reconciled totals until resolved.",
                {"duplicate_key_fields": [str(k) for k in key], "original": seen[key]["source_record_id"]})
        else:
            r["is_duplicate"] = False
            r["duplicate_of"] = None
            seen[key] = r


def match_lines_to_orders(ctx, cfg, lines, orders):
    """Pass 1-4: settlement line ↔ internal order."""
    window = cfg["date_window_days"]
    tol = cfg["amount_tolerance_minor"]
    by_payment, by_order = {}, {}
    for o in orders:
        if o.get("razorpay_payment_id"):
            by_payment.setdefault(o["razorpay_payment_id"], []).append(o)
        if o.get("razorpay_order_id"):
            by_order.setdefault(o["razorpay_order_id"], []).append(o)
    matched_orders = set()

    def try_identifier(line, candidates, id_field, id_strength):
        if len(candidates) > 1:
            ctx.add_exception(
                "IDENTIFIER_CONFLICT", "critical",
                [line["source_record_id"]] + [c["source_record_id"] for c in candidates],
                line["gross_amount_minor"], 0.95, "reject_auto_match",
                f"Identifier {id_field}={line.get(id_field.replace('razorpay_', ''))} maps to multiple internal orders. "
                "Auto-match rejected.", {"conflicting_orders": [c["source_record_id"] for c in candidates]},
                status="UNRESOLVED")
            return True
        order = candidates[0]
        if order["source_record_id"] in matched_orders:
            return False
        diff = abs(line["gross_amount_minor"] - order["gross_amount_minor"])
        dd = day_diff(line["settlement_date"], order["order_date"])
        if diff == 0 or (cfg["enable_tolerance"] and diff <= tol):
            amount_ev = 1.0 if diff == 0 else 0.75
            conf = score(cfg, id_strength, amount_ev, date_evidence(dd, window))
            decision = "auto_matched" if conf >= cfg["auto_threshold"] else (
                "review" if conf >= cfg["review_threshold"] else "unresolved")
            evidence = {
                "matched_on": id_field, "identifier_value": order.get(id_field) or line.get("payment_id") or line.get("order_id"),
                "settlement_gross_minor": line["gross_amount_minor"], "order_gross_minor": order["gross_amount_minor"],
                "amount_diff_minor": diff, "date_diff_days": dd,
                "settlement_date": line["settlement_date"], "order_date": order["order_date"],
                "match_type": "exact" if diff == 0 else "tolerance",
                "components": {"identifier": id_strength, "amount": amount_ev, "date": date_evidence(dd, window)},
            }
            m = ctx.add_match("order_settlement", "exact" if diff == 0 else "tolerance",
                              [line["source_record_id"]], [order["source_record_id"]], conf, decision, evidence)
            if decision != "unresolved":
                matched_orders.add(order["source_record_id"])
                line["_matched_order"] = order
            if decision == "review":
                ctx.add_exception(
                    "AMBIGUOUS_MATCH", "medium",
                    [line["source_record_id"], order["source_record_id"]],
                    line["gross_amount_minor"], conf, "human_review",
                    f"Confidence {conf} is below the auto-match threshold {cfg['auto_threshold']}. Human review required.",
                    evidence, match_index=len(ctx.matches) - 1)
            if 2 <= dd <= window:
                ctx.add_exception(
                    "TIMING_DIFFERENCE", "low",
                    [line["source_record_id"], order["source_record_id"]],
                    0, conf, "probable_match",
                    f"Settlement date {line['settlement_date'][:10]} differs from order date {order['order_date'][:10]} "
                    f"by {dd} day(s), inside the configured {window}-day settlement window. Probable match with date evidence.",
                    {"date_diff_days": dd, "configured_window_days": window}, match_index=len(ctx.matches) - 1)
            return True
        ctx.add_exception(
            "IDENTIFIER_CONFLICT", "critical",
            [line["source_record_id"], order["source_record_id"]],
            diff, 0.95, "reject_auto_match",
            f"Identifier {id_field} agrees but amounts conflict: settlement gross {line['gross_amount_minor']} vs "
            f"order gross {order['gross_amount_minor']} (difference {diff} paise exceeds tolerance {tol}). "
            "Auto-match refused; the record is left unresolved.",
            {"matched_on": id_field, "settlement_gross_minor": line["gross_amount_minor"],
             "order_gross_minor": order["gross_amount_minor"], "amount_diff_minor": diff,
             "tolerance_minor": tol}, status="UNRESOLVED")
        return True

    for line in lines:
        handled = False
        if line.get("payment_id") and line["payment_id"] in by_payment:
            handled = try_identifier(line, by_payment[line["payment_id"]], "razorpay_payment_id", 1.0)
        if not handled and line.get("order_id") and line["order_id"] in by_order:
            handled = try_identifier(line, by_order[line["order_id"]], "razorpay_order_id", 0.95)
        if handled:
            continue
        # Pass 3: candidate generation (no identifier hit)
        candidates = []
        if cfg["enable_candidates"]:
            for o in orders:
                if o["source_record_id"] in matched_orders:
                    continue
                diff = abs(line["gross_amount_minor"] - o["gross_amount_minor"])
                dd = day_diff(line["settlement_date"], o["order_date"])
                if diff > max(tol * 5, line["gross_amount_minor"] // 100) or dd > window + 3:
                    continue
                amount_ev = 1.0 if diff == 0 else (0.75 if diff <= tol else 0.3)
                conf = score(cfg, 0.0, amount_ev, date_evidence(dd, window))
                candidates.append((conf, o, diff, dd))
            candidates.sort(key=lambda c: (-c[0], c[1]["source_record_id"]))
            candidates = candidates[:cfg["max_candidates"]]
        if not candidates:
            ctx.add_exception(
                "MISSING_ORDER", "high", [line["source_record_id"]],
                abs(line["net_amount_minor"]), 0.9, "leave_unresolved",
                f"Settlement line {line['source_record_id']} (payment_id={line.get('payment_id')}) has no corresponding "
                "internal order and no plausible candidate. Review source ingestion or order mapping.",
                {"payment_id": line.get("payment_id"), "order_id": line.get("order_id"),
                 "gross_amount_minor": line["gross_amount_minor"]}, status="UNRESOLVED")
            continue
        top = candidates[0]
        cand_evidence = [{"order": c[1]["source_record_id"], "confidence": c[0],
                          "amount_diff_minor": c[2], "date_diff_days": c[3]} for c in candidates]
        if len(candidates) > 1 and (candidates[0][0] - candidates[1][0]) < cfg["ambiguity_gap"]:
            ctx.add_exception(
                "AMBIGUOUS_MATCH", "medium",
                [line["source_record_id"]] + [c[1]["source_record_id"] for c in candidates],
                line["gross_amount_minor"], top[0], "human_review",
                f"{len(candidates)} internal orders are plausible candidates with similar confidence "
                f"(top {candidates[0][0]} vs next {candidates[1][0]}, gap below {cfg['ambiguity_gap']}). "
                "The system refuses to force-match; human review required.",
                {"candidates": cand_evidence}, status="OPEN")
        elif top[0] >= cfg["review_threshold"]:
            m = ctx.add_match("order_settlement", "fuzzy", [line["source_record_id"]],
                              [top[1]["source_record_id"]], top[0],
                              "review" if top[0] < cfg["auto_threshold"] else "auto_matched",
                              {"candidates": cand_evidence, "selected": top[1]["source_record_id"]})
            if m["decision"] == "review":
                ctx.add_exception(
                    "AMBIGUOUS_MATCH", "medium",
                    [line["source_record_id"], top[1]["source_record_id"]],
                    line["gross_amount_minor"], top[0], "human_review",
                    f"Best candidate confidence {top[0]} is in the review band "
                    f"({cfg['review_threshold']}–{cfg['auto_threshold']}). Human confirmation required.",
                    {"candidates": cand_evidence}, match_index=len(ctx.matches) - 1)
            else:
                matched_orders.add(top[1]["source_record_id"])
                line["_matched_order"] = top[1]
        else:
            ctx.add_exception(
                "MISSING_ORDER", "high", [line["source_record_id"]],
                abs(line["net_amount_minor"]), top[0], "leave_unresolved",
                f"No candidate reaches the review threshold {cfg['review_threshold']} "
                f"(best {top[0]}). Left unresolved; do not force-match.",
                {"candidates": cand_evidence}, status="UNRESOLVED")
    return matched_orders


def check_fee_tax(ctx, cfg, lines):
    tol = cfg["amount_tolerance_minor"]
    for line in lines:
        if line.get("fee_minor") is None:
            continue
        expected_fee = line["gross_amount_minor"] * cfg["fee_rate_bps"] // 10000
        expected_tax = expected_fee * cfg["tax_on_fee_bps"] // 10000
        actual_tax_on_expected = (line.get("fee_minor") or 0) * cfg["tax_on_fee_bps"] // 10000
        ids = [line["source_record_id"]]
        if line.get("_matched_order"):
            ids.append(line["_matched_order"]["source_record_id"])
        if abs((line.get("fee_minor") or 0) - expected_fee) > tol:
            ctx.add_exception(
                "FEE_VARIANCE", "medium", ids,
                abs((line.get("fee_minor") or 0) - expected_fee), 0.9, "human_review",
                f"Source fee {line['fee_minor']} paise differs from the configured demo assumption "
                f"({cfg['fee_rate_bps'] / 100}% of gross = {expected_fee} paise) by "
                f"{abs(line['fee_minor'] - expected_fee)} paise. Assumption version {cfg['assumptions_version']} — "
                "demo assumption, not a universal fee rule. Do not auto-post; flag for review.",
                {"source_fee_minor": line["fee_minor"], "expected_fee_minor": expected_fee,
                 "fee_rate_bps": cfg["fee_rate_bps"], "assumptions_version": cfg["assumptions_version"]})
        elif abs((line.get("tax_minor") or 0) - actual_tax_on_expected) > tol:
            ctx.add_exception(
                "TAX_VARIANCE", "high", ids,
                abs((line.get("tax_minor") or 0) - actual_tax_on_expected), 0.9, "human_review",
                f"Source tax {line['tax_minor']} paise differs from the configured demo assumption "
                f"({cfg['tax_on_fee_bps'] / 100}% of fee = {actual_tax_on_expected} paise). "
                f"Assumption version {cfg['assumptions_version']} — demo assumption, not tax advice.",
                {"source_tax_minor": line["tax_minor"], "expected_tax_minor": actual_tax_on_expected,
                 "tax_on_fee_bps": cfg["tax_on_fee_bps"], "assumptions_version": cfg["assumptions_version"]})
        computed_net = line["gross_amount_minor"] - (line.get("fee_minor") or 0) - (line.get("tax_minor") or 0)
        if computed_net != line["net_amount_minor"]:
            ctx.add_exception(
                "UNEXPECTED_ADJUSTMENT", "high", ids,
                abs(computed_net - line["net_amount_minor"]), 0.85, "human_review",
                f"Net amount {line['net_amount_minor']} does not equal gross - fee - tax ({computed_net}). "
                "An unexplained component exists in the amount waterfall.",
                {"gross_minor": line["gross_amount_minor"], "fee_minor": line.get("fee_minor"),
                 "tax_minor": line.get("tax_minor"), "net_minor": line["net_amount_minor"],
                 "computed_net_minor": computed_net})


def link_refunds(ctx, cfg, refund_lines, orders):
    by_payment = {o["razorpay_payment_id"]: o for o in orders if o.get("razorpay_payment_id")}
    for line in refund_lines:
        order = by_payment.get(line.get("payment_id"))
        if not order:
            ctx.add_exception(
                "MISSING_ORDER", "high", [line["source_record_id"]],
                abs(line["net_amount_minor"]), 0.9, "leave_unresolved",
                f"Refund adjustment {line['source_record_id']} references payment_id={line.get('payment_id')} "
                "with no internal order.", {}, status="UNRESOLVED")
            continue
        refund_amt = abs(line["net_amount_minor"])
        amount_ok = abs(refund_amt - order["refund_amount_minor"]) <= cfg["amount_tolerance_minor"]
        conf = 0.95 if amount_ok else 0.7
        m = ctx.add_match("refund", "exact", [line["source_record_id"]], [order["source_record_id"]],
                          conf, "auto_matched" if amount_ok else "review",
                          {"matched_on": "razorpay_payment_id", "refund_line_minor": line["net_amount_minor"],
                           "order_refund_minor": order["refund_amount_minor"], "amount_agrees": amount_ok})
        ctx.add_exception(
            "PARTIAL_REFUND", "medium",
            [line["source_record_id"], order["source_record_id"]],
            refund_amt, conf, "verify_refund_linkage",
            f"Refund of {refund_amt} paise on payment {line.get('payment_id')} reduces the expected net for order "
            f"{order['internal_order_id']} (order refund recorded: {order['refund_amount_minor']} paise, "
            f"{'amounts agree' if amount_ok else 'AMOUNTS DISAGREE'}). Payment, refund and settlement records linked.",
            {"refund_line_minor": line["net_amount_minor"], "order_refund_minor": order["refund_amount_minor"]},
            match_index=len(ctx.matches) - 1)


def match_batches_to_bank(ctx, cfg, lines, bank_rows):
    tol = cfg["amount_tolerance_minor"]
    window = cfg["date_window_days"]
    batches = {}
    for line in lines:
        b = batches.setdefault(line["settlement_id"], {
            "batch_id": line["settlement_id"], "utr": line.get("utr"),
            "total_net_minor": 0, "line_ids": [], "date": line["settlement_date"]})
        b["total_net_minor"] += line["net_amount_minor"]
        b["line_ids"].append(line["source_record_id"])
        if line["settlement_date"] > b["date"]:
            b["date"] = line["settlement_date"]
    credits = [r for r in bank_rows if not r["is_duplicate"] and (r.get("credit_amount_minor") or 0) > 0]
    utr_groups = {}
    for c in credits:
        if c.get("utr"):
            utr_groups.setdefault(c["utr"], []).append(c)
    matched_credits, matched_batches = set(), set()
    deferred_missing = []
    ambiguous_batches, ambiguous_credit_ids = set(), set()

    for batch in sorted(batches.values(), key=lambda b: b["batch_id"]):
        rows = utr_groups.get(batch["utr"] or "", [])
        rows = [r for r in rows if r["source_record_id"] not in matched_credits]
        if rows:
            bank_amt = sum(r["credit_amount_minor"] for r in rows)
            diff = abs(bank_amt - batch["total_net_minor"])
            dd = min(day_diff(batch["date"], r["value_date"]) for r in rows)
            evidence = {
                "matched_on": "utr", "utr": batch["utr"], "batch_id": batch["batch_id"],
                "batch_net_minor": batch["total_net_minor"], "bank_credit_minor": bank_amt,
                "amount_diff_minor": diff, "date_diff_days": dd,
                "component_bank_rows": [r["source_record_id"] for r in rows],
                "component_settlement_lines": batch["line_ids"],
            }
            if diff == 0 or (cfg["enable_tolerance"] and diff <= tol):
                conf = score(cfg, 1.0, 1.0 if diff == 0 else 0.75, date_evidence(dd, window))
                mtype = "one_to_many" if len(rows) > 1 else ("exact" if diff == 0 else "tolerance")
                decision = "auto_matched" if conf >= cfg["auto_threshold"] else "review"
                ctx.add_match("settlement_bank", mtype, batch["line_ids"],
                              [r["source_record_id"] for r in rows], conf, decision, evidence)
                matched_batches.add(batch["batch_id"])
                matched_credits.update(r["source_record_id"] for r in rows)
                if 2 <= dd <= window:
                    ctx.add_exception(
                        "TIMING_DIFFERENCE", "low",
                        batch["line_ids"][:3] + [r["source_record_id"] for r in rows], 0, conf,
                        "probable_match",
                        f"Bank value date differs from settlement date by {dd} day(s), inside the configured "
                        f"{window}-day window.", {"date_diff_days": dd, "configured_window_days": window},
                        match_index=len(ctx.matches) - 1)
            else:
                ctx.add_exception(
                    "AMOUNT_MISMATCH", "high",
                    batch["line_ids"][:5] + [r["source_record_id"] for r in rows],
                    diff, 0.9, "human_review",
                    f"UTR {batch['utr']} agrees but the bank credit ({bank_amt} paise) differs from the settlement "
                    f"batch net ({batch['total_net_minor']} paise) by {diff} paise, beyond tolerance {tol}. "
                    "Likely components: fee/tax difference, partial refund, or missing line.",
                    evidence)
                matched_batches.add(batch["batch_id"])
                matched_credits.update(r["source_record_id"] for r in rows)
            continue
        # candidate scoring against non-UTR-matched credits
        candidates = []
        if cfg["enable_candidates"]:
            btoken = norm_token(batch["batch_id"])
            for c in credits:
                if c["source_record_id"] in matched_credits:
                    continue
                diff = abs(c["credit_amount_minor"] - batch["total_net_minor"])
                if diff > tol * 5:
                    continue
                dd = day_diff(batch["date"], c["value_date"])
                narr = norm_token(c.get("narration"))
                id_ev = 0.8 if btoken and btoken in narr else 0.0
                amount_ev = 1.0 if diff == 0 else (0.75 if diff <= tol else 0.3)
                conf = score(cfg, id_ev, amount_ev, date_evidence(dd, window),
                             narration=1.0 if id_ev else 0.4)
                candidates.append((conf, c, diff, dd))
            candidates.sort(key=lambda x: (-x[0], x[1]["source_record_id"]))
            candidates = candidates[:cfg["max_candidates"]]
        cand_evidence = [{"bank": c[1]["source_record_id"], "confidence": c[0],
                          "amount_diff_minor": c[2], "date_diff_days": c[3],
                          "narration": c[1].get("narration")} for c in candidates]
        if not candidates:
            deferred_missing.append((batch, [], 0.9))
            continue
        if len(candidates) > 1 and (candidates[0][0] - candidates[1][0]) < cfg["ambiguity_gap"]:
            ambiguous_batches.add(batch["batch_id"])
            ambiguous_credit_ids.update(c[1]["source_record_id"] for c in candidates)
            ctx.add_exception(
                "AMBIGUOUS_MATCH", "medium",
                batch["line_ids"][:3] + [c[1]["source_record_id"] for c in candidates],
                abs(batch["total_net_minor"]), candidates[0][0], "human_review",
                f"Settlement batch {batch['batch_id']} has {len(candidates)} plausible bank credits with similar "
                f"confidence ({', '.join(str(c[0]) for c in candidates)}). Narrations are ambiguous and no UTR link "
                "exists. The system refuses to force-match this record; it is routed to human review.",
                {"batch_id": batch["batch_id"], "batch_net_minor": batch["total_net_minor"],
                 "candidates": cand_evidence})
            continue
        top = candidates[0]
        if top[0] >= cfg["auto_threshold"]:
            ctx.add_match("settlement_bank", "fuzzy", batch["line_ids"], [top[1]["source_record_id"]],
                          top[0], "auto_matched",
                          {"batch_id": batch["batch_id"], "candidates": cand_evidence,
                           "selected": top[1]["source_record_id"]})
            matched_batches.add(batch["batch_id"])
            matched_credits.add(top[1]["source_record_id"])
        elif top[0] >= cfg["review_threshold"]:
            ctx.add_match("settlement_bank", "fuzzy", batch["line_ids"], [top[1]["source_record_id"]],
                          top[0], "review",
                          {"batch_id": batch["batch_id"], "candidates": cand_evidence,
                           "selected": top[1]["source_record_id"]})
            ctx.add_exception(
                "AMBIGUOUS_MATCH", "medium",
                batch["line_ids"][:3] + [top[1]["source_record_id"]],
                abs(batch["total_net_minor"]), top[0], "human_review",
                f"Best bank candidate for batch {batch['batch_id']} has confidence {top[0]}, inside the review band. "
                "Human confirmation required.", {"candidates": cand_evidence},
                match_index=len(ctx.matches) - 1)
        else:
            deferred_missing.append((batch, cand_evidence, top[0]))

    # Pass 5: controlled aggregate matching (many settlements -> one credit)
    if cfg["enable_aggregate"]:
        open_batches = [b for b in batches.values() if b["batch_id"] not in matched_batches]
        for c in credits:
            if c["source_record_id"] in matched_credits:
                continue
            narr = norm_token(c.get("narration"))
            found = None
            for size in (2, 3):
                for combo in combinations(sorted(open_batches, key=lambda b: b["batch_id"]), size):
                    if sum(b["total_net_minor"] for b in combo) == c["credit_amount_minor"] and \
                       all(day_diff(b["date"], c["value_date"]) <= cfg["date_window_days"] for b in combo):
                        found = combo
                        break
                if found:
                    break
            if not found:
                continue
            tokens_cited = all(norm_token(b["batch_id"]) in narr for b in found)
            id_ev = 0.8 if tokens_cited else 0.0
            conf = score(cfg, id_ev, 1.0, 1.0, narration=1.0 if tokens_cited else 0.4)
            decision = "auto_matched" if conf >= cfg["auto_threshold"] else "review"
            all_lines = [lid for b in found for lid in b["line_ids"]]
            m = ctx.add_match("settlement_bank", "many_to_one", all_lines, [c["source_record_id"]],
                              conf, decision,
                              {"aggregate_batches": [b["batch_id"] for b in found],
                               "component_settlement_lines": all_lines,
                               "batch_totals_minor": {b["batch_id"]: b["total_net_minor"] for b in found},
                               "bank_credit_minor": c["credit_amount_minor"],
                               "narration_cites_batches": tokens_cited,
                               "narration": c.get("narration")})
            if decision == "review":
                ctx.add_exception(
                    "AMBIGUOUS_MATCH", "medium", [c["source_record_id"]] + all_lines[:3],
                    c["credit_amount_minor"], conf, "human_review",
                    "Aggregate match found but the bank narration does not cite the settlement batches. "
                    "Human confirmation required.", m["evidence"], match_index=len(ctx.matches) - 1)
            matched_credits.add(c["source_record_id"])
            for b in found:
                matched_batches.add(b["batch_id"])
                open_batches = [ob for ob in open_batches if ob["batch_id"] != b["batch_id"]]

    for batch, cand_evidence, conf in deferred_missing:
        if batch["batch_id"] in matched_batches:
            continue
        ctx.add_exception(
            "MISSING_BANK_ENTRY", "high", batch["line_ids"],
            abs(batch["total_net_minor"]), conf, "human_review",
            f"Settlement batch {batch['batch_id']} (net {batch['total_net_minor']} paise, "
            f"UTR {batch['utr']}) has no corresponding bank credit above the review threshold. "
            "Review timing, account, or a missing statement page.",
            {"batch_id": batch["batch_id"], "utr": batch["utr"],
             "batch_net_minor": batch["total_net_minor"], "candidates": cand_evidence})

    for c in credits:
        if c["source_record_id"] not in matched_credits and c["source_record_id"] not in ambiguous_credit_ids:
            ctx.add_exception(
                "UNEXPECTED_ADJUSTMENT", "high", [c["source_record_id"]],
                c["credit_amount_minor"], 0.85, "human_review",
                f"Bank credit {c['source_record_id']} ({c['credit_amount_minor']} paise, narration "
                f"'{c.get('narration')}') cannot be explained by any settlement batch. Left unresolved.",
                {"narration": c.get("narration"), "value_date": c.get("value_date")},
                status="UNRESOLVED")
    return batches, matched_batches, matched_credits


def run_matching(orders, settlements, bank_entries, config=None):
    cfg = dict(DEFAULT_CONFIG)
    if config:
        cfg.update({k: v for k, v in config.items() if v is not None})
        if config.get("weights"):
            cfg["weights"] = {**DEFAULT_CONFIG["weights"], **config["weights"]}
    ctx = MatchContext()

    detect_duplicates(ctx, settlements, lambda r: (
        r.get("payment_id") or "", r.get("order_id") or "", r["gross_amount_minor"],
        r["net_amount_minor"], r["settlement_id"], r.get("adjustment_type") or ""), "Settlement")
    detect_duplicates(ctx, bank_entries, lambda r: (
        r.get("utr") or "", r.get("credit_amount_minor") or 0, r.get("debit_amount_minor") or 0,
        (r.get("value_date") or "")[:10], norm_token(r.get("narration"))), "Bank")
    detect_duplicates(ctx, orders, lambda r: (r["internal_order_id"],), "Order")

    active = [s for s in settlements if not s["is_duplicate"]]
    payment_lines = [s for s in active if not s.get("adjustment_type")]
    refund_lines = [s for s in active if (s.get("adjustment_type") or "").lower() == "refund"]
    other_adjustments = [s for s in active if s.get("adjustment_type") and
                         (s.get("adjustment_type") or "").lower() != "refund"]
    live_orders = [o for o in orders if not o["is_duplicate"]]

    matched_orders = match_lines_to_orders(ctx, cfg, payment_lines, live_orders)
    check_fee_tax(ctx, cfg, [l for l in payment_lines if l.get("_matched_order")])
    link_refunds(ctx, cfg, refund_lines, live_orders)
    for adj in other_adjustments:
        ctx.add_exception(
            "DISPUTE_ADJUSTMENT", "high", [adj["source_record_id"]],
            abs(adj["net_amount_minor"]), 0.9, "human_review",
            f"Settlement line {adj['source_record_id']} carries adjustment type "
            f"'{adj.get('adjustment_type')}'. Review required before it enters the close.",
            {"adjustment_type": adj.get("adjustment_type"), "net_minor": adj["net_amount_minor"]})

    batches, matched_batches, matched_credits = match_batches_to_bank(ctx, cfg, active, bank_entries)

    line_matched_ids = set()
    for m in ctx.matches:
        if m["plane"] in ("order_settlement", "refund") and m["decision"] in ("auto_matched", "approved"):
            line_matched_ids.update(m["source_a_ids"])
    eligible_settlements = len(active)
    eligible_credits = len([b for b in bank_entries if not b["is_duplicate"] and (b.get("credit_amount_minor") or 0) > 0])
    stats = {
        "rules_version": cfg["rules_version"],
        "config": {k: v for k, v in cfg.items()},
        "total_orders": len(orders), "total_settlement_lines": len(settlements),
        "total_bank_rows": len(bank_entries),
        "duplicate_records": len([r for r in settlements + bank_entries + orders if r["is_duplicate"]]),
        "eligible_settlement_lines": eligible_settlements,
        "eligible_bank_credits": eligible_credits,
        "auto_matched_settlement_lines": len(line_matched_ids),
        "matched_batches": len(matched_batches), "total_batches": len(batches),
        "matched_credits": len(matched_credits),
        "forced_match_count": 0,
    }
    return {"matches": ctx.matches, "exceptions": ctx.exceptions, "stats": stats}
