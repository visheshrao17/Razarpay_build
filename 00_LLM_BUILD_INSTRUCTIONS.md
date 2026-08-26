# SettleSense LLM Build Instructions

## Role

You are the lead software engineer responsible for building **SettleSense**, a multi-source settlement reconciliation agent for the Razorpay AI Buildathon.

You must use the files in this build pack as the source of truth. Read this file first, then read `PROJECT_REQUIREMENTS.md`, `TASK.md`, `MILESTONES.md`, and the relevant files in `docs/` before writing implementation code.

## Product Definition

SettleSense reconciles three financial sources:

1. Razorpay settlement or settlement-reconciliation records.
2. A bank statement containing credits and debits.
3. An internal order ledger containing expected merchant transactions.

The system identifies matched records, explains differences, classifies exceptions, supports human review, and produces an audit-ready close report.

## Non-Negotiable Rules

- Use deterministic backend code for money, identifiers, matching, thresholds, and final decisions.
- Use AI only for evidence-grounded exception classification, explanation, and suggested next steps.
- Never invent a settlement, bank entry, order, payment, refund, fee, tax, or cause.
- Never force-match a conflicting or ambiguous record.
- Every decision must cite the source record IDs and the rules or model version used.
- Keep the system functional without Razorpay credentials using synthetic fixtures.
- Use Razorpay Test Mode only when credentials are available and configured on the server.
- Never expose API secrets to the frontend or commit secrets to the repository.
- Treat fee, tax, timing, and settlement-cycle behavior as configurable demo assumptions unless verified for the account.
- Do not create tax filings, accounting postings, legal opinions, or live-money actions.

## Required Build Behavior

The final product must:

- Process at least 100 records in one reconciliation run.
- Load settlement, bank, and internal ledger data.
- Preserve raw source values and normalized values.
- Perform exact matching, tolerance matching, candidate generation, and controlled aggregate matching.
- Detect duplicate, missing, conflicting, timing, refund, fee, tax, and ambiguous cases.
- Produce match confidence and evidence.
- Route uncertain records to a human review queue.
- Generate source-linked AI explanations.
- Maintain an append-only audit trail.
- Report precision, recall, match rate, throughput, amount variance, and unresolved exceptions.
- Export a Markdown, JSON, or CSV close report.
- Demonstrate at least one deliberate failure where the system refuses to force-match a record.

## Required Implementation Order

Implement the project in this order:

1. Read all documentation files.
2. Lock the scope and assumptions.
3. Create schemas and database tables.
4. Generate deterministic synthetic data and independent ground truth.
5. Implement ingestion and normalization.
6. Implement deterministic matching.
7. Implement exception taxonomy and confidence bands.
8. Add AI explanations with strict structured output.
9. Add the optional Razorpay adapter.
10. Add human review, audit log, and report export.
11. Add frontend screens.
12. Run evaluation and failure tests.
13. Prepare the demo and submission documentation.

Do not begin with the LLM integration. Do not implement the Razorpay adapter before the synthetic pipeline works.

## Files to Read Before Implementation

| File | Why it matters |
|---|---|
| `PROJECT_REQUIREMENTS.md` | Product requirements, scope, personas, and non-goals. |
| `TASK.md` | Detailed technical backlog and acceptance criteria. |
| `MILESTONES.md` | Phase order, prompts, validation gates, and definitions of done. |
| `RAZORPAYX_CONTEXT.md` | RazorpayX Test Mode context and platform constraints. |
| `docs/assumptions.md` | Demo assumptions and configurable values. |
| `docs/data-dictionary.md` | Typed source and output fields. |
| `docs/architecture.md` | Component and data-flow design. |
| `docs/matching-rules.md` | Matching precedence and confidence behavior. |
| `docs/metric-definitions.md` | Evaluation formulas. |
| `docs/exception-taxonomy.md` | Exception codes and actions. |
| `docs/api-contract.md` | Backend endpoints and schemas. |
| `docs/ai-guardrails.md` | AI boundaries and safe output. |
| `docs/audit-log-spec.md` | Audit event structure. |
| `docs/test-plan.md` | Required tests. |
| `docs/data-generation.md` | Synthetic data and ground truth requirements. |
| `docs/demo-script.md` | Final demo story. |
| `docs/limitations.md` | Required disclosures. |

## Phase Execution Protocol

At the beginning of each phase:

1. Read the phase section in `MILESTONES.md`.
2. Read all Markdown files listed for that phase.
3. Inspect the current repository state.
4. List the exact implementation tasks you will perform.
5. Identify risks and assumptions.

During the phase:

1. Make the smallest implementation that satisfies the phase.
2. Preserve existing interfaces unless a documented change is required.
3. Write tests with the implementation.
4. Update the relevant Markdown documentation when behavior changes.
5. Keep synthetic mode working at all times.

At the end of the phase:

1. Run the phase validation gate.
2. Run relevant tests.
3. Check that no secrets are present.
4. Update the checklist in `TASK.md` or the relevant phase documentation.
5. Report completed work, test commands, outputs, unresolved risks, and the next phase.
6. Do not proceed if a critical validation gate fails.

## Required Final Response from the LLM

When the implementation is complete, return:

- Project summary.
- Features implemented.
- Files created or changed.
- Setup commands.
- Environment variables required.
- Synthetic-data generation command.
- Reconciliation command.
- Evaluation command.
- Test results.
- Final metrics.
- Known limitations.
- Razorpay Test Mode integration status.
- Demo instructions.

## Recommended First Prompt

```text
Read every Markdown file in this SettleSense build pack, especially 00_LLM_BUILD_INSTRUCTIONS.md, PROJECT_REQUIREMENTS.md, TASK.md, MILESTONES.md, and all docs/*.md files. Do not write code yet. First summarize the architecture, data contract, matching policy, AI guardrails, evaluation requirements, and phase dependencies. Then list any contradictions or missing decisions. Wait for approval before implementing Phase 0.
```
