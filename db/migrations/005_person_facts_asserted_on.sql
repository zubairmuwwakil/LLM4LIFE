-- Preserve date-only provenance for imported People facts without inventing a clock time.

BEGIN;

ALTER TABLE llm4life.person_facts
  ADD COLUMN IF NOT EXISTS asserted_on date;

CREATE INDEX IF NOT EXISTS person_facts_asserted_on_idx
  ON llm4life.person_facts(person_id, asserted_on DESC)
  WHERE asserted_on IS NOT NULL;

COMMIT;
