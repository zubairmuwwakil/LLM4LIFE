# Tool Registry

_Last updated: 2026-09-03_

This registry separates **target ownership**, **current runtime status**, and **user-facing interfaces**. See `config/tools.yaml` for machine-readable runtime detail, `docs/STATUS.md` for live migration status, and `docs/LONG_TERM_ROADMAP.md` for the durable end-state plan.

## Core systems

| Tool | v2 role | Runtime status | Important boundary |
|---|---|---|---|
| **ChatGPT** | Primary conversational/control surface | Connected | Router/orchestrator, not durable chat-state |
| **Neon / PostgreSQL** | Durable LLM4LIFE machine state + domain DB host | **Connected/live** | Canonical actions + Product Tracker; target People structured state is not implemented yet |
| **Cloudflare** | Shared edge/event runtime for fitting LLM4LIFE backends | **Production-live** | Google Tasks sync + Product Tracker Worker/Queue/Hyperdrive; runtime, not canonical data owner |
| **Google Tasks** | Preferred personal-action client | **Production-live** | Human UI/capture for Neon actions |
| **Google Calendar** | Commitments + execution schedule | Connected/live | Calendar is schedule, not backlog or relationship database |
| **Product Tracker** | Canonical personal-care inventory owner | **Production canonical v0.4.0** | Neon state; Notion projection/rollback only |
| **Notion** | Projection/reference/rollback + optional workspace | Connected | Not default canonical backend; Product Tracker inbound sync disabled |
| **Vercel** | Web-app runtime where still best fit | User-live | Evaluate per project; runtime only |
| **Google Contacts** | Target People address-book projection/human client | Connector available; People migration incomplete | Do not treat target role as completed cutover |
| **Apple Contacts** | Current Apple-device contact client/source during migration | User-live | Target is synchronized client rather than independent second truth |
| **Obsidian** | Narrative knowledge + narrative relationship memory | Partial through backup path | Structured People machine state target is Neon; preferred future write path is trusted live-vault bridge |
| **Things 3** | Legacy/optional task UX | User-live | Not canonical |
| **Jira** | Engineering backlog | Connector available | Engineering work does not belong in personal backlog |
| **GitHub** | Code/repository truth + public LLM4LIFE architecture | Connected read/write | Never store private people/relationship data in public repo |
| **ORC** | Coding-agent orchestration | External subsystem | LLM4LIFE invokes rather than duplicates it |
| **InUnity** | Consolidated finance | MCP live/read-verified | Providers remain official authorities |
| **Gmail / Slack** | Source/communication surfaces | Connected | Route durable state to domain owners |

## Google Tasks production integration

```text
Google Tasks
    ^  |
    |  v
Cloudflare Worker
    ^  |
    |  v
Neon canonical actions

Google Calendar = execution time
```

Google Tasks is an execution/client surface. Relationship follow-ups should reuse the same Neon action domain rather than inventing a People-specific task lifecycle.

## Product Tracker

Personal-care inventory is deliberately separate from generic shopping state.

Production architecture:

```text
ChatGPT / clients
      |
      v
Cloudflare Worker
 authenticated API
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

Current verified state includes:

- Product Tracker/Neon canonical cutover complete;
- production Worker v0.4.0;
- Notion inbound sync disabled;
- application retry/reconciliation gates passed;
- Cloudflare retry→DLQ behavior verified in isolated staging;
- durable `DeadLetterEvent` receipts and authenticated reliability status endpoint live;
- invocation-scoped Prisma clients behind Hyperdrive;
- stable Product Tracker Event ID + query-before-create hardening deployed for future Notion Inventory Events;
- 24-hour post-cutover observation/temporary staging cleanup remains operational closeout, not an ownership blocker.

See `docs/STATUS.md` and `docs/decisions/2026-09-03-product-tracker-runtime.md`.

## People / Relationships

**Current status: Phase 0 architecture only.**

```text
                     Neon target
       stable person identity + structured state
                   /       |       \
                  v        v        v
       Google Contacts   actions   references
        address-book     followup   to sources
           client           |
             |              v
       Apple Contacts   Google Tasks

Obsidian = narrative relationship memory
Google Calendar = scheduled interactions
```

Important boundaries:

- no People tables/import/cutover has been completed yet;
- Apple + Google Contacts are still fragmented source material;
- stable `person_id`, external refs, structured relationship metadata/facts/interactions are the Neon target;
- Obsidian retains narrative notes/reflections/context;
- Google Contacts is the preferred human-facing address-book client after dedup/cutover;
- exact phone/email/address/birthday field authority remains a Phase 1 validation question;
- follow-ups reuse personal actions/Google Tasks;
- same-name-only auto-merge is prohibited;
- public repo contains schemas/contracts only, never real people data.

See `docs/PEOPLE.md` and `docs/decisions/2026-09-03-people-subsystem-architecture.md`.

## Canonical ownership shortcut

```text
LLM4LIFE machine state       -> Neon/PostgreSQL
Personal actions             -> Neon
Personal action client       -> Google Tasks
Shared event/runtime layer   -> Cloudflare where workload fits
Scheduled execution          -> Google Calendar
Personal-care inventory      -> Product Tracker / Neon
Product Tracker UI rollback  -> Notion projection/reference
General shopping/list state  -> Neon when structured automation is justified
Engineering work             -> Jira
Code/repository truth        -> GitHub
Coding-agent orchestration   -> ORC
Knowledge/reasoning          -> Obsidian
Stable person identity       -> Neon target after People migration
Structured relationship state-> Neon target after People migration
Relationship narrative       -> Obsidian
Address-book client          -> Google Contacts after People cutover
Consolidated finance         -> InUnity
Official provider state      -> respective provider
```

## Runtime verification rule

Before claiming a tool/runtime is live:

1. inspect `docs/STATUS.md` and `config/tools.yaml`;
2. perform a harmless live read when possible;
3. only claim a write/runtime cutover after an actual supported operation succeeds;
4. distinguish target architecture from deployed reality.

For People specifically, do not infer “Neon owns People” means the schema/import exists. The current migration state is explicitly Phase 0.

## Free-first / component review

Prefer already-paid capability, then strong free tiers/open source, then paid services only for material incremental value. No tool is retained merely because it is already in the stack; evaluate **keep / reposition / consolidate / replace / retire** as architecture evolves.
