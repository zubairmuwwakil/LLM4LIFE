-- LLM4LIFE People/Relationships Phase 1 schema.
--
-- Public schema only: never place real contact payloads, provider IDs, emails,
-- phone numbers, birthdays, relationship notes, credentials, or message bodies
-- in this repository.
--
-- This migration intentionally reuses llm4life.external_refs for People rather
-- than introducing a person_external_refs duplicate abstraction.

BEGIN;

-- People exposed a generic gap in external_refs: provider IDs are only unique
-- inside an account/provider scope. Add explicit scope and lightweight source
-- lifecycle metadata so all domains can use the same cross-system primitive.
ALTER TABLE llm4life.external_refs
  ADD COLUMN IF NOT EXISTS account_scope text,
  ADD COLUMN IF NOT EXISTS first_seen_at timestamptz,
  ADD COLUMN IF NOT EXISTS last_seen_at timestamptz,
  ADD COLUMN IF NOT EXISTS archived_at timestamptz;

UPDATE llm4life.external_refs
SET account_scope = COALESCE(NULLIF(btrim(account_scope), ''), 'default'),
    first_seen_at = COALESCE(first_seen_at, created_at),
    last_seen_at = COALESCE(last_seen_at, updated_at, created_at);

ALTER TABLE llm4life.external_refs
  ALTER COLUMN account_scope SET DEFAULT 'default',
  ALTER COLUMN account_scope SET NOT NULL,
  ALTER COLUMN first_seen_at SET DEFAULT now(),
  ALTER COLUMN first_seen_at SET NOT NULL,
  ALTER COLUMN last_seen_at SET DEFAULT now(),
  ALTER COLUMN last_seen_at SET NOT NULL;

ALTER TABLE llm4life.external_refs
  ADD CONSTRAINT external_refs_account_scope_nonblank_ck
    CHECK (btrim(account_scope) <> ''),
  ADD CONSTRAINT external_refs_seen_order_ck
    CHECK (last_seen_at >= first_seen_at),
  ADD CONSTRAINT external_refs_archive_order_ck
    CHECK (archived_at IS NULL OR archived_at >= first_seen_at);

DROP INDEX IF EXISTS llm4life.external_refs_external_identity_uq;
CREATE UNIQUE INDEX external_refs_external_identity_uq
  ON llm4life.external_refs(system_id, account_scope, internal_type, external_id)
  WHERE external_id IS NOT NULL;

-- Production currently has this redundant ad-hoc index even though migrations
-- 001-003 do not define it. The generic scoped identity index above already
-- enforces the same invariant for action refs and is the canonical definition.
DROP INDEX IF EXISTS llm4life.external_refs_google_calendar_action_external_id_uq;

-- Non-sensitive system-registry rows required for future People references.
INSERT INTO llm4life.systems (id, kind, canonical_role, lifecycle_status)
VALUES
  ('google_contacts', 'address_book', 'contact_field_authority_candidate', 'transitional'),
  ('apple_contacts', 'address_book_client', 'migration_source_and_future_client', 'transitional'),
  ('obsidian', 'knowledge_store', 'narrative_relationship_context', 'active')
ON CONFLICT (id) DO NOTHING;

