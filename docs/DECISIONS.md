# Decision Log

Newest explicit decisions override older conflicting decisions. Entries describe the rationale available at the time and are expected to evolve.

---

## 2026-08-27 — Separate tools by responsibility instead of consolidating everything into Notion

**Decision:** Keep Things 3, Obsidian, and Notion, but give them distinct jobs.

- Things 3 -> personal actions/reminders
- Obsidian -> thinking, learning, durable knowledge
- Notion -> structured databases/state

**Reason:** Their overlap becomes harmful only when the same object is maintained in multiple places. Specialization gives a cleaner system than forcing one app to be the entire productivity stack.

**Rule:** action -> Things, thinking -> Obsidian, structure -> Notion.

---

## 2026-08-27 — Jira remains the source of truth for engineering bugs/backlog

**Decision:** Engineering bugs and technical backlog items live in Jira rather than Things or Notion.

**Reason:** Jira already tracks work arising from GitHub repositories and is purpose-built for engineering workflow.

**Implication:** Do not mirror Jira tickets into Things or rebuild Jira in Notion. Cross-link instead.

---

## 2026-08-27 — GitHub owns code/repository truth

**Decision:** GitHub owns code, PRs, commits, releases, and repository-level technical truth.

**Reason:** Active repositories already contain plans, tests, research, compliance material, contracts, and decision documentation near the code. Moving that material into Notion would create drift.

---

## 2026-08-27 — Slack is work communication; Discord is personal communication

**Decision:**

- Slack -> work/software-engineering communication
- Discord -> personal/life communication

**Reason:** This creates a clean contextual boundary and also provides natural notification surfaces for work vs personal events.

**Implication:** Chat messages may produce actions elsewhere, but Slack/Discord should not become permanent task databases.

---

## 2026-08-27 — AI becomes the universal command/routing layer

**Decision:** The preferred interaction model is an AI/LLM that can see and act across systems rather than requiring the user to manually open each destination app.

**Desired entry points:** ChatGPT, Slack, Discord, iPhone Share Sheet/Shortcuts, email, browser capture, and other practical surfaces.

**Reason:** The user values low-friction conversational control and wants information routed to the correct authoritative system automatically.

**Important constraint:** The AI is an interface/router, not another canonical database.

---

## 2026-08-27 — ChatGPT / Claude / OpenClaw roles are complementary and provisional

**Current working model:**

- ChatGPT -> primary conversational command layer and native connected-tool interface
- Claude -> coding-heavy agent where useful
- OpenClaw -> candidate integration/channel plumbing where native integrations are insufficient

**Status:** Provisional, not a permanent vendor architecture.

**Reason:** Avoid turning multiple AI products into competing sources of truth. Use each for its strongest role and revisit as capabilities change.

---

## 2026-08-27 — Autonomous routing is preferred

**Decision:** The AI should create/update the correct records autonomously instead of asking where every item should go.

**Reason:** Manual confirmation for routine organization destroys much of the value of a universal command layer.

**Safeguard:** Autonomy scales with reversibility and consequence. Low-risk reversible actions are preferred candidates for automatic execution; destructive or materially consequential actions receive stronger safeguards.

---

## 2026-08-27 — Every autonomous write returns a receipt

**Decision:** Successful autonomous writes should send a compact confirmation in the originating channel.

Examples:

- `Created JIRA-142 — Fix staging auth crash`
- `Added to Things — Renew passport`
- `Updated Notion — Toothpaste stock: 1 remaining`

Multiple writes from one request should produce one consolidated receipt.

**Reason:** This preserves trust and visibility without forcing pre-action confirmations.

---

## 2026-08-27 — Maintain a central AI Activity Log in Notion

**Decision:** Create a machine-maintained Notion audit database for meaningful autonomous AI actions.

**Implemented:** `AI Activity Log` under the existing `Tooling Workflow — Apps & Roles` area.

**Tracked concepts:** source, destination, action type, status, timestamp, links, details, error, reversibility, action ID.

**Reason:** Autonomy without auditability is difficult to trust or debug.

---

## 2026-08-27 — Proactive/event-driven AI is desired

**Decision:** The system should detect meaningful changes and act/notify without waiting for a user prompt.

Potential signals include failed builds, stale blockers, action-required email, low stock, expirations/renewals, deadlines, and other high-value exceptions.

**Rule:** event -> evaluate importance -> act if appropriate -> log -> notify.

**Anti-goal:** event -> notify about everything.

---

## 2026-08-27 — Daily cross-system digest enabled

**Decision:** Send a daily digest around 8:00 AM America/Toronto.

The digest currently includes:

- Top 3 priorities for today
- Needs attention today
- Work/engineering
- Personal/admin
- Upcoming deadlines
- Neglected but important
- What can be ignored today
- Cleanup performed
- Learned preferences
- Tool ROI opportunities
- Automated actions taken

**Reason:** Provide one attention-oriented overview rather than requiring manual checks across every application.

---

## 2026-08-27 — Top 3 priorities should be ranked across systems

