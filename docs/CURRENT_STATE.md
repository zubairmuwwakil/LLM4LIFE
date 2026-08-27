# Current State

_Last updated: 2026-08-27_

This file describes the current operating model. It is descriptive, not sacred.

## Tool ownership

| Tool | Current responsibility | Explicit non-goals |
|---|---|---|
| GitHub | Code, PRs, commits, releases, repository truth | Personal task management, life database |
| Jira | Engineering bugs, backlog, technical work items | Personal reminders, general notes |
| Things 3 | Personal actions, reminders, next actions | Knowledge base, engineering backlog, structured databases |
| Google Calendar | Time commitments and scheduled events | General task backlog |
| Obsidian | Personal knowledge/context layer: thinking, learning, durable notes, daily/diary context, PARA Areas/Projects/Resources, spaced repetition, mistake logs | Routine task management, structured operational state better owned by Notion, duplicate GitHub content |
| Notion | Structured life state and personal operations | Duplicate Jira/GitHub state, deep notes, duplicate finance app state |
| Slack | Work/software-engineering communication and work notification surface | Long-term task source of truth |
| Discord | Personal communication and personal notification surface | Long-term task source of truth |
| Gmail | Email intake and source context | Final home for actions that belong elsewhere |

## AI layer

The user wants an AI/LLM with access to as much of the system as practical so they can interact through a low-friction conversational interface.

Current conceptual roles:

- **ChatGPT** — primary command interface and native connected-tool surface where useful.
- **Claude** — strong coding-focused agent, especially for code work.
- **OpenClaw** — candidate integration/channel plumbing where native integrations are insufficient, particularly for reaching the AI from multiple surfaces.

These roles are not exclusive and should be revisited as capabilities change.

## Anywhere capture

Desired entry points include:

- ChatGPT
- Slack
- Discord
- iPhone Shortcuts / Share Sheet
- email forwarding/intake
- browser capture

The user should not need to decide which destination app to open before expressing intent. The AI/router should classify and send the item to the correct system.

## Obsidian reality check

The private `zubairmuwwakil/Obsidian` repository is the backed-up Obsidian vault and should be consulted when deeper personal knowledge/context is needed.

The vault is a PARA-style personal knowledge base with roughly 1,090 notes. Its current lifecycle is:

`00 Inbox -> 10 Daily -> 20 Areas / 30 Projects / 50 Resources -> 90 Archive`

It also contains derived dashboards, Maps of Content, templates, software-engineering learning material, spaced-repetition prompts, and a formal AI learning contract.

Important vault rules that align with LLM4LIFE:

- **One home per item. Link instead of copying.**
- Obsidian may link to GitHub or Notion when those systems are canonical.
- GitHub owns doing/showing (code, project artifacts, public TILs); Obsidian owns remembering/reasoning (concept notes, learning prompts, mistake logs).
- For software-engineering learning work, agents must follow the vault's own `AGENTS.md` and canonical `AI Operating Manual (READ ME).md`.
- The learning contract is intentionally less frictionless than the general life-automation layer: AI should promote retrieval/generation rather than simply provide finished answers when the goal is learning.

The presence of an Area, Project, subscription note, or finance note in Obsidian does **not automatically make Obsidian the operational source of truth** for that object. Obsidian is allowed to hold context, reasoning, narrative, and links while structured live state remains in the appropriate system.

An older imported note in the vault used the shorthand `Discord for attention; Notion for record; Things for work`. Treat that as historical context, not current global policy when it conflicts with newer LLM4LIFE decisions.

## Notion conclusion

After inspecting the Notion workspace, active code repositories, and the Obsidian vault, the current conclusion remains:

> Notion's highest-value role is Personal Operations / Life Database.

Why:

1. Engineering repositories already keep substantial implementation plans, research, compliance material, architectural decisions, tests, and source truth next to code.
2. Jira already owns engineering work tracking.
3. Dedicated finance applications own transaction/state/calculation logic.
4. Obsidian already provides the deep personal knowledge/context layer.
5. Notion is strongest where durable structured personal/admin state benefits from databases, relations, views, and AI retrieval.

Good Notion examples:

- personal-care and household inventory
- shopping thresholds
- subscriptions and memberships
- benefits and cancellation instructions
- important documents and expiration dates
- warranties
- property/vehicle/insurance metadata
- loyalty programs
- administrative contacts/vendors
- AI activity log

### Existing evidence

The existing personal-care system is a good example of useful Notion design: product records, counts, shopping needs, and usage events form structured state that can generate actions elsewhere.

The generic Projects Hub appears lower-value because engineering projects already have stronger authoritative systems and the Notion project database is sparsely used.

## Finance boundary

Dedicated financial applications should own:

- transactions
- balances
- net worth
- cashflow calculations
- credit-card recommendation logic
- financial forecasting

Notion can still hold administrative metadata such as:

- membership/subscription notes
- cancellation instructions
- benefits/reference information
- non-calculated administrative records

Obsidian may hold financial reasoning, research, or contextual notes, but it should link to the canonical operational/financial record rather than duplicate live state.

## Communication boundary

- Slack = work/software-engineering communication.
- Discord = personal/life communication.

Messages may create actions, but the conversation itself should not become the long-term task manager.

When a message implies work:

- engineering work -> Jira
- personal action -> Things 3
- time commitment -> Calendar when appropriate
- durable knowledge/context -> Obsidian
- structured state -> Notion

## Current audit log

A Notion database named **AI Activity Log** has been created under the existing Tooling Workflow area.

It is intended to record meaningful autonomous writes/actions with fields for source, destination, action type, status, timestamp, links, details, errors, and reversibility.

It should be machine-maintained rather than manually curated.
