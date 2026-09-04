# Home, Utilities & Household Inventory

**Status:** Provisional / subject to change  
**Purpose:** Record current household providers and define a scalable personal-operations model for groceries, household maintenance, vehicle maintenance, and recurring home obligations.

## Current providers and surfaces

| Area | Current system | Provisional direction |
|---|---|---|
| Internet | EBOX | Keep for now; provider choice is operational/cost-driven and can change independently of LLM4LIFE architecture |
| Mobile carrier | Freedom Mobile | Keep for now; evaluate periodically based on price, coverage, roaming, and integration value |
| Water utility | Durham Region water billing | Treat provider as authoritative for billing/service; LLM4LIFE may track due dates, costs, and documents but should not duplicate provider records |
| Home security / smart home | Google Home | Keep as an edge/control surface for now; evaluate against other smart-home options only if there is a concrete reliability/integration benefit |
| Grocery / shopping list | No dedicated canonical system today | Create a dedicated personal-operations domain rather than forcing groceries into Notes, Calendar, or an ad-hoc chat history |
| Household maintenance | No dedicated system today | Create structured assets + maintenance schedules + generated tasks/reminders |
| Vehicle maintenance | No dedicated system today | Create structured vehicle maintenance records/schedules; execution reminders flow to tasks/calendar as appropriate |
| Package / delivery tracking | Amazon and provider-specific delivery surfaces | Keep provider apps as execution/status sources; only normalize delivery state into LLM4LIFE if automation value justifies it |

## Production-grade household model

The long-term design should separate **durable household state** from **execution surfaces**.

```text
                LLM4LIFE personal operations
                         |
                 Neon / PostgreSQL
                         |
       +-----------------+------------------+
       |                 |                  |
    groceries       household assets     vehicle assets
 / shopping list     + maintenance       + maintenance
       |                 |                  |
       +-------- due/action generation -----+
                         |
                  Google Tasks
                         |
             if time-specific/appointment
                         |
                  Google Calendar
```

### Groceries / shopping

Recommended canonical model: a small structured list in the LLM4LIFE backend rather than a dedicated paid app.

Potential fields:
- item
- quantity
- category/store section
- preferred store
- recurring/default item flag
- added_at
- purchased_at
- notes
- optional target store or price context

This allows conversational actions such as:
- "add coffee syrup to groceries"
- "what do I still need from Costco?"
- "mark milk and eggs purchased"
- "show recurring groceries I haven't bought recently"

The exact user-facing surface can remain flexible. Google Tasks may be used as a projection/checklist when useful, but should not be forced to carry richer grocery metadata.

### Household maintenance

Recommended canonical objects:
- household_asset (HVAC/filter/appliance/smoke detector/etc.)
- maintenance_rule
- last_completed_at
- next_due_at or recurrence rule
- notes/manual link
- cost/history where useful

A scheduler generates a Google Task when maintenance becomes due. Calendar is used only when a task requires a real appointment or dedicated time block.

### Vehicle maintenance

Use the same pattern with vehicle-specific fields:
- vehicle
- maintenance_type
- mileage interval and/or time interval
- last service date
- last service odometer
- next due date / odometer threshold
- service provider
- cost / receipt reference

Do not depend on remembering maintenance through chat history alone.

## Architectural principles

1. Provider apps remain authoritative for provider-specific execution and official account/service records.
2. LLM4LIFE owns normalized personal operational state that provider apps do not manage well across domains.
3. Google Tasks is an execution surface for actionable work, not the complete household database.
4. Google Calendar is for appointments/time commitments, not every maintenance obligation.
5. Prefer free/already-paid-for components. Do not add a paid household-management app unless it provides a clearly superior capability that cannot reasonably be built from the existing stack.
6. Current providers are replaceable when price, reliability, integration, or long-term architecture justifies switching.

## Implementation follow-up after inventory

- Add grocery/shopping-list tables and commands to the LLM4LIFE backend.
- Add generic asset + maintenance-schedule modeling that can support home and vehicle assets without separate bespoke schedulers.
- Build due-action generation into Google Tasks.
- Add Calendar events only for actual appointments or explicitly scheduled work blocks.
- Define a simple capture path from ChatGPT/Shortcuts for "add grocery item," "record maintenance," and "remind me when due."
- Periodically audit providers (internet/mobile/security) for cost and reliability, but keep provider-shopping logic separate from canonical household state.
