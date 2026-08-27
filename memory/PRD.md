# SettleSense PRD & Progress Memory

## Original problem statement
"in this repository you find the requirement and other docs start building this" — repository is the SettleSense
build pack (Razorpay AI Buildathon, Track 4: AI Finance Controller): a multi-source settlement reconciliation agent.
Source-of-truth docs: 00_LLM_BUILD_INSTRUCTIONS.md, PROJECT_REQUIREMENTS.md, TASK.md, MILESTONES.md, docs/*.md.

## User choices (2026-06 session 1)
- AI models: GPT-5.4 + Claude Sonnet 4.6 + Gemini 3.1 Pro (all selectable, via Emergent Universal Key)
- Database: PostgreSQL (explicitly requested over MongoDB)
- Razorpay Test Mode: user WILL PROVIDE KEYS LATER (adapter built, env-gated, currently unconfigured)
- Auth: simple demo login (JWT, seeded operator + reviewer accounts)
- Scope: full MVP end-to-end

## Architecture
- Backend: FastAPI + SQLAlchemy(async) + asyncpg + PostgreSQL (supervisor program `postgresql`, db `settlesense`)
- Frontend: React 18 (CRA) + Tailwind 3 + recharts + sonner + @phosphor-icons; IBM Plex Sans/Mono, Swiss light theme
- AI: emergentintegrations LlmChat, strict JSON output, validated evidence citations, abstention, deterministic fallback
- Files: backend/{server.py,auth.py,models.py,database.py,taxonomy.py,services/{matching,ingestion,audit,ai_explain,evaluation,report}.py,adapters/razorpay_adapter.py,routers/{runs,exceptions,misc,common}.py}
- scripts/generate_dataset.py (seed 20260824), scripts/evaluate.py, tests/test_matching.py (16 tests)

## Core requirements (static, from build pack)
- Deterministic matching only; AI explains, never decides. Zero forced matches. Every decision cites evidence + rules version.
- ≥100 records/run; precision ≥0.95 on independent ground truth; append-only hash-chained audit; signed close report.
- Works without Razorpay credentials (synthetic fixtures default).

## What's been implemented (2026-06, session 1 — full MVP)
- Deterministic dataset generator: 129 settlements / 110 orders / 21 bank rows / 110 payments + independent ground_truth.json + checksums (12 seeded scenario types incl. deliberate ambiguous failure batch setl_0006)
- Ingestion (CSV upload + fixture registration, validation, raw preserved, idempotent re-upload)
- Matching engine: exact (payment/order/UTR+amount) → tolerance → candidate scoring (≤5, deterministic) → one-to-many/many-to-one aggregation; duplicate/conflict detection; confidence weights 0.40/0.25/0.20/0.10/0.05; bands 0.90/0.60
- 14-code exception taxonomy with severity/evidence/amount-at-risk; INVALID_SOURCE from ingestion
- AI explanations (3 models selectable) with schema validation + evidence-ID verification + abstention + fallback; audit-logged with model+prompt version
- Human review: approve/reject/split/merge/request_data/leave_unresolved with mandatory note; audit human_gate events
- Append-only hash-chained audit trail; close report (md/json/csv) with SHA-256 report hash; run states CREATED→…→CLOSED
- Evaluation: precision/recall vs GT (both 1.00), 3-way baseline comparison endpoint + offline script
- Razorpay Test Mode adapter (settlements recon fetch, retries, normalization, fixture fallback) — awaiting keys
- Webhook endpoint with dedupe; JWT auth with brute-force lockout; seeded users
- Frontend: Login, Runs (setup w/ tolerances+AI model), Run Summary (metrics, charts, baselines), Matches (+detail w/ side-by-side records, waterfall, evidence, audit), Exception queue (filters, AI explain modal, resolve), Audit timeline, Report preview/export
- 16 pytest tests passing; measured: 260 records/run, precision 1.00, recall 1.00, match rate 90.3%, 0 forced matches

## Testing (iteration 1, 2026-06)
- Testing agent: backend 20/21, frontend all flows pass. Fixed after: (1) server-side reviewer-note validation on resolve (400 on empty), (2) data-testid="metric-recall" on RunSummary, (3) /app/scripts/pg_bootstrap.sh + supervisor program pg_bootstrap (idempotent postgres cluster/role/db recovery across container restarts). All re-verified via curl.

## Backlog / next tasks
- P0: Razorpay Test Mode keys from user → verify adapter end-to-end (/api/runs/{id}/sources/razorpay)
- P1: CSV upload UI for user's own source files (backend endpoint exists; UI button not yet built)
- P1: docs/*.md refresh where implementation details differ (they largely match)
- P2: webhook signature verification (RAZORPAY_WEBHOOK_SECRET), reviewer resolution-time metric, diagrams/architecture.mmd
- P2: demo video / submission packaging per Phase 9
