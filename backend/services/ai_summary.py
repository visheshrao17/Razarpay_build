"""LLM-powered run-level summary generation for reconciliation insights."""
import asyncio
import json
import os

AI_SUMMARY_TIMEOUT = 60

SUMMARY_SYSTEM_PROMPT = """You are a financial operations analyst inside SettleSense, a settlement reconciliation system.
You are given the complete results of a reconciliation run: metrics, exception counts by category, severity breakdown, and individual exception details.

Your job: produce a clear, actionable executive summary of the reconciliation run covering:
1. **overall_assessment**: A 2-3 sentence executive summary of the run's health
2. **key_findings**: Array of 3-6 key findings (each a short sentence)
3. **common_root_causes**: Array of identified root causes with frequency — explain WHY exceptions occurred
4. **risk_analysis**: Brief assessment of financial risk from unresolved exceptions
5. **recommendations**: Array of 3-5 prioritized recommendations for the operations team
6. **data_quality_notes**: Any observations about data quality issues in the source files
7. **confidence**: Your confidence in this analysis (0-1)

STRICT RULES:
- Base ALL findings on the provided evidence only. Never invent data.
- Amounts are in integer paise (INR minor units). Convert to INR for display (divide by 100).
- Focus on patterns across exceptions, not individual exceptions.
- Be specific: cite exception codes, amounts, and counts.
- Keep language professional and concise — this is for finance operations teams.

Return ONLY a JSON object (no markdown fences, no commentary) with the fields above."""


def build_summary_payload(metrics, exception_summary, exceptions_sample):
    """Build a compact payload for the LLM summarization."""
    return {
        "metrics": {
            "records_processed": metrics.get("records_processed"),
            "overall_match_rate": metrics.get("overall_match_rate"),
            "auto_matched_records": metrics.get("auto_matched_records"),
            "eligible_records": metrics.get("eligible_records"),
            "matched_amount_minor": metrics.get("matched_amount_minor"),
            "unresolved_amount_minor": metrics.get("unresolved_amount_minor"),
            "exception_count": metrics.get("exception_count"),
            "duplicate_records": metrics.get("duplicate_records"),
            "invalid_rows": metrics.get("invalid_rows"),
            "review_records": metrics.get("review_records"),
            "elapsed_seconds": metrics.get("elapsed_seconds"),
            "exception_counts": metrics.get("exception_counts", {}),
        },
        "exception_summary": exception_summary,
        "exceptions_sample": exceptions_sample[:20],  # Send up to 20 exceptions for analysis
    }


async def generate_run_summary(metrics, exception_summary, exceptions_sample):
    """Generate an LLM-powered run summary. Returns (result_dict, model_version). Never raises."""
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return _fallback_summary(metrics, exception_summary, "no LLM key configured"), "none"

    payload = build_summary_payload(metrics, exception_summary, exceptions_sample)

    try:
        import httpx
        messages = [
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, default=str)}
        ]

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": messages,
                },
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "SettleSense",
                },
                timeout=AI_SUMMARY_TIMEOUT
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]

        parsed = _extract_json(text)
        if not isinstance(parsed, dict):
            return _fallback_summary(metrics, exception_summary, "invalid AI output format"), "gpt-4o-mini"

        # Ensure required fields exist
        required = ["overall_assessment", "key_findings", "common_root_causes", "recommendations"]
        for f in required:
            if f not in parsed:
                return _fallback_summary(metrics, exception_summary, f"missing field '{f}'"), "gpt-4o-mini"

        parsed["_fallback"] = False
        parsed["_model"] = "openrouter"
        return parsed, "gpt-4o-mini"

    except asyncio.TimeoutError:
        return _fallback_summary(metrics, exception_summary, "AI timeout"), "gpt-4o-mini"
    except Exception as e:
        return _fallback_summary(metrics, exception_summary, f"AI error: {type(e).__name__}: {e}"), "gpt-4o-mini"


def _extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in output")
    return json.loads(text[start:end + 1])


def _fallback_summary(metrics, exception_summary, reason):
    """Generate a deterministic fallback summary when LLM is unavailable."""
    exc_counts = metrics.get("exception_counts", {})
    total_exceptions = metrics.get("exception_count", 0)
    match_rate = metrics.get("overall_match_rate", 0)
    unresolved = metrics.get("unresolved_amount_minor", 0)

    # Identify top exception categories
    top_codes = sorted(exc_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    findings = []
    if match_rate and match_rate > 0:
        findings.append(f"Overall match rate is {match_rate * 100:.1f}%")
    if total_exceptions:
        findings.append(f"{total_exceptions} exceptions identified across {len(exc_counts)} categories")
    if unresolved:
        findings.append(f"₹{unresolved / 100:,.2f} remains unresolved and at risk")
    for code, count in top_codes[:3]:
        findings.append(f"{code}: {count} occurrences")

    root_causes = []
    for code, count in top_codes:
        root_causes.append({"cause": code.replace("_", " ").lower(), "count": count,
                            "description": f"{count} exceptions of type {code}"})

    return {
        "overall_assessment": f"Reconciliation processed {metrics.get('records_processed', 0)} records with "
                              f"a {match_rate * 100:.1f}% match rate. {total_exceptions} exceptions require review.",
        "key_findings": findings,
        "common_root_causes": root_causes,
        "risk_analysis": f"Total unresolved amount at risk: ₹{unresolved / 100:,.2f}",
        "recommendations": [
            "Review high-severity exceptions first",
            "Investigate common root causes for patterns",
            "Verify source file data quality",
        ],
        "data_quality_notes": f"{metrics.get('invalid_rows', 0)} invalid rows detected in source files",
        "confidence": 0.5,
        "_fallback": True,
        "_fallback_reason": reason,
    }
