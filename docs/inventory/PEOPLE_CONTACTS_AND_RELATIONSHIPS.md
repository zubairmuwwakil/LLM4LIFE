# People, Contacts & Relationships Inventory

**Status:** Provisional / subject to change  
**Purpose:** Consolidate scattered contact and relationship state without forcing one application to own every aspect of a person record.

## Current situation

The user's people/contact information is currently fragmented across:

- Apple Contacts
- Google Contacts
- calendar entries / important dates
- **Obsidian, which is currently the main place relationship context is being stored**

The Obsidian relationship system is still early-stage and should not be treated as a permanently fixed architecture merely because it exists today.

## Current ownership

| Layer | Current owner / surface | Status |
|---|---|---|
| Contact identity | Apple Contacts + Google Contacts | Fragmented / needs consolidation |
| Relationship context | **Obsidian** | Current source for relationship notes/context; early-stage and provisional |
| Follow-up state | Scattered / ad hoc | No dedicated canonical system yet |
| Fixed dates / meetings | Calendar | Useful execution surface, not relationship database |

## Recommended production-grade model

Do not treat an address book as a complete relationship-management system.

Use three logical layers:

1. **Contact identity / address book**
   - name
   - phone numbers
   - email addresses
   - postal address
   - organization
   - birthday where appropriate

2. **Private relationship context**
   - relationship type
   - how/where the person is known
   - important context worth remembering
   - interests/preferences when intentionally recorded
   - last meaningful interaction
   - relationship-specific notes

3. **Follow-up / action state**
   - next follow-up date
   - recurring check-in cadence if intentionally set
   - promises / commitments
   - tasks arising from conversations
   - important upcoming dates

These layers may integrate, but they should not be forced into one vendor's contact-note field.

## Provisional long-term direction

| Layer | Provisional direction | Notes |
|---|---|---|
| **Canonical address book** | **Google Contacts** | Strong fit with Gmail / Google Calendar / Google Tasks and has a documented People API; verify during migration before finalizing |
| **Apple Contacts** | Synced Apple-device client | Prefer consuming the canonical contact set instead of maintaining a separate manually edited address book |
| **Relationship context** | **Obsidian for now** | Keep as current source while the workflow is still developing; do not migrate merely for architectural neatness |
| **Structured relationship metadata** | Possible future private LLM4LIFE backend (Neon/PostgreSQL) | Add only if structured querying, reminders, integrations, or automation justify it |
| **Follow-up tasks** | Google Tasks | Use for concrete actions generated from relationship state |
| **Scheduled meetings / fixed dates** | Google Calendar | Use for real commitments and important dates, not as a relationship-history database |

## Target direction under evaluation

```text
                  Google Contacts
              canonical contact identity
                       |
                       v
                 relationship layer
             currently: Obsidian notes
                       |
             +---------+----------+
             |                    |
             v                    v
        Google Tasks        Google Calendar
         follow-ups          fixed dates/events

Future only if justified:
Obsidian relationship context <-> private structured metadata in Neon

Apple Contacts = synced Apple-device client for the canonical address book
```

## Obsidian's current role

Obsidian is presently the most important relationship-context system because it already stores personal notes and linked context about people.

Do not prematurely replace it.

The main question for implementation is whether Obsidian alone remains sufficient or whether a small structured private backend should complement it.

A likely production-grade split, if needed, would be:

- **Obsidian:** narrative context, relationship notes, reflections, human-readable memory;
- **structured backend:** person IDs, contact mappings, last-contact date, next-follow-up date, cadence, status and integration references;
- **Google Contacts:** phone/email/address-book identity;
- **Google Tasks:** actionable follow-ups;
- **Google Calendar:** actual scheduled interactions and fixed dates.

This avoids copying narrative notes into a database merely because a database exists.

## Questions the eventual system should answer

- Who have I not spoken to in a while?
- What context do I have about this person?
- Who did I say I would follow up with?
- What birthdays or important dates are coming up?
- Who should I reconnect with this month?

## Migration approach

During implementation:

1. inventory and deduplicate Apple Contacts vs Google Contacts;
2. verify whether Google Contacts should become canonical;
3. preserve the current Obsidian relationship notes and links;
4. inspect how the existing Obsidian people system is structured before changing it;
5. only create private structured relationship tables if a concrete automation/querying need cannot be handled cleanly by Obsidian metadata plus integrations;
6. generate Google Tasks for actionable follow-ups rather than creating calendar clutter;
7. use Google Calendar only when an interaction is actually scheduled or date-specific.

## Privacy boundaries

- The public LLM4LIFE repository should contain architecture, schemas and placeholders only — never actual private contact data or relationship notes.
- Relationship context belongs in private systems such as the user's Obsidian vault and, if later justified, private backend storage.
- Do not ingest or retain complete personal conversations by default merely because an integration technically allows it.
- Prefer least-privilege access and explicit source references.

## Free-first constraint

Prefer free or already-paid-for components. Do not introduce a paid personal CRM unless it provides a clear advantage that cannot reasonably be achieved with the existing stack.