-- Stable internal person identity. display_name is nullable because real
-- provider contacts can be nameless (for example, phone/email-only records).
CREATE TABLE IF NOT EXISTS llm4life.people (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  display_name text,
  preferred_name text,
  status text NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'dormant', 'archived', 'merged')),
  merged_into_person_id uuid REFERENCES llm4life.people(id) ON DELETE RESTRICT,
  archived_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (display_name IS NULL OR btrim(display_name) <> ''),
  CHECK (preferred_name IS NULL OR btrim(preferred_name) <> ''),
  CHECK (merged_into_person_id IS NULL OR merged_into_person_id <> id),
  CHECK ((status = 'merged') = (merged_into_person_id IS NOT NULL)),
  CHECK ((status IN ('archived', 'merged')) = (archived_at IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS people_status_idx
  ON llm4life.people(status);
CREATE INDEX IF NOT EXISTS people_merged_into_idx
  ON llm4life.people(merged_into_person_id)
  WHERE merged_into_person_id IS NOT NULL;

CREATE TRIGGER people_set_updated_at
BEFORE UPDATE ON llm4life.people
FOR EACH ROW EXECUTE FUNCTION llm4life.set_updated_at();

-- One operational relationship-state row per person. This is deliberately
-- small and user-centric; narrative history remains in Obsidian.
CREATE TABLE IF NOT EXISTS llm4life.relationships (
  person_id uuid PRIMARY KEY REFERENCES llm4life.people(id) ON DELETE RESTRICT,
  relationship_type text,
  status text
    CHECK (status IS NULL OR status IN ('active', 'occasional', 'dormant', 'archived')),
  started_on date,
  ended_on date,
  check_in_cadence_days integer CHECK (check_in_cadence_days IS NULL OR check_in_cadence_days > 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (ended_on IS NULL OR started_on IS NULL OR ended_on >= started_on)
);

CREATE INDEX IF NOT EXISTS relationships_status_idx
  ON llm4life.relationships(status);

CREATE TRIGGER relationships_set_updated_at
BEFORE UPDATE ON llm4life.relationships
FOR EACH ROW EXECUTE FUNCTION llm4life.set_updated_at();

-- Structured durable facts only. Long-form context remains in Obsidian.
-- source_external_ref_id points to the generic external_refs model when a fact
-- is provider-derived. Model suggestions are not equivalent to user truth.
CREATE TABLE IF NOT EXISTS llm4life.person_facts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id uuid NOT NULL REFERENCES llm4life.people(id) ON DELETE RESTRICT,
  fact_key text NOT NULL CHECK (btrim(fact_key) <> ''),
  value jsonb NOT NULL,
  source_kind text NOT NULL
    CHECK (source_kind IN (
      'user_asserted',
      'user_edited_import',
      'provider_observation',
      'interaction_observation',
      'model_suggestion'
    )),
  source_system_id text REFERENCES llm4life.systems(id) ON DELETE RESTRICT,
  source_external_ref_id uuid REFERENCES llm4life.external_refs(id) ON DELETE SET NULL,
  source_event_id uuid REFERENCES llm4life.events(id) ON DELETE SET NULL,
  asserted_at timestamptz,
  observed_at timestamptz,
  confidence numeric(4,3) CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
  sensitivity_class text NOT NULL DEFAULT 'standard'
    CHECK (sensitivity_class IN ('standard', 'sensitive')),
  supersedes_id uuid REFERENCES llm4life.person_facts(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (supersedes_id IS NULL OR supersedes_id <> id),
  CHECK (NOT (source_kind = 'model_suggestion' AND sensitivity_class = 'sensitive'))
);

-- Importers must validate that supersedes_id belongs to the same person_id and
-- fact_key before insert. The database still prevents branching histories below.
CREATE INDEX IF NOT EXISTS person_facts_person_key_idx
  ON llm4life.person_facts(person_id, fact_key, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS person_facts_one_successor_uq
  ON llm4life.person_facts(supersedes_id)
  WHERE supersedes_id IS NOT NULL;

-- Minimal interaction metadata. occurred_on is always present; occurred_at is
-- optional so date-only history does not invent a clock time.
CREATE TABLE IF NOT EXISTS llm4life.interactions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  interaction_key text UNIQUE,
  occurred_on date NOT NULL,
  occurred_at timestamptz,
  interaction_type text NOT NULL CHECK (btrim(interaction_type) <> ''),
  channel text,
  source_kind text NOT NULL DEFAULT 'provider_observation'
    CHECK (source_kind IN ('user_asserted', 'provider_observation', 'interaction_import')),
  source_system_id text REFERENCES llm4life.systems(id) ON DELETE RESTRICT,
  summary text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS interactions_occurred_idx
  ON llm4life.interactions(occurred_on DESC, occurred_at DESC);

CREATE TABLE IF NOT EXISTS llm4life.interaction_people (
  interaction_id uuid NOT NULL REFERENCES llm4life.interactions(id) ON DELETE CASCADE,
  person_id uuid NOT NULL REFERENCES llm4life.people(id) ON DELETE RESTRICT,
  role text,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (interaction_id, person_id)
);

CREATE INDEX IF NOT EXISTS interaction_people_person_idx
  ON llm4life.interaction_people(person_id, interaction_id);

-- Relationship follow-ups stay in the existing action lifecycle. This join is
-- only relational linkage; it does not create a second task backend.
CREATE TABLE IF NOT EXISTS llm4life.action_people (
  action_id uuid NOT NULL REFERENCES llm4life.actions(id) ON DELETE CASCADE,
  person_id uuid NOT NULL REFERENCES llm4life.people(id) ON DELETE RESTRICT,
  relation_kind text NOT NULL DEFAULT 'subject' CHECK (btrim(relation_kind) <> ''),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (action_id, person_id, relation_kind)
);

CREATE INDEX IF NOT EXISTS action_people_person_idx
  ON llm4life.action_people(person_id, action_id);

COMMIT;
