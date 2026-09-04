# People / Relationships Phase 1 Report

**Date:** 2026-09-04  
**Status:** Phase 1 schema and read-only Apple/Google inventory/reconciliation are complete. Stable provider-reference acquisition is still required before Phase 2 canonical import.  
**Privacy:** No real names, contact fields, provider IDs, birthdays, relationship notes, or message content are recorded here.

## Executive decision

- Reuse `llm4life.external_refs`; do not create `person_external_refs`.
- `004_people.sql` is deployed to production.
- People schema remains empty: 0 People rows, 0 facts, 0 interactions immediately after deployment.
- All 95 pre-existing external refs were preserved.
- Real private exports were reconciled read-only: 753 Google saved contacts + 451 Apple/iCloud contacts.
- 239 cross-source pairs are clean one-to-one high-confidence duplicate candidates; no high-confidence one-to-many ambiguity exists.
- Ambiguous/conflicting/name-only candidates remain unresolved by design; no automatic merge occurred.
- Mutable standard address-book field authority is now an **accepted target** for Google Contacts after cutover. Neon remains the authority for stable person identity, provider refs and structured relationship state. Apple becomes the synchronized device client.
- No real contacts were imported, merged, modified, or deleted.

## External reference model

People uses the generic `llm4life.external_refs` table. Provider refs are account-scoped and lifecycle-aware.

The export inventory exposed an important Phase 2 blocker: neither source export contains stable provider IDs suitable for canonical external references.

- Google CSV provides no People API `people/...` resource name.
- The supplied Apple/iCloud vCard contains no `UID` properties.

All 1,204 normalized export records therefore have snapshot-only IDs. These IDs are useful for deterministic reconciliation but **must never be persisted as provider refs**.

Before Phase 2 import, obtain stable Google People resource names through a supported People API enumeration path and scoped Apple `CNContact.identifier` values when Apple migration receipts require them.

## Production schema

Live tables:

- `people`
- `relationships`
- `person_facts`
- `interactions`
- `interaction_people`
- `action_people`

Intentionally deferred:

- `person_contact_points`
- real contact imports/merges
- provider write/cutover
- automatic relationship capture/automation

## Private inventory receipt

Only aggregate counts are recorded publicly.

| Metric | Google | Apple/iCloud |
|---|---:|---:|
| Source records | 753 | 451 |
| With name | 747 | 450 |
| With email | 118 | 93 |
| With phone | 714 | 354 |
| With address | 75 | 46 |
| With birthday | 55 | 94 |
| With organization | 100 | 90 |
| With notes | 74 | 31 |
| Stable export/provider IDs | 0 | 0 |

Combined source records: **1,204**.

### Duplicate candidates

The deterministic candidate engine produced:

- **239 high-confidence** candidates;
- **33 conflict** candidates;
- **32 weak name-only** candidates.

All 239 high-confidence candidates are cross-source Google↔Apple one-to-one pairs. There are **0 high-confidence one-to-many** cases.

If only those 239 clean pairs are treated as the same identity, the provisional distinct-person count is **965**. Conflict and weak candidates remain separate until reviewed; this number is not a final canonical People count.

Cross-source Apple coverage:

- 239 high-confidence matches;
- 11 conflict candidates;
- 18 weak name-only candidates;
- 183 contacts with no Google candidate.

No candidate is auto-mergeable in Phase 1.

## Parser correction discovered during real inventory

Apple vCard 3.0 commonly uses grouped properties such as `item1.EMAIL`, `item1.TEL` and `item1.ADR`. The first inventory parser matched only bare property names and would have undercounted Apple email/address fields.

The parser was corrected to strip group prefixes before property classification, and a synthetic regression test was added. The corrected run is the source of all counts in this report.

## Field-preservation findings

The high-confidence overlap shows that Google already contains most shared core data, but Apple has additional values that must be preserved before cutover.

Within the 239 clean high-confidence pairs, Apple contributes additional data including:

- 15 additional strong phone values across 11 pairs;
- 1 Apple-only email value;
- 1 Apple-only address;
- 1 Apple-only organization value;
- 10 Apple-only contact-note records;
- 28 contacts with an Apple photo while the Google match has no photo;
- 8 matched contacts with Apple social-profile data and no Google website field.

