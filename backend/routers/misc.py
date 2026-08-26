import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import WebhookEvent, Run, Source
from auth import get_current_user
from adapters import razorpay_adapter
from services.audit import append_event

router = APIRouter(prefix="/api", tags=["misc"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "settlesense", "time": datetime.now(timezone.utc).isoformat()}


@router.get("/razorpay/status")
async def razorpay_status(user=Depends(get_current_user)):
    return {"configured": razorpay_adapter.is_configured(),
            "mode": "test" if razorpay_adapter.is_configured() else "synthetic_only",
            "note": "Synthetic fixtures remain the default. Configure RAZORPAY_KEY_ID and "
                    "RAZORPAY_KEY_SECRET in backend/.env to enable the Test Mode adapter."}


@router.post("/runs/{run_id}/sources/razorpay")
async def fetch_razorpay_source(run_id: str, year: int | None = None, month: int | None = None,
                                user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not razorpay_adapter.is_configured():
        raise HTTPException(status_code=400, detail={
            "code": "API_DATA_GAP",
            "message": "Razorpay Test Mode credentials are not configured. The app continues to work "
                       "in synthetic mode — register the seeded fixture instead."})
    run = (await db.execute(select(Run).where(Run.run_id == run_id))).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    now = datetime.now(timezone.utc)
    try:
        data = await razorpay_adapter.fetch_settlement_recon(year or now.year, month or now.month)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail={"code": "API_DATA_GAP", "message": str(e),
                                                     "fallback": "use the synthetic fixture"})
    items = data.get("items", [])
    rows = razorpay_adapter.normalize_recon_items(items)
    if not rows:
        raise HTTPException(status_code=400, detail={
            "code": "API_DATA_GAP",
            "message": "Razorpay Test Mode returned no settlement recon items for this period. "
                       "Use the synthetic fixture."})
    import csv as _csv
    import io as _io
    buf = _io.StringIO()
    w = _csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    from routers.runs import _ingest_source, _update_run_status_after_sources
    src = await _ingest_source(db, run, "settlement", "razorpay_test_mode_recon.csv",
                               buf.getvalue().encode())
    run.used_fixture = False
    await _update_run_status_after_sources(db, run)
    await db.commit()
    return {"run_id": run_id, "source": {"source_id": src.source_id, "rows": src.row_count,
                                         "valid": src.valid_rows, "invalid": src.invalid_rows},
            "disclosure": "Data fetched from Razorpay Test Mode. Bank statement and internal ledger "
                          "remain synthetic."}


@router.post("/webhooks/razorpay")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.json()
    event_id = request.headers.get("x-razorpay-event-id") or payload.get("event_id") or \
        f"evt_{uuid.uuid4().hex[:12]}"
    existing = (await db.execute(select(WebhookEvent).where(
        WebhookEvent.event_id == event_id))).scalar_one_or_none()
    if existing:
        return {"status": "duplicate_ignored", "event_id": event_id}
    db.add(WebhookEvent(event_id=event_id, event_type=payload.get("event", "unknown"),
                        payload=payload))
    await append_event(db, "external", "system", "webhook_received",
                       decision="stored",
                       evidence=[{"field": "event_id", "value": event_id},
                                 {"field": "event", "value": payload.get("event", "unknown")}],
                       outcome=f"Webhook {payload.get('event', 'unknown')} persisted and deduplicated")
    await db.commit()
    return {"status": "stored", "event_id": event_id}
