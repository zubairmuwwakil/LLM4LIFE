# Integrations

_Last updated: 2026-08-27_

## Desired topology

```text
                       AI command layer
                    /         |         \
              ChatGPT      Claude     OpenClaw
                  |            |          |
           native plugins    coding    channel/custom
                  |                       plumbing
                  +------------+------------+
                               |
             +-----------------+------------------+
             |                 |                  |
           Jira             Notion             GitHub
           Things 3         Calendar           Gmail
           Slack            Discord            Obsidian
```

This is a conceptual topology, not a requirement that every vendor be used for every operation.

## Integration rule

Prefer the shortest reliable path:

1. native integration/plugin when it fully satisfies the need;
2. supported app automation surface;
3. thin custom integration;
4. broader automation middleware only if the first three are insufficient.

Avoid creating a mesh of app-to-app synchronization.

Prefer:

```text
source -> AI/router -> authoritative destination
```

over:

```text
Things <-> Notion <-> Jira <-> Obsidian <-> Slack
```

## ChatGPT

Current intended role: primary conversational command center where connected tools provide sufficient read/write access.

Use native connected capabilities when practical rather than rebuilding them externally.

## Claude

Current intended role: coding-heavy work/agent usage.

Claude should still respect the same ownership/routing rules in this repo rather than inventing a separate productivity architecture.

## OpenClaw

Current intended role: optional integration/channel infrastructure, especially where reaching the AI from arbitrary surfaces or custom plumbing is valuable.

Do not make OpenClaw a second competing system of record or duplicate AI policy unnecessarily.

## Things 3 bridge

Things 3 remains the personal action system.

Preferred supported bridges:

- Apple Shortcuts
- Things URL scheme
- AppleScript on macOS
- Mail to Things when appropriate

Avoid unsupported direct database/cloud credential manipulation.

## Slack and Discord

Slack and Discord serve both as communication contexts and potential AI entry/notification surfaces.

- Slack defaults to work context.
- Discord defaults to personal context.

A command issued in one channel may route to a different underlying system while returning its receipt to the origin.

## Notion

Notion is both:

1. a structured personal/life-state store; and
2. the current location of the AI Activity Log.

Notion should not become the integration hub merely because it can link to many services. The AI/router layer owns orchestration.

## Obsidian

Obsidian is intentionally treated as a knowledge/thinking system rather than a workflow database.

Integrations should preserve local/durable note ownership and avoid copying all structured Notion data into the vault.

## Gmail

Email is an intake/source system. When an email implies an action or state change, route the resulting object to its authoritative destination while preserving a link/reference to the source email when possible.

## Future integration decisions

When evaluating a new connector or platform, ask:

1. What friction does it remove?
2. Which current capability does it replace or improve?
3. Does it create another source of truth?
4. Can an existing paid/installed capability already do the job?
5. Is the integration reversible and maintainable?
6. Will an AI agent be able to understand and debug it later?

Add a decision-log entry before making a new integration a core architectural dependency.
