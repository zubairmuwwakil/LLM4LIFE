# 2026-08-27 — Runtime Operations Decisions

This decision record supplements `docs/DECISIONS.md` with operational decisions made after the original architecture pass.

## Proactively detect missing systems

**Decision:** The AI should not only optimize existing workflows. It may detect recurring/consequential domains with no reliable owner, trigger, durable record, follow-up, or retrieval path and build the smallest useful low-risk workflow when already authorized.

**Constraint:** Do not build a database/dashboard for every category or one-off fact. Reuse existing tools first.

See `docs/GAP_DETECTION.md`.

---

## Backlog and Calendar are different layers

**Decision:**

- Things 3 owns the personal backlog.
- Jira owns the engineering backlog.
- Google Calendar owns the execution schedule.
- AI owns the scheduling/orchestration step between backlog and time.

Calendar task blocks are scheduled representations, not a second canonical backlog.

See `docs/PLANNING.md`.

---

## Default movable-work window is 1 PM–9 PM

**Decision:** Movable personal work, errands, study, routine admin, and movable deep work should be scheduled between **13:00 and 21:00 America/Toronto** by default.

**Constraint:** Fixed commitments outside that window remain fixed. A newer explicit instruction for a specific task/day can override the default.

The planner should leave buffer inside the window rather than trying to fill all eight hours.

See `config/scheduling.yaml`.

---

## Evening plan + morning sanity check

**Decision:** Use two complementary planning automations:

- `Plan Tomorrow` around 7 PM prepares the next day and maintains a short rolling horizon.
- `Daily Systems Digest` around 8 AM performs the final schedule/attention sanity check.

This avoids making the morning digest do all planning from scratch.

---

## Follow-up automation must feed the planner

**Decision:** The hourly Calendar Task Follow-Up must not blindly push unfinished tasks to the next day at the same time.

It now reassesses whether the task still matters and, when appropriate, selects a realistic future slot within the planning model.

Repeated misses are behavioral evidence for priority/duration/scheduling adaptation.

---

## Separate design intent from runtime connectivity

**Decision:** LLM4LIFE must explicitly distinguish:

- what a tool is supposed to own;
- what the user actively uses;
- what the AI is authorized to do;
- what the current runtime can technically access right now.

**Reason:** Without this separation, agents can incorrectly claim access to tools such as Things, Jira, Discord, or the live local Obsidian vault simply because those tools appear in architecture documentation.

Implemented with:

- `docs/TOOL_REGISTRY.md`
- `docs/STATUS.md`
- `config/tools.yaml`

---

## Maintain explicit automation registry

**Decision:** Active recurring/conditional behavior must be documented separately from high-level architecture.

Implemented with:

- `docs/AUTOMATIONS.md`
- `config/automations.yaml`

Stale duplicate one-time Discord warning reminders that had already fired were disabled as reversible cleanup.

---

## Public-repo privacy boundary

**Decision:** Because LLM4LIFE is public, it documents architecture/policy only and must not become a store for private life state, secrets, sensitive identifiers, private communications, or confidential work information.

Agents may use private connected context to operate the system without copying that private content into this repository.

See `docs/SECURITY.md`.
