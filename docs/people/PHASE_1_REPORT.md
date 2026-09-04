# People / Relationships Phase 1 Report

**Date:** 2026-09-04  
**Status:** Phase 1 implementation proposal validated on a disposable Neon branch; **not applied to production**.  
**Privacy:** No real names, contact fields, provider IDs, birthdays, relationship notes, or message content are recorded here.

## Executive decision: reuse `external_refs`

Do **not** create a persistent `person_external_refs` table.

Reuse and generalize `llm4life.external_refs`. It is already the cross-domain primitive for provider projections, so a People-only reference table would duplicate idempotency, lifecycle, and reconciliation semantics.

People exposed one real generic gap: provider IDs need explicit account scope. `004_people.sql` adds `account_scope`, `first_seen_at`, `last_seen_at`, and `archived_at`, and changes external-ID uniqueness to:

```text
(system_id, account_scope, internal_type, external_id)
```

Tradeoff: the generic table is polymorphic, so `internal_id` cannot have a normal FK to every internal object table. People import/reconciliation code must therefore reject orphan `internal_type='person'` refs. Splitting the model solely to regain that FK is not worth fragmenting the established abstraction.

## Proposed minimum schema

`004_people.sql` adds:

- `people` — stable UUID identity plus archive/merge lineage. `display_name` is nullable because provider records can be phone/email-only.
- `relationships` — one small operational relationship-state row per person; narrative stays in Obsidian.
- `person_facts` — structured facts with provenance, confidence, sensitivity class, and one-successor supersession.
- `interactions` — minimal interaction metadata; required `occurred_on` plus optional `occurred_at` prevents invented times.
- `interaction_people` — multi-person linkage.
- `action_people` — relation to the existing canonical action lifecycle; no second relationship-follow-up backend.

Intentionally omitted:

- `person_external_refs` storage table — generic `external_refs` is used instead.
- `person_contact_points` — deferred until field-authority testing proves a canonical/derived copy is justified.
- CRM scoring, raw message archives, or another task/calendar lifecycle.

Merge lineage keeps the losing person row as `status='merged'` with `merged_into_person_id`. Phase 2 merges should also emit the existing durable event/action-receipt audit so moved refs are reversible; no separate merge-history subsystem is needed yet.

## Validation receipts

### Production read-only inspection

- No People tables exist in production.
- `llm4life.external_refs` is live across Google Calendar, Google Tasks, and Notion mappings.
- 95 existing external refs were present at validation time.
- Production has one ad-hoc Google Calendar uniqueness index not represented in migrations `001-003`; the proposed migration removes it in favor of the generic account-scoped uniqueness rule.

### Disposable Neon branch

The proposed migration was applied only to a temporary Neon branch.

Synthetic SQL validation passed for:

- same name, different people;
- exact provider-ref rerun idempotency;
- same provider ref cannot map to two people in one account;
- identical external IDs can exist independently in different account scopes;
- renamed contact retains stable identity;
- archived provider record remains preserved without implicitly archiving the person;
- fact provenance and one-successor supersession;
- sensitive model-suggested facts cannot be stored as `sensitive`;
- multi-person interactions;
- `action_people` rerun idempotency;
- People/action linkage creates no Google Task or Calendar ref as a side effect.

After cleanup: zero People/fact/interaction rows and all 95 pre-existing external refs still present.

### Dedup engine

`scripts/people_dedup.py` is read-only and dry-run by design. Tests use synthetic data only.

Rules:

1. Exact provider ref resolves identity before field matching.
2. Strong contact-point matches generate candidates, not destructive merges.
3. Email + strong phone, or a strong contact point plus the same normalized name, is `high` confidence but still **not auto-merged in Phase 1**.
4. One strong signal without support is `conflict` for review.
5. A strong signal with conflicting names is `conflict`.
6. Name-only matches are weak, opt-in candidates and never auto-mergeable.
7. Candidate IDs and pair ordering are deterministic across reruns/input order.
8. Email normalization does not guess provider-specific aliases such as Gmail dot/plus equivalence.
9. Phone normalization is conservative; ambiguous local numbers are not strong signals.

## Google Contacts findings

A safe read-only sample was inspected through the connected Google Contacts surface. Saved contacts expose the expected resource ID and representative fields such as names, emails, phones, addresses, birthdays, organizations, and photos.

The current connector is **not sufficient for complete reconciliation inventory**:

- search is query-oriented, not enumerate-all;
- results are connector-limited;
- search can mix saved `people/...` contacts and `otherContacts/...` records;
- `read_contact` successfully reads saved contacts but failed on an `otherContacts/...` search result.

Use the supported People API for complete inventory instead. `people.connections.list` supports pagination, field masks, total counts, sync tokens, and deleted-resource markers. Full saved-contact inventory should request the contact source specifically, include `metadata`, and treat an expired sync token as a reason for another full sync. `people.updateContact` uses source ETags for conflict detection and recommends sequential mutations for the same user.

Official references:

