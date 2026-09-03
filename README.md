# LLM4LIFE

LLM4LIFE is an **AI-driven personal operating system**: a control/orchestration layer that lets AI work across the user's life systems without making chat history, one SaaS app, or one giant database responsible for everything.

The architecture is deliberately revisitable. Current tools are replaceable when a more reliable, scalable, lower-cost or better-integrated design is justified.

> **Core idea:** one canonical owner per object/domain; AI provides the universal interface and orchestration layer.

## Current phase

**v2 migration started — 2026-09-02.**

A full inventory of the user's software, services, devices, personal workflows and side-project ecosystem is complete. The first production-grade backend/contracts are now committed.

See:

- [`docs/decisions/2026-09-02-production-architecture-v2.md`](docs/decisions/2026-09-02-production-architecture-v2.md)
- [`config/domains.yaml`](config/domains.yaml)
- [`system.yaml`](system.yaml)
- [`docs/STATUS.md`](docs/STATUS.md)

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
 receipts/sync state      relationships     provider authority
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
| Contact identity | **Google Contacts** after Apple/Google dedup migration |
| Knowledge, reasoning, learning | **Obsidian** |
| Relationship context | **Obsidian** |
| Engineering backlog | **Jira** |
| Code/repository truth | **GitHub** |
| Coding-agent orchestration | **ORC** (`agent-orchestrator`) |
| Consolidated personal finance | **InUnity** |
| Official bank/card/provider state | respective provider |
| Cloud files | **Google Drive** preferred; OneDrive secondary after audit |

See [`config/domains.yaml`](config/domains.yaml) for the complete machine-readable domain matrix.

## Why PostgreSQL now exists

The old architecture relied too heavily on SaaS applications and chat/automation context for operational state.

Neon/PostgreSQL is introduced only for **machine-readable state LLM4LIFE itself needs to operate reliably**, such as:

- stable internal IDs and external references;
- personal actions;
- jobs and job runs;
- normalized events;
- idempotency/deduplication state;
- execution/action receipts;
- sync checkpoints;
- adaptive scheduling rules and execution telemetry;
- household/vehicle maintenance;
- grocery/shopping-list state.

It is **not** a dumping ground for narrative knowledge, relationship journals, full conversations, health records or provider credentials.

## Database migrations

```text
db/
  README.md
  migrations/
    001_core.sql
    002_actions_and_adaptation.sql
```

The schema is PostgreSQL-first and portable even though Neon is the current hosted target.

The migrations have been committed but are **not yet applied to the live Neon project**. See `docs/STATUS.md`.

## Obsidian

Obsidian remains the private, human-readable knowledge/context layer:

- learning and reasoning;
- durable notes/research;
- diary/reflections;
- person/relationship context;
- long-form personal knowledge.

The existing People system's `link, don't copy` pattern is intentionally preserved. Relationship automation should first use structured frontmatter + derived views rather than creating a second relationship database prematurely.

The preferred eventual AI write path is:

```text
AI/router -> trusted local adapter -> live Obsidian vault -> normal backup/sync
```

GitHub backup access is useful but is not the desired permanent real-time editing architecture.

## Personal actions and planning

Target model:

```text
Neon personal actions             Jira engineering backlog
         \                              /
          \                            /
             AI planner / scheduler
                      |
                      v
              Google Calendar
               execution plan

