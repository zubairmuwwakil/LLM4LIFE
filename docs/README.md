# Documentation Index

LLM4LIFE has multiple documentation layers because **architecture, runtime connectivity, policy, automation configuration, and historical decisions are different kinds of truth**.

Do not copy the same information into every file. Update the narrowest authoritative document and link to it elsewhere.

## What to read for what

| Question | Authoritative file(s) |
|---|---|
| What is connected/live right now? | `STATUS.md`, `../config/tools.yaml` |
| What does each tool own and who uses it? | `TOOL_REGISTRY.md`, `../config/tools.yaml` |
| What is the high-level architecture? | `../system.yaml`, `CURRENT_STATE.md` |
| Where should an item be routed? | `ROUTING.md` |
| How should backlog become a day plan? | `PLANNING.md`, `../config/scheduling.yaml` |
| What automations are active and how do they interact? | `AUTOMATIONS.md`, `../config/automations.yaml` |
| What should the morning digest do? | `DIGEST.md` |
| What may AI do autonomously? | `AUTONOMY.md` |
| How may AI learn/change low-risk rules? | `ADAPTATION.md` |
| How should missing workflows be detected/built? | `GAP_DETECTION.md` |
| What gets captured from conversations into Obsidian? | `KNOWLEDGE_CAPTURE.md` |
| How should People/Contacts/Relationships be designed or migrated? | `PEOPLE.md`, `decisions/2026-09-03-people-subsystem-architecture.md` |
| How should connectors/bridges be designed? | `INTEGRATIONS.md` |
| What can be public / what must remain private? | `SECURITY.md` |
| Why was a choice made? | `DECISIONS.md`, `decisions/` |
| What should an AI agent do first? | `../AGENTS.md` |

## Truth categories

### Runtime truth

Examples:

- connector exists today;
- write path is verified;
- automation is enabled;
- current scheduling window.

Use `STATUS.md` and machine-readable config.

Runtime truth can change without changing the architecture.

### Architectural truth

Examples:

- Neon owns LLM4LIFE machine state;
- Calendar owns scheduled execution, not backlog;
- AI is the scheduler/router;
- People structured machine state has a target owner even while migration is incomplete.

Use `system.yaml`, `CURRENT_STATE.md`, domain policy docs such as `PEOPLE.md`, and dated decisions.

### Authorization/policy truth

Examples:

- AI may autonomously merge low-risk Obsidian notes when the correct write path exists;
- purchases are not pre-approved;
- low-risk scheduling changes are pre-approved.

Use `AUTONOMY.md`, `ADAPTATION.md`, `KNOWLEDGE_CAPTURE.md`, `PEOPLE.md`, `SECURITY.md`.

### Historical truth

Examples:

- why Notion was narrowed to personal operations;
- why monthly tool audits were rejected;
- why an earlier People audit favored Obsidian frontmatter before a newer architecture decision changed the target.

Use decision records and inventory/audit documents.

Historical decisions explain the path; they do not automatically override a newer explicit current policy.

## Precedence

When documentation appears to conflict:

1. newest explicit user decision/instruction;
2. current safety/security constraints;
3. verified runtime truth for questions of technical access;
4. newest explicit decision record;
5. current policy/config docs;
6. older narrative/historical notes.

A runtime limitation does not change target canonical ownership. Conversely, a target owner does not prove its migration is live.

## Documentation update rule

When something changes, update only the necessary layers.

### Connector becomes available

Update:

- `STATUS.md`
- `TOOL_REGISTRY.md`
- `../config/tools.yaml`
- `INTEGRATIONS.md` if topology changed
- decision record if it becomes a core dependency

### Automation changes

Update:

- `AUTOMATIONS.md`
- `../config/automations.yaml`
- relevant policy (`PLANNING.md`, `DIGEST.md`, etc.)
- `STATUS.md` when operationally material

### Ownership/routing changes

Update:

- `../system.yaml`
- `../config/domains.yaml`
- `CURRENT_STATE.md`
- `TOOL_REGISTRY.md`
- `ROUTING.md`
- domain contract when one exists (for example `PEOPLE.md`)
- dated decision record

### Scheduling preference changes

Update:

- `../config/scheduling.yaml`
- `PLANNING.md`
- active planning automations
- decision record if material

## Public-repo discipline

This documentation repository is public.

Do not improve documentation completeness by copying private state into it.

Good documentation explains **classes of data, flows, permissions, roles, limitations, and behavior**. It does not need the user's private message bodies, account numbers, private contact profiles, or diary/health contents.

See `SECURITY.md`.

## Anti-drift rule for AI agents

Before adding a new markdown file, ask:

1. Does an existing authoritative file already cover this topic?
2. Can I improve that file instead?
3. Is this a distinct truth category or just duplicate prose?
4. Will another agent know which copy to trust six months from now?

Prefer fewer canonical files with clear boundaries over documentation sprawl.
