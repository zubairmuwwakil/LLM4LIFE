# Current State

_Last updated: 2026-09-03_

LLM4LIFE has completed the v2 foundation and is migrating domains one at a time with explicit ownership, reconciliation gates and rollback.

The target architecture is user-owned/durable where it matters, while runtime cutovers are tracked separately from design decisions.

## Current operating model

```text
User expresses intent through practical channels
                  |
                  v
          LLM4LIFE / AI router
                  |
      +-----------+-----------+----------------+
      |                       |                |
      v                       v                v
   machine state          knowledge         domain truth
 Neon/PostgreSQL           Obsidian      Jira/GitHub/InUnity
      |
      +--------+------------------+
               |                  |
               v                  v
        Google Tasks       Google Calendar
          action UI        execution/time
```

Communication/source surfaces include Gmail, Slack, Discord, WhatsApp, iMessage, Shortcuts/Share Sheet and browser capture where integrations are available.

## v2 ownership

| Domain | Owner / direction | Runtime state |
|---|---|---|
| LLM4LIFE machine state | Neon/PostgreSQL | Live |
| Personal actions | Neon backend; Google Tasks user-facing client | Live |
| Execution schedule | Google Calendar | Live |
| Engineering backlog | Jira | Live by connector/domain |
| Code/repository truth | GitHub | Live |
| Coding-agent orchestration | ORC | External subsystem |
| Knowledge/reasoning/learning | Obsidian | Partial live access; preferred local bridge pending |
| Stable person identity | Neon target | **People Phase 0 only; not migrated** |
| Structured relationship machine state | Neon target | **People Phase 0 only; not implemented** |
| Relationship narrative/context | Obsidian | Current private narrative system |
| Address-book UI | Google Contacts after People dedup/cutover | Migration incomplete; Apple + Google fragmented |
| Personal-care inventory | Product Tracker / Neon | Production canonical |
| Household + vehicle maintenance | Neon/PostgreSQL | Schema/domain direction established |
| Grocery/shopping-list state | Neon/PostgreSQL when structured automation is justified | Incremental |
| Consolidated finance | InUnity | Live by domain |
| Official provider records/execution | respective provider | Provider authority |
| Files | Google Drive preferred; OneDrive secondary after audit | Ongoing |

See `config/domains.yaml` for the complete registry.

## What is implemented now

### Personal actions / planning

- Neon `llm4life.actions` is canonical personal action/backlog state.
- Google Tasks is the production human-facing action projection/capture surface.
- Google Calendar owns scheduled execution and fixed commitments.
- Notion planning databases are rollback/reference rather than canonical state.
- recurring-action instances, execution telemetry, adaptive rules and receipts are part of the durable planning model.

### Product Tracker

- Product Tracker/Neon is the canonical personal-care inventory owner.
- production Cloudflare Worker + Queue + Hyperdrive are live;
- Notion inbound inventory sync is disabled;
- Notion is projection/reference/rollback only;
- durable retry/DLQ observability is live;
- stable Product Tracker Event ID query-before-create hardening is deployed for future Notion event projections;
- post-cutover observation/cleanup remains the final operational closeout step.

### People / Relationships

**Phase 0 only.** The architecture is documented, but the new People backend has not been built or populated.

The accepted target is:

```text
Neon
  stable person identity
  external references
  structured relationship machine state
  structured facts + provenance
        |
        +--> Google Contacts (address-book client/projection after cutover)
        +--> LLM4LIFE actions -> Google Tasks (follow-ups)
        +--> Google Calendar (scheduled interactions)

Obsidian
  narrative relationship memory
  diary/reflections
  long-form person context
```

Current private data remains fragmented across Apple Contacts, Google Contacts and Obsidian. Do not claim migration/canonical cutover until schema, import, dedup and projection gates in `docs/PEOPLE.md` pass.

## Planning model

```text
Neon personal actions        Jira engineering work
          \                         /
           \                       /
              AI planner/scheduler
                       |
                       v
                Google Calendar
                 execution plan
```

Google Tasks is the preferred human action client/projection.

Current scheduling semantics remain:

- sleep 11 PM–7 AM protected;
- weekday work 9 AM–1 PM soft-busy;
- movable personal work defaults to 1 PM–9 PM America/Toronto;
- leave buffer;
- fixed commitments do not move for optimization;
- waiting/blocked actions do not consume execution time;
- repeated misses feed scheduling adaptation rather than endless blind rescheduling.

## Obsidian

Obsidian remains the durable narrative knowledge/context system.

It owns:

- learning and reasoning;
- durable notes/research;
- diary/reflections;
- narrative relationship/person context;
- contextual knowledge that benefits from readable Markdown.

The older recommendation to keep structured relationship operations in Obsidian frontmatter and defer Neon People tables has been superseded by the 2026-09-03 People architecture decision. **Narrative stays in Obsidian; structured cross-system People machine state moves to Neon when that migration is implemented.**

The preferred future AI write path is a trusted local bridge to the live vault. GitHub backup access is useful but is not the permanent real-time architecture.

## Contacts / People migration

Contact state is currently fragmented across Apple Contacts and Google Contacts.

Target after a verified migration:

```text
Neon People state -> Google Contacts address-book projection/client
                          |
                          v
                    Apple Contacts
                 synced Apple-device client

Neon person_id <----reference/link----> Obsidian person narrative
```

The exact field-level authority for phone/email/address/birthday must be validated during Phase 1 against real Google Contacts API/conflict semantics. Default target is Neon-owned structured state projected outward; an exception should be documented explicitly if provider authority proves materially better.

Migration requires read-only inventory, conservative deduplication, idempotent import, merge audit and rollback before canonical cutover.

See `docs/PEOPLE.md`.

## Household operations

The full inventory revealed real missing systems for:

- grocery/shopping lists;
- household maintenance;
- vehicle maintenance.

These are modeled as LLM4LIFE-owned structured domains. Tasks should be generated when work becomes actionable; Calendar is used when actual time is reserved.

## Finance

- InUnity is the main consolidated finance system.
- MoneyTalks refers to the same product lineage rather than a separate system.
- Looply functionality has been absorbed into InUnity.
- PickMe feeds relevant purchase/card data to InUnity.
- MarketLens feeds market data to InUnity.
- Banks/card issuers/brokerages remain authoritative for official provider state and execution.

## Communication and ingress

Communication applications are edge channels, not state databases.

The desired pattern is:

```text
Gmail / Slack / Discord / WhatsApp / iMessage / Shortcuts
                        |
                        v
                LLM4LIFE ingress/router
                        |
                        v
                 canonical destination
```

Preserve the valuable cross-channel experience previously provided by OpenClaw, but OpenClaw itself remains replaceable by native connectors or thin bridges.

For People, communication sources may provide references/evidence for explicit interactions, but complete private message histories should not be copied into Neon by default.

## Notion

Notion is no longer the default target backend.

Current best role:

- optional dashboards/projections;
- rollback/reference views;
- structured human-facing workspaces where useful;
- ad-hoc collaboration when it provides real value.

Product Tracker uses Notion only as projection/reference/rollback. Personal planning also treats prior Notion state as rollback/reference.

## Free-first constraint

Prefer already-paid capabilities, strong free tiers and thin open-source/custom adapters before introducing new recurring SaaS costs.

Production-grade means reliable ownership, idempotency, observability and rollback — not adding more subscriptions.
