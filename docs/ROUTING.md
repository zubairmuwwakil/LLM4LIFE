# Routing

_Last updated: 2026-09-03_

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
| Stable person identity / structured People state | Neon **target after People migration** |
| Relationship narrative / reflections | Obsidian |
| Address-book UI | Google Contacts **after People/contact dedup cutover** |
| Relationship follow-up | Existing Neon personal action -> Google Tasks |
| Scheduled interaction | Google Calendar |
| Household/vehicle maintenance state | Neon/PostgreSQL |
| Grocery/shopping-list state | Neon/PostgreSQL |
| Consolidated finance state | InUnity |
| Official bank/card/brokerage record | respective provider |
| Work communication | Slack |
| Email source/intake | Gmail |
| Personal communication | originating/provider channel |

See `config/domains.yaml` for full ownership and `docs/PEOPLE.md` for People-specific rules.

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

## People and relationship information

The People target is a split between structured machine state and narrative context:

```text
stable person_id / external refs ------> Neon (after People migration)
structured relationship state --------> Neon (after People migration)
structured facts + provenance --------> Neon (after People migration)
relationship narrative/reflections ---> Obsidian
address-book human UI ----------------> Google Contacts after dedup/cutover
follow-up action ----------------------> Neon personal action -> Google Tasks
scheduled interaction ----------------> Google Calendar
communication evidence ---------------> originating provider; link, do not archive wholesale
```

**Runtime warning:** People is currently Phase 0 documentation. Apple/Google Contacts remain fragmented and the People Neon schema has not been implemented yet. Do not route live writes to a nonexistent backend merely because the target is documented.

When the People runtime is built, resolve a person by stable ID/external refs before fuzzy signals. Same-name-only auto-merge is prohibited.

Do not turn Google Contacts notes, Neon JSON blobs, or Obsidian into competing copies of the same relationship narrative.

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
- one person duplicated because names differ slightly across sources;
- two different people merged because their names match;
- bank/provider state copied into LLM4LIFE merely for dashboard completeness.

## Migration routing rule

During v2 migration, a target owner may not yet be live.

When the current workflow still relies on a transitional source:

- use the current live source when required to keep the workflow functioning;
- do not create new architectural dependence on it unnecessarily;
- migrate/reconcile the domain deliberately;
- do not silently dual-write indefinitely;
- preserve external IDs and rollback.

For People specifically, read-only inventory and dedup analysis comes before canonical import or contact-provider mutation.

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
