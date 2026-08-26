# What You Can Build with RazorpayX Test Mode

**Prepared by Manus AI | 24 August 2026**

## Executive Recommendation

Build **PayoutGuard**: an AI-powered payout risk verifier and reconciliation control tower for merchants.

PayoutGuard reviews a batch of vendor, employee, or partner payout requests; detects duplicates, unusual amounts, beneficiary inconsistencies, and suspicious velocity; routes risky requests to human review; creates safe payouts through RazorpayX Test Mode; tracks the payout lifecycle through webhooks; and reconciles the final payout and transaction records against the original request.

This is the best use of the supplied RazorpayX capability because it creates a complete, demonstrable loop:

> **Payout request → AI risk analysis → deterministic policy gate → human approval → RazorpayX test payout → webhook lifecycle → account-statement reconciliation → audit report**

RazorpayX Test Mode supports contacts, fund accounts, payouts, webhooks, bulk upload, dummy balance, and account statements. It uses no real money, and Test Mode data does not appear in the live environment. [1] This gives you a safe way to demonstrate real payout operations without handling real funds.

## Why PayoutGuard Fits the Buildathon

PayoutGuard fits best in **Track 2 — AI Risk Manager**, with **Track 4 — AI Finance Controller** as a secondary positioning option.

For Track 2, the product is a strictly defense-only verifier for payout fraud and operational loss. It can report precision, recall, false-positive cost, and the amount of suspicious payout value intercepted. For Track 4, the post-payout reconciliation component can process a batch of 50 or more synthetic records and report match rate plus unresolved exceptions. The safest submission is to choose one primary track rather than presenting two disconnected products.

| Buildathon requirement | How PayoutGuard satisfies it |
|---|---|
| Working product | It reviews payout requests, creates Test Mode payouts, tracks states, and produces a reconciliation report. |
| Meaningful AI | AI detects anomalies, explains evidence, prioritizes review, and summarizes exceptions. |
| Defense-only risk use | It recommends review or blocks unsafe payout execution; it has no offensive capability. |
| Measured evaluation | Use a labelled holdout batch and report precision, recall, false-positive cost, and review yield. |
| Human-in-the-loop | High-risk payouts require approval in your application before the API call. |
| Razorpay integration | Use RazorpayX Contacts, Fund Accounts, Payouts, Transactions, and Webhooks. |
| Graceful failure | Duplicate request, insufficient balance, reversed payout, or missing webhook is routed to an exception state. |
| Strong demo | One safe payout, one blocked payout, one manually moved payout lifecycle, and one reconciliation exception. |

## What RazorpayX Test Mode Actually Enables

The supplied official documentation states that Test Mode is a sandbox replica of RazorpayX. Contacts, fund accounts, payouts, and webhooks are available through the API, Dashboard, and in some cases bulk upload. The environment has its own dummy balance and does not use real money. [1]

A payout requires a Contact and a Fund Account. Fund Accounts can be created with bank-account or VPA information and must be linked to a Test Mode Contact. Payouts can then be created, viewed, and moved through lifecycle states. New payouts normally start in `processing`, or `queued` when the dummy balance is insufficient. In Test Mode, the payout does not progress automatically; it must be moved manually from the Dashboard. [1]

The Test Mode webhook events listed in the documentation are `payout.queued`, `payout.initiated`, `payout.processed`, `payout.reversed`, and `transaction.created`. The account statement can be viewed in the Dashboard or fetched through Transaction APIs. [1]

| RazorpayX surface | PayoutGuard use |
|---|---|
| Contacts | Store merchant-approved beneficiaries and detect new or changed recipients. |
| Fund Accounts | Verify that a payout destination belongs to the intended Contact. |
| Payouts | Execute the final Test Mode payout after policy approval. |
| Dummy balance | Demonstrate insufficient-balance and queued-payout behavior safely. |
| Payout webhooks | Update the state machine without polling continuously. |
| Transactions | Reconcile payout outcomes against the internal request ledger. |
| Account statements | Produce a close or payout-control report. |
| Bulk upload | Seed a realistic batch of contacts, fund accounts, or payout requests. |

## Product Concept

### One-line pitch

**PayoutGuard prevents costly payout mistakes by verifying who should be paid, how much they should receive, and whether the payout actually settled.**

### The real problem

Merchants often process vendor, employee, creator, marketplace, and partner payouts from spreadsheets or semi-structured requests. Common losses include duplicate payouts, changed beneficiary details, unusual amounts, rushed payouts outside policy, payouts to inactive accounts, and payouts that appear complete in an internal system but are later reversed or never reconciled.

