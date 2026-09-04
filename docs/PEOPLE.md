# People & Relationships Subsystem

**Status:** Canonical identity live; Apple → Google provider migration complete; Apple-device sync verification pending  
**Decision date:** 2026-09-03  
**Schema deployment:** 2026-09-04  
**Production cutover:** 2026-09-04  
**Primary decision:** `docs/decisions/2026-09-03-people-subsystem-architecture.md`  
**Production receipt:** `docs/people/PHASE_2_PRODUCTION_RECEIPT.md`  
**Historical Phase 1 report:** `docs/people/PHASE_1_REPORT.md`

This document is the implementation contract for LLM4LIFE People/Relationships.

## Agent quick start

Before changing this subsystem:

1. Read `AGENTS.md`, `docs/STATUS.md`, this file, `config/people-phase2.yaml`, and the dated People decision.
2. Treat the newest explicit runtime decision as authoritative over historical migration docs.
3. Use stable Neon `person_id` values and generic provider refs; never use display names as keys.
4. Never auto-merge two people solely because names match.
5. Preserve provenance for structured facts and interactions.
6. Keep private contact payloads, provider IDs, OAuth material, plans, receipts, and relationship narrative out of the public repository.
7. Do not create a second task system for relationship follow-ups; use the existing LLM4LIFE action domain.
8. Keep imports/syncs idempotent, reversible, and observable.
9. Do not perform provider deletion or destructive legacy cleanup without separate explicit approval.
10. Check live provider/database state before writing; do not infer runtime from target docs alone.

## Goal

Create a reliable personal People/Relationships layer that lets LLM4LIFE resolve one real person across systems and operate on durable, privacy-conscious context without turning the stack into a life-ERP or surveillance archive.

The system should support questions such as:

- Who is this person across my systems?
- What durable context has been intentionally recorded about them?
- When did we last meaningfully interact?
- What did I promise to follow up on?
- What birthdays or important dates are upcoming?
- Which relationship actions are due or overdue?
- What source supports a structured fact?

## Non-goals

Do not:

- archive complete private conversations by default;
- automatically infer and persist sensitive personal attributes;
- assign reductive relationship scores by default;
- duplicate personal actions or Calendar commitments;
- replace Obsidian narrative notes with database blobs;
- make Google Contacts, Apple Contacts, Obsidian, and Neon independently editable competing truths;
- copy raw address-book data into Neon merely because it can be represented structurally.

## Current ownership

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
              |
        +-----+-------------------------+
        |              |                |
        v              v                v
 Google Contacts   LLM4LIFE actions  Google Calendar
 provider address    follow-ups       scheduled interaction
 book / field owner*      |
        |                 v
 Apple Contacts      Google Tasks
 synced device client
