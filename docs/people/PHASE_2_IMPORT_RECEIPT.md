# People Phase 2 Production Import Receipt

**Date:** 2026-09-04  
**Status:** Google-backed canonical People identity import is live in production Neon. Apple-to-Google field migration is still pending.  
**Privacy:** This receipt intentionally contains aggregate counts only. It contains no names, emails, phone numbers, addresses, birthdays, provider resource IDs, raw export rows, OAuth material, or relationship narrative.

## Production result

The supported Google People API enumeration produced a complete saved-contact snapshot with stable provider resource names. The production import then created canonical Neon People identities and account-scoped Google external references without copying provider-owned contact values into Neon.

Verified production state:

- 753 Google saved contacts enumerated with provider-stable resource names;
- 33 clear non-person/service records held out from the People domain;
- 720 Google person external references imported;
- 716 active canonical People identities;
- 3 clean duplicate clusters collapsed, covering 7 source references;
- 0 orphan Google person references;
- 0 non-active People rows after the canonical import;
- 0 email, phone, address, birthday, or note values copied into Neon external-reference metadata;
- every imported provider reference has the expected privacy-minimized metadata shape;
- exact selected provider-ID coverage matched the private source snapshot;
- idempotent upsert behavior was verified after production import.

A Neon snapshot was created immediately before the production import for rollback safety.

## Data ownership after this step

- **Neon** owns stable internal `person_id`, provider-reference linkage, and structured relationship machine state.
- **Google Contacts** remains the intended mutable authority for standard address-book fields after full cutover.
- **Apple Contacts** remains a migration source and future synchronized device client until Apple-only data is reconciled and projected into Google.
- **Obsidian** remains the narrative relationship-context store.

Contact values such as emails, phone numbers, addresses and birthdays are not duplicated into Neon by this import. Google provider resource names are the durable external identity references; export-row hashes are not provider refs.

## Merge policy used

Only the previously reviewed deterministic clean duplicate clusters were collapsed. Ambiguous, conflicting and weak-name candidates were not automatically merged. The production import pre-collapsed the approved clusters to shared canonical IDs rather than creating historical merged rows.

## Provider mutations

This production step mutated Neon only. It did not create, update, merge or delete Google Contacts records. Provider contact deletion remains unauthorized.

## Remaining Phase 2 work

1. Reconcile the private Apple/iCloud corpus against the now-live Google stable-reference corpus.
2. Build a deterministic non-destructive Apple-to-Google projection plan.
3. Preserve Apple-only contact points, photos, titles, custom dates, social profiles and appropriate contact notes.
4. Create/update Google contacts only where the approved migration plan requires it.
5. Capture stable Google resource names for newly created Apple-only contacts and add those provider refs to Neon idempotently.
6. Verify preservation and then complete the Google field-authority / Apple-client cutover.

No destructive contact cleanup is part of this remaining work.