The project should not claim to solve every fraud type. Define a narrow problem: **pre-payout detection of suspicious or inconsistent payout requests, followed by post-payout reconciliation**.

### Target users

The primary users are finance operators, accounts-payable teams, marketplace-operations teams, and founders who approve payouts. The secondary users are risk analysts who investigate the exceptions produced by the system.

## How the Product Works

### Core workflow

1. The user uploads or generates a batch of payout requests.
2. PayoutGuard validates required fields and resolves each request to an existing Contact and Fund Account.
3. The anomaly engine checks amount, frequency, beneficiary changes, duplicate references, inactive contacts, and balance sufficiency.
4. The explanation agent summarizes why a payout is safe, suspicious, or unresolved.
5. A deterministic policy engine assigns one of four states: **auto-approve**, **human review**, **reject**, or **insufficient evidence**.
6. Only an approved request can create a RazorpayX Test Mode payout.
7. Webhook events update the payout lifecycle.
8. The reconciliation worker matches the original request, Razorpay payout, webhook events, and transaction record.
9. The dashboard reports approved value, blocked value, processed value, reversed value, match rate, and unresolved exceptions.

### Product screens

| Screen | Purpose |
|---|---|
| Payout Inbox | Shows all requests with amount, beneficiary, risk band, and state. |
| Risk Explanation | Shows evidence such as duplicate reference, amount deviation, new fund account, or unusual velocity. |
| Approval Queue | Lets a human approve, reject, or request more evidence. |
| Payout Timeline | Shows request, approval, API response, webhook events, and final state. |
| Reconciliation View | Matches internal request to payout ID and transaction ID. |
| Policy Console | Defines amount limits, beneficiary-change rules, velocity limits, and balance buffer. |
| Evaluation Dashboard | Reports precision, recall, false-positive cost, review yield, and reconciliation match rate. |

## AI and Guardrail Architecture

```text
Payout Request Batch
        |
Schema + Identity Validation
        |
Feature Builder
(amount, velocity, beneficiary age, duplicate reference, balance)
        |
Risk Scoring Model
        |
Explanation Agent
        |
Deterministic Policy Engine
   /             |              \
Approve       Review          Reject
   |             |              |
Human approval  Evidence       Audit record
   |
RazorpayX Test Mode Payout API
        |
Webhook Ingestion + Signature Verification
        |
Payout State Machine
        |
Transaction / Account Statement Reconciliation
        |
Final Audit Report
```

The LLM should never decide alone whether a payout is executable. It may summarize evidence or explain a model result, but the final action must pass deterministic checks. Those checks should include maximum amount, allowed currency, active Contact, matching Fund Account, duplicate idempotency key, beneficiary-change cooldown, velocity threshold, available Test Mode balance, and human approval status.

Because the supplied documentation states that RazorpayX Test Mode does not provide the normal Approval Workflow states `pending` and `rejected`, PayoutGuard should implement its own application-level approval state before calling the payout API. The Dashboard can still be used to manually move a payout from `processing` to a later state for demonstration. [1]

## Recommended Evaluation Method

Create a synthetic labelled batch of **100 payout requests**. The batch should contain 70 legitimate requests and 30 suspicious or erroneous requests distributed across duplicate reference, amount spike, new beneficiary, inactive Contact, repeated velocity, insufficient balance, and payout reversal cases.

Split the data before model tuning. Use a temporal or merchant-held-out test split where possible. Report the following metrics:

| Metric | Definition |
|---|---|
| Precision | Of requests flagged as suspicious, the proportion that are actually suspicious or erroneous. |
| Recall | Of all suspicious or erroneous requests, the proportion detected. |
| False-positive cost | Review effort or customer/vendor friction caused by incorrectly flagging a legitimate request. |
| Review yield | Suspicious value divided by total value sent to human review. |
| Blocked value | Rupee value prevented from automatic execution by the policy gate. |
| Reconciliation match rate | Requests matched to the correct RazorpayX payout and transaction records. |
| Exception rate | Records that could not be safely matched or verified. |
| Webhook completeness | Expected lifecycle events received and processed without duplication. |

Do not claim that blocked value equals money saved unless the dataset explicitly defines that counterfactual. Use “suspicious value intercepted” for the demo and reserve “money saved” for a labelled counterfactual analysis.

## Three Possible Versions of the Product

| Version | Description | Best track | Score |
|---|---|---|---:|
| **PayoutGuard Core** | Pre-payout anomaly verifier with human approval and real Test Mode payout execution. | AI Risk Manager | **9.0/10** |
| **PayoutGuard Reconcile** | Post-payout matching of requests, payouts, webhooks, and transactions across 50+ records. | AI Finance Controller | **8.8/10** |
| **PayoutGuard Treasury Agent** | Adds balance forecasting, queued-payout prioritization, and payout scheduling. | Open Track | **7.8/10** |

