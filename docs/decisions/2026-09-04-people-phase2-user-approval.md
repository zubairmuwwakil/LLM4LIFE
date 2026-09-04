# Decision: Phase 2 real People import, conservative merge, and non-destructive contact edits are approved

**Date:** 2026-09-04  
**Status:** User-approved execution scope; technically blocked on stable provider-reference/write path

## Approval

The user explicitly approved:

1. importing real People records;
2. merging duplicate identities conservatively;
3. editing contact records as part of the migration.

This removes the prior policy gate for those actions.

## What this approval does not change

Approval does not weaken identity-safety requirements. Canonical import still requires stable provider references. Export row hashes, CSV row numbers, and other snapshot-only identifiers must never be stored as durable `llm4life.external_refs`.

Conflict candidates and name-only candidates remain manual-review items. Only clean one-to-one high-confidence matches may be merged automatically.

This approval also does not authorize provider-contact deletion, destructive Obsidian cleanup, or new credentials/OAuth/macOS permissions unless separately approved.

## Current technical blocker

The installed Google Contacts connector currently exposes targeted profile/search/read operations, but no complete saved-contact enumeration or contact write operations.

The completed exports also contain no stable provider identifiers:

- Google CSV: no `people/...` resource names;
- Apple/iCloud vCard: no stable UID fields.

Therefore production People import must remain paused until a supported provider-ID path exists. Importing now would create identities that cannot be safely re-resolved or updated idempotently.

## Execution once the blocker is removed

1. Enumerate Google saved contacts with stable `people/...` resource names.
2. Obtain scoped Apple identifiers where needed for migration receipts.
3. Attach stable refs to the private reconciliation corpus.
4. Import canonical `llm4life.people` + generic external refs transactionally and idempotently.
5. Auto-merge only the already-proven clean one-to-one high-confidence set.
6. Keep conflict/name-only candidates unresolved pending review.
7. Apply approved non-destructive contact edits to preserve/centralize mutable fields in Google Contacts.
8. Verify rerun idempotency, zero orphan refs, counts, rollback, and Apple-device synchronization.

## Invariants

- stable refs before canonical import;
- no fuzzy/name-only automatic merge;
- no silent field loss;
- no provider deletion without separate approval;
- no long-term Apple/Google dual mutable truth;
- no private contact payloads in the public repository.
