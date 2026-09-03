# Decision: Google Tasks Projection Worker

**Date:** 2026-09-02  
**Status:** Accepted; implementation committed, runtime deployment pending OAuth/Cloudflare secrets

## Context

LLM4LIFE now owns canonical personal action state in Neon/PostgreSQL. Google Tasks is still the preferred lightweight human-facing action client, but the current ChatGPT runtime does not expose a native Google Tasks connector.

The user also prefers free/no-new-subscription infrastructure and does not want GitHub Actions consumed by general personal automation.

## Decision

Implement a thin Google Tasks adapter as a Cloudflare Worker with a 15-minute Cron Trigger.

```text
Google Tasks
    ^  |
    |  v
Cloudflare Worker
    ^  |
    |  v
Neon/PostgreSQL (canonical actions)

Google Calendar remains execution/time.
```

The implementation lives under `integrations/google-tasks-worker/`.

## Ownership and conflict rules

- `llm4life.actions` remains canonical action state.
- Google Tasks is a projection **and an authorized capture/control surface**, not a second canonical database.
- New tasks created in the dedicated `LLM4LIFE` Google Tasks list become Neon `inbox` actions.
- Google completion/reopen gestures update Neon status.
- Safe Google title/date edits are ingested when Neon has not independently changed since the previous projection.
- If both Google and Neon changed, Neon wins non-status fields and the conflict is recorded.
- Deleting a Google Task never deletes the canonical Neon action; it disables that projection.
- Neon cancelled/archived actions can be removed from Google Tasks because the Google record is only a projection.
- Existing historical completed actions are not backfilled into Google Tasks unless they already had a projection.

## Date semantics

Google Tasks API discards time-of-day from the task `due` field. Therefore:

- regular actions project `due_date`, or only the local calendar day of `due_at`;
- waiting actions project `follow_up_date`, or only the local calendar day of `follow_up_at`;
- `scheduled_for` is **never** represented as a Google Tasks due date;
- Google Calendar remains the execution-time owner.

## Runtime and observability

The Worker:

- runs every 15 minutes;
- uses the Neon serverless driver;
- records a durable `jobs` / `job_runs` execution trail;
- uses `external_refs` for Google Task IDs;
- uses `sync_checkpoints` for integration state;
- writes idempotent `action_receipts` for meaningful state changes/conflicts;
- never falls back to Notion if Neon is unavailable.

## Authentication

Use Google OAuth 2.0 with only:

`https://www.googleapis.com/auth/tasks`

A local PKCE/loopback helper obtains the refresh token once. Runtime credentials are Cloudflare Worker secrets and must never be committed to the public repository.

For a persistent personal deployment, do not leave the Google OAuth app in Testing status because Testing refresh tokens are time-limited.

## Why Cloudflare Worker

Chosen over Mac cron and GitHub Actions because:

- it runs when the user's laptop is off;
- Cloudflare is already part of the user's stack;
- Cron Triggers are appropriate for periodic API synchronization;
- it preserves GitHub Actions for repository CI/CD;
- it fits the free-first constraint;
- it keeps the adapter small and replaceable.

## Alternatives rejected for now

- **GitHub Actions:** quota is already a pain point and CI should remain repo-focused.
- **Always-on Mac cron:** unreliable when the laptop sleeps/offlines.
- **Make Google Tasks canonical:** insufficient domain richness and conflicts with the established Neon ownership model.
- **Notion task bridge:** planning state has already been cut over from Notion.

## Rollback

Disabling/removing the Worker does not destroy canonical actions. Google Task IDs remain in `external_refs`, and Neon continues to operate with ChatGPT planning + Google Calendar. The projection can be rebuilt later.
