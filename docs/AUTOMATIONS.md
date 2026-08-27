# Automations

_Last verified: 2026-08-27_

This file documents the **active automation layer** around LLM4LIFE. It intentionally omits internal task IDs; names and behavior are the stable interface.

All times below use **America/Toronto** unless stated otherwise.

## Active automations

| Automation | Schedule | Mode | Purpose | Main systems | Current policy |
|---|---|---|---|---|---|
| **Plan Tomorrow** | Daily around 7:00 PM | Flexible | Build tomorrow's realistic execution plan and maintain a short 7-day horizon | Calendar + available backlogs/sources | Schedule movable work primarily 1–9 PM; leave buffer; do not move fixed commitments |
| **Daily Systems Digest** | Daily around 8:00 AM | Flexible | Morning attention brief and final schedule sanity check | Calendar, Gmail, GitHub, Notion, Slack, Jira when available, other connected sources | Top 3 + schedule health + exceptions + neglected work + system gaps + ROI + actions taken |
| **Calendar Task Follow-Up** | Hourly | Condition watch | Check task/reminder-style Calendar blocks that ended about an hour ago and ask whether they were completed | Google Calendar | If unfinished, reassess and place in a realistic 1–7 day window within 1–9 PM rather than blindly pushing one day |
| **Personal Care Heartbeat** | Tuesday around 7:00 PM | Flexible | Brief weekly personal-care inventory status | Notion | Read-only; always reports inventory health |
| **Personal Care Restock** | Friday around 7:00 PM | Flexible | Full practical shopping/restock digest | Notion | Read-only; groups active restock needs by urgency |

## Daily planning lifecycle

```text
Canonical backlog/state
  Things 3 (personal)      Jira (engineering)
  Gmail / Notion / GitHub signals
              |
              v
      Plan Tomorrow (~7 PM)
              |
              v
     Google Calendar plan
     movable work: 1–9 PM
              |
              v
 Daily Systems Digest (~8 AM)
      sanity check / adjust
              |
              v
          execution
              |
              v
Calendar Task Follow-Up (~1h after task blocks)
        complete / reassess
              |
              +----> future realistic slot if still valuable
```

## Plan Tomorrow

Primary responsibilities:

1. inspect fixed Calendar commitments and existing task blocks;
2. inspect authoritative backlog/action sources that are actually connected;
3. never claim Things/Jira was inspected if the connector was unavailable;
4. rank work by urgency, consequence of delay, impact, dependencies, neglect, effort, available windows, batching, and observed behavior;
5. schedule a realistic amount of movable work inside **1:00 PM–9:00 PM** by default;
6. leave buffer;
7. resolve movable-task collisions;
8. keep lower-confidence future work in its canonical backlog;
9. maintain at most a short 7-day high-confidence horizon;
10. log meaningful autonomous schedule changes when the audit log is available.

## Daily Systems Digest

The morning digest should be an **attention surface**, not a second planning database.

Current sections:

- Top 3 priorities for today
- Schedule health
- Needs attention today
- Work / engineering
- Personal / admin
- Upcoming deadlines
- Neglected but important
- What can be ignored today
- Cleanup performed
- Learned preferences
- System gaps
- Tool ROI opportunities
- Automated actions taken

It may autonomously fix low-risk movable scheduling problems. It must not move/cancel fixed external commitments merely to make the calendar cleaner.

## Calendar Task Follow-Up

This is feedback for the planner, not a separate task system.

Workflow:

```text
movable task block ends
        |
~1 hour later
        v
ask: completed?
  |             |
yes             no
  |             |
mark completed  mark undone
                |
                v
       reassess current value
                |
       still worth doing?
          |          |
         yes         no
          |          |
 next realistic     stop blind
 1–7 day slot       rescheduling
```

Repeated misses are behavioral evidence for duration, priority, and scheduling heuristics.

## Personal-care automations

These use Notion as the canonical structured inventory layer.

They are deliberately narrow:

- **Heartbeat** gives a compact health signal.
- **Restock** produces the actual shopping-oriented list.
- Neither should create a duplicate inventory database elsewhere.

## Retired / cleaned automations

Two duplicate one-time reminders named **Fix Discord channel ID warning** had already fired in January 2026 and were still enabled. They were disabled on 2026-08-27 as stale automation clutter.

A completed one-time **Gemini Plan Reset** reminder is inactive and is not part of the active operating system.

## Automation design rules

1. **One automation = one clear responsibility.**
2. Do not use a recurring task when an event-driven signal is available and reliable.
3. Do not create overlapping automations that both reschedule the same work independently.
4. Planning automation owns movable Calendar placement.
5. Domain automations should update/read the canonical source, not create shadow databases.
6. Deduplicate before writing.
7. Log meaningful autonomous writes when practical.
8. Return concise receipts or exception reports, not verbose routine success logs.
9. Do not auto-expand permissions.
10. Purchases, cancellations, money movement, security changes, consequential external messages, destructive actions, and other hard-to-reverse actions remain outside standing low-risk approval.

## Change procedure

When an active automation changes materially:

1. update this file;
2. update `config/automations.yaml`;
3. update the relevant policy doc (`PLANNING.md`, `DIGEST.md`, etc.);
4. log the rationale in a decision record when the architecture/behavior meaningfully changes;
5. if it changes live scheduling or routing, note the change in `docs/STATUS.md`.