Build **PayoutGuard Core** first. Add reconciliation as a mandatory verification stage, not as a separate product. Do not build the Treasury Agent unless the core workflow is already complete.

## Suggested Demo Story

Start with a batch of 20 payout requests and say: “This merchant is about to pay ₹2,40,000. Three requests are unsafe, but a spreadsheet workflow will not explain which ones.”

First, submit a normal payout. PayoutGuard validates the Contact and Fund Account, shows a low-risk explanation, obtains approval, creates the Test Mode payout, and displays the payout ID. Next, submit a duplicate request with a changed amount. The system flags the duplicate and amount deviation, routes it to review, and refuses to create the payout. Then submit a payout while the dummy balance is insufficient. The system records `queued`, explains the balance condition, and does not mislabel the payout as processed. Finally, use the Dashboard to move one payout forward, replay the webhook, and show the final reconciliation result.

The closing screen should show:

| Outcome | Example display |
|---|---:|
| Total requests evaluated | 20 |
| Total requested value | ₹2,40,000 |
| Auto-approved value | ₹1,60,000 |
| Review value | ₹50,000 |
| Rejected or unresolved value | ₹30,000 |
| Test payouts created | 10 |
| Processed payouts | 8 |
| Reversed payouts | 1 |
| Reconciliation match rate | 94% |
| Unresolved exceptions | 3 |

Use these only as demo placeholders until the actual seeded run produces the numbers.

## What Not to Build

Do not build a generic chatbot that merely answers “what is the payout status?” Do not build a dashboard without a decision or verification loop. Do not claim that RazorpayX Test Mode automatically progresses payouts; the supplied documentation explicitly says lifecycle advancement is manual in Test Mode. [1]

Do not depend on the RazorpayX Approval Workflow for the demo because `pending` and `rejected` states are unavailable in Test Mode. Implement approval in your own application. Do not expose live credentials, use real beneficiary information, or represent dummy-balance outcomes as real financial transactions.

Do not make the LLM responsible for arithmetic, identity matching, policy enforcement, or final payout execution. Those responsibilities belong in typed backend code and deterministic policy checks.

## 24–48 Hour Build Plan

| Time | Deliverable |
|---|---|
| Hours 0–3 | Create repository, data schema, environment variables, and synthetic payout generator. |
| Hours 3–8 | Implement Contacts, Fund Accounts, payout-request ledger, and duplicate/idempotency checks. |
| Hours 8–13 | Build anomaly features and a simple rules-plus-model risk scorer. |
| Hours 13–18 | Create held-out evaluation script with precision, recall, false-positive cost, and review yield. |
| Hours 18–24 | Implement application-level approval queue and deterministic policy engine. |
| Hours 24–30 | Integrate RazorpayX Test Mode payout creation and dummy-balance handling. |
| Hours 30–35 | Add webhook endpoint, signature verification, idempotent event processing, and state machine. |
| Hours 35–40 | Add transaction/account-statement reconciliation and exception ledger. |
| Hours 40–44 | Build dashboard views and failure-injection controls. |
| Hours 44–47 | Run final evaluation, write README, add architecture diagram, and record demo. |
| Hours 47–48 | Remove secrets, freeze scope, test setup from a clean environment, and submit. |

## Final Recommendation

Build **PayoutGuard Core** in the **AI Risk Manager** track.

Its winning formula is:

> **A defense-only AI payout verifier that catches suspicious payout requests before execution, requires human approval for risky cases, executes safe payouts through RazorpayX Test Mode, tracks the lifecycle through webhooks, and reconciles every result against an internal ledger.**

This project is more compelling than a plain payout dashboard because it demonstrates AI decision support, real Test Mode actions, deterministic safety, human oversight, measurable false positives and recall, event-driven architecture, and honest handling of Test Mode limitations. The most memorable feature should be the **Payout Decision Receipt**: one compact record that explains why a payout was approved, blocked, or sent to review and links that decision to the final RazorpayX payout and transaction state.

### References

[1]: https://razorpay.com/docs/build/llm-docs/x/dashboard/test-mode.md "Razorpay Docs: RazorpayX Test Mode"

[2]: https://razorpay.com/docs/api/x/payouts/ "Razorpay Docs: Payout APIs"

[3]: https://razorpay.com/docs/api/x/transactions/ "Razorpay Docs: Transaction APIs"

[4]: https://razorpay.com/docs/build/llm-docs/webhooks.md "Razorpay Docs: Webhooks"
