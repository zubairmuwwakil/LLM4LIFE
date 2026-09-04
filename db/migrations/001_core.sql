-- LLM4LIFE v2 core schema
-- Public architecture/migration only. Never place real credentials or private payloads here.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS llm4life;

CREATE OR REPLACE FUNCTION llm4life.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

-- Registry of systems known to the orchestration layer.
CREATE TABLE IF NOT EXISTS llm4life.systems (
  id text PRIMARY KEY,
  kind text NOT NULL,
  canonical_role text,
  lifecycle_status text NOT NULL DEFAULT 'active'
    CHECK (lifecycle_status IN ('active', 'transitional', 'optional', 'retired')),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER systems_set_updated_at
BEFORE UPDATE ON llm4life.systems
FOR EACH ROW EXECUTE FUNCTION llm4life.set_updated_at();

-- Cross-system references without copying the provider-owned object itself.
CREATE TABLE IF NOT EXISTS llm4life.external_refs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  internal_type text NOT NULL,
  internal_id uuid NOT NULL,
  system_id text NOT NULL REFERENCES llm4life.systems(id),
  external_id text,
  external_url text,
  ref_kind text NOT NULL DEFAULT 'primary',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (external_id IS NOT NULL OR external_url IS NOT NULL)
);

CREATE UNIQUE INDEX IF NOT EXISTS external_refs_external_identity_uq
  ON llm4life.external_refs(system_id, internal_type, external_id)
  WHERE external_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS external_refs_internal_idx
  ON llm4life.external_refs(internal_type, internal_id);

CREATE TRIGGER external_refs_set_updated_at
BEFORE UPDATE ON llm4life.external_refs
FOR EACH ROW EXECUTE FUNCTION llm4life.set_updated_at();

-- Durable job definitions. The runner may be ChatGPT Automations, cron, a worker,
-- or another adapter; the registry is independent of the execution vendor.
CREATE TABLE IF NOT EXISTS llm4life.jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_key text NOT NULL UNIQUE,
  name text NOT NULL,
  domain text NOT NULL,
  handler text NOT NULL,
  enabled boolean NOT NULL DEFAULT true,
  trigger_kind text NOT NULL
    CHECK (trigger_kind IN ('schedule', 'condition', 'event', 'manual')),
  schedule_expression text,
  timezone text,
  config jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK ((trigger_kind = 'schedule' AND schedule_expression IS NOT NULL)
      OR trigger_kind <> 'schedule')
);

CREATE TRIGGER jobs_set_updated_at
BEFORE UPDATE ON llm4life.jobs
FOR EACH ROW EXECUTE FUNCTION llm4life.set_updated_at();

-- One row per attempted execution. run_key is the idempotency boundary.
CREATE TABLE IF NOT EXISTS llm4life.job_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id uuid NOT NULL REFERENCES llm4life.jobs(id) ON DELETE RESTRICT,
  run_key text NOT NULL,
  status text NOT NULL
    CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'skipped')),
  triggered_at timestamptz NOT NULL DEFAULT now(),
  started_at timestamptz,
  finished_at timestamptz,
  input_fingerprint text,
  output_summary text,
  error_code text,
  error_summary text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE (job_id, run_key),
  CHECK (finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at)
);

CREATE INDEX IF NOT EXISTS job_runs_job_time_idx
  ON llm4life.job_runs(job_id, triggered_at DESC);

-- Normalized event envelope for event-driven workflows. Payloads should be
-- minimal and purpose-specific; do not ingest full conversations by default.
CREATE TABLE IF NOT EXISTS llm4life.events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_key text NOT NULL UNIQUE,
  event_type text NOT NULL,
  source_system_id text REFERENCES llm4life.systems(id),
  subject_type text,
  subject_id uuid,
  occurred_at timestamptz NOT NULL,
  received_at timestamptz NOT NULL DEFAULT now(),
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS events_type_time_idx
  ON llm4life.events(event_type, occurred_at DESC);
CREATE INDEX IF NOT EXISTS events_subject_idx
  ON llm4life.events(subject_type, subject_id);

-- Auditable receipt for meaningful autonomous writes. This replaces the need
-- for Notion to be the long-term audit backend while remaining projection-friendly.
CREATE TABLE IF NOT EXISTS llm4life.action_receipts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  action_key text NOT NULL UNIQUE,
  action_type text NOT NULL,
  source_system_id text REFERENCES llm4life.systems(id),
  destination_system_id text REFERENCES llm4life.systems(id),
  subject_type text,
  subject_id uuid,
  status text NOT NULL
    CHECK (status IN ('planned', 'succeeded', 'failed', 'reverted', 'skipped')),
  reversible boolean NOT NULL DEFAULT true,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  summary text NOT NULL,
  source_ref text,
  destination_ref text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS action_receipts_time_idx
  ON llm4life.action_receipts(occurred_at DESC);
