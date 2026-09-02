# People, Contacts & Relationships Inventory

**Status:** Provisional / subject to change  
**Purpose:** Consolidate scattered contact and relationship state without forcing one application to own every aspect of a person record.

## Current situation

The user's people/contact information is currently fragmented across:

- Apple Contacts
- Google Contacts
- calendar entries / important dates
- **Obsidian, which is currently the main place relationship context is being stored**

The Obsidian relationship system is still early-stage and should not be treated as permanently fixed merely because it exists today.

## Current ownership

| Layer | Current owner / surface | Status |
|---|---|---|
| Contact identity | Apple Contacts + Google Contacts | Fragmented / needs consolidation |
| Relationship context | **Obsidian** | Current source for relationship notes/context; early-stage but already structurally useful |
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

This means the core concept is already good enough to preserve: **Obsidian can remain the narrative relationship-memory system.**

### What needs improvement

The current People area also contains migration/import residue and inconsistent generations of the system: some person folders contain older files, imported journal material, interaction folders, and duplicate-looking profile/summary files alongside the newer canonical-note convention.

The relationship dashboard is currently mostly manually curated and its `Recent interactions`, `Open loops`, and `Things to remember` sections are not yet driven by structured metadata.

The Person Template contains useful fields such as current status, connection level, last interaction and next step, but those values are currently body text rather than normalized frontmatter. That makes reliable querying and automation harder.

The Interaction Template is also primarily narrative. It has a follow-up section, but no normalized machine-readable date/person/type/follow-up state.

### Decision after audit

**Do not migrate relationship notes out of Obsidian.**

Instead, improve the existing private Obsidian system first. Add a thin structured metadata layer to canonical person and interaction notes so Dataview/automation can answer operational questions while narrative context remains readable Markdown.

Neon/PostgreSQL should not become the relationship source of truth yet. Introduce backend relationship tables only when a real cross-system automation requirement cannot be satisfied cleanly by Obsidian metadata plus Google integrations.

## Recommended production-grade model

Use three logical layers:

1. **Contact identity / address book**
   - name
   - phone numbers
   - email addresses
   - postal address
   - organization
   - birthday where appropriate

2. **Private relationship context**
   - how/where the person is known
   - important context worth remembering
   - interests/preferences when intentionally recorded
   - reflections and narrative notes
   - linked diary/history

3. **Operational relationship metadata**
   - relationship/category
   - status
   - last meaningful interaction
   - next follow-up date
   - optional check-in cadence
   - open-loop state
   - references to address-book identity

These layers may integrate, but they should not be forced into one vendor's contact-note field.

## Provisional long-term direction

| Layer | Provisional direction | Notes |
|---|---|---|
| **Canonical address book** | **Google Contacts** | Strong fit with Gmail / Google Calendar / Google Tasks; verify/deduplicate before finalizing migration |
| **Apple Contacts** | Synced Apple-device client | Prefer consuming the canonical contact set instead of maintaining a separate manually edited address book |
| **Relationship context** | **Obsidian** | Keep as primary private narrative relationship-memory system |
| **Structured relationship metadata** | **Obsidian frontmatter first** | Use machine-readable fields in canonical person/interaction notes before introducing another database |
| **Future backend relationship projection** | Optional private LLM4LIFE/Neon layer | Add only when cross-system querying, event processing, scale, or automation justifies it |
| **Follow-up tasks** | Google Tasks | Generate concrete actions from relationship metadata; tasks are execution, not relationship truth |
| **Scheduled meetings / fixed dates** | Google Calendar | Use for real commitments and date-specific interactions |

## Target architecture

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

## Automation goal

**The user should be able to tell the AI information naturally without manually maintaining the relationship database.**

Examples:

- “Tara is studying for another certification.”
- “I met Alex at a conference today.”
- “Remind me to check in with Jordan in three weeks.”
- “Kayla really likes this restaurant.”
- “I spoke with Sam today about changing jobs.”

LLM4LIFE should classify the information and route it to the correct owner rather than blindly appending everything to one note.

### Automated capture pipeline

```text
ChatGPT / messaging / manual capture / calendar context
                       |
                       v
                LLM4LIFE ingress
                       |
             classify + resolve person
                       |
        +--------------+----------------+
        |              |                |
        v              v                v
  contact identity  relationship     interaction/
      change          memory          observation
        |              |                |
 Google Contacts    Obsidian       Obsidian interaction
                                         |
                                         v
                                derive operational state
                                    /          \
                                   v            v
                             Google Tasks   Google Calendar
```

### Capture rules

