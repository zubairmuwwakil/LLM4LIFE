# LLM4LIFE

LLM4LIFE documents an **AI-driven personal operating system**: how AI agents, communication tools, task managers, knowledge systems, developer tooling, calendars, structured life databases, and automations work together without duplicating responsibility.

This repository is deliberately a **living architecture**, not a frozen specification. Current choices should change when evidence shows a better workflow.

> **Core idea:** AI is the universal command, planning, and routing layer; each underlying tool remains the single source of truth for the responsibility it is best at.

## Start here

For a human overview, read this README.

For an AI agent, read [`AGENTS.md`](AGENTS.md) first.

For the current operational truth, use:

- [`docs/TOOL_REGISTRY.md`](docs/TOOL_REGISTRY.md) — every important tool, who uses it, what it owns, and actual AI access
- [`docs/STATUS.md`](docs/STATUS.md) — what is connected/live vs partial/planned today
- [`docs/AUTOMATIONS.md`](docs/AUTOMATIONS.md) — active scheduled/conditional workflows
- [`config/tools.yaml`](config/tools.yaml) — machine-readable tool/access registry
- [`config/automations.yaml`](config/automations.yaml) — machine-readable automation registry
- [`config/scheduling.yaml`](config/scheduling.yaml) — machine-readable scheduling preferences

**Important:** architectural ownership and technical connectivity are different. For example, Things 3 can be the canonical personal backlog while the current AI still lacks a direct Things bridge.

## Current architecture

```text
                           USER
                            |
                            v
                     AI command layer
             ChatGPT / Claude / repo agents
                 optional OpenClaw plumbing
                            |
        +-------------------+-------------------+
        |                   |                   |
     capture             routing             planning
        |                   |                   |
        v                   v                   v
 Slack / Discord /      canonical          backlog -> time
 Gmail / ChatGPT          systems          Google Calendar

Canonical systems:
- Things 3         -> personal backlog/actions
- Jira             -> engineering bugs/backlog
- GitHub           -> code/repository truth
- Google Calendar  -> fixed time + current execution schedule
- Notion           -> structured life/personal-operations state
- Obsidian         -> knowledge, reasoning, learning, context
- Slack            -> work communication
- Discord          -> personal communication
- Gmail            -> email intake/source context
```

The AI should make this feel like **one system** without flattening everything into one giant database.

## Current responsibility rule

```text
Personal action/backlog     -> Things 3
Engineering work/backlog    -> Jira
Code/repository truth       -> GitHub
Scheduled execution/time    -> Google Calendar
Structured personal state   -> Notion
Thinking/knowledge/learning -> Obsidian
Work conversation           -> Slack
Personal conversation       -> Discord
Email source/input          -> Gmail
Cross-system orchestration  -> AI layer
```

## Day-to-day planning model

The user should not have to manually decide what belongs on each future day.

```text
Things 3 personal backlog      Jira engineering backlog
           \                         /
            \                       /
             +----> AI planner <----+
                       |
                       v
                Google Calendar
                 execution plan
```

Current planning defaults:

- movable personal work: **1:00 PM–9:00 PM America/Toronto**
- leave buffer instead of filling all available hours
- today/tomorrow get concrete execution blocks
- next 7 days only get high-confidence important work
- beyond 7 days stays mostly in backlog unless deadlines/lead time justify scheduling
- fixed meetings, appointments, travel, legal/financial commitments are not moved merely for optimization
- missed work is reevaluated rather than blindly moved one day forever

See [`docs/PLANNING.md`](docs/PLANNING.md).

## Active automation loop

```text
~7 PM   Plan Tomorrow
           |
           v
       Calendar plan
           |
~8 AM   Daily Systems Digest
       + schedule sanity check
           |
           v
    execute day / task blocks
           |
           v
hourly   Calendar Task Follow-Up
```

Weekly personal-care inventory heartbeat/restock automations also run from Notion.

See [`docs/AUTOMATIONS.md`](docs/AUTOMATIONS.md).

## Current runtime situation

As of 2026-08-27:

### Directly verified / useful now

- GitHub — connected read/write
- Notion — connected read/write
- Google Calendar — connected read/write
- Gmail — connected; read verified and supported write actions exposed
- Slack — connected; read verified and supported write actions exposed
- ChatGPT Automations — active

### Important gaps

- **Things 3:** no verified direct AI bridge yet; this is the biggest blocker to complete personal-backlog planning.
- **Obsidian:** AI can access the backed-up GitHub vault, but a direct live local-vault bridge is not yet verified.
- **Jira:** canonical for engineering work, but a direct Jira/Atlassian connector must be verified in the runtime before claiming live access.
- **Discord:** used for personal communication, but no direct ChatGPT Discord connector is assumed; OpenClaw/thin custom plumbing is the candidate path.

