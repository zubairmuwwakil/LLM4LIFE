# People & Relationships Subsystem

**Status:** Phase 2 identity/provider migration live; Apple-device sync verification pending before Google mutable-field authority declaration  
**Decision date:** 2026-09-03  
**Schema deployment:** 2026-09-04  
**Provider migration:** 2026-09-04  
**Primary decision:** `docs/decisions/2026-09-03-people-subsystem-architecture.md`  
**Historical Phase 1 report:** `docs/people/PHASE_1_REPORT.md`  
**Provider migration runbook/receipt:** `docs/people/APPLE_GOOGLE_MIGRATION.md`

This document is the implementation contract for LLM4LIFE People/Relationships. It distinguishes target architecture from verified live runtime.

## Agent quick start

Before changing this subsystem:

1. Read `AGENTS.md`, `docs/STATUS.md`, this file, the dated People decision, `config/people-phase2.yaml`, `config/domains.yaml`, and `system.yaml`.
2. Treat the Phase 1 report as historical; use current status/config for live state.
3. Never merge two people solely because their names match.
4. Use stable internal person IDs and generic provider external references; display names are not keys.
5. Preserve provenance for structured facts and interactions.
6. Do not copy relationship narrative or raw private conversations into the public repository.
7. Do not create a second task system for relationship follow-ups; use the existing LLM4LIFE action domain.
8. Make imports and syncs idempotent and resumable.
9. Provider-contact deletion and destructive Obsidian cleanup are not authorized.
10. Do not declare Google mutable-field authority until Apple-device sync is verified.

## Goal

Create a reliable personal People/Relationships layer that lets LLM4LIFE resolve one person across systems, retain intentionally durable context with provenance, link meaningful interactions and follow-ups, and route each type of state to the correct owner.

The user should be able to communicate naturally. The system should resolve the person, classify the information, store only durable signal, and route actions/schedule/context without turning LLM4LIFE into a surveillance archive or duplicate CRM.

## Non-goals

Do **not**:

- archive complete private conversations;
- automatically infer and persist sensitive personal attributes;
- assign reductive relationship scores by default;
- duplicate the personal action backlog or Calendar commitments;
- replace Obsidian narrative notes with database blobs;
- make Google Contacts, Apple Contacts, Obsidian and Neon independently editable competing truths;
- copy provider-owned contact values into Neon without a demonstrated operational need.

## Ownership

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
 synchronized device client after verified cutover
