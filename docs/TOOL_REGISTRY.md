# Tool Registry

_Last verified: 2026-08-27_

This is the operational inventory for LLM4LIFE. It answers four questions for every important tool:

1. **What is it for?**
2. **Who uses it?**
3. **What is its source-of-truth responsibility?**
4. **What can the AI actually access today?**

Do not confuse architectural intent with runtime access. A tool may be canonical even when the current AI session cannot directly read or write it.

## Status vocabulary

- **CONNECTED** — a direct connector/path has been exercised successfully in the current ChatGPT environment.
- **PARTIAL** — useful access exists, but not the complete desired read/write path.
- **USER-LIVE** — actively used by the user, but the current AI does not have a verified direct integration.
- **OPTIONAL / PLANNED** — part of the architecture only when it removes real friction; do not assume it is deployed.
- **AUXILIARY** — available capability, but not a canonical LLM4LIFE domain owner.

## Core tools

| Tool | Status | Canonical responsibility | Primary users/actors | AI use today | Important limitation |
|---|---|---|---|---|---|
| **ChatGPT** | CONNECTED / primary control plane | Universal conversational interface, routing, orchestration, automation execution | User, scheduled automations | Reads/writes through connected tools; maintains LLM4LIFE policy | Must not become a separate source-of-truth database |
| **GitHub** | CONNECTED, read/write verified | Code, repositories, PRs, commits, releases, repository-local technical truth; LLM4LIFE policy repo | User, ChatGPT, Claude/coding agents, Copilot/Codex-style agents | Direct read/write connector is working | Personal tasks and life-state do not belong here |
| **Jira** | USER-LIVE; direct ChatGPT path not verified in this runtime | Engineering bugs, backlog, technical work items | User, engineering agents | Treat as canonical when referenced; use a verified Jira/Atlassian connector before claiming read/write access | Never mirror the whole engineering backlog into Things or Notion |
| **Things 3** | USER-LIVE; AI bridge missing | Personal backlog, personal actions, reminders, next actions | User; AI planner once bridge exists | No verified direct server-side access today | Highest-priority planning integration gap; do not pretend the backlog was inspected |
| **Google Calendar** | CONNECTED, read/write verified | Fixed commitments plus the current execution schedule/time blocks selected from backlog | User, ChatGPT planner, follow-up automation | Direct calendar read/write works | Calendar is not the permanent task backlog |
| **Notion** | CONNECTED, read/write verified | Structured personal/life state, inventories, admin metadata, AI Activity Log | User, ChatGPT/automations | Direct read/write works; used for AI Activity Log and structured state | Do not rebuild GitHub/Jira, Obsidian, or finance engines here |
| **Obsidian** | PARTIAL | Durable personal knowledge/context, reasoning, learning, long-form notes, PARA vault | User, ChatGPT/Claude/other agents | AI can inspect the backed-up GitHub vault and is authorized to maintain notes | Direct live local-vault bridge is not yet verified; GitHub backup access is not the same thing as writing the open local vault immediately |
| **Slack** | CONNECTED; read verified, write-capable connector exposed | Work/software-engineering communication and work notification surface | User, ChatGPT/agents | Current Slack account connection is reachable; read path verified | Slack is communication/I-O, not task storage; consequential messages still need safeguards |
| **Discord** | USER-LIVE; direct ChatGPT connector not available here | Personal/life communication and desired personal notification surface | User; OpenClaw/custom bridge if deployed | No direct ChatGPT Discord connector is currently assumed | Do not claim messages were sent/read unless a real bridge is present |
| **Gmail** | CONNECTED; account read verified, connector is read/write capable | Email intake, source context, action-required message detection | User, digest/planner, ChatGPT | Current Gmail connection is reachable; messages can be searched/read and supported actions exist | Email should route actions/state to canonical systems rather than become the task manager |

## AI / agent tools

