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
- add a clearly requested Calendar event
- classify/tag/route information
- create links between systems
- archive clearly stale low-value material when reversible
- deduplicate routine records
- resurface neglected important items

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
