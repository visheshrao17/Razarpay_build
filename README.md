# SettleSense — Multi-Source Settlement Reconciliation Agent

> **SettleSense explains where every rupee went by reconciling Razorpay settlements, bank credits, and internal
> orders while refusing to force-match unexplained differences.**

Built for the **Razorpay AI Buildathon — Track 4: AI Finance Controller**.

## What it does

SettleSense reconciles three financial sources — Razorpay settlement lines, a bank statement, and an internal
order ledger — across 260+ records per run. It:

- performs **deterministic matching** in ordered passes (payment ID + amount → order ID + amount → UTR + amount →
  tolerance → candidate scoring → controlled one-to-many/many-to-one aggregation),
- classifies every unresolved record into a **14-code exception taxonomy** with severity, evidence and amount at risk,
- generates **evidence-grounded AI explanations** (GPT-5.4 / Claude Sonnet 4.6 / Gemini 3.1 Pro, strict JSON,
  validated citations, abstention, deterministic fallback),
- routes uncertainty to a **human review queue** (approve / reject / split / request data / leave unresolved),
- maintains an **append-only, hash-chained audit trail** for every material decision,
- exports a **hash-signed close report** (Markdown / JSON / CSV),
- and reports **precision, recall, match rate, throughput and unresolved value** against independently generated
  ground truth, including a three-way baseline comparison.

**Central rule:** SettleSense matches records only when evidence is sufficient and leaves unexplained records
unresolved. Forced matches: **0**, by construction.

## Measured results (seeded fixture, seed 20260824)

| Metric | Value |
|---|---|
| Records processed per run | 260 (129 settlement lines, 110 orders, 21 bank rows) |
| Auto-match precision (independent ground truth) | **1.00** |
| Auto-match recall | **1.00** |
| Overall match rate | 90.3% (the remaining 9.7% is honestly unresolved) |
| Throughput | > 20,000 records/second |
| Forced matches | **0** |
| Exception categories exercised | 12 (duplicates, timing, fee/tax variance, refunds, missing records, ambiguity, conflicts, invalid rows, unexplained credits) |

Baseline comparison (same dataset, same ground truth): exact-only → recall 0.9835; + tolerance → 0.9835;
final candidate/aggregate matcher → **1.00**, all at precision 1.00.

## Architecture

```
React (dashboard) ── /api ──> FastAPI ──> PostgreSQL
                               │
       ingestion & validation (raw preserved) → deterministic matching engine
                               │
       exceptions + evidence → AI explanation (strict JSON, validated, abstains)
                               │
       human review queue → append-only hash-chained audit log → signed close report
Adapters: synthetic fixtures (default) │ Razorpay Test Mode (optional, env-gated)
```

See `docs/architecture.md`, `docs/matching-rules.md`, `docs/exception-taxonomy.md`, `docs/ai-guardrails.md`,
`docs/audit-log-spec.md`, `docs/metric-definitions.md` for the full contract.

## Quick start

```bash
# 1. Generate the deterministic dataset + independent ground truth
python scripts/generate_dataset.py --seed 20260824 --records 120 --output data/generated

# 2. Backend (FastAPI, port 8001) & frontend (React, port 3000) run under supervisor
sudo supervisorctl restart backend frontend

# 3. Offline evaluation (matcher vs ground truth + baseline comparison)
python scripts/evaluate.py --out data/evaluation/results.json

# 4. Tests
python -m pytest tests/ -q
```

Login (demo): `operator@settlesense.dev / operator123` or `reviewer@settlesense.dev / reviewer123`.

UI flow: **New run → Load demo fixture → Execute → Summary → Matches / Exceptions (AI explain, resolve) →
Audit → Report (export)**.

## AI boundaries

Deterministic code owns money, identifiers, matching, thresholds and final decisions. The LLM only classifies and
explains exceptions from structured evidence, must cite real source-record IDs (validated server-side), abstains on
insufficient evidence, and falls back deterministically on timeout/invalid output. It can never change an amount,
force a match, or resolve an exception.

## Razorpay integration status

Synthetic mode is the default and requires no credentials. An optional, server-side Razorpay **Test Mode** adapter
(`backend/adapters/razorpay_adapter.py`) fetches settlement reconciliation data when `RAZORPAY_KEY_ID` /
`RAZORPAY_KEY_SECRET` are set in `backend/.env`, with retries, rate-limit handling and a fixture fallback.
Secrets never reach the frontend or the repository.

## Disclosures & limitations

- All committed data is **synthetic** (seeded, checksummed); it does not represent real merchant/bank/Razorpay behaviour.
- Fee (2% of gross) and tax (18% of fee) are **versioned demo assumptions (v1.0)**, not universal rules.
- The close report is an operational control report — not a tax filing, accounting posting or audit opinion.
- See `docs/limitations.md` for the full list.

## Demo (5 minutes)

Follow `docs/demo-script.md`: one full 260-record run → one exact match → one fee variance with amount waterfall →
one **deliberate graceful failure** (ambiguous bank credit with two equal candidates that the system refuses to
force-match) → one human resolution with audit event → exported hash-signed close report.
