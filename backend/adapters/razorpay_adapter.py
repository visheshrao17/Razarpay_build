"""Optional Razorpay Test Mode adapter. The app must work without credentials (synthetic mode)."""
import os
import asyncio
import httpx

BASE_URL = "https://api.razorpay.com/v1"


def get_credentials():
    key_id = (os.environ.get("RAZORPAY_KEY_ID") or "").strip()
    key_secret = (os.environ.get("RAZORPAY_KEY_SECRET") or "").strip()
    if key_id and key_secret:
        return key_id, key_secret
    return None


def is_configured():
    return get_credentials() is not None


async def _get(path, params=None, retries=2):
    creds = get_credentials()
    if not creds:
        raise RuntimeError("Razorpay credentials not configured")
    last_error = None
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(f"{BASE_URL}{path}", params=params, auth=creds)
            if resp.status_code == 429:
                await asyncio.sleep(1 + attempt)
                last_error = "rate limited"
                continue
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            last_error = str(e)
            await asyncio.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"Razorpay API failed after retries: {last_error}")


async def fetch_settlements(count=100):
    return await _get("/settlements", {"count": min(count, 100)})


async def fetch_settlement_recon(year, month):
    return await _get("/settlements/recon/combined", {"year": year, "month": month})


def normalize_recon_items(items):
    """Map Razorpay settlement recon items into the internal settlement CSV row shape."""
    rows = []
    for idx, item in enumerate(items, start=1):
        rows.append({
            "source_record_id": f"rzp_settlement_{idx:04d}",
            "settlement_id": item.get("settlement_id") or "",
            "payment_id": item.get("payment_id") or (item.get("entity_id") if item.get("type") == "payment" else "") or "",
            "order_id": item.get("order_id") or "",
            "utr": item.get("settlement_utr") or item.get("utr") or "",
            "settlement_date": item.get("settled_at") or item.get("created_at") or "",
            "gross_amount_minor": item.get("amount") or 0,
            "fee_minor": item.get("fee") or 0,
            "tax_minor": item.get("tax") or 0,
            "net_amount_minor": item.get("credit") or ((item.get("amount") or 0) - (item.get("fee") or 0) - (item.get("tax") or 0)),
            "method": item.get("method") or "",
            "adjustment_type": item.get("type") if item.get("type") not in (None, "payment") else "",
            "currency": item.get("currency") or "INR",
        })
    return rows
