import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import (Run, Source, InvalidRecord, OrderRecord, SettlementRecord, BankRecord,
                    PaymentRecord, MatchDecision, ExceptionRecord, AuditEvent)
from auth import get_current_user
from services import ingestion
from services.matching import run_matching, DEFAULT_CONFIG
from services.evaluation import evaluate, baseline_comparison
from services.audit import build_event, last_hash, append_event
from services import report as report_svc
from routers.common import (load_run_records, run_out, source_out, match_out, exception_out,
                            audit_out, fetch_records_by_ids)
from taxonomy import SEVERITY_ORDER

router = APIRouter(prefix="/api/runs", tags=["runs"])
DATA_DIR = Path(os.environ.get("DATA_DIR", "/app/data"))

RECORD_MODELS = {"settlement": SettlementRecord, "internal_ledger": OrderRecord,
                 "bank_statement": BankRecord, "payments": PaymentRecord}


class CreateRunRequest(BaseModel):
    name: str
    currency: str = "INR"
    config: dict | None = None


async def _get_run(db, run_id) -> Run:
    run = (await db.execute(select(Run).where(Run.run_id == run_id))).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run


@router.post("")
async def create_run(body: CreateRunRequest, user=Depends(get_current_user),
                     db: AsyncSession = Depends(get_db)):
    count = (await db.execute(select(func.count(Run.run_id)))).scalar() or 0
    run_id = f"run_{count + 1:04d}"
    config = dict(DEFAULT_CONFIG)
    if body.config:
        for k in ("amount_tolerance_minor", "date_window_days", "auto_threshold",
                  "review_threshold", "fee_rate_bps", "tax_on_fee_bps", "ai_model"):
            if k in body.config and body.config[k] is not None:
                config[k] = body.config[k]
    run = Run(run_id=run_id, name=body.name, currency=body.currency, status="CREATED",
              config=config, rules_version=config["rules_version"],
              assumptions_version=config["assumptions_version"])
    db.add(run)
    await append_event(db, run_id, "system", "run_created", decision="created",
                       outcome=f"Run '{body.name}' created by {user.email}")
    await db.commit()
    return run_out(run)


