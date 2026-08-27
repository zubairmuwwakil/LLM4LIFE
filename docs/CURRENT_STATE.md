# Current State

_Last updated: 2026-08-27_

This file is the narrative description of the current operating model. It is descriptive, not sacred.

For exact runtime/connectivity status, use `docs/STATUS.md`. For the complete tool matrix, use `docs/TOOL_REGISTRY.md`.

## Current operating model

```text
User expresses intent anywhere practical
             |
             v
        AI router/planner
             |
   +---------+---------+----------------+
   |         |         |                |
 action   engineering knowledge       structure
   |         |         |                |
 Things    Jira     Obsidian          Notion
   \         /                           |
    \       /                            |
     AI selects execution work           |
             |                            |
             v                            |
       Google Calendar <-----------------+
        execution schedule
```

Communication/source surfaces:

- Slack -> work/software-engineering communication
- Discord -> personal/life communication
- Gmail -> email intake/source context
- GitHub -> code/repository truth

## Tool ownership

| Tool | Current responsibility | Explicit non-goals |
|---|---|---|
| GitHub | Code, PRs, commits, releases, repository truth, LLM4LIFE policy | Personal task management, life database |
| Jira | Engineering bugs, backlog, technical work items | Personal reminders, general notes |
| Things 3 | Personal backlog, actions, reminders, next actions | Knowledge base, engineering backlog, structured life database |
| Google Calendar | Fixed time commitments and the current execution schedule | Permanent general task backlog |
| Obsidian | Personal knowledge/context: reasoning, learning, durable notes, PARA context, daily/diary, research, retrieval prompts, mistake logs | Routine task management, structured operational state better owned by Notion, duplicate GitHub content |
| Notion | Structured life state, personal operations, inventories/admin metadata, AI Activity Log | Duplicate Jira/GitHub state, deep knowledge, duplicate finance-engine state |
| Slack | Work/software-engineering communication and desired work notification surface | Long-term task source of truth |
| Discord | Personal/life communication and desired personal notification surface | Long-term task source of truth |
| Gmail | Email intake and source context | Final home for actions/state that belong elsewhere |
| AI layer | Routing, planning, orchestration, attention management | Becoming another canonical database |

## Day planning is now first-class

The largest day-to-day workflow is:

```text
Things 3 personal backlog       Jira engineering backlog
             \                        /
              \                      /
                AI planner/scheduler
                       |
                       v
                Google Calendar
                 execution plan
```

Current default:

- movable personal/admin/study/deep-work blocks: **1:00 PM–9:00 PM America/Toronto**;
- leave buffer;
- plan tomorrow in the evening;
- sanity-check the plan in the morning;
- use a short 7-day high-confidence horizon;
- keep the long tail in the real backlog;
- treat missed work as evidence and reassess it instead of blindly pushing it one day forever.

The biggest limitation is direct Things access: Things is canonical, but the current AI runtime does not yet have a verified Things bridge.

See `docs/PLANNING.md`, `docs/AUTOMATIONS.md`, and `config/scheduling.yaml`.

## AI layer

Current conceptual roles:

- **ChatGPT** — primary command/planning/orchestration layer and native connected-tool surface.
- **Claude / Claude Code** — coding-heavy specialist.
- **OpenClaw** — optional channel/custom-integration plumbing when a native path is missing.
- **Repository agents (Copilot/Codex-style)** — code/repo-local assistance governed by this repo.

These are roles, not competing sources of truth.

## Runtime reality

Currently verified useful direct paths in the ChatGPT environment include:

- GitHub read/write;
- Notion read/write;
- Google Calendar read/write;
- Gmail connection with read verified and supported write actions exposed;
- Slack connection with read verified and supported write actions exposed;
- scheduled/conditional automations.

Important partial/missing paths:

- Things 3 direct bridge;
- direct live local Obsidian vault bridge (GitHub backup is accessible);
- direct Jira connector should be verified before claims of access;
- direct Discord connection is not assumed.

See `docs/STATUS.md` for the operational snapshot.

## Anywhere capture

Desired entry points include:

- ChatGPT
- Slack
- Discord
- iPhone Shortcuts / Share Sheet
- email
- browser capture

The user should not need to choose a destination app before expressing intent. The AI/router should classify and route to the canonical owner.

## Obsidian

The `zubairmuwwakil/Obsidian` GitHub repository is a backup/source for the Obsidian vault and can be consulted when deeper personal knowledge/context is needed.

The vault is PARA-style:

`00 Inbox -> 10 Daily -> 20 Areas / 30 Projects / 50 Resources -> 90 Archive`

Key rules:

- **One home per item; link instead of copying.**
- GitHub owns code/project artifacts; Obsidian owns remembering/reasoning.
- Obsidian may link to Notion/GitHub/Jira rather than duplicate canonical operational state.
- AI is authorized for autonomous knowledge maintenance, including create/link/merge/rewrite/capture, subject to provenance/privacy safeguards.
- For software-engineering learning, the vault's retrieval-first learning contract remains authoritative and intentionally introduces desirable difficulty.

Technical caveat: access to the GitHub backup is not the same as a verified live local-vault editing bridge.

## Notion

Current conclusion:

> **Notion's highest-value role is Personal Operations / Life Database.**

Strong fits:

- personal-care/household inventory
- shopping thresholds
- subscriptions/membership metadata
- benefits/cancellation instructions
- important document metadata and expiries
- warranties
- property/vehicle/insurance administrative metadata
- loyalty programs
- administrative contacts/vendors
- AI Activity Log

Weak fits:

- duplicate engineering project manager
- duplicate Jira backlog
- deep personal knowledge archive
- duplicate finance engine

## Finance boundary

Dedicated financial applications own live financial state/calculation, such as:

- transactions
- balances/net worth
- cash-flow calculations/forecasting
- credit-card recommendation logic
- other application-specific financial logic

Notion may hold administrative reference metadata. Obsidian may hold financial reasoning/research. Neither should duplicate the live finance engine by default.

## Communication boundary

- Slack = work/software-engineering communication.
- Discord = personal/life communication.

Messages may create objects elsewhere:

- engineering work -> Jira
- personal action -> Things
- scheduled execution/time -> Calendar
- durable knowledge -> Obsidian
- structured state -> Notion

Slack/Discord remain communication surfaces, not task databases.

## Automation layer

Active automation includes:

- evening `Plan Tomorrow`;
- morning `Daily Systems Digest`;
- hourly conditional `Calendar Task Follow-Up`;
- weekly personal-care heartbeat;
- weekly personal-care restock digest.

See `docs/AUTOMATIONS.md` for exact responsibilities and interaction rules.

## Audit layer

A Notion database named **AI Activity Log** records meaningful autonomous actions when practical.

It should store only enough metadata to understand/debug the action: source, destination, type, status, timestamp, links, details/error, and reversibility.

It must not become a repository for private chain-of-thought or unnecessary sensitive content.

## Public repo boundary

`LLM4LIFE` is public. Architecture and policy belong here; private life state does not.

Read `docs/SECURITY.md` before adding real-world examples or runtime details.
