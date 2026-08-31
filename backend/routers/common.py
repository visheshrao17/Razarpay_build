from sqlalchemy import select
from models import OrderRecord, SettlementRecord, BankRecord


def order_dict(o: OrderRecord):
    return {"source_type": "internal_ledger", "source_record_id": o.source_record_id,
            "internal_order_id": o.internal_order_id, "razorpay_order_id": o.razorpay_order_id,
            "razorpay_payment_id": o.razorpay_payment_id, "order_date": o.order_date,
            "gross_amount_minor": o.gross_amount_minor, "refund_amount_minor": o.refund_amount_minor,
            "expected_net_amount_minor": o.expected_net_amount_minor, "currency": o.currency,
            "status": o.status, "customer_reference": o.customer_reference,
            "is_duplicate": o.is_duplicate, "duplicate_of": o.duplicate_of}


def settlement_dict(s: SettlementRecord):
    return {"source_type": "settlement", "source_record_id": s.source_record_id,
            "settlement_id": s.settlement_id, "payment_id": s.payment_id, "order_id": s.order_id,
            "utr": s.utr, "settlement_date": s.settlement_date,
            "gross_amount_minor": s.gross_amount_minor, "fee_minor": s.fee_minor,
            "tax_minor": s.tax_minor, "net_amount_minor": s.net_amount_minor,
            "method": s.method, "adjustment_type": s.adjustment_type, "currency": s.currency,
            "is_duplicate": s.is_duplicate, "duplicate_of": s.duplicate_of}


def bank_dict(b: BankRecord):
    return {"source_type": "bank_statement", "source_record_id": b.source_record_id,
            "bank_entry_id": b.bank_entry_id, "value_date": b.value_date, "utr": b.utr,
            "narration": b.narration, "credit_amount_minor": b.credit_amount_minor,
            "debit_amount_minor": b.debit_amount_minor, "account_reference": b.account_reference,
            "currency": b.currency, "is_duplicate": b.is_duplicate, "duplicate_of": b.duplicate_of}


async def load_run_records(db, run_id):
    orders = [(order_dict(o)) for o in
              (await db.execute(select(OrderRecord).where(OrderRecord.run_id == run_id))).scalars()]
    settlements = [(settlement_dict(s)) for s in
                   (await db.execute(select(SettlementRecord).where(SettlementRecord.run_id == run_id))).scalars()]
    banks = [(bank_dict(b)) for b in
             (await db.execute(select(BankRecord).where(BankRecord.run_id == run_id))).scalars()]
    return orders, settlements, banks


async def fetch_records_by_ids(db, run_id, record_ids):
    ids = list(set(record_ids))
    found = []
    for model, to_dict in ((OrderRecord, order_dict), (SettlementRecord, settlement_dict),
                           (BankRecord, bank_dict)):
        rows = (await db.execute(select(model).where(
            model.run_id == run_id, model.source_record_id.in_(ids)))).scalars()
        found.extend(to_dict(r) for r in rows)
    return found


def match_out(m):
    return {"match_id": m.match_id, "run_id": m.run_id, "plane": m.plane,
            "match_type": m.match_type, "source_a_ids": m.source_a_ids,
            "source_b_ids": m.source_b_ids, "confidence": m.confidence,
            "evidence": m.evidence, "decision": m.decision, "rules_version": m.rules_version,
            "reviewer_id": m.reviewer_id,
            "reviewed_at": m.reviewed_at.isoformat() if m.reviewed_at else None,
            "created_at": m.created_at.isoformat() if m.created_at else None}


def exception_out(e):
    return {"exception_id": e.exception_id, "run_id": e.run_id,
            "exception_code": e.exception_code, "severity": e.severity,
            "record_ids": e.record_ids, "amount_at_risk_minor": e.amount_at_risk_minor,
            "confidence": e.confidence, "status": e.status,
            "recommended_action": e.recommended_action, "explanation": e.explanation,
            "evidence": e.evidence, "ai_explanation": e.ai_explanation, "match_id": e.match_id,
            "resolved_by": e.resolved_by, "resolution_action": e.resolution_action,
            "resolution_note": e.resolution_note,
            "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
            "created_at": e.created_at.isoformat() if e.created_at else None}


def audit_out(a):
    return {"audit_event_id": a.audit_event_id, "seq": a.seq,
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            "run_id": a.run_id, "actor": a.actor, "step": a.step,
            "source_record_ids": a.source_record_ids, "exception_id": a.exception_id,
            "match_id": a.match_id, "rules_version": a.rules_version,
            "assumptions_version": a.assumptions_version, "model_version": a.model_version,
            "decision": a.decision, "confidence": a.confidence, "human_gate": a.human_gate,
            "evidence": a.evidence, "outcome": a.outcome,
            "previous_event_hash": a.previous_event_hash, "event_hash": a.event_hash}


def run_out(r, sources=None):
    return {"run_id": r.run_id, "name": r.name, "currency": r.currency, "status": r.status,
            "rules_version": r.rules_version, "assumptions_version": r.assumptions_version,
            "config": r.config, "source_checksums": r.source_checksums,
            "summary_metrics": r.summary_metrics, "ai_summary": r.ai_summary,
            "used_fixture": r.used_fixture,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "sources": sources or []}


def source_out(s):
    return {"source_id": s.source_id, "run_id": s.run_id, "source_type": s.source_type,
            "filename": s.filename, "checksum": s.checksum, "row_count": s.row_count,
            "valid_rows": s.valid_rows, "invalid_rows": s.invalid_rows, "status": s.status}
