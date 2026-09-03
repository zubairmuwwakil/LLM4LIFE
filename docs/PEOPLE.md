# People & Relationships Subsystem

**Status:** Phase 0 architecture accepted; implementation not started  
**Decision date:** 2026-09-03  
**Primary decision:** `docs/decisions/2026-09-03-people-subsystem-architecture.md`  
**Historical audit:** `docs/inventory/PEOPLE_CONTACTS_AND_RELATIONSHIPS.md`

This document is the implementation contract for future agents working on LLM4LIFE People/Relationships.

It intentionally distinguishes **target architecture** from **live runtime**. Do not claim the People migration is complete merely because this design exists.

## Agent quick start

Before changing this subsystem:

1. Read `AGENTS.md`, `docs/STATUS.md`, this file, the dated People decision, `config/domains.yaml`, and `system.yaml`.
2. Check the current migration phase before writing data or changing ownership.
3. Prefer read-only inventory and dry-run reconciliation before any import/merge.
4. Never merge two people solely because their names match.
5. Use stable internal person IDs and provider external references; display names are not keys.
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
| Stable internal `person_id` | Neon | Never use display name as identity |
| Cross-system person mappings | Neon | Google/Apple/Obsidian/message/calendar refs |
| Structured relationship state | Neon | Type/status/cadence/open operational metadata when justified |
| Structured durable person facts | Neon | Only when queryable/operationally useful; provenance required |
| Interaction metadata | Neon | Minimal metadata/source refs; not raw conversation archives |
| Long-form relationship narrative | Obsidian | Human-readable private notes, diary/reflections, nuanced context |
| Address-book UI | Google Contacts | Target human-facing contact projection after dedup/cutover |
| Apple-device contact UX | Apple Contacts | Synced client after migration, not independent truth |
| Relationship follow-up task | Existing LLM4LIFE action domain | Project to Google Tasks; do not create a separate task backend |
| Scheduled interaction | Google Calendar | Real time commitment only |
| Communication history | Original provider | Source/evidence surface; do not copy wholesale by default |

### Contact-field authority during migration

Apple and Google Contacts are currently fragmented. Until reconciliation/cutover is complete, the current provider records remain live source material.

**Default target recommendation:** once the import/dedup pipeline is verified, Neon should own the stable person entity and intentionally managed structured contact state, with Google Contacts serving as the primary human-facing address-book projection and Apple Contacts consuming that set.

This recommendation is deliberately reviewable in Phase 1. If Google Contacts API semantics or operational reliability make field-level provider authority materially better for phone/email/address data, document that exception explicitly instead of creating silent bidirectional dual truth.

## Design principles

### 1. Stable identity before automation

Every person gets a stable internal ID. Names, emails and phone numbers are attributes/match signals, not primary identity.

External references should be unique within provider/account scope.

### 2. Link, do not copy

Obsidian narrative should reference a stable person identity. Neon should reference the canonical Obsidian note when useful rather than copying the full prose.

Provider messages, Calendar events and Google Contacts records should normally be linked through external references rather than copied wholesale.

### 3. Structured signal vs narrative context

Use Neon for data that benefits from deterministic querying, deduplication, event processing or automation.

Use Obsidian for nuance, reflections, long-form context, diary history and knowledge that is better read as prose.

A fact does not belong in Neon merely because it can be represented as a column.

### 4. Provenance is first-class

A future agent must be able to answer: **Where did this fact come from?**

Structured facts should preserve enough provenance to distinguish at least:

- explicit user assertion;
- user-edited/imported contact data;
- provider-derived observation;
- interaction-derived observation;
- model-derived suggestion/inference.

Model inference is not equivalent to user-asserted truth.

### 5. Conservative identity merging

Preferred resolution order:

1. existing exact external reference;
2. existing stable internal ID supplied by the source;
3. unique normalized contact point with strong evidence;
4. multiple independent matching signals;
5. user confirmation for ambiguous cases.

**Never auto-merge on same/similar name alone.**

### 6. Reversible migration

Imports, merges and cutovers require:

- dry-run output;
- before/after counts;
- deterministic idempotency keys;
- preserved provider IDs;
- reversible merge/audit information;
- no destructive cleanup until reconciliation passes.

### 7. Minimum useful system

Do not pre-build every conceivable CRM feature. Add a table/field only when it has a concrete retrieval, routing, automation or integrity purpose.

## Proposed Phase 1 data model

