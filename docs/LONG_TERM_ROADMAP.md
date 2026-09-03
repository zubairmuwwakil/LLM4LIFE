# LLM4LIFE Long-Term Roadmap

_Last updated: 2026-09-03_

This is the durable **north-star roadmap** for LLM4LIFE. It describes the desired end state, the migration sequence, and the gates that must be met before a legacy system is demoted or removed.

`docs/STATUS.md` answers **what is live now**. `system.yaml` defines machine-readable ownership and policy. Decision records explain major architectural changes. This file answers **where the whole system is going**.

## North star

LLM4LIFE is a personal AI control plane, not a monolithic life database.

```text
conversational / edge inputs
ChatGPT / Gmail / Slack / Shortcuts / Share Sheet / channel bridges
                         |
                         v
                 LLM4LIFE control plane
              classify / route / orchestrate
                         |
        +----------------+----------------+
        |                |                |
        v                v                v
      Neon            Obsidian       domain systems
 machine state     narrative context  Jira/GitHub/InUnity
        |                                providers/apps
        v
 execution surfaces
 Google Tasks / Google Calendar
```

The goal is a system where the user can communicate intent naturally and the correct durable system is updated automatically, with explicit ownership, least privilege, idempotency, provenance, rollback, and observable execution.

## Governing principles

### 1. Nothing is grandfathered

No current application, provider, database, framework, host, or workflow is permanent merely because it is already in use.

At any meaningful architecture review, every component may be classified as:

- **keep** — still the best fit;
- **reposition** — useful, but no longer the canonical owner;
- **consolidate** — duplicate capability should move into another system;
- **replace** — a materially better long-term option exists;
- **retire** — no longer provides enough value to justify complexity.

A replacement must improve the system materially on reliability, scalability, security, integration quality, maintainability, ownership, cost, or user experience. Change for novelty alone is not a goal.

### 2. One canonical owner per object/domain

Each durable object should have one authoritative owner. Other systems are clients, projections, execution surfaces, integrations, caches, or rollback references.

Avoid long-term dual-write architectures.

### 3. ChatGPT is the interface and orchestrator, not the database

Chat history is not durable operational state. Long-lived state belongs in Neon, Obsidian, a domain system, or the authoritative external provider.

### 4. User-owned machine state lives in PostgreSQL when database semantics add value

Neon/PostgreSQL is preferred for LLM4LIFE-owned structured operational state such as actions, jobs, receipts, sync checkpoints, external references, maintenance state, and domain services that benefit from relational/event semantics.

It must not become a raw dump of private messages, narrative notes, medical records, credentials, or provider-owned official records.

### 5. Narrative knowledge stays human-readable

Obsidian remains the preferred owner for long-form reasoning, learning, research context, reflections, and relationship narrative. Structured frontmatter should be attempted before inventing parallel database tables.

### 6. Prefer events and webhooks over polling

When a provider exposes reliable event delivery, prefer event-driven processing. Polling is acceptable only when no reliable event path exists or reconciliation requires it.

### 7. Every autonomous write should be safe to retry

Durable automation should use stable identities, idempotency keys, execution receipts, retry/failure policy, checkpoints where relevant, and enough observability to determine what happened without relying on a chat transcript.

### 8. Free/already-paid first

Preference order:

1. capability already being paid for;
2. strong free tier;
3. open-source/self-hosted when operationally sensible;
4. a new paid service only when its incremental value materially justifies recurring cost.

Production-grade does not mean maximizing subscriptions or infrastructure complexity.

### 9. Preserve rollback during migrations

A target architecture is not a completed cutover. Migrate one domain at a time, verify parity/runtime behavior, preserve rollback, and only then demote the previous source.

### 10. Public architecture must remain non-sensitive

This repository may document contracts, schemas, ownership, placeholders, and operating policy. It must not contain credentials, tokens, private contact/relationship content, health records, financial identifiers, confidential work content, or private message bodies.

## Target ownership map

