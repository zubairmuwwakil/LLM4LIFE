# Finance & Money Systems Inventory

**Status:** Provisional / subject to change  
**Purpose:** Record the current financial software surfaces and define ownership boundaries for a scalable long-term LLM4LIFE architecture.

## Current usage

| System | Current role | Provisional long-term direction |
|---|---|---|
| **Wealthsimple** | Investment/financial account platform and usual tax filing software | Keep as an external financial institution/service; do not treat it as LLM4LIFE's canonical cross-system data model |
| **Bank apps** | Institution-specific banking access and transactions | Keep as external execution/source systems; InUnity should aggregate/reference rather than attempt to replace regulated bank systems |
| **Credit-card issuer apps** | Card account access, transactions, statements, rewards/account servicing | Keep as issuer-specific execution/source systems; normalize useful metadata into InUnity where appropriate |
| **Apple Wallet** | Payment/card wallet and transaction/capture surface | Keep as a high-value mobile/payments surface; integrate through supported Shortcuts/intents rather than treating Wallet itself as canonical analytics state |
| **InUnity** | Main user-built financial platform and unifier. MoneyTalks is the same product/name lineage rather than a separate competing system. InUnity is intended to own the consolidated financial experience and state needed by the user's own finance stack | Treat as the primary user-owned finance system and main destination for data from specialized subsystems |
| **MoneyTalks** | Earlier/current naming for what is now InUnity, not a separate source of truth | Do not model MoneyTalks as a competing application. Treat references to MoneyTalks as InUnity unless a future explicit split is introduced |
| **PickMe** | Specialized credit-card recommendation / Card Copilot for best-card selection, purchase capture and card optimization | Keep specialized. PickMe sends relevant purchase/card data into InUnity; InUnity is the main consolidated destination/source for the broader finance experience |
| **MarketLens / marketdata** | Specialized market-data service used by InUnity | Keep as a provider/service feeding InUnity. Do not duplicate market-data acquisition logic inside InUnity unless intentionally replacing MarketLens |
| **Looply** | Receipts/bills/subscriptions workflow | Relationship to InUnity still needs explicit review. Avoid duplicate canonical receipt/bill/subscription state if both remain active |
| **Crypto.com** | Crypto exchange/account application | Keep as an external crypto institution/source system; do not store exchange credentials or keys in LLM4LIFE |
| **MetaMask / Phantom** | Self-custody wallet browser extensions | Keep isolated from general automation/browser trust boundaries; LLM4LIFE should never hold seed phrases/private keys |
| **Rakuten** | Cashback/rewards source | Keep for now; long term expose cashback opportunities through PickMe/InUnity/LLM4LIFE when reliable data access exists |

## Corrected product architecture

The user's finance stack is **not** a set of peer applications competing for ownership.

The intended shape is:

```text
External financial systems
Banks / card issuers / Wealthsimple / Crypto.com / Apple Wallet
                         |
                         v
                ingestion / normalization
                         |
                         v
                     InUnity
          main user-owned finance platform
                 /                 \
                /                   \
               v                     v
           PickMe                MarketLens
     card-decision specialist   market-data service
          |                         |
          +------ data/events ------+
                    into InUnity
```

### Ownership rule

- **InUnity is the main source for the user's consolidated finance system.**
- **MoneyTalks = InUnity**, not a separate product that needs independent ownership.
- **PickMe is specialized and feeds InUnity.** It should not become the broader finance source of truth.
- **MarketLens is specialized infrastructure used by InUnity.** It provides market data rather than owning the user's financial state.
- External banks, card issuers, exchanges and other regulated providers remain authoritative for their own official account records and execution.

## Production-grade direction

This is a strong architectural pattern and should be preserved unless later evidence suggests a better boundary:

```text
specialized producers/services -> stable contracts/events -> InUnity
```

Prefer explicit APIs/event contracts between PickMe, MarketLens and InUnity rather than shared-database coupling or duplicated tables across products.

Potential shared/canonical objects inside the InUnity domain may include:

- account
- card
- transaction
- merchant
- receipt
- bill/subscription
- reward/cashback opportunity
- budget/category
- portfolio/holding references

Market quotes and provider-specific raw data can remain owned by MarketLens where appropriate while InUnity consumes the normalized outputs it needs.

## Remaining finance architecture question

The main unresolved product boundary is **Looply**.

During implementation, determine whether Looply:

1. remains a specialized receipt/bill/subscription ingestion service feeding InUnity; or
2. is absorbed into InUnity if maintaining it separately provides no meaningful operational or architectural advantage.

Do not maintain the same canonical receipt, bill, subscription, or transaction state independently in both systems.

## Security boundaries

- Never store online-banking passwords, card credentials, crypto seed phrases, private keys, 2FA secrets, or recovery codes in the public LLM4LIFE repo.
- Use provider APIs/OAuth/official integrations where available.
- Secrets belong in secret managers or local/runtime environment configuration, not architecture docs.
- Crypto signing authority should remain isolated from autonomous AI/browser agents by default.

## Immediate implementation follow-up after inventory

- Treat InUnity as the central user-owned finance system when creating the system-of-record matrix.
- Document MoneyTalks as the same product/name lineage rather than a separate system.
- Define stable PickMe -> InUnity event/API contracts.
- Define stable MarketLens -> InUnity data contracts.
- Resolve Looply's role and eliminate any duplicate canonical finance state.
- Define ingestion adapters/events for Apple Wallet, email receipts, issuer/bank exports/APIs, Rakuten-like rewards data, and other external sources.
