# Tool Registry

_Last updated: 2026-09-03_

This registry separates **target ownership**, **current runtime status**, and **user-facing interfaces**. See `config/tools.yaml` for machine-readable detail, `docs/STATUS.md` for live migration status, and `docs/LONG_TERM_ROADMAP.md` for the durable end-state plan.

## Core systems

| Tool | v2 role | Runtime status | Important boundary |
|---|---|---|---|
| **ChatGPT** | Primary conversational/control surface | Connected | Router/orchestrator, not durable chat-state |
| **Neon / PostgreSQL** | Durable LLM4LIFE machine state + domain DB host | **Connected/live** | Canonical personal actions; hosts Product Tracker DB |
| **Cloudflare** | Shared edge/event runtime for fitting LLM4LIFE backends | **Google Tasks live; Product Tracker code ready** | Runtime, queues and retries; not canonical data owner |
| **Google Tasks** | Preferred personal-action client | **Production-live v0.2.0** | Human UI/capture for Neon actions |
| **Google Calendar** | Commitments + execution schedule | Connected/live | Calendar is schedule, not backlog |
| **Product Tracker** | Target personal-care inventory owner | **Neon mirror live; Cloudflare deployment pending** | Owns SKU/balance/event/reorder semantics |
| **Notion** | Rollback/reference + transitional inventory control | Connected | Planning not canonical; inventory remains live until Product Tracker cutover |
| **Vercel** | Web-app runtime where still best fit | User-live | No longer Product Tracker target; evaluate per project |
| **Google Contacts** | Preferred canonical address book after migration | Connector available; migration incomplete | Contact identity, not relationship narrative |
| **Apple Contacts** | Current synced/device contact client | User-live | Should not remain independent second truth after migration |
| **Obsidian** | Narrative knowledge and relationship context | Partial through backup path | Preferred future write path is trusted live-vault bridge |
| **Things 3** | Legacy/optional task UX | User-live | Not canonical |
| **Jira** | Engineering backlog | Connector available | Engineering work does not belong in personal backlog |
| **GitHub** | Code/repository truth | Connected read/write | Not a personal-life database |
| **ORC** | Coding-agent orchestration | External subsystem | LLM4LIFE invokes rather than duplicates it |
| **InUnity** | Consolidated finance | **MCP complete / recently read-verified** | Providers remain official authorities |
| **Gmail / Slack** | Source/communication surfaces | Connected | Route durable state to domain owners |

## Google Tasks production integration

```text
Google Tasks
    ^  |
    |  v
Cloudflare Worker v0.2.0
    ^  |
    |  v
Neon canonical actions

Google Calendar = execution time
```

Verified:

- `llm4life-google-tasks-sync` deployed;
- OAuth complete;
- manual + scheduled sync succeeded;
- 14 Google Tasks bindings;
- both checkpoints present;
- durable sync job enabled.

## Product Tracker

Personal-care inventory is deliberately separate from generic shopping state.

Current data state:

- 25 active Needs;
- 26 active Products;
- 26 balances;
- 26 baseline events;
- zero orphan records;
- zero baseline/balance mismatches.

### Cloudflare target runtime

```text
ChatGPT / clients / Notion webhook
              |
              v
      Cloudflare Worker
              |
              v
             Neon
 inventory/events + outbox/receipts
              |
              v
      Cloudflare Queue
 async projection / retries
              |
              v
 Notion projection / future effects
```

Implemented in `zubairmuwwakil/Product_Tracker`:

- Worker HTTP API/webhook entrypoint;
- Queue producer + consumer;
- durable exact-by-ID outbox/webhook processors;
- DLQ/retry configuration;
- scheduled 5-minute reconciliation of **pending Product Tracker delivery state only**;
- Wrangler dry-run CI validation;
- dependency audit/typecheck/tests/Prisma CI all green.

The scheduled relay is not normal polling and does not query Notion. It repairs the transaction-vs-queue-publish gap by republishing durable Neon rows that remain due.

Notion is still the inventory control surface until live Cloudflare verification passes. The mirror plus CI-green code does **not** equal cutover.

Cloudflare Workflows and Hyperdrive are optional future additions only when justified; neither is required for initial deployment.

See `docs/decisions/2026-09-03-product-tracker-runtime.md`.

## Canonical ownership shortcut

```text
LLM4LIFE machine state       -> Neon/PostgreSQL
Personal actions             -> Neon
Personal action client       -> Google Tasks
Shared event/runtime layer   -> Cloudflare where workload fits
Scheduled execution          -> Google Calendar
Personal-care inventory now  -> Notion control + verified Product Tracker mirror
Personal-care target owner   -> Product Tracker / Neon
Product Tracker target host  -> Cloudflare Worker + Queue
General shopping/list state  -> Neon when structured automation is justified
Engineering work             -> Jira
Code/repository truth        -> GitHub
Coding-agent orchestration   -> ORC
Knowledge/reasoning          -> Obsidian
Relationship context         -> Obsidian
Contact identity             -> Google Contacts after migration
Consolidated finance         -> InUnity
Official provider state      -> respective provider
```

## Runtime verification rule

Before claiming a tool/runtime is live:

1. inspect `docs/STATUS.md` and `config/tools.yaml`;
2. perform a harmless live read when possible;
3. only claim a write/runtime cutover after an actual supported operation succeeds;
4. distinguish target architecture from deployed reality.

## Free-first / component review

Prefer already-paid capability, then strong free tiers/open source, then paid services only for material incremental value. No tool is retained merely because it is already in the stack; evaluate **keep / reposition / consolidate / replace / retire** as architecture evolves.
