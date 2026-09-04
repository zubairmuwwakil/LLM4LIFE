# Private People Inventory Runbook

**Purpose:** complete the remaining read-only People Phase 1 inventory/reconciliation gate without copying real contact payloads into the public repository or writing to Neon/provider contact stores.

This runbook is deliberately export-first. The connected Google Contacts search surface is useful for targeted reads but is not a complete enumeration API: it is query-oriented, result-limited, and may mix saved contacts with Google `Other Contacts`. Do not approximate a full inventory by issuing alphabet/single-letter searches.

## Safety boundary

This workflow is read-only.

It does **not** authorize:

- importing real people into Neon;
- persisting export-derived snapshot IDs into `llm4life.external_refs`;
- merging, editing, deleting, or creating Google/Apple contacts;
- changing Google-vs-Neon contact-field authority;
- adding OAuth scopes/credentials or macOS Contacts permissions;
- copying raw or normalized contact payloads into Git/GitHub.

Keep all real export and derived files under `.private/people/` or another private local path outside the repository.

## 1. Obtain private snapshots

### Google saved contacts

Use the supported Google Contacts export UI to export the complete saved-contact set. Google documents CSV and vCard export from Contacts:

- https://support.google.com/contacts/answer/7199294

For this Phase 1 snapshot, **Google CSV is preferred** because it makes field-presence auditing straightforward. It is not a stable provider-reference source: the CSV does not expose the People API `resourceName` (`people/...`). Stable Google provider refs still require a supported People API enumeration path before canonical import.

Place the file privately, for example:

```text
.private/people/raw/google_contacts.csv
```

Google `Other Contacts` should remain a separate evidence source. Do not silently promote auto-collected correspondents into the intentional address book.

### Apple / iCloud contacts

Use iCloud Contacts' supported **Export vCard** flow. Apple documents selecting contacts and exporting them as vCard; exporting multiple contacts produces one vCard file:

- https://support.apple.com/guide/icloud/export-contact-information-mmfba748b2/icloud

Place it privately, for example:

```text
.private/people/raw/icloud_contacts.vcf
```

For the eventual runtime bridge, prefer the supported macOS Contacts framework (`CNContactStore`) over UI automation. Apple contact identifiers are device-scoped and must not replace the canonical Neon `person_id`.

## 2. Normalize privately

Create the private directory if needed:

```bash
mkdir -p .private/people/raw
```

Normalize Google:

```bash
python scripts/people_inventory.py google-csv \
  .private/people/raw/google_contacts.csv \
  --account-scope google-primary \
  --output .private/people/google_contacts.json
```

Normalize Apple/iCloud:

```bash
python scripts/people_inventory.py vcard \
  .private/people/raw/icloud_contacts.vcf \
  --source apple_contacts \
  --account-scope icloud-primary \
  --output .private/people/apple_contacts.json
```

The normalizer keeps only the fields needed for conservative identity matching:

- display name;
- email addresses;
- phone numbers;
- source/account scope;
- export identifier metadata.

For address, birthday, organization, and notes it stores **presence booleans only**, not values. Photos are not retained. This minimizes the private matching corpus while still allowing aggregate field-preservation checks.

The CLI prints aggregate counts only.

## 3. Combine snapshots

```bash
python scripts/people_inventory.py combine \
  .private/people/google_contacts.json \
  .private/people/apple_contacts.json \
  --output .private/people/combined_contacts.json
```

Optional aggregate-only check:

```bash
python scripts/people_inventory.py summarize \
  .private/people/combined_contacts.json
```

## 4. Generate duplicate candidates

Run the existing deterministic dry-run engine:

```bash
python scripts/people_dedup.py \
  .private/people/combined_contacts.json \
  --output .private/people/duplicate_candidates.json
```

This produces candidates only. It never auto-merges.

A separate optional review pass can include exact normalized-name-only matches:

```bash
python scripts/people_dedup.py \
  .private/people/combined_contacts.json \
  --include-name-only \
  --output .private/people/duplicate_candidates_with_name_only.json
```

Name-only candidates are always weak and never auto-mergeable.

## 5. Reconciliation checklist

Before any canonical import, record **aggregate/non-sensitive receipts only**:

1. total saved Google contacts exported;
2. total Apple/iCloud contacts exported;
3. contacts with email/phone/address/birthday/organization/notes by source;
4. number of high/conflict/weak candidates;
5. number of records with snapshot-only identifiers;
6. number of records with export UIDs;
7. any field class present in Apple but not preservable in the proposed Google-centered model;
8. unresolved duplicate/conflict count.

Do not publish names, email addresses, phone numbers, birthdays, addresses, notes, provider IDs, or candidate pair details.

## Identifier rule

The normalized export's `external_id` is **not automatically a provider identity**.

- Google CSV rows use deterministic `google-csv:row:...` IDs marked `snapshot_only`. Never persist these into `llm4life.external_refs`.
- vCard `UID` values are preserved as `vcard-uid:...` and marked `export_uid`, but they remain export identifiers until provider/device semantics are independently verified.
- Canonical Google `people/...` resource names and any eventual Apple device/container identifiers must come from their supported provider interfaces and be stored with explicit account/device scope.

## Field-authority gate

Aggregate presence comparison is necessary but not sufficient to finalize mutable contact-field authority. Before Google Contacts becomes authoritative for phone/email/address/birthday, perform a private local preservation review of any Apple-only or structurally richer fields that matter.

If Google cannot preserve important Apple data without lossy transformation, revise the field-authority recommendation rather than creating hidden bidirectional dual truth.

## Definition of Phase 1 inventory complete

The inventory portion of Phase 1 is complete only when:

- complete saved-contact snapshots exist for Google and Apple/iCloud;
- normalized counts are reproducible;
- duplicate candidates have been generated deterministically;
- ambiguous candidates remain unresolved rather than guessed;
- field-preservation risk has been reviewed;
- no private contact payload has entered the public repo;
- no provider or Neon contact mutation occurred.

Only then move to the separately approved Phase 2 canonical identity import.
