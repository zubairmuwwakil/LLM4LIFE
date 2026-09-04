# LLM4LIFE Database

This directory contains the public, credential-free schema for LLM4LIFE's durable machine-state backend.

## Role

The database is **not** a universal copy of the user's life.

It stores machine-readable state that the orchestration layer itself needs to operate reliably, such as:

- system/integration registry;
- external object references;
- jobs and execution runs;
- normalized events;
- action/audit receipts;
- sync checkpoints;
- household/vehicle assets and maintenance schedules;
- shopping/grocery state where useful.

Narrative knowledge remains in Obsidian. Engineering state remains in Jira/GitHub. Financial domain state remains in InUnity and provider systems. Health data is not copied here by default.

## Provider

Current target: **Neon PostgreSQL**.

The architecture is PostgreSQL-first rather than Neon-specific so the database can be moved later if necessary.

## Migrations

Apply migrations in filename order:

```text
db/migrations/001_core.sql
```

A local/runtime `DATABASE_URL` may be used by migration tooling, but its actual value must never be committed.

## Safety

Before applying a migration to the primary database:

1. verify the target project/database;
2. use a Neon branch or other disposable database for schema validation when practical;
3. review destructive statements separately;
4. preserve rollback/recovery options;
5. never place secrets or private example rows in migration files.

## Data minimization

`jsonb` columns exist for integration flexibility, not as permission to dump raw provider payloads.

Prefer normalized fields and minimal purpose-specific metadata. Do not ingest complete conversations, emails, health records, credentials, bank identifiers, or other sensitive payloads merely because storage is available.

## Next implementation steps

1. Apply `001_core.sql` to a disposable Neon branch and validate constraints/indexes.
2. Seed only non-sensitive system identifiers required by runtime code.
3. Add a small deterministic data-access layer.
4. Move automation/job registry and receipts from documentation-only state into the database.
5. Migrate one operational domain at a time; avoid long-term dual-write.
