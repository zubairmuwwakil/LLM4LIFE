# Runtime Status

_Last updated: 2026-09-04_

This file describes **what is actually live now**. Long-term target ownership is defined by `config/domains.yaml`, `system.yaml`, domain contracts such as `docs/PEOPLE.md`, and `docs/LONG_TERM_ROADMAP.md`.

## Headline

LLM4LIFE v2 is live with Neon as durable machine state, Google Tasks as the human action projection, Google Calendar as the execution schedule, and Product Tracker/Neon as the canonical personal-care inventory service.

Product Tracker Phase 2 reliability and write cutover are complete. Production is on Worker `v0.4.0`, Notion inbound inventory sync is disabled, durable reliability status/DLQ receipts are live, and stable Notion event-idempotency hardening is deployed.

The **People / Relationships identity layer and Apple→Google provider migration are now production-live**. Neon holds stable People identity and Google provider refs; the reconciled Google address book contains the preserved original contacts plus the Apple-only creates. Google mutable-field authority is **not yet formally cut over** until Apple-device sync is verified.

## Current architecture

```text
                         ChatGPT / LLM4LIFE
                                |
            +-------------------+-------------------+
            |                   |                   |
            v                   v                   v
         Neon             Google Calendar      Domain systems
   durable machine state     execution time    Jira/GitHub/ORC,
            |                                     InUnity, etc.
      +-----+-------------------+
      |                         |
      v                         v
Google Tasks              Product Tracker
human action UI           personal-care inventory
      |                         |
Cloudflare Worker         Cloudflare Worker
sync runtime              + Queue + Hyperdrive
                                |
                                v
                              Neon
                     canonical inventory/events
                                |
                                v
                         Notion projection/UI
```

## Verified planning state

- Neon `llm4life.actions` is canonical personal action/backlog state.
- Google Tasks is production-live as the human-facing task projection/capture surface.
- Google Calendar owns scheduled execution and fixed commitments.
- Notion planning databases are rollback/reference only.
- Personal-care inventory is canonical in Neon database `product_tracker`, owned through the Product Tracker domain service.

## Product Tracker production state

### Baseline

Verified at migration baseline:

- 25 active Needs;
- 26 active Products;
- 26 balances;
- 26 baseline inventory events;
- zero orphan Product/balance relationships;
- zero balance-vs-baseline mismatches;
- derived inventory health: 5 `BUY_NOW`, 1 `RESTOCK`, 19 `STOCKED`.

The 25/26 relationship is expected because one functional Need has two active SKUs.

### Runtime

Live Worker:

```text
llm4life-product-tracker
```

Production path:

```text
ChatGPT / clients
      |
      v
Cloudflare Worker
 authenticated API
      |
      v
  Hyperdrive
      |
      v
     Neon
 canonical inventory/events
 outbox + webhook receipts
 dead-letter receipts
      |
      v
Cloudflare Queue
 retries + reconciliation
      |
      v
Notion projection
```

Verified cutover/reliability behavior:

- `GET /health` succeeds and reports Product Tracker `v0.4.0` with `notionInboundSyncEnabled=false`;
- authenticated reliability status reports zero failed/overdue/dead-letter work when clean;
- protected `/internal/relay` is clean when no durable work is pending;
- duplicate/retried API mutations create exactly one canonical InventoryEvent;
- outbound Neon → Notion projection works;
- application-side failures use durable backoff and become terminal `FAILED` at attempt 8;
- reconciliation recovered deliberately pending durable work without duplicate Notion side effects;
- deliberate staging queue-handler crashes were retried by Cloudflare and delivered to the DLQ;
- durable `DeadLetterEvent` persistence and reliability status are live;
- Worker database access uses Hyperdrive and the dedicated least-privilege Neon runtime role;
- Prisma/pg clients are invocation-scoped in Workers;
- Notion Inventory Events carries `Product Tracker Event ID`, and projection queries that stable ID before create.

### Ownership boundary

Product Tracker/Neon is the **canonical personal-care inventory owner**.

Production sets `NOTION_INBOUND_SYNC_ENABLED=false`. Signed Notion webhook calls remain authenticated/acknowledged but do not mutate Neon. Notion Shopping Needs, Products and Inventory Events are projection/reference/rollback surfaces only.

All human/agent personal-care inventory mutations must route through Product Tracker domain events. Do not silently dual-write or fall back to Notion when Product Tracker/Neon is unavailable.

### Remaining closeout

The 24-hour post-cutover observation window and temporary reliability staging cleanup remain. These are operational closeout tasks, not ownership blockers.

## People / Relationships — production state

The production Neon schema includes:

- `llm4life.people`
- `llm4life.relationships`
- `llm4life.person_facts`
- `llm4life.interactions`
- `llm4life.interaction_people`
- `llm4life.action_people`

