# Tool Registry

_Last updated: 2026-09-02_

This registry separates **target ownership**, **current runtime status**, and **user-facing interfaces**. See `config/tools.yaml` for machine-readable detail and `docs/STATUS.md` for live migration status.

## Core systems

| Tool | v2 role | Runtime status | Important boundary |
|---|---|---|---|
| **ChatGPT** | Primary conversational/control surface | Connected | Router/orchestrator, not durable state stored only in chat |
| **Neon / PostgreSQL** | Durable LLM4LIFE machine-state backend | Partial; schema committed but not yet applied | Own LLM4LIFE operational state, not every private narrative/provider record |
| **Google Tasks** | Preferred user-facing personal action client | User-live; direct ChatGPT task connector not verified | UI/projection for personal actions, not rich domain database |
| **Google Calendar** | Commitments + execution schedule | Connected/live | Calendar blocks are projections of actions, not the permanent backlog |
| **Google Contacts** | Preferred canonical address book after migration | Connector available; migration incomplete | Identity/contact facts, not relationship narrative |
| **Apple Contacts** | Current address-book client/source | User-live | Intended to become synced client after dedup migration |
| **Obsidian** | Narrative knowledge, learning, diary, relationship context | Partial through private GitHub backup | Preferred future write path is a trusted local-vault bridge |
| **Notion** | Transitional live dependency + optional future dashboard/projection | Live/connected | No longer the default v2 canonical life backend |
| **Things 3** | Legacy/optional task UX | User-live | Not canonical in v2 |
| **Jira** | Engineering backlog/bugs/work items | Atlassian connector available; verify per operation | Do not mirror engineering backlog into personal tasks |
| **GitHub** | Code/repository truth + LLM4LIFE public architecture | Connected read/write | Not a personal-life database |
| **ORC** | Coding-agent orchestration subsystem | External repo/subsystem | LLM4LIFE invokes ORC; does not duplicate its routing/verification logic |
| **InUnity** | Consolidated user-owned finance system | Domain application | MoneyTalks is same lineage; Looply functionality absorbed; PickMe/MarketLens feed it |
| **Gmail** | Email/source/intake surface | Connected capability | Route durable actions/state elsewhere |
| **Slack** | Work communication/automation surface | Connected capability | Communication, not canonical task state |
| **Discord** | Preferred historical personal AI/channel surface | User-live; no direct ChatGPT connector assumed | Requires verified bridge for AI access |
| **WhatsApp** | Personal communication / optional AI channel | User-live | Bridge/API verification required |
| **iMessage** | Personal communication source | User-live | Likely requires trusted local Mac bridge |
| **OpenClaw** | Optional channel/local-integration plumbing | Provisional | Not a database or second policy authority |

## Storage/file systems

| Tool | Direction |
|---|---|
| **Google Drive** | Preferred canonical cloud file store |
| **OneDrive** | Secondary/exception-only after audit |
| **Time Machine** | Local disaster recovery, separate from sync |

## Domain/edge systems

These remain specialized provider or execution surfaces rather than central LLM4LIFE state owners:

- Google Maps / Waze
- Uber / Lyft
- GO Transit / PRESTO
- DoorDash / Uber Eats / SkipTheDishes
- streaming/media providers
- game platforms
- retailer/provider apps
- bank/card-provider apps
- smart-home provider apps

LLM4LIFE may compare, route, contextualize or trigger actions across these systems without copying their full histories into the backend.

## Canonical ownership shortcut

```text
LLM4LIFE machine state      -> Neon/PostgreSQL
Personal actions            -> Neon backend; Google Tasks client
Scheduled execution         -> Google Calendar
Engineering work            -> Jira
Code/repository truth       -> GitHub
Coding-agent orchestration  -> ORC
Knowledge/reasoning         -> Obsidian
Relationship context        -> Obsidian
Contact identity            -> Google Contacts after migration
Consolidated finance        -> InUnity
Official provider state     -> respective provider
Email/source context        -> Gmail
Work communication          -> Slack
```

## Migration reality

Some currently live ChatGPT automations still use Notion databases for Tasks, execution telemetry, scheduling preferences, shopping needs and audit logging. Those are **transitional runtime dependencies**, not evidence that Notion remains the v2 owner.

Do not disable or delete them before data reconciliation and replacement verification.

## Runtime verification rule

Before claiming a tool is usable for the current operation:

1. inspect `docs/STATUS.md` and `config/tools.yaml`;
2. perform a harmless read if the task depends on live access;
3. only claim a write succeeded after a real supported write succeeds;
4. do not confuse user usage, policy authorization, target ownership and technical connectivity.

## Free-first rule

Prefer capabilities already paid for, then strong free tiers/open-source options. Add a new paid product only when it provides a material advantage that existing/free capabilities cannot reasonably deliver.
