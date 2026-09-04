# People, Contacts & Relationships Inventory

> **Historical audit note — superseded architecture:** This document preserves the 2026-09-02 inventory/audit and the rationale that existed at that time. Its recommendation to keep structured relationship operations in Obsidian frontmatter and defer Neon People tables has been superseded by `docs/decisions/2026-09-03-people-subsystem-architecture.md`. The current implementation contract is `docs/PEOPLE.md`. Preserve the audit evidence below, but do not treat its old target architecture as current.

**Status:** Historical inventory / useful source audit  
**Original purpose:** Consolidate scattered contact and relationship state without forcing one application to own every aspect of a person record.

## Current situation at time of audit

The user's people/contact information was fragmented across:

- Apple Contacts
- Google Contacts
- calendar entries / important dates
- **Obsidian, which was the main place relationship context was being stored**

The Obsidian relationship system was early-stage and was not intended to be treated as permanently fixed merely because it existed.

## Ownership observed at time of audit

| Layer | Current owner / surface | Status at audit |
|---|---|---|
| Contact identity | Apple Contacts + Google Contacts | Fragmented / needs consolidation |
| Relationship context | **Obsidian** | Current source for relationship notes/context; early-stage but structurally useful |
| Follow-up state | Scattered / ad hoc | No dedicated canonical system yet |
| Fixed dates / meetings | Google Calendar direction | Execution surface, not relationship database |

## Obsidian audit — 2026-09-02

The existing vault was inspected before recommending a replacement.

### What is already strong

The current vault follows a good knowledge-architecture principle: **link, do not copy**.

The People system has:

- a `20 Areas/People/` domain with person-specific folders;
- a canonical person-note convention using `00 <Name>.md`;
- `type: person` and `aliases:` frontmatter for identity/link resolution;
- a `Person Template` for consistent human-readable profiles;
- an `Interaction Template` for meaningful interactions;
- diary entries that link to people rather than restating the same event in multiple places;
- per-person `Mentions — <Name>` notes using Dataview/backlinks to surface linked diary and other notes;
- a People MOC and a Relationships Dashboard as navigation/projection layers.

This remains important evidence for the current architecture: **Obsidian is a strong narrative relationship-memory system and should not be replaced by database blobs.**

### What needs improvement

The current People area also contains migration/import residue and inconsistent generations of the system: some person folders contain older files, imported journal material, interaction folders, and duplicate-looking profile/summary files alongside the newer canonical-note convention.

The relationship dashboard is mostly manually curated and its `Recent interactions`, `Open loops`, and `Things to remember` sections are not yet driven by reliable structured machine state.

The Person Template contains useful fields such as current status, connection level, last interaction and next step, but those values are body text rather than consistently normalized machine-readable state.

The Interaction Template is also primarily narrative. It has a follow-up section, but no normalized machine-readable date/person/type/follow-up state.

### Historical recommendation after audit

The 2026-09-02 recommendation was:

**Do not migrate relationship notes out of Obsidian. Improve structured frontmatter first, and introduce Neon relationship tables only after a concrete cross-system limitation appears.**

The first sentence remains current: narrative relationship notes should stay in Obsidian.

The second part is now superseded. On 2026-09-03, the target changed to a first-class People subsystem where Neon owns stable internal person identity and structured relationship machine state, while Obsidian keeps narrative context.

See `docs/PEOPLE.md` for the current target and migration gates.

## Durable findings that still apply

Use distinct logical layers even though current target ownership has changed:

1. **Stable person identity / address-book state**
   - stable person identity
   - cross-system references
   - name/contact fields where authority is intentionally established
   - organization/birthday where appropriate

2. **Private relationship narrative**
   - how/where the person is known
   - important nuanced context worth remembering
   - reflections and narrative notes
   - linked diary/history

3. **Operational relationship metadata**
   - relationship/category/status
   - last meaningful interaction
   - follow-up/cadence/open loops
   - structured facts with provenance

The current architecture assigns layers 1 and 3 to Neon after migration, and layer 2 to Obsidian.

## Historical target architecture

The diagram below is preserved to explain the previous recommendation; it is **not the current target**.

```text
                   Google Contacts
               canonical contact identity
                        |
                        | contact reference
                        v
             +------------------------+
             |        Obsidian        |
             | canonical person note  |
             | narrative context      |
             | linked diary/history   |
             | structured frontmatter |
             +-----------+------------+
                         |
              due/open operational state
                +--------+--------+
                |                 |
                v                 v
          Google Tasks      Google Calendar
           follow-ups       scheduled events

Only if future requirements justify it:
Obsidian metadata -> LLM4LIFE event/projection layer -> Neon
```

Current target is documented in `docs/PEOPLE.md`.

