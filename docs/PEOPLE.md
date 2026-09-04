# People & Relationships Subsystem

**Status:** Phase 1 schema live in production; complete read-only contact inventory and reconciliation still pending  
**Decision date:** 2026-09-03  
**Schema deployment:** 2026-09-04  
**Primary decision:** `docs/decisions/2026-09-03-people-subsystem-architecture.md`  
**Phase 1 report:** `docs/people/PHASE_1_REPORT.md`  
**Historical audit:** `docs/inventory/PEOPLE_CONTACTS_AND_RELATIONSHIPS.md`

This document is the implementation contract for LLM4LIFE People/Relationships.

It distinguishes **target architecture** from **live runtime**. The minimum People schema is now live, but no real contact import/dedup cutover has occurred.

## Agent quick start

Before changing this subsystem:

1. Read `AGENTS.md`, `docs/STATUS.md`, this file, the dated People decision, `docs/people/PHASE_1_REPORT.md`, `config/domains.yaml`, and `system.yaml`.
2. Check the current migration phase before writing data or changing ownership.
3. Prefer read-only inventory and dry-run reconciliation before any import/merge.
4. Never merge two people solely because their names match.
5. Use stable internal person IDs and generic provider external references; display names are not keys.
6. Preserve provenance for structured facts and interactions.
7. Do not copy relationship narrative or raw private conversations into the public repository.
8. Do not create a second task system for relationship follow-ups; use the existing LLM4LIFE action domain.
9. Make imports/idempotent syncs safe to rerun.
10. If a better architecture is discovered, propose it with tradeoffs and migration impact rather than silently diverging.

## Goal

Create a reliable personal People/Relationships layer that lets LLM4LIFE answer and act on questions such as:

- Who is this person across my systems?
- What durable context have I intentionally recorded about them?
- When did we last meaningfully interact?
- What did I promise to follow up on?
- What birthdays or important dates are upcoming?
- Which relationship actions are due or overdue?
- What source supports a structured fact?

The user should be able to communicate naturally. The system should resolve the person, classify the information, store only durable signal, and route actions/schedule/context to the correct owner.

## Non-goals

Do **not** build a life-ERP or surveillance archive.

This subsystem is not intended to:

- archive complete private conversations;
- automatically infer and persist sensitive personal attributes;
- assign reductive relationship scores by default;
- duplicate the personal action backlog;
- duplicate Calendar commitments;
- replace Obsidian narrative notes with database blobs;
- create a paid personal-CRM dependency when the existing stack can do the job;
- make Google Contacts, Apple Contacts, Obsidian and Neon independently editable competing truths.

## Target ownership

```text
                     LLM4LIFE / AI
                          |
                    resolve person
                          |
              +-----------+-----------+
              |                       |
              v                       v
        Neon People state        Obsidian
     stable identity + refs      narrative memory
     structured operations       reflections/context
     facts + provenance          linked long-form notes
              |
        +-----+-------------------------+
        |              |                |
        v              v                v
 Google Contacts   LLM4LIFE actions  Google Calendar
 address-book UI     follow-ups       scheduled interaction
        |
 Apple Contacts
 synced device client
```

### Canonical responsibilities

| Object / field class | Target owner | Notes |
|---|---|---|
| Stable internal `person_id` | Neon | Production schema live; no real People imported yet |
| Cross-system person mappings | Neon | Uses generic `llm4life.external_refs`; no `person_external_refs` table |
| Structured relationship state | Neon | Schema live; empty pending import |
| Structured durable person facts | Neon | Provenance required; schema live |
| Interaction metadata | Neon | Minimal metadata/source refs; not raw conversation archives |
| Long-form relationship narrative | Obsidian | Human-readable private notes, diary/reflections, nuanced context |
| Address-book UI | Google Contacts | Target human-facing client; field-authority cutover not yet complete |
| Apple-device contact UX | Apple Contacts | Current source/client during migration; target synchronized client |
| Relationship follow-up task | Existing LLM4LIFE action domain | Project to Google Tasks; do not create a separate task backend |
| Scheduled interaction | Google Calendar | Real time commitment only |
| Communication history | Original provider | Source/evidence surface; do not copy wholesale by default |

### Contact-field authority during migration

Apple and Google Contacts remain fragmented. Existing provider records remain live source material until reconciliation/cutover completes.

**Current conditional recommendation:** Neon owns stable person identity, generic provider refs and structured relationship state, while Google Contacts becomes authoritative for mutable address-book fields only if complete Apple/iCloud inventory demonstrates that required fields and records can be preserved. This is not a production field-ownership cutover yet.

