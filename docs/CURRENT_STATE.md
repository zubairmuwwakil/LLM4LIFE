# Current State

_Last updated: 2026-09-02_

LLM4LIFE has completed a full personal software/life-system inventory and has entered **v2 migration**.

The target architecture is now user-owned/durable where it matters, while existing live SaaS workflows remain temporarily operational until migrated.

## Current operating model

```text
User expresses intent through practical channels
                  |
                  v
          LLM4LIFE / AI router
                  |
      +-----------+-----------+----------------+
      |                       |                |
      v                       v                v
   machine state          knowledge         domain truth
 Neon/PostgreSQL           Obsidian      Jira/GitHub/InUnity
      |
      +--------+------------------+
               |                  |
               v                  v
        Google Tasks       Google Calendar
          action UI        execution/time
```

Communication/source surfaces include Gmail, Slack, Discord, WhatsApp, iMessage, Shortcuts/Share Sheet and browser capture where integrations are available.

## v2 ownership

| Domain | Owner / direction |
|---|---|
| LLM4LIFE machine state | Neon/PostgreSQL |
| Personal actions | Neon backend; Google Tasks preferred user-facing client |
| Execution schedule | Google Calendar |
| Engineering backlog | Jira |
| Code/repository truth | GitHub |
| Coding-agent orchestration | ORC |
| Knowledge/reasoning/learning | Obsidian |
| Relationship context | Obsidian |
| Contact identity | Google Contacts after Apple/Google dedup migration |
| Household + vehicle maintenance | Neon/PostgreSQL |
| Grocery/shopping-list state | Neon/PostgreSQL |
| Consolidated finance | InUnity |
| Official provider records/execution | respective provider |
| Files | Google Drive preferred; OneDrive secondary after audit |

See `config/domains.yaml` for the complete registry.

## What is implemented now

The repo now contains:

- v2 architecture decision and domain ownership registry;
- v2 `system.yaml`, `AGENTS.md`, and tool registry;
- `db/migrations/001_core.sql` for systems, refs, jobs/runs, events, receipts, sync state, assets/maintenance and shopping;
- `db/migrations/002_actions_and_adaptation.sql` for actions, execution telemetry and adaptive rules;
- credential-free `DATABASE_URL` and local-vault path placeholders.

The schema has **not yet been applied** to Neon because project discovery through the connector requires an organization/project resolution step.

## Transitional runtime

Target architecture and runtime cutover are intentionally separate.

Existing ChatGPT planning automations currently use Notion-backed state including Tasks, Task Execution Log, Scheduling Model, Shopping Needs and AI Activity Log. These workflows stay live until Neon equivalents are populated and verified.

Things 3 and older Notion state should not be deleted simply because v2 is adopted.

## Planning model

Target:

```text
Neon personal actions        Jira engineering work
          \                         /
           \                       /
              AI planner/scheduler
                       |
                       v
                Google Calendar
                 execution plan
```

Google Tasks is the preferred human action client/projection.

Current scheduling semantics remain:

- sleep 11 PM–7 AM protected;
- weekday work 9 AM–1 PM soft-busy;
- movable personal work defaults to 1 PM–9 PM America/Toronto;
- leave buffer;
- fixed commitments do not move for optimization;
- waiting/blocked actions do not consume execution time;
- repeated misses feed scheduling adaptation rather than endless blind rescheduling.

## Obsidian

Obsidian remains the durable narrative knowledge/context system.

It owns:

- learning and reasoning;
- durable notes/research;
- diary/reflections;
- relationship/person context;
- contextual knowledge that benefits from readable Markdown.

The People/Relationships system already uses a useful link-not-copy model. Improve its structured frontmatter and derived views before adding relationship tables to Neon.

The preferred future AI write path is a trusted local bridge to the live vault. GitHub backup access is useful but is not the permanent real-time architecture.

## Contacts

Contact identity is currently fragmented across Apple Contacts and Google Contacts.

Target:

```text
Google Contacts -> canonical address book
Apple Contacts  -> synced Apple-device client
Obsidian        -> relationship context
```

Migration requires deduplication before canonical cutover.

## Household operations

The full inventory revealed real missing systems for:

- grocery/shopping lists;
- household maintenance;
- vehicle maintenance.

These are now modeled in the v2 backend schema. Tasks should be generated when work becomes actionable; Calendar is used when actual time is reserved.

## Finance

- InUnity is the main consolidated finance system.
- MoneyTalks refers to the same product lineage rather than a separate system.
- Looply functionality has been absorbed into InUnity.
- PickMe feeds relevant purchase/card data to InUnity.
- MarketLens feeds market data to InUnity.
- Banks/card issuers/brokerages remain authoritative for official provider state and execution.

## Communication and ingress

Communication applications are edge channels, not state databases.

The desired pattern is:

```text
Gmail / Slack / Discord / WhatsApp / iMessage / Shortcuts
                        |
                        v
                LLM4LIFE ingress/router
                        |
                        v
                 canonical destination
```

Preserve the valuable cross-channel experience previously provided by OpenClaw, but OpenClaw itself remains replaceable by native connectors or thin bridges.

## Notion

Notion is no longer the default target backend.

Future best role:

- optional dashboards/projections;
- structured human-facing workspaces;
- ad-hoc collaboration where it is actually useful.

Current Notion planning/inventory/audit databases remain transitional live state until migrated.

## Free-first constraint

Prefer already-paid capabilities, then strong free tiers/open-source solutions. New paid products require a clear material advantage.

## Public repo boundary

LLM4LIFE is public. It stores architecture, contracts, schemas and placeholders — never real credentials, private people/relationship data, health records, financial identifiers, confidential work data or private message bodies.
