# People Phase 2 Production Receipt

**Date:** 2026-09-04  
**Scope:** Google canonical identity import + non-destructive Apple → Google Contacts provider cutover  
**Privacy:** aggregate operational metadata only; no private contact values, provider IDs, OAuth material, plans, or receipts are committed here.

## Result

People Phase 2 has completed the canonical identity import and the non-destructive Apple → Google Contacts provider migration.

The remaining ownership gate is **Apple-device sync verification**. Google Contacts is the intended mutable standard address-book field authority, but that authority is not declared fully live until Apple Contacts is verified to consume the Google-canonical address book as the synchronized device client.

## Verified provider state

Private refreshed Google snapshot verification after cutover:

- 934 saved Google contacts;
- 934 unique provider-stable `people/...` IDs;
- all original 753 Google provider IDs retained;
- exactly 181 new Google provider IDs created from Apple-only contacts;
- zero original Google provider IDs lost;
- no provider deletion path was used.

The refreshed snapshot is private-local at:

```text
.private/people/google_people_live_after_apple.json
```

The private per-operation apply receipt remains local at:

```text
.private/people/apple_google_apply_receipt.json
```

Neither file belongs in the public repository.

## Verified Neon state

After classifying the 181 new provider records conservatively:

- 169 new person-like Google refs were imported to Neon;
- 12 obvious demo/test/non-person/service records were deliberately left provider-only;
- 885 canonical People rows are active;
- 889 Google person external refs are live;
- the 4-ref difference is expected from the previously reviewed safe duplicate clusters;
- zero Google person refs are orphaned;
- zero Google person refs are archived.

The complete sorted Google-person-ref set in Neon was verified against the reviewed private expected set. The exact set matched.

## Privacy boundary verified

For the 169 new Google person refs, Neon external-reference metadata contains only:

- `etag`;
- `external_id_stability`;
- `snapshot_generated_at`;
- `source`.

Phone numbers, email addresses, postal addresses, birthdays, notes, and other raw address-book payloads were **not** copied into Neon.

Neon remains the stable identity / structured People machine-state owner. Mutable address-book values remain provider-owned.

## Reconciliation / held work

The migration intentionally preserved review queues rather than forcing uncertain merges or narrative writes:

- 12 Apple identity conflicts held;
- 11 name-only weak matches held;
- 1 empty Apple export record held;
- 31 Apple notes held for classification rather than auto-written;
- no same-name-only auto-merge;
- no automatic note-to-Google write;
- no provider contact deletion.

These held items are follow-up review work, not blockers for the canonical identity import or provider migration.

## Reliability closeout

The live cutover encountered a transient Google People `createContact` 502. The migration runtime was hardened before resuming:

- ambiguous 5xx create outcomes are reconciled before retry;
- future creates use deterministic temporary migration markers;
- retryable failures search for the marker before any second POST;
- non-retryable 4xx responses are not blindly retried;
- durable per-operation receipts make the apply resumable;
- successful temporary markers are removed while preserving legitimate user-defined contact fields;
- no provider delete endpoint was introduced.

The final refreshed provider count matched the deterministic create plan exactly, confirming no loss and no extra create beyond the 181 planned Apple-only contacts.

## Remaining gate

Before declaring the mutable contact-field cutover fully complete:

1. verify Apple Contacts on the user’s devices is consuming/syncing the Google-canonical address book as intended;
2. then mark Google Contacts as live mutable standard contact-field authority;
3. separately review the 12 identity conflicts, 11 weak name-only matches, and 31 note candidates;
4. keep provider deletion and destructive legacy cleanup out of scope unless separately approved.

Historical Phase 1 documents remain historical. Current runtime truth belongs in `docs/STATUS.md`, `docs/PEOPLE.md`, this receipt, and `config/people-phase2.yaml`.
