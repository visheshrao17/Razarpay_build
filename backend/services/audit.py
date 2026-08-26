"""Append-only audit trail with a per-run hash chain."""
import hashlib
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, desc
from models import AuditEvent


def _hash(payload: dict, prev_hash: str) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str) + prev_hash
    return hashlib.sha256(canonical.encode()).hexdigest()


def build_event(run_id, actor, step, prev_hash, *, source_record_ids=None, exception_id=None,
                match_id=None, rules_version="v1.0", assumptions_version="v1.0",
                model_version="none", decision="", confidence=None, human_gate=False,
                evidence=None, outcome=""):
    ts = datetime.now(timezone.utc)
    payload = {
        "run_id": run_id, "actor": actor, "step": step, "timestamp": ts.isoformat(),
        "source_record_ids": source_record_ids or [], "exception_id": exception_id,
        "match_id": match_id, "decision": decision, "confidence": confidence,
        "human_gate": human_gate, "evidence": evidence or [], "outcome": outcome,
        "rules_version": rules_version, "model_version": model_version,
    }
    event_hash = _hash(payload, prev_hash)
    return AuditEvent(
        audit_event_id=f"audit_{uuid.uuid4().hex[:12]}", timestamp=ts, run_id=run_id,
        actor=actor, step=step, source_record_ids=source_record_ids or [],
        exception_id=exception_id, match_id=match_id, rules_version=rules_version,
        assumptions_version=assumptions_version, model_version=model_version,
        decision=decision, confidence=confidence, human_gate=human_gate,
        evidence=evidence or [], outcome=outcome,
        previous_event_hash=prev_hash, event_hash=event_hash,
    ), event_hash


async def last_hash(db, run_id) -> str:
    res = await db.execute(select(AuditEvent.event_hash).where(AuditEvent.run_id == run_id)
                           .order_by(desc(AuditEvent.seq)).limit(1))
    row = res.scalar_one_or_none()
    return row or "genesis"


async def append_event(db, run_id, actor, step, **kwargs):
    prev = await last_hash(db, run_id)
    event, _ = build_event(run_id, actor, step, prev, **kwargs)
    db.add(event)
    return event
