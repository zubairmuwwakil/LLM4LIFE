# Work & Employer Software Inventory

**Status:** Provisional / subject to change  
**Purpose:** Document employer-controlled software surfaces and define how they should interact with LLM4LIFE without becoming personal systems of record.

## Current usage

The user currently uses the standard work stack across employers/clients, including:

- Outlook
- Gmail
- Microsoft Teams
- Slack
- Microsoft 365
- Google Workspace
- employer/client VPNs
- HR / payroll / benefits portals
- time tracking where required
- ticketing/project systems where required
- remote desktop / VDI where required

There is nothing currently identified as materially unique to TELUS that requires a special architectural subsystem.

## Architectural classification

These tools are primarily **employer-controlled execution and communication surfaces**.

They should not become canonical stores for the user's broader personal state merely because important work happens there.

### Preferred role boundaries

| Domain | Preferred owner / role |
|---|---|
| Employer email | Employer-provided Outlook/Gmail account |
| Employer chat | Teams/Slack as required by employer |
| Employer documents | Employer Microsoft 365 / Google Workspace |
| Employer tasks/projects | Employer-required Jira, ticketing, project or workflow tools |
| Personal career knowledge | Obsidian |
| Public implementation evidence | GitHub / portfolio where legally and contractually appropriate |
| Personal scheduling | Google Calendar, with work events projected only when policy and account boundaries permit |
| LLM4LIFE | Personal orchestration layer; must respect employer data boundaries and least privilege |

## Production-grade direction

Do **not** try to replace employer-mandated tools with personal alternatives.

Instead:

1. keep employer systems authoritative for employer-owned data;
2. integrate only when technically supported and allowed by employer policy;
3. avoid copying confidential work content into personal Obsidian, LLM4LIFE, Neon, or public repositories;
4. allow only narrow personal projections where useful, such as a meeting time, deadline, or generic follow-up reminder;
5. keep personal credentials and employer credentials separated;
6. do not route employer messages through personal automation unless explicitly permitted;
7. preserve account boundaries between Microsoft 365 / Google Workspace identities.

## LLM4LIFE interaction model

Where integrations are permitted, LLM4LIFE may act as a personal interface that references employer systems without taking ownership of employer state.

Example:

```text
Employer Outlook / Teams / Slack / M365 / Workspace
                       |
              policy-permitted read
                       |
                       v
                   LLM4LIFE
                       |
        personal action / schedule projection
                       |
             Google Tasks / Calendar
```

The projection should be minimal. For example:

- acceptable: `Follow up on work item Friday`
- avoid by default: copying confidential email bodies, proprietary code, customer information, internal documents, or sensitive HR data into personal storage

## Security / privacy boundaries

- Employer/client data remains in employer/client-controlled systems unless an explicit approved workflow says otherwise.
- Never commit employer credentials, VPN settings containing secrets, confidential documents, internal messages, or proprietary code to LLM4LIFE.
- Personal AI agents should use least-privilege access and separate identities where possible.
- Local or connected AI access to work systems must be treated as an employer-policy question, not assumed safe because a connector exists.

## Free-first constraint

No new paid work-management product is required. Use the systems already provided by the employer/client, and add personal tooling only when it fills a clearly separate personal need.
