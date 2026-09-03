# Tool Registry

_Last updated: 2026-09-03_

This registry separates **target ownership**, **current runtime status**, and **user-facing interfaces**. See `config/tools.yaml` for machine-readable detail and `docs/STATUS.md` for live migration status.

## Core systems

| Tool | v2 role | Runtime status | Important boundary |
|---|---|---|---|
| **ChatGPT** | Primary conversational/control surface | Connected | Router/orchestrator, not durable state stored only in chat |
| **Neon / PostgreSQL** | Durable LLM4LIFE machine-state backend + domain DB host | **Connected/live** | Canonical personal actions; also hosts dedicated Product Tracker DB |
| **Google Tasks** | Preferred user-facing personal action client | **Production-live v0.2.0** | Human UI/capture surface for Neon actions; not canonical rich domain state |
| **Cloudflare** | Edge runtime for Google Tasks projection | **Production-live Worker** | Runs Google Tasks sync every 15 minutes |
| **Google Calendar** | Commitments + execution schedule | Connected/live | Calendar blocks are projections of actions, not the permanent backlog |
| **Product Tracker** | Target canonical personal-care inventory domain service | **Neon mirror live; hosted runtime pending** | Owns SKU/balance/event/reorder semantics; generic shopping_items do not |
| **Notion** | Rollback/reference for planning + transitional personal-care control surface | Connected | Planning not canonical; inventory remains live until Product Tracker runtime cutover |
| **Google Contacts** | Preferred canonical address book after migration | Connector available; migration incomplete | Identity/contact facts, not relationship narrative |
| **Apple Contacts** | Current address-book client/source | User-live | Intended to become synced client after dedup migration |
| **Obsidian** | Narrative knowledge, learning, diary, relationship context | Partial through private GitHub backup | Preferred future write path is a trusted local-vault bridge |
| **Things 3** | Legacy/optional task UX | User-live | Not canonical in v2 |
| **Jira** | Engineering backlog/bugs/work items | Atlassian connector available; verify per operation | Do not mirror engineering backlog into personal tasks |
| **GitHub** | Code/repository truth + LLM4LIFE public architecture | Connected read/write | Not a personal-life database |
| **ORC** | Coding-agent orchestration subsystem | External repo/subsystem | LLM4LIFE invokes ORC; does not duplicate its routing/verification logic |
| **InUnity** | Consolidated user-owned finance system | **ChatGPT MCP integration complete; recently read-verified** | PickMe/MarketLens feed it; provider systems remain official record/execution owners |
| **Gmail** | Email/source/intake surface | Connected capability | Route durable actions/state elsewhere |
| **Slack** | Work communication/automation surface | Connected capability | Communication, not canonical task state |
| **Discord** | Preferred historical personal AI/channel surface | User-live; no direct ChatGPT connector assumed | Requires verified bridge for AI access |
| **WhatsApp** | Personal communication / optional AI channel | User-live | Bridge/API verification required |
| **iMessage** | Personal communication source | User-live | Likely requires trusted local Mac bridge |
| **OpenClaw** | Optional channel/local-integration plumbing | Provisional | Not a database or second policy authority |

## Google Tasks production integration

```text
Google Tasks
    ^  |
    |  v
Cloudflare Worker v0.2.0
    ^  |
    |  v
Neon/PostgreSQL canonical actions

Google Calendar = execution time
```

Verified current production state:

- Worker `llm4life-google-tasks-sync` deployed on v0.2.0;
- Google OAuth completed;
- manual sync succeeded;
- scheduled cron succeeded;
- 14 Google Tasks action bindings verified in Neon;
- both Google Tasks checkpoints verified;
- durable `google-tasks-sync` job enabled.

v0.2.0 batches Neon SQL and Google mutations, uses incremental Google reads with overlap, and keeps existing idempotent external-ref/checkpoint/run-key safeguards.

## Product Tracker inventory migration

Personal-care inventory is richer than a normal shopping list, so it has a dedicated domain service rather than being flattened into `llm4life.shopping_items`.

```text
Notion Shopping Needs / Personal Care Products
              | transitional control
              v
        Product Tracker
              |
              v
Neon / product_tracker database
  InventoryNeed
  Product
  InventoryBalance
  InventoryEvent
  OutboxEvent
  WebhookReceipt
```

Current verified mirror:

- 25 active Needs;
- 26 active Products;
- 26 balances;
- 26 import baseline events;
- zero orphan records;
- zero balance/baseline mismatches.

The mirror is **not** equivalent to write cutover. Notion stays live for personal-care edits until the hosted Product Tracker API/webhook/outbox path is verified. After cutover, meaningful inventory writes must flow through Product Tracker events and Notion becomes projection/rollback UI.

Product Tracker has been refactored so the same transactional queue runtime can either run as a dedicated worker or in-process with the web API. A free-first single-service Render Blueprint is prepared for runtime verification; a dedicated always-on worker remains the upgrade path if needed later.

## InUnity MCP

InUnity remains the finance-domain owner and has a completed ChatGPT MCP integration. A recent `get_attention_summary` read was successfully exercised. Because the InUnity namespace is not surfaced in every ChatGPT session, agents should re-check live tool availability before a finance call rather than treating the integration as absent.

## Storage/file systems

| Tool | Direction |
|---|---|
| **Google Drive** | Preferred canonical cloud file store |
| **OneDrive** | Secondary/exception-only after audit |
| **Time Machine** | Local disaster recovery, separate from sync |

## Canonical ownership shortcut

```text
LLM4LIFE machine state       -> Neon/PostgreSQL
Personal actions             -> Neon backend
Personal action client       -> Google Tasks
Personal-action sync         -> Cloudflare Worker
Scheduled execution          -> Google Calendar
Personal-care inventory now  -> Notion control + verified Product Tracker mirror
Personal-care target owner   -> Product Tracker on Neon after runtime cutover
General shopping/list state  -> LLM4LIFE generic shopping tables as appropriate
Engineering work             -> Jira
Code/repository truth        -> GitHub
Coding-agent orchestration   -> ORC
Knowledge/reasoning          -> Obsidian
Relationship context         -> Obsidian
Contact identity             -> Google Contacts after migration
Consolidated finance         -> InUnity
Finance ChatGPT interface    -> InUnity MCP when surfaced/verified
Official provider state      -> respective provider
Email/source context         -> Gmail
Work communication           -> Slack
```

## Migration reality

The personal planning backend has moved from Notion to Neon and Google Tasks is a live client/projection. Personal-care inventory has reached the **verified mirror** stage in Product Tracker/Neon, but Notion has not yet been demoted because the hosted event-write + webhook/outbox runtime still needs end-to-end verification.

## Runtime verification rule

Before claiming a tool is usable for the current operation:

1. inspect `docs/STATUS.md` and `config/tools.yaml`;
2. perform a harmless read if the task depends on live access;
3. only claim a write succeeded after a real supported write succeeds;
4. distinguish user usage, policy authorization, target ownership and technical connectivity.

## Free-first rule

Prefer capabilities already paid for, then strong free tiers/open-source options. Add a new paid product only when it provides a material advantage that existing/free capabilities cannot reasonably deliver.
