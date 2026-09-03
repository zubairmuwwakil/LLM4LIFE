# LLM4LIFE

LLM4LIFE is an **AI-driven personal operating system**: a control/orchestration layer that lets AI work across the user's life systems without making chat history, one SaaS app, or one giant database responsible for everything.

> **Core idea:** one canonical owner per object/domain; AI provides the universal interface and orchestration layer.

## Governing rule: nothing is grandfathered

Current tools are not permanent merely because they are already in use. Every meaningful component can be **kept, repositioned, consolidated, replaced, or retired** when a materially better long-term design is justified on reliability, scalability, security, integration quality, maintainability, portability, cost, or UX.

Change for novelty alone is not a goal. Production-grade also does not mean maximizing subscriptions or infrastructure complexity.

## Start here

- [`docs/LONG_TERM_ROADMAP.md`](docs/LONG_TERM_ROADMAP.md) — durable north star, migration sequence, and done gates.
- [`docs/STATUS.md`](docs/STATUS.md) — what is actually live now.
- [`system.yaml`](system.yaml) — machine-readable architecture and governing policy.
- [`docs/decisions/2026-09-02-production-architecture-v2.md`](docs/decisions/2026-09-02-production-architecture-v2.md) — adopted v2 ownership architecture.
- [`docs/decisions/2026-09-03-product-tracker-runtime.md`](docs/decisions/2026-09-03-product-tracker-runtime.md) — Product Tracker Vercel/event-driven runtime decision.
- [`config/domains.yaml`](config/domains.yaml) — detailed domain ownership.

## Current phase

**v2 production migration is active.** The foundation and personal-action cutover are already live; remaining domains are migrated incrementally with rollback preserved.

Current major runtime facts:

- Neon/PostgreSQL is the live LLM4LIFE machine-state backend.
- Personal actions are canonical in Neon.
- Google Tasks is the production-live human action client/projection.
- Google Calendar remains execution/time ownership.
- Cloudflare Worker v0.2.0 runs the Google Tasks sync every 15 minutes.
- Notion planning databases are rollback/reference, not canonical task state.
- InUnity remains the consolidated finance owner and its ChatGPT MCP path has been exercised successfully.
- Product Tracker has a parity-verified personal-care inventory mirror in a dedicated Neon database; runtime cutover is still pending, so Notion remains the transitional inventory control surface.

Always use `docs/STATUS.md` for the latest verified runtime state rather than inferring live status from target architecture.

## v2 architecture

```text
                     USER / CHANNELS
 ChatGPT · Gmail · Slack · Discord · Shortcuts · Share Sheet · local bridges
                            |
                            v
                 LLM4LIFE CONTROL PLANE
                classify · route · orchestrate
                            |
        +-------------------+-------------------+
        |                   |                   |
        v                   v                   v
 Neon/PostgreSQL         Obsidian          Domain systems
 machine state           knowledge         Jira / GitHub
 jobs/actions/events      reasoning         ORC / InUnity
 receipts/sync state      relationships     Product Tracker
        |
        +------------+----------------------+
                     |                      |
                     v                      v
               Google Tasks          Google Calendar
                action UI            execution/time
```

## Canonical responsibility map

| Domain | Owner / direction |
|---|---|
| LLM4LIFE machine state | **Neon/PostgreSQL** |
| Personal action state | **Neon/PostgreSQL** |
| Personal action UI | **Google Tasks** |
| Time commitments / execution schedule | **Google Calendar** |
| Personal-care inventory | **Product Tracker / Neon** after verified runtime cutover; Notion transitional until then |
| Contact identity | **Google Contacts** after Apple/Google dedup migration |
| Knowledge, reasoning, learning | **Obsidian** |
| Relationship context | **Obsidian** |
| Engineering backlog | **Jira** |
| Code/repository truth | **GitHub** |
| Coding-agent orchestration | **ORC** (`agent-orchestrator`) |
| Consolidated personal finance | **InUnity** |
| Official bank/card/provider state | respective provider |
| Cloud files | **Google Drive** preferred; OneDrive secondary after audit |

See [`config/domains.yaml`](config/domains.yaml) and [`docs/LONG_TERM_ROADMAP.md`](docs/LONG_TERM_ROADMAP.md) for the complete ownership/migration model.

## Why PostgreSQL exists

Neon/PostgreSQL is used for **machine-readable state LLM4LIFE or user-owned domain services need to operate reliably**, including:

- stable internal IDs and external references;
- personal actions;
- jobs and job runs;
- normalized events;
- idempotency/deduplication state;
- execution/action receipts;
- sync checkpoints;
- adaptive scheduling rules and execution telemetry;
- household/vehicle maintenance;
- structured shopping state where useful;
- specialized user-owned domain databases such as Product Tracker.

It is **not** a dumping ground for narrative knowledge, relationship journals, full conversations, health records, financial credentials, or provider-owned official records.

## Personal actions and planning — live

```text
                 Neon canonical actions
                    /             \
                   v               v
            Google Tasks       AI planner
             action UX             |
                                   v
                           Google Calendar
                            execution/time
```

The planning cutover is complete enough that live planning automations use Neon canonical action state. Notion Tasks, Task Execution Log, Scheduling Model, and AI Activity Log are rollback/reference for migrated planning data.

Current scheduling defaults include:

