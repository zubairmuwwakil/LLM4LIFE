# Runtime Status

_Last updated: 2026-09-02_

This file describes **what is actually live now** while LLM4LIFE migrates to the v2 architecture.

Target ownership is defined by `config/domains.yaml` and `system.yaml`. A target being documented does not mean cutover has happened.

## Headline

The full software/life-system inventory is complete and **v2 foundation implementation has started**.

Already implemented in the public LLM4LIFE repo:

- v2 production architecture decision;
- machine-readable v2 domain ownership registry;
- v2 `system.yaml`;
- PostgreSQL migrations for core orchestration state;
- PostgreSQL actions + execution telemetry + adaptive-rules schema;
- household/vehicle maintenance schema;
- grocery/shopping-list schema;
- v2 agent instructions and environment-variable placeholders.

Not yet completed:

- applying the schema to the user's Neon database;
- migrating live Notion Tasks / Task Execution Log / Scheduling Model / AI Activity Log state;
- Google Tasks synchronization/projection adapter;
- live local Obsidian write bridge;
- Apple Contacts -> Google Contacts dedup/canonical migration;
- migration of household/shopping workflows into the backend;
- production event/worker runtime.

## Important transitional rule

Existing working automations are **not being disabled during the foundation pass**.

Current planning automations may still depend on transitional Notion databases such as:

- Tasks;
- Task Execution Log;
- Scheduling Model;
- Shopping Needs;
- AI Activity Log.

Those dependencies remain runtime truth until their Neon-backed replacements are reconciled and verified.

## Runtime paths

| System | Runtime status | Current role / limitation |
|---|---|---|
| GitHub | Connected, read/write verified | Architecture/config/code repository operations |
| ChatGPT Automations | Connected/live | Current scheduled/conditional execution surface; some prompts still reference transitional Notion state |
| Google Calendar | Connected in current operating system | Execution schedule and commitments |
| Notion | Transitional live dependency | Existing task/planning/inventory/audit workflows may still use it; no longer the v2 target backend |
| Gmail | Connected capability | Email/source context and actions through supported connector paths |
| Slack | Connected capability | Work communication/context |
| Neon | **Partial** | Connector exists, but initial project discovery required an organization ID that was not resolved in the first v2 pass; schema therefore remains committed but unapplied |
| Google Tasks | User-live / target client | Preferred v2 personal-action UI; direct ChatGPT task connector not currently verified |
| Google Contacts | Connector available; migration not done | Preferred canonical address book after Apple/Google dedup |
| Apple Contacts | User-live | Still contains part of contact identity; intended to become a synced client after migration |
| Obsidian | Partial | Private GitHub backup can be inspected/maintained; trusted live local-vault bridge remains unimplemented |
| Jira / Atlassian | Connector available; verify per task | Canonical engineering backlog |
| ORC | External subsystem | Coding-agent orchestrator; not the life-state backend |
| Discord / WhatsApp / iMessage | User-live channels | Cross-channel AI access requires verified native/custom/OpenClaw bridge |

## v2 target ownership

```text
LLM4LIFE machine state      -> Neon/PostgreSQL
Personal action state       -> Neon/PostgreSQL
Personal action UI          -> Google Tasks
Execution schedule          -> Google Calendar
Knowledge/reasoning         -> Obsidian
Relationship context        -> Obsidian
Contact identity            -> Google Contacts after migration
Engineering backlog         -> Jira
Code/repository truth       -> GitHub
Coding orchestration        -> ORC
Consolidated finance        -> InUnity
```

See `config/domains.yaml` for the full domain matrix.

## Current highest-priority implementation gaps

### P0 — Resolve/apply Neon backend

The schema exists in:

- `db/migrations/001_core.sql`
- `db/migrations/002_actions_and_adaptation.sql`

Next step is to identify the correct Neon project/organization, validate migrations on a disposable branch, and apply them through the normal migration path.

### P0 — Migrate planning state without breaking current automations

The current daily planning loop still uses transitional Notion task state. Migration should:

1. reconcile current tasks and external Calendar references;
2. import execution telemetry needed for scheduling learning;
3. preserve waiting/follow-up semantics;
4. validate Neon reads/writes;
5. introduce Google Tasks projection/sync;
6. update automations only after parity is proven.

Avoid long-term dual-write.

### P1 — Live Obsidian bridge

Desired path:

```text
AI/router -> authenticated local adapter -> live vault -> normal vault backup/sync
```

GitHub backup edits are not the preferred permanent real-time write mechanism.

### P1 — Contacts consolidation

Inventory/deduplicate Apple Contacts and Google Contacts before making Google Contacts canonical. Do not blindly merge duplicates.

### P1 — Household operations

Use the new asset/maintenance/shopping schema for household and vehicle maintenance plus grocery/shopping state, then emit actions to Google Tasks and actual scheduled work to Calendar.

## Scheduling runtime

Until live migration changes it, the current planning semantics remain:

- sleep 11:00 PM–7:00 AM protected;
- weekday work 9:00 AM–1:00 PM soft-busy;
- movable personal work defaults to 1:00 PM–9:00 PM America/Toronto;
- leave buffer;
- fixed commitments are not moved for optimization;
- waiting work should not occupy execution blocks;
- repeated misses are evidence for replanning.

## Public repository constraint

This repo contains architecture, contracts and schemas only.

Never commit actual database URLs, credentials, private contact/relationship information, health data, financial identifiers, confidential work content or private message bodies.

## When to update this file

Update it after an actual runtime cutover or connection change, especially when:

- Neon schema is applied;
- task data is migrated;
- Google Tasks sync becomes live;
- a local Obsidian bridge is deployed;
- contacts are consolidated;
- a transitional Notion dependency is retired;
- a connector becomes verified/unavailable.
