# Runtime Status

_Last updated: 2026-09-02_

This file describes **what is actually live now**. Target ownership is defined by `config/domains.yaml` and `system.yaml`.

## Headline

The v2 Neon backend is live and **personal action/planning state has been cut over from Notion to Neon**.

Implemented and verified:

- dedicated `llm4life` Neon project and production schema;
- 15 production `llm4life` tables from the v2 migrations;
- date-only deadline/follow-up semantics (`db/migrations/003_date_only_action_semantics.sql`);
- snapshot migration of all 15 Notion Tasks rows;
- migration of both existing Task Execution Log rows;
- stable Notion and Google Calendar external references;
- migration checkpoints and audit receipts;
- source/destination parity verification;
- live Daily Planning Loop, Calendar Task Follow-Up, and Weekly Systems Review prompts cut over to Neon canonical task state;
- Google Tasks projection Worker implementation committed under `integrations/google-tasks-worker/`;
- InUnity ChatGPT MCP integration completed and recently read-verified.

The Google Tasks Worker is **implemented but not deployed yet**. Google OAuth secrets and a Cloudflare Worker deployment are still required before Google Tasks becomes a live projection/client.

Parity at cutover:

- 15 Notion task rows -> 15 Neon actions;
- 2 Notion execution rows -> 2 Neon action executions;
- status distribution matched exactly: 1 Done, 1 legacy status-less item, 1 Next, 10 Scheduled, 2 Waiting;
- the legacy status-less item was preserved as `inbox` with migration metadata rather than inventing meaning;
- 15 Notion action references were preserved;
- 13 Google Calendar action bindings were preserved;
- Scheduling Model contained **no learned overrides**, so zero artificial `adaptive_rules` were created.

## Canonical planning runtime

```text
Neon/PostgreSQL
  llm4life.actions
  llm4life.action_executions
  llm4life.adaptive_rules
  llm4life.external_refs
  llm4life.action_receipts
          |
          v
  ChatGPT planning automations
          |
          v
   Google Calendar
    execution/time
```

Target client path once deployment completes:

```text
Google Tasks
      ^  |
      |  v
Cloudflare Worker (15-minute sync)
      ^  |
      |  v
Neon/PostgreSQL canonical actions
```

### Current ownership

- **Neon `llm4life.actions`** -> canonical personal action/backlog state.
- **Google Calendar** -> execution schedule and fixed time commitments.
- **Neon `action_executions`** -> scheduling/execution telemetry.
- **Neon `adaptive_rules`** -> learned scheduling overrides; currently empty until evidence justifies a rule.
- **Neon `action_receipts`** -> meaningful autonomous-action audit metadata.
- **Notion Tasks / Task Execution Log / Scheduling Model / AI Activity Log** -> rollback/reference only for migrated planning state; live planning automations must not write them as canonical state.
- **Notion Shopping Needs** -> still transitional for personal-care inventory until that domain is migrated.
- **InUnity** -> canonical consolidated finance application; ChatGPT MCP integration is implemented and has been exercised successfully.

## Active planning automations

The following live automations now use Neon canonical action state:

1. **Daily Planning Loop** — 7:30 AM + 7:30 PM.
2. **Calendar Task Follow-Up** — hourly condition watch.
3. **Weekly Systems Review** — Friday around 5 PM.

Legacy Calendar events remain compatible:

- new blocks use `[LLM4LIFE:ACTION_ID=<uuid>]` where possible;
- existing `[LLM4LIFE:TASK_URL] <notion-url>` markers may still resolve through `external_refs`;
- the Notion record is an identifier/rollback source, not canonical task state.

If Neon is unavailable, automations are instructed **not** to silently fall back to Notion writes.

## Google Tasks adapter state

Code exists at `integrations/google-tasks-worker/` and includes:

- Cloudflare Worker runtime;
- Cron Trigger every 15 minutes;
- Neon serverless database access;
- least-privilege Google Tasks OAuth scope;
- local PKCE OAuth bootstrap helper;
- automatic dedicated `LLM4LIFE` task-list discovery/creation;
- Neon -> Google Tasks projection;
- Google Tasks -> Neon capture, complete/reopen, and safe title/date ingestion;
- conflict detection when both sides changed;
- safe deletion semantics: deleting a Google Task never deletes the Neon action;
- `jobs` / `job_runs`, `external_refs`, `sync_checkpoints`, and `action_receipts` integration;
- protected manual `/sync` endpoint and public `/health` endpoint.

