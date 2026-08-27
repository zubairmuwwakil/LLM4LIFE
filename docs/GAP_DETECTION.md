# Gap Detection

_Last updated: 2026-08-27_

## Purpose

The AI should not only optimize systems that already exist. It should also notice when an important recurring domain has **no reliable owner, no durable record, no trigger, or no review path**.

The goal is to prevent silent operational gaps without turning every part of life into a database.

## Core rule

> Detect repeated or consequential unmanaged state, then build the smallest useful system in the correct canonical tool.

A missing system is not simply "something without a Notion database." It is a recurring responsibility where important information, actions, deadlines, or context can be lost because no existing workflow reliably owns them.

## Signals that a system may be missing

Strong signals include:

- the same type of reminder is manually recreated repeatedly;
- important information is repeatedly searched for across chat/email/notes;
- deadlines depend on memory rather than a tracked date;
- recurring maintenance has no owner or next occurrence;
- receipts, warranties, policies, memberships, or documents are mentioned repeatedly but cannot be retrieved reliably;
- the user repeatedly asks "where did I put / when does / what was" about the same domain;
- multiple tools contain partial versions of the same state with no canonical home;
- an important workflow repeatedly fails because there is no trigger, routing rule, or follow-up step;
- an AI action repeatedly needs context that is not stored durably anywhere appropriate;
- a life/admin domain has meaningful consequence but only exists in transient messages.

## Detection process

When a potential gap is detected:

1. **Verify recurrence or consequence.** Do not create infrastructure for every one-off fact.
2. **Check existing systems first.** Search the appropriate canonical sources before assuming a system is absent.
3. **Choose one owner.** Apply the LLM4LIFE ownership model rather than inventing another source of truth.
4. **Design the minimum viable workflow.** Prefer one small database, rule, view, recurring trigger, template, or bridge over a large new system.
5. **Reuse before adding.** Prefer an existing tool/capability over another subscription or service.
6. **Automate only within existing authority.** Low-risk reversible setup may be implemented automatically; consequential actions keep their safeguards.
7. **Link rather than copy.** Preserve canonical ownership across systems.
8. **Observe whether the new system actually reduces friction.** Simplify or remove it if it creates more maintenance than value.
9. **Log material changes.** Record meaningful new systems/rules in the AI Activity Log and LLM4LIFE decision history.

## Canonical destination examples

| Gap | Preferred owner |
|---|---|
| Personal action/reminder process | Things 3 |
| Scheduled/time-bound commitment | Google Calendar |
| Structured durable personal/admin state | Notion |
| Durable reasoning, context, lesson, research | Obsidian |
| Engineering bug/backlog process | Jira |
| Code/repository state | GitHub |
| Work notification/communication workflow | Slack |
| Personal notification/communication workflow | Discord |

Examples of good Notion gap candidates include warranties, important-document expiries, memberships/benefits, property/vehicle administrative records, recurring household maintenance metadata, and other structured life operations that do not already have a better canonical application.

## Minimum-system principle

Do **not** build a system merely because one could exist.

A new system should usually satisfy at least one of these:

- prevents a meaningful failure;
- eliminates repeated manual work;
- makes important information reliably retrievable;
- replaces duplicate tracking;
- creates a useful trigger/follow-up path;
- materially reduces cognitive load.

Prefer:

```text
one field + one trigger + one useful view
```

over:

```text
large dashboard + many properties + recurring maintenance
```

## Autonomous implementation

The standing recommendation policy allows the AI to implement a newly detected system automatically when all of the following are true:

- the need is supported by repeated evidence or meaningful consequence;
- the design is low-risk and reversible;
- the destination tool is already authorized;
- it does not create a purchase, cancellation, financial commitment, destructive action, external commitment, or new permission grant;
- the system has a clear canonical owner;
- the implementation is reasonably minimal.

Examples of autonomous setup:

- add a Notion database/property/view for a clearly recurring structured admin domain;
- create a safe routing rule;
- add a recurring reminder or Calendar event when the cadence is clearly established;
- create an Obsidian MOC/template for recurring durable knowledge;
- add a low-risk follow-up or deduplication rule;
- add documentation or cross-links between existing systems.

## When not to auto-build

Do not autonomously create systems that:

- require purchasing/subscribing to a product;
- require new credentials, permissions, or account access;
- create consequential external commitments;
- move money or change financial products;
- materially change production systems;
- depend on highly uncertain assumptions;
- create substantial maintenance burden without strong evidence of value.

In these cases, surface the gap and recommended design instead.

## Lifecycle

Every new workflow should be treated as provisional.

The AI should watch for:

- continued manual work despite the system;
- duplicate records;
- ignored reminders;
- low retrieval/use frequency;
- user overrides;
- system-generated noise;
- a better canonical owner becoming available.

A low-value system may be simplified, merged, archived, or removed when doing so is safe and reversible.

## Anti-goals

- Do not turn life into an ERP system.
- Do not create a database for every category of information.
- Do not add tools merely because they are popular or novel.
- Do not confuse visibility with value.
- Do not create review rituals unless they solve a demonstrated problem.
- Do not duplicate state just to make an AI dashboard look complete.