**Decision:** Rank the day's top three using urgency, impact, dependencies, time sensitivity, and observed behavior.

**Reason:** A digest that only lists information still leaves prioritization work to the user.

---

## 2026-08-27 — Explicitly identify what can be ignored

**Decision:** The daily digest should include `What can be ignored today`.

**Reason:** Protecting attention is as important as surfacing tasks. The system should help reduce work, not merely rank an ever-growing list.

---

## 2026-08-27 — Resurface neglected but important items

**Decision:** Meaningful items sitting roughly 7–14+ days without progress may be resurfaced.

**Constraint:** Age alone is not importance. Do not resurrect low-value clutter.

---

## 2026-08-27 — Allow autonomous cleanup of stale low-value reversible items

**Decision:** The AI may archive/close/clean clearly low-value stale items when the operation is low-risk and reversible.

**Constraint:** Do not automatically delete data or close consequential external work merely because it is stale.

---

## 2026-08-27 — Learn from user behavior over time

**Decision:** Use repeated deferrals, ignores, fast completions, overrides, reopenings, and recurring priorities to improve routing and ranking.

**Constraint:** Learned behavior is a soft preference. Explicit instructions and genuinely urgent/high-impact signals override it.

---

## 2026-08-27 — Proactively audit tool ROI and suggest additions as well as removals

**Decision:** The AI should identify underused/redundant tools and suggest cancel, downgrade, consolidate, or replace opportunities. It may also suggest new tools/integrations when they clearly improve the system.

**Constraint:** Prefer capabilities already paid for/available before recommending another subscription. Avoid novelty-driven tool sprawl.

**Important:** Recommendations are allowed; purchases/subscriptions/cancellations are consequential actions and are not silently executed under the current policy.

---

## 2026-08-27 — No separate monthly tool-stack scorecard

**Decision:** Do not add a formal monthly keep/cancel/replace/add review ritual.

**Reason:** Daily/event-driven recommendations are enough. Another recurring review would add process overhead.

---

## 2026-08-27 — Notion's best role is Personal Operations / Life Database

**Decision:** Invest in Notion primarily as structured personal/life operations, not as another engineering project manager or financial engine.

**Evidence:**

- Active engineering repos already contain substantial project/decision documentation.
- Jira already owns bugs/backlog.
- The existing Notion Projects Hub is comparatively sparse.
- The existing personal-care inventory/usage/shopping system is a strong example of structured data that genuinely benefits from Notion.
- Dedicated finance software already owns financial calculations and transaction state.

**Good expansion areas:** subscriptions, memberships, household inventory, warranties, important documents, expiries, insurance/property/vehicle metadata, loyalty programs, administrative vendors/contacts, and audit history.

---

## 2026-08-27 — Treat the architecture as explicitly open to change

**Decision:** LLM4LIFE records current best decisions but should make revision easy for humans and agents.

**Process:**

1. update current-state docs;
2. update `system.yaml` when machine behavior changes;
3. append a dated decision with rationale;
4. explicitly supersede conflicting older rules instead of silently layering exceptions.

**Goal:** Preserve reasoning and clarity, not historical architecture for its own sake.

---

## 2026-08-27 — Obsidian is an autonomous read/write destination

**Decision:** AI may autonomously create, organize, move, tag, link, archive, and update Obsidian notes when intent and destination are clear.

**Reason:** Obsidian is a real operational knowledge/context layer in the AI-driven system. Requiring confirmation for every routine knowledge write would create unnecessary friction and undermine the universal-router model.

**Preferred behavior:** triage inbox captures, maintain PARA placement/frontmatter, add links/MOC references, create contextual notes, and prefer `90 Archive` over deletion.

**Critical exception:** This does not override the Obsidian software-engineering learning contract. For learning exercises, the vault's retrieval-first Assistance Ladder remains authoritative; autonomous writes must not silently perform the thinking or generate the exercise solution on the user's behalf.

**Boundary:** Obsidian autonomy concerns knowledge/context. It should still link to—not duplicate—canonical structured operational state in Notion, engineering work in Jira, or code/repository truth in GitHub.

---

## 2026-08-27 — Obsidian may autonomously merge and rewrite existing notes

**Decision:** AI may autonomously merge duplicate/overlapping Obsidian notes and substantively rewrite existing notes when doing so improves the canonical knowledge record or resolves stale/conflicting information.

**Reason:** A self-maintaining knowledge layer must be able to reduce entropy, not only add new material. Requiring approval for every safe consolidation would allow duplication and contradictions to accumulate.

**Safeguards:** Preserve meaningful user-authored reasoning, provenance, dates, source links, and useful historical context. Preserve or repair links where practical. Prefer merge + archive over destructive deletion. If a conflict cannot be resolved confidently, keep both contextualized claims or flag it instead of silently choosing one.

**Learning exception:** The software-engineering learning contract remains authoritative. Rewrites must not erase retrieval prompts, mistake evidence, authored reasoning, or otherwise turn the learning system into polished AI-generated reference material.