1. **Durable personal fact/context** -> update the person's canonical Obsidian note.
2. **Meaningful interaction or event** -> create/link an interaction or diary note; do not duplicate the full event inside the person profile.
3. **Phone/email/address/birthday identity data** -> Google Contacts, with Obsidian storing only a provider reference where useful.
4. **Actionable promise/follow-up** -> record the relationship context in Obsidian and create a Google Task as the execution item.
5. **Actual scheduled meeting/date** -> Google Calendar.
6. **Temporary, uncertain, trivial, or conversational information** -> do not automatically persist it as durable relationship memory.
7. **Sensitive inferred claims** -> do not infer or persist them merely from message content; prefer explicit user-provided facts and observations.

## How Obsidian should be written automatically

The **local Obsidian vault remains the authoritative working copy**. Its private GitHub repository is backup/version history, not the preferred application API.

Long-term automation should therefore use a trusted local LLM4LIFE bridge/worker on the user's Mac to:

1. resolve the canonical person note;
2. make an atomic Markdown/frontmatter update locally;
3. preserve existing prose and links;
4. create an interaction note when appropriate;
5. validate frontmatter/schema;
6. let the existing Obsidian Git workflow version and push the resulting file changes.

Avoid routinely having cloud agents independently edit the remote Obsidian GitHub repository while the local vault is also changing; that creates avoidable merge/conflict risk.

Until the local bridge exists, relationship capture can remain conversational/manual and implementation work should focus on standardizing the schema first.

## Suggested canonical person metadata

The exact private template can evolve, but the architecture should support fields such as:

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

Do not duplicate phone numbers, email addresses, or canonical birthdays in this metadata if Google Contacts owns those values. Store references rather than redundant copies where possible.

## Suggested interaction metadata

Interaction notes can remain narrative while gaining lightweight frontmatter:

```yaml
type: interaction
interaction_id: <stable-private-id>
date: YYYY-MM-DD
people: []
interaction_type: <in_person|call|text|event|other>
follow_up_needed: false
follow_up_date: null
```

This allows Dataview or an automation layer to derive `last_interaction`, recent interactions and pending follow-ups instead of requiring manual dashboard maintenance.

## Derived state vs authored state

Prefer deriving operational fields from source events whenever reliable:

- `last_interaction` should eventually be derivable from interaction notes rather than manually maintained in multiple places;
- dashboard `Recent interactions` should be a query;
- `Open loops` should be derived from structured follow-up/open-loop metadata;
- follow-up tasks can be projected into Google Tasks without making Google Tasks the relationship source of truth.

This keeps the system resilient to missed manual updates.

## Questions the system should answer

- Who have I not spoken to in a while?
- What context do I have about this person?
- Who did I say I would follow up with?
- What follow-ups are overdue?
- What birthdays or important dates are coming up?
- Who should I reconnect with this month?
- What was my most recent meaningful interaction with this person?

## Migration / cleanup approach

1. Keep all existing relationship content intact during cleanup.
2. Establish exactly one canonical person note per person.
3. Identify legacy/imported duplicate-looking files and either link, merge intentionally, or archive them; never delete merely because names overlap.
4. Standardize the Person Template frontmatter.
5. Standardize the Interaction Template frontmatter.
6. Convert the Relationships Dashboard from manually maintained lists toward derived Dataview/Bases views where practical.
7. Inventory and deduplicate Apple Contacts vs Google Contacts.
8. If Google Contacts is confirmed as canonical, sync it to Apple devices and stop independently editing both stores.
9. Build a trusted local relationship-write adapter for LLM4LIFE so conversational capture can safely update the vault.
10. Add person-resolution logic so names/aliases/contact IDs map to one stable private `person_id`.
11. Generate Google Tasks for due follow-ups rather than duplicating relationship state in Tasks.
12. Use Google Calendar only when an interaction is actually scheduled or date-specific.
13. Re-evaluate Neon only after the improved Obsidian system reveals a concrete limitation.

## Privacy boundaries

- The public LLM4LIFE repository contains architecture, schemas and placeholders only — never actual contact data or relationship notes.
- Relationship context remains in private systems.
- Actual provider contact IDs and person IDs are private data and should not be committed to LLM4LIFE.
- Do not ingest or retain complete personal conversations by default merely because an integration technically allows it.
- Prefer least-privilege access and explicit source references.
- Automation must distinguish explicit user-provided information from model inference; inferred sensitive facts should not silently become durable person records.

## Free-first constraint

Prefer free or already-paid-for components. The current stack can provide a capable personal relationship-management system without adding a paid personal CRM.
