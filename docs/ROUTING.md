# Routing

_Last updated: 2026-09-02_

## Goal

The user should be able to speak naturally from practical entry points. LLM4LIFE should infer the correct domain owner and act without forcing manual app selection.

## Canonical v2 routing

| Intent | Canonical destination / pattern |
|---|---|
| Personal action/reminder | Neon action state -> Google Tasks client; Calendar only when scheduled |
| Scheduled commitment/time | Google Calendar |
| Engineering bug/backlog | Jira |
| Code/PR/commit/release/repository state | GitHub |
| Coding-agent work | ORC |
| LLM4LIFE machine/automation state | Neon/PostgreSQL |
| Knowledge, reasoning, learning | Obsidian |
| Relationship/person context | Obsidian |
| Contact phone/email/address identity | Google Contacts after migration |
| Household/vehicle maintenance state | Neon/PostgreSQL |
| Grocery/shopping-list state | Neon/PostgreSQL |
| Consolidated finance state | InUnity |
| Official bank/card/brokerage record | respective provider |
| Work communication | Slack |
| Email source/intake | Gmail |
| Personal communication | originating/provider channel |

See `config/domains.yaml` for full ownership.

## Routing algorithm

1. Parse intent and identify the object type/domain.
2. Read `config/domains.yaml` for target ownership.
3. Check whether the domain has completed migration or still has a transitional live source.
4. Verify runtime access when a read/write is required.
5. Search before creating duplicates.
6. Use stable internal IDs plus external references when objects span systems.
7. Update the canonical record and create only necessary projections/execution objects.
8. Use idempotency keys for automated/retried writes.
9. Record a durable execution/action receipt when the backend is live.
10. Return a concise user receipt.

## Backlog vs execution

Target personal-action flow:

```text
Neon action
  |
  +--> Google Tasks     human action UI
  |
  +--> Google Calendar  only when execution time is reserved
```

Do not reconstruct canonical task state from Calendar alone.

Engineering work remains in Jira, not in the personal-action backend unless there is a genuinely separate personal reminder that links to the Jira item.

## Relationship information

Route different parts of a person to different owners:

```text
phone/email/address/birthday -> Google Contacts
relationship context         -> Obsidian
follow-up action             -> personal actions / Google Tasks
scheduled interaction        -> Google Calendar
```

Do not turn the Google Contacts notes field or Neon into a dump of relationship narrative.

## Provider/edge apps

Travel, food delivery, shopping, media, banking-provider, smart-home and similar apps are normally **execution/source surfaces**.

LLM4LIFE may compare or contextualize them, but should not persist full provider histories unless a concrete durable use case exists.

## Duplicate prevention

Avoid:

- Jira issue duplicated as a personal task instead of linked;
- Google Task and Neon action drifting as independent records;
- Calendar event treated as a permanent task record;
- Notion manually duplicating Neon/Jira/GitHub state;
- relationship narrative copied into Contacts + Obsidian + database;
- bank/provider state copied into LLM4LIFE merely for dashboard completeness.

## Migration routing rule

During v2 migration, a target owner may not yet be live.

When the current workflow still relies on a transitional source such as Notion:

- use the current live source when required to keep the workflow functioning;
- do not create new architectural dependence on it unnecessarily;
- migrate/reconcile the domain deliberately;
- do not silently dual-write indefinitely.

## Event-driven behavior

Preferred:

```text
event -> normalize -> deduplicate -> evaluate importance -> act -> receipt -> notify if useful
```

Important watchers should define:

- stable job/watcher identity;
- trigger/event type;
- deduplication/idempotency key;
- importance threshold;
- action;
- retry/failure policy;
- cooldown where relevant;
- destination/owner;
- execution receipt.

## Tool philosophy

Prefer native connectors/APIs, then supported app automation, then thin deterministic bridges. Add broad middleware or paid glue services only when they solve a demonstrated problem better than the existing/free options.
