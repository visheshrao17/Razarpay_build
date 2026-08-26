# SettleSense Product Requirements

## Product Summary

SettleSense is an AI-assisted reconciliation system for merchants. It compares Razorpay settlement data, bank statement records, and an internal order ledger. It identifies matches, explains differences, routes uncertain items to human review, and produces a traceable close report.

## Target User

The target user is a merchant finance operator, accounts-receivable analyst, accounts-payable analyst, or finance controller who currently reconciles payment and settlement records through spreadsheets.

## User Problem

A merchant may know the total amount deposited into its bank account but still be unable to explain how that amount relates to individual orders, payments, refunds, fees, taxes, timing differences, and adjustments. A useful system must increase verification capacity without hiding uncertainty.

## Core User Story

As a finance operator, I want to upload or retrieve settlement data, bank data, and internal order data so that I can see which records match, understand every difference, resolve exceptions, and export an audit-ready close report.

## Product Workflow

```text
Create reconciliation run
        ↓
Load three source datasets
        ↓
Validate and normalize records
        ↓
Match orders, settlements, and bank entries
        ↓
Score confidence and classify exceptions
        ↓
Explain evidence with AI
        ↓
Review uncertain records
        ↓
Generate final close report
```

## Functional Requirements

### Source management

- The system must accept settlement, bank statement, and internal order data.
- Each upload must be associated with a run ID and source type.
- Raw source data must be preserved.
- Normalized records must retain source-record references.
- Invalid rows must be reported without silently disappearing.

### Reconciliation

- The system must match records using ordered deterministic rules.
- It must support exact identifier matching.
- It must support configurable date and amount tolerances.
- It must detect duplicates and identifier conflicts.
- It must support controlled one-to-many and many-to-one matches.
- It must produce evidence for every match decision.
- It must refuse to force-match ambiguous records.

### Exception management

- Every unmatched or conflicting record must receive an exception code.
- Exceptions must have severity, evidence, confidence, and suggested action.
- Users must be able to filter and sort exceptions.
- Users must be able to resolve exceptions through a review workflow.
- Every review action must be logged.

### AI assistance

- AI may classify exceptions.
- AI may summarize evidence.
- AI may suggest a next review action.
- AI may answer constrained questions over the reconciliation data.
- AI must cite source record IDs.
- AI must return an abstention when evidence is insufficient.
- AI must not change financial values or override deterministic policy.

### Reporting

- The system must show batch-level metrics.
- The system must show matched and unresolved amounts.
- The system must show exception categories.
- The system must show assumptions used in the run.
- The system must export a close report.
- The report must include audit references.

## Non-Functional Requirements

| Requirement | Target |
|---|---|
| Reproducibility | Same seed and input produce the same result. |
| Safety | No unexplained record is force-matched. |
| Explainability | Each decision cites source fields and IDs. |
| Availability | Synthetic mode works without external credentials. |
| Privacy | Use synthetic or minimized data in the demo. |
| Performance | Process at least 100 records in a single run. |
| Auditability | Every material decision is append-only logged. |
| Resilience | AI failure does not stop deterministic reconciliation. |

## User Roles for MVP

The MVP needs only two logical roles:

| Role | Permissions |
|---|---|
| Operator | Run reconciliation, inspect records, and view reports. |
| Reviewer | Resolve exceptions and record decisions. |

A full enterprise permission system is out of scope.

## MVP Screens

1. **Run Setup:** Select sources, configure tolerances, and start a run.
2. **Run Summary:** View processed records, match rate, unresolved value, and exception counts.
3. **Match Detail:** Inspect source rows, evidence, confidence, and amount waterfall.
4. **Exception Queue:** Review unresolved and low-confidence records.
5. **Audit Timeline:** Trace decisions and review actions.
6. **Report View:** Preview and export the final close report.

## Buildathon Success Criteria

The project is successful when it can process 100 or more records, report match-rate and precision/recall metrics on independent ground truth, explain unresolved exceptions, show one deliberate graceful failure, and generate an audit-ready report.

## Demo Success Criteria

The five-minute demo must show one full run, one exact match, one fee or timing exception, one ambiguous record that is not force-matched, one human resolution, and the final report.

## Out of Scope

The MVP must not include live-money operations, autonomous accounting posting, tax filing, legal advice, full ERP integration, production-grade multi-tenancy, unrestricted natural-language SQL, or a general-purpose finance chatbot.

## References

[1]: https://razorpay.com/buildathon/ "Razorpay AI Buildathon"

[2]: https://razorpay.com/docs/api/settlements/ "Razorpay Settlement APIs"
