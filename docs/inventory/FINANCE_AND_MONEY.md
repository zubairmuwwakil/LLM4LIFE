# Finance & Money Systems Inventory

**Status:** Provisional / subject to change  
**Purpose:** Record the current financial software surfaces and define ownership boundaries for a scalable long-term LLM4LIFE architecture.

## Current usage

| System | Current role | Provisional long-term direction |
|---|---|---|
| **Wealthsimple** | Investment/financial account platform and usual tax filing software | Keep as an external financial institution/service; do not treat it as LLM4LIFE's canonical cross-system data model |
| **Bank apps** | Institution-specific banking access and transactions | Keep as external execution/source systems; LLM4LIFE/InUnity should aggregate/reference rather than attempt to replace regulated bank systems |
| **Credit-card issuer apps** | Card account access, transactions, statements, rewards/account servicing | Keep as issuer-specific execution/source systems; normalize useful metadata into the user's own applications where appropriate |
| **Apple Wallet** | Payment/card wallet and transaction/capture surface | Keep as a high-value mobile/payments surface; integrate through supported Shortcuts/intents rather than treating Wallet itself as canonical analytics state |
| **InUnity** | Emerging user-built financial/life unifier; intended to handle banking/credit-card views, budgeting, receipt scanning and broader money operations | Strong candidate to become the primary user-facing finance application, but exact boundary with MoneyTalks and Looply must be settled before implementation |
| **MoneyTalks** | Existing/planned budgeting and financial unifier capabilities | Re-evaluate whether it remains a distinct product, is renamed/absorbed into InUnity, or becomes a module/service beneath it |
| **PickMe** | Credit-card recommendation / Card Copilot for best-card selection, purchase capture and card optimization | Keep as the specialized card-decision subsystem unless its responsibilities are intentionally folded into InUnity; avoid duplicating card recommendation logic in multiple apps |
| **Looply** | Existing receipts/bills/subscriptions workflow | Re-evaluate against InUnity's intended receipt-scanning/bill/subscription scope; likely consolidation candidate if responsibilities overlap |
| **MarketLens / marketdata** | Market-data service intended to feed financial applications | Keep as a specialized data service if still useful; downstream apps should consume it rather than duplicate market-data acquisition |
| **Crypto.com** | Crypto exchange/account application | Keep as an external crypto institution/source system; do not store exchange credentials or keys in LLM4LIFE |
| **MetaMask / Phantom** | Self-custody wallet browser extensions | Keep isolated from general automation/browser trust boundaries; LLM4LIFE should never hold seed phrases/private keys |
| **Rakuten** | Cashback/rewards source | Keep for now; long term expose cashback opportunities through PickMe/InUnity/LLM4LIFE when reliable data access exists |

## Core architecture principle

External financial institutions remain authoritative for regulated account execution and official balances/transactions. The user's own applications should provide the **normalized intelligence and experience layer**.

```text
Banks / card issuers / Wealthsimple / Crypto.com / Apple Wallet
                         |
                         v
               ingestion / normalization
                         |
                  shared financial model
                         |
          +--------------+---------------+
          |                              |
       InUnity                         PickMe
 broad money/life UI            card-decision specialist
          |
 budgeting / receipts / bills / subscriptions

 MarketLens -> market data consumed where needed
```

This is directional, not final.

## Major consolidation decision to resolve after inventory

The current product family contains overlapping or potentially overlapping responsibilities:

- **InUnity** — intended broad financial/life unifier, budgeting and receipt scanning;
- **MoneyTalks** — financial unifier/budgeting capabilities;
- **Looply** — receipts/bills/subscriptions;
- **PickMe** — card optimization and transaction-related workflows.

Before implementation, explicitly decide whether:

1. **InUnity becomes the umbrella product** and MoneyTalks/Looply are absorbed as modules/services;
2. MoneyTalks remains the finance engine while InUnity is a broader presentation/orchestration layer;
3. Looply remains a dedicated ingestion/subscription service feeding InUnity;
4. PickMe remains a separately deployable specialist but exposes APIs/events into the shared financial model.

Do not allow multiple products to independently maintain the same canonical transaction, subscription, receipt, budget, or card metadata.

## Production-grade direction

Prefer a shared normalized domain model and event contracts over point-to-point duplication. Examples of canonical objects may include:

- account
- card
- transaction
- merchant
- receipt
- bill/subscription
- reward/cashback opportunity
- budget/category
- market instrument/quote

Exact schema ownership should be designed after the full inventory is complete.

## Security boundaries

- Never store online-banking passwords, card credentials, crypto seed phrases, private keys, 2FA secrets, or recovery codes in the public LLM4LIFE repo.
- Use provider APIs/OAuth/official integrations where available.
- Secrets belong in secret managers or local/runtime environment configuration, not architecture docs.
- Crypto signing authority should remain isolated from autonomous AI/browser agents by default.

## Immediate implementation follow-up after inventory

- Resolve the InUnity vs MoneyTalks vs Looply ownership/consolidation model.
- Define the canonical financial data model and system-of-record matrix.
- Define ingestion adapters/events for Apple Wallet, email receipts, issuer/bank exports/APIs, Rakuten-like rewards data, and market data.
- Keep PickMe's recommendation engine specialized unless there is a compelling reason to merge it.
