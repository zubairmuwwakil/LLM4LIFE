# Google Tasks Projection Worker

This Cloudflare Worker projects LLM4LIFE personal actions from Neon into a dedicated Google Tasks list and ingests safe user edits back into canonical Neon state.

## Architecture

```text
Google Tasks (human action client)
          ^        |
          |        | capture / complete / reopen / safe edits
          |        v
 Cloudflare Worker every 15 min
          |
          v
Neon llm4life.actions (canonical)
```

Google Calendar remains the execution/time layer. Google Tasks is not used to store execution time.

## Sync contract

Neon remains canonical, but Google Tasks is an authorized input surface:

- Neon creates/updates active Google Tasks projections.
- New tasks created inside the dedicated `LLM4LIFE` Google Tasks list are captured into Neon as `inbox` actions.
- Completing a Google Task marks the Neon action `done`.
- Reopening a completed Google Task moves the Neon action to `next`.
- Google title/date edits are ingested when Neon has not independently changed since the last projection.
- When both sides changed, Neon wins non-status fields and a sync-conflict receipt is recorded.
- Deleting a Google Task does **not** delete the Neon action. It disables that projection and records a receipt.
- Neon `cancelled`/`archived` actions are removed from Google Tasks because Google Tasks is only a projection.
- Historical `done` Neon actions are not created in Google Tasks if they were never projected before.

### Date semantics

The Google Tasks API stores only the **date** portion of a task's `due` field; time-of-day is discarded. Therefore:

- regular actions project `due_date` (or the local day of `due_at` when present);
- waiting actions project `follow_up_date` (or the local day of `follow_up_at`);
- `scheduled_for` is never used as a Google Tasks due date; execution time remains in Google Calendar.

## Runtime state

The Worker uses existing LLM4LIFE tables:

- `llm4life.actions`
- `llm4life.external_refs`
- `llm4life.jobs`
- `llm4life.job_runs`
- `llm4life.sync_checkpoints`
- `llm4life.action_receipts`

No additional database migration is required.

## Google setup (one time)

1. In a Google Cloud project you control, enable **Google Tasks API**.
2. Configure the OAuth consent screen for personal use.
3. Request only `https://www.googleapis.com/auth/tasks`.
4. Create an **OAuth Client ID → Desktop app** and download the JSON credentials file.
5. For a persistent deployment, do not leave the OAuth app in **Testing**: Google limits refresh-token lifetime for Testing apps. For a personal-use app, you can publish it without making it a public multi-user product; an unverified warning can still appear.
6. From this directory:

```bash
npm install
npm run oauth -- /absolute/path/to/client_secret.json
```

The helper opens Google's authorization page with PKCE and a local loopback callback, then prints the three Google secret values for you to store securely.

## Cloudflare deployment

The Worker is configured with a Cron Trigger every 15 minutes (`*/15 * * * *`). Cloudflare cron expressions execute in UTC; this interval is timezone-independent.

Set secrets — never commit their values:

```bash
npx wrangler secret put DATABASE_URL
npx wrangler secret put GOOGLE_CLIENT_ID
npx wrangler secret put GOOGLE_CLIENT_SECRET
npx wrangler secret put GOOGLE_REFRESH_TOKEN
npx wrangler secret put SYNC_ADMIN_TOKEN
```

Then deploy:

```bash
npm run deploy
```

The Worker automatically finds a Google Tasks list named `LLM4LIFE`; if none exists it creates exactly one. If more than one list has that exact title, sync fails rather than guessing.

## Manual smoke test

After deployment:

```bash
curl -X POST \
  -H "Authorization: Bearer $SYNC_ADMIN_TOKEN" \
  https://<worker-host>/sync
```

Public health check:

```bash
curl https://<worker-host>/health
```

Verify after the first sync:

- active Neon actions appear in the `LLM4LIFE` Google Tasks list;
- `llm4life.external_refs` contains `google_tasks` projection refs;
- `llm4life.job_runs` contains a successful `google-tasks-sync` run;
- `llm4life.sync_checkpoints` contains `google_tasks_tasklist` and `google_tasks_projection`;
- no secrets appear in GitHub or Worker logs.

## Failure behavior

- Google/Neon failures mark the run failed in `job_runs`.
- Re-running the same scheduled invocation is idempotent once it succeeded.
- A failed sync never falls back to Notion.
- Google deletion never destroys canonical Neon action state.