This is a **starting schema, not frozen implementation**. Future agents may improve it if they preserve the invariants above and document why.

### `people`

Minimum stable entity:

```text
id UUID PK
display_name
preferred_name nullable
status active|dormant|archived
created_at
updated_at
archived_at nullable
```

Avoid stuffing every contact field into this table before the contact-authority decision is verified.

### `person_external_refs`

Maps one person to provider/system objects.

```text
id UUID PK
person_id FK -> people.id
system_id
account_scope nullable
external_id
external_url nullable
ref_type
is_primary boolean
first_seen_at
last_seen_at
metadata jsonb nullable
UNIQUE(system_id, account_scope, external_id)
```

Candidate systems include Google Contacts, Apple Contacts import identifiers, Obsidian canonical notes, Calendar identities and communication-provider identities where technically appropriate.

### `relationships`

Structured operational relationship metadata only.

```text
id UUID PK
person_id FK -> people.id
relationship_type nullable
status nullable
started_on nullable
ended_on nullable
check_in_cadence_days nullable
created_at
updated_at
```

Do not create a numeric closeness/quality score by default. Add one only if a concrete useful workflow justifies it and the user approves the semantics.

### `person_facts`

Flexible structured facts with provenance.

```text
id UUID PK
person_id FK -> people.id
fact_key
value jsonb
source_kind
source_system nullable
source_ref nullable
asserted_at nullable
observed_at nullable
confidence nullable
sensitivity_class nullable
supersedes_id nullable
created_at
```

Prefer superseding historical facts when provenance/history matters instead of silently overwriting evidence.

### `interactions`

Minimal interaction/event metadata.

```text
id UUID PK
occurred_at
interaction_type
channel nullable
source_system nullable
source_ref nullable
summary nullable
created_at
```

### `interaction_people`

```text
interaction_id FK -> interactions.id
person_id FK -> people.id
role nullable
PRIMARY KEY(interaction_id, person_id)
```

Long narrative interaction notes belong in Obsidian. `summary` should stay concise and operationally useful.

### Action linkage

Do not create a parallel `relationship_followups` task table unless a real limitation in the existing action model is proven.

Preferred pattern:

```text
people/person relation
      |
      v
LLM4LIFE action (canonical follow-up)
      |
      +--> Google Tasks
      +--> Google Calendar only when scheduled
```

If relational querying becomes important, add a small `action_people` join rather than another task lifecycle.

### Contact points

A `person_contact_points` table may be added after Phase 1 ownership testing if Neon is confirmed as canonical for phone/email/address data.

Do not implement bidirectional contact-field synchronization before conflict policy and cutover semantics are explicit.

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

### Sensitive facts

Do not automatically persist inferred sensitive facts such as health status, religion, politics, sexuality, criminal history or similarly sensitive attributes merely because a message or model inference suggests them.

Prefer explicit user-provided facts and narrowly necessary operational metadata. When uncertain whether information deserves durable storage, do not persist it automatically.

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

## Import and dedup strategy

### Phase 0 — documentation

**Current phase.**

- architecture/ownership documented;
- old frontmatter-first-only recommendation superseded;
- no People tables created yet;
- no contact records migrated yet.

### Phase 1 — schema + read-only inventory

1. Design migration SQL and tests.
2. Inspect Google Contacts and available Apple Contacts export/supported access path.
3. Produce counts by source and normalized candidate identifiers.
4. Generate a duplicate-candidate report without modifying providers.
5. Decide contact-field authority after seeing real provider semantics.
6. Verify public repo contains no private contact payloads.

**Gate:** schema reviewed, migration test passes, inventory report is reproducible, no production mutations.

### Phase 2 — canonical identity import

1. Snapshot/export source contact sets where supported.
2. Import into Neon with stable `person_id` and external refs.
3. Re-run import and prove idempotency.
4. Resolve high-confidence duplicates automatically only under strict rules.
5. Route ambiguous merges to user review.
6. Preserve merge audit/rollback data.

**Gate:** source counts reconciled, zero orphan refs, rerun creates zero unintended duplicates.

### Phase 3 — address-book projection cutover

1. Choose/verify field authority.
2. Project canonical address-book state to Google Contacts.
3. Verify Apple device consumption/sync path.
4. Run reconciliation in both directions during a bounded migration window if required.
5. Stop maintaining independent Apple/Google truths.

**Gate:** sampled contacts match canonical state, create/update/delete semantics verified, rollback tested.

