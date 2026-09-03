# 2026-09-02 — Production Architecture v2

**Status:** Adopted as the new target architecture. Migration is incremental; existing live automations remain operational until their state is safely moved.

This decision supersedes older conflicting 2026-08-27 ownership decisions where they assign **Things 3** as the canonical personal backlog or **Notion** as the canonical structured life-state backend.

## Why this changed

A full inventory of the user's actual personal, engineering, financial, household, communication, device, knowledge, relationship, media, travel, work and automation systems showed that the earlier architecture over-relied on SaaS applications as canonical stores.

The user also explicitly wants a more scalable, production-grade, long-term system, is willing to switch current tools when justified, and prefers free/already-paid-for capabilities before adding subscriptions.

The new design keeps specialized applications where their UX or provider authority matters, but introduces a user-owned durable machine-state layer rather than making Notion or a chat thread the backend.

## Core decision

Use a **hub-and-spoke architecture** with explicit ownership:

```text
                       conversational / edge inputs
 ChatGPT / Gmail / Slack / Discord / Shortcuts / Share Sheet / local bridge
                                  |
                                  v
                         LLM4LIFE control plane
                    classify / route / orchestrate
                                  |
         +------------------------+-----------------------+
         |                        |                       |
         v                        v                       v
      Neon                   Obsidian                domain systems
 machine state          narrative knowledge       Jira/GitHub/InUnity
 operational metadata   people/learning/context   Google/finance/providers
         |
         +-------------> execution surfaces
                         Google Tasks / Calendar
```

### Neon / PostgreSQL

Neon becomes the preferred durable backend for **machine-readable cross-system state that LLM4LIFE itself needs to operate reliably**.

Good candidates include:

- integration/service registry;
- stable internal object IDs and external references;
- automation/job registry;
- execution receipts and idempotency/deduplication keys;
- structured household assets and maintenance schedules;
- grocery/shopping-list state if it provides real value;
- vehicle-maintenance state;
- lightweight cross-system task/orchestration metadata where needed;
- sync/checkpoint state;
- AI activity/audit metadata that does not contain sensitive payloads.

Neon should **not** become a dump of every private narrative, full message history, health record, bank credential, or provider-owned live state.

### Obsidian

Obsidian remains the canonical human-readable narrative knowledge/context layer.

It owns:

- learning and reasoning;
- durable personal knowledge;
- diary and reflections;
- relationship context and person notes;
- long-form context and research;
- contextual notes that do not benefit from database semantics.

For relationships, structured frontmatter should be tried before copying narrative context into Neon.

### Google Contacts

Google Contacts is the preferred candidate for the canonical address book after Apple/Google contacts are deduplicated and migration is verified.

Apple Contacts should become a synced Apple-device client rather than an independently maintained second address book.

### Google Tasks

Google Tasks becomes the preferred simple personal **action/execution client** during migration away from Apple Reminders/Things 3.

It should not be asked to store rich domain state. LLM4LIFE may keep stable orchestration/task metadata in Neon when necessary while Google Tasks remains the user-facing actionable list.

### Google Calendar

Google Calendar remains canonical for time commitments and execution scheduling. Backlog/state should not be reconstructed from calendar events alone.

### Notion

Notion is repositioned from canonical life database to an optional **structured workspace/dashboard/projection layer**.

It may remain useful for views, ad-hoc trackers and human-friendly dashboards, but new core workflows should not require manual duplication into Notion when Neon or a domain application already owns the data.

Existing Notion databases/automations are not deleted during migration. They remain live until replacements are verified.

### GitHub + Jira + ORC

- GitHub remains canonical for code/repository truth.
- Jira remains canonical for engineering backlog/work items.
- ORC (`agent-orchestrator`) remains the coding-agent orchestration subsystem.
- LLM4LIFE invokes/reasons about ORC rather than rebuilding its model routing, quota handling or verification behavior.

### Finance

- InUnity is the main user-owned consolidated financial system.
- MoneyTalks is the same product lineage as InUnity, not a separate canonical system.
- Looply functionality has been absorbed into InUnity.
- PickMe sends relevant purchase/card data into InUnity.
- MarketLens is a specialized market-data service consumed by InUnity.
- Banks, card issuers, brokerages and other regulated providers remain authoritative for their official provider records/execution.

### Communication

Gmail, Slack, Discord, WhatsApp, iMessage and similar systems are edge channels/source context. They should not become canonical task or knowledge databases.

The valuable OpenClaw capability to preserve is cross-channel AI access. OpenClaw itself remains replaceable by native connectors, webhooks or a thin LLM4LIFE ingress/local-bridge layer if those provide better reliability, observability and least privilege.

## Free-first constraint

Architecture and tool recommendations should prefer:

1. capabilities already paid for;
2. strong free tiers;
3. open-source/self-hosted components when operationally reasonable;
4. additional paid products only when the incremental value materially justifies the recurring cost.

Production-grade does not mean maximizing enterprise complexity or subscription count.

## Migration safety

This decision changes **target ownership**, not all live runtime behavior immediately.

Until migration is complete:

- do not disable working Notion/ChatGPT automations merely because their backend is now transitional;
- do not delete Things/Notion data before replacement state has been verified;
- add durable backend primitives first;
- migrate one domain at a time;
- dual-read temporarily when necessary, but avoid long-term dual-write;
- use idempotency and execution receipts for autonomous jobs;
- preserve rollback paths.

## First implementation slice

1. Define the core Neon schema for systems, external references, jobs, job runs/events and audit receipts.
2. Add domain tables only where the inventory demonstrated a real gap: household assets/maintenance, vehicle maintenance and shopping/grocery state are initial candidates.
3. Update machine-readable LLM4LIFE ownership/configuration to v2.
4. Build deterministic adapters rather than embedding vendor-specific assumptions throughout the orchestrator.
5. Migrate existing Notion-backed planning/task automation only after the new state path is tested.
6. Build the live local Obsidian write adapter separately; do not use GitHub backup edits as the permanent local-vault write mechanism.

## Superseded decisions

Where they conflict with this record, the following older rules are superseded:

- `Things 3 owns the canonical personal backlog`;
- `Notion owns canonical structured life state`;
- `Notion AI Activity Log is the long-term audit backend`.

The older records remain valuable historical context and should not be deleted.
