# Runtime Status

_Last updated: 2026-09-03_

This file describes **what is actually live now**. Target ownership is defined by `config/domains.yaml` and `system.yaml`.

## Headline

The v2 Neon backend is live, personal action/planning state is canonical in Neon, and the Google Tasks projection/client is **production-live on Worker v0.2.0** through Cloudflare.

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
- Google Tasks OAuth completed and Cloudflare Worker deployed;
- first Google Tasks bulk projection completed successfully after one safe retry;
- Google Tasks Worker v0.2.0 deployed and manually verified;
- v0.2.0 15-minute Cloudflare cron independently verified succeeding;
- InUnity ChatGPT MCP integration completed and recently read-verified.

## Canonical planning runtime

```text
                           +--> Google Tasks
                           |    human action client
                           |
Neon/PostgreSQL actions ---+
        |                  |
        |                  +<-- Cloudflare Worker v0.2.0
        |                       15-minute sync
        |
        +--> ChatGPT planner --> Google Calendar
                                  execution/time
```

### Current ownership

- **Neon `llm4life.actions`** -> canonical personal action/backlog state.
- **Google Tasks** -> live human-facing action client and authorized capture/completion surface; not canonical state.
- **Cloudflare Worker** -> live Google Tasks <-> Neon projection/sync runtime.
- **Google Calendar** -> execution schedule and fixed time commitments.
- **Neon `action_executions`** -> scheduling/execution telemetry.
- **Neon `adaptive_rules`** -> learned scheduling overrides; currently empty until evidence justifies a rule.
- **Neon `action_receipts`** -> meaningful autonomous-action audit metadata.
- **Notion Tasks / Task Execution Log / Scheduling Model / AI Activity Log** -> rollback/reference only for migrated planning state.
- **Notion Shopping Needs** -> still transitional for personal-care inventory until that domain is migrated.
- **InUnity** -> canonical consolidated finance application; ChatGPT MCP integration is implemented and has been exercised successfully.

## Google Tasks production state

The live Worker is deployed as `llm4life-google-tasks-sync` with a `*/15 * * * *` Cron Trigger.

Verified production state:

- Worker health reports `version: 0.2.0`;
- 17 Neon actions total;
- 14 Google Tasks projection bindings in `external_refs`;
- both `google_tasks_tasklist` and `google_tasks_projection` checkpoints present;
- `google-tasks-sync` job enabled;
- v0.2.0 manual sync succeeded with zero conflicts or duplicate writes;
- a subsequent v0.2.0 scheduled cron also succeeded;
- latest `job_runs.metadata` and the projection checkpoint record `worker_version: 0.2.0`.

The first v0.1 bulk projection exceeded Cloudflare Workers Free's 50 external-subrequest limit after partially completing safely. The retry completed the remaining work because stable external references made the process idempotent.

### v0.2 hardening — production-live

Worker v0.2.0 addresses the first-run scaling issue by:

- grouping Neon SQL with `sql.transaction(...)` so many statements share one database HTTP fetch;
- batching Google Tasks create/patch/delete mutations through the Google Tasks multipart batch endpoint, up to 50 mutations per Google batch request;
- using the previous projection checkpoint as `updatedMin` for incremental Google reads after the initial snapshot;
- adding a five-minute overlap window to avoid timestamp-boundary misses;
- using external-ref push metadata to decide when a Neon change needs to be patched to Google without rereading every Google task;
- handling cancelled/archived projection deletion directly in the core worker;
- retaining idempotent run keys, external refs, checkpoints, and action receipts.

No database schema migration was required for v0.2.

## Active planning automations

The following live automations use Neon canonical action state:

1. **Daily Planning Loop** — 7:30 AM + 7:30 PM.
2. **Calendar Task Follow-Up** — hourly condition watch.
3. **Weekly Systems Review** — Friday around 5 PM.

Legacy Calendar events remain compatible:

- new blocks use `[LLM4LIFE:ACTION_ID=<uuid>]` where possible;
- existing `[LLM4LIFE:TASK_URL] <notion-url>` markers may still resolve through `external_refs`;
- the Notion record is an identifier/rollback source, not canonical task state.

If Neon is unavailable, automations are instructed **not** to silently fall back to Notion writes.

## Google Tasks sync contract

- New tasks created in the dedicated `LLM4LIFE` list may be captured as Neon `inbox` actions.
- Completing a Google Task may mark the corresponding Neon action `done`.
- Reopening a projected task may return the Neon action to `next`.
- Safe title/date edits can be ingested when Neon did not independently change.
- Conflicts preserve Neon as canonical and record a receipt.
- Deleting a Google Task never deletes the Neon action; it disables the projection.
- Cancelled/archived Neon actions are removed from the Google projection.
- Google Tasks due values are date-only; time-of-day execution remains in Google Calendar.

## Runtime paths

| System | Runtime status | Current role / limitation |
|---|---|---|
| GitHub | Connected, read/write verified | Architecture/config/code repository operations |
| Neon | **Connected / canonical personal action backend** | Production schema and action state live; read/write verified |
| ChatGPT Automations | Connected/live | Planner/follow-up/review use Neon canonical task state |
| Google Tasks | **Production-live v0.2.0** | Human action client/projection; Neon remains canonical |
| Cloudflare | **Production-live Worker runtime** | v0.2.0 sync every 15 minutes; ChatGPT app enabled but this session does not expose its namespace |
| Google Calendar | Connected | Execution schedule and commitments |
| Notion | Transitional / rollback for planning | Planning snapshot retained; Shopping Needs still live until migrated |
| InUnity | **MCP integration complete / recently read-verified** | Consolidated finance system; re-check namespace before a live call when needed |
| Gmail | Connected capability | Email/source context and supported actions |
| Slack | Connected capability | Work communication/context |
| Google Contacts | Connector available; migration not done | Preferred canonical address book after Apple/Google dedup |
| Apple Contacts | User-live | Still contains part of contact identity; intended to become synced client |
| Obsidian | Partial | GitHub-backed vault accessible; trusted live local-vault bridge remains unimplemented |
| Jira / Atlassian | Connector available; verify per task | Canonical engineering backlog |
| ORC | External subsystem | Coding-agent orchestrator |
| Discord / WhatsApp / iMessage | User-live channels | Cross-channel AI access still requires verified bridge/native integration |

## Next implementation priorities

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

This repo contains architecture, contracts and schemas only. Never commit actual database URLs, OAuth credentials, refresh tokens, private task payloads, private contact/relationship details, health records, financial identifiers, confidential work content, or private message bodies.
