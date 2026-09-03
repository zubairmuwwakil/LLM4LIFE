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
- live Daily Planning Loop, Calendar Task Follow-Up, and Weekly Systems Review prompts cut over to Neon canonical task state.

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

### Current ownership

- **Neon `llm4life.actions`** -> canonical personal action/backlog state.
- **Google Calendar** -> execution schedule and fixed time commitments.
- **Neon `action_executions`** -> scheduling/execution telemetry.
- **Neon `adaptive_rules`** -> learned scheduling overrides; currently empty until evidence justifies a rule.
- **Neon `action_receipts`** -> meaningful autonomous-action audit metadata.
- **Notion Tasks / Task Execution Log / Scheduling Model / AI Activity Log** -> rollback/reference only for migrated planning state; live planning automations must not write them as canonical state.
- **Notion Shopping Needs** -> still transitional for personal-care inventory until that domain is migrated.

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

## Runtime paths

| System | Runtime status | Current role / limitation |
|---|---|---|
| GitHub | Connected, read/write verified | Architecture/config/code repository operations |
| Neon | **Connected / canonical personal action backend** | Production schema and migrated action state are live; read/write path verified |
| ChatGPT Automations | Connected/live | Planner/follow-up/review now point at Neon canonical task state |
| Google Calendar | Connected | Execution schedule and commitments |
| Notion | Transitional / rollback for planning | Planning snapshot retained for rollback/reference; Shopping Needs still live until migrated |
| Google Tasks | Target client, integration pending | Preferred user-facing personal-action projection; no native ChatGPT/installed plugin was found in the current environment, so an OAuth adapter is still required |
| Gmail | Connected capability | Email/source context and supported actions |
| Slack | Connected capability | Work communication/context |
| Google Contacts | Connector available; migration not done | Preferred canonical address book after Apple/Google dedup |
| Apple Contacts | User-live | Still contains part of contact identity; intended to become synced client |
| Obsidian | Partial | GitHub-backed vault accessible; trusted live local-vault bridge remains unimplemented |
| Jira / Atlassian | Connector available; verify per task | Canonical engineering backlog |
| ORC | External subsystem | Coding-agent orchestrator |
| Discord / WhatsApp / iMessage | User-live channels | Cross-channel AI access still requires verified bridge/native integration |

## Next implementation priorities

### P0 — Google Tasks projection adapter

Google Tasks remains the preferred simple action UI, but no native ChatGPT connector/plugin is available in the current runtime.

Implement a thin adapter using the official Google Tasks API with least-privilege OAuth. Neon remains canonical; Google Tasks is a projection/client. Avoid long-term bidirectional ambiguity.

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
