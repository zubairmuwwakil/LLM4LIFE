# Automations

_Last reconciled: 2026-09-02_

This file documents the current live scheduled/conditional automation set. Internal task IDs and private account/calendar identifiers are intentionally omitted.

All times use **America/Toronto**.

## Active automation set

| Automation | Schedule | Mode | Current purpose |
|---|---|---|---|
| **Daily Planning Loop** | Daily at 7:30 AM and 7:30 PM | Exact | Morning execution sanity check + evening next-day/rolling-horizon planning |
| **Calendar Task Follow-Up** | Hourly | Condition watch | Capture outcome of recently ended user-owned task-style Calendar blocks and intelligently complete/wait/replan |
| **Weekly Systems Review** | Friday around 5:00 PM | Flexible | Weekly reconciliation, next-week planning, scheduling-learning review, and personal-care/restock review |

Standalone `Plan Tomorrow`, standalone morning digest, personal-care heartbeat and personal-care restock automations are disabled/merged rather than running overlapping responsibilities.

## Live backend

The planning loop has been cut over to **Neon/PostgreSQL**.

```text
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

Canonical runtime rules:

- `llm4life.actions` owns personal action/backlog state.
- Google Calendar owns execution/time, not backlog truth.
- `action_executions` owns historical completion/miss/waiting evidence.
- `adaptive_rules` contains learned overrides only when evidence actually supports one.
- `action_receipts` records meaningful autonomous writes with idempotent keys.
- Notion Tasks / Task Execution Log / Scheduling Model / AI Activity Log are **rollback/reference only** for migrated planning state.
- Notion Shopping Needs remains transitional for personal-care inventory until that domain is migrated.
- If Neon is unavailable, automations must not silently fall back to writing Notion task state.

## Migration/cutover verification

At cutover:

- 15 Notion task rows were imported as 15 Neon actions;
- 2 execution-log rows were imported as 2 Neon execution rows;
- 15 Notion source references and 13 Google Calendar bindings were preserved;
- source and destination status distributions matched;
- the one status-less legacy record was preserved as `inbox` with migration metadata;
- the old Scheduling Model had no learned overrides, so no artificial adaptive rule was created;
- date-only due/follow-up fields were preserved as date-only columns rather than coerced into fake clock times.

## Daily Planning Loop

### Morning run — 7:30 AM

Purpose: final sanity/attention check for today.

Expected behavior:

- rank today's three most important outcomes;
- give a concise chronological execution view;
- surface overdue, due-soon, waiting-follow-up or at-risk exceptions;
- fix low-risk movable conflicts/routing defects when evidence is strong;
- avoid noisy empty sections.

### Evening run — 7:30 PM

Purpose: plan tomorrow and maintain a realistic short horizon.

Expected behavior:

- review unfinished/missed/waiting/newly actionable work from Neon;
- choose tomorrow's top outcomes;
- schedule a realistic subset of `next` actions;
- update Neon action state and Google Calendar bindings;
- resolve obvious movable conflicts;
- preserve buffers;
- deliberately defer low-value work rather than overfilling the day;
- keep waiting work off the execution schedule while blocked.

### Calendar binding

New scheduled blocks should use an action marker such as:

```text
[LLM4LIFE:ACTION_ID=<uuid>]
```

Existing migrated blocks may still contain:

```text
[LLM4LIFE:TASK_URL] <notion-url>
```

The legacy Notion URL is used only to resolve the corresponding Neon action via `external_refs`; it no longer makes Notion canonical.

## Calendar Task Follow-Up

This automation is the feedback loop for scheduled personal actions.

Resolution order:

1. `ACTION_ID` marker;
2. Google Calendar `external_refs` mapping;
3. legacy Notion URL mapping through `external_refs`;
4. otherwise report an unmapped legacy event rather than invent a relationship.

Rules:

- scan a catch-up window so scheduler delays do not create gaps;
- deduplicate with stable execution keys;
- exclude external meetings/appointments/travel/fixed commitments;
- recurring-event status edits apply to the **single occurrence**, not the whole series;
- `waiting` is not a scheduling failure;
- never fabricate actual duration;
- reassess value before rescheduling a missed action;
- persist execution evidence in `llm4life.action_executions`;
- persist meaningful action/schedule writes in `llm4life.action_receipts`.

## Weekly Systems Review

The Friday review should:

- review completion, misses, repeated deferrals, waiting state and cancelled work from Neon;
- inspect upcoming deadlines/commitments and schedule realism;
- plan a realistic subset of next-week work;
- analyze execution evidence by useful context/time windows;
- avoid overfitting small samples;
- create/update adaptive rules only with enough evidence;
- include a concise personal-care/restock section from transitional Notion Shopping Needs;
- report meaningful learned patterns with evidence/confidence.

Current learning thresholds:

- fewer than 5 comparable observations -> collect only;
- 5–9 -> tentative pattern, no autonomous global default change;
- 10+ -> low-risk learned override may be considered when the effect is meaningful and consistent.

Explicit instructions always override learned rules.

## Scheduling semantics

Current defaults:

- sleep 11 PM–7 AM protected;
- weekday work 9 AM–1 PM soft-busy;
- movable personal work defaults to 1 PM–9 PM;
- Hard items do not move automatically;
- Semi-hard items move only for strong reasons;
- Flexible items may be optimized;
- waiting actions do not consume execution time;
- date-only due/follow-up values remain date-only;
- due date is distinct from scheduled execution time;
- leave buffer and batch compatible contexts when useful.

## Google Tasks

Google Tasks is still the preferred simple **user-facing projection/client**, but it is not canonical state.

No native Google Tasks ChatGPT connector or installable plugin was found during the cutover. The remaining implementation is a thin least-privilege OAuth adapter using the official Google Tasks API.

Desired relationship:

```text
Neon action state -> Google Tasks projection
```

Avoid making Google Tasks and Neon competing bidirectional sources of truth.

## v2 durable job model

`db/migrations/001_core.sql` defines durable `jobs` and `job_runs` tables.

Important automations should eventually have:

- stable job identity;
- trigger/schedule definition;
- idempotent run key;
- execution status/receipt;
- retry/failure policy;
- observability/logging;
- explicit source/destination;
- state that survives chat-thread growth.

ChatGPT Automations may remain an execution surface; PostgreSQL supplies durable orchestration state.

## Automation design rules

1. One automation has one clear responsibility.
2. Prefer event-driven triggers when reliable.
3. Do not have multiple automations independently reschedule the same work.
4. Calendar placement belongs to the planning layer.
5. Canonical state is updated before/with projections; do not create shadow databases.
6. Use idempotency and deduplication.
7. Record meaningful execution receipts.
8. Preserve date-only semantics.
9. Return concise exception-oriented outputs.
10. Do not auto-expand permissions.
11. Purchases, cancellations, money movement, security changes, destructive operations and consequential external messages remain outside standing low-risk approval.
12. GitHub Actions are repository CI/CD infrastructure, not the default personal-life scheduler.