@router.get("")
async def list_runs(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    runs = (await db.execute(select(Run).order_by(Run.created_at.desc()))).scalars().all()
    out = []
    for r in runs:
        sources = (await db.execute(select(Source).where(Source.run_id == r.run_id))).scalars().all()
        out.append(run_out(r, [source_out(s) for s in sources]))
    return out


@router.get("/{run_id}")
async def get_run(run_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    run = await _get_run(db, run_id)
    sources = (await db.execute(select(Source).where(Source.run_id == run_id))).scalars().all()
    return run_out(run, [source_out(s) for s in sources])


async def _ingest_source(db, run: Run, source_type: str, filename: str, content: bytes):
    if source_type not in ingestion.NORMALIZERS:
        raise HTTPException(status_code=400, detail=f"Unknown source_type '{source_type}'")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (limit 10 MB)")
    rows = ingestion.parse_csv_bytes(content)
    valid, invalid = ingestion.validate_and_normalize(source_type, rows)
    checksum = ingestion.checksum_bytes(content)

    model = RECORD_MODELS[source_type]
    await db.execute(delete(model).where(model.run_id == run.run_id))
    await db.execute(delete(InvalidRecord).where(InvalidRecord.run_id == run.run_id,
                                                 InvalidRecord.source_type == source_type))
    await db.execute(delete(Source).where(Source.run_id == run.run_id,
                                          Source.source_type == source_type))
    db.add_all([model(run_id=run.run_id, **rec) for rec in valid])
    db.add_all([InvalidRecord(run_id=run.run_id, source_type=source_type, **inv) for inv in invalid])
    src = Source(source_id=f"src_{uuid.uuid4().hex[:10]}", run_id=run.run_id,
                 source_type=source_type, filename=filename, checksum=checksum,
                 row_count=len(rows), valid_rows=len(valid), invalid_rows=len(invalid),
                 status="LOADED")
    db.add(src)
    checksums = dict(run.source_checksums or {})
    checksums[source_type] = checksum
    run.source_checksums = checksums
    await append_event(db, run.run_id, "system", "source_registered",
                       decision="loaded",
                       evidence=[{"field": "checksum", "value_hash": checksum},
                                 {"field": "rows", "value": len(rows)}],
                       outcome=f"Source {source_type} ({filename}): {len(valid)} valid, "
                               f"{len(invalid)} invalid rows")
    return src


async def _update_run_status_after_sources(db, run):
    types = {s.source_type for s in
             (await db.execute(select(Source).where(Source.run_id == run.run_id))).scalars()}
    run.status = "READY" if all(t in types for t in ingestion.REQUIRED_SOURCES) else "INGESTING"


@router.post("/{run_id}/sources/fixture")
async def register_fixtures(run_id: str, user=Depends(get_current_user),
                            db: AsyncSession = Depends(get_db)):
    run = await _get_run(db, run_id)
    if run.status in ("RUNNING",):
        raise HTTPException(status_code=409, detail="Run is executing")
    results = []
    for source_type, filename in ingestion.FIXTURE_FILES.items():
        path = DATA_DIR / "generated" / filename
        if not path.exists():
            raise HTTPException(status_code=400,
                                detail=f"Fixture {filename} not found. Run scripts/generate_dataset.py first.")
        src = await _ingest_source(db, run, source_type, filename, path.read_bytes())
        results.append(source_out(src))
    run.used_fixture = True
    await _update_run_status_after_sources(db, run)
    await db.commit()
    return {"run_id": run_id, "status": run.status, "sources": results}


@router.post("/{run_id}/sources")
async def upload_source(run_id: str, source_type: str = Form(...), file: UploadFile = File(...),
                        user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    run = await _get_run(db, run_id)
    if run.status in ("RUNNING",):
        raise HTTPException(status_code=409, detail="Run is executing")
    content = await file.read()
    src = await _ingest_source(db, run, source_type, file.filename or f"{source_type}.csv", content)
    await _update_run_status_after_sources(db, run)
    await db.commit()
    return source_out(src)


@router.post("/{run_id}/execute")
async def execute_run(run_id: str, force: bool = Query(False), user=Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    run = await _get_run(db, run_id)
    if run.status == "COMPLETED" and not force:
        return {"run_id": run_id, "status": run.status, "idempotent": True,
                "summary_metrics": run.summary_metrics}
    if run.status not in ("READY", "COMPLETED", "REVIEWING"):
        raise HTTPException(status_code=409,
                            detail=f"Run is {run.status}; register settlement, bank_statement and "
                                   "internal_ledger sources first")
    run.status = "RUNNING"
    await db.commit()
    try:
        t0 = time.perf_counter()
        orders, settlements, banks = await load_run_records(db, run_id)
        result = run_matching(orders, settlements, banks, run.config)
        elapsed = time.perf_counter() - t0

        await db.execute(delete(MatchDecision).where(MatchDecision.run_id == run_id))
        await db.execute(delete(ExceptionRecord).where(ExceptionRecord.run_id == run_id))

        # persist duplicate flags
        for recs, model in ((orders, OrderRecord), (settlements, SettlementRecord), (banks, BankRecord)):
            for r in recs:
                if r.get("is_duplicate"):
                    row = (await db.execute(select(model).where(
                        model.run_id == run_id,
                        model.source_record_id == r["source_record_id"]))).scalar_one()
                    row.is_duplicate = True
                    row.duplicate_of = r.get("duplicate_of")

        prev_hash = await last_hash(db, run_id)
        events = []

        def chain(actor, step, **kw):
            nonlocal prev_hash
            ev, prev_hash = build_event(run_id, actor, step, prev_hash,
                                        rules_version=run.rules_version,
                                        assumptions_version=run.assumptions_version, **kw)
            events.append(ev)
            return ev

        match_rows, match_index_to_id = [], {}
        for idx, m in enumerate(result["matches"]):
            mid = f"match_{uuid.uuid4().hex[:10]}"
            match_index_to_id[idx] = mid
            match_rows.append(MatchDecision(
                match_id=mid, run_id=run_id, plane=m["plane"], match_type=m["match_type"],
                source_a_ids=m["source_a_ids"], source_b_ids=m["source_b_ids"],
                confidence=m["confidence"], evidence=m["evidence"], decision=m["decision"],
                rules_version=m["rules_version"]))
            chain("matcher", "match_decision", match_id=mid,
                  source_record_ids=m["source_a_ids"][:5] + m["source_b_ids"][:5],
                  decision=m["decision"], confidence=m["confidence"],
                  evidence=[{"field": k, "value": str(v)[:120]} for k, v in
                            list(m["evidence"].items())[:6]],
                  outcome=f"{m['plane']} {m['match_type']} match ({m['decision']})")
        db.add_all(match_rows)

        exception_rows = []
        for e in result["exceptions"]:
            eid = f"exc_{uuid.uuid4().hex[:10]}"
            linked_match = match_index_to_id.get(e.get("match_index"))
            exception_rows.append(ExceptionRecord(
                exception_id=eid, run_id=run_id, exception_code=e["exception_code"],
                severity=e["severity"], record_ids=e["record_ids"],
                amount_at_risk_minor=e["amount_at_risk_minor"], confidence=e["confidence"],
                status=e["status"], recommended_action=e["recommended_action"],
                explanation=e["explanation"], evidence=e["evidence"], match_id=linked_match))
            chain("matcher", "exception_created", exception_id=eid, match_id=linked_match,
                  source_record_ids=e["record_ids"][:8], decision=e["status"].lower(),
                  confidence=e["confidence"],
                  outcome=f"{e['exception_code']} [{e['severity']}]: {e['explanation'][:180]}")

        # INVALID_SOURCE exceptions from ingestion validation
        invalids = (await db.execute(select(InvalidRecord).where(
            InvalidRecord.run_id == run_id))).scalars().all()
        for inv in invalids:
            eid = f"exc_{uuid.uuid4().hex[:10]}"
            rec_id = (inv.raw or {}).get("source_record_id") or f"{inv.source_type}_row_{inv.row_number}"
            exception_rows.append(ExceptionRecord(
                exception_id=eid, run_id=run_id, exception_code="INVALID_SOURCE",
                severity="medium", record_ids=[rec_id], amount_at_risk_minor=0, confidence=1.0,
                status="OPEN", recommended_action="reject_row",
                explanation=f"Row {inv.row_number} of {inv.source_type} failed validation and was "
                            f"excluded from matching: {'; '.join(inv.errors)}. Raw value preserved.",
                evidence={"validation_errors": inv.errors, "raw": inv.raw}))
            chain("matcher", "exception_created", exception_id=eid, source_record_ids=[rec_id],
                  decision="open", outcome=f"INVALID_SOURCE: {'; '.join(inv.errors)[:160]}")
        db.add_all(exception_rows)

        # metrics
        stats = result["stats"]
        line_net = {s["source_record_id"]: s["net_amount_minor"] for s in settlements}
        credit_amt = {b["source_record_id"]: b.get("credit_amount_minor") or 0 for b in banks}
        auto_line_ids, auto_credit_ids = set(), set()
        for m in result["matches"]:
            if m["decision"] == "auto_matched":
                if m["plane"] in ("order_settlement", "refund"):
                    auto_line_ids.update(m["source_a_ids"])
                elif m["plane"] == "settlement_bank":
                    auto_credit_ids.update(m["source_b_ids"])
        active_lines = [s for s in settlements if not s.get("is_duplicate")]
        credits = [b for b in banks if not b.get("is_duplicate") and (b.get("credit_amount_minor") or 0) > 0]
        matched_amount = sum(abs(line_net[i]) for i in auto_line_ids)
        unresolved_amount = (sum(abs(s["net_amount_minor"]) for s in active_lines
                                 if s["source_record_id"] not in auto_line_ids)
                             + sum(credit_amt[c["source_record_id"]] for c in credits
                                   if c["source_record_id"] not in auto_credit_ids))
        records_processed = len(orders) + len(settlements) + len(banks) + len(invalids)
        eligible = stats["eligible_settlement_lines"] + stats["eligible_bank_credits"]
        matched_count = len(auto_line_ids) + len(auto_credit_ids)
        exception_counts = {}
        for e in result["exceptions"]:
            exception_counts[e["exception_code"]] = exception_counts.get(e["exception_code"], 0) + 1
        if invalids:
            exception_counts["INVALID_SOURCE"] = exception_counts.get("INVALID_SOURCE", 0) + len(invalids)
        match_type_counts = {}
        for m in result["matches"]:
            key = f"{m['plane']}:{m['match_type']}:{m['decision']}"
            match_type_counts[key] = match_type_counts.get(key, 0) + 1

        metrics = {
            "records_processed": records_processed,
            "elapsed_seconds": round(elapsed, 3),
            "throughput_records_per_second": round(records_processed / elapsed, 1) if elapsed else None,
            "eligible_records": eligible,
            "auto_matched_records": matched_count,
            "overall_match_rate": round(matched_count / eligible, 4) if eligible else None,
            "review_records": len([m for m in result["matches"] if m["decision"] == "review"]),
            "review_rate": round(len([m for m in result["matches"] if m["decision"] == "review"]) / eligible, 4) if eligible else None,
            "gross_amount_minor": sum(o["gross_amount_minor"] for o in orders),
            "matched_amount_minor": matched_amount,
            "unresolved_amount_minor": unresolved_amount,
            "duplicate_records": stats["duplicate_records"],
            "invalid_rows": len(invalids),
            "exception_count": len(result["exceptions"]) + len(invalids),
            "exception_counts": exception_counts,
            "match_type_counts": match_type_counts,
            "forced_match_count": 0,
            "auto_match_precision": None,
            "auto_match_recall": None,
            "rules_version": run.rules_version,
            "assumptions_version": run.assumptions_version,
        }
        gt_path = DATA_DIR / "generated" / "ground_truth.json"
        if run.used_fixture and gt_path.exists():
            gt = json.loads(gt_path.read_text())
            ev = evaluate(result["matches"], gt)
            metrics.update({"auto_match_precision": ev["auto_match_precision"],
                            "auto_match_recall": ev["auto_match_recall"],
                            "dataset_version": ev["dataset_version"],
                            "evaluation": ev})

        chain("system", "run_executed", decision="completed", confidence=None,
              outcome=f"Reconciliation completed: {records_processed} records, "
                      f"{len(result['matches'])} match decisions, "
                      f"{len(result['exceptions']) + len(invalids)} exceptions, "
                      f"match rate {metrics['overall_match_rate']}, 0 forced matches")
        db.add_all(events)
        run.summary_metrics = metrics
        run.status = "COMPLETED"
        run.completed_at = datetime.now(timezone.utc)
        await db.commit()
        return {"run_id": run_id, "status": run.status, "summary_metrics": metrics}
    except Exception:
        await db.rollback()
        run2 = await _get_run(db, run_id)
        run2.status = "FAILED"
        await append_event(db, run_id, "system", "run_failed", decision="failed",
                           outcome="Run failed; committed audit events preserved")
        await db.commit()
        raise


@router.get("/{run_id}/summary")
async def run_summary(run_id: str, db: AsyncSession = Depends(get_db),
                      user=Depends(get_current_user)):
    run = await _get_run(db, run_id)
    exceptions = (await db.execute(select(ExceptionRecord).where(
        ExceptionRecord.run_id == run_id))).scalars().all()
    status_counts, sev_counts, code_counts = {}, {}, {}
    open_amount = 0
    for e in exceptions:
        status_counts[e.status] = status_counts.get(e.status, 0) + 1
        sev_counts[e.severity] = sev_counts.get(e.severity, 0) + 1
        code_counts[e.exception_code] = code_counts.get(e.exception_code, 0) + 1
        if e.status in ("OPEN", "IN_REVIEW", "UNRESOLVED"):
            open_amount += e.amount_at_risk_minor or 0
    matches = (await db.execute(select(MatchDecision.decision, func.count())
                                .where(MatchDecision.run_id == run_id)
                                .group_by(MatchDecision.decision))).all()
    return {"run_id": run_id, "status": run.status, "summary_metrics": run.summary_metrics,
            "ai_summary": run.ai_summary, "config": run.config,
            "exception_status_counts": status_counts, "exception_severity_counts": sev_counts,
            "exception_code_counts": code_counts,
            "open_exception_amount_minor": open_amount,
            "match_decision_counts": {d: c for d, c in matches}}


@router.post("/{run_id}/ai-summary")
async def generate_run_ai_summary(run_id: str, db: AsyncSession = Depends(get_db),
                                  user=Depends(get_current_user)):
    run = await _get_run(db, run_id)
    if not run.summary_metrics:
        raise HTTPException(status_code=400, detail="Run must be executed first")
    
    # Check if we already have it
    if run.ai_summary and not run.ai_summary.get("_fallback"):
        return {"run_id": run_id, "ai_summary": run.ai_summary}

    exceptions = (await db.execute(select(ExceptionRecord).where(
        ExceptionRecord.run_id == run_id))).scalars().all()
    
    exception_summary = {
        "status_counts": {}, "severity_counts": {}, "code_counts": {}
    }
    sample_exceptions = []
    
    for e in exceptions:
        exception_summary["status_counts"][e.status] = exception_summary["status_counts"].get(e.status, 0) + 1
        exception_summary["severity_counts"][e.severity] = exception_summary["severity_counts"].get(e.severity, 0) + 1
        exception_summary["code_counts"][e.exception_code] = exception_summary["code_counts"].get(e.exception_code, 0) + 1
        
        if len(sample_exceptions) < 20 and e.status in ("OPEN", "IN_REVIEW", "UNRESOLVED"):
            sample_exceptions.append({
                "exception_code": e.exception_code,
                "severity": e.severity,
                "amount_at_risk_minor": e.amount_at_risk_minor,
                "explanation": e.explanation
            })

    from services.ai_summary import generate_run_summary
    summary_result, model_version = await generate_run_summary(
        run.summary_metrics, exception_summary, sample_exceptions
    )
    
    run.ai_summary = summary_result
    await db.commit()
    
    return {"run_id": run_id, "ai_summary": summary_result}


@router.get("/{run_id}/matches")
async def list_matches(run_id: str, decision: str | None = None, plane: str | None = None,
                       match_type: str | None = None, limit: int = 200, offset: int = 0,
                       db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    q = select(MatchDecision).where(MatchDecision.run_id == run_id)
    if decision:
        q = q.where(MatchDecision.decision == decision)
    if plane:
        q = q.where(MatchDecision.plane == plane)
    if match_type:
        q = q.where(MatchDecision.match_type == match_type)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    rows = (await db.execute(q.order_by(MatchDecision.confidence.desc(), MatchDecision.match_id)
                             .limit(limit).offset(offset))).scalars().all()
    return {"total": total, "matches": [match_out(m) for m in rows]}


@router.get("/{run_id}/matches/{match_id}")
async def match_detail(run_id: str, match_id: str, db: AsyncSession = Depends(get_db),
                       user=Depends(get_current_user)):
    m = (await db.execute(select(MatchDecision).where(
        MatchDecision.run_id == run_id, MatchDecision.match_id == match_id))).scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Match not found")
    records = await fetch_records_by_ids(db, run_id, m.source_a_ids + m.source_b_ids)
    exceptions = (await db.execute(select(ExceptionRecord).where(
        ExceptionRecord.run_id == run_id, ExceptionRecord.match_id == match_id))).scalars().all()
    audits = (await db.execute(select(AuditEvent).where(
        AuditEvent.run_id == run_id, AuditEvent.match_id == match_id)
        .order_by(AuditEvent.seq))).scalars().all()
    return {"match": match_out(m), "records": records,
            "exceptions": [exception_out(e) for e in exceptions],
            "audit_events": [audit_out(a) for a in audits]}


@router.get("/{run_id}/exceptions")
async def list_exceptions(run_id: str, code: str | None = None, severity: str | None = None,
                          status: str | None = None, limit: int = 300, offset: int = 0,
                          db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    q = select(ExceptionRecord).where(ExceptionRecord.run_id == run_id)
    if code:
        q = q.where(ExceptionRecord.exception_code == code)
    if severity:
        q = q.where(ExceptionRecord.severity == severity)
    if status:
        q = q.where(ExceptionRecord.status == status)
    rows = (await db.execute(q)).scalars().all()
    rows.sort(key=lambda e: (SEVERITY_ORDER.get(e.severity, 9), -(e.amount_at_risk_minor or 0)))
    total = len(rows)
    return {"total": total, "exceptions": [exception_out(e) for e in rows[offset:offset + limit]]}


@router.get("/{run_id}/audit")
async def list_audit(run_id: str, actor: str | None = None, step: str | None = None,
                     limit: int = 500, offset: int = 0,
                     db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    q = select(AuditEvent).where(AuditEvent.run_id == run_id)
    if actor:
        q = q.where(AuditEvent.actor == actor)
    if step:
        q = q.where(AuditEvent.step == step)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    rows = (await db.execute(q.order_by(AuditEvent.seq.desc()).limit(limit).offset(offset))).scalars().all()
    return {"total": total, "events": [audit_out(a) for a in rows]}


@router.get("/{run_id}/evaluation")
async def run_evaluation(run_id: str, db: AsyncSession = Depends(get_db),
                         user=Depends(get_current_user)):
    run = await _get_run(db, run_id)
    gt_path = DATA_DIR / "generated" / "ground_truth.json"
    if not run.used_fixture or not gt_path.exists():
        raise HTTPException(status_code=400,
                            detail="Baseline evaluation requires the seeded fixture with independent ground truth")
    gt = json.loads(gt_path.read_text())
    orders, settlements, banks = await load_run_records(db, run_id)
    comparison = baseline_comparison(orders, settlements, banks, gt, run.config)
    return {"run_id": run_id, "dataset_version": gt.get("dataset_version"),
            "baselines": comparison,
            "note": "Same seeded dataset evaluated against three matcher configurations. "
                    "Ground truth was generated independently of the matcher."}


@router.get("/{run_id}/report")
async def get_report(run_id: str, format: str = Query("json", pattern="^(json|markdown|csv)$"),
                     db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    run = await _get_run(db, run_id)
    if not run.summary_metrics:
        raise HTTPException(status_code=400, detail="Execute the run before generating a report")
    sources = (await db.execute(select(Source).where(Source.run_id == run_id))).scalars().all()
    matches = (await db.execute(select(MatchDecision).where(MatchDecision.run_id == run_id)
                                .order_by(MatchDecision.match_id))).scalars().all()
    exceptions = (await db.execute(select(ExceptionRecord).where(ExceptionRecord.run_id == run_id))).scalars().all()
    exceptions.sort(key=lambda e: (SEVERITY_ORDER.get(e.severity, 9), -(e.amount_at_risk_minor or 0)))
    reviewer_rows = (await db.execute(select(AuditEvent).where(
        AuditEvent.run_id == run_id, AuditEvent.human_gate == True)  # noqa: E712
        .order_by(AuditEvent.seq))).scalars().all()
    reviewer_events = [{"timestamp": a.timestamp.isoformat(), "actor": a.actor,
                        "decision": a.decision, "exception_id": a.exception_id,
                        "outcome": a.outcome} for a in reviewer_rows]
    first = (await db.execute(select(AuditEvent).where(AuditEvent.run_id == run_id)
                              .order_by(AuditEvent.seq).limit(1))).scalar_one_or_none()
    last = (await db.execute(select(AuditEvent).where(AuditEvent.run_id == run_id)
                             .order_by(AuditEvent.seq.desc()).limit(1))).scalar_one_or_none()
    count = (await db.execute(select(func.count()).select_from(AuditEvent)
                              .where(AuditEvent.run_id == run_id))).scalar()
    audit_range = {"first": first.audit_event_id if first else None,
                   "last": last.audit_event_id if last else None, "count": count}
    rep = report_svc.build_report(run, sources, matches, exceptions, reviewer_events,
                                  audit_range, run.summary_metrics)
    rep["report_hash"] = report_svc.report_hash(rep)
    await append_event(db, run_id, "system", "report_generated", decision="generated",
                       evidence=[{"field": "report_hash", "value_hash": rep["report_hash"]},
                                 {"field": "format", "value": format}],
                       outcome=f"Close report generated ({format}), hash {rep['report_hash'][:16]}…")
    if run.status == "COMPLETED":
        run.status = "REVIEWING"
    await db.commit()
    if format == "markdown":
        return PlainTextResponse(report_svc.render_markdown(rep), media_type="text/markdown")
    if format == "csv":
        return Response(report_svc.render_csv(rep), media_type="text/csv",
                        headers={"Content-Disposition": f"attachment; filename={run_id}_close_report.csv"})
    return rep