Runtime deployment is still blocked on:

1. enabling Google Tasks API in the user's Google Cloud project;
2. creating a personal-use OAuth desktop client and obtaining a refresh token;
3. storing `DATABASE_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, and `SYNC_ADMIN_TOKEN` as Cloudflare Worker secrets;
4. deploying the Worker and running the first smoke test.

The official Cloudflare ChatGPT app was enabled by the user, but this current session still does not expose a Cloudflare tool namespace, so deployment could not be performed through ChatGPT yet.

## Runtime paths

| System | Runtime status | Current role / limitation |
|---|---|---|
| GitHub | Connected, read/write verified | Architecture/config/code repository operations |
| Neon | **Connected / canonical personal action backend** | Production schema and migrated action state are live; read/write path verified |
| ChatGPT Automations | Connected/live | Planner/follow-up/review now point at Neon canonical task state |
| Google Calendar | Connected | Execution schedule and commitments |
| Notion | Transitional / rollback for planning | Planning snapshot retained for rollback/reference; Shopping Needs still live until migrated |
| Google Tasks | **Adapter implemented; deployment pending** | Preferred human action client; Cloudflare + Google OAuth runtime not live yet |
| Cloudflare | Partial | Existing user platform and intended Google Tasks Worker runtime; ChatGPT app enabled but namespace not visible in this session |
| InUnity | **MCP integration complete / recently read-verified** | Consolidated finance system; current session should re-check namespace before a live call |
| Gmail | Connected capability | Email/source context and supported actions |
| Slack | Connected capability | Work communication/context |
| Google Contacts | Connector available; migration not done | Preferred canonical address book after Apple/Google dedup |
| Apple Contacts | User-live | Still contains part of contact identity; intended to become synced client |
| Obsidian | Partial | GitHub-backed vault accessible; trusted live local-vault bridge remains unimplemented |
| Jira / Atlassian | Connector available; verify per task | Canonical engineering backlog |
| ORC | External subsystem | Coding-agent orchestrator |
| Discord / WhatsApp / iMessage | User-live channels | Cross-channel AI access still requires verified bridge/native integration |

## Next implementation priorities

### P0 — Deploy Google Tasks projection adapter

Implementation and architecture are complete. The remaining work is runtime setup:

1. enable Google Tasks API;
2. create personal OAuth credentials using only `https://www.googleapis.com/auth/tasks`;
3. use the committed OAuth helper to obtain a refresh token;
4. add secrets to Cloudflare;
5. deploy `llm4life-google-tasks-sync`;
6. run one manual sync;
7. verify Google Task projections + Neon refs/job receipts;
8. allow the 15-minute Cron Trigger to take over.

Do not use Google Tasks' due field as execution time. Its API stores only a date; Google Calendar remains the time-of-day owner.

### P1 — Migrate remaining Notion operational state

Move domains only when their replacement is ready:

- Shopping Needs -> Neon shopping state;
- historical AI Activity Log -> optionally retain in Notion or normalize useful audit metadata into `action_receipts`;
- retire old planning databases only after a rollback window.

### P1 — Live Obsidian bridge

Desired path:

```text
AI/router -> authenticated local adapter -> live vault -> normal vault backup/sync
```

### P1 — Contacts consolidation

Deduplicate Apple + Google Contacts before making Google Contacts canonical.

### P1 — Household operations

Populate `assets`, `maintenance_rules`, `maintenance_events`, `shopping_lists`, and `shopping_items`, then surface actions through the action backend and Calendar when time-specific.

## Scheduling runtime

Current defaults remain:

- sleep 11:00 PM–7:00 AM protected;
- weekday work 9:00 AM–1:00 PM soft-busy;
- movable personal work defaults to 1:00 PM–9:00 PM America/Toronto;
- leave buffer;
- hard commitments are not moved for optimization;
- waiting work does not occupy execution time;
- date-only deadlines/follow-ups remain date-only;
- repeated misses are evidence for replanning, not an instruction to endlessly push work forward.

## Public repository constraint

This repo contains architecture, contracts and schemas only. Never commit actual database URLs, credentials, private task payloads, private contact/relationship details, health records, financial identifiers, confidential work content, or private message bodies.
