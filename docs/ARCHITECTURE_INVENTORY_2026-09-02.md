# Provisional Architecture Inventory — 2026-09-02

**Status:** Provisional / subject to change  
**Purpose:** Capture decisions made while auditing the user's complete personal software stack before implementing the long-term LLM4LIFE architecture.

> This document is a checkpoint, not a frozen architecture. Every tool and boundary below should be challenged if a more scalable, reliable, maintainable, or better-integrated production-grade design is identified.

## Implementation commitment

This inventory session is intentionally **discovery first, implementation second**.

**As soon as the current session finishes reviewing the full software/app stack, begin implementing the long-term architecture.** Do not leave the recommendations as documentation-only future work. The inventory exists to avoid prematurely building around an incomplete picture of the user's life systems.

## Current architectural direction

### LLM4LIFE

LLM4LIFE is the architecture and orchestration system for the user's broader personal life. Software development and side projects are important parts of it, but they are not its entire purpose.

LLM4LIFE should document:

- what systems/apps are used;
- why each exists;
- which system owns which kind of information;
- how systems integrate;
- what the source of truth is for each domain;
- configuration/integration requirements without committing secrets;
- current limitations and migration plans;
- opportunities to replace the current approach with a stronger production-grade design.

The repository describes the architecture; it should not become a dump of private life state.

## Current system ownership

| System | Current / intended responsibility | Direction |
|---|---|---|
| **ChatGPT** | Primary conversational interface, planning, personal orchestration, connected-tool control surface | Keep as primary interface for now; vendor role remains revisitable |
| **LLM4LIFE** | Documents and coordinates the overall personal-system architecture | Expand into the architectural/control-plane project without duplicating domain systems |
| **Neon / PostgreSQL** | Emerging machine-readable shared state for long-term orchestration | Move toward this as durable backend state where appropriate after inventory is complete |
| **Obsidian** | Personal knowledge, reasoning, journal, life context, learning, and software-engineering learning notes | Keep. Do not move technical *learning* notes merely because they are technical |
| **Notion** | Structured workspace, trackers, dashboards, personal operations, and quick product/status views | Keep, but prefer it as a structured interface/projection rather than manually duplicating canonical engineering state |
| **GitHub** | Code, commits, PRs, releases, repository-specific architecture and technical truth | Keep as canonical implementation/repository truth |
| **Jira** | Engineering backlog: epics, features, bugs, technical execution state | Keep as canonical engineering work tracker |
| **Google Calendar** | Canonical calendar / schedule / time commitments | Continue migration from Apple Calendar; preferred because of stronger integration support |
| **Google Tasks** | Canonical simple personal task interface for now | Continue migration from Apple Reminders / Things where appropriate; reassess once shared backend is implemented |
| **Things 3** | High-quality personal task UX historically used for small tasks, todos, reminders, and long-term goals | Keep available because the UX is valued, but do not make it the architectural source of truth while AI/API integration is weak |
| **Apple Calendar** | Previous calendar system | Migrating away as canonical calendar |
| **Apple Reminders** | Previous reminders/task system | Migrating away as canonical task system |
| **ORC (`agent-orchestrator`)** | AI coding control plane: routes coding work across model/effort pools, manages quota-aware escalation, independently verifies work, and performs cross-vendor review | Keep as the coding-specific orchestration layer. LLM4LIFE should integrate with ORC rather than duplicate its coding-agent routing logic |
| **Claude Code / Codex / Gemini / Copilot and other coding agents** | Coding workers/specialists used underneath the development workflow | Prefer access through ORC where practical instead of treating each as an independent workflow/source of truth |
| **Gmail** | Email communication and intake for receipts, bills, subscriptions, account/admin messages, and actionable context | Keep as a primary communication/intake source; route durable actions/state elsewhere |
| **Slack** | Work communication plus the user's own workspace for personal automation and repository/project automation | Keep as an automation/control and notification surface, not a canonical database |
| **Discord** | Personal/community communication and historically the preferred conversational surface for OpenClaw | Keep as an optional conversational/automation channel if it remains useful; not a source of truth |
| **WhatsApp** | Personal messaging and historically an OpenClaw-accessible communication source | Treat as a communication source/surface only; do not depend on it as canonical state |
| **iMessage / Messages** | Personal messaging and historically an OpenClaw-accessible communication source | Keep as communication only; integration is valuable, but canonical data should live elsewhere |
| **OpenClaw** | Historical/potential integration bridge giving the AI conversational access through Discord/WhatsApp and access to messaging sources such as iMessage/WhatsApp | Re-evaluate after full inventory. Preserve the useful channel/message-access pattern, but compare against a more production-grade LLM4LIFE integration layer before committing to OpenClaw as core infrastructure |
| **Apple Shortcuts / Share Sheet** | Low-friction iPhone capture and automation entry point | Keep as a high-value edge/capture layer feeding LLM4LIFE |
| **Apple Notes** | Still actively used for notes/capture, but role is not yet cleanly defined | Keep temporarily; evaluate whether it should remain a fast scratchpad/capture UI or be consolidated into Obsidian/another capture pipeline |