| Domain | Long-term canonical owner | Human/execution surface | Important boundary |
|---|---|---|---|
| AI orchestration | LLM4LIFE / ChatGPT | ChatGPT + future ingress channels | Chat is not durable state |
| Personal actions | Neon | Google Tasks | Calendar events are execution projections, not backlog |
| Scheduled commitments | Google Calendar | Google Calendar | Do not reconstruct backlog from Calendar |
| Engineering backlog | Jira | Jira | Do not mirror into personal tasks |
| Code/repository truth | GitHub | GitHub / developer tools | Code truth stays repo-native |
| Coding-agent orchestration | ORC | ORC CLI/adapters | LLM4LIFE invokes ORC rather than duplicating it |
| Narrative knowledge | Obsidian | Obsidian | Live vault bridge preferred over editing backup as permanent path |
| Contact identity | Google Contacts after dedup | Google/Apple clients | Apple Contacts becomes a synced client, not second independent truth |
| Relationship narrative | Obsidian | Obsidian + conversational capture | No relationship DB until automation need justifies one |
| Consolidated finance | InUnity | InUnity + InUnity MCP | Providers remain authoritative for official records/execution |
| Card decision/capture | PickMe | PickMe | Relevant data flows into InUnity |
| Market data | MarketLens | InUnity/consumers | Specialized feed, not general finance owner |
| Personal-care inventory | Product Tracker on Neon | API + transitional Notion projection | Inventory changes are events; Notion becomes projection after cutover |
| Household/vehicle maintenance | Neon domain state | Google Tasks / Calendar | Provider apps remain sources/execution where appropriate |
| General shopping/grocery state | Neon when structured automation adds value | lightweight client/projection | Do not create a paid list-app dependency by default |
| Health aggregation | Apple Health | Apple devices/apps | Do not copy health records into Neon by default |
| Files | Google Drive preferred after audit | Drive/local clients | OneDrive becomes secondary/exception if consolidation is justified |
| Email/source context | Gmail | Gmail | Durable actions route to their owner |
| Work communication | Slack | Slack | Communication is not task truth |
| Personal communication | provider channel | WhatsApp/iMessage/Discord/etc. | Bridges are ingress, not canonical databases |
| Job registry/runtime metadata | Neon | execution may be ChatGPT automation, Worker, workflow, or cron | Execution trigger is not durable job state |

## Migration scoreboard

### Personal actions and planning

**Current:** Neon is canonical; Google Tasks projection/capture and Google Calendar execution are production-live. Notion planning databases are rollback/reference.

**Target:** Neon remains canonical while user-facing clients remain replaceable projections.

**Done gate:**

- all normal action creation/completion/edit flows work without Notion;
- scheduled execution telemetry and receipts are durable in Neon;
- no live planning automation silently falls back to Notion writes.

**Status:** substantially complete; continue observability and cleanup rather than redesigning ownership.

### Personal-care inventory / Product Tracker

**Current:** a parity-verified Product Tracker mirror exists in a dedicated database inside the existing Neon project. Notion is still the live human control surface until runtime cutover is verified.

**Target:**

```text
ChatGPT / clients / Notion webhook
              |
              v
        Product Tracker API
          hosted on Vercel
              |
              v
             Neon
 canonical inventory/event state
              |
              v
 durable async processing
 Vercel event/queue/workflow primitive
              |
              v
 Notion projection / notifications / future clients
```

The long-term runtime should be **event-driven**. Do not choose a host merely to preserve the old infinite polling loop. Fastify can be served through Vercel Functions, while asynchronous projection/retry work should move from a permanent polling process to Vercel's durable async primitives where they fit. Native Vercel Cron on Hobby must not be used for frequent polling; current Hobby cron limits make that the wrong architecture anyway.

**Done gate:**

- Vercel deployment is healthy;
- authenticated inventory reads match Neon;
- API mutation creates exactly one durable inventory event under retry;
- Notion webhook ingestion is verified;
- durable async projection/retry path is verified;
- reconciliation can detect drift without an always-on polling loop;
- only then does Notion become projection/rollback rather than source.

**Status:** data mirror complete; runtime cutover pending.

### Notion retirement/repositioning

**Current:** planning is rollback/reference; personal-care inventory remains transitional.

**Target:** optional dashboard/projection/ad-hoc workspace only where it provides real UX value.

**Done gate:** every remaining Notion-backed operational domain has a verified canonical replacement and rollback window.

Notion does not need to be removed entirely; it simply must not accidentally become the backend for new core state.

### Obsidian live bridge

**Current:** narrative ownership is defined, but the trusted live-vault write path is incomplete.

**Target:**

```text
LLM4LIFE -> authenticated least-privilege local adapter -> live Obsidian vault
```

Normal Obsidian sync/backup remains responsible for file durability. GitHub backup access is useful for recovery/read context but is not the desired permanent write path.

**Done gate:** authenticated live-vault read/write, atomic file updates, path restrictions, auditability, and no secrets in the public LLM4LIFE repo.

### Contacts consolidation

**Current:** contact identity is split between Apple and Google ecosystems.

**Target:** Google Contacts is the canonical address book; Apple Contacts is a synchronized device client.

**Done gate:** deduplicate first, preserve all important fields, verify sync in both ecosystems, then stop independently maintaining two address books.

### Household and vehicle operations

**Current:** schema capability exists, but the domain is not yet comprehensively populated/automated.

**Target:** assets, maintenance rules, maintenance events, and provider references in Neon; actionable work surfaces in Google Tasks; actual scheduled work in Calendar.

