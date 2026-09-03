# Decision: People/Relationships becomes a first-class LLM4LIFE subsystem

**Date:** 2026-09-03  
**Status:** Accepted target architecture; implementation not started  
**Supersedes where conflicting:** the 2026-09-02 recommendation to keep all structured relationship operations in Obsidian frontmatter and defer Neon People tables indefinitely.

## Context

The user's people information is fragmented across Apple Contacts, Google Contacts, Calendar and an early-stage Obsidian relationship system.

A 2026-09-02 audit correctly identified strengths in the Obsidian model: human-readable notes, link-not-copy behavior, person folders, interaction notes and narrative context. That audit recommended improving Obsidian frontmatter before introducing a relationship backend.

The newer architecture direction is broader: LLM4LIFE needs durable cross-system identity resolution, provenance, idempotent imports, conservative deduplication, interaction metadata and relationship automation that future agents can operate without treating Markdown files or a SaaS contact app as a transactional machine-state backend.

## Decision

Create a **People/Relationships subsystem** with these boundaries:

1. **Neon/PostgreSQL** becomes the target owner for stable internal person identity, cross-system person references and structured relationship machine state.
2. **Obsidian** remains the owner for relationship narrative, reflections, long-form context, diary/history and nuanced human-readable notes.
3. **Google Contacts** becomes the preferred human-facing address-book projection/client after Apple/Google deduplication and verified cutover.
4. **Apple Contacts** should become a synchronized Apple-device client rather than an independently maintained second source of truth.
5. **LLM4LIFE personal actions** own concrete relationship follow-ups; Google Tasks is their execution/projection client.
6. **Google Calendar** owns real scheduled interactions and important fixed time commitments.
7. Communication providers remain evidence/ingress sources; complete private conversation history is not copied into LLM4LIFE by default.

The exact field-level authority for phone/email/address/birthday is intentionally left for Phase 1 validation. The default recommendation is Neon-owned structured contact state projected to Google Contacts once migration reliability is proven. If provider ownership is materially better after real API testing, the exception must be explicitly documented rather than creating silent bidirectional dual truth.

## Why

### Cross-system stable identity

A person needs one internal identity even if names, emails, contact records or source applications change. Google Contacts IDs and Obsidian filenames are useful external references but should not be the universal identity key.

### Machine state vs narrative knowledge

Structured state that drives deterministic automation belongs in a transactional machine-state store. Narrative human memory belongs in Obsidian. This preserves the strengths of the existing relationship notes without asking Markdown/frontmatter to become a synchronization database.

### Agent reliability

Future agents need:

- stable IDs;
- explicit owners;
- provenance;
- conflict rules;
- idempotency;
- migration gates;
- tests and rollback.

Those properties are difficult to guarantee if person resolution and operational state are spread across contact-app fields and free-form notes.

### Reuse existing action/calendar systems

Relationship follow-ups should not introduce another task lifecycle. Concrete actions belong in the existing LLM4LIFE action domain, and real scheduled interactions belong in Calendar.

## Consequences

### Positive

- one cross-system person identity;
- deterministic references across Contacts, Obsidian, Calendar and communication sources;
- reliable structured querying and automation;
- provenance-aware facts;
- conservative dedup/merge workflow;
- Obsidian narrative remains intact;
- no new paid personal CRM is required.

### Costs / risks

- private structured People data will exist in Neon and needs strong access discipline;
- contact migration requires careful deduplication and rollback;
- sync/conflict semantics must be proven before address-book cutover;
- over-modeling relationships could create unnecessary complexity;
- automated capture could become invasive/noisy without strict persistence rules.

These risks are addressed by phased rollout, least privilege, synthetic public fixtures, conservative merge rules and the minimum-useful-system principle.

## Invariants

Future implementations must preserve these unless a newer explicit decision supersedes them:

- display names are never primary identity keys;
- exact provider references beat fuzzy matching;
- same-name-only auto-merge is prohibited;
- ambiguous merges require review rather than guessing;
- structured facts retain provenance;
- sensitive inferred personal facts are not silently persisted;
- raw private conversation archival is opt-in/use-case-specific, not default;
- narrative relationship notes remain in private narrative systems rather than copied into the public repo;
- relationship follow-ups reuse the existing action domain;
- migration/import/sync operations are rerunnable/idempotent;
- destructive cleanup happens only after reconciliation and rollback verification.

## Migration sequence

1. **Phase 0:** documentation and architecture only.
2. **Phase 1:** schema design, tests and read-only Apple/Google contact inventory.
3. **Phase 2:** stable person identity import + external refs + conservative dedup.
4. **Phase 3:** address-book projection/cutover and Apple client synchronization.
5. **Phase 4:** Obsidian linking and conversational fact/interaction capture.
6. **Phase 5:** low-noise relationship automation.

See `docs/PEOPLE.md` for detailed gates, suggested schema and agent workflow.

## Open design space

This decision establishes boundaries, not every table/field forever.

Future agents are explicitly encouraged to propose materially better designs for:

- contact-field authority;
- schema/database boundaries;
- provenance representation;
- Apple Contacts migration path;
- Obsidian write integration;
- interaction granularity;
- relationship automation thresholds.

A recommendation should state the expected benefit, migration/rollback cost, security impact and duplicate-truth implications. Do not preserve a design merely because it is documented here.

## Runtime note

At the time of this decision:

- the People Neon schema has **not** been created;
- Apple/Google contact data has **not** been migrated;
- Google Contacts has **not** been cut over as projection/client;
- existing Obsidian relationship material remains intact and live as private context.

Target architecture is not proof of runtime cutover.
