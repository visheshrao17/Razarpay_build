"""Close report generation (markdown / json / csv) with a SHA-256 report hash."""
import csv
import hashlib
import io
import json
from datetime import datetime, timezone


def fmt_inr(minor):
    if minor is None:
        return "—"
    sign = "-" if minor < 0 else ""
    return f"{sign}₹{abs(minor) / 100:,.2f}"


def build_report(run, sources, matches, exceptions, reviewer_events, audit_range, metrics):
    return {
        "report_type": "SettleSense Close Report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run.run_id,
        "run_name": run.name,
        "run_status": run.status,
        "rules_version": run.rules_version,
        "assumptions_version": run.assumptions_version,
        "assumptions": run.config,
        "disclosure": ("This is an operational reconciliation control report over SYNTHETIC or Test Mode data. "
                       "It is not a tax filing, accounting posting, audit opinion or legal opinion. "
                       "Fee/tax/timing behaviour uses versioned demo assumptions."),
        "source_checksums": {s.source_type: {"filename": s.filename, "checksum": s.checksum,
                                             "rows": s.row_count, "valid": s.valid_rows,
                                             "invalid": s.invalid_rows} for s in sources},
        "metrics": metrics,
        "matched_records": [{
            "match_id": m.match_id, "plane": m.plane, "match_type": m.match_type,
            "decision": m.decision, "confidence": m.confidence,
            "source_a_ids": m.source_a_ids, "source_b_ids": m.source_b_ids,
            "reviewer_id": m.reviewer_id,
        } for m in matches],
        "exceptions": [{
            "exception_id": e.exception_id, "code": e.exception_code, "severity": e.severity,
            "status": e.status, "record_ids": e.record_ids,
            "amount_at_risk_minor": e.amount_at_risk_minor,
            "recommended_action": e.recommended_action, "explanation": e.explanation,
            "resolution_action": e.resolution_action, "resolved_by": e.resolved_by,
            "resolution_note": e.resolution_note,
        } for e in exceptions],
        "reviewer_actions": reviewer_events,
        "audit_event_range": audit_range,
    }


def report_hash(report_dict):
    canonical = json.dumps({k: v for k, v in report_dict.items() if k != "report_hash"},
                           sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def render_markdown(report):
    m = report["metrics"]
    lines = [
        f"# {report['report_type']}",
        "",
        f"- **Run:** `{report['run_id']}` — {report['run_name']} ({report['run_status']})",
        f"- **Generated:** {report['generated_at']}",
        f"- **Rules version:** {report['rules_version']} | **Assumptions version:** {report['assumptions_version']}",
        f"- **Report hash:** `{report['report_hash']}`",
        f"- **Audit event range:** {report['audit_event_range'].get('first')} → {report['audit_event_range'].get('last')} "
        f"({report['audit_event_range'].get('count')} events)",
        "",
        f"> {report['disclosure']}",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Records processed | {m.get('records_processed')} |",
        f"| Throughput (records/sec) | {m.get('throughput_records_per_second')} |",
        f"| Overall match rate | {m.get('overall_match_rate')} |",
        f"| Auto-match precision | {m.get('auto_match_precision')} |",
        f"| Auto-match recall | {m.get('auto_match_recall')} |",
        f"| Matched amount | {fmt_inr(m.get('matched_amount_minor'))} |",
        f"| Unresolved amount | {fmt_inr(m.get('unresolved_amount_minor'))} |",
        f"| Forced matches | {m.get('forced_match_count')} (target: 0) |",
        "",
        "## Assumptions used in this run (demo assumptions, versioned)",
        "",
        "```json",
        json.dumps(report["assumptions"], indent=2, default=str),
        "```",
        "",
        "## Source checksums",
        "",
        "| Source | File | SHA-256 | Rows | Valid | Invalid |",
        "|---|---|---|---:|---:|---:|",
    ]
    for st, s in report["source_checksums"].items():
        lines.append(f"| {st} | {s['filename']} | `{s['checksum'][:16]}…` | {s['rows']} | {s['valid']} | {s['invalid']} |")
    lines += ["", "## Exception summary", "", "| Code | Count |", "|---|---:|"]
    counts = {}
    for e in report["exceptions"]:
        counts[e["code"]] = counts.get(e["code"], 0) + 1
    for code, n in sorted(counts.items()):
        lines.append(f"| {code} | {n} |")
    lines += ["", "## Unresolved / open exceptions", ""]
    for e in report["exceptions"]:
        if e["status"] in ("OPEN", "IN_REVIEW", "UNRESOLVED"):
            lines.append(f"- **{e['exception_id']}** `{e['code']}` [{e['severity']}] {e['status']} — "
                         f"{fmt_inr(e['amount_at_risk_minor'])} at risk — records: {', '.join(e['record_ids'][:6])}")
            lines.append(f"  - {e['explanation']}")
    lines += ["", "## Reviewer actions", ""]
    if not report["reviewer_actions"]:
        lines.append("_No reviewer actions recorded._")
    for a in report["reviewer_actions"]:
        lines.append(f"- {a['timestamp']} — **{a['actor']}** {a['decision']} on {a.get('exception_id')} — {a['outcome']}")
    lines += ["", f"## Matched records ({len(report['matched_records'])})", "",
              "| Match | Plane | Type | Decision | Confidence | A | B |", "|---|---|---|---|---:|---|---|"]
    for mm in report["matched_records"]:
        lines.append(f"| {mm['match_id']} | {mm['plane']} | {mm['match_type']} | {mm['decision']} | "
                     f"{mm['confidence']} | {', '.join(mm['source_a_ids'][:3])}{'…' if len(mm['source_a_ids']) > 3 else ''} | "
                     f"{', '.join(mm['source_b_ids'][:3])} |")
    return "\n".join(lines)


def render_csv(report):
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["record_kind", "id", "plane_or_code", "type_or_severity", "decision_or_status",
                "confidence", "amount_minor", "a_ids", "b_or_record_ids", "note"])
    for m in report["matched_records"]:
        w.writerow(["match", m["match_id"], m["plane"], m["match_type"], m["decision"],
                    m["confidence"], "", "|".join(m["source_a_ids"]), "|".join(m["source_b_ids"]), ""])
    for e in report["exceptions"]:
        note = (e["explanation"] or "").replace("\n", " ")
        if note.startswith(("=", "+", "-", "@")):
            note = "'" + note
        w.writerow(["exception", e["exception_id"], e["code"], e["severity"], e["status"],
                    "", e["amount_at_risk_minor"], "", "|".join(e["record_ids"]), note])
    return out.getvalue()
