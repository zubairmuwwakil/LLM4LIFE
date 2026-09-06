BEGIN;

CREATE TABLE IF NOT EXISTS llm4life.person_dates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id uuid NOT NULL REFERENCES llm4life.people(id) ON DELETE RESTRICT,
  date_type text NOT NULL CHECK (btrim(date_type) <> ''),
  label text NULL CHECK (label IS NULL OR btrim(label) <> ''),
  year integer NULL CHECK (year IS NULL OR year BETWEEN 1000 AND 9999),
  month smallint NOT NULL CHECK (month BETWEEN 1 AND 12),
  day smallint NOT NULL CHECK (day BETWEEN 1 AND 31),
  recurrence text NOT NULL DEFAULT 'annual' CHECK (recurrence IN ('annual','none')),
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','superseded','retracted')),
  source_kind text NOT NULL CHECK (source_kind IN (
    'user_asserted','user_edited_import','provider_observation','calendar_import','model_suggestion'
  )),
  source_system_id text NULL REFERENCES llm4life.systems(id) ON DELETE RESTRICT,
  source_external_ref_id uuid NULL REFERENCES llm4life.external_refs(id) ON DELETE SET NULL,
  confidence numeric NULL CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
  sensitivity_class text NOT NULL DEFAULT 'standard' CHECK (sensitivity_class IN ('standard','sensitive')),
  supersedes_id uuid NULL REFERENCES llm4life.person_dates(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (supersedes_id IS NULL OR supersedes_id <> id),
  CHECK (NOT (source_kind='model_suggestion' AND sensitivity_class='sensitive')),
  CHECK (make_date(2000, month::integer, day::integer) IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS person_dates_person_type_idx
  ON llm4life.person_dates(person_id, date_type, status);
CREATE INDEX IF NOT EXISTS person_dates_annual_lookup_idx
  ON llm4life.person_dates(month, day, date_type)
  WHERE status='active' AND recurrence='annual';
CREATE INDEX IF NOT EXISTS person_dates_source_idx
  ON llm4life.person_dates(source_system_id)
  WHERE source_system_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS llm4life.person_relationship_edges (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_person_id uuid NOT NULL REFERENCES llm4life.people(id) ON DELETE RESTRICT,
  target_person_id uuid NOT NULL REFERENCES llm4life.people(id) ON DELETE RESTRICT,
  relationship_type text NOT NULL CHECK (btrim(relationship_type) <> ''),
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','historical','unknown','retracted')),
  started_on date NULL,
  ended_on date NULL,
  source_kind text NOT NULL CHECK (source_kind IN (
    'user_asserted','user_edited_import','provider_observation','interaction_observation','model_suggestion'
  )),
  source_system_id text NULL REFERENCES llm4life.systems(id) ON DELETE RESTRICT,
  source_external_ref_id uuid NULL REFERENCES llm4life.external_refs(id) ON DELETE SET NULL,
  confidence numeric NULL CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
  sensitivity_class text NOT NULL DEFAULT 'standard' CHECK (sensitivity_class IN ('standard','sensitive')),
  supersedes_id uuid NULL REFERENCES llm4life.person_relationship_edges(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (source_person_id <> target_person_id),
  CHECK (ended_on IS NULL OR started_on IS NULL OR ended_on >= started_on),
  CHECK (supersedes_id IS NULL OR supersedes_id <> id),
  CHECK (NOT (source_kind='model_suggestion' AND sensitivity_class='sensitive'))
);

CREATE INDEX IF NOT EXISTS person_relationship_edges_source_idx
  ON llm4life.person_relationship_edges(source_person_id, relationship_type, status);
CREATE INDEX IF NOT EXISTS person_relationship_edges_target_idx
  ON llm4life.person_relationship_edges(target_person_id, relationship_type, status);
CREATE INDEX IF NOT EXISTS person_relationship_edges_source_system_idx
  ON llm4life.person_relationship_edges(source_system_id)
  WHERE source_system_id IS NOT NULL;

COMMIT;