Neon -> Google Tasks for human action-list UX
```

Current scheduling defaults:

- sleep **11 PM–7 AM** protected;
- weekday work **9 AM–1 PM** soft-busy;
- movable personal work defaults to **1 PM–9 PM America/Toronto**;
- leave buffer;
- waiting/blocked actions do not consume execution time;
- fixed external commitments do not move for optimization;
- repeated misses feed adaptive scheduling rather than blind daily rescheduling.

## Live automation loop

Current active automation responsibilities:

```text
07:30  Daily Planning Loop — morning sanity check
19:30  Daily Planning Loop — tomorrow / rolling-horizon planning
hourly Calendar Task Follow-Up — execution outcome feedback
Friday 17:00-ish Weekly Systems Review — reconciliation + learning + restock
```

These automations currently use **transitional Notion-backed state**. They are not being disabled until the Neon replacement is populated and verified.

See [`docs/AUTOMATIONS.md`](docs/AUTOMATIONS.md) and [`config/automations.yaml`](config/automations.yaml).

## Notion and Things 3

### Notion

Notion is repositioned from canonical life backend to:

- transitional live dependency during migration;
- optional dashboard/projection layer;
- ad-hoc structured workspace where it provides real human UX value.

Do not create new core state in Notion merely because a database is easy to add.

### Things 3

Things 3 becomes legacy/optional UX rather than the v2 canonical backlog. Existing data should be reconciled before retirement or reduced use.

## People and relationships

```text
Google Contacts -> phone/email/address/birthday identity
Obsidian        -> relationship context and narrative memory
Personal action -> follow-up
Calendar        -> scheduled interaction
```

The user should eventually be able to tell the AI information naturally and have it classified into the correct place without manually editing person records.

## Household operations

The inventory identified real missing systems for:

- groceries/shopping lists;
- household maintenance;
- vehicle maintenance.

These are now represented in the v2 PostgreSQL schema. Due maintenance becomes an action; only actual scheduled work belongs on Calendar.

## Finance

Current architecture:

```text
External financial sources
          |
          v
        InUnity
    consolidated finance
       ^          ^
       |          |
    PickMe    MarketLens
```

- MoneyTalks is the same product lineage as InUnity, not a separate canonical system.
- Looply functionality has already been absorbed into InUnity.
- Banks/card issuers/brokerages remain authoritative for their official records and execution.

## ORC

`agent-orchestrator` (ORC) is the coding-specific control plane.

LLM4LIFE may invoke ORC, but does not recreate ORC's coding model routing, quota-aware escalation, independent verification or cross-vendor review logic.

## Communication and capture

Gmail, Slack, Discord, WhatsApp, iMessage, Apple Shortcuts and Share Sheet are edge channels/source surfaces.

Preferred shape:

```text
source/channel -> LLM4LIFE ingress/router -> canonical destination
```

The useful capability previously provided by OpenClaw is cross-channel AI access; OpenClaw itself remains replaceable by native connectors/webhooks/thin bridges when those are stronger.

## Free-first constraint

Tool decisions follow this order:

1. capability already paid for;
2. strong free tier;
3. open-source/self-hosted option when operationally reasonable;
4. new paid product only when incremental value clearly justifies recurring cost.

**Production-grade does not mean more subscriptions or more enterprise complexity.**

## Design principles

1. One canonical owner per object/domain.
2. AI is interface/router/orchestrator, not a database trapped in a chat thread.
3. Link external records rather than copying them.
4. Provider-authoritative state stays with the provider.
5. Backlog is not Calendar.
6. Important jobs have durable identity, idempotency and execution receipts.
7. Safe reversible work can be automated; consequential actions keep stronger safeguards.
8. Event-driven/exception-oriented behavior beats notification spam.
9. Learn from repeated evidence with rollback.
10. Build the minimum useful system, not life-as-ERP.
11. Free/already-paid-first.
12. Everything remains revisitable.

## Repository map

```text
README.md                           Human entry point
AGENTS.md                           Agent operating instructions
system.yaml                         High-level machine architecture

config/
  domains.yaml                      Canonical v2 domain ownership
  tools.yaml                        Runtime/tool registry
  automations.yaml                  Live automation responsibility registry
  scheduling.yaml                   Scheduling defaults

db/
  README.md                         Database role/migration policy
  migrations/                       PostgreSQL schema migrations

docs/
  STATUS.md                         What is live vs target
  TOOL_REGISTRY.md                  Human tool inventory
  CURRENT_STATE.md                  Current architecture narrative
  ROUTING.md                        Routing logic
  PLANNING.md                       Planning/action model
  AUTOMATIONS.md                    Automation loop
  SECURITY.md                       Public/private boundary
  inventory/                        Full software/life inventory
  decisions/                        Dated architecture decisions
```

## Security

`LLM4LIFE` is public.

Never commit real database URLs, passwords/tokens, private contact or relationship information, health records, financial identifiers, confidential work content, private messages or other sensitive operational state.

Architecture, schemas, variable **names**, placeholders and non-sensitive contracts belong here.