See [`docs/STATUS.md`](docs/STATUS.md) for the current snapshot.

## Design principles

1. **One owner per responsibility.** Parallel sources of truth create drift.
2. **AI is interface/router/planner, not the database.**
3. **Link, do not duplicate.** Preserve deep links/provenance instead of copying records everywhere.
4. **Backlog is not Calendar.** Tasks live in their canonical backlog; Calendar shows selected execution time.
5. **Autonomy for safe reversible work.** Routine organization should not require repetitive approval.
6. **Consequential actions keep stronger safeguards.** Money, destructive deletion, credentials/security, consequential external messages, production changes, and new permissions are not covered by standing low-risk approval.
7. **Receipts build trust.** Meaningful autonomous writes should be visible and auditable.
8. **Event-driven/exception-oriented beats notification spam.**
9. **Learn with evidence and rollback.** Repeated behavior may tune low-risk rules; one observation should not become doctrine.
10. **Detect missing systems.** The AI may build the smallest useful workflow when an important recurring domain has no reliable owner/process.
11. **Minimum useful system over infrastructure sprawl.** Do not turn life into an ERP.
12. **Everything is revisitable.** Preserve rationale, not tradition.

## Notion's role

Notion's current highest-ROI role is **Personal Operations / Life Database**, not another engineering project manager or finance engine.

Good examples:

- household/personal-care inventory
- subscriptions and membership metadata
- warranties and important document metadata
- renewals and expiries
- insurance/property/vehicle administrative records
- loyalty programs
- administrative vendors/contacts
- AI Activity Log

Engineering truth stays with GitHub/Jira. Deep knowledge stays with Obsidian. Core financial calculation/state stays with dedicated finance applications.

## Obsidian's role

Obsidian is the **personal knowledge/context layer**: reasoning, learning, durable notes, PARA context, daily/diary context, research, retrieval prompts, and mistake logs.

AI is authorized to autonomously create, organize, link, merge, rewrite, and capture durable conversation knowledge there, subject to privacy safeguards and the vault's stricter retrieval-first software-engineering learning contract.

Current technical caveat: GitHub backup access is not equivalent to a verified direct write path into the live local vault.

## AI adaptation

The system may learn from:

- repeated deferral/ignoring
- quick completion
- manual overrides
- reopened work
- routing failures
- duplicate creation
- missed urgency
- notification noise
- repeated rescheduling
- duration mismatch

Low-risk routing, prioritization, notification, capture, deduplication, scheduling, and cleanup rules may be tuned autonomously when evidence is strong enough and rollback is available.

The AI may **not** self-tune by expanding permissions or weakening safeguards.

## Repository map

```text
README.md                      Human entry point
AGENTS.md                      Canonical agent operating instructions
CLAUDE.md                      Claude entry point
system.yaml                    High-level machine-readable architecture

config/
  tools.yaml                   Tool/runtime/access registry
  automations.yaml             Active automation registry
  scheduling.yaml              Scheduling preferences

docs/
  TOOL_REGISTRY.md             What every tool does + who uses it + access
  STATUS.md                    Live / partial / planned runtime status
  CURRENT_STATE.md             Narrative current architecture
  ROUTING.md                   Routing logic
  PLANNING.md                  Backlog -> Calendar day-planning model
  AUTOMATIONS.md               Active automation behavior
  DIGEST.md                    Morning digest behavior
  AUTONOMY.md                  What AI may do automatically
  ADAPTATION.md                Self-tuning rules and rollback
  GAP_DETECTION.md             Proactive missing-system detection
  KNOWLEDGE_CAPTURE.md         Conversation -> Obsidian capture policy
  INTEGRATIONS.md              Integration topology and bridge strategy
  SECURITY.md                  Public-repo/security/privacy rules
  DECISIONS.md                 Original chronological decision log
  decisions/                   Supplemental dated decision records
```

## Public repository warning

This repository is currently **public**.

It should contain architecture/policy only. Do not commit secrets, credentials, account numbers, sensitive personal records, private message/email contents, confidential work data, or raw private activity logs.

See [`docs/SECURITY.md`](docs/SECURITY.md).

## Change policy

When a meaningful architectural decision changes:

1. verify the real runtime situation;
2. update the relevant policy/current-state docs;
3. update machine-readable config when behavior/access changed;
4. add a dated decision record with rationale;
5. explicitly supersede older conflicts rather than layering hidden exceptions;
6. keep private/sensitive operational state out of this public repo.

The goal is not to preserve today's architecture. The goal is to make **the current architecture, its reasons, its limitations, and its next gaps obvious to both humans and AI agents**.
