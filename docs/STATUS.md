# Runtime Status

_Last verified: 2026-08-27_

This file describes **what is actually live/connected now**, not just what the architecture wants.

It is a point-in-time operational snapshot. Runtime connections can change independently of design decisions, so agents should verify live access before depending on it.

## Current headline

The core architecture is usable today, but the AI still has three important integration gaps:

1. **Things 3** — canonical personal backlog, but no verified direct AI bridge.
2. **Obsidian live vault** — AI can read/maintain the GitHub-backed vault, but a direct local-vault write bridge is not yet verified.
3. **Discord** — personal communication is user-live, but there is no direct ChatGPT Discord connector in the current runtime.

Jira is also canonical for engineering work, but a direct Jira/Atlassian read/write path should be verified before an agent claims access.

## Directly verified in the current ChatGPT environment

| System | Read | Write | Current use |
|---|---:|---:|---|
| GitHub | Yes | Yes | LLM4LIFE policy/docs, repository/code access |
| Notion | Yes | Yes | Structured life state and AI Activity Log |
| Google Calendar | Yes | Yes | Life calendar, execution schedule, task blocks |
| Gmail | Yes | Connector exposes writes; not all actions tested this pass | Email intake/source context |
| Slack | Yes | Connector exposes writes; not all actions tested this pass | Work communication/context |
| ChatGPT Automations | Yes | Yes | Daily planning, digest, follow-up, inventory checks |

`Write` means the current integration exposes supported write actions; it does not mean every write is authorized by LLM4LIFE policy.

## User-live but not fully connected to the AI router

| System | User usage | AI situation |
|---|---|---|
| Things 3 | Personal backlog, reminders, next actions | No verified direct bridge; planner must not pretend to see it |
| Jira | Engineering bugs/backlog | Canonical by policy; direct runtime connector is not assumed without verification |
| Obsidian | Personal knowledge/context vault | GitHub backup/repo is accessible; live local-vault bridge remains a gap |
| Discord | Personal/life communication | No direct ChatGPT connector assumed; custom/OpenClaw bridge is the intended direction if needed |
| Claude / Claude Code | Coding specialist | Reads repo policy when used; not a connected life-OS runtime here |
| OpenClaw | Optional integration plumbing | Provisional; deployment/config should be verified before use |

## Active automation state

The active LLM4LIFE automation set is documented in `docs/AUTOMATIONS.md` and `config/automations.yaml`.

Current high-level loop:

```text
~7 PM  Plan Tomorrow
           |
           v
       Calendar plan
           |
~8 AM  Daily Systems Digest / schedule sanity check
           |
           v
    execute 1 PM–9 PM movable-work window
           |
 hourly Calendar Task Follow-Up checks recently ended task blocks
```

Separate weekly personal-care inventory checks are also active.

## Current planning policy

- Personal backlog: **Things 3**
- Engineering backlog: **Jira**
- Execution schedule: **Google Calendar**
- Scheduler/orchestrator: **AI**
- Default movable-work window: **1:00 PM–9:00 PM America/Toronto**
- Rolling planning horizon: **7 days for high-confidence important work**
- Fixed external commitments are not moved merely to optimize the plan.

## Highest-priority gaps

### P0 — Things 3 bridge

Why it matters: the day planner cannot be complete if it cannot inspect the canonical personal backlog.

Preferred supported bridge options:

- Apple Shortcuts
- Things URL scheme
- AppleScript on macOS
- thin deterministic adapter using supported Things interfaces

Anti-goal: modifying Things' internal database or private cloud credentials directly.

### P1 — Live Obsidian bridge

Why it matters: policy authorizes autonomous note creation/maintenance, but GitHub backup access may lag the actual open vault and is not the ideal write mechanism.

Desired end state:

```text
AI -> safe local bridge -> live Obsidian vault -> normal vault sync/backup
```

Do not treat GitHub as the permanent editor for local knowledge if a safer live-vault interface becomes available.

### P1 — Jira direct connector verification

Why it matters: engineering planning should pull from Jira without copying tickets into another backlog.

Desired end state: AI can read/update Jira items and link them into schedule/receipts while Jira remains canonical.

### P1 — Discord AI bridge

Why it matters: Discord is the preferred personal communication/notification surface, but current ChatGPT direct access is absent.

Potential solution: OpenClaw or another thin channel bridge. Do not add a large middleware stack only to solve one message route.

### P2 — Channel delivery of proactive output

Current automations exist, but agents should not assume every automated report is being delivered to Slack or Discord. Channel-specific delivery should be configured and verified separately.

## Current cleanup / resolved conflicts

- The Calendar Task Follow-Up automation has been aligned with the planner: unfinished tasks now seek a realistic future slot within the 1–9 PM default window rather than blindly copying to the same time tomorrow.
- Two stale duplicate one-time Discord warning reminders from January 2026 were disabled after they had already fired.
- Calendar planning now treats overlaps between movable task blocks as defects to resolve, not as acceptable scheduling.

## Public repository constraint

`LLM4LIFE` is currently a **public GitHub repository**.

Therefore this repo should contain architecture and operational policy, but **not**:

- passwords, API keys, tokens, cookies, auth material;
- account numbers or high-risk identifiers;
- private email contents;
- private diary/relationship/health details;
- confidential work data;
- raw activity logs containing sensitive data.

Store only the minimum non-sensitive metadata needed to explain the system.

See `docs/SECURITY.md`.

## How to update this file

Update `STATUS.md` when one of these materially changes:

- connector becomes available/unavailable;
- read/write capability changes;
- a bridge is deployed;
- a major automation is enabled/disabled;
- canonical ownership changes;
- a major integration gap is resolved;
- the default planning window or execution model changes.

Do **not** edit status just because a vendor advertises a feature. Verify the actual runtime path first.
