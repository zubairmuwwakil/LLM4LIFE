# AI & Automation Inventory

**Status:** Provisional / subject to change  
**Purpose:** Record current AI/automation tools, their intended boundaries, and the direction for a scalable long-term LLM4LIFE control plane.

## Current usage

| System | Current role | Provisional long-term direction |
|---|---|---|
| **ChatGPT** | Primary conversational interface, planning, personal orchestration, connected-tool control surface, and scheduled automations | Keep as the primary user-facing AI interface for now. Do not rely on a single chat thread as durable system state; externalize state, jobs, and receipts |
| **Gemini AI Pro** | General AI assistant, including useful browser-side Ask Gemini workflows in Chrome | Keep as a complementary assistant where its browser/context integration is valuable; avoid duplicating canonical state across AI vendors |
| **Claude / Claude Code** | Coding and software-development assistance | Prefer use through ORC where practical so coding-agent routing, verification, escalation, and quota policy remain centralized |
| **Codex** | Coding agent/workflow | Same boundary as other coding agents: worker/specialist beneath ORC where practical |
| **GitHub Copilot** | Coding assistance | Keep available as a coding worker/tool, but avoid creating a separate competing orchestration workflow around it |
| **ORC (`agent-orchestrator`)** | Coding-specific AI control plane across model/effort pools with verification and cross-vendor review | Keep as the canonical coding orchestration layer. LLM4LIFE may invoke ORC, but should not duplicate its routing, quota, verification, or escalation logic |
| **OpenClaw** | Historical/potential automation and messaging bridge, including Discord/WhatsApp conversational access and message-context access | Re-evaluate after full inventory. Preserve the valuable cross-channel capability, but compare OpenClaw against a more observable, least-privilege LLM4LIFE ingress/event architecture |
| **Apple Shortcuts** | Mobile capture, Wallet/mobile automation, and low-friction personal workflows | Keep as an edge automation layer. Shortcuts should trigger or feed canonical systems rather than own durable state |
| **Slack / Discord automation** | Personal/repository automation, notifications, and conversational control surfaces | Keep as interfaces/channels, not databases or canonical job state |
| **ChatGPT scheduled tasks / automations** | Time-based reminders, recurring summaries/checks, and conversational automations | Useful as an execution surface, but not a durable source of truth. Important recurring jobs should have external state/receipts and should not depend on indefinite chat-context growth |
| **GitHub Actions** | Repository CI/CD and automation | Keep focused on repository workflows. Avoid using GitHub Actions as the general LLM4LIFE scheduler, especially where quota/runtime limits or repo coupling make it unreliable |
| **cron jobs** | Deterministic scheduled scripts/jobs | Keep as a valid low-level scheduling mechanism where appropriate, but standardize ownership, configuration, logging, retries, and health monitoring rather than scattering unmanaged cron entries across devices/servers |

## Core architecture principle

LLM4LIFE should become the **general personal control plane**, while specialized execution systems remain underneath it.

```text
User / channels
ChatGPT / Slack / Discord / Shortcuts / browser
                    |
                    v
             LLM4LIFE control plane
        intent + routing + policy + state refs
                    |
        +-----------+-----------+----------------+
        |                       |                |
        v                       v                v
 personal systems            ORC          deterministic jobs
 Tasks/Calendar/etc.     coding control       cron/workers
                               |
                               v
                 Claude / Codex / Gemini /
                    Copilot / other agents
```

## Production-grade scheduler/job direction

Do not treat every scheduler as interchangeable.

### Appropriate roles

- **Google Calendar** -> human time commitments / time blocks.
- **Google Tasks** -> personal actionable work.
- **ChatGPT automations** -> conversational reminders/checks and convenient scheduled AI execution.
- **GitHub Actions** -> code/repository CI/CD and repository-scoped automation.
- **cron** -> deterministic scheduled scripts with no need for conversational context.
- **future LLM4LIFE worker/job layer** -> durable personal-system jobs that need retries, state, observability, idempotency, or cross-service orchestration.

### Long-term requirement

Important recurring automations should eventually have:

- stable job identity;
- durable configuration/state outside chat context;
- last-run and next-run metadata;
- structured execution receipts;
- retry/failure policy;
- idempotency where writes are involved;
- logs/observability;
- least-privilege credentials;
- explicit ownership and destination system.

This is stronger than accumulating unrelated automations in one long-running conversation or relying on undocumented cron jobs.

## GitHub Actions boundary

GitHub Actions remains valuable for CI/CD, testing, builds, releases, repository checks, and repo-related maintenance. The user reports that available Actions usage can be exhausted quickly, which is another reason not to make it the universal personal automation runtime.

Use alternative workers/schedulers for non-repository personal automation when that reduces coupling, runtime constraints, or quota pressure.

## cron boundary

cron itself is production-proven for simple deterministic schedules. The weakness is not cron; it is **unmanaged cron**.

During implementation, inventory existing cron jobs and either:

1. keep simple local/server jobs in a declarative tracked configuration with logging/health checks; or
2. move stateful/cross-system jobs into the future LLM4LIFE worker/job layer.

Do not require a local laptop to be awake for critical automation unless that is an intentional local-only security boundary.

## AI vendor strategy

The architecture should remain multi-model rather than hard-coding the user's life system to one AI vendor.

- ChatGPT is the primary conversational control surface for now.
- Gemini remains useful, especially where browser integration is strong.
- Coding models belong beneath ORC where practical.
- LLM4LIFE should hold vendor-neutral intent/contracts/state references wherever possible.

## Immediate implementation follow-up after inventory

- Define the LLM4LIFE job/automation registry schema in the shared backend.
- Define an execution receipt/event model.
- Inventory current cron jobs and scheduled AI automations.
- Separate repository CI/CD jobs from personal/life automation.
- Define when a job stays in ChatGPT automation, cron, GitHub Actions, or moves to a durable worker.
- Define how LLM4LIFE invokes ORC without duplicating ORC internals.
- Re-evaluate OpenClaw specifically for channel ingress/messaging capabilities versus a dedicated LLM4LIFE integration layer.