```

`*` Google Contacts is the intended mutable standard address-book field authority. Provider migration is complete, but that authority is not declared fully live until Apple-device sync is verified.

### Canonical responsibilities

| Object / field class | Current owner | Notes |
|---|---|---|
| Stable internal `person_id` | **Neon** | Production-live |
| Cross-system person mappings | **Neon** | Generic `llm4life.external_refs`; account-scoped |
| Structured relationship state | **Neon** | Operational machine state only |
| Structured durable person facts | **Neon** | Provenance required |
| Interaction metadata | **Neon** | Minimal metadata/source refs; not raw conversations |
| Long-form relationship narrative | **Obsidian** | Private human-readable context |
| Provider address book | **Google Contacts** | Canonical provider corpus after Apple migration |
| Mutable standard contact fields | **Google Contacts, pending final sync gate** | Declare fully live after Apple sync verification |
| Apple-device contact UX | **Apple Contacts** | Target synchronized device client |
| Relationship follow-up task | **LLM4LIFE action domain** | Project to Google Tasks |
| Scheduled interaction | **Google Calendar** | Real time commitment only |
| Communication history | **Original provider** | Link/reference rather than copy wholesale |

## Live production state

### Schema

Migration `db/migrations/004_people.sql` is production-live and provides:

- `llm4life.people`
- `llm4life.relationships`
- `llm4life.person_facts`
- `llm4life.interactions`
- `llm4life.interaction_people`
- `llm4life.action_people`

People reuses the generic `llm4life.external_refs` table. There is no `person_external_refs` table.

`external_refs` supports provider `account_scope`, first/last-seen timestamps, and archive lifecycle metadata.

### Initial Google canonical identity import

The complete initial Google saved-contact inventory contained 753 contacts.

After conservative person/service filtering and collapse of three reviewed safe duplicate clusters:

- 720 Google person external refs were imported;
- 716 canonical active People rows were created;
- 3 duplicate clusters were collapsed;
- 7 source refs participated in those clusters;
- zero orphan refs remained;
- raw phone/email/address/birthday/note payloads were not copied into Neon.

### Apple → Google provider migration

The approved non-destructive migration processed 451 Apple contacts against the 753-contact Google baseline.

Pre-write reconciliation:

- 246 one-to-one high-confidence existing-contact matches;
- 181 Apple-only contacts planned for create;
- 12 identity conflicts held;
- 11 name-only weak matches held;
- 1 empty export record held;
- 31 Apple notes held for classification;
- 115 Apple photos detected.

The migration writes are complete. Final provider verification found:

- 934 saved Google contacts;
- 934 unique provider-stable `people/...` IDs;
- all original 753 Google provider IDs retained;
- exactly 181 new Google provider IDs created from Apple-only records;
- zero original provider IDs lost;
- no provider deletion performed.

The cutover runtime is resumable and includes special recovery for ambiguous transient `createContact` failures so a 5xx does not cause blind duplicate creation.

### New provider refs → Neon

The 181 newly created provider records were classified conservatively:

- 169 person-like refs imported into Neon;
- 12 obvious demo/test/non-person/service records deliberately left provider-only.

Current verified production totals:

- 885 People rows;
- 885 active People rows;
- 889 Google person external refs;
- zero orphan Google person refs;
- zero archived Google person refs.

The 4-ref difference is expected from the previously reviewed duplicate clusters.

The exact sorted provider-ref set in Neon matches the reviewed private expected set.

For the 169 new refs, Neon metadata contains only:

- `etag`
- `external_id_stability`
- `snapshot_generated_at`
- `source`

No private phone, email, postal-address, birthday, or note values were copied into Neon.

## Stable identity rules

Every person has a stable Neon UUID.

Names, emails, phone numbers, birthdays, organizations, and other contact values are match signals/attributes—not primary identity.

Preferred resolution order:

1. exact existing external reference;
2. stable internal `person_id` supplied by the caller/source;
3. unique normalized strong contact point with supporting evidence;
4. multiple independent matching signals;
5. explicit user confirmation for ambiguous candidates.

**Never auto-merge on same/similar name alone.**

Merges must preserve reversible lineage and provider refs.

## Contact-field boundary

Neon owns stable person identity and structured People machine state.

Raw mutable address-book values remain provider-authoritative. `person_contact_points` remains intentionally deferred; do not duplicate phone/email/address/birthday into Neon without a newer explicit design decision demonstrating a concrete operational need.

Google Contacts now contains the reconciled provider corpus. The only remaining ownership gate is verifying that Apple Contacts on the user’s devices consumes/syncs the Google-canonical address book correctly.

After that verification:

- Google Contacts becomes the declared live mutable standard contact-field authority;
- Apple Contacts becomes the synchronized device client;
- Neon remains stable identity / structured relationship state;
- Obsidian remains narrative relationship memory.

Do not create a long-term bidirectional dual truth.

## Structured signal vs narrative

Use Neon for data that benefits from deterministic querying, provenance, automation, linking, or lifecycle integrity.

Use Obsidian for nuance, reflections, long-form context, diary history, and relationship narrative.

A fact does not belong in Neon merely because it can be represented as a column.

### Provenance

Structured facts should distinguish at least:

- explicit user assertion;
- user-edited/imported contact data;
- provider-derived observation;
- interaction-derived observation;
- model-derived suggestion/inference.

Model inference is not equivalent to user-asserted truth. Sensitive model suggestions are not silently persisted as sensitive facts.

## Privacy policy

People data is private even when the architecture repository is public.

Never commit actual:

- private names/contact profiles as migration payloads;
- provider person/contact IDs;
- phone numbers/emails/addresses;
- birthdays;
- interaction summaries;
- relationship notes;
- message bodies;
- OAuth credentials/tokens;
- private reconciliation plans or receipts.

Public repo content may contain schemas, synthetic fixtures, architecture, aggregate counts, and non-sensitive operational status.

Do not automatically persist inferred sensitive facts such as health status, religion, politics, sexuality, criminal history, or similarly sensitive attributes merely because a message or model inference suggests them.

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

## Held migration work

The following were intentionally not auto-resolved during provider migration:

- 12 identity conflicts;
- 11 name-only weak matches;
- 31 Apple notes requiring classification;
- 1 empty Apple export record.

These are review queues, not blockers for the canonical identity or provider migration.

Do not resolve the identity queues using name similarity alone. Notes should be routed deliberately to Obsidian narrative, a structured fact with provenance, or nowhere if they are stale/noisy.

## Current next gate

1. Verify Apple Contacts on the user’s devices is consuming/syncing the Google-canonical provider address book.
2. If verified, declare Google Contacts live mutable standard contact-field authority and Apple Contacts the synchronized client.
3. Review held identity conflicts and weak matches separately.
4. Review note candidates separately.
5. Keep provider deletion and destructive cleanup out of scope unless separately approved.

## Reliability requirements

Recurring sync/import workers must have:

- durable cursor/checkpoint;
- stable job identity;
- idempotency keys;
- retries with bounded failure policy;
- execution receipts;
- duplicate/conflict metrics;
- last-success timestamp;
- dead-letter/error visibility when async delivery is used;
- least-privilege credentials.

The Apple → Google cutover runtime additionally guards ambiguous create outcomes by reconciling before retry so transient 5xx responses cannot produce blind duplicate POSTs.

Do not rely on a long-running chat thread as operational state.

## Testing expectations

Tests should continue covering:

- external-ref uniqueness and account scoping;
- idempotent import rerun;
- same-name different-person case;
- renamed contact same-person case;
- multiple emails/phones;
- provider record archived/deleted handling;
- ambiguous merge remains unmerged;
- merge rollback/audit;
- Obsidian link without narrative duplication;
- follow-up links to the existing LLM4LIFE action rather than duplicate task state;
- sensitive inference is not silently persisted;
- projection retry does not duplicate provider objects;
- transient provider create failure cannot create a duplicate on retry.

## Accepted/current decisions

- Neon owns stable internal person identity and structured People machine state.
- People uses generic `llm4life.external_refs`.
- Google Contacts contains the canonical reconciled provider address book.
- Google Contacts is the intended mutable contact-field authority, pending Apple sync verification.
- Apple Contacts is the target synchronized device client.
- Obsidian owns narrative relationship memory.
- Relationship follow-ups use the existing personal action system.
- Calendar owns scheduled interactions.
- Provenance and conservative dedup are mandatory.
- Raw conversation archival is not the default.
- Provider deletion is not authorized.

## Open design space

- exact fact taxonomy and sensitivity classes;
- whether a derived minimal contact-point matching index becomes useful later;
- best long-term local Apple Contacts bridge implementation if provider sync alone proves insufficient;
- interaction granularity and automation thresholds;
- later People automation after data quality is proven.

## Anti-patterns

Do not:

- create a competing People reference table without a concrete proven need;
- use names as foreign keys;
- automatically merge on fuzzy-name similarity;
- write the same relationship narrative to Neon, Obsidian, and Google Contacts notes;
- create recurring “keep in touch” tasks for everyone without user-value evidence;
- infer private facts from silence/message tone and store them as truth;
- introduce long-term bidirectional contact-field dual-write;
- delete legacy provider/Obsidian state before reconciliation and rollback are verified.

## Definition of subsystem success

People/Relationships succeeds when one real person resolves to one stable internal identity across systems; contact reconciliation is deterministic and reversible; provider writes are resumable/idempotent; narrative remains private/readable in Obsidian; structured facts have provenance; follow-ups reuse the action engine; Calendar remains execution-only; and future agents can determine owner, runtime state, invariants, tests, and rollback without relying on chat history.
