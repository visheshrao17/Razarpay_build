# SettleSense Limitations and Disclosures

## Data Disclosure

The evaluation dataset is synthetic. It is designed to test matching behavior and does not represent actual merchant, bank, Razorpay, or customer data.

## Razorpay Integration Disclosure

The application must work without Razorpay credentials using the synthetic adapter. If Razorpay Test Mode is configured, the README must identify which fields and operations came from Test Mode and which were generated locally.

## Accounting Disclosure

The close report is an operational reconciliation control report. It is not a tax filing, accounting posting, audit opinion, legal opinion, or guarantee of tax-credit eligibility. Fee, tax, settlement-cycle, timing-window, and amount-tolerance behavior must be labeled as account-specific or demo assumptions unless independently verified.

## AI Disclosure

The AI classifies and explains exceptions. It does not own financial truth, change source records, calculate authoritative tax, or resolve unsupported ambiguity. AI outputs are validated and may abstain.

## Matching Limitations

Fuzzy matching can produce candidates but cannot establish financial truth by itself. Unmatched records may require source documents, bank advice, merchant review, or manual investigation.

## Test Mode Limitations

Test Mode is a sandbox and does not use real money. Test data may not expose every production field or lifecycle behavior. Any missing or mocked behavior must be disclosed in the demo and README.

## Security Limitations

The MVP is a hackathon prototype. It must protect secrets and minimize personal data, but it is not a complete enterprise security review. Production deployment would require stronger authentication, authorization, monitoring, retention controls, and compliance review.

## Known-Future Work

Potential future work includes ERP export, richer bank formats, account-specific fee configuration, production-grade access controls, model monitoring, multilingual explanations, and human-review workload analytics.
