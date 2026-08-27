# LLM4LIFE

LLM4LIFE documents an **AI-driven personal operating system**: how AI agents, communication tools, task managers, knowledge systems, developer tooling, and life databases should work together without duplicating responsibility.

This repository is intentionally **a living design**, not a frozen specification. The current choices are defaults that should change when evidence shows a better workflow.

## The idea in one sentence

> Use AI as the universal command and routing layer, while each underlying tool remains the single source of truth for the job it is best at.

## Current architecture

```text
                           AI command layer
                 ChatGPT / Claude / OpenClaw / agents
                              |
          +-------------------+-------------------+
          |                   |                   |
       capture             routing             retrieval
          |                   |                   |
          v                   v                   v
  Slack / Discord /      domain systems      cross-system context
  ChatGPT / Shortcut

Domain systems:
- GitHub           -> code, pull requests, releases
- Jira             -> engineering bugs and backlog
- Things 3         -> personal actions
- Google Calendar  -> time commitments
- Notion           -> structured personal/life state
- Obsidian         -> thinking, learning, durable knowledge
- Slack            -> work/software-engineering communication
- Discord          -> personal communication
- Gmail            -> email intake and source context
```

The AI layer should make the system feel like **one interface**, but it should not collapse the underlying responsibilities into one giant database.

## Current responsibility rule

```text
If it requires action       -> Things 3 (personal) or Jira (engineering)
If it requires time         -> Google Calendar
If it requires thinking     -> Obsidian
If it requires structure    -> Notion
If it is code               -> GitHub
If it is work conversation  -> Slack
If it is personal chat      -> Discord
```

See [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md) for the detailed ownership map and [`docs/ROUTING.md`](docs/ROUTING.md) for routing behavior.

## Design principles

1. **One owner per responsibility.** Avoid parallel task lists and duplicate sources of truth.
2. **AI is the interface/router, not the database.** Data should live in the correct domain system.
3. **Link, do not duplicate.** A Things task can link to Notion; a Notion record can link to Jira; neither should recreate the other system.
4. **Autonomy by default for safe work.** Low-risk, reversible organization can happen automatically.
5. **Consequential actions get stronger safeguards.** Destructive, externally visible, financial, or difficult-to-reverse actions should be treated differently.
6. **Receipts build trust.** Autonomous writes should produce short confirmations and be auditable.
7. **Event-driven beats inbox checking.** Prefer meaningful triggers and exception handling over constant manual polling.
8. **Optimize for attention, not notification volume.** The system should suppress noise and surface what matters.
9. **Preferences are learned, not hard-coded forever.** Behavior should tune prioritization without hiding genuinely urgent items.
10. **Everything is revisitable.** Decisions in this repo represent the best current model, not permanent doctrine.

## What Notion is for

The current conclusion is that Notion has the highest ROI as a **Personal Operations / Life Database** rather than as another engineering project manager or financial application.

Good Notion domains include:

- household and personal-care inventory
- subscriptions and memberships
- warranties and important documents
- renewals and expiries
- insurance/property/vehicle metadata
- loyalty programs
- important vendors/contacts
- administrative reference information
- AI activity/audit history

Engineering truth should remain with GitHub + Jira. Core financial state/calculation should remain in the dedicated financial applications rather than be rebuilt in Notion.

## Agent entry point

AI agents should read [`AGENTS.md`](AGENTS.md) first.

Recommended read order:

1. `AGENTS.md`
2. `docs/CURRENT_STATE.md`
3. `docs/ROUTING.md`
4. `docs/AUTONOMY.md`
5. `docs/DECISIONS.md`

## Repository structure

```text
README.md                 Human overview
AGENTS.md                 Instructions for AI agents
docs/CURRENT_STATE.md     Current systems and ownership
docs/ROUTING.md           Routing and notification logic
docs/AUTONOMY.md          What AI may do automatically
docs/DIGEST.md            Daily digest behavior
docs/DECISIONS.md         Chronological decision log
```

## Change policy

When the operating model changes:

1. update the relevant current-state document;
2. append a dated entry to `docs/DECISIONS.md` explaining what changed and why;
3. prefer replacing an outdated rule over layering exceptions on top of it;
4. record unresolved questions explicitly instead of inventing certainty.

The goal is not to preserve this architecture. The goal is to preserve **clarity about why the architecture currently looks the way it does**.