- sleep **11 PM–7 AM** protected;
- weekday work **9 AM–1 PM** soft-busy;
- movable personal work defaults to **1 PM–9 PM America/Toronto**;
- waiting/blocked actions do not consume execution time;
- due dates and execution times are distinct;
- repeated misses are evidence for adaptation rather than blind rescheduling.

See [`docs/AUTOMATIONS.md`](docs/AUTOMATIONS.md) and [`config/automations.yaml`](config/automations.yaml).

## Product Tracker / personal-care inventory

The long-term owner is a dedicated Product Tracker domain service backed by its own database inside the existing Neon project.

The data mirror is already parity-verified, but runtime cutover is intentionally incomplete.

Target runtime:

```text
ChatGPT / clients / Notion webhook
              |
              v
        Product Tracker API
        Vercel Functions
              |
              v
             Neon
 canonical inventory/event state
              |
              v
 durable Vercel async processing
              |
              v
 Notion projection / future clients
```

The existing infinite polling worker is transitional implementation debt. The target is event-driven processing with durable retry semantics, not choosing a host merely to keep a polling loop alive.

See [`docs/decisions/2026-09-03-product-tracker-runtime.md`](docs/decisions/2026-09-03-product-tracker-runtime.md).

## Obsidian

Obsidian remains the private, human-readable knowledge/context layer for learning, reasoning, durable research/context, reflections, and relationship narrative.

Preferred eventual AI write path:

```text
AI/router -> trusted local adapter -> live Obsidian vault -> normal backup/sync
```

GitHub backup access is useful but is not the desired permanent real-time editing path.

## Contacts

Target identity model:

```text
Google Contacts -> canonical phone/email/address/birthday/org identity
Apple Contacts  -> synchronized Apple-device client
Obsidian        -> person/relationship narrative context
```

Deduplicate before consolidating; never destroy one address book simply because the target has been chosen.

## Household operations

Neon is the target structured owner for household/vehicle assets, maintenance rules, and maintenance events. Due work becomes a personal action; only actual scheduled execution belongs on Calendar.

General shopping/grocery state should be structured only when automation provides real value. Avoid creating a new paid list-app dependency by default.

## Finance

```text
External financial providers
          |
          v
        InUnity
    consolidated finance
       ^          ^
       |          |
    PickMe    MarketLens
```

- InUnity owns consolidated user-controlled finance state.
- PickMe specializes in card decisions/purchase capture.
- MarketLens specializes in market data.
- Provider systems remain authoritative for their official records and execution.
- LLM4LIFE must not become a second financial ledger or credential store.

## Engineering

- **Jira** — engineering backlog/bugs/work items.
- **GitHub** — code/repository truth.
- **ORC** — coding-agent routing, quota-aware escalation, independent verification, and cross-vendor review.
- **LLM4LIFE** — invokes/routes these systems; it does not duplicate their canonical state.

## Communication and capture

Gmail, Slack, Discord, WhatsApp, iMessage, Apple Shortcuts, Share Sheet, and future bridges are ingress/source surfaces.

Preferred shape:

```text
many ingress channels -> one LLM4LIFE routing policy -> correct canonical owner
```

A bridge is replaceable infrastructure, not a second policy authority or database.

## Durable automation

ChatGPT Automations, Cloudflare Workers, Vercel Functions/Queues/Workflows, cron, or dedicated workers may execute jobs depending on workload.

The runtime is replaceable. Important LLM4LIFE-owned jobs require durable identity, idempotency, execution receipts, retry/failure policy, observability, and checkpoints where appropriate. Chat threads are not durable job state.

## Free-first constraint

Tool decisions follow this order:

1. capability already paid for;
2. strong free tier;
3. open-source/self-hosted option when operationally reasonable;
4. new paid product only when incremental value clearly justifies recurring cost.

**Production-grade does not mean more subscriptions or more enterprise complexity.**

## Migration rules

1. Migrate one domain at a time.
2. Preserve working legacy state until replacement parity/runtime behavior is verified.
3. Temporary dual-read is acceptable; long-term dual-write is not.
4. Keep stable provenance/external references.
5. Prefer idempotent/event-driven adapters over hidden vendor coupling.
6. Update `docs/STATUS.md` only when runtime reality changes.
7. Update the long-term roadmap/decision records when the target changes.
8. Preserve superseded decisions as historical context.

## Repository map

```text
README.md                           Human entry point
AGENTS.md                           Agent operating instructions
system.yaml                         Machine architecture/policy

config/
  domains.yaml                      Canonical domain ownership
  tools.yaml                        Runtime/tool registry
  automations.yaml                  Live automation responsibility registry
  scheduling.yaml                   Scheduling defaults

db/
  README.md                         Database role/migration policy
  migrations/                       PostgreSQL schema migrations

docs/
  LONG_TERM_ROADMAP.md              North star + migration scoreboard
  STATUS.md                         What is actually live now
  TOOL_REGISTRY.md                  Human tool inventory
  CURRENT_STATE.md                  Architecture narrative
  ROUTING.md                        Routing logic
  PLANNING.md                       Planning/action model
  AUTOMATIONS.md                    Automation loop
  SECURITY.md                       Public/private boundary
  inventory/                        Full software/life inventory
  decisions/                        Dated architecture decisions
```

## Security

`LLM4LIFE` is public.

Never commit real database URLs, passwords/tokens, private contact or relationship information, health records, financial identifiers, confidential work content, private messages, or other sensitive operational state.

Architecture, schemas, variable **names**, placeholders, and non-sensitive contracts belong here.
