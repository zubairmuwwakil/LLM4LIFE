# Apple → Google Contacts Phase 2 Migration

**Status:** provider apply complete; refreshed Google stable-ID snapshot verified; new person-like refs imported to Neon; Apple-device sync verification remains before field-authority declaration.  
**Privacy:** real vCards, plans, receipts, names, contact values and Google resource names stay under `.private/people/` and must never be committed.

## Goal

Converge mutable standard address-book fields into Google Contacts while preserving Neon as the stable Person identity authority and Apple Contacts as a synchronized device client after cutover.

The migration is intentionally non-destructive. Provider-contact deletion is not authorized and the migration helper implements no delete endpoint.

## Reconciliation baseline

The complete private Apple export was compared with the complete stable-ID Google saved-contact snapshot using the conservative People identity rules:

- 451 Apple contacts;
- 753 Google saved contacts before provider apply;
- 246 clean one-to-one high-confidence matches eligible for additive update;
- 181 Apple-only contacts eligible for Google create;
- 12 identity conflicts held;
- 11 name-only weak matches held;
- 1 empty export record held;
- 31 Apple notes held for separate classification;
- 115 Apple photos detected.

Only aggregate counts are recorded publicly.

## Completed provider apply

The approved non-destructive migration was executed through `scripts/run_apple_google_phase2.sh --apply`.

Verified post-apply state:

- 934 Google saved contacts;
- 934 unique provider-stable `people/...` IDs;
- all 753 original Google provider IDs preserved;
- exactly 181 new Google contacts created from Apple-only records;
- temporary migration idempotency markers cleaned after durable receipt success;
- no provider contact deletion performed.

The first live apply encountered a transient Google `createContact` HTTP 502. The migration was hardened before resuming so an ambiguous server failure cannot cause a blind duplicate create. New creates use deterministic temporary markers, retryable failures are reconciled before a second POST, and non-retryable 4xx failures are not retried.

## Post-apply Neon reconciliation

The 181 newly-created Google contacts were reviewed against the People-domain boundary:

- 169 person-like Google refs imported to Neon idempotently;
- 12 obvious service/sample contacts retained in Google but kept provider-only;
- production Neon now contains 885 active People and 889 Google person refs;
- zero orphan Google person refs;
- zero non-active People introduced by the import;
- zero phone/email/address/birthday/note values copied into Neon ref metadata;
- exact new-ref set verified and idempotent rerun verified.

Google Contacts remains the provider for mutable address-book values. Neon stores stable person identity and provider references, not a duplicate contact-value database.

## Safety invariants

`scripts/apple_google_phase2.py` and the resilient apply wrapper enforce:

1. High-confidence matches must form a one-to-one graph or planning aborts.
2. Conflicts and name-only matches are never written automatically.
3. Existing Google names are never overwritten.
4. Every existing-contact update starts with a fresh Google People `GET` restricted to the contact source.
5. Email, phone, URL, event, nickname and preserved social-profile values are unioned additively.
6. Existing birthdays are never replaced when they disagree; the field is held for review.
7. Existing addresses are not duplicated when a different Google address already exists; the field is held for review.
8. Organizations may be enriched only when the same organization is missing a title/department. Conflicting organization values are held.
9. Apple photos are written to an existing Google contact only when the contact has no contact photo or only a default contact photo.
10. Apple notes are not auto-written. They need contact-note vs narrative classification; narrative belongs in Obsidian.
11. Google mutations are sequential.
12. The private receipt is written after each operation so interrupted runs can resume without repeating successful work.
13. Source SHA-256 digests bind the plan to the exact Apple vCard and Google snapshot.
14. Create retries are uncertainty-safe across transient 5xx/network failures.
15. There is no Google contact-delete call in the migration helper.

## Rich-field mapping

| Apple field | Google target | Behavior |
|---|---|---|
| `TEL` | `phoneNumbers` | additive union |
| `EMAIL` | `emailAddresses` | additive union |
| `ADR` | `addresses` | add if Google has none; otherwise hold non-matching value |
| `BDAY` | `birthdays` | add if absent; conflicting singleton held |
| `ORG` + `TITLE` | `organizations` | add/enrich conservatively; conflicting same-org values held |
| `URL` | `urls` | additive union |
| `X-ABDATE` | `events` | additive union; Apple omit-year semantics preserved |
| `NICKNAME` | `nicknames` | additive union |
| `X-SOCIALPROFILE` | `urls` or `userDefined` | web URLs become URLs; non-HTTP identifiers are preserved as user-defined contact data |
| `PHOTO` | contact photo | preserve only when not overwriting a real Google contact photo |
| `NOTE` | none automatically | held for classification |

Apple's `X-APPLE-OMIT-YEAR=1604` convention is converted to a month/day Google `Date` without persisting 1604 as a real year.

## Private runtime artifacts

These remain local/private and must not be committed:

```text
.private/people/apple_contacts.vcf
.private/people/google-oauth-client.json
.private/people/google-people-token.json
.private/people/google_people_live.json
.private/people/apple_google_plan.json
.private/people/apple_google_apply_receipt.json
.private/people/google_people_live_after_apple.json
```

## Remaining cutover gate

Provider migration and Neon identity reconciliation are complete. The remaining authority gate is operational:

1. verify Apple devices are consuming the Google contact state without material field loss;
2. only then declare Google Contacts the live mutable-field authority and Apple Contacts a synchronized client;
3. separately review held identity conflicts, weak/name-only matches and note candidates;
4. do not perform destructive provider cleanup without separate explicit approval.

Provider deletion remains a separate approval gate.