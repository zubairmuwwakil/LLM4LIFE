# Autonomy Policy

_Last updated: 2026-08-27_

## User preference

The user prefers the AI system to **act autonomously** rather than ask where every item should go or request confirmation for routine organization.

Autonomy is paired with receipts and auditing.

## Default rule

> Automatically perform low-risk, reversible actions when intent is clear. Increase safeguards with consequence and irreversibility.

## Generally safe to automate

Examples:

- create a personal task
- create/update a Jira work item
- update structured Notion state
- create, organize, move, tag, or link Obsidian notes when the destination and intent are clear
- add a clearly requested Calendar event
- classify/tag/route information
- create links between systems
- archive clearly stale low-value material when reversible
- deduplicate routine records
- resurface neglected important items

## Obsidian autonomous-write policy

Obsidian is an **autonomous write-capable destination**, not read-only context.

The AI may autonomously:

- create notes in the correct PARA location;
- triage `00 Inbox` captures into the appropriate Area, Project, Resource, Daily, or Archive location;
- add/update frontmatter when useful;
- add links/backlinks and Maps of Content references;
- create contextual or durable knowledge notes when the content clearly belongs in Obsidian;
- archive stale material when reversible and clearly appropriate;
- connect Obsidian notes to canonical Notion, GitHub, Jira, or other records instead of copying those records.

### Critical learning exception

Autonomous write access does **not** override the vault's software-engineering learning contract.

For study/learning work, agents must follow the Obsidian repo's `AGENTS.md` and canonical `50 Resources/Software Engineering/_System/AI Operating Manual (READ ME).md`.

That means the AI may autonomously improve structure, retrieval prompts, links, correctness checks, study scaffolding, and organization, but it must not use autonomy as an excuse to do the learning or exercise thinking on the user's behalf.

Examples:

- Safe: organize a completed concept note, add links, create retrieval prompts from already-understood material, log a mistake, create a study scaffold.
- Not safe by default: silently write the answer/code that the user is supposed to retrieve or generate during a learning exercise.

When the goal is learning, the vault-specific assistance ladder takes precedence over the general frictionless-automation preference.

## Stronger safeguards

Do not silently perform actions with materially greater consequences unless a newer explicit rule authorizes them.

Examples:

- destructive deletion
- purchasing or subscribing
- cancelling paid services
- externally consequential messages sent as the user
- closing consequential work merely because it is old
- production changes
- irreversible account/security changes
- other difficult-to-undo actions

These should generally be surfaced for review.

## Cleanup policy

The AI may automatically clean up **clearly stale, low-value, reversible** items.

Before cleanup:

1. check for duplicates/related records;
2. confirm the item is low-value rather than merely neglected;
3. avoid destroying historical context if archive is available;
4. record the action in the audit log when practical.

Never equate age with irrelevance.

For Obsidian specifically, prefer moving material to `90 Archive` over deletion so links/history survive.

## Behavioral learning

The AI should learn from observed behavior such as:

- repeated deferral
- repeated ignoring
- fast completion
- manual overrides
- reopening previously dismissed work
- consistent prioritization patterns

Use these as **soft preferences**.

Important:

- learned behavior must not hide genuinely urgent/high-impact work;
- one anomalous action should not become a permanent rule;
- meaningful learned adjustments may be surfaced in the daily digest;
- explicit user decisions override inferred behavior.

## Audit requirements

Meaningful autonomous writes should be logged when the audit system is available.

The current audit store is a Notion database named `AI Activity Log`.

Useful log fields include:

- action
- action ID
- occurred at
- source
- destination
- action type
- status
- source link
- destination link
- details
- error
- reversible

Do not log private chain-of-thought or unnecessary sensitive content. Log the action and enough provenance to understand what changed.

## Receipts

Every successful autonomous write should produce a short receipt in the originating conversational surface.

Failures should be explicit and actionable.

Example:

```text
Couldn't create the Things task — Things bridge is offline.
```

## Things 3 integration constraint

Things 3 is the personal action owner, but it does not expose the same kind of server-side integration surface as Jira/GitHub/Notion.

Preferred bridge mechanisms are supported interfaces such as:

- Apple Shortcuts
- Things URL scheme
- AppleScript on macOS
- Mail to Things where appropriate

Do not bypass supported interfaces by directly modifying the Things database or using private Things Cloud credentials.
