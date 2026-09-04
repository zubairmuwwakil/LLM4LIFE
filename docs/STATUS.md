# Runtime Status

_Last updated: 2026-09-04_

This file describes **what is actually live now**. Long-term target ownership is defined by `config/domains.yaml`, `system.yaml`, domain contracts such as `docs/PEOPLE.md`, and `docs/LONG_TERM_ROADMAP.md`.

## Headline

LLM4LIFE v2 is live with Neon as durable machine state, Google Tasks as the human action projection, Google Calendar as the execution schedule, and Product Tracker/Neon as the canonical personal-care inventory service.

Product Tracker Phase 2 reliability and write cutover are complete. Production is on Worker `v0.4.0`, Notion inbound inventory sync is disabled, durable reliability status/DLQ receipts are live, and the stable Product Tracker Event ID query-before-create hardening is deployed.

The **People / Relationships canonical identity layer is now live in production Neon**, and the approved non-destructive Apple → Google Contacts provider migration has completed. Production currently has 885 active People rows and 889 Google person external refs with zero orphans. Google Contacts is the intended mutable standard address-book field owner, but Apple-device sync verification is still required before that field-authority cutover is declared fully live.

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
            |
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
- Prisma/pg clients are invocation-scoped in Workers after a cross-request I/O bug was caught during staging;
- Notion Inventory Events now carries `Product Tracker Event ID`, and projection queries that stable ID before create to close the known create-then-pointer retry window for future events.

### Ownership boundary

Product Tracker/Neon is the **canonical personal-care inventory owner**.

Production sets `NOTION_INBOUND_SYNC_ENABLED=false`. Signed Notion webhook calls remain authenticated/acknowledged but do not mutate Neon. Notion Shopping Needs, Products and Inventory Events are projection/reference/rollback surfaces only.

All human/agent personal-care inventory mutations must route through Product Tracker domain events. Do not silently dual-write or fall back to Notion when Product Tracker/Neon is unavailable.

### Remaining closeout

The 24-hour post-cutover observation window and temporary reliability staging cleanup remain. These are operational closeout tasks, not ownership blockers.

## People / Relationships — canonical identity live

The production Neon schema includes:

- `llm4life.people`
- `llm4life.relationships`
- `llm4life.person_facts`
- `llm4life.interactions`
- `llm4life.interaction_people`
- `llm4life.action_people`

The generic `llm4life.external_refs` model is reused for People mappings. It supports provider `account_scope`, first/last-seen timestamps and archive lifecycle metadata.

### Canonical Google identity import

The initial complete Google saved-contact inventory contained 753 contacts. After conservative person/service filtering and collapse of three previously reviewed clean duplicate clusters, the initial canonical import established:

- 720 Google person external refs;
- 716 canonical active People rows;
- 3 clean duplicate clusters collapsed;
- 7 source refs participating in those duplicate clusters;
- zero orphan Google person refs;
- no raw phone/email/address/birthday/note payload copied into Neon.

### Apple → Google provider cutover

The approved non-destructive Apple → Google migration completed against 451 Apple contacts.

Reconciliation before writes identified:

- 246 one-to-one high-confidence existing-contact matches;
- 181 Apple-only contacts planned for create;
- 12 identity conflicts held;
- 11 name-only weak matches held;
- 1 empty Apple export record held;
- 31 Apple notes held for classification rather than auto-write.

The final private refreshed Google snapshot verifies:

- 934 saved Google contacts;
- 934 unique provider-stable IDs;
- all original 753 Google provider IDs retained;
- exactly 181 new provider IDs created from Apple-only records;
- zero original provider IDs lost;
- no provider deletion performed.

The 181 new provider records were classified conservatively before Neon import. 169 person-like refs were imported, while 12 obvious demo/test/non-person/service records remain provider-only.

### Current production People totals

Verified after cutover:

