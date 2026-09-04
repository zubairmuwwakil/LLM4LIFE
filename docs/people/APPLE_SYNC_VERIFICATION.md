# Apple Contacts Sync Verification

**Purpose:** verify the final People Phase 2 operational gate before declaring Google Contacts the mutable standard address-book field authority.

The provider migration and Neon identity reconciliation are already complete. This check proves that the Mac Contacts store is actually consuming the post-cutover Google Contacts state without material field loss.

## One-command verification

Run on the user's Mac from the LLM4LIFE repo:

```bash
git pull
bash scripts/run_people_sync_verification.sh
```

The wrapper:

1. reads the private post-cutover Google snapshot at `.private/people/google_people_live_after_apple.json`;
2. uses the macOS Contacts framework read-only to export the current Contacts containers into `.private/people/apple_contacts_live.json`;
3. automatically evaluates each Apple Contacts container and selects the one with the highest overlap with the Google snapshot;
4. requires at least 98% Google-contact identity coverage;
5. requires no more than 1% loss across core synchronized field instances (email, phone, address, birthday, organization and URL presence);
6. reports photo presence separately as advisory because Apple may lazy-load contact images;
7. writes an aggregate-only private receipt at `.private/people/apple_google_sync_verification_receipt.json`.

No contact mutation or provider deletion is performed.

## Privacy

The raw Apple runtime snapshot contains contact values and is private. It must stay under `.private/people/` and must never be committed.

The verification receipt intentionally omits:

- names;
- emails;
- phone numbers;
- addresses;
- provider contact IDs;
- Apple container IDs/names.

Only aggregate coverage, field-loss counts, container type/counts and thresholds are emitted.

## Pass condition

The gate passes only when both are true:

```text
identity coverage >= 0.98
core field loss rate <= 0.01
```

A passing local receipt is evidence that Apple Contacts is consuming the reconciled Google state closely enough to proceed with the mutable-field authority declaration. A failed receipt should be investigated rather than weakening thresholds or deleting legacy state.

## Local permissions

Full Contacts access is required because the verifier must enumerate the complete synchronized container. Modern Apple platforms can grant **Limited Access** to only a selected subset of contacts; Limited Access is insufficient for whole-address-book reconciliation.

If the exporter reports `authorization_status` of `limited` or `denied`:

1. Open **System Settings → Privacy & Security → Contacts**.
2. Find the terminal app used to run the verifier (for example Terminal, iTerm, Warp, or whichever host macOS lists for the request).
3. Enable Contacts access and choose **Full Access** if macOS offers an access-level choice.
4. Rerun `bash scripts/run_people_sync_verification.sh`.

The exporter re-checks the authorization state after the permission prompt and refuses to continue unless the effective state is full/authorized. Permission failures are emitted as compact structured errors rather than Swift stack dumps.

The exporter is read-only and does not create, update or delete contacts.

## CI coverage

Synthetic tests cover full sync, partial sync, material field loss and receipt privacy. GitHub Actions also type-checks the Contacts-framework Swift exporter on a macOS runner so SDK/API errors are caught before local execution.
