# Decision: Google Contacts owns mutable standard address-book fields after People cutover

**Date:** 2026-09-04  
**Status:** Accepted target architecture; production field cutover not yet live  
**Supersedes where conflicting:** the conditional field-authority recommendation in the 2026-09-03 People subsystem decision and earlier Phase 1 documents.

## Context

The People schema is live in Neon, but real contacts remain fragmented between Google Contacts and Apple/iCloud Contacts.

Phase 1 completed a private, read-only export reconciliation:

- 753 Google saved contacts;
- 451 Apple/iCloud contacts;
- 239 clean one-to-one high-confidence cross-source duplicate candidates;
- no high-confidence one-to-many ambiguity;
- conflict and name-only candidates intentionally left unresolved;
- no real contact or Neon People mutation.

The inventory also showed Apple-only data that must be preserved before cutover, including additional phone values, notes, photos, job titles, custom dates and social-profile metadata.

## Decision

After cutover:

1. **Neon/PostgreSQL** owns stable `person_id`, account-scoped provider refs, structured relationship state, provenance-aware facts and interaction metadata.
2. **Google Contacts** owns mutable standard address-book fields: names/contact identity presentation, phone numbers, email addresses, postal addresses, birthdays, organization/job data, contact notes, URLs, labeled dates/events, relations and photos.
3. **Apple Contacts** becomes a synchronized Apple-device client rather than an independently maintained second mutable truth.
4. **Obsidian** continues to own long-form/narrative relationship context.
5. `person_contact_points` remains deferred; Neon does not duplicate all Google contact fields merely because it can.

This is a target-ownership decision only. No real Google/Apple field cutover is authorized by this document.

## Apple-specific preservation mapping

Before Apple stops being independent truth:

- contact photos -> Google contact-photo endpoint;
- job title/department/organization -> Google organization fields;
- labeled custom dates -> Google events;
- URL fields -> Google URLs;
- Apple social-profile fields -> Google URLs when a semantic URL can be represented, otherwise Google user-defined fields preserving service/identifier semantics;
- Apple notes -> classify as address-book note vs narrative relationship context; narrative context belongs in Obsidian rather than being duplicated into Google.

No Apple-only field is silently discarded during migration.

## Why Google rather than Neon for mutable contact fields

The real corpus does not justify maintaining a second copy of routine phone/email/address/birthday data in Neon.

Google People API already provides the provider semantics needed for mutable contacts, including field masks, contact updates, optimistic concurrency via ETags, supported list/sync behavior and a dedicated photo mutation endpoint.

Keeping standard mutable fields provider-authoritative reduces private-data duplication and avoids a long-term bidirectional Google↔Neon field synchronization problem.

Neon still provides the durable cross-system identity and relationship layer that Google Contacts cannot replace.

## Why Apple is not a second authority

The Apple corpus contains useful data and richer Apple-specific properties, but maintaining Apple and Google as independently editable truths would create conflict resolution and duplicate-sync complexity.

Apple's local Contacts framework remains useful for:

- obtaining device-scoped `CNContact.identifier` references during migration;
- validating that projected Google contacts appear correctly on Apple devices;
- preserving good native Apple UX after cutover.

Apple identifiers are external scoped references, not canonical identity.

## Phase 2 blocker discovered

The two exports are sufficient for reconciliation but not for canonical provider-ref import:

- Google CSV does not expose People API `people/...` resource names;
- the Apple vCard export contains no `UID` properties.

All export IDs are therefore snapshot-only. They must not be stored in `llm4life.external_refs`.

Before Phase 2, acquire stable Google People resource names through supported enumeration and scoped Apple `CNContact.identifier` values where needed.

## Invariants

- never use export row numbers or hashes as durable provider refs;
- never auto-merge on name similarity alone;
- ambiguous conflict/weak candidates remain separate until reviewed;
- do not drop Apple-specific fields during projection;
- do not create long-term bidirectional field-level dual truth;
- do not copy narrative relationship notes into Google merely to centralize them;
- preserve rollback until Google projection and Apple-device synchronization are verified.

## Consequences

### Positive

- one mutable address-book field owner;
- less private-data duplication in Neon;
- standard provider sync/conflict semantics;
- Apple devices retain native Contacts UX;
- Neon remains focused on identity/relationships rather than becoming a contact-store clone.

### Costs / risks

- Apple-specific social-profile metadata needs explicit conversion;
- photos and Apple-only fields must be migrated before cutover;
- stable provider refs require a stronger API/local enumeration path than the exports provide;
- Google provider availability becomes relevant to contact-field mutations.

These are acceptable because migration remains phased, reversible and approval-gated.

## Next gate

Do not start real canonical import until stable provider refs can be acquired and the user separately approves real People/provider-ref writes.
