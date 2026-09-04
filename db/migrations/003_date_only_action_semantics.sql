-- Preserve date-only task semantics during migration from Notion.
-- A due/follow-up date without a clock time must not be coerced into an invented timestamp.

BEGIN;

ALTER TABLE llm4life.actions
  ADD COLUMN IF NOT EXISTS due_date date,
  ADD COLUMN IF NOT EXISTS follow_up_date date;

CREATE INDEX IF NOT EXISTS actions_due_date_idx
  ON llm4life.actions(due_date)
  WHERE status NOT IN ('done', 'cancelled', 'archived');

CREATE INDEX IF NOT EXISTS actions_follow_up_date_idx
  ON llm4life.actions(follow_up_date)
  WHERE status = 'waiting';

COMMIT;
