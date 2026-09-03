# AGENTS.md

This repository describes the user's evolving AI-driven personal operating system.

## Prime directive

**Do not preserve an old tool boundary merely because it appears in an older document. Newest explicit decisions win. Distinguish target architecture from completed runtime migration.**

The current v2 target is defined by:

- `docs/decisions/2026-09-02-production-architecture-v2.md`
- `system.yaml`
- `config/domains.yaml`
- `config/tools.yaml`

Older August 2026 material remains historical context where it conflicts.

## Mandatory read order

Before making architecture, routing, automation, or integration decisions, read:

1. `docs/STATUS.md` — what is actually live/connected now
2. `docs/TOOL_REGISTRY.md` — human-readable tool/runtime inventory
3. `config/tools.yaml` — machine-readable runtime/tool truth
4. `config/domains.yaml` — v2 canonical domain ownership
5. `system.yaml` — high-level architecture/policies
6. `docs/decisions/2026-09-02-production-architecture-v2.md`
7. `docs/CURRENT_STATE.md`
8. `docs/ROUTING.md`
9. `docs/PLANNING.md`
10. `docs/AUTOMATIONS.md`
11. `config/automations.yaml`
12. `config/scheduling.yaml`
13. `docs/AUTONOMY.md`
14. `docs/ADAPTATION.md`
15. `docs/GAP_DETECTION.md`
16. `docs/KNOWLEDGE_CAPTURE.md`
17. `docs/PEOPLE.md` when work touches people, contacts, relationships, interaction capture, dedup or follow-ups
18. `docs/SECURITY.md`
19. `docs/DECISIONS.md` and relevant files under `docs/decisions/`

If decisions conflict, the **newest explicit decision wins**.

## Runtime truth rule

A target owner does not prove migration is complete, and a connector being installed does not prove a specific read/write works.

Before claiming live access:

1. inspect `docs/STATUS.md` and `config/tools.yaml`;
2. if the task depends on the connection, perform a harmless read through the real connector/bridge;
3. only claim a write succeeded after an actual supported write succeeds;
4. distinguish:
   - canonical target ownership;
   - transitional/live ownership;
   - user usage;
   - policy authorization;
   - technical connection right now.

During v2 migration, existing Notion-backed planning automations may remain live even though Notion is no longer the target canonical backend. Do not break a working transitional path before its replacement is reconciled and verified.

## v2 core mental model

The AI/agent is a **universal interface, router, planner and orchestrator**. Durable LLM4LIFE machine state belongs outside chat history.

```text
inputs / channels
      |
      v
LLM4LIFE control plane
      |
  +---+----------------------+-------------------+
  |                          |                   |
  v                          v                   v
Neon                      Obsidian           domain systems
machine state             narrative          Jira/GitHub/InUnity
jobs/actions/receipts      knowledge          provider authority
  |
  +----> Google Tasks / Google Calendar
          user execution surfaces
```

### Canonical v2 responsibilities

- **Neon/PostgreSQL** — LLM4LIFE-owned structured machine state: actions, external references, jobs/runs, events, receipts, sync checkpoints, adaptive rules, household/vehicle maintenance, shopping state, and the target structured People/Relationships machine state once that migration is implemented.
- **Google Tasks** — preferred user-facing personal action client/projection during v2.
- **Google Calendar** — fixed commitments and execution schedule; not the permanent backlog.
- **Google Contacts** — preferred human-facing address-book projection/client after People/contact dedup migration; do not assume its target role means that migration is already complete.
- **Obsidian** — narrative personal knowledge, reasoning, learning, diary/reflections and narrative relationship context.
- **Jira** — engineering backlog/bugs/work items.
- **GitHub** — code, repositories, PRs, commits, releases and repository truth.
- **ORC (`agent-orchestrator`)** — coding-agent routing, quota-aware escalation and independent verification.
- **InUnity** — user-owned consolidated finance system. PickMe and MarketLens feed it. MoneyTalks is the same product lineage; Looply functionality has been absorbed.
- **Gmail / Slack / Discord / WhatsApp / iMessage** — communication and source/ingress surfaces, not canonical task databases.
- **Notion** — transitional dependency and optional future dashboard/projection layer, not the default v2 backend.
- **Things 3** — legacy/optional UX, not canonical in v2.

