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
- [`docs/decisions/2026-09-03-product-tracker-runtime.md`](docs/decisions/2026-09-03-product-tracker-runtime.md) — Product Tracker Cloudflare Worker/Queue runtime decision.
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
- Product Tracker has a parity-verified personal-care inventory mirror in Neon.
- Product Tracker's **Cloudflare Worker + Queue implementation is committed and CI-green, but deployment/runtime cutover is still pending**, so Notion remains the transitional inventory control surface.

Always use `docs/STATUS.md` for verified runtime state rather than inferring live status from target architecture.

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
 domain databases         relationships     Product Tracker
        |
        +------------+----------------------+
                     |                      |
                     v                      v
               Google Tasks          Google Calendar
                action UI            execution/time

Cloudflare = shared event/runtime layer where workloads fit
```

## Canonical responsibility map

| Domain | Owner / direction |
|---|---|
| LLM4LIFE machine state | **Neon/PostgreSQL** |
| Personal action state | **Neon/PostgreSQL** |
| Personal action UI | **Google Tasks** |
| Time commitments / execution schedule | **Google Calendar** |
| Shared event/runtime infrastructure | **Cloudflare** where workload fits; runtime only, not data owner |
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

## Why PostgreSQL exists

Neon/PostgreSQL is used for **machine-readable state LLM4LIFE or user-owned domain services need to operate reliably**, including stable IDs/references, actions, jobs/runs, events, idempotency, receipts, checkpoints, scheduling telemetry, maintenance state, structured shopping state where useful, and specialized user-owned domain databases such as Product Tracker.

It is **not** a dumping ground for narrative knowledge, full conversations, health records, credentials, or provider-owned official records.

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

Live planning automations use Neon canonical action state. Notion Tasks, Task Execution Log, Scheduling Model, and migrated AI Activity Log state are rollback/reference rather than operational task truth.

## Product Tracker / personal-care inventory

The long-term owner is a dedicated Product Tracker domain service backed by its own database inside the existing Neon project.

The data mirror is parity-verified; runtime cutover is intentionally incomplete.

Target runtime:

```text
ChatGPT / clients / Notion webhook
              |
              v
      Cloudflare Worker
    API / webhook ingress
              |
              v
             Neon
 canonical inventory/events
 outbox + webhook receipts
              |
              v
      Cloudflare Queue
 async projection / retries
              |
              v
 Notion projection / future clients
```

The normal path is event-driven. A low-frequency Cloudflare scheduled relay only republishes pending durable Product Tracker delivery rows if queue publication was missed; it does **not** poll Notion or recreate the old infinite database polling worker.

Cloudflare Workflows and Hyperdrive are optional future primitives only when justified. Neon remains canonical inventory state.

See [`docs/decisions/2026-09-03-product-tracker-runtime.md`](docs/decisions/2026-09-03-product-tracker-runtime.md).

## Obsidian

Obsidian remains the private, human-readable knowledge/context layer for learning, reasoning, durable research/context, reflections, and relationship narrative.

Preferred eventual AI write path:

```text
AI/router -> trusted local adapter -> live Obsidian vault -> normal backup/sync
```

## Contacts

Target identity model:

```text
Google Contacts -> canonical identity/contact facts
Apple Contacts  -> synchronized Apple-device client
Obsidian        -> person/relationship narrative context
```

Deduplicate before consolidating.

## Household operations

Neon is the target structured owner for household/vehicle assets, maintenance rules, and maintenance events. Due work becomes a personal action; only scheduled execution belongs on Calendar.

General shopping/grocery state should be structured only when automation provides real value. Personal-care inventory stays in Product Tracker rather than being flattened into generic shopping rows.

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

Provider systems remain authoritative for official records/execution. LLM4LIFE must not become a parallel financial ledger or credential store.

## Engineering

- **Jira** — engineering backlog/bugs/work items.
- **GitHub** — code/repository truth.
- **ORC** — coding-agent orchestration and verification.
- **LLM4LIFE** — routes/invokes rather than duplicating those systems.

## Communication and capture

Gmail, Slack, Discord, WhatsApp, iMessage, Shortcuts, Share Sheet, and future bridges are ingress/source surfaces.

```text
many ingress channels -> one LLM4LIFE routing policy -> correct canonical owner
```

A bridge is replaceable infrastructure, not a second policy authority or database.

## Durable automation

ChatGPT Automations, Cloudflare Workers/Queues/Workflows, Vercel Functions for fitting web workloads, cron, or dedicated workers may execute jobs depending on workload.

The runtime is replaceable. Important LLM4LIFE-owned jobs require durable identity, idempotency, receipts, retry/failure policy, observability, and checkpoints where appropriate. Chat threads are not durable job state.

## Free-first constraint

1. capability already paid for;
2. strong free tier;
3. open-source/self-hosted when operationally reasonable;
4. new paid product only when incremental value materially justifies recurring cost.

**Production-grade does not mean more subscriptions or more enterprise complexity.**

## Migration rules

1. Migrate one domain at a time.
2. Preserve working legacy state until replacement parity/runtime behavior is verified.
3. Temporary dual-read is acceptable; long-term dual-write is not.
4. Keep stable provenance/external references.
5. Prefer idempotent/event-driven adapters over hidden vendor coupling.
6. Update `docs/STATUS.md` only when runtime reality changes.
7. Update roadmap/decisions when the target changes.
8. Preserve superseded decisions as historical context.

## Repository map

```text
README.md                           Human entry point
AGENTS.md                           Agent operating instructions
system.yaml                         Machine architecture/policy
config/                             Domain/tool/automation/scheduling registries
db/                                 PostgreSQL migrations/contracts
docs/LONG_TERM_ROADMAP.md           North star + migration scoreboard
docs/STATUS.md                      Verified live state
docs/TOOL_REGISTRY.md               Human tool/runtime registry
docs/decisions/                     Dated architecture decisions
```

## Security

`LLM4LIFE` is public. Never commit real database URLs, passwords/tokens, private contact/relationship information, health records, financial identifiers, confidential work content, private messages, or other sensitive operational state.
