# LLM4LIFE

LLM4LIFE is an **AI-driven personal operating system**: a control/orchestration layer that lets AI work across the user's life systems without making chat history, one SaaS app, or one giant database responsible for everything.

> **Core idea:** one canonical owner per object/domain; AI provides the universal interface and orchestration layer.

## Governing rule: nothing is grandfathered

Current tools are not permanent merely because they are already in use. Every meaningful component can be **kept, repositioned, consolidated, replaced, or retired** when a materially better long-term design is justified on reliability, scalability, security, integration quality, maintainability, portability, cost, or UX.

Change for novelty alone is not a goal. Production-grade also does not mean maximizing subscriptions or infrastructure complexity.

## Start here

- [`AGENTS.md`](AGENTS.md) — mandatory operating rules for development agents.
- [`docs/STATUS.md`](docs/STATUS.md) — what is actually live now.
- [`docs/LONG_TERM_ROADMAP.md`](docs/LONG_TERM_ROADMAP.md) — durable north star, migration sequence, and done gates.
- [`system.yaml`](system.yaml) — machine-readable architecture and governing policy.
- [`config/domains.yaml`](config/domains.yaml) — detailed domain ownership.
- [`docs/PEOPLE.md`](docs/PEOPLE.md) — People/Contacts/Relationships implementation contract.
- [`docs/decisions/2026-09-03-people-subsystem-architecture.md`](docs/decisions/2026-09-03-people-subsystem-architecture.md) — newest People architecture decision.
- [`docs/decisions/2026-09-02-production-architecture-v2.md`](docs/decisions/2026-09-02-production-architecture-v2.md) — adopted v2 base architecture.

## Current phase

**v2 production migration is active.** Major domains are migrated one at a time with explicit ownership, reconciliation gates and rollback.

Current major runtime facts:

- Neon/PostgreSQL is the live LLM4LIFE machine-state backend.
- Personal actions are canonical in Neon.
- Google Tasks is the production-live human action client/projection.
- Google Calendar owns execution/time.
- Notion planning databases are rollback/reference rather than canonical task state.
- InUnity remains the consolidated finance owner.
- Product Tracker/Neon is the **production canonical** personal-care inventory owner.
- Product Tracker Worker `v0.4.0`, Queue, Hyperdrive, durable reliability status/DLQ receipts and stable Notion event-idempotency hardening are live.
- People / Relationships has advanced to **Phase 1 schema live**: the production Neon People schema exists, but no real contacts have been imported, merged, or cut over yet.

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
 structured domains       narrative         Product Tracker
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
| Personal-care inventory | **Product Tracker / Neon**; Notion projection/reference/rollback |
| Stable person identity | **Neon**; schema live, real identity import pending |
| Structured relationship machine state | **Neon**; schema live, real data import pending |
| Address-book human client | **Google Contacts** after People dedup/cutover |
| Apple-device contacts | **Apple Contacts** as synchronized client after migration |
| Knowledge, reasoning, learning | **Obsidian** |
| Relationship narrative/context | **Obsidian** |
| Engineering backlog | **Jira** |
| Code/repository truth | **GitHub** |
| Coding-agent orchestration | **ORC** (`agent-orchestrator`) |
| Consolidated personal finance | **InUnity** |
| Official bank/card/provider state | respective provider |
| Cloud files | **Google Drive** preferred; OneDrive secondary after audit |

## Why PostgreSQL exists

Neon/PostgreSQL is used for **machine-readable state LLM4LIFE or user-owned domain services need to operate reliably**, including stable IDs/references, actions, jobs/runs, events, idempotency, receipts, checkpoints, scheduling telemetry, maintenance state, structured shopping state where useful, Product Tracker, and the structured People layer.

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

Live planning automations use Neon canonical action state. Notion planning state is rollback/reference rather than operational task truth.

## Product Tracker / personal-care inventory — live

```text
ChatGPT / clients
      |
      v
Cloudflare Worker v0.4.0
      |
      v
 Hyperdrive -> Neon
 canonical inventory/events
 durable outbox + webhook receipts
 dead-letter receipts
      |
      v
Cloudflare Queue
 retries + reconciliation
      |
      v
Notion projection / rollback UI
```

Production has Notion inbound sync disabled. All canonical inventory mutations route through Product Tracker domain events.

The system includes durable retry/reconciliation, DLQ observability and a stable `Product Tracker Event ID` on Notion Inventory Events so projection retries query-before-create instead of recreating a page after the known create-then-pointer failure window.

A short post-cutover observation/staging-cleanup step remains operational closeout, not an ownership blocker.

## People / Contacts / Relationships — Phase 1

**Current phase: production People schema live; read-only inventory/reconciliation incomplete.**

Live structured layer:

```text
                     Neon People state
        stable person_id + generic external_refs
      structured relationship/fact/interaction state
              /              |              \
             v               v               v
    Google Contacts      LLM4LIFE actions   source refs
   address-book client      follow-ups
          |                    |
          v                    v
   Apple Contacts        Google Tasks

Obsidian = narrative relationship memory
Google Calendar = scheduled interactions
```

Key runtime facts:

- `004_people.sql` is deployed to production Neon;
- People uses generic `llm4life.external_refs`, not a second `person_external_refs` table;
- existing external refs were preserved through migration;
- no real People/contact rows have been imported yet;
- same-name-only auto-merge is prohibited;
- structured facts require provenance;
- sensitive model inference is not silently persisted;
- raw private conversations are not archived by default;
- relationship follow-ups reuse the existing action system;
- Obsidian remains the narrative/reflective layer;
- Google/Apple field ownership has not been cut over.

Current evidence conditionally favors Google Contacts as the mutable address-book field owner after reconciliation, but complete Apple/iCloud inventory and explicit cutover approval are still required.

See [`docs/PEOPLE.md`](docs/PEOPLE.md) and [`docs/people/PHASE_1_REPORT.md`](docs/people/PHASE_1_REPORT.md).

## Obsidian

Obsidian remains the private, human-readable knowledge/context layer for learning, reasoning, durable research/context, reflections, and relationship narrative.

Preferred eventual AI write path:

```text
AI/router -> trusted local adapter -> live Obsidian vault -> normal backup/sync
```

The People subsystem should link structured identities to Obsidian notes rather than copying narrative prose into Neon.

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

A bridge is replaceable infrastructure, not a second policy authority or database. For People, communication systems may be sources/references for meaningful interactions but are not automatically copied into a private conversation warehouse.

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
8. Preserve superseded decisions/inventories as historical context.
9. For People, complete read-only inventory/dedup analysis before real source mutations.

## Repository map

```text
README.md                           Human entry point
AGENTS.md                           Agent operating instructions
system.yaml                         Machine architecture/policy
config/                             Domain/tool/automation/scheduling registries
db/                                 PostgreSQL migrations/contracts
docs/PEOPLE.md                      People subsystem implementation contract
docs/people/PHASE_1_REPORT.md       People Phase 1 receipts and remaining gates
docs/LONG_TERM_ROADMAP.md           North star + migration scoreboard
docs/STATUS.md                      Verified live state
docs/TOOL_REGISTRY.md               Human tool/runtime registry
docs/decisions/                     Dated architecture decisions
```

## Security

`LLM4LIFE` is public. Never commit real database URLs, passwords/tokens, private contact/relationship information, health records, financial identifiers, confidential work content, private messages, or other sensitive operational state. Use synthetic People fixtures in code/tests.
