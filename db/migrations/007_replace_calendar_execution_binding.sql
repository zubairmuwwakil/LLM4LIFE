CREATE OR REPLACE FUNCTION llm4life.replace_calendar_execution_binding(
    p_action_id uuid,
    p_external_id text,
    p_account_scope text,
    p_metadata jsonb DEFAULT '{}'::jsonb
)
RETURNS TABLE(ref_id uuid, action_id uuid, external_id text)
LANGUAGE sql
SECURITY DEFINER
SET search_path TO 'pg_catalog', 'llm4life'
AS '
WITH valid_input AS (
    SELECT a.id AS action_id,
           p_external_id AS external_id,
           p_account_scope AS account_scope
    FROM llm4life.actions a
    WHERE a.id = p_action_id
      AND p_external_id IS NOT NULL
      AND btrim(p_external_id) <> ''''
      AND p_account_scope IS NOT NULL
      AND btrim(p_account_scope) <> ''''
),
archived AS (
    UPDATE llm4life.external_refs er
       SET archived_at = current_timestamp,
           updated_at = current_timestamp
      FROM valid_input v
     WHERE er.internal_type = ''action''
       AND er.internal_id = v.action_id
       AND er.system_id = ''google_calendar''
       AND er.ref_kind = ''execution_binding''
       AND er.archived_at IS NULL
       AND er.external_id IS DISTINCT FROM v.external_id
    RETURNING er.id
),
upserted AS (
    INSERT INTO llm4life.external_refs (
        internal_type,
        internal_id,
        system_id,
        external_id,
        ref_kind,
        metadata,
        account_scope,
        first_seen_at,
        last_seen_at,
        archived_at,
        updated_at
    )
    SELECT
        ''action'',
        v.action_id,
        ''google_calendar'',
        v.external_id,
        ''execution_binding'',
        COALESCE(p_metadata, ''{}''::jsonb),
        v.account_scope,
        current_timestamp,
        current_timestamp,
        NULL,
        current_timestamp
    FROM valid_input v
    ON CONFLICT (system_id, account_scope, internal_type, external_id)
        WHERE external_id IS NOT NULL
    DO UPDATE SET
        ref_kind = ''execution_binding'',
        metadata = llm4life.external_refs.metadata || EXCLUDED.metadata,
        archived_at = NULL,
        last_seen_at = current_timestamp,
        updated_at = current_timestamp
    WHERE llm4life.external_refs.internal_id = EXCLUDED.internal_id
    RETURNING id, internal_id, llm4life.external_refs.external_id
)
SELECT u.id, u.internal_id, u.external_id
FROM upserted u
';

COMMENT ON FUNCTION llm4life.replace_calendar_execution_binding(uuid, text, text, jsonb)
IS 'Guarded Task Engine API: atomically archive prior active execution bindings and establish exactly one replacement Google Calendar execution binding.';

CREATE OR REPLACE FUNCTION llm4life.archive_action_execution_bindings(
    p_action_id uuid
)
RETURNS integer
LANGUAGE sql
SECURITY DEFINER
SET search_path TO 'pg_catalog', 'llm4life'
AS '
WITH archived AS (
    UPDATE llm4life.external_refs er
       SET archived_at = current_timestamp,
           updated_at = current_timestamp
     WHERE er.internal_type = ''action''
       AND er.internal_id = p_action_id
       AND er.system_id = ''google_calendar''
       AND er.ref_kind = ''execution_binding''
       AND er.archived_at IS NULL
    RETURNING 1
)
SELECT count(*)::integer FROM archived
';

COMMENT ON FUNCTION llm4life.archive_action_execution_bindings(uuid)
IS 'Guarded Task Engine API: archive all active Google Calendar execution bindings for one action without exposing raw external_refs rows.';