Do not create long-term bidirectional dual truth.

## Design principles

### 1. Stable identity before automation

Every person gets a stable internal UUID. Names, emails and phone numbers are attributes/match signals, not primary identity.

External references are unique within provider/account scope.

### 2. One generic external-reference model

People reuses `llm4life.external_refs`, the existing cross-domain mapping primitive. Provider refs are keyed by system, account scope, internal type and external ID. Do not introduce a duplicate `person_external_refs` table unless a newer explicit decision proves the generic abstraction inadequate.

### 3. Link, do not copy

Obsidian narrative should reference a stable person identity. Neon should reference the canonical Obsidian note when useful rather than copying the full prose.

Provider messages, Calendar events and Contacts records should normally be linked through external references rather than copied wholesale.

### 4. Structured signal vs narrative context

Use Neon for data that benefits from deterministic querying, deduplication, event processing or automation.

Use Obsidian for nuance, reflections, long-form context, diary history and knowledge that is better read as prose.

A fact does not belong in Neon merely because it can be represented as a column.

### 5. Provenance is first-class

A future agent must be able to answer: **Where did this fact come from?**

Structured facts should preserve enough provenance to distinguish at least:

- explicit user assertion;
- user-edited/imported contact data;
- provider-derived observation;
- interaction-derived observation;
- model-derived suggestion/inference.

Model inference is not equivalent to user-asserted truth. Sensitive model suggestions are not silently persisted as sensitive facts.

### 6. Conservative identity merging

Preferred resolution order:

1. existing exact external reference;
2. existing stable internal ID supplied by the source;
3. unique normalized strong contact point with supporting evidence;
4. multiple independent matching signals;
5. user confirmation for ambiguous cases.

**Never auto-merge on same/similar name alone.**

### 7. Reversible migration

Imports, merges and cutovers require:

- dry-run output;
- before/after counts;
- deterministic idempotency keys;
- preserved provider IDs;
- reversible merge/audit information;
- no destructive cleanup until reconciliation passes.

### 8. Minimum useful system

Do not pre-build every conceivable CRM feature. Add a table/field only when it has a concrete retrieval, routing, automation or integrity purpose.

## Live Phase 1 data model

Migration `db/migrations/004_people.sql` is production-live and adds:

### `people`

Stable internal identity, archive state and reversible merge lineage.

### Generic `external_refs`

People-specific provider mappings use the existing `llm4life.external_refs` table. Phase 1 added `account_scope`, first/last-seen timestamps and archive lifecycle metadata to make provider identity account-safe.

### `relationships`

Small operational relationship state only. Narrative remains in Obsidian.

### `person_facts`

Flexible structured facts with provenance, confidence, sensitivity classification and supersession.

### `interactions`

Minimal interaction/event metadata. `occurred_on` is required and `occurred_at` is optional so date-only history does not invent time-of-day precision.

### `interaction_people`

Many-person interaction linkage.

### `action_people`

Relationship/person linkage to the existing canonical personal-action lifecycle. This is not another task backend.

### Contact points

`person_contact_points` remains intentionally deferred. Do not duplicate phone/email/address/birthday into Neon until complete inventory and field-authority testing proves the copy is justified.

## Runtime state after schema deployment

Verified immediately after production migration on 2026-09-04:

- all six People tables exist;
- People rows: 0;
- person facts: 0;
- interactions: 0;
- 95 existing generic external refs preserved;
- no real contacts imported or mutated.

This means the backend structure is live, but **identity migration and provider cutover are not**.

## Privacy and inference policy

People data is private even when the architecture repo is public.

Never commit actual:

- names/contact profiles;
- provider person/contact IDs;
- phone numbers/emails/addresses;
- birthdays;
- interaction summaries;
- relationship notes;
- message bodies.

Public repo content may include schemas, placeholder examples and non-sensitive architecture only.

Do not automatically persist inferred sensitive facts such as health status, religion, politics, sexuality, criminal history or similarly sensitive attributes merely because a message or model inference suggests them.

## Capture/routing contract

For natural-language input about a person:

```text
input
  |
resolve person
  |
classify information
  |
  +--> identity/contact update -> People/contact pipeline
  +--> structured durable fact -> Neon + provenance
  +--> narrative context ------> Obsidian
  +--> meaningful interaction -> Neon metadata + optional Obsidian narrative
  +--> follow-up -------------> LLM4LIFE action
  +--> fixed meeting/date ----> Google Calendar
  +--> transient/trivial -----> do not persist
```

One input may create more than one linked object when the concepts are genuinely different; avoid copying the same payload into every system.

## Migration sequence

### Phase 0 — documentation