### Phase 4 — Obsidian linkage + conversational capture

1. Map canonical person IDs to Obsidian person notes without moving narrative into Neon.
2. Preserve existing notes and links.
3. Add safe local-vault write path when available.
4. Implement classification/person resolution for conversational capture.
5. Add fact/interaction provenance.

### Phase 5 — relationship automation

Only after data quality is proven:

- due follow-ups;
- promised follow-up detection where evidence is explicit;
- birthdays/important-date preparation;
- optional “haven't interacted recently” suggestions;
- interaction-derived `last_interaction`;
- lightweight reconnection recommendations.

These should start conservative and notification-light. Do not optimize relationships into a gamified score.

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

Before a People cutover, tests should cover at minimum:

- external-ref uniqueness;
- idempotent import rerun;
- same-name different-person case;
- renamed contact same-person case;
- multiple emails/phones;
- provider record deleted/archived;
- ambiguous merge remains unmerged;
- merge rollback/audit;
- Obsidian link without narrative duplication;
- follow-up creates/links an LLM4LIFE action rather than duplicate task state;
- sensitive inference is not silently persisted;
- projection retry does not duplicate provider objects.

## Agent development contract

Future coding agents generally work best when the task gives them a narrow source of truth, explicit invariants and observable acceptance criteria. For this subsystem:

### Before coding

- restate the current phase;
- list files/tables you expect to touch;
- identify destructive or irreversible operations;
- inspect existing migrations/tests rather than guessing;
- verify connector/API capabilities before designing around them.

### While coding

- make small cohesive changes;
- prefer migrations/scripts that are safe to rerun or have explicit rollback;
- include deterministic tests for identity/dedup logic;
- add structured logs/receipts for background work;
- never place secrets or private person data in fixtures committed to this public repo;
- use synthetic fixtures.

### Before declaring completion

Report:

- commit/PR or migration identifiers;
- tests/CI run results;
- before/after counts when data changed;
- what is deployed vs merely committed;
- remaining known risks;
- exact rollback path;
- next recommended step.

Do not say “done” when only target code or documentation exists.

## Fixed decisions vs open design space

### Accepted defaults

- Neon will own stable internal person identity and structured People machine state.
- Obsidian remains the narrative relationship-memory system.
- Google Contacts becomes the preferred address-book projection/client after dedup and verified cutover.
- Apple Contacts should become a synchronized device client rather than an independent truth.
- relationship follow-ups use the existing personal action system;
- Calendar owns scheduled interactions;
- provenance and conservative dedup are required;
- raw conversation archival is not the default.

### Explicitly open for future recommendations

Future agents should challenge these when evidence supports a materially better design:

- exact contact-field authority between Neon and Google Contacts after real API testing;
- whether People tables should stay in the existing `llm4life` schema or move to a dedicated private schema/database;
- exact fact taxonomy and sensitivity classes;
- whether interaction summaries belong in Neon or only references are sufficient;
- best supported Apple Contacts import/sync path;
- whether a local Obsidian bridge or another supported interface provides the best write path;
- how much relationship automation is useful before it becomes noisy;
- whether additional entity types such as organizations/households deserve first-class models later.

A future agent may recommend changing an accepted default. It must explain the concrete benefit, costs, data migration, rollback, security impact and how the proposal avoids duplicate truth.

## Anti-patterns

Do not:

- create `people_v2_final_final` style replacement stores instead of migrating deliberately;
- use names as foreign keys;
- automatically merge on fuzzy-name similarity;
- write the same relationship narrative to Neon, Obsidian and Google Contacts notes;
- create recurring “keep in touch” tasks for everyone without user-value evidence;
- infer private facts from silence/message tone and store them as truth;
- add a paid CRM merely because it has a polished UI;
- introduce long-term bidirectional dual-write without explicit conflict resolution;
- delete legacy Apple/Google/Obsidian state before reconciliation and rollback are verified.

## Definition of subsystem success

People/Relationships is successful when:

1. one real person resolves to one stable internal identity across systems;
2. contact projections can be rebuilt/reconciled from deliberate canonical state;
3. narrative context remains readable and private in Obsidian;
4. structured facts have source/provenance;
5. imports and retries are idempotent;
6. relationship follow-ups use the existing action engine;
7. scheduled interactions use Calendar without becoming relationship truth;
8. the system can answer useful relationship questions without storing conversational exhaust;
9. future agents can determine current phase, owner, invariants, tests and rollback without relying on chat history.
