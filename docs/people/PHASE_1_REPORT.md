# People / Relationships Phase 1 Report

**Date:** 2026-09-04  
**Status:** Phase 1 implementation proposal validated on a disposable Neon branch; **not applied to production**.  
**Privacy:** This report contains no real names, contact fields, provider IDs, birthdays, relationship notes, or message content.

## Executive decision

Do **not** create a persistent `person_external_refs` table.

Reuse and generalize the existing `llm4life.external_refs` table. It is already the cross-domain primitive used by actions and provider projections, so a People-only table would duplicate identity, idempotency, lifecycle, and reconciliation semantics.

People exposed one real generic gap: provider object IDs need an explicit account scope. Migration `004_people.sql` therefore adds `account_scope`, `first_seen_at`, `last_seen_at`, and `archived_at` to the generic reference table and changes external-ID uniqueness to:

```text
(system_id, account_scope, internal_type, external_id)
```

### Tradeoff

The generic table is polymorphic, so `internal_id` cannot have a normal foreign key to every possible internal object type. For People, import/reconciliation validation must therefore reject orphan `internal_type='person'` refs. Creating a second table solely to regain that FK is not worth splitting the established reference abstraction.

## Proposed minimum schema

`004_people.sql` adds:

- `people` — stable UUID identity, archive/merge lineage; display name is nullable because a provider record can be phone/email-only.
- `relationships` — one small operational relationship-state row per person; narrative stays in Obsidian.
- `person_facts` — structured facts with provenance, confidence, sensitivity class, and linear supersession.
- `interactions` — minimal metadata with both required `occurred_on` and optional `occurred_at`, so date-only history does not invent a time.
- `interaction_people` — many-person interaction linkage.
- `action_people` — relational linkage to the existing canonical action lifecycle; no second relationship-follow-up backend.

Intentionally omitted:

- `person_external_refs` storage table — replaced by generic `external_refs`.
- `person_contact_points` — deferred until field-authority testing justifies a canonical/derived copy.
- CRM scoring, raw message archives, or a second task/calendar lifecycle.

Merge lineage is represented by preserving the source person as `status='merged'` with `merged_into_person_id`. Phase 2 merge operations should additionally emit the existing durable event/action-receipt audit so moved refs can be reversed; no separate merge-history subsystem is needed yet.

## Validation receipts

### Production read-only inspection

Production Neon was inspected read-only before schema design.

- No People tables exist in production.
- `llm4life.external_refs` is live and already used across Google Calendar, Google Tasks, and Notion mappings.
- 95 existing external refs were present at validation time.
- Production contains one ad-hoc Google Calendar uniqueness index not represented by migrations `001-003`; `004_people.sql` removes that redundant index in favor of the generic account-scoped uniqueness rule.

### Disposable Neon branch

The proposed migration was applied only to a temporary Neon branch.

Synthetic SQL validation passed for:

- same display name, different people;
- exact provider-ref rerun idempotency;
- same provider ref cannot map to two people in the same account;
- identical external IDs can exist independently in different provider account scopes;
- renamed contact retains the same person/provider identity;
- archived provider record remains preserved without implicitly archiving the person;
- fact provenance and one-successor supersession;
- sensitive model-suggested facts cannot be persisted as `sensitive`;
- multi-person interaction linkage;
- `action_people` rerun idempotency;
- People/action linkage creates no Google Task or Calendar ref as a side effect.

After test cleanup the branch contained zero People/fact/interaction rows, while all 95 pre-existing external refs remained.

### Dedup engine

`scripts/people_dedup.py` is read-only and dry-run by design. Its unit tests use synthetic data only.

Rules:

1. Exact existing provider ref resolves identity before field matching.
2. Exact strong contact points generate candidates, not destructive merges.
3. Email + strong phone, or a strong contact point plus same normalized name, is `high` confidence but still **not auto-merged in Phase 1**.
4. A single strong signal without support is `conflict` for review.
5. A strong signal with conflicting names is `conflict`.
6. Name-only matches are weak and only emitted when explicitly requested; they are never auto-mergeable.
7. Candidate IDs and pair ordering are deterministic across reruns/input order.
8. Email normalization intentionally does not assume Gmail-style dot/plus aliases.
9. Phone normalization is conservative; ambiguous local numbers are not strong signals.

## Google Contacts findings

The connected Google Contacts surface was verified against the authenticated account and a safe read-only sample. Representative saved contacts expose the expected resource ID and fields such as names, email, phones, addresses, birthdays, organizations, and photos.

The current ChatGPT connector is **not sufficient for a complete reconciliation inventory**:

- search is query-oriented rather than an enumerate-all operation;
- result count is capped by the connector;
- search can return both saved `people/...` contacts and `otherContacts/...` records;
- the connector's `read_contact` path successfully reads saved contacts but failed for an `otherContacts/...` search result.

For complete inventory, use the supported Google People API directly rather than pretending query search is exhaustive. `people.connections.list` supports full pagination, field masks, total counts, sync tokens, and deleted-resource markers. `people.updateContact` uses source ETags to detect write conflicts and recommends sequential mutations for one user.

Official references:

