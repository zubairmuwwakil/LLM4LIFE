# 2026-09-03 — Product Tracker Runtime: Cloudflare Workers + Queues + Neon

**Status:** Adopted target architecture. The Neon mirror is live; Cloudflare runtime implementation is in progress and write cutover is not yet complete.

## Context

Product Tracker began as a conventional Node/Fastify API plus a continuously running PostgreSQL-backed inbox/outbox polling worker.

Render was considered because it naturally accommodates that process model. Vercel was then considered as a more serverless/event-driven runtime. After reviewing the broader LLM4LIFE infrastructure direction, Cloudflare is the better long-term target because it already runs the production Google Tasks integration and now provides the required compute, queueing, retry and workflow primitives on the same platform.

The goal is not to preserve a particular hosting provider or process model. It is to minimize infrastructure sprawl while keeping Neon as the user-owned durable state layer.

## Decision

Use this as the Product Tracker target runtime:

```text
ChatGPT / clients / Notion webhook
              |
              v
      Cloudflare Worker
    HTTP/API/webhook ingress
              |
              v
             Neon
 canonical inventory/event state
 outbox + webhook receipt ledger
              |
              v
      Cloudflare Queue
 async projection / retries
              |
              v
 Notion projection / future effects
```

Cloudflare Workflows may be added later if a genuinely multi-step durable process benefits from workflow semantics. Do not introduce Workflows merely because the product exists.

## Ownership

- **Neon** owns Product Tracker's durable inventory state, balances, inventory events, idempotency records, webhook receipts and outbox/reconciliation state.
- **Cloudflare** owns runtime execution, ingress, queue delivery, retries and observability.
- **Notion** remains a transitional human control surface until cutover, then becomes projection/rollback UI.
- Cloudflare is replaceable infrastructure, not canonical inventory truth.

## Reliability model

The PostgreSQL transaction remains the durable boundary:

1. validate/authenticate an API command or webhook;
2. commit inventory state/event changes and durable delivery intent to Neon;
3. publish the resulting work to Cloudflare Queue;
4. Queue consumers perform external side effects idempotently;
5. persist processed/failure state back to Neon;
6. use a low-frequency Cloudflare scheduled handler to republish durable pending rows that were committed but never successfully queued or became stale.

The scheduled handler is a reconciliation safety net. It does not poll Notion and is not a recreation of the old infinite worker loop.

## Why Cloudflare over Vercel for this domain

Vercel remains a valid application host, but Product Tracker benefits from standardizing backend infrastructure with the Cloudflare runtime already used by LLM4LIFE. Cloudflare currently provides:

- Workers for HTTP/API execution;
- Queues for durable asynchronous work, batching and retries;
- scheduled handlers for reconciliation;
- Workflows for future durable multi-step processes when justified;
- PostgreSQL connectivity to Neon, with Hyperdrive available as a later connection optimization.

This reduces the number of core backend platforms LLM4LIFE must operate without changing the source-of-truth model.

## Rules

- Preserve Product Tracker's event-based inventory model.
- Preserve idempotency and stable canonical keys.
- Queue delivery is at-least-once; all canonical writes and external side effects must be retry-safe.
- Keep Neon outbox/receipt records even when Cloudflare Queue is the normal delivery path.
- Do not make a remote queue publish part of the assumed database atomic boundary.
- Do not recreate continuous database polling inside Workers.
- Reconciliation may inspect Product Tracker's own durable pending-delivery ledger at a low frequency.
- Keep domain logic separate from Cloudflare-specific ingress/delivery code where practical.
- Notion remains live for personal-care edits until the hosted Cloudflare path passes the full cutover gate.
- Hyperdrive is a later optimization after functional runtime verification, not a prerequisite for first deployment.

## Migration sequence

1. Keep the verified Neon mirror unchanged.
2. Add the Cloudflare Worker HTTP entrypoint.
3. Refactor worker processing into exact-by-ID operations usable by Queue consumers and the legacy Node worker.
4. Add Queue + DLQ bindings and queue retries.
5. Publish normal webhook/outbox work immediately after durable Neon commit.
6. Add low-frequency reconciliation of missed queue publishes/stale claims.
7. Enforce Wrangler dry-run bundling in CI.
8. Provision Cloudflare queues and secrets.
9. Deploy the Worker.
10. Verify `/health` and authenticated `/v1/needs` against the Neon mirror.
11. Verify duplicate/retried API mutations create only one canonical inventory event.
12. Verify Notion webhook signature validation, deduplication and Queue consumption.
13. Verify outbound Notion projection, retry and reconciliation behavior.
14. Verify DLQ/observability.
15. Only then make Product Tracker/Neon authoritative and demote Notion to projection/rollback.
16. Evaluate Hyperdrive after the runtime is proven.

## Superseded directions

The earlier Render single-service target and subsequent Vercel Functions/Queue target are superseded by this decision. They remain historical context for why the architecture moved away from hosting around a permanent polling process and toward a consolidated event-driven runtime.
