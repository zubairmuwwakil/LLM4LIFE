# 2026-09-03 — Product Tracker Runtime: Vercel + Neon + Event-Driven Async Work

**Status:** Adopted target architecture. The Neon mirror is live; the runtime cutover is not yet complete.

## Context

Product Tracker's existing implementation was designed as a conventional Node/Fastify API plus a continuously running PostgreSQL-backed inbox/outbox polling worker.

A temporary free-hosting design proposed putting the API and polling loop into one Render web-service process. That would accommodate the existing implementation, but it optimizes hosting around an implementation detail rather than choosing the best long-term architecture.

The user already uses Vercel and wants free/already-paid, scalable, production-grade infrastructure with minimal service sprawl.

Current Vercel supports Fastify deployments through Vercel Functions and provides durable asynchronous primitives such as Vercel Queues / Workflows. Vercel Hobby Cron is not appropriate for frequent polling, so the system should become event-driven rather than replace an always-on worker with frequent scheduled polls.

## Decision

Use this as the Product Tracker target runtime:

```text
ChatGPT / clients / Notion webhook
              |
              v
        Product Tracker API
          Vercel Functions
              |
              v
             Neon
 canonical inventory/event state
              |
              v
 durable asynchronous processing
 Vercel Queue/Workflow primitive
              |
              v
 Notion projection / notifications / future clients
```

### Neon remains canonical

Product Tracker inventory state, inventory events, balances, idempotency records, webhook receipts, and reconciliation metadata remain in the dedicated `product_tracker` database inside the existing LLM4LIFE Neon project.

Vercel is a runtime, not the canonical inventory database.

### Fastify remains acceptable

Do not rewrite the API merely to adopt Vercel. Fastify can be hosted through Vercel Functions. Domain logic should stay independent of the hosting adapter.

### Replace infinite polling with event-driven work

The existing `while` polling worker is transitional implementation debt.

Target behavior:

1. inbound API or webhook request validates/authenticates;
2. canonical database transaction records the domain change and any required durable work intent;
3. asynchronous work is dispatched to a durable Vercel queue/workflow primitive;
4. consumers perform projection/side effects idempotently;
5. failures retry without duplicating the canonical inventory event;
6. reconciliation remains available for drift detection and recovery.

Do not introduce a frequent Vercel Hobby Cron simply to emulate the old worker loop.

### Transactional correctness remains mandatory

Moving to an event-driven host must not weaken the existing design guarantees:

- stable canonical product/need keys;
- inventory changes represented as events;
- no direct uncontrolled balance mutation;
- idempotency keys on external writes;
- durable webhook receipt/deduplication;
- retry-safe Notion projection;
- observable failed work;
- reconciliation path for missed external events.

If Vercel's native delivery primitive cannot provide an atomic publish with the Neon transaction, retain a database outbox/dispatch record and use a safe dispatcher pattern rather than accepting a dual-write race.

## Why not Render as the target

Render is not rejected as a platform generally. It is rejected as the Product Tracker **target** because the proposed free design was primarily preserving a long-running polling process.

That would:

- add another hosting platform to the stack;
- preserve an unnecessary always-running worker abstraction;
- expose the free web-service sleep/wake behavior to an operational workflow;
- make the hosting choice harder to replace later.

The event-driven Vercel design better matches the user's existing stack and reduces service sprawl.

## Migration sequence

1. Keep the verified Neon mirror unchanged.
2. Remove Render-specific deployment configuration from Product Tracker.
3. Make the Fastify API Vercel-compatible without moving domain logic into platform-specific handlers.
4. Refactor the polling worker into durable event/queue/workflow consumers.
5. Preserve/rework the database outbox where needed for atomicity and reconciliation.
6. Deploy on Vercel.
7. Verify `/health` and authenticated `/v1/needs` against the Neon mirror.
8. Verify one API inventory mutation is exactly-once at the domain-event level under retries.
9. Verify Notion webhook ingestion and deduplication.
10. Verify asynchronous projection and retry behavior.
11. Verify drift reconciliation.
12. Only then make Product Tracker/Neon authoritative and demote Notion to projection/rollback.

## Superseded runtime direction

Any earlier Product Tracker documentation describing a free Render web service with `RUN_WORKER_IN_PROCESS=true` as the target hosted runtime is superseded by this decision.

The reusable worker-loop refactor may remain temporarily if it is useful during migration, but it is not the desired end-state runtime architecture.