- https://developers.google.com/people/api/rest/v1/people.connections/list
- https://developers.google.com/people/api/rest/v1/people/updateContact
- https://developers.google.com/people/api/rest/v1/otherContacts/list

Google `Other Contacts` are evidence/candidate input only; do not silently promote auto-collected correspondents into the intentional address book.

## Apple Contacts findings

### Phase 1 inventory

Use a local vCard export first, process it privately/transiently, and never commit the export or normalized rows. Apple supports vCard export from Contacts/iCloud; this is deterministic, free, user-controlled, and avoids adding a new background service or permission just for initial inventory.

Official references:

- https://support.apple.com/en-ca/guide/icloud/mmfba748b2/icloud
- https://support.apple.com/en-us/108306

### Eventual runtime bridge

Use a small trusted macOS bridge based on `CNContactStore`, not UI automation. The framework supports contact enumeration, containers/groups, change-history tokens, save requests, and store-change notifications.

`CNContact.identifier` is only unique on the current device. It may be persisted across app launches but must **not** become the cross-device canonical person ID. Apple refs therefore need device/container account scope while Neon `person_id` stays canonical.

During reconciliation inspect both the unified human-visible view and `CNContactFetchRequest.unifyResults = false` when individual linked source records must remain distinguishable.

Official references:

- https://developer.apple.com/documentation/contacts/cncontactstore
- https://developer.apple.com/documentation/contacts/cncontact/identifier
- https://developer.apple.com/documentation/contacts/cncontactfetchrequest/unifyresults

## Contact-field authority recommendation

Current **conditional recommendation** for Phase 2/3:

```text
Neon
  stable person_id
  provider refs
  relationship state
  facts/provenance
  interaction metadata

Google Contacts
  mutable address-book fields, if Apple inventory proves migration preserves them

Apple Contacts
  synchronized device client after reconciliation

Obsidian
  narrative context
```

This differs from the earlier default that Neon would own phone/email/address/birthday.

Why Google is currently the stronger candidate:

- it is already the intended human address-book UI;
- People API supports full enumeration, incremental sync, deletion markers, field masks, and ETag conflict handling;
- provider authority avoids a difficult bidirectional field-level conflict problem when the user edits contacts directly;
- it minimizes duplicated private contact payloads in Neon;
- Neon can still resolve identity through provider refs and add only a derived minimal contact-point index later if matching performance requires it.

**This is not permanently decided yet.** Before ownership changes, complete the Apple/iCloud inventory and verify all needed fields/records can be preserved in the Google-centered model. Then require explicit cutover approval.

## Privacy/security assessment

- Public repo: schemas, algorithms, synthetic fixtures, and non-personal capability findings only.
- Raw Google/Apple exports: private/transient.
- Real provider IDs/account scopes: private runtime state.
- No full conversation archival by default.
- Contact notes must not become a duplicate of Obsidian relationship narrative.
- Sensitive model inference must not become durable truth; schema adds a guard against persisting model-suggested sensitive facts as sensitive records.
- Direct People API inventory needs an authorized read scope; do not create credentials/scopes without approval.
- A future macOS Contacts bridge needs Contacts permission; do not request it until that work is approved.

## Exact Phase 2 plan

1. Obtain complete read-only snapshots:
   - Google saved contacts via `people.connections.list`, contact source only;
   - Google `Other Contacts` separately as evidence only;
   - Apple/iCloud vCard export processed locally.
2. Keep raw snapshots outside the public repo; record only counts/fingerprints in durable receipts.
3. Run deterministic normalization and candidate generation.
4. Review all ambiguous/conflict candidates; never merge by name alone.
5. Verify Apple fields/contacts can be preserved under the proposed Google-field-authority model; revise authority if evidence says otherwise.
6. Apply `004_people.sql` to production **only after explicit approval**.
7. Import `people` plus generic `external_refs` transactionally with deterministic import keys.
8. Re-run the same import and require zero unintended new people/refs.
9. For approved merges, keep the losing person row, move refs transactionally, and emit a reversible durable receipt/event containing before/after mappings.
10. Reconcile counts and require zero orphan person refs.
11. Before Google write-back, test create/update/delete/ETag conflict behavior on a bounded synthetic contact set.
12. Only then approve/cut mutable field authority and verify Apple sync.
13. Link Obsidian notes to stable `person_id` later without moving narrative into Neon.

## Current blockers / approval gates

Safe Phase 1 engineering is complete as far as currently authorized interfaces allow, but a **complete real contact inventory has not been performed** because:

- the current Google connector cannot exhaustively enumerate saved + other contacts;
- direct Google People API scope/credentials have not been created;
- no private Apple/iCloud vCard export is available in this runtime.

Stop before:

- applying `004_people.sql` to production Neon;
- importing, merging, modifying, or deleting real contacts;
- changing Google/Apple contact ownership in production;
- destructive Obsidian cleanup;
- creating new OAuth credentials/scopes or local Contacts permissions.