**Done gate:** recurring maintenance can be generated idempotently, completion updates maintenance history, and provider-specific state remains linked instead of copied unnecessarily.

### Durable automation architecture

**Current:** ChatGPT Automations are useful execution triggers; Neon already contains jobs/job_runs/receipts primitives.

**Target:** every important scheduled/conditional process has durable identity and state independent of a conversation thread. ChatGPT, Cloudflare, Vercel, or another runtime may execute a job, but Neon remains the durable registry when LLM4LIFE owns the process.

**Done gate:** job history, retries, failures, checkpoints, and state transitions can be inspected without depending on accumulated chat context.

### Communication and capture ingress

**Current:** Gmail and Slack have direct paths; other channels may require bridges.

**Target:** multiple low-friction ingress channels can submit intent/events to the same LLM4LIFE routing policy without becoming independent policy engines or databases.

Preferred principle:

```text
many ingress channels -> one routing/control policy -> correct domain owner
```

**Done gate:** each adopted bridge has least-privilege credentials, explicit supported actions, deduplication/idempotency, and can be removed without losing canonical state.

### Files/storage rationalization

**Current:** multiple cloud/local stores exist.

**Target:** Google Drive is the preferred canonical cloud file store if audit confirms it covers the requirements; OneDrive becomes secondary/exception; Time Machine remains disaster recovery rather than sync.

**Done gate:** duplicates and exceptional workflows are understood before any destructive consolidation.

### Finance integration

**Current:** InUnity is the consolidated user-owned finance application and its ChatGPT MCP integration has been implemented/read-verified.

**Target:** InUnity remains the finance-domain owner; PickMe and MarketLens feed it; provider systems retain official authority.

**Done gate:** finance workflows route through InUnity/MCP where appropriate without copying provider credentials or making LLM4LIFE a parallel financial ledger.

### Tool and subscription rationalization

This is continuous, not a one-time migration.

For every material tool or service, record:

1. what real job it performs;
2. whether it owns canonical data or is merely a client/integration;
3. overlap with another system;
4. portability/lock-in risk;
5. integration and automation quality;
6. security/least-privilege posture;
7. ongoing cost;
8. whether a free/already-paid alternative is production-grade enough;
9. keep / reposition / consolidate / replace / retire decision.

A tool may remain because it is excellent; it may not remain merely because migration is inconvenient.

## Implementation order

The roadmap is intentionally dependency-aware rather than a giant rewrite.

### Phase A — Core foundation

- Neon machine-state foundation.
- personal-action migration.
- Google Tasks projection/capture.
- Calendar execution integration.
- durable receipts/checkpoints/job primitives.

**State:** largely complete.

### Phase B — Remove remaining Notion operational dependency

- finish Product Tracker runtime using Vercel + Neon + durable event processing;
- verify inventory runtime and demote Notion inventory to projection/rollback;
- retain historical Notion data until rollback confidence is sufficient.

### Phase C — Knowledge and identity

- implement trusted live Obsidian bridge;
- deduplicate and consolidate contacts;
- improve structured retrieval without duplicating narrative state into PostgreSQL.

### Phase D — Household operations

- populate household/vehicle asset and maintenance state;
- generate actionable work through canonical action system;
- add shopping/grocery structure only where automation justifies it.

### Phase E — Ingress and orchestration hardening

- evaluate native connectors vs OpenClaw vs thin custom bridges per channel;
- standardize event envelopes, provenance, authorization, idempotency, and routing;
- keep one policy authority.

### Phase F — Durable job execution

- progressively move important scheduled workflows from conversation-dependent execution toward durable job definitions and observable runs;
- choose runtime per workload rather than forcing every job onto one host.

### Phase G — Continuous system optimization

- periodically re-evaluate all tools, hosts, databases, agent frameworks, providers, and subscriptions;
- replace only when evidence shows a meaningful improvement;
- keep architecture documentation synchronized with real runtime cutovers.

## Decision and documentation rules

When a major architecture choice changes:

1. update or add a decision record;
2. update `system.yaml` / machine-readable registries;
3. update `docs/STATUS.md` only when runtime reality changes;
4. update this roadmap if the long-term target changes;
5. preserve superseded decisions for historical context rather than rewriting history.

The newest explicit adopted decision wins when documents conflict.

## Definition of success

LLM4LIFE is successful when:

- the user can state intent once and the correct system is updated;
- durable state survives chat/session changes;
- each domain has an explicit owner;
- automated writes are retry-safe and observable;
- the system can evolve without large-scale rewrites because integrations are adapters, not hard-coded assumptions;
- private/sensitive data is kept out of the public architecture repo;
- costs stay low because new paid services are added only when justified;
- replacing any non-authoritative client or runtime does not destroy canonical state;
- architecture documentation describes both the **target** and the **actual live state** accurately.