See `config/domains.yaml` for the full domain registry.

## Migration rule

Target ownership and live runtime can differ temporarily.

For each migration:

1. identify the old live source and the v2 owner;
2. create/test the new storage or adapter;
3. reconcile data and external IDs;
4. temporarily dual-read if necessary;
5. avoid long-term dual-write;
6. switch one workflow/domain at a time;
7. verify results and receipts;
8. preserve rollback;
9. only then retire/reposition the old source.

Never delete or disable working legacy state merely because a target architecture has been documented.

## Agent routing behavior

When receiving an item:

1. Determine whether it is an action, time commitment, engineering work, code, structured machine state, knowledge/context, relationship context, contact identity, household/maintenance state, shopping state, finance state, or communication.
2. Find the v2 canonical owner in `config/domains.yaml`.
3. Check whether migration for that domain is live or transitional.
4. Verify runtime integration if an actual read/write is needed.
5. Search before creating a duplicate.
6. Route/update instead of copying state across systems.
7. Preserve source/deep links/external references when useful.
8. Use stable IDs and idempotency keys for automated writes.
9. Return a short receipt for meaningful writes.
10. Log execution/audit state in the durable backend once available.

## Personal actions and planning

### Target model

```text
Neon action state
      |
      +----> Google Tasks (human action UI)
      |
      +----> AI scheduler ----> Google Calendar (execution)
```

Jira remains separate for engineering work.

Calendar task blocks are scheduled representations, not a second canonical task record.

### Transitional runtime

Some current ChatGPT automations still use Notion `Tasks`, `Task Execution Log`, `Scheduling Model`, `Shopping Needs` and `AI Activity Log`. Treat those as live transitional dependencies until the v2 Neon path is applied and verified.

Do not silently rewrite or disable those automations as part of unrelated work.

### Scheduling defaults

Unless newer explicit instructions override them:

- sleep 11:00 PM–7:00 AM is protected;
- weekday work 9:00 AM–1:00 PM is soft-busy;
- movable personal work defaults to 1:00 PM–9:00 PM America/Toronto;
- leave buffer;
- fixed external commitments do not move for optimization;
- waiting/blocked work should not consume execution time;
- repeated misses are evidence for replanning, not a reason to blindly push one day forever.

## Obsidian policy

Obsidian remains an autonomous read/write-capable **knowledge/context** destination by policy, but the preferred eventual write path is a trusted local bridge to the live vault.

GitHub access to the private Obsidian backup is useful context and maintenance access, but should not be treated as the permanent real-time local-vault integration.

### People and relationship information

The People architecture changed on 2026-09-03. **Do not follow the older “Obsidian frontmatter first; avoid Neon relationship tables” recommendation as the current target.** Read `docs/PEOPLE.md` and `docs/decisions/2026-09-03-people-subsystem-architecture.md` before developing this subsystem.

Target boundaries:

- Neon owns the stable internal `person_id`, cross-system person references and structured People/relationship machine state once the migration is implemented.
- Obsidian owns long-form/narrative relationship context, reflections, diary/history and nuanced person notes.
- Google Contacts is the preferred address-book projection/human client after dedup/cutover; Apple Contacts should become a synchronized device client rather than independent truth.
- Concrete follow-ups use the existing LLM4LIFE personal action domain and project to Google Tasks.
- Scheduled interactions use Google Calendar.
- Do not persist complete private conversations merely because a channel bridge can read them.
- Do not auto-merge people on name similarity alone; stable refs and conservative dedup rules are mandatory.
- Structured facts require provenance; model inference is not user-asserted truth.

**Runtime warning:** Phase 0 is documentation only. The People Neon schema/contact migration is not live merely because the target is documented.

### Learning exception

For software-engineering learning, the Obsidian vault's own `AGENTS.md` and AI Operating Manual override frictionless automation. Preserve retrieval-first/desirable-difficulty behavior.

## Household and personal operations

The inventory demonstrated real operational gaps for:

- grocery/shopping lists;
- household maintenance;
- vehicle maintenance.