| Agent/tool | Current role | Who uses it | Status / rule |
|---|---|---|---|
| **ChatGPT** | Primary life/work command layer and connected-tool orchestrator | User | Current primary runtime. Must read this repo before making architectural changes. |
| **Claude / Claude Code** | Coding-heavy specialist | User | External specialist. Should read `CLAUDE.md` -> `AGENTS.md` and follow the same ownership rules rather than creating a parallel productivity architecture. |
| **GitHub Copilot / Codex-style repo agents** | Repository-local coding/maintenance assistance | User / GitHub workflows | `.github/copilot-instructions.md` routes agents back to canonical LLM4LIFE policy. |
| **OpenClaw** | Optional channel/custom-integration plumbing | User / future automations | Provisional. Useful for gaps such as Discord or local bridges; not a database and not a second policy authority. Deployment is not assumed unless verified. |
| **ChatGPT Automations** | Scheduled/conditional orchestration | System on user's behalf | LIVE. See `docs/AUTOMATIONS.md` and `config/automations.yaml`. |

## Auxiliary connected capabilities

These can be useful when a task requires them, but they are **not currently core domain owners** in LLM4LIFE.

| Capability | Intended use | Rule |
|---|---|---|
| **Google Drive / Docs / Sheets / Slides** | Fetch or work with user documents and files when those artifacts are the real source | Do not move all knowledge into Drive merely because a connector exists. Respect the original artifact as canonical. |
| **Google Contacts** | Recipient/attendee identity resolution | Use to resolve people for Gmail/Calendar; it is not a CRM by default. |
| **Namecheap connector** | Domain availability/pricing tasks | Domain utility only; not part of the personal OS state model. |
| **Apple Music connector** | Music discovery/playlist tasks | Personal media utility; not part of planning/knowledge architecture. |

## Domain applications and codebases

These are products/services in the wider ecosystem, not replacements for the productivity stack.

| System | Current architectural role | Source of truth |
|---|---|---|
| **In Unity / MoneyTalks** | Personal-finance command center: transaction/state/cash-flow/net-worth style calculations | Its own application/database, not Notion |
| **PickMe** | Credit-card recommendation/capture/card-selection domain | Its own repository/application data |
| **MarketLens / marketdata** | Market-data service feeding finance applications | Service/database and repository |
| **Looply / return-saas** | Receipts, bills, subscription-related ingestion/workflows | Its own application/database |

Do not infer that these applications are production-connected to the AI router merely because their repositories exist. Verify an API/connector before acting on live application state.

## Human vs AI responsibility

### User

The user should be able to:

- dump personal actions into Things;
- view/execute the day from Calendar;
- communicate at work in Slack and personally in Discord;
- think/learn in Obsidian;
- use Notion for structured personal operations;
- use Jira/GitHub for engineering;
- ask the AI instead of manually routing every new input.

### AI router

The AI should:

- classify the intent;
- locate the canonical owner;
- search before creating duplicates;
- perform safe reversible writes autonomously;
- schedule selected backlog into Calendar;
- preserve source/deep links;
- log meaningful writes;
- return compact receipts;
- detect integration gaps rather than hallucinate access.

### Scheduled automations

Automations should:

- plan and sanity-check days;
- follow up on task-style calendar blocks;
- produce useful exception-oriented digests;
- run narrow domain checks such as personal-care restock status;
- never silently expand their own permissions.

## Runtime verification rule for agents

Before claiming that a tool is connected or writable:

1. inspect `docs/STATUS.md`;
2. if the task depends on live access, attempt a harmless read through the connector;
3. only claim write capability after the connector/action is actually available;
4. distinguish `authorized by policy` from `technically connected right now`;
5. if unavailable, use the documented bridge/gap rather than inventing success.

## Ownership shortcut

```text
personal backlog/action    -> Things 3
engineering backlog/bug    -> Jira
code/repository truth      -> GitHub
scheduled execution/time   -> Google Calendar
structured life state      -> Notion
knowledge/reasoning         -> Obsidian
work communication          -> Slack
personal communication      -> Discord
email source/input          -> Gmail
finance calculations/state  -> dedicated finance apps
orchestration               -> AI layer
```
