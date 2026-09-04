# Apple → Google Contacts Phase 2 Migration

**Status:** deterministic private plan ready; provider apply pending the user-local OAuth token.  
**Privacy:** real vCards, plans, receipts, names, contact values and Google resource names stay under `.private/people/` and must never be committed.

## Goal

Converge mutable standard address-book fields into Google Contacts while preserving Neon as the stable Person identity authority and Apple Contacts as a synchronized device client after cutover.

The migration is intentionally non-destructive. Provider-contact deletion is not authorized and the migration helper implements no delete endpoint.

## Private reconciliation result

The complete private Apple export was compared with the complete stable-ID Google saved-contact snapshot using the conservative People identity rules:

- 451 Apple contacts;
- 753 Google saved contacts;
- 246 clean one-to-one high-confidence matches eligible for additive update;
- 181 Apple-only contacts eligible for Google create;
- 12 identity conflicts held;
- 11 name-only weak matches held;
- 1 empty export record held;
- 31 Apple notes held for separate classification;
- 115 Apple photos detected.

Only aggregate counts are recorded publicly.

## Safety invariants

`scripts/apple_google_phase2.py` enforces the following:

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
12. The private receipt is written after each operation so interrupted runs can resume without repeating successful creates/updates.
13. Source SHA-256 digests bind the plan to the exact Apple vCard and Google snapshot used to create it.
14. There is no Google contact-delete call in this migration helper.

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
| `X-SOCIALPROFILE` | `urls` or `userDefined` | real web URLs become URLs; non-HTTP Apple identifiers are preserved as user-defined contact data |
| `PHOTO` | contact photo | preserve only when not overwriting a real Google contact photo |
| `NOTE` | none automatically | held for classification |

Apple's `X-APPLE-OMIT-YEAR=1604` convention is converted to a month/day Google `Date` without persisting 1604 as a real year.

## Commands

The local private Apple export should be placed at:

```text
.private/people/apple_contacts.vcf
```

The stable Google snapshot and OAuth files from the earlier bootstrap remain:

```text
.private/people/google_people_live.json
.private/people/google-oauth-client.json
.private/people/google-people-token.json
```

Generate/re-generate the private plan:

```bash
python scripts/apple_google_phase2.py plan
```

Validate the plan and source digests without provider writes:

```bash
python scripts/apple_google_phase2.py apply
```

Perform the already-approved non-destructive provider writes:

```bash
python scripts/apple_google_phase2.py apply --apply
```

The apply step writes/resumes:

```text
.private/people/apple_google_apply_receipt.json
```

and, after successful completion, refreshes the stable Google snapshot to:

```text
.private/people/google_people_live_after_apple.json
```

## After provider apply

1. Reconcile the refreshed Google stable IDs against the apply receipt.
2. Import newly-created **person-like** Google refs into Neon idempotently.
3. Keep service/business contacts provider-only unless they belong in the People domain.
4. Verify zero orphan refs, stable counts and rerun idempotency.
5. Verify Apple sync before declaring Google Contacts the live mutable-field authority.
6. Review the 12 identity conflicts, 11 weak matches and note candidates separately. Do not silently auto-resolve them.

Provider deletion or destructive duplicate cleanup remains a separate approval gate.