The v2 backend contains minimum useful schemas for these domains. Use Tasks/Calendar as outputs for due actions; do not treat them as the underlying maintenance database.

Do not create a database for every one-off life fact.

## Finance boundary

- InUnity owns consolidated user-controlled finance state.
- PickMe -> InUnity.
- MarketLens -> InUnity.
- External banks/card issuers/brokerages remain authoritative for official provider records and execution.
- Do not store bank passwords, card credentials, crypto seeds/private keys, recovery codes or other financial secrets in LLM4LIFE.

## ORC boundary

ORC owns coding-agent orchestration. LLM4LIFE may invoke ORC, but must not recreate ORC's model routing, quota handling, escalation, verification or cross-vendor review logic.

## Free-first rule

Prefer, in order:

1. capabilities already paid for;
2. strong free tiers;
3. open-source/self-hosted components when operationally reasonable;
4. new paid products only when the incremental value clearly justifies the recurring cost.

Production-grade does **not** mean adding subscriptions or enterprise complexity by default.

## Autonomy

The user prefers low-friction autonomous operation for safe, reversible work.

Generally acceptable when intent is clear and runtime access exists:

- create/update personal actions;
- create/update Jira work;
- add user-requested calendar events;
- maintain Obsidian knowledge/context;
- classify/route/link information;
- maintain low-risk machine state;
- create execution receipts/checkpoints;
- improve low-risk documentation/routing/configuration;
- implement minimum useful workflows using already-authorized capabilities.

Standing low-risk approval does **not** authorize:

- purchases/subscriptions or cancellations;
- moving/spending money;
- destructive deletion;
- account/security/credential changes;
- new credentials/permissions/access grants;
- externally consequential messages or commitments;
- material production changes;
- legal or similarly hard-to-reverse commitments;
- weakening safeguards.

## Adaptation

Low-risk routing, prioritization, notification, capture, deduplication, duration and scheduling rules may adapt from repeated evidence.

Requirements:

- one observation is not a permanent rule;
- prefer small reversible changes;
- preserve rollback;
- track sample size/confidence where practical;
- explicit user instructions override learned preferences;
- learned rules never override safety.

The v2 target stores adaptive rules and execution telemetry in PostgreSQL rather than requiring a SaaS page as the permanent model.

## Gap detection

When an important recurring domain has no reliable owner, trigger, follow-up or retrieval path:

1. verify recurrence/consequence;
2. check existing domain owners first;
3. choose one owner;
4. build the smallest useful workflow;
5. reuse existing/free capabilities;
6. automate only within current authority;
7. monitor value/noise and simplify if necessary.

Anti-goal: life as ERP.

## Integration priority

Prefer:

1. native supported connector/API;
2. supported app automation interface;
3. thin deterministic custom adapter/local bridge;
4. broader middleware only when truly justified.

Prefer hub-and-spoke routing. Avoid mesh synchronization.

## Jobs and automation

Important recurring jobs should have durable state outside the conversational thread:

- stable job identity;
- trigger/schedule definition;
- idempotency key;
- execution run/receipt;
- retries/failure policy;
- observability;
- least-privilege credentials;
- explicit owner/destination.

Use:

- GitHub Actions for repository CI/CD;
- cron for deterministic local/server scripts when appropriate;
- ChatGPT Automations for conversational scheduled/conditional execution;
- a durable worker when retries/state/observability require it.

Do not use GitHub Actions as a general personal-life scheduler simply because it exists.

## Public-repository security

`LLM4LIFE` is public.

Never commit:

- passwords/API keys/tokens/cookies;
- private emails or message bodies;
- account numbers/high-risk identifiers;
- private people profiles or relationship notes;
- health/medical records;
- confidential employer/client content;
- raw sensitive activity logs;
- actual database connection strings.

Architecture, schemas, variable **names**, placeholders and non-sensitive contracts are appropriate.

Private connected context may be used operationally without copying it into this repository.

## Change management

For a material architecture change:

1. add/update a dated decision record;
2. update `system.yaml` and `config/domains.yaml`;
3. update `config/tools.yaml` if runtime/tool roles changed;
4. update runtime docs only when live cutover actually occurs;
5. preserve historical decisions rather than deleting rationale.

Newest explicit decision wins.
