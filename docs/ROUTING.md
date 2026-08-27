# Routing

_Last updated: 2026-08-27_

## Goal

The user should be able to speak naturally from almost anywhere. The AI layer should infer destination and act without forcing the user to manually choose an app first.

## Canonical routing rules

| Intent | Destination |
|---|---|
| Engineering bug / technical backlog | Jira |
| Code, PR, commit, release, repository state | GitHub |
| Personal action / reminder | Things 3 |
| Scheduled commitment / time-bound event | Google Calendar |
| Structured durable life/admin state | Notion |
| Thinking, learning, notes, durable knowledge | Obsidian |
| Work/software-engineering conversation | Slack |
| Personal conversation | Discord |
| Email source context | Gmail |

## Routing algorithm

1. Parse the user's actual intent, not just keywords.
2. Identify the authoritative system for that class of information.
3. Search/check for an existing item when duplication is plausible.
4. Update existing state instead of creating duplicates where possible.
5. Preserve source context with links or provenance.
6. Perform the safe write autonomously.
7. Log meaningful autonomous actions when the activity log is available.
8. Send a short receipt to the originating channel.

## Duplicate prevention

Avoid these common failure modes:

- copying a Jira bug into Things as a second task
- rebuilding GitHub project state in Notion
- storing the same durable notes in both Obsidian and Notion
- turning Calendar into a generic task list
- using Slack saves or Discord pins as permanent task systems

Link across systems when cross-reference is useful.

## Personal vs engineering actions

The distinction is based on responsibility, not where the request originated.

Example:

```text
Slack message: "The auth endpoint crashes on staging."
-> Jira issue
-> link source thread if useful
-> optional work receipt in Slack
```

```text
Slack message: "Remind me to call my insurer tomorrow."
-> Things 3 or Calendar depending on whether time is essential
-> receipt in Slack because Slack was the origin
```

## Notifications

Default notification surfaces:

- work-related -> Slack
- personal/life -> Discord

The originating channel can receive the immediate action receipt even if the destination system differs.

## Receipt format

Single action:

```text
Created JIRA-142 — Fix staging auth crash
```

Multiple actions:

```text
Done:
- Jira: JIRA-142 created
- Calendar: deadline added for Sept 3
- Slack: blocker notification sent
```

Receipts should be concise and include destination links/IDs when available.

## Event-driven behavior

Prefer:

```text
event -> evaluate importance -> act if appropriate -> log -> notify
```

Avoid:

```text
event -> notify user about everything
```

Potential monitored events include:

- failed CI/builds
- stale or blocking Jira issues
- upcoming deadlines
- action-required email
- low inventory
- renewals/expiries
- repeatedly deferred or neglected work

Every watcher should ideally define:

- trigger
- importance threshold
- action
- cooldown
- deduplication key
- notification destination

## Tool philosophy

Do not add automation middleware merely because it exists. Prefer native connectors, existing AI capabilities, Shortcuts/scripts, and a thin integration layer before adding another paid glue service.
