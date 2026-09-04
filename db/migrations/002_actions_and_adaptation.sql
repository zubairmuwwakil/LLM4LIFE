-- LLM4LIFE v2 personal-action and adaptive-scheduling schema

BEGIN;

-- Canonical personal action state for the orchestration layer.
-- Google Tasks is the preferred user-facing action client; Calendar is the
-- execution schedule. Their provider IDs are linked through external_refs.
CREATE TABLE IF NOT EXISTS llm4life.actions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  action_key text UNIQUE,
  title text NOT NULL,
  status text NOT NULL DEFAULT 'inbox'
    CHECK (status IN ('inbox', 'next', 'scheduled', 'waiting', 'done', 'cancelled', 'archived')),
  domain text NOT NULL DEFAULT 'personal',
  priority smallint NOT NULL DEFAULT 0 CHECK (priority BETWEEN 0 AND 5),
  scheduling_rigidity text NOT NULL DEFAULT 'flexible'
    CHECK (scheduling_rigidity IN ('hard', 'semi_hard', 'flexible')),
  context text,
  location_label text,
  due_at timestamptz,
  follow_up_at timestamptz,
  scheduled_for timestamptz,
  planned_duration_min integer CHECK (planned_duration_min IS NULL OR planned_duration_min > 0),
  source_system_id text REFERENCES llm4life.systems(id),
  source_ref text,
  completed_at timestamptz,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (completed_at IS NULL OR status IN ('done', 'cancelled', 'archived'))
);

CREATE INDEX IF NOT EXISTS actions_status_due_idx
  ON llm4life.actions(status, due_at);
CREATE INDEX IF NOT EXISTS actions_follow_up_idx
  ON llm4life.actions(follow_up_at)
  WHERE status = 'waiting';
CREATE INDEX IF NOT EXISTS actions_scheduled_for_idx
  ON llm4life.actions(scheduled_for)
  WHERE status = 'scheduled';

CREATE TRIGGER actions_set_updated_at
BEFORE UPDATE ON llm4life.actions
FOR EACH ROW EXECUTE FUNCTION llm4life.set_updated_at();

-- Historical execution telemetry. This is the durable replacement target for
-- a separate SaaS "Task Execution Log" and is intentionally fact-oriented.
CREATE TABLE IF NOT EXISTS llm4life.action_executions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  action_id uuid NOT NULL REFERENCES llm4life.actions(id) ON DELETE CASCADE,
  execution_key text NOT NULL,
  outcome text NOT NULL
    CHECK (outcome IN ('planned', 'done', 'missed', 'waiting', 'cancelled')),
  planned_start timestamptz,
  planned_duration_min integer CHECK (planned_duration_min IS NULL OR planned_duration_min > 0),
  actual_start timestamptz,
  completed_at timestamptz,
  actual_duration_min integer CHECK (actual_duration_min IS NULL OR actual_duration_min >= 0),
  context text,
  calendar_kind text,
  calendar_event_ref text,
  notes text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (action_id, execution_key),
  CHECK (completed_at IS NULL OR actual_start IS NULL OR completed_at >= actual_start)
);

CREATE INDEX IF NOT EXISTS action_executions_action_time_idx
  ON llm4life.action_executions(action_id, created_at DESC);
CREATE INDEX IF NOT EXISTS action_executions_learning_idx
  ON llm4life.action_executions(context, outcome, planned_start DESC);

-- Learned scheduling/routing rules are explicit, versionable and reversible.
-- They are soft preferences and never override safety or explicit instructions.
CREATE TABLE IF NOT EXISTS llm4life.adaptive_rules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_key text NOT NULL,
  scope text NOT NULL DEFAULT 'global',
  rule_type text NOT NULL,
  value jsonb NOT NULL,
  status text NOT NULL DEFAULT 'experimental'
    CHECK (status IN ('experimental', 'active', 'reverted', 'retired')),
  confidence numeric(4,3) CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
  sample_size integer NOT NULL DEFAULT 0 CHECK (sample_size >= 0),
  evidence_summary text,
  supersedes_id uuid REFERENCES llm4life.adaptive_rules(id) ON DELETE SET NULL,
  effective_from timestamptz NOT NULL DEFAULT now(),
  reverted_at timestamptz,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS adaptive_rules_current_uq
  ON llm4life.adaptive_rules(rule_key, scope)
  WHERE status IN ('experimental', 'active');

CREATE TRIGGER adaptive_rules_set_updated_at
BEFORE UPDATE ON llm4life.adaptive_rules
FOR EACH ROW EXECUTE FUNCTION llm4life.set_updated_at();

COMMIT;
