BEGIN;

CREATE OR REPLACE FUNCTION llm4life.replace_calendar_execution_binding(
    p_action_id uuid,
    p_external_id text,
    p_account_scope text,
    p_metadata jsonb DEFAULT '{}'::jsonb
)
RETURNS TABLE(ref_id uuid, action_id uuid, external_id text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'pg_catalog', 'llm4life'
AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM llm4life.actions a WHERE a.id = p_action_id) THEN
        RAISE EXCEPTION 'action % does not exist', p_action_id USING ERRCODE = 'P0002';
    END IF;
    IF p_external_id IS NULL OR btrim(p_external_id) = '' THEN
        RAISE EXCEPTION 'external_id is required' USING ERRCODE = '22023';
    END IF;
    IF p_account_scope IS NULL OR btrim(p_account_scope) = '' THEN
        RAISE EXCEPTION 'account_scope is required' USING ERRCODE = '22023';
    END IF;

    -- Archive every other active execution binding for this action in the same
    -- transaction that establishes the replacement. Historical/status/recovery
    -- refs are intentionally untouched.
    UPDATE llm4life.external_refs er
       SET archived_at = now(), updated_at = now()
     WHERE er.internal_type = 'action'
       AND er.internal_id = p_action_id
       AND er.system_id = 'google_calendar'
       AND er.ref_kind = 'execution_binding'
       AND er.archived_at IS NULL
       AND er.external_id IS DISTINCT FROM p_external_id;

    RETURN QUERY
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
    VALUES (
        'action',
        p_action_id,
        'google_calendar',
        p_external_id,
        'execution_binding',
        COALESCE(p_metadata, '{}'::jsonb),
        p_account_scope,
        now(),
        now(),
        NULL,
        now()
    )
    ON CONFLICT (system_id, account_scope, internal_type, external_id)
        WHERE external_id IS NOT NULL
    DO UPDATE SET
        ref_kind = 'execution_binding',
        metadata = llm4life.external_refs.metadata || EXCLUDED.metadata,
        archived_at = NULL,
        last_seen_at = now(),
        updated_at = now()
    WHERE llm4life.external_refs.internal_id = EXCLUDED.internal_id
    RETURNING id, internal_id, llm4life.external_refs.external_id;
END;
$$;

COMMENT ON FUNCTION llm4life.replace_calendar_execution_binding(uuid, text, text, jsonb)
IS 'Guarded Task Engine API: atomically archive prior active execution bindings and establish exactly one replacement Google Calendar execution binding.';

COMMIT;