Complete.

### Phase 1 — schema + read-only inventory

**Schema portion complete and production-live. Inventory portion still incomplete.**

Completed:

1. reviewed migrations `001-003` and production schema drift;
2. selected generic `external_refs` over a People-specific duplicate;
3. built and tested `004_people.sql`;
4. validated synthetic identity/dedup invariants on a disposable Neon branch;
5. applied the approved schema to production;
6. verified zero People data and preservation of 95 existing refs;
7. inspected Google Contacts connector behavior read-only;
8. defined the Apple vCard / future `CNContactStore` path;
9. built a deterministic dry-run duplicate-candidate engine.

Still required before real import:

1. complete Google saved-contact inventory through a supported enumeration path;
2. complete Apple/iCloud inventory privately;
3. run the candidate engine against the private normalized corpus;
4. review conflicts and field-preservation semantics;
5. decide mutable contact-field authority explicitly.

### Phase 2 — canonical identity import

Only after the remaining Phase 1 inventory gates pass and real-contact import is explicitly approved:

1. import stable `people` rows and generic external refs;
2. rerun and prove idempotency;
3. route ambiguous duplicates to review;
4. preserve merge lineage and durable receipts;
5. reconcile source counts and require zero orphan refs.

### Phase 3 — address-book projection/cutover

1. finalize field authority;
2. verify Google create/update/delete/ETag semantics on bounded synthetic contacts;
3. project/reconcile canonical state;
4. verify Apple-device consumption/sync;
5. stop maintaining independent Apple/Google truths.

### Phase 4 — Obsidian linkage + conversational capture

Map stable person IDs to Obsidian narrative notes without copying prose into Neon, then add conservative conversational fact/interaction capture.

### Phase 5 — relationship automation

Only after data quality is proven: due follow-ups, explicit promised-follow-up detection, birthday preparation, and lightweight reconnection suggestions. Reuse existing actions and Calendar.

## Observability and reliability requirements

Any recurring sync/import worker must have:

- durable cursor/checkpoint;
- stable job identity;
- idempotency keys;
- retries with bounded failure policy;
- execution receipts;
- duplicate/conflict metrics;
- last-success timestamp;
- dead-letter/error visibility when async delivery is used;
- least-privilege credentials.

Do not rely on a long-running chat thread as operational state.

## Testing expectations

Before contact cutover, tests must continue covering:

- external-ref uniqueness and account scoping;
- idempotent import rerun;
- same-name different-person case;
- renamed contact same-person case;
- multiple emails/phones;
- provider record deleted/archived;
- ambiguous merge remains unmerged;
- merge rollback/audit;
- Obsidian link without narrative duplication;
- follow-up links to the existing LLM4LIFE action rather than duplicate task state;
- sensitive inference is not silently persisted;
- projection retry does not duplicate provider objects.

## Agent development contract

Before coding, inspect current runtime state, current migration phase and supported provider interfaces. Use synthetic fixtures in this public repository. Keep changes rerunnable, auditable and reversible. Report what is deployed vs merely committed.

## Fixed decisions vs open design space

### Accepted/current

- Neon owns stable internal person identity and structured People machine state; schema is now live.
- People uses generic `llm4life.external_refs`, not a separate People-specific ref table.
- Obsidian owns narrative relationship memory.
- relationship follow-ups use the existing personal action system;
- Calendar owns scheduled interactions;
- provenance and conservative dedup are required;
- raw conversation archival is not the default.

### Explicitly open

- final mutable contact-field authority after complete Apple/Google inventory;
- exact fact taxonomy and sensitivity classes;
- whether a derived minimal contact-point matching index becomes useful later;
- best long-term local Apple Contacts bridge implementation;
- interaction granularity and automation thresholds.

## Anti-patterns

Do not:

- create a competing People reference table without a concrete proven need;
- use names as foreign keys;
- automatically merge on fuzzy-name similarity;
- write the same relationship narrative to Neon, Obsidian and Google Contacts notes;
- create recurring “keep in touch” tasks for everyone without user-value evidence;
- infer private facts from silence/message tone and store them as truth;
- introduce long-term bidirectional contact-field dual-write;
- delete legacy Apple/Google/Obsidian state before reconciliation and rollback are verified.

## Definition of subsystem success

People/Relationships succeeds when one real person resolves to one stable internal identity across systems; contact reconciliation is deterministic and reversible; narrative remains private/readable in Obsidian; structured facts have provenance; imports and retries are idempotent; relationship follow-ups reuse the action engine; Calendar remains execution-only; and future agents can determine current phase, owner, invariants, tests and rollback without relying on chat history.
