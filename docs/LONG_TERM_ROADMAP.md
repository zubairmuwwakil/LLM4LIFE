# LLM4LIFE Long-Term Roadmap

_Last updated: 2026-09-03_

This is the durable **north-star roadmap** for LLM4LIFE. `docs/STATUS.md` answers what is live now; this file describes where the whole system is going and the gates required before legacy systems are demoted.

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
 domain DBs                           providers/apps
        |
        v
 execution surfaces + event runtimes
 Google Tasks / Calendar / Cloudflare
```

The goal is that the user states intent once and LLM4LIFE updates the correct durable owner automatically with least privilege, idempotency, provenance, rollback, and observable execution.

## Governing principles

### Nothing is grandfathered

Every material component may be classified as **keep / reposition / consolidate / replace / retire**. A replacement must materially improve reliability, scalability, security, integration quality, maintainability, ownership, cost, portability, or UX. Change for novelty alone is not a goal.

### One canonical owner per object/domain

Other systems are clients, projections, integrations, caches, runtimes, or rollback references. Avoid long-term dual-write architectures.

### ChatGPT is interface/orchestrator, not database

Durable operational state belongs in Neon, Obsidian, a domain service, or the authoritative provider—not only in a chat thread.

### Neon owns user-controlled structured machine state when DB semantics help

Use PostgreSQL for actions, jobs/runs, events, receipts, checkpoints, external references, maintenance state, and specialized user-owned domain databases. Do not turn it into a raw dump of messages, narrative notes, health records, credentials, or provider-owned official records.

### Obsidian owns narrative knowledge

Learning, reasoning, research context, reflections, and relationship narrative remain human-readable. Use frontmatter before inventing parallel database models.

### Prefer events/webhooks over polling

Polling is a fallback/reconciliation mechanism, not the default architecture when reliable event delivery exists.

### Autonomous writes must be retry-safe

Use stable identity, idempotency, receipts, retry/failure policy, observability, and checkpoints where relevant.

### Free/already-paid first

Prefer already-paid capability, then strong free tiers, then OSS/self-hosting when operationally reasonable, then paid services only when incremental value materially justifies recurring cost.

### Preserve rollback

A target is not a cutover. Migrate one domain at a time, verify parity and runtime behavior, then demote the old source.

## Target ownership map

| Domain | Long-term owner | Interface/runtime boundary |
|---|---|---|
| AI orchestration | LLM4LIFE / ChatGPT | ChatGPT + ingress channels |
| Personal actions | Neon | Google Tasks client; Calendar execution |
| Shared event compute | Cloudflare where workload fits | Runtime only, never canonical data owner |
| Engineering backlog | Jira | GitHub links / ORC tooling |
| Code truth | GitHub | developer tooling |
| Coding orchestration | ORC | LLM4LIFE invokes it |
| Narrative knowledge | Obsidian | trusted live-vault bridge target |
| Contact identity | Google Contacts after dedup | Apple Contacts synchronized client |
| Relationship context | Obsidian | actions/Calendar for follow-up |
| Consolidated finance | InUnity | providers retain official authority |
| Personal-care inventory | Product Tracker / Neon | Cloudflare Worker + Queue runtime; Notion projection after cutover |
| Household/vehicle maintenance | Neon | Google Tasks / Calendar |
| General grocery/shopping | Neon when structure adds value | lightweight client/projection |
| Health aggregation | Apple Health | no Neon copy by default |
| Files | Google Drive preferred after audit | OneDrive secondary/exception if justified |
| Job registry/state | Neon | execution runtime chosen per workload |

## Migration scoreboard

### Personal actions and planning

**Current:** Neon canonical; Google Tasks projection/capture and Google Calendar execution are production-live; Notion planning is rollback/reference.

**Done gate:** normal action flows work without Notion, telemetry/receipts are durable, and no planning automation silently falls back to Notion writes.

**Status:** substantially complete.

### Personal-care inventory / Product Tracker

**Current:** parity-verified Product Tracker mirror exists in a dedicated Neon database; Notion remains live control until runtime verification.

**Target:**

```text
ChatGPT / clients / Notion webhook
              |
              v
      Cloudflare Worker
              |
              v
             Neon
 canonical inventory/events
 outbox + webhook receipt ledger
              |
              v
      Cloudflare Queue
 async projection / retries
              |
              v
 Notion projection / future effects