## Automation goal that remains valid

**The user should be able to tell the AI information naturally without manually maintaining the relationship database.**

LLM4LIFE should classify the information, resolve the person conservatively, preserve provenance, and route it to the correct owner rather than blindly appending everything to one note.

### Durable capture lessons

1. **Narrative durable context** -> Obsidian.
2. **Structured durable fact with operational/query value** -> current People architecture targets Neon with provenance.
3. **Meaningful interaction** -> minimal structured metadata when useful; narrative detail can remain in Obsidian.
4. **Actionable promise/follow-up** -> existing LLM4LIFE personal action domain / Google Tasks projection.
5. **Actual scheduled meeting/date** -> Google Calendar.
6. **Temporary, uncertain, trivial, or conversational information** -> do not automatically persist it as durable relationship memory.
7. **Sensitive inferred claims** -> do not infer or persist them merely from message content; prefer explicit user-provided facts and observations.

## Obsidian write-path finding that remains valid

The **local Obsidian vault remains the authoritative working copy for narrative notes**. Its private GitHub repository is backup/version history, not the preferred application API.

Long-term automation should use a trusted local LLM4LIFE bridge/worker on the user's Mac to:

1. resolve the canonical person note;
2. make an atomic Markdown/frontmatter update locally;
3. preserve existing prose and links;
4. create an interaction note when appropriate;
5. validate frontmatter/schema;
6. let the existing Obsidian Git workflow version and push the resulting file changes.

Avoid routinely having cloud agents independently edit the remote Obsidian GitHub repository while the local vault is also changing; that creates avoidable merge/conflict risk.

## Historical suggested person metadata

This was the original Obsidian-frontmatter proposal and remains useful as migration input, not current canonical machine-state design:

```yaml
type: person
person_id: <stable-private-id>
aliases: []
contact_provider: google
contact_ref: <provider-resource-id>
relationship_type: <family|friend|partner|professional|other>
status: <active|occasional|dormant|archived>
last_interaction: YYYY-MM-DD
next_follow_up: YYYY-MM-DD
follow_up_cadence_days: null
open_loops: 0
```

Current architecture should avoid duplicating these structured values in both Obsidian and Neon. Narrative notes should link to the stable person identity; machine state should have one owner.

## Historical suggested interaction metadata

```yaml
type: interaction
interaction_id: <stable-private-id>
date: YYYY-MM-DD
people: []
interaction_type: <in_person|call|text|event|other>
follow_up_needed: false
follow_up_date: null
```

The current design moves deterministic interaction metadata/provenance toward Neon while allowing narrative interaction notes to remain in Obsidian.

## Derived state vs authored state

This principle remains current:

- derive `last_interaction` from reliable interaction records where possible;
- derive dashboards/views rather than manually copying values;
- derive open loops from structured action/follow-up state;
- project follow-up actions into Google Tasks without making Google Tasks the relationship source of truth.

## Questions the system should answer

- Who have I not spoken to in a while?
- What context do I have about this person?
- Who did I say I would follow up with?
- What follow-ups are overdue?
- What birthdays or important dates are coming up?
- Who should I reconnect with this month?
- What was my most recent meaningful interaction with this person?

These questions remain useful acceptance criteria for the People subsystem.

## Migration/cleanup findings that remain useful

1. Keep all existing relationship content intact during cleanup.
2. Establish exactly one stable internal identity per real person.
3. Identify legacy/imported duplicate-looking files and link/merge/archive intentionally; never delete merely because names overlap.
4. Preserve Obsidian person/interaction narrative.
5. Convert manually maintained views toward derived state where useful.
6. Inventory and deduplicate Apple Contacts vs Google Contacts before cutover.
7. Build a trusted local relationship-write adapter for Obsidian narrative capture when practical.
8. Add person-resolution logic so names/aliases/provider IDs map conservatively to one stable private person ID.
9. Generate Google Tasks through the existing personal-action domain rather than duplicating relationship state in Tasks.
10. Use Google Calendar only when an interaction is actually scheduled/date-specific.

The current detailed phased migration is in `docs/PEOPLE.md`.

## Privacy boundaries

- The public LLM4LIFE repository contains architecture, schemas and placeholders only — never actual contact data or relationship notes.
- Relationship context remains in private systems.
- Actual provider contact IDs and person IDs are private data and should not be committed to LLM4LIFE.
- Do not ingest or retain complete personal conversations by default merely because an integration technically allows it.
- Prefer least-privilege access and explicit source references.
- Automation must distinguish explicit user-provided information from model inference; inferred sensitive facts should not silently become durable person records.

## Free-first constraint

Prefer free or already-paid-for components. The current stack can provide a capable People/relationship system without adding a paid personal CRM.
