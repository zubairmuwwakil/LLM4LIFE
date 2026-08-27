# Daily Systems Digest

_Last updated: 2026-08-27_

A daily cross-system digest is enabled for approximately **8:00 AM America/Toronto**.

The digest is the **morning attention and schedule-sanity surface**. It is not the permanent task backlog and it is not where the whole day should be planned from scratch.

The evening `Plan Tomorrow` automation prepares the initial plan; the digest checks whether that plan is still realistic.

See `docs/AUTOMATIONS.md`.

## Purpose

The digest should answer:

1. What are the three most important outcomes today?
2. Is today's Calendar realistic?
3. What changed overnight?
4. What is becoming neglected?
5. What can safely be ignored?
6. What did automation already handle?
7. Are any important systems/workflows missing?
8. Are any tools/services creating poor ROI?

The goal is **less cognitive load and fewer dropped obligations**, not more notifications.

## Current sections

### Top 3 priorities for today

Rank across available connected systems using:

- urgency
- impact
- consequence of delay
- dependencies/blockers
- time sensitivity
- observed behavior
- current Calendar reality

Do not manufacture confidence from unavailable sources. If Things/Jira is not connected, say so when that materially weakens the ranking.

### Schedule health

Inspect today's Google Calendar for:

- overlapping movable task blocks;
- unrealistic workload;
- task blocks outside the default movable window without an explicit reason;
- stale/missed movable task blocks;
- high-priority work with no realistic execution window;
- missing buffer / excessive context switching.

Default movable-work window: **1:00 PM–9:00 PM America/Toronto**.

The digest may autonomously repair low-risk movable scheduling problems.

It must not move/cancel fixed meetings, appointments, travel, legal/financial commitments, or other consequential fixed events merely to optimize the schedule.

### Needs attention today

Important exceptions or actions that should not be buried inside category summaries.

### Work / engineering

Relevant GitHub, Jira (when available), Slack, CI/build/release, or engineering changes.

Jira remains canonical for engineering backlog even when direct Jira connectivity is unavailable.

### Personal / admin

Relevant personal actions, email/admin state, household/life operations, errands, and similar items.

Things 3 remains the canonical personal backlog. The digest must not pretend to have inspected Things when no bridge is available.

### Upcoming deadlines

Time-sensitive upcoming commitments, due dates, renewals, expiries, and preparation lead-time risks.

### Neglected but important

Resurface meaningful items that have gone stale, especially roughly **7–14+ days** without progress.

Do not resurrect clutter merely because it is old.

### What can be ignored today

Explicitly identify low-value, non-urgent, duplicative, or safely deferrable work.

Protecting attention is a first-class output. The system should reduce work, not merely rank an ever-growing pile.

### Cleanup performed

Report low-risk reversible cleanup that automation performed.

Examples:

- resolved duplicate task blocks;
- archived stale low-value material where safe;
- removed redundant automation clutter;
- simplified a noisy low-risk workflow.

### Learned preferences

Only show this section when there is a meaningful new behavioral pattern or a material low-risk rule adjustment.

Potential evidence:

- repeated deferrals;
- unusually quick completions;
- repeated manual priority overrides;
- recurring routing corrections;
- repeated scheduling misses;
- duration estimates consistently wrong in the same direction.

Learned behavior remains a **soft preference**, not a safety or urgency override.

### System gaps

Look for important recurring/consequential domains with no reliable:

- canonical owner;
- trigger;
- durable record;
- follow-up;
- retrieval workflow.

Before building anything:

1. verify the problem is recurring or meaningful;
2. check existing canonical systems;
3. reuse an existing capability first;
4. design the smallest useful workflow;
5. implement automatically only when low-risk, reversible, and already authorized.

See `docs/GAP_DETECTION.md`.

### Tool ROI opportunities

Evidence-driven options may include:

- cancel;
- downgrade;
- consolidate;
- replace;
- add an integration/tool only when it clearly removes friction or fills a real capability gap.

Prefer extracting more value from existing tools before adding another subscription.

For each recommendation, state:

- concrete benefit;
- what it replaces/improves;
- evidence supporting the recommendation.

Safe/reversible workflow improvements within existing access are pre-approved. Purchases, subscriptions, cancellations, financial actions, new permissions, and other consequential changes are not.

### Automated actions taken

Summarize meaningful autonomous actions already completed.

Do not dump the full audit log.

## Morning scheduling behavior

The digest should treat the Calendar as an **execution schedule**, not the backlog.

When movable work is overloaded or colliding:

1. preserve fixed commitments;
2. protect the highest-value outcomes;
3. leave buffer;
4. move/defer lower-priority movable work;
5. keep unscheduled tasks in their real backlog rather than endlessly calendaring everything.

If an unfinished task has already been picked up by `Calendar Task Follow-Up`, avoid creating another duplicate reschedule.

## Noise controls

- deduplicate repeated signals;
- prioritize exceptions over routine success;
- include direct links/IDs when useful and safe;
- omit empty sections when that improves readability;
- do not repeat the same low-value warning every day;
- if nothing important happened, say so briefly.

## Runtime access rule

The digest should use only sources that are actually connected during that run.

Current runtime status is documented in:

- `docs/STATUS.md`
- `docs/TOOL_REGISTRY.md`
- `config/tools.yaml`

If a canonical source is unavailable, the digest may still make a best-effort plan from available data, but it should flag the limitation when material.

## Relationship to the AI Activity Log

The digest is the **human attention surface**.

The Notion AI Activity Log is the **audit surface**.

Do not dump the complete activity log into the digest. Summarize only what changes decisions or attention.
