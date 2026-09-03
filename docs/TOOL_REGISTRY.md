# Tool Registry

_Last updated: 2026-09-03_

This registry separates **target ownership**, **current runtime status**, and **user-facing interfaces**. See `config/tools.yaml` for machine-readable detail and `docs/STATUS.md` for live migration status.

## Core systems

| Tool | v2 role | Runtime status | Important boundary |
|---|---|---|---|
| **ChatGPT** | Primary conversational/control surface | Connected | Router/orchestrator, not durable state stored only in chat |
| **Neon / PostgreSQL** | Durable LLM4LIFE machine-state backend | **Connected/live** | Canonical personal actions + LLM4LIFE operational state |
| **Google Tasks** | Preferred user-facing personal action client | **Production-live** | Human UI/capture surface for Neon actions; not canonical rich domain state |
| **Cloudflare** | Edge runtime for Google Tasks projection | **Production-live Worker** | Runs sync every 15 minutes; ChatGPT app enabled, but current session does not expose its tool namespace |
| **Google Calendar** | Commitments + execution schedule | Connected/live | Calendar blocks are projections of actions, not the permanent backlog |
| **Google Contacts** | Preferred canonical address book after migration | Connector available; migration incomplete | Identity/contact facts, not relationship narrative |
| **Apple Contacts** | Current address-book client/source | User-live | Intended to become synced client after dedup migration |
| **Obsidian** | Narrative knowledge, learning, diary, relationship context | Partial through private GitHub backup | Preferred future write path is a trusted local-vault bridge |
| **Notion** | Rollback/reference for migrated planning + transitional remaining domains | Connected | No longer canonical for personal tasks; Shopping Needs still transitional |
| **Things 3** | Legacy/optional task UX | User-live | Not canonical in v2 |
| **Jira** | Engineering backlog/bugs/work items | Atlassian connector available; verify per operation | Do not mirror engineering backlog into personal tasks |
| **GitHub** | Code/repository truth + LLM4LIFE public architecture | Connected read/write | Not a personal-life database |
| **ORC** | Coding-agent orchestration subsystem | External repo/subsystem | LLM4LIFE invokes ORC; does not duplicate its routing/verification logic |
| **InUnity** | Consolidated user-owned finance system | **ChatGPT MCP integration complete; recently read-verified** | PickMe/MarketLens feed it; provider systems remain official record/execution owners |
| **Gmail** | Email/source/intake surface | Connected capability | Route durable actions/state elsewhere |
| **Slack** | Work communication/automation surface | Connected capability | Communication, not canonical task state |
| **Discord** | Preferred historical personal AI/channel surface | User-live; no direct ChatGPT connector assumed | Requires verified bridge for AI access |
| **WhatsApp** | Personal communication / optional AI channel | User-live | Bridge/API verification required |
| **iMessage** | Personal communication source | User-live | Likely requires trusted local Mac bridge |
| **OpenClaw** | Optional channel/local-integration plumbing | Provisional | Not a database or second policy authority |

## Google Tasks production integration

```text
Google Tasks
    ^  |
    |  v
Cloudflare Worker (every 15 min)
    ^  |
    |  v
Neon/PostgreSQL canonical actions

Google Calendar = execution time
```

Verified current production state:

- Worker `llm4life-google-tasks-sync` deployed;
- Google OAuth completed;
- manual sync succeeded;
- scheduled cron succeeded;
- 14 Google Tasks action bindings verified in Neon;
- both Google Tasks checkpoints verified;
- durable `google-tasks-sync` job enabled.

Important behavior:

- new tasks in the dedicated `LLM4LIFE` Google Tasks list can be captured as Neon `inbox` actions;
- completion/reopen propagates to Neon;
- safe title/date edits can flow into Neon;
- concurrent edits produce a receipt and Neon wins non-status conflicts;
- deleting a Google Task never deletes the Neon action;
- `scheduled_for` stays in Google Calendar, not Google Tasks;
- Google Tasks API due dates are only day-level projections;
- the Worker records jobs, runs, external refs, checkpoints, and action receipts in Neon.

### v0.2 hardening

The first bulk production projection safely hit Cloudflare Free's 50 external-subrequest ceiling before a retry completed the remaining work. Worker v0.2 is committed and pending redeploy with:

- Neon `sql.transaction(...)` batching;
- Google Tasks multipart batch mutations, up to 50 operations per Google batch request;
- incremental `updatedMin` Google reads after the first snapshot;
- five-minute overlap on incremental reads;
- core cancelled/archived cleanup;
- existing idempotent external-ref/checkpoint/run-key safeguards.

No database migration is required for v0.2.

## InUnity MCP

InUnity remains the finance-domain owner and has a completed ChatGPT MCP integration. A recent `get_attention_summary` read was successfully exercised. Because the InUnity namespace is not surfaced in every ChatGPT session, agents should re-check live tool availability before a finance call rather than treating the integration as absent.

## Storage/file systems

| Tool | Direction |
|---|---|
| **Google Drive** | Preferred canonical cloud file store |
| **OneDrive** | Secondary/exception-only after audit |
| **Time Machine** | Local disaster recovery, separate from sync |

## Canonical ownership shortcut

```text
LLM4LIFE machine state      -> Neon/PostgreSQL
Personal actions            -> Neon backend
Personal action client      -> Google Tasks
Personal-action sync        -> Cloudflare Worker
Scheduled execution         -> Google Calendar
Engineering work            -> Jira
Code/repository truth       -> GitHub
Coding-agent orchestration  -> ORC
Knowledge/reasoning         -> Obsidian
Relationship context        -> Obsidian
Contact identity            -> Google Contacts after migration
Consolidated finance        -> InUnity
Finance ChatGPT interface   -> InUnity MCP when surfaced/verified
Official provider state     -> respective provider
Email/source context        -> Gmail
Work communication          -> Slack
```

## Migration reality

The personal planning backend has moved from Notion to Neon and Google Tasks is now a live client/projection. Notion planning databases remain rollback/reference copies, while Shopping Needs remains transitional until its Neon replacement is populated.

## Runtime verification rule

Before claiming a tool is usable for the current operation:

1. inspect `docs/STATUS.md` and `config/tools.yaml`;
2. perform a harmless read if the task depends on live access;
3. only claim a write succeeded after a real supported write succeeds;
4. distinguish user usage, policy authorization, target ownership and technical connectivity.

## Free-first rule

Prefer capabilities already paid for, then strong free tiers/open-source options. Add a new paid product only when it provides a material advantage that existing/free capabilities cannot reasonably deliver.