## Important boundaries

### Obsidian vs project documentation

Keep conceptual learning and durable engineering knowledge in Obsidian.

Examples:

- "How PostgreSQL indexes work" -> **Obsidian**
- "What I learned about React today" -> **Obsidian**
- "PickMe API contract" -> **PickMe GitHub repository**
- "MoneyTalks deployment instructions" -> **MoneyTalks GitHub repository**

The distinction is **knowledge being learned/remembered** versus **documentation required to operate a specific software system**.

### Notion vs Jira/GitHub

Notion can provide fast product dashboards and structured views, but long term it should not require manually maintaining a second copy of engineering truth.

Preferred production-grade direction:

```text
Jira / GitHub canonical engineering state
              |
              v
       sync / projection
              |
              v
       Notion dashboards
```

Notion remains useful as a human-friendly structured workspace while canonical engineering state stays closer to engineering systems.

### ORC vs LLM4LIFE

ORC owns **coding-agent orchestration**.

LLM4LIFE owns **life-system orchestration and architecture**.

LLM4LIFE may invoke or reason about ORC, but should not rebuild ORC's model routing, quota management, verification, escalation, or cross-vendor review machinery.

### Tasks and scheduling

Current transition:

```text
Previous                         Current direction
--------                         -----------------
Apple Calendar      ---------->  Google Calendar
Apple Reminders     ---------->  Google Tasks
Things 3            ----->        optional preferred UX / non-canonical client
```

Long-term target under evaluation:

```text
                 LLM4LIFE
                     |
              shared backend state
              Neon / PostgreSQL
                     |
       +-------------+-------------+
       |             |             |
       v             v             v
Google Calendar  Google Tasks     Jira
   schedule      personal tasks  engineering work

      Obsidian                   Notion
      knowledge             structured views
```

This diagram is **directional, not final**. The inventory may reveal better boundaries or systems.

## Communication and capture inventory

### Current usage

- **Gmail** is both communication and a high-value intake source for receipts, bills, subscriptions, account/admin messages, and other actionable context.
- **Slack** has two real roles: work/software communication, and the user's own workspace for personal/repository automation.
- **Discord** is used for both communities and personal communication, and was the user's preferred conversational interface when using OpenClaw.
- **OpenClaw** previously provided conversational access through Discord and WhatsApp and could access iMessage and WhatsApp message context. The user valued this cross-channel visibility.
- **WhatsApp** and **iMessage** are therefore important message sources even if they should not own durable state.
- **Apple Notes** remains actively used, but the user is open to replacing or narrowing its role.
- **Voice capture** is not currently a meaningful workflow.
- **Apple Shortcuts / Share Sheet** remain useful low-friction capture/automation surfaces.

### Provisional production-grade direction

Communication applications should be treated as **edge channels and event sources**, not canonical databases.

```text
Gmail / Slack / Discord / WhatsApp / iMessage
Apple Notes / Shortcuts / Share Sheet
                    |
                    v
             LLM4LIFE ingress/router
                    |
          normalize intent / event
                    |
      +-------------+--------------+----------------+
      |             |              |                |
 personal task   engineering    knowledge       structured state
      |             |              |                |
 Google Tasks      Jira         Obsidian      Notion / Postgres
      |
 scheduled execution -> Google Calendar

 software execution -> ORC -> GitHub
```

Long-term, the valuable capability from the OpenClaw setup is **not necessarily OpenClaw itself**; it is the ability to ingest and act across multiple communication channels while preserving a single routing policy and canonical ownership model. During implementation, compare OpenClaw against native connectors, webhooks, messaging bridges, and a dedicated LLM4LIFE ingress/event layer. Prefer the option that provides the strongest reliability, observability, authentication, least-privilege access, and low vendor lock-in.

### Apple Notes decision remains open

Do not migrate Apple Notes merely for architectural neatness. During implementation, inspect actual usage and choose one of two likely roles:

1. **Fast scratch/capture client** whose durable content is routed into Obsidian or structured systems; or
2. **Retire/consolidate** if Shortcuts/Share Sheet plus Obsidian provide equally low-friction capture.

Avoid maintaining durable notes in both Apple Notes and Obsidian without a clear ownership rule.

## Architecture review rule for the remainder of the inventory

For every app/service discovered during this audit, record:

1. **What is it used for today?**
2. **Is it the canonical source of truth or only an interface/view?**
3. **What integrations/APIs are available?**
4. **Is there duplicated responsibility elsewhere?**
5. **Would keeping it be production-grade and scalable?**
6. **If not, what should eventually replace or reposition it?**
7. **What needs to be implemented immediately after the inventory session?**

Do not preserve a tool merely because it is already in use. Do not replace a tool merely for architectural purity when its UX or specialized capability provides real value.