- 885 People rows;
- 885 active People rows;
- 889 Google person external refs;
- zero orphan Google person refs;
- zero archived Google person refs.

The 4-ref difference between active People and Google person refs is expected from the previously reviewed duplicate clusters.

For the 169 newly imported refs, Neon metadata contains only `etag`, `external_id_stability`, `snapshot_generated_at`, and `source`. Raw contact values remain provider-authoritative and were not copied into Neon.

### Field authority

Neon is live as the stable person-identity and structured People machine-state owner.

Google Contacts is now the canonical provider address book after the Apple → Google migration, but **mutable standard contact-field authority is not yet declared fully live** until Apple Contacts is verified to consume/sync the Google-canonical address book on the user’s devices.

Apple Contacts remains the device client during this final verification step. Obsidian remains the narrative relationship-context owner.

Provider deletion and destructive legacy cleanup remain out of scope without new approval.

Read `docs/PEOPLE.md`, `docs/people/PHASE_2_PRODUCTION_RECEIPT.md`, `config/people-phase2.yaml`, and the historical `docs/people/PHASE_1_REPORT.md` before People work.

## Runtime paths

| System | Status | Role |
|---|---|---|
| ChatGPT / LLM4LIFE | Live | Control plane / orchestration |
| Neon | Live | Durable machine state + Product Tracker canonical inventory + canonical People identity state |
| Google Tasks | Production-live | Human action projection/capture |
| Google Calendar | Live | Execution schedule and commitments |
| Cloudflare | Production-live | Google Tasks sync + Product Tracker Worker/Queue/Hyperdrive runtime |
| Product Tracker | Production canonical v0.4.0 | Specialized personal-care inventory owner |
| Notion | Auxiliary | Planning rollback + personal-care projection/reference |
| InUnity | MCP live/read-verified | Finance domain |
| Obsidian | Partial | Narrative knowledge/relationship context; live bridge pending |
| Google Contacts | Provider migration complete | Canonical provider address book; mutable-field authority pending Apple sync verification |
| Apple Contacts | Sync verification pending | Target synchronized device client |
| Jira / ORC / GitHub | Live by domain | Engineering backlog / coding orchestration / code truth |

## Next priorities

### P0 — Verify Apple Contacts sync and close People field authority

1. Verify Apple Contacts on the user’s devices is consuming/syncing the Google-canonical address book as intended.
2. If verified, declare Google Contacts the live mutable standard contact-field authority and Apple Contacts the synchronized client.
3. Keep Neon as stable identity / structured People machine state; do not copy raw address-book payloads into Neon.

### P0 — Review held People migration candidates

Review separately, without broad auto-merge or destructive cleanup:

- 12 identity conflicts;
- 11 name-only weak matches;
- 31 Apple note candidates for Obsidian-vs-structured-fact routing.

### P0 — Observe and close Product Tracker staging

Run the 24-hour post-cutover check. If health, durable retry state and projection remain clean, remove the temporary reliability Worker/Queues and temporary Neon reliability branch.

### P1 — Live Obsidian bridge

```text
AI/router -> authenticated local adapter -> live vault -> normal vault backup/sync
```

People narrative linkage should build on this when practical rather than treating the private backup repository as the permanent real-time application API.

### P1 — Remaining Notion cleanup

Retain useful Product Tracker dashboard/rollback views but do not restore Notion to source-of-truth responsibilities.

### P1 — Household operations

Populate generic household/vehicle asset + maintenance state while keeping personal-care inventory inside Product Tracker.

See `docs/LONG_TERM_ROADMAP.md` for the broader sequence.

## Public repository constraint

Public repositories contain architecture, contracts, schemas, synthetic examples and non-sensitive runtime metadata only. Never commit database URLs, passwords, OAuth credentials, refresh tokens, API tokens, webhook secrets, private inventory/task payloads, private relationship/contact details, health records, financial identifiers, confidential work content, or private message bodies.
