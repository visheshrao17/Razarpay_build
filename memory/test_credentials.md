# SettleSense Test Credentials

## Demo accounts (seeded on backend startup, idempotent)
| Role | Email | Password |
|---|---|---|
| Operator | operator@settlesense.dev | operator123 |
| Reviewer | reviewer@settlesense.dev | reviewer123 |

## Auth endpoints
- POST /api/auth/login  {"email","password"} → sets httpOnly `access_token` cookie AND returns `access_token` in body (Bearer fallback supported)
- POST /api/auth/logout
- GET  /api/auth/me
- Brute force: 5 failed attempts per ip:email → 15 min lockout (HTTP 429)

## Database
- PostgreSQL (supervisor-managed program `postgresql`): postgresql://settlesense:settlesense_local@localhost:5432/settlesense

## Demo data
- Seeded fixture: /app/data/generated (regenerate: `python scripts/generate_dataset.py --seed 20260824 --records 120 --output data/generated`)
- Typical flow: login → POST /api/runs → POST /api/runs/{id}/sources/fixture → POST /api/runs/{id}/execute
- EMERGENT_LLM_KEY configured in backend/.env for AI explanations (models: gpt-5.4, claude-sonnet-4-6, gemini-3.1-pro-preview)
- Razorpay Test Mode keys NOT configured yet (RAZORPAY_KEY_ID/RAZORPAY_KEY_SECRET empty; adapter returns 400 with fixture fallback note)
