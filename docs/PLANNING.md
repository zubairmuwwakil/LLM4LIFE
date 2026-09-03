# Day Planning & Backlog Scheduling

_Last updated: 2026-09-02_

## Purpose

The planning layer should reliably answer:

1. What should I do today?
2. When will important remaining work get done?
3. What is waiting/blocked instead of actually actionable?

## v2 target model

```text
Neon personal actions             Jira engineering backlog
         \                              /
          \                            /
             AI planner / scheduler
                      |
                      v
              Google Calendar
               execution plan

Neon actions -> Google Tasks as preferred human action UI/projection
```

### Ownership

- **Neon/PostgreSQL** — canonical LLM4LIFE personal action state after migration.
- **Google Tasks** — preferred human-facing personal action client/projection.
- **Jira** — canonical engineering backlog/work items.
- **Google Calendar** — commitments and selected execution time blocks.
- **AI layer** — planning/scheduling decisions subject to safeguards.
- **Neon action execution telemetry + adaptive rules** — durable learning model after migration.

Calendar task blocks are projections, not a second task database.

## Transitional runtime

Existing ChatGPT planning automations currently use Notion `Tasks`, `Task Execution Log` and `Scheduling Model`. Those remain live until their Neon equivalents are populated and parity is verified.

Do not disable the existing planning loop merely because this target document changed.

## Action lifecycle

The v2 action model supports:

- `inbox` — captured, not triaged;
- `next` — actionable, unscheduled;
- `scheduled` — has an execution block;
- `waiting` — blocked on an external response/condition;
- `done`;
- `cancelled`;
- `archived`.

Waiting actions should use a follow-up date and should not consume execution time while blocked.

## Planning objective order

Optimize in this order:

1. prevent important things from slipping;
2. save time;
3. reduce mental load;
4. increase useful output.

Do not maximize calendar utilization.

## Scheduling defaults

Unless a newer explicit instruction or strong learned rule overrides them:

- sleep **11:00 PM–7:00 AM** is protected;
- weekday work **9:00 AM–1:00 PM** is soft-busy;
- movable personal/admin/study/deep work defaults to **1:00 PM–9:00 PM America/Toronto**;
- leave buffer;
- fixed external commitments remain fixed;
- due date and execution time are separate fields.

`config/scheduling.yaml` remains the machine-readable baseline for time-window preferences.

## Daily planning loop

### Evening

1. Read fixed Calendar commitments.
2. Read current actionable personal state from the live source (transitional Notion until cutover; Neon after migration).
3. Read Jira and other authoritative signals when relevant/available.
4. Identify overdue, urgent, high-impact, dependency-unblocking and neglected-important work.
5. Exclude blocked/waiting work from execution time.
6. Estimate duration conservatively when absent.
7. Select a realistic amount of tomorrow work.
8. Schedule selected work into open windows.
9. Leave buffer and resolve movable collisions.
10. Keep the unscheduled long tail in the action/backlog owner.

### Morning

The morning run is a sanity/attention check rather than a second full planning system:

- today's top outcomes;
- chronological execution view;
- due/overdue/waiting/at-risk exceptions;
- low-risk conflict fixes where justified.

## Follow-up feedback loop

After a scheduled action block ends, record an execution outcome rather than only mutating Calendar text.

Target outcomes:

- done;
- missed;
- waiting;
- cancelled.

Do not fabricate actual duration. Record it only when genuinely known/reported.

Repeated outcomes feed adaptive scheduling rules with sample size/confidence; they are not psychological truths.

## Adaptive scheduling

The v2 backend supports versioned `adaptive_rules`.

Rules should:

- remain soft preferences;
- include evidence/sample size where practical;
- require repeated evidence before activation;
- preserve superseded/reverted rules for rollback;
- never override explicit instructions or safety constraints.

## Horizon

- **Today/tomorrow:** concrete execution blocks.
- **Next 7 days:** high-confidence important work only.
- **Beyond 7 days:** remain mostly unscheduled unless deadline/lead time warrants reserved time.

## Missed work

When a movable action is missed:

1. reassess whether it still matters;
2. do not blindly move it to tomorrow forever;
3. raise urgency if consequences increased;
4. demote/defer/archive low-value work when evidence supports it;
5. reschedule only into a realistic future slot when still worthwhile;
6. record the execution outcome for learning.

## Calendar hygiene

Prevent:

- overlapping movable blocks;
- duplicate projections;
- stale blocks after completion/cancellation;
- too many small context switches;
- edge-to-edge scheduling without buffer;
- blocked/waiting work reserving time.

Batch compatible errands/calls/online/deep-work tasks when useful.

## Google Tasks projection

The long-term action adapter should synchronize a useful subset of Neon action fields to Google Tasks without forcing Google Tasks to hold the entire domain model.

Required design properties:

- stable mapping through external references;
- idempotent create/update;
- conflict policy;
- completion reconciliation;
- no infinite sync loop;
- clear behavior when Google Tasks API/direct connector is unavailable.

## Success metric

The user can trust that:

- important work has a durable home;
- today is realistic;
- Calendar reflects intended execution rather than backlog storage;
- blocked work is followed up without calendar clutter;
- missed work improves future planning;
- planning state survives chat-thread growth or automation context changes.
