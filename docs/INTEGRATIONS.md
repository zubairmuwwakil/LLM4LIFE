# Integrations

_Last updated: 2026-08-27_

## Principle

Prefer the shortest reliable path that preserves one canonical owner per responsibility.

Order of preference:

1. native supported connector/plugin;
2. supported app automation surface;
3. thin deterministic custom bridge;
4. broader middleware only when the first three are insufficient.

Avoid creating a mesh of app-to-app synchronization.

Prefer:

```text
source -> AI/router -> authoritative destination
```

over:

```text
Things <-> Notion <-> Jira <-> Obsidian <-> Slack
```

## Desired topology

```text
                           AI command layer
                    /            |            \
               ChatGPT        Claude        OpenClaw
                 |            coding          optional
          native connectors    specialist      plumbing
                 |
       +---------+---------+---------+---------+
       |         |         |         |         |
    GitHub     Notion   Calendar   Gmail     Slack
       |
       +---- bridges/gaps ----> Things / Jira / Discord / live Obsidian
```

This is conceptual. Always verify current runtime access in `docs/STATUS.md` before claiming a connection exists.

## Current verified direct paths

As of 2026-08-27 in the current ChatGPT runtime:

- **GitHub:** read/write verified.
- **Notion:** read/write verified.
- **Google Calendar:** read/write verified.
- **Gmail:** account/read path verified; connector exposes supported write actions.
- **Slack:** account/read path verified; connector exposes supported write actions.
- **ChatGPT Automations:** live and managing planning/digest/follow-up/inventory jobs.

See `config/tools.yaml` for machine-readable status.

## Current integration gaps

### Things 3

Canonical responsibility: personal backlog/actions.

Current situation: user-live, but no verified direct AI bridge.

Preferred bridges:

- Apple Shortcuts
- Things URL scheme
- AppleScript on macOS
- thin deterministic adapter using supported Things interfaces

Avoid unsupported direct database/cloud-credential manipulation.

This is the highest-value integration gap because the planner cannot fully schedule the personal backlog without reading Things.

### Jira

Canonical responsibility: engineering bugs/backlog.

Current situation: Jira remains authoritative, but direct Jira/Atlassian access should be verified at runtime before claiming reads/writes.

Desired behavior once connected:

- read eligible engineering backlog;
- update/create work items when authorized;
- link scheduled execution blocks back to Jira;
- never mirror the Jira database into Things/Notion.

### Obsidian live vault

Canonical responsibility: durable knowledge/context.

Current situation: the backed-up GitHub vault can be read/maintained, but a direct live local-vault bridge is not verified.

Desired end state:

```text
AI -> safe local bridge -> live Obsidian vault -> normal sync/backup
```

Do not confuse authorization to autonomously maintain notes with technical proof that the live vault is writable from the current runtime.

### Discord

Canonical responsibility: personal/life communication and desired personal notification surface.

Current situation: user-live, no direct ChatGPT Discord connector assumed.

Candidate path:

- OpenClaw if already deployed and useful;
- otherwise a thin channel bridge.

Avoid building a large integration platform just to send one type of notification.

## ChatGPT

Current role: primary conversational command/planning/orchestration center.

Use native connected capabilities when they satisfy the need. Do not rebuild a working native connector externally without a measurable reason.

## Claude / Claude Code

Current role: coding-heavy specialist.

Claude should read `CLAUDE.md` and `AGENTS.md` and follow the same ownership model rather than inventing a separate life/project architecture.

## OpenClaw

Current role: optional integration/channel plumbing where native capabilities are insufficient.

OpenClaw is not:

- a canonical database;
- a second policy authority;
- automatically required for every integration.

Verify deployment/config before depending on it.

## Slack

Slack is the work communication I/O surface.

Potential uses:

- receive work-context commands;
- search work context;
- deliver high-value work notifications/receipts;
- interact with engineering discussions.

Do not use Slack Later/pins/reminders as a competing task system when the action belongs in Jira/Things.

Externally consequential messages still follow `docs/AUTONOMY.md` safeguards.

## Discord

Discord is the personal communication I/O surface.

Personal messages may create Things tasks, Calendar commitments, Obsidian context, or Notion structured records through the AI router once a real bridge exists.

Discord itself should not become the permanent storage layer for those objects.

## Gmail

Gmail is an intake/source system.

Examples:

- bill/refund/deadline email -> detect actionable implication;
- route action to Things/Calendar as appropriate;
- route structured state to Notion if it belongs there;
- preserve source email link/provenance when useful.

Do not leave all obligations buried in email simply because email was the source.

## Google Calendar

Calendar is both:

- the canonical store for actual time commitments; and
- the execution surface for selected movable work.

It is **not** the permanent backlog.

The AI planner should convert eligible backlog into realistic Calendar blocks while preserving the original canonical task in Things/Jira.

Default movable-work window: **1 PM–9 PM America/Toronto**.

## Notion

Notion is a structured state store and the current audit location.

It should not become the integration hub merely because it can link to many services. Orchestration belongs in the AI layer.

## GitHub

GitHub owns code/repository truth and hosts this public policy repo.

It is also the current AI-accessible path to the Obsidian backup repository, but should not automatically become the permanent live-note editor.

## Integration evaluation checklist

Before adopting a new connector/platform, ask:

1. What recurring friction does it remove?
2. Which capability does it replace/improve?
3. Does it create another source of truth?
4. Is there already a paid/installed capability that can do this?
5. Does it preserve the canonical owner?
6. Is it reversible and maintainable?
7. Can an AI agent understand/debug it later?
8. What permissions/credentials does it require?
9. Can we solve the same problem with a thinner bridge?
10. Does the current runtime actually support it, or are we only assuming it does?

New credentials/permissions are not covered by the standing low-risk approval policy.

## Documentation requirements

When a bridge is actually deployed or removed:

- update `docs/STATUS.md`;
- update `docs/TOOL_REGISTRY.md`;
- update `config/tools.yaml`;
- update this file if topology changed;
- record a dated decision if it becomes a core dependency.