CREATE INDEX IF NOT EXISTS action_receipts_subject_idx
  ON llm4life.action_receipts(subject_type, subject_id);

-- Cursor/checkpoint storage for deterministic integrations and pollers.
CREATE TABLE IF NOT EXISTS llm4life.sync_checkpoints (
  integration_key text PRIMARY KEY,
  cursor_value text,
  checkpoint_at timestamptz NOT NULL DEFAULT now(),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER sync_checkpoints_set_updated_at
BEFORE UPDATE ON llm4life.sync_checkpoints
FOR EACH ROW EXECUTE FUNCTION llm4life.set_updated_at();

-- Household + vehicle assets share one generic asset model. Domain-specific
-- providers can be linked through external_refs rather than copied here.
CREATE TABLE IF NOT EXISTS llm4life.assets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  asset_type text NOT NULL,
  name text NOT NULL,
  location_label text,
  status text NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'inactive', 'disposed', 'archived')),
  acquired_on date,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS assets_type_status_idx
  ON llm4life.assets(asset_type, status);

CREATE TRIGGER assets_set_updated_at
BEFORE UPDATE ON llm4life.assets
FOR EACH ROW EXECUTE FUNCTION llm4life.set_updated_at();

-- Recurring maintenance can be date-based, usage/meter-based, or one-time.
CREATE TABLE IF NOT EXISTS llm4life.maintenance_rules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  asset_id uuid NOT NULL REFERENCES llm4life.assets(id) ON DELETE CASCADE,
  rule_key text NOT NULL,
  title text NOT NULL,
  cadence_kind text NOT NULL
    CHECK (cadence_kind IN ('days', 'meter', 'date', 'manual')),
  interval_days integer,
  interval_meter numeric,
  meter_unit text,
  next_due_date date,
  next_due_meter numeric,
  instructions text,
  enabled boolean NOT NULL DEFAULT true,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (asset_id, rule_key),
  CHECK (interval_days IS NULL OR interval_days > 0),
  CHECK (interval_meter IS NULL OR interval_meter > 0)
);

CREATE INDEX IF NOT EXISTS maintenance_rules_due_date_idx
  ON llm4life.maintenance_rules(next_due_date)
  WHERE enabled = true;

CREATE TRIGGER maintenance_rules_set_updated_at
BEFORE UPDATE ON llm4life.maintenance_rules
FOR EACH ROW EXECUTE FUNCTION llm4life.set_updated_at();

CREATE TABLE IF NOT EXISTS llm4life.maintenance_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  asset_id uuid NOT NULL REFERENCES llm4life.assets(id) ON DELETE CASCADE,
  rule_id uuid REFERENCES llm4life.maintenance_rules(id) ON DELETE SET NULL,
  completed_at timestamptz NOT NULL,
  meter_value numeric,
  meter_unit text,
  notes text,
  source_system_id text REFERENCES llm4life.systems(id),
  receipt_id uuid REFERENCES llm4life.action_receipts(id) ON DELETE SET NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS maintenance_events_asset_time_idx
  ON llm4life.maintenance_events(asset_id, completed_at DESC);

-- Generic shopping/grocery lists. Keep this small: list state, not a retailer ERP.
CREATE TABLE IF NOT EXISTS llm4life.shopping_lists (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  list_type text NOT NULL DEFAULT 'general',
  status text NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'archived')),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (name, list_type)
);

CREATE TRIGGER shopping_lists_set_updated_at
BEFORE UPDATE ON llm4life.shopping_lists
FOR EACH ROW EXECUTE FUNCTION llm4life.set_updated_at();

CREATE TABLE IF NOT EXISTS llm4life.shopping_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  list_id uuid NOT NULL REFERENCES llm4life.shopping_lists(id) ON DELETE CASCADE,
  item_key text,
  name text NOT NULL,
  quantity text,
  state text NOT NULL DEFAULT 'needed'
    CHECK (state IN ('needed', 'planned', 'purchased', 'removed')),
  priority smallint NOT NULL DEFAULT 0 CHECK (priority BETWEEN 0 AND 5),
  preferred_retailer text,
  notes text,
  added_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS shopping_items_active_key_uq
  ON llm4life.shopping_items(list_id, item_key)
  WHERE item_key IS NOT NULL AND state IN ('needed', 'planned');
CREATE INDEX IF NOT EXISTS shopping_items_active_idx
  ON llm4life.shopping_items(list_id, state, priority DESC, added_at);

CREATE TRIGGER shopping_items_set_updated_at
BEFORE UPDATE ON llm4life.shopping_items
FOR EACH ROW EXECUTE FUNCTION llm4life.set_updated_at();

COMMIT;
