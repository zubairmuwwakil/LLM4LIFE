# Diary-reviewed People data → Neon

**Phase:** People Phase 4  
**Purpose:** safely import already-reviewed, non-sensitive diary-derived People facts and interactions into Neon without copying narrative or note paths.

## Preconditions

The input must already have passed the private diary review pipeline:

```text
.private/people/diary_fact_plan.json
```

The plan remains `apply_allowed: false`. That field is intentional: validation alone never authorizes a write.

The production schema must also include migration `005_person_facts_asserted_on.sql`, which adds nullable date-only provenance:

```sql
llm4life.person_facts.asserted_on date
```

This avoids inventing timestamps for diary evidence that only has a calendar date.

## Dry run

Dry run is the default:

```bash
python3 scripts/import_people_diary_plan.py
```

The importer checks:

- every target `person_id` is active;
- the `obsidian` system registry row exists;
- `person_facts.asserted_on` is live;
- deterministic fact IDs are not already present;
- deterministic interaction keys are not already present;
- same-person / same-date / same-fact-key collisions do not disagree;
- same-people / same-date / same-interaction-type collisions do not disagree;
- every proposal is `standard`, never `sensitive`;
- source kinds remain `user_edited_import` or `interaction_import`;
- source note paths and diary prose are never written to Neon.

Default receipt:

```text
.private/people/diary_neon_import_receipt.json
```

The receipt is aggregate-only and contains no names, person IDs, note paths, diary prose, or fact values.

## Idempotency

Facts use deterministic UUIDv5 IDs derived from:

- source content SHA-256;
- source date;
- person ID;
- fact key;
- canonical fact value.

Interactions use deterministic UUIDv5 IDs and a stable `interaction_key` derived from:

- source content SHA-256;
- occurred date;
- interaction type;
- sorted participant IDs;
- reviewed summary.

Moving or renaming an Obsidian note therefore does not duplicate imported data because note paths are not part of the identity.

## Conflicts

The importer never overwrites conflicting durable People data.

A fact conflicts when the same person, fact key, and asserted date already exist with a different value.

An interaction conflicts when the same participant set, date, and interaction type already exist with a different summary.

Any conflict blocks the whole apply attempt.

## Apply gate

A write requires both explicit CLI flags:

```bash
python3 scripts/import_people_diary_plan.py --apply --user-authorized
```

`--apply` without `--user-authorized` is refused.

The flag records that a separate explicit authorization occurred after plan review; it does not make validation itself an authorization.

## Sensitive data

This importer refuses `sensitive` proposals entirely, even if the user-authorized flag is supplied. Sensitive diary-derived data requires a separate reviewed persistence path rather than being mixed into routine People imports.

## Neon write shape

Facts write only structured fields:

- deterministic `id`;
- `person_id`;
- `fact_key`;
- structured `value`;
- `source_kind = user_edited_import`;
- `source_system_id = obsidian`;
- date-only `asserted_on`;
- confidence;
- sensitivity class (`standard` only here).

Interactions write:

- deterministic `id` and `interaction_key`;
- `occurred_on`;
- interaction type;
- reviewed short summary;
- `source_kind = interaction_import`;
- `source_system_id = obsidian`;
- participant links in `interaction_people`.

Raw diary narrative remains exclusively in Obsidian/private review artifacts.
