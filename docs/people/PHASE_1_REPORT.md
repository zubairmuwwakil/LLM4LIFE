# People / Relationships Phase 1 Report

**Date:** 2026-09-04  
**Status:** Phase 1 schema is **live in production Neon**; complete Apple/Google inventory and real-contact reconciliation are still pending.  
**Privacy:** No real names, contact fields, provider IDs, birthdays, relationship notes, or message content are recorded here.

See `docs/STATUS.md` for current runtime state and this report for the Phase 1 architecture decision, validation receipts, inventory findings, privacy boundaries, and remaining approval gates.

## Executive decision

- Reuse `llm4life.external_refs`; do not create `person_external_refs`.
- `004_people.sql` is deployed to production.
- People schema is live and empty: 0 People rows, 0 facts, 0 interactions immediately after deployment.
- All 95 pre-existing external refs were preserved.
- No real contacts were imported, merged, modified, or deleted.
- Complete Google/Apple inventory and field-authority cutover remain separate gated work.

## External reference model

People exposed one generic gap: provider IDs need explicit account scope. `004_people.sql` adds `account_scope`, `first_seen_at`, `last_seen_at`, and `archived_at`, with uniqueness on:

```text
(system_id, account_scope, internal_type, external_id)
```

The generic table is polymorphic, so People import/reconciliation code must reject orphan `internal_type='person'` refs. That tradeoff is preferable to fragmenting the established reference abstraction.

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
- mutable Google/Apple field-ownership cutover
- automatic relationship capture/automation

## Validation receipts

Before deployment, production had no People tables and 95 generic external refs. The proposed migration was validated on a disposable Neon branch with synthetic data only.

Synthetic validation covered:

- same name, different people;
- exact provider-ref rerun idempotency;
- provider-ref uniqueness within account scope;
- same external ID across different account scopes;
- renamed contact retaining stable identity;
- archived provider record preservation;
- fact provenance/supersession;
- sensitive model-suggested fact guard;
- multi-person interactions;
- `action_people` rerun idempotency;
- no accidental Google Task/Calendar side effects.

After approved production deployment, all six tables existed, People/facts/interactions remained at zero, and all 95 pre-existing external refs remained present.

## Dedup engine

`scripts/people_dedup.py` is read-only/dry-run and uses deterministic candidate IDs. Exact provider refs resolve first; strong contact signals produce candidates; same-name-only matches never auto-merge; ambiguous/conflicting cases remain reviewable.

## Google Contacts findings

The connected connector is useful for targeted read-only lookup but is not a complete inventory API because it is query-oriented, result-limited, mixes saved contacts with `Other Contacts`, and cannot reliably read every `otherContacts/...` result.

For exhaustive reconciliation, use the supported Google People API enumeration path rather than treating connector search as complete.

## Apple Contacts findings

Use a private local vCard export for initial read-only inventory. For the eventual runtime bridge, prefer a trusted macOS `CNContactStore` adapter over UI automation. Apple identifiers are device-local external refs, never the canonical `person_id`.

## Contact-field authority

Current conditional recommendation:

```text
Neon
  stable person_id
  provider refs
  relationship state
  facts/provenance
  interaction metadata

Google Contacts
  mutable address-book fields if complete Apple inventory proves preservation

Apple Contacts
  synchronized device client after reconciliation

Obsidian
  narrative context
```

This remains pending complete Apple/iCloud inventory, preservation testing, and explicit cutover approval.

## Privacy/security

- Public repo contains schemas/algorithms/synthetic fixtures only.
- Raw Google/Apple exports stay private/transient.
- Real provider IDs/account scopes stay private runtime state.
- No full conversation archival by default.
- Sensitive model inference does not become durable truth automatically.
- New People API scopes or macOS Contacts permissions remain approval-gated.

## Next plan

1. Complete Google saved-contact inventory via a supported enumeration path.
2. Complete Apple/iCloud inventory privately.
3. Run deterministic normalization and duplicate-candidate generation.
4. Review conflicts; never merge by name alone.
5. Verify Apple fields can be preserved under the proposed Google-field-authority model.
6. Obtain explicit approval before importing real People/refs.
7. Prove import rerun idempotency and zero orphan refs.
8. Audit/review every merge and preserve reversible lineage.
9. Test bounded synthetic Google write-back/ETag behavior before any field-ownership cutover.
10. Link Obsidian narrative notes later without copying prose into Neon.

## Remaining approval gates

Stop before:

- importing, merging, modifying, or deleting real contacts;
- changing Google/Apple contact ownership in production;
- destructive Obsidian cleanup;
- creating new OAuth credentials/scopes or local Contacts permissions.
