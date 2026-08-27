# Day Planning & Backlog Scheduling

_Last updated: 2026-08-27_

## Purpose

The user wants the system to answer two questions reliably:

1. **What should I do today?**
2. **When will the rest of my backlog actually get done?**

The planning layer should convert obligations and backlog into a realistic calendar without turning Google Calendar into the permanent task database.

## Canonical model

```text
Things 3 / Jira / other authoritative sources
                |
                v
         AI planning layer
   priority + effort + constraints
                |
                v
        Google Calendar
       execution schedule
```

### Ownership

- **Things 3** owns the personal backlog and next actions.
- **Jira** owns engineering backlog/work items.
- **Google Calendar** owns the current execution plan: appointments, commitments, deadlines, and time blocks selected for actual execution.
- **AI** decides what should move from backlog into time, subject to safeguards and available integrations.

Calendar events created from tasks are **scheduled representations**, not a second canonical copy of the task.

## Planning objective order

Optimize in this order:

1. prevent important things from slipping through the cracks;
2. save time;
3. reduce mental load;
4. increase output.

Do not maximize calendar utilization. A completely full calendar is fragile.

## Default scheduling window

For **movable personal tasks, errands, study blocks, routine admin, and movable deep work**, the default scheduling window is:

- **1:00 PM–9:00 PM America/Toronto**

Rules:

- Do not schedule movable work outside this window by default.
- Fixed commitments such as appointments, meetings, travel, or externally required times may exist outside the window and should be preserved.
- A specific newer instruction for a task or day may override this default.
- Keep buffer inside the 1–9 PM window rather than trying to occupy every minute.
- The machine-readable source for this preference is `config/scheduling.yaml`.

## Daily planning loop

### Evening planning

Each evening, prepare the next day and maintain a short future horizon.

1. Read fixed commitments and existing calendar blocks.
2. Read available authoritative backlogs and actionable inputs.
3. Identify overdue, urgent, high-impact, dependency-unblocking, and neglected-but-important work.
4. Estimate a reasonable duration when one is not available; use conservative defaults and learn from actual completion behavior.
5. Select a realistic amount of work for tomorrow.
6. Place selected work into open calendar windows, normally within the default 1:00 PM–9:00 PM movable-work window.
7. Leave buffer; do not pack the day edge-to-edge.
8. Detect overlaps and impossible schedules.
9. Push lower-priority work forward rather than creating collisions.
10. Keep unscheduled backlog in its canonical task system.

### Morning check

The morning digest acts as the final execution check:

- show the Top 3 outcomes for the day;
- flag calendar collisions or unrealistic load;
- surface anything important that appeared after the evening plan;
- identify what can safely be ignored today.

## Scheduling rules

### Fixed vs movable

**Fixed:** appointments, meetings, flights, externally committed times, deadlines with a required clock time.

**Movable:** personal/admin tasks, errands, study blocks, deep work, routine reviews, self-imposed work blocks.

Never move a fixed commitment merely to make the plan prettier.

### Priority signals

Consider:

- hard deadline / time sensitivity;
- consequence of delay;
- dependency value;
- impact;
- age / neglect;
- effort and available window;
- location/context constraints;
- batching opportunities;
- observed completion behavior;
- repeated deferral or manual override.

### Backlog horizon

The system should maintain a rolling schedule, not attempt to calendar every possible someday item.

Recommended behavior:

- **Today/tomorrow:** concrete execution blocks.
- **Next 7 days:** schedule high-confidence important work where useful.
- **Beyond 7 days:** keep most tasks in the backlog unless there is a deadline, appointment, preparation lead time, or strong reason to reserve time.

## Rescheduling

When a movable task is missed:

1. determine whether it still matters;
2. avoid blindly moving it to the next day forever;
3. raise its priority if delay has growing consequences;
4. lower/archive it if repeated deferral indicates low value and evidence supports that conclusion;
5. place it in the next realistic window if still worthwhile.

Repeated rescheduling is behavioral evidence and may tune future duration/priority estimates under `docs/ADAPTATION.md`.

## Calendar hygiene

The planning system should actively prevent:

- overlapping movable tasks;
- duplicate task blocks;
- calendar blocks with no clear action;
- too many tiny context switches;
- full-day schedules with no buffer;
- stale task blocks that remain after the underlying task is completed or abandoned.

Prefer batching similar errands/admin tasks when practical.

## Things 3 integration constraint

Things 3 is the intended canonical personal backlog, but the current connected AI environment may not have direct server-side Things access.

Until a supported bridge exists:

- never pretend the Things backlog was inspected when it was not;
- use connected sources that are available;
- treat a Things bridge as a high-priority integration gap;
- preferred bridge options remain Apple Shortcuts, Things URL scheme, AppleScript on macOS, or another thin deterministic adapter using supported interfaces.

Once the bridge exists, the planning layer should be able to:

- read eligible backlog items;
- schedule selected tasks on Calendar;
- preserve a link/reference to the Things item when possible;
- mark/complete/reschedule through supported Things interfaces;
- avoid maintaining a duplicate task database in Calendar or Notion.

## Autonomy

Scheduling and rescheduling **movable, low-risk personal work** is pre-approved when the AI has enough information and the operation is reversible.

Do not autonomously move/cancel:

- external meetings or appointments;
- travel bookings;
- legal/financial commitments;
- other externally consequential fixed commitments.

## Success metric

A successful planning layer means the user can mostly trust:

- today is already realistic when they wake up;
- important work has a future home;
- missed work is intelligently replanned;
- the calendar reflects intention without becoming the permanent backlog;
- they do not need to manually hunt across apps to decide what to do next.