Across the full Apple export, notable field classes include:

- 115 contacts with photos;
- 94 with birthdays;
- 90 with organizations;
- 46 with addresses;
- 35 with job titles;
- 31 with notes;
- 14 contacts containing social-profile fields (18 profile entries total);
- 5 contacts containing custom labeled dates;
- 2 contacts containing URL fields;
- 1 contact containing a nickname.

These findings mean current Google data alone is not sufficient for cutover; Apple fields must be merged/projected first.

## Contact-field authority decision

After the real inventory, the target field authority is:

```text
Neon
  stable person_id
  provider refs
  relationship state
  facts/provenance
  interaction metadata

Google Contacts
  mutable standard address-book fields after cutover

Apple Contacts
  synchronized device client after cutover

Obsidian
  narrative relationship context
```

Google People API supports the standard field classes needed for the corpus, including addresses, biographies/notes, birthdays, email addresses, events, organizations, phone numbers, relations, URLs and user-defined fields; contact photos are handled by the dedicated photo endpoint.

Apple-specific migration mapping:

- Apple photos → Google contact photo endpoint;
- job title/department/organization → Google organizations;
- labeled custom dates → Google events;
- URLs → Google URLs;
- social profiles → Google URLs where a semantic URL can be represented, otherwise a user-defined field preserving service/identifier semantics;
- Apple notes → classify as address-book note vs relationship narrative before projection; narrative belongs in Obsidian rather than being duplicated into Google.

`person_contact_points` remains deferred. The inventory does not justify duplicating all phone/email/address/birthday values into Neon merely for storage.

## Google Contacts findings

The connected ChatGPT connector remains useful for targeted lookup but is not a complete enumeration API. The export solved the count/field-preservation inventory problem, but Phase 2 still needs stable People API resource names for external refs and reliable reruns.

Use the supported Google People API connection enumeration path for stable `people/...` resource names before canonical import.

## Apple Contacts findings

The private vCard export is sufficient for read-only corpus reconciliation but contains no stable UID values. For provider-scoped migration references, use a trusted local macOS Contacts bridge with `CNContactStore`/`CNContact.identifier`; treat those identifiers as device/account scoped, never canonical identity.

## Privacy/security

- Public repo contains aggregate receipts, schemas, algorithms and synthetic fixtures only.
- Raw/normalized exports stay private/transient.
- Real contact/candidate details are not committed.
- No full conversation archival by default.
- Sensitive model inference does not become durable truth automatically.
- New People API scopes or macOS Contacts permissions remain approval-gated.

## Phase 1 conclusion

The **read-only inventory/reconciliation gate is complete**:

- complete Google saved-contact export processed;
- complete Apple/iCloud export processed;
- normalization is reproducible;
- deterministic duplicate candidates generated;
- ambiguous candidates remain unresolved rather than guessed;
- field-preservation risks identified;
- target mutable contact-field authority selected;
- no provider or Neon contact mutation occurred.

Phase 2 canonical import is **not yet authorized or technically ready** because stable provider references are still missing from the export data.

## Next plan

1. Acquire stable Google People `people/...` resource names through supported enumeration.
2. Acquire scoped Apple `CNContact.identifier` values if needed for migration receipts/linkage.
3. Join those stable refs to the already-reconciled private corpus without relying on display names alone.
4. Obtain explicit approval before writing real `people`/external-ref rows.
5. Import canonical identity + refs idempotently; keep conflict/weak candidates separate.
6. Prove rerun idempotency, zero orphan refs and reversible merge lineage.
7. Test bounded synthetic Google create/update/photo/ETag behavior before the real address-book field cutover.
8. Preserve Apple-specific fields before retiring Apple as independent truth.

## Remaining approval gates

Stop before:

- importing real People/provider refs into Neon;
- merging, modifying, deleting or creating real Google/Apple contacts;
- changing Google/Apple field ownership in production;
- destructive Obsidian cleanup;
- creating new OAuth credentials/scopes or local Contacts permissions.
