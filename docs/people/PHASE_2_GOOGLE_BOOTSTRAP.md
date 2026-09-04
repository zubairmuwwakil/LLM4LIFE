# People Phase 2 — Google Stable-ID Bootstrap

**Status:** User has approved real People import, conservative clean one-to-one merges, non-destructive contact edits, Google People API read/write authorization, and the provider permission flow. Contact deletion is not approved.

## Why this local bootstrap exists

The installed ChatGPT Google Contacts connector can search/read named contacts but cannot enumerate the complete address book or mutate contacts. The Google CSV export is complete enough for reconciliation but contains no durable People API `people/...` resource names.

Phase 2 therefore needs one local OAuth bootstrap to obtain stable Google provider IDs before any canonical Neon import.

Apple stable IDs are not a blocker for the first Phase 2 import. Google Contacts is the accepted mutable address-book authority after cutover. Apple-only export records can be migrated into Google later, at which point Google returns durable `people/...` IDs. Apple export row hashes remain migration evidence only and never become `external_refs`.

## Safety boundary

Google's `https://www.googleapis.com/auth/contacts` scope is the only People scope that permits contact edits. It also technically permits deletion. LLM4LIFE does **not** treat scope capability as user authorization: provider contact deletion remains prohibited until separately approved.

The bootstrap script itself performs no create/update/delete calls. It only enumerates saved contacts and writes a private stable-ID snapshot.

Keep the OAuth client, refresh token, and generated snapshot under `.private/people/`, which is git-ignored. Treat the token as a secret.

## One-time Google setup

1. In Google Cloud Console, select the Google Cloud project that should own the LLM4LIFE People integration (or create one if no suitable existing project exists).
2. Enable **People API** for that project.
3. Configure the OAuth consent screen if the project has not already done so.
4. Create an **OAuth client ID** with application type **Desktop app**.
5. Download the client JSON and save it locally as:

```text
.private/people/google-oauth-client.json
```

Never commit that file.

## Run the authorization + enumeration

From the LLM4LIFE repository root:

```bash
python3 -m venv .venv-people
source .venv-people/bin/activate
python -m pip install -r requirements-people-phase2.txt
python scripts/google_people_phase2.py enumerate --account-scope google-primary
```

The browser opens Google's OAuth consent page. Sign into the same Google account used for the saved-contact export and click **Allow**.

The script stores the refresh token privately at:

```text
.private/people/google-people-token.json
```

and writes the stable-ID snapshot at:

```text
.private/people/google_people_live.json
```

The terminal prints aggregate counts only.

Recommended local hardening:

```bash
chmod 600 .private/people/google-oauth-client.json \
  .private/people/google-people-token.json \
  .private/people/google_people_live.json
```

## Snapshot contents

The stable-ID snapshot keeps only what Phase 2 matching requires:

- Google `people/...` resource name;
- ETag;
- display name;
- email values;
- phone values;
- deleted/archive marker;
- booleans indicating the presence of richer field classes.

It deliberately does not copy address, birthday, organization, biography/note, event, relation, URL, photo, or user-defined values into this intermediate matching snapshot.

## Next step after enumeration

Provide `.private/people/google_people_live.json` to the Phase 2 reconciliation process privately. The next plan will:

1. map the 753 Google export rows to durable `people/...` IDs;
2. re-evaluate the 239 clean Google↔Apple pairs against those stable refs;
3. leave conflict/name-only cases unmerged;
4. create a deterministic migration plan for Apple-only records and Apple-only fields;
5. require ETag-safe Google updates and sequential writes;
6. create/import canonical Neon `people` and `external_refs` only from durable provider identities;
7. prove rerun idempotency and zero orphan refs.

No export row hash may be inserted into `llm4life.external_refs`.

## Permission receipt

The user explicitly approved the Google People API read/write permission flow in chat on 2026-09-04 after separately approving real People import, clean high-confidence merging, and non-destructive contact edits.

This approval does not include contact deletion or destructive Obsidian cleanup.
