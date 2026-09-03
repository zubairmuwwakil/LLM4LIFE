# Automations

_Last reconciled: 2026-09-02_

This file documents the current live scheduled/conditional automation set and its v2 migration target. Internal task IDs and private account/calendar identifiers are intentionally omitted.

All times use **America/Toronto**.

## Active automation set

| Automation | Schedule | Mode | Current purpose |
|---|---|---|---|
| **Daily Planning Loop** | Daily at 7:30 AM and 7:30 PM | Exact | Morning execution sanity check + evening next-day/rolling-horizon planning |
| **Calendar Task Follow-Up** | Hourly | Condition watch | Capture outcome of recently ended user-owned task-style Calendar blocks and intelligently complete/wait/replan |
| **Weekly Systems Review** | Friday around 5:00 PM | Flexible | Weekly reconciliation, next-week planning, scheduling-learning review, and personal-care/restock review |

Standalone `Plan Tomorrow`, standalone morning digest, personal-care heartbeat and personal-care restock automations have been disabled/merged where appropriate rather than running overlapping responsibilities.

## Current backend vs target backend

### Current transitional runtime

The active prompts currently rely on a combination of:

- Google Calendar;
- Notion Tasks;
- Notion Task Execution Log;
- Notion Scheduling Model;
- Notion Shopping Needs;
- other verified sources such as Jira/GitHub/Gmail/Slack when relevant and available.

This is **runtime truth**, not the long-term ownership decision.

### v2 target

```text
Neon actions / execution telemetry / adaptive rules / shopping state
                             |
                             v
                    planning automations
                             |
                  +----------+----------+
                  |                     |
                  v                     v
            Google Tasks          Google Calendar
             action UI            execution/time
```

The migration must preserve the behavior of the existing loop before removing its Notion dependencies.

## Daily Planning Loop

### Morning run — 7:30 AM

Purpose: final sanity/attention check for today.

Expected output/behavior:

- rank today's three most important outcomes;
- give a concise chronological execution view;
- surface only overdue, due-soon, waiting-follow-up or at-risk exceptions;
- fix low-risk movable conflicts/routing defects when evidence is strong;
- avoid noisy empty sections.

### Evening run — 7:30 PM

Purpose: plan tomorrow and maintain a realistic short horizon.

Expected behavior:

- review unfinished/missed/waiting/newly actionable work;
- choose tomorrow's top outcomes;
- schedule a realistic subset of actionable work;
- resolve obvious movable conflicts;
- preserve buffers;
- deliberately defer low-value work rather than overfilling the day;
- keep waiting work off the execution schedule while blocked.

## Calendar Task Follow-Up

This automation is the feedback loop for scheduled personal actions.

Rules:

- scan a catch-up window so scheduler delays do not create gaps;
- deduplicate aggressively so overlapping checks do not produce duplicate follow-ups;
- exclude external meetings/appointments/travel/fixed commitments;
- recurring-event status edits apply to the **single occurrence**, not the whole series;
- `waiting` is not a scheduling failure;
- never fabricate actual duration;
- reassess value before rescheduling a missed item;
- record execution evidence for later scheduling learning.

Target v2 persistence is `llm4life.action_executions` plus `llm4life.adaptive_rules`.

## Weekly Systems Review

The Friday review combines work that previously existed across separate weekly automations.

It should:

- review completion, misses, repeated deferrals, waiting state and cancelled work;
- inspect upcoming deadlines/commitments and schedule realism;
- plan a realistic subset of next-week work;
- analyze execution evidence by useful context/time windows;
- avoid overfitting small samples;
- include a concise personal-care/restock section;
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
- waiting tasks do not consume execution time;
- due date is distinct from scheduled execution time;
- leave buffer and batch compatible contexts when useful.

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

ChatGPT Automations may remain the execution surface; PostgreSQL supplies durable orchestration state.

## Automation design rules

1. One automation has one clear responsibility.
2. Prefer event-driven triggers when reliable.
3. Do not have multiple automations independently reschedule the same work.
4. Calendar placement belongs to the planning layer.
5. Canonical state is updated before/with projections; do not create shadow databases.
6. Use idempotency and deduplication.
7. Record meaningful execution receipts.
8. Return concise exception-oriented outputs.
9. Do not auto-expand permissions.
10. Purchases, cancellations, money movement, security changes, destructive operations and consequential external messages remain outside standing low-risk approval.
11. GitHub Actions are repository CI/CD infrastructure, not the default personal-life scheduler.
12. Do not disable a working transitional Notion dependency until its v2 replacement has been verified.
