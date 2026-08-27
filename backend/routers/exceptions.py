from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import ExceptionRecord, MatchDecision, Run
from auth import get_current_user
from services.audit import append_event
from services.ai_explain import generate_explanation, ALLOWED_MODELS, DEFAULT_MODEL, PROMPT_VERSION
from routers.common import exception_out, fetch_records_by_ids, match_out
from taxonomy import RESOLUTION_ACTIONS

router = APIRouter(prefix="/api/exceptions", tags=["exceptions"])

ACTION_TO_STATUS = {
    "approve_match": "RESOLVED",
    "reject_match": "REJECTED",
    "split_match": "IN_REVIEW",
    "merge_match": "RESOLVED",
    "request_data": "IN_REVIEW",
    "leave_unresolved": "UNRESOLVED",
}


async def _get_exception(db, exception_id) -> ExceptionRecord:
    e = (await db.execute(select(ExceptionRecord).where(
        ExceptionRecord.exception_id == exception_id))).scalar_one_or_none()
    if not e:
        raise HTTPException(status_code=404, detail=f"Exception {exception_id} not found")
    return e


@router.get("/{exception_id}")
async def exception_detail(exception_id: str, db: AsyncSession = Depends(get_db),
                           user=Depends(get_current_user)):
    e = await _get_exception(db, exception_id)
    records = await fetch_records_by_ids(db, e.run_id, e.record_ids)
    match = None
    if e.match_id:
        m = (await db.execute(select(MatchDecision).where(
            MatchDecision.match_id == e.match_id))).scalar_one_or_none()
        match = match_out(m) if m else None
    return {"exception": exception_out(e), "records": records, "match": match}


class ResolveRequest(BaseModel):
    action: str
    note: str = ""
    match_id: str | None = None


@router.post("/{exception_id}/resolve")
async def resolve_exception(exception_id: str, body: ResolveRequest,
                            db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    if body.action not in RESOLUTION_ACTIONS:
        raise HTTPException(status_code=400,
                            detail=f"Action must be one of {RESOLUTION_ACTIONS}")
    if not body.note.strip():
        raise HTTPException(status_code=400,
                            detail="A reviewer note is required for the audit log")
    e = await _get_exception(db, exception_id)
    previous_status = e.status
    new_status = ACTION_TO_STATUS[body.action]
    now = datetime.now(timezone.utc)
    e.status = new_status
    e.resolved_by = user.email
    e.resolved_at = now
    e.resolution_action = body.action
    e.resolution_note = body.note

    match_update = None
    target_match_id = body.match_id or e.match_id
    if target_match_id:
        m = (await db.execute(select(MatchDecision).where(
            MatchDecision.match_id == target_match_id))).scalar_one_or_none()
        if m:
            if body.action in ("approve_match", "merge_match"):
                m.decision = "approved"
            elif body.action in ("reject_match", "split_match"):
                m.decision = "rejected"
            m.reviewer_id = user.email
            m.reviewed_at = now
            match_update = {"match_id": m.match_id, "decision": m.decision}

    event = await append_event(
        db, e.run_id, "reviewer", "review",
        exception_id=exception_id, match_id=target_match_id,
        source_record_ids=e.record_ids[:8], decision=body.action, human_gate=True,
        evidence=[{"field": "previous_status", "value": previous_status},
                  {"field": "new_status", "value": new_status},
                  {"field": "note", "value": body.note[:300]}],
        outcome=f"{user.email} ({user.role}) applied {body.action}: {previous_status} → {new_status}. "
                f"Note: {body.note[:200]}")
    await db.commit()
    return {"exception_id": exception_id, "previous_status": previous_status,
            "new_status": new_status, "reviewer_id": user.email,
            "timestamp": now.isoformat(), "audit_event_id": event.audit_event_id,
            "match_update": match_update, "exception": exception_out(e)}


class ExplainRequest(BaseModel):
    model: str | None = None


@router.post("/{exception_id}/explain")
async def explain_exception(exception_id: str, body: ExplainRequest = ExplainRequest(),
                            db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    e = await _get_exception(db, exception_id)
    run = (await db.execute(select(Run).where(Run.run_id == e.run_id))).scalar_one()
    model_key = body.model or (run.config or {}).get("ai_model") or DEFAULT_MODEL
    if body.model and body.model not in ALLOWED_MODELS:
        raise HTTPException(status_code=400,
                            detail=f"Model must be one of {list(ALLOWED_MODELS)}")
    records = await fetch_records_by_ids(db, e.run_id, e.record_ids)
    exception_payload = exception_out(e)
    result, model_version = await generate_explanation(exception_payload, records, model_key)
    e.ai_explanation = result
    validation = "fallback" if result.get("_fallback") else "valid"
    await append_event(
        db, e.run_id, "ai", "explanation",
        exception_id=exception_id, source_record_ids=result.get("evidence_ids", [])[:8],
        model_version=f"{model_version} (prompt {PROMPT_VERSION})",
        decision="abstained" if result.get("abstain") else "explained",
        confidence=float(result.get("confidence") or 0),
        evidence=[{"field": "validation", "value": validation},
                  {"field": "evidence_ids", "value": ", ".join(result.get("evidence_ids", [])[:6])}],
        outcome=(result.get("summary") or "")[:250])
    await db.commit()
    return {"exception_id": exception_id, "ai_explanation": result,
            "model_version": model_version, "validation": validation}