- https://developers.google.com/people/api/rest/v1/people.connections/list
- https://developers.google.com/people/api/rest/v1/people/updateContact
- https://developers.google.com/people/api/rest/v1/otherContacts/list

`Other Contacts` should be treated as evidence/candidates, not silently promoted into the canonical address book. They can include auto-collected correspondents rather than intentionally saved contacts.

## Apple Contacts findings

### Phase 1 inventory recommendation

Use a local vCard export as the first read-only inventory source, process it privately/transiently, and do not commit the export or normalized rows.

Apple supports exporting contacts as vCard from Contacts/iCloud. This is deterministic, free, user-controlled, and requires no new background service or credentials.

Official references:

- https://support.apple.com/en-ca/guide/icloud/mmfba748b2/icloud
- https://support.apple.com/en-us/108306

### Eventual runtime architecture

Use a small trusted macOS bridge built on `CNContactStore`, not UI automation. Apple documents supported contact enumeration, containers/groups, change-history tokens, save requests, and change notifications.

Important identity rule: `CNContact.identifier` is unique only on the current device. It can be persisted between app launches, but it must **not** become the cross-device canonical person ID. Store Apple refs with device/container account scope and keep Neon `person_id` canonical.

For reconciliation, inspect both:

- unified contacts for the human-visible view; and
- `CNContactFetchRequest.unifyResults = false` when source-linked records must remain distinguishable.

Official references:

- https://developer.apple.com/documentation/contacts/cncontactstore
- https://developer.apple.com/documentation/contacts/cncontact/identifier
- https://developer.apple.com/documentation/contacts/cncontactfetchrequest/unifyresults

## Recommended contact-field authority

**Recommendation for Phase 2/3 approval:**

```text
Neon
  stable person_id
  provider refs
  relationship state
  facts/provenance
  interaction metadata

Google Contacts
  canonical mutable address-book fields
  name / phone / email / postal address / birthday / organization

Apple Contacts
  synchronized device client after reconciliation

Obsidian
  narrative context
```

This differs from the prior default recommendation that Neon become canonical for phone/email/address/birthday.

Why Google field authority is better after the Phase 1 evidence:

- Google already provides the intended human address-book UI.
- The supported People API has full enumeration, incremental change sync, deletion markers, field masks, and ETag conflict detection.
- Keeping mutable contact fields authoritative at the provider avoids a hard bidirectional conflict problem when the user edits contacts directly.
- It minimizes duplicated private contact payloads in Neon.
- Neon can still resolve identity deterministically through provider refs and, only if later required, a derived minimal normalized matching index.

This is a **recommendation, not a production ownership change**. Do not update canonical ownership configuration or begin write-back until the Phase 2/3 cutover is explicitly approved and tested.

## Privacy/security assessment

- Public repository: schemas, algorithms, synthetic fixtures, and capability findings only.
- Raw Apple/Google exports: private and transient.
- Actual provider IDs/account scopes: private runtime state.
- No full conversation archival by default.
- Provider contact notes should not become a second copy of Obsidian relationship narrative.
- Sensitive model inference must not become durable truth; schema includes a guard against persisting model-suggested sensitive facts as sensitive records.
- Direct Google People API inventory would require an authorized read scope; do not create new credentials/permissions without approval.
- A future macOS Contacts bridge requires Contacts permission; do not request it until implementation/cutover work is approved.

## Exact Phase 2 migration plan

1. Obtain complete read-only snapshots:
   - Google saved contacts via `people.connections.list` pagination;
   - Google `Other Contacts` separately as evidence only;
   - Apple/iCloud vCard export processed locally.
2. Store raw snapshots outside the public repo and record only inventory counts/fingerprints in receipts.
3. Run deterministic normalization and duplicate-candidate generation.
4. Review all ambiguous/conflict candidates; never merge on name alone.
5. Apply `004_people.sql` to production **only after explicit approval**.
6. Import stable `people` rows plus generic `external_refs` in a transaction with deterministic import keys.
7. Re-run the same import and require zero unintended new people/refs.
8. For approved merges:
   - keep the losing person row as `merged`;
   - move refs transactionally;
   - emit a reversible durable receipt/event containing the before/after mapping;
   - never delete the source person as part of the merge.
9. Reconcile counts and require zero orphan person refs.
10. Before Google write-back, test create/update/delete/ETag conflict behavior on a bounded non-production/synthetic contact set.
11. Only then cut mutable contact-field authority to Google and verify Apple consumption/sync.
12. Link Obsidian notes to stable `person_id` later without moving narrative into Neon.

## Current blockers / approval gates

Safe Phase 1 engineering is complete as far as current authorized interfaces allow, but a **complete real contact inventory has not been performed** because:

- the current Google Contacts connector cannot enumerate the entire saved/other-contact corpus reliably;
- direct Google People API scope/credentials have not been created;
- no private Apple/iCloud vCard export is available in this runtime.

Stop before all of the following unless explicitly approved:

- apply `004_people.sql` to production Neon;
- import, merge, modify, or delete real contacts;
- change Google/Apple contact ownership in production;
- destructively clean Obsidian People material;
- create new OAuth credentials/scopes or local Contacts permissions.