```

### Canonical responsibilities

| Object / field class | Owner / current state |
|---|---|
| Stable internal `person_id` | **Neon — live** |
| Cross-system person mappings | **Neon — live**, via generic `llm4life.external_refs` |
| Structured relationship state | **Neon** |
| Structured durable person facts | **Neon**, provenance required |
| Interaction metadata | **Neon**, minimal metadata/source refs only |
| Long-form relationship narrative | **Obsidian** |
| Mutable standard address-book fields | **Google Contacts candidate**; provider migration complete, authority declaration pending Apple sync verification |
| Apple-device contact UX | **Apple Contacts** as target synchronized client; verification pending |
| Relationship follow-up task | Existing **LLM4LIFE action domain** → Google Tasks projection |
| Scheduled interaction | **Google Calendar** |
| Communication history | Original provider; link/reference rather than wholesale copy |

Do not create long-term bidirectional dual truth.

## Design principles

### Stable identity before automation

Every person gets a stable internal UUID. Names, emails and phone numbers are attributes/match signals, not primary identity. Provider references are unique within provider/account scope.

### One generic external-reference model

People reuses `llm4life.external_refs`. Do not introduce a `person_external_refs` duplicate unless a newer explicit decision proves the generic abstraction inadequate.

### Link, do not copy

Obsidian narrative should reference stable person identity. Provider messages, Calendar events and Contacts records should normally be linked through external references rather than copied wholesale.

### Structured signal vs narrative context

Use Neon for deterministic identity, relationships, provenance, interaction metadata and automation state. Use Obsidian for nuance, reflections and long-form relationship context.

### Provenance is first-class

Structured facts must distinguish user assertion, user-edited/imported data, provider observation, interaction observation and model suggestion. Model inference is not equivalent to user truth. Sensitive model suggestions are not silently persisted.

### Conservative identity merging

Preferred resolution order:

1. exact existing provider reference;
2. stable internal ID supplied by a trusted source;
3. unique normalized strong contact point with supporting evidence;
4. multiple independent matching signals;
5. user confirmation for ambiguity.

**Never auto-merge on same/similar name alone.**

### Reversible and idempotent migration

Imports, merges and provider writes require before/after counts, deterministic identities, provider IDs, receipts/checkpoints, conservative holds and non-destructive behavior. Ambiguous create failures must be reconciled before retry.

## Live data model

Migration `db/migrations/004_people.sql` is production-live and provides:

- `people` — stable internal identity and reversible merge lineage;
- generic `external_refs` — provider/account-scoped identity mapping;
- `relationships` — small operational relationship state;
- `person_facts` — structured facts with provenance/confidence/sensitivity/supersession;
- `interactions` — minimal interaction/event metadata;
- `interaction_people` — person linkage for interactions;
- `action_people` — person linkage into the existing canonical action lifecycle.

`person_contact_points` remains intentionally deferred. Phone/email/address/birthday stay provider-authoritative unless a later concrete runtime need justifies a minimal derived index.

## Verified production state

### Initial Google identity import

The original Google stable-ID inventory contained 753 saved contacts. Conservative classification/import produced:

- 720 Google person refs;
- 716 canonical active People;
- 33 non-person/service holdouts;
- 3 clean duplicate clusters collapsed, covering 7 source refs;
- zero orphans;
- exact external-ID set and rerun idempotency verified.

Only provider identity metadata and display names entered Neon; contact values did not.

### Apple → Google reconciliation and provider apply

Private reconciliation of 451 Apple contacts against the Google inventory produced:

- 246 clean one-to-one existing-Google matches;
- 181 Apple-only contacts eligible for create;
- 12 identity conflicts held;
- 11 name-only weak matches held;
- 1 empty record held;
- 31 notes held for classification;
- 115 Apple photos detected.

The approved non-destructive provider migration completed. Post-apply Google state:

- 934 saved contacts;
- 934 unique stable provider IDs;
- all 753 original Google IDs preserved;
- exactly 181 Apple-only contacts created;
- no provider deletions.

A live transient `createContact` 502 exposed an uncertainty window. The apply runtime was hardened so new creates carry deterministic temporary markers, retryable failures reconcile first, and a second POST happens only when the prior create is proven not to have landed. Markers are removed after durable success.

### Post-apply Neon import

The 181 new Google contacts were reviewed against the People-domain boundary:

- 169 person-like refs imported idempotently;
- 12 obvious service/sample contacts kept provider-only;
- 885 active People total;
- 889 Google person refs total;
- zero orphan refs;
- zero non-active People;
- zero contact-value keys in new provider-ref metadata;
- exact new-ref set and idempotent rerun verified.

This is the current production identity baseline.

## Privacy and inference policy

People data is private even when the architecture repo is public.

Never commit actual names/contact profiles, provider person IDs, phone numbers, emails, addresses, birthdays, interaction summaries, relationship notes, message bodies, OAuth material, private plans or provider receipts.

Public repo content may include schemas, synthetic fixtures, code, safety rules and non-sensitive aggregate runtime counts.

Do not automatically persist inferred sensitive facts such as health status, religion, politics, sexuality, criminal history or similarly sensitive attributes.

## Capture/routing contract

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

Complete. Historical details remain in `docs/people/PHASE_1_REPORT.md` and related receipts.

### Phase 2 — canonical identity import + Apple→Google migration

**Production-live.** Completed:

1. imported stable Google-backed People identities and generic provider refs;
2. proved idempotency and zero orphans;
3. conservatively collapsed only reviewed clean duplicate clusters;
4. reconciled the full Apple export against Google;
5. additively enriched clean Google matches;
6. created Apple-only Google contacts without destructive provider cleanup;
7. hardened transient-create recovery;
8. refreshed and verified stable Google IDs;
9. imported 169 new person-like refs to Neon while leaving 12 provider-only service/sample contacts outside People.

### Phase 3 — address-book authority cutover

In progress. Provider migration is complete; the remaining gate is to verify Apple-device consumption/sync without material field loss. After that verification, Google Contacts can be declared the mutable address-book field authority and Apple Contacts the synchronized device client.

Deletion/destructive duplicate cleanup is a separate approval gate and is not part of this phase by default.

### Phase 4 — Obsidian linkage + conversational capture

Map stable person IDs to Obsidian narrative notes without copying prose into Neon, then add conservative conversational fact/interaction capture.

### Phase 5 — relationship automation

Only after data quality is proven: due follow-ups, explicit promised-follow-up detection, birthday preparation and lightweight reconnection suggestions. Reuse existing actions and Calendar.

## Observability and reliability requirements

Any recurring People sync/import worker must have durable cursor/checkpoint, stable job identity, idempotency keys, bounded retries, execution receipts, duplicate/conflict metrics, last-success state and failure visibility. Do not rely on a long-running chat thread as operational state.

## Testing expectations

Continue covering:

- external-ref uniqueness/account scope;
- idempotent import rerun;
- same-name different-person and renamed-contact cases;
- multiple emails/phones;
- provider archive/deletion observation without unsafe deletion propagation;
- ambiguous merge remains held;
- merge rollback/audit;
- transient create ambiguity does not duplicate provider contacts;
- Obsidian linkage without narrative duplication;
- follow-up links to the existing action system;
- sensitive inference is not silently persisted.

## Fixed decisions vs open design space

### Accepted/current

- Neon owns stable internal person identity and structured People machine state.
- People uses generic `llm4life.external_refs`.
- Google provider migration is complete and Google holds mutable address-book values.
- Obsidian owns narrative relationship memory.
- Relationship follow-ups use the existing personal action system.
- Calendar owns scheduled interactions.
- Provenance and conservative dedup are required.
- Raw conversation archival is not the default.
- Provider deletion is not authorized.

### Still open / pending evidence

- formal Google mutable-field authority declaration after Apple sync verification;
- exact fact taxonomy and sensitivity classes;
- whether a minimal derived contact-point matching index becomes useful;
- best long-term local Apple Contacts bridge implementation;
- interaction granularity and automation thresholds.

## Anti-patterns

Do not create a competing People reference table, use names as foreign keys, auto-merge on fuzzy names, duplicate narrative across Neon/Obsidian/Google Contacts, create indiscriminate keep-in-touch tasks, store inferred private facts as truth, introduce long-term dual-write, or destructively clean legacy/provider state before an explicit authorized gate.

## Definition of subsystem success

People/Relationships succeeds when one real person resolves to one stable internal identity across systems; contact reconciliation is deterministic and reversible; mutable contact state has one owner; narrative remains private/readable in Obsidian; structured facts have provenance; imports/retries are idempotent; relationship follow-ups reuse the action engine; Calendar remains execution-only; and future agents can determine current phase, owner, invariants, tests and rollback without relying on chat history.