People reuses the generic `llm4life.external_refs` model rather than introducing a separate `person_external_refs` table.

### Initial Google identity import

The stable-ID Google baseline contained 753 saved contacts. Conservative classification/import produced:

- 720 Google person refs;
- 716 canonical active People;
- 33 clear non-person/service holdouts;
- 3 clean duplicate clusters collapsed, representing 7 source refs;
- zero orphan refs;
- exact provider-ID coverage and idempotent rerun verified.

### Apple → Google provider migration

The private Apple export contained 451 contacts. Reconciliation produced:

- 246 clean one-to-one high-confidence existing-Google matches;
- 181 Apple-only contacts eligible for Google create;
- 12 identity conflicts held;
- 11 name-only weak matches held;
- 1 empty record held;
- 31 notes held for classification;
- 115 Apple photos detected.

The approved non-destructive provider apply completed successfully. Post-apply verification shows:

- 934 Google saved contacts with 934 unique stable provider IDs;
- all 753 original Google IDs preserved;
- exactly 181 Apple-only contacts created;
- no provider contact deletions;
- transient create failures protected by uncertainty-safe idempotent recovery.

### Post-apply Neon reconciliation

The 181 new Google contacts were reviewed against the People-domain boundary:

- 169 person-like refs imported to Neon;
- 12 obvious service/sample contacts kept provider-only;
- 885 active People total;
- 889 Google person refs total;
- zero orphan refs;
- zero non-active People introduced;
- zero email/phone/address/birthday/note values copied into new external-ref metadata;
- exact new-ref set and idempotent rerun verified.

Neon therefore owns stable person identity and provider mappings. Google continues to hold mutable address-book values. Obsidian remains the intended narrative owner.

### Still pending

- Apple-device sync/consumption verification;
- formal declaration of Google Contacts as mutable address-book field authority after that verification;
- review of held identity conflicts/name-only matches and note candidates;
- live Obsidian People linkage/capture;
- relationship automation beyond the base schema/action linkage.

Do not destructively clean provider or Obsidian state. Provider deletion is not authorized.

Read `docs/PEOPLE.md`, `docs/people/APPLE_GOOGLE_MIGRATION.md`, the historical `docs/people/PHASE_1_REPORT.md`, and the dated People decision before People work.

## Runtime paths

| System | Status | Role |
|---|---|---|
| ChatGPT / LLM4LIFE | Live | Control plane / orchestration |
| Neon | Live | Durable machine state + canonical stable People identity + Product Tracker canonical inventory |
| Google Tasks | Production-live | Human action projection/capture |
| Google Calendar | Live | Execution schedule and commitments |
| Cloudflare | Production-live | Google Tasks sync + Product Tracker Worker/Queue/Hyperdrive runtime |
| Product Tracker | Production canonical v0.4.0 | Specialized personal-care inventory owner |
| Notion | Auxiliary | Planning rollback + personal-care projection/reference |
| InUnity | MCP live/read-verified | Finance domain |
| Obsidian | Partial | Narrative knowledge/relationship context; live People bridge pending |
| Google Contacts | Provider migration complete | Reconciled address book; mutable-field authority declaration pending Apple sync verification |
| Apple Contacts | Migration source / current device client | Target synchronized client; sync verification pending |
| Jira / ORC / GitHub | Live by domain | Engineering backlog / coding orchestration / code truth |

## Next priorities

### P0 — Verify Apple contact sync

Confirm an Apple device is consuming the reconciled Google contact state without material field loss. If verified, declare Google Contacts the mutable address-book field authority and Apple Contacts the synchronized device client.

### P0 — Observe and close Product Tracker staging

Run the 24-hour post-cutover check. If health, durable retry state and projection remain clean, remove temporary reliability staging resources through their normal cleanup gate.

### P1 — People held-item review

Review the identity-conflict/name-only hold set and classify held notes. Do not silently auto-resolve ambiguous people and do not copy narrative notes into Neon.

### P1 — Live Obsidian bridge

```text
AI/router -> authenticated local adapter -> live vault -> normal vault backup/sync
```

Link stable People identities to narrative notes without turning Obsidian prose into duplicate database blobs.

### P1 — Household operations

Populate generic household/vehicle asset + maintenance state while keeping personal-care inventory inside Product Tracker.

See `docs/LONG_TERM_ROADMAP.md` for the broader sequence.

## Public repository constraint

Public repositories contain architecture, contracts, schemas, synthetic examples and non-sensitive aggregate runtime metadata only. Never commit database URLs, passwords, OAuth credentials, refresh tokens, API tokens, webhook secrets, private inventory/task payloads, private relationship/contact details, provider person IDs, health records, financial identifiers, confidential work content, or private message bodies.