```

The database transaction is the durable boundary. Normal work publishes Queue messages after commit. A low-frequency Cloudflare scheduled relay only republishes due Product Tracker ledger rows when queue publication was missed or a claim became stale; it does not poll Notion.

Cloudflare Workflows are optional when genuinely multi-step durable workflows emerge. Hyperdrive is a later Postgres connection optimization after the direct Neon runtime is proven.

**Done gate:**

- Cloudflare Worker deployment healthy;
- authenticated reads match Neon;
- duplicate/retried API requests create one canonical inventory event;
- Notion webhook authentication/deduplication verified;
- Queue projection/retry path verified;
- reconciliation recovers missed publication;
- DLQ/observability verified;
- only then Notion becomes projection/rollback.

**Status:** mirror complete; Cloudflare implementation committed and CI-green; deployment/cutover pending.

### Notion repositioning

**Current:** planning rollback/reference; personal-care inventory transitional.

**Target:** optional dashboard/projection/ad-hoc workspace only where it provides real UX value.

**Done gate:** every remaining operational Notion domain has a verified replacement and rollback window.

### Obsidian live bridge

**Target:**

```text
LLM4LIFE -> authenticated least-privilege local adapter -> live Obsidian vault
```

**Done gate:** authenticated read/write, atomic updates, path restrictions, auditability, and no private vault data in the public LLM4LIFE repo.

### Contacts consolidation

**Target:** Google Contacts canonical; Apple Contacts synchronized device client.

**Done gate:** deduplicate first, preserve important fields, verify both ecosystems, then stop independently maintaining two address books.

### Household and vehicle operations

**Target:** assets/rules/events in Neon; actionable work in Google Tasks; actual scheduled work in Calendar; provider state linked rather than copied unnecessarily.

### Durable automation architecture

Important jobs must have durable identity/state independent of conversation threads. Execution may use ChatGPT Automations, Cloudflare Workers/Queues/Workflows, Vercel where still best fit, cron, or a dedicated worker. Neon remains the durable registry when LLM4LIFE owns the process.

**Done gate:** runs, retries, failures, checkpoints, and state transitions can be inspected without accumulated chat context.

### Communication/capture ingress

```text
many ingress channels -> one routing/control policy -> correct domain owner
```

Every adopted bridge must use least privilege, explicit actions, deduplication/idempotency, and remain removable without loss of canonical state.

### Files/storage rationalization

Google Drive is preferred canonical cloud storage if audit confirms it fits. OneDrive becomes secondary/exception; Time Machine remains disaster recovery. Understand duplicates before destructive consolidation.

### Finance

InUnity remains the consolidated user-owned finance owner; PickMe and MarketLens feed it; providers retain official authority. LLM4LIFE must not become a second financial ledger or credential store.

### Tool/subscription rationalization

For every material tool, periodically record its real job, canonical ownership, overlap, lock-in, integration quality, security, cost, free/already-paid alternatives, and keep/reposition/consolidate/replace/retire decision.

## Implementation order

### Phase A — Core foundation

- Neon machine-state foundation;
- personal-action migration;
- Google Tasks projection/capture;
- Calendar execution integration;
- durable receipts/checkpoints/job primitives.

**State:** largely complete.

### Phase B — Finish Product Tracker and remove remaining Notion operational dependency

- deploy Product Tracker on Cloudflare Worker + Queue;
- verify inventory runtime and demote Notion inventory to projection/rollback;
- retain historical Notion data until rollback confidence is sufficient;
- evaluate Hyperdrive only after functional runtime verification.

### Phase C — Knowledge and identity

- trusted live Obsidian bridge;
- contact dedup/consolidation;
- stronger structured retrieval without duplicating narrative state.

### Phase D — Household operations

- populate household/vehicle assets and maintenance;
- generate actions idempotently;
- add general shopping structure only where automation justifies it.

### Phase E — Ingress/orchestration hardening

- evaluate native connectors vs OpenClaw vs thin bridges per channel;
- standardize event envelopes, provenance, authorization, idempotency, and routing;
- keep one policy authority.

### Phase F — Durable job execution

- move important conversation-dependent schedules toward durable job definitions/runs;
- choose runtime per workload rather than forcing every job onto one host;
- prefer Cloudflare as the shared event runtime when it materially simplifies the stack, while keeping runtimes replaceable.

### Phase G — Continuous system optimization

Periodically re-evaluate tools, hosts, databases, agent frameworks, providers, and subscriptions. Replace only when evidence shows a meaningful total-system improvement.

## Documentation rules

When a major architecture choice changes:

1. update/add a decision record;
2. update machine-readable registries;
3. update `docs/STATUS.md` only when runtime reality changes;
4. update this roadmap when the long-term target changes;
5. preserve superseded decisions as historical context.

Newest explicit adopted decision wins when documents conflict.

## Definition of success

LLM4LIFE succeeds when the user states intent once and the correct system is updated; durable state survives sessions; each domain has an explicit owner; automated writes are retry-safe and observable; integrations remain replaceable; sensitive data stays out of public architecture; cost remains low; and documentation accurately distinguishes **target architecture** from **live runtime**.
