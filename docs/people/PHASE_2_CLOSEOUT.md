# People Phase 2 Closeout Receipt

Date: 2026-09-04

This is an aggregate-only production receipt. It intentionally contains no contact names, provider person IDs, phone numbers, email addresses, postal addresses, birthdays, notes, OAuth material, private plans or migration receipts.

## Provider migration

- Google saved contacts before Apple migration: 753
- Apple contacts reconciled: 451
- clean one-to-one existing-Google matches: 246
- Apple-only Google contacts created: 181
- Google saved contacts after migration: 934
- unique stable provider IDs after migration: 934
- original Google provider IDs preserved: 753
- provider contact deletions: 0
- identity conflicts held: 12
- name-only weak matches held: 11
- empty export records held: 1
- Apple notes held for classification: 31
- Apple photos detected: 115

The live migration encountered a transient Google `createContact` 502. Before resuming, the runtime was hardened with uncertainty-safe create recovery: ambiguous retryable failures are reconciled before another POST, deterministic temporary markers protect new creates, and markers are removed after durable receipt success.

## Neon identity state

Initial stable Google identity import:

- 716 canonical active People
- 720 Google person refs
- 33 clear non-person/service holdouts
- 3 clean duplicate clusters representing 7 source refs
- zero orphan refs

Post-Apple provider reconciliation:

- newly-created Google contacts reviewed: 181
- newly-created person-like refs imported to Neon: 169
- newly-created service/sample contacts kept provider-only: 12
- total active People: 885
- total Google person refs: 889
- orphan Google person refs: 0
- non-active People: 0
- private contact-value keys in newly-imported ref metadata: 0
- exact new-ref set verified: yes
- idempotent rerun verified: yes

Neon stores stable identity and provider reference metadata. Mutable contact values remain provider-owned and were not duplicated into the People external-reference metadata.

## Safety / remaining gate

- Provider contact deletion remains unauthorized and unimplemented.
- Destructive Obsidian cleanup remains unauthorized.
- Ambiguous identities remain held rather than guessed.
- Google Contacts mutable-field authority is not yet formally declared.
- Remaining cutover gate: verify Apple devices consume the reconciled Google contact state without material field loss; after that, Google Contacts can become the mutable address-book field authority and Apple Contacts the synchronized device client.

The historical Phase 1 report remains unchanged as a point-in-time record.