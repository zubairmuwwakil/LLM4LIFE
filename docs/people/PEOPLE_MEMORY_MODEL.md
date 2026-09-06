# People memory model

**Phase:** People Phase 4  
**Purpose:** keep Obsidian as rich narrative authority while promoting only durable, reviewable, operational People memory into Neon.

## Storage boundary

Use the narrowest structured store that matches the memory:

| Memory | Store | Examples |
| --- | --- | --- |
| Durable person attribute or preference | `llm4life.person_facts` | interests, work/education, food/order preferences, background |
| Important or recurring date | `llm4life.person_dates` | birthday, anniversary, annual remembrance, custom important date |
| User-to-person relationship state | `llm4life.relationships` | friend/partner/family relationship to the user, cadence, active/dormant |
| Person-to-person relationship | `llm4life.person_relationship_edges` | parent, child, sibling, partner, friend, coworker |
| Dated event involving people | `llm4life.interactions` + `interaction_people` | meetup, meal, trip, call, gift given |
| Follow-up / next step | `llm4life.actions` + `action_people` | buy gift, check in, follow up, plan activity |
| Rich narrative or subjective context | Obsidian | diary prose, detailed history, nuanced impressions |

Do not convert narrative into structured memory just because it can be parsed.

## Important dates

`person_dates` supports date-only memory even when a year is unknown. `month` and `day` are required; `year` is optional. `recurrence` is either `annual` or `none`.

Recommended `date_type` values are open vocabulary but should remain stable machine keys, for example:

- `birthday`
- `friendship_anniversary`
- `relationship_anniversary`
- `memorial`
- `important_date`

Date records carry provenance, confidence, sensitivity, and supersession state. Invalid month/day combinations are rejected by the database.

## Person-to-person graph

`person_relationship_edges` is distinct from `relationships`:

- `relationships` describes the user's relationship with one person.
- `person_relationship_edges` describes one resolved Person relative to another resolved Person.

The edge is directional. For example, `source_person_id=A`, `target_person_id=B`, `relationship_type=parent` means A is a parent of B. Symmetric concepts such as `sibling` or `friend` can be queried from either endpoint; importers should avoid manufacturing a reverse edge unless the source or canonicalization policy requires it.

Unresolved names must not enter this table. They stay in private candidate review until identity resolution is explicit.

## Provenance and safety

Both structured memory tables follow the People safety model:

- People IDs are stable Neon UUIDs.
- source system and optional external-ref provenance are retained.
- confidence is bounded to 0..1.
- standard and sensitive records are distinguished.
- sensitive model suggestions are rejected.
- supersession/retraction is preferred over destructive deletion.
- no diary prose or Obsidian note paths belong in these tables.
- name-only or fuzzy matching never creates a durable relationship edge.

## Promotion policy

Promote when the source is explicit and the memory is useful operationally. Examples include a clearly stated birthday, a resolved sibling relationship, a stable food preference, or a dated meetup.

Keep in Obsidian when the content is subjective, interpretive, context-heavy, or likely to change without an explicit source. Examples include vibe scores, inferred motives, attachment labels, compatibility judgments, or free-form relationship analysis.

## Query goals

This model supports future workflows such as:

- upcoming birthdays and anniversaries;
- gift ideas based on durable preferences and prior gift interactions;
- relationship-aware context before a meetup;
- family/social graph traversal;
- stale-contact and check-in suggestions;
- open-loop reminders tied to a person;
- retrieving structured memory first, then selectively opening Obsidian narrative only when deeper context is needed.
