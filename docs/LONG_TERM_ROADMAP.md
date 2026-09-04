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

Use PostgreSQL for actions, jobs/runs, events, receipts, checkpoints, external references, maintenance state, specialized user-owned domain databases, and the target structured People/Relationships machine state. Do not turn it into a raw dump of messages, narrative notes, health records, credentials, or provider-owned official records.

### Obsidian owns narrative knowledge

Learning, reasoning, research context, reflections, and relationship narrative remain human-readable. Structured cross-system People state may live in Neon without copying the narrative itself.

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
| Stable person identity | Neon after People migration | Google Contacts address-book projection/client |
| Structured relationship machine state | Neon after People migration | actions/Calendar for execution |
| Relationship narrative/context | Obsidian | linked to stable person identity |
| Apple-device contacts | Apple Contacts | synchronized client after People migration |
| Consolidated finance | InUnity | providers retain official authority |
| Personal-care inventory | Product Tracker / Neon | Cloudflare Worker + Queue + Hyperdrive; Notion projection/rollback |
| Household/vehicle maintenance | Neon | Google Tasks / Calendar |
| General grocery/shopping | Neon when structure adds value | lightweight client/projection |
| Health aggregation | Apple Health | no Neon copy by default |
| Files | Google Drive preferred after audit | OneDrive secondary/exception if justified |
| Job registry/state | Neon | execution runtime chosen per workload |

## Migration scoreboard

### Personal actions and planning

**Current:** Neon canonical; Google Tasks projection/capture and Google Calendar execution are production-live; Notion planning is rollback/reference.

**Status:** substantially complete.

### Personal-care inventory / Product Tracker

**Current:** Product Tracker/Neon is production canonical. Cloudflare Worker `v0.4.0`, Queue, Hyperdrive, reliability status/DLQ receipts and stable Notion event-idempotency hardening are live. Notion inbound sync is disabled and Notion is projection/reference/rollback.

**Remaining closeout:** complete the post-cutover observation window and remove temporary reliability staging infrastructure if production remains clean.

**Status:** canonical cutover complete; observation/cleanup active.

### People / Contacts / Relationships

**Current:** Phase 0 architecture accepted; implementation not started. Apple + Google Contacts remain fragmented. Obsidian remains the live private narrative relationship system.

**Target:**

```text
Neon
 stable person identity
 cross-system refs
 structured relationship/fact/interaction state
      |
      +--> Google Contacts address-book client/projection
      +--> LLM4LIFE actions -> Google Tasks follow-ups
      +--> Google Calendar scheduled interactions

Obsidian
 narrative relationship memory
 diary/reflections
 long-form context
```

**Done gate:**

- minimum People schema reviewed/tested;
- read-only Apple/Google inventory completed;
- stable person IDs and external refs imported idempotently;
- duplicate candidates reconciled conservatively;
- same-name-only auto-merge prohibited/tested;
- ambiguous merges remain reviewable and reversible;
- contact-field authority/conflict policy explicitly chosen;
- Google Contacts projection/cutover verified;
- Apple-device sync path verified;
- Obsidian person notes linked without copying narrative into Neon;
- structured facts preserve provenance;
- relationship follow-ups reuse the existing action domain;
- no private People payloads committed to the public repo.

**Status:** **NEXT — Phase 0 complete, Phase 1 schema + read-only inventory pending.**

See `docs/PEOPLE.md`.

### Notion repositioning

**Current:** planning rollback/reference and Product Tracker projection/reference/rollback.

**Target:** optional dashboard/projection/ad-hoc workspace only where it provides real UX value.

### Obsidian live bridge

**Target:**

```text
LLM4LIFE -> authenticated least-privilege local adapter -> live Obsidian vault
```

**Done gate:** authenticated read/write, atomic updates, path restrictions, auditability, and no private vault data in the public LLM4LIFE repo.

The People subsystem can proceed with schema/contact inventory independently, but narrative write automation should use this bridge when practical.

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

For People, communication systems should normally provide source references/interaction signals, not full-message archival.

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

### Phase B — Product Tracker canonical cutover

- deploy Cloudflare Worker + Queue + Hyperdrive;
- verify API mutation idempotency/retry/reconciliation/DLQ;
- disable Notion inbound writes;
- demote Notion to projection/rollback;
- add reliability status and stable Notion event ID hardening;
- observe production, then remove temporary reliability staging.

**State:** cutover/hardening complete; observation/cleanup remains.

### Phase C — People / identity / relationships — NEXT

Follow `docs/PEOPLE.md` rather than improvising from chat history.

1. **Phase 1:** minimum schema + tests + read-only Google/Apple contact inventory.
2. Decide exact field-level authority after real API/conflict testing.
3. **Phase 2:** stable identity import + external refs + conservative dedup/merge audit.
4. **Phase 3:** Google Contacts projection/cutover + Apple synchronized-client verification.
5. **Phase 4:** Obsidian stable-person linking + conversational structured fact/interaction capture.
6. **Phase 5:** low-noise relationship automation using existing actions/Calendar.

Do not start by mass-editing contacts or migrating narrative notes.

### Phase D — Knowledge bridge + household operations

- trusted live Obsidian bridge;
- populate household/vehicle assets and maintenance;
- generate actions idempotently;
- add general shopping structure only where automation justifies it.

The Obsidian bridge can be pulled earlier if People Phase 4 needs it, but it should not block read-only People inventory/schema work.

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
3. update the domain implementation contract when one exists;
4. update `docs/STATUS.md` only when runtime reality changes;
5. update this roadmap when the long-term target changes;
6. preserve superseded decisions/inventories as historical context.

Newest explicit adopted decision wins when documents conflict.

## Definition of success

LLM4LIFE succeeds when the user states intent once and the correct system is updated; durable state survives sessions; each domain has an explicit owner; automated writes are retry-safe and observable; integrations remain replaceable; sensitive data stays out of public architecture; cost remains low; and documentation accurately distinguishes **target architecture** from **live runtime**.
