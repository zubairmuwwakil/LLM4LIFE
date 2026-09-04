-- Synthetic-only validation for db/migrations/004_people.sql.
-- Run on a disposable database/Neon branch after migrations 001-004.

DO $$
DECLARE
  p_same_name_a uuid := gen_random_uuid();
  p_same_name_b uuid := gen_random_uuid();
  v_interaction_id uuid := gen_random_uuid();
  v_action_id uuid := gen_random_uuid();
  v_fact_old uuid := gen_random_uuid();
  v_fact_new uuid := gen_random_uuid();
  duplicate_blocked boolean := false;
  successor_blocked boolean := false;
  sensitive_model_blocked boolean := false;
  row_count integer;
BEGIN
  INSERT INTO llm4life.people (id, display_name)
  VALUES
    (p_same_name_a, 'Synthetic Same Name'),
    (p_same_name_b, 'Synthetic Same Name');

  SELECT count(*) INTO row_count
  FROM llm4life.people
  WHERE id IN (p_same_name_a, p_same_name_b);
  IF row_count <> 2 THEN
    RAISE EXCEPTION 'same-name people must remain distinct';
  END IF;

  INSERT INTO llm4life.external_refs (
    internal_type, internal_id, system_id, account_scope, external_id, ref_kind
  ) VALUES (
    'person', p_same_name_a, 'google_contacts', 'synthetic-account', 'people/synthetic-a', 'contact'
  );

  -- Exact provider-ref rerun must be idempotent.
  INSERT INTO llm4life.external_refs (
    internal_type, internal_id, system_id, account_scope, external_id, ref_kind
  ) VALUES (
    'person', p_same_name_a, 'google_contacts', 'synthetic-account', 'people/synthetic-a', 'contact'
  ) ON CONFLICT DO NOTHING;

  SELECT count(*) INTO row_count
  FROM llm4life.external_refs
  WHERE internal_type = 'person'
    AND internal_id = p_same_name_a
    AND system_id = 'google_contacts'
    AND account_scope = 'synthetic-account'
    AND external_id = 'people/synthetic-a';
  IF row_count <> 1 THEN
    RAISE EXCEPTION 'external-ref rerun created a duplicate';
  END IF;

  -- Same provider object cannot map to another person in the same account.
  BEGIN
    INSERT INTO llm4life.external_refs (
      internal_type, internal_id, system_id, account_scope, external_id, ref_kind
    ) VALUES (
      'person', p_same_name_b, 'google_contacts', 'synthetic-account', 'people/synthetic-a', 'contact'
    );
  EXCEPTION WHEN unique_violation THEN
    duplicate_blocked := true;
  END;
  IF NOT duplicate_blocked THEN
    RAISE EXCEPTION 'external-ref uniqueness did not block duplicate mapping';
  END IF;

  -- The same provider external ID may exist independently in another account.
  INSERT INTO llm4life.external_refs (
    internal_type, internal_id, system_id, account_scope, external_id, ref_kind
  ) VALUES (
    'person', p_same_name_b, 'google_contacts', 'synthetic-account-2', 'people/synthetic-a', 'contact'
  );
  SELECT count(*) INTO row_count
  FROM llm4life.external_refs
  WHERE internal_type = 'person' AND system_id = 'google_contacts'
    AND external_id = 'people/synthetic-a';
  IF row_count <> 2 THEN
    RAISE EXCEPTION 'account-scoped external IDs were not modeled independently';
  END IF;

  -- Renaming a contact/person leaves stable identity + provider ref unchanged.
  UPDATE llm4life.people SET display_name = 'Synthetic Renamed' WHERE id = p_same_name_a;
  IF NOT EXISTS (
    SELECT 1 FROM llm4life.external_refs
    WHERE internal_type = 'person' AND internal_id = p_same_name_a
      AND system_id = 'google_contacts' AND account_scope = 'synthetic-account'
      AND external_id = 'people/synthetic-a'
  ) THEN
    RAISE EXCEPTION 'rename broke provider identity mapping';
  END IF;

  -- A provider contact can be archived without archiving the real person.
  INSERT INTO llm4life.external_refs (
    internal_type, internal_id, system_id, account_scope, external_id, ref_kind, archived_at
  ) VALUES (
    'person', p_same_name_b, 'apple_contacts', 'synthetic-device', 'apple/synthetic-b', 'source_contact', now()
  );
  IF NOT EXISTS (
    SELECT 1 FROM llm4life.external_refs
    WHERE internal_type = 'person' AND internal_id = p_same_name_b
      AND system_id = 'apple_contacts' AND archived_at IS NOT NULL
  ) THEN
    RAISE EXCEPTION 'archived provider ref was not preserved';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM llm4life.people WHERE id = p_same_name_b AND status = 'active') THEN
    RAISE EXCEPTION 'provider archive must not implicitly archive the person';
  END IF;

  -- Fact provenance + one-successor supersession.
  INSERT INTO llm4life.person_facts (
    id, person_id, fact_key, value, source_kind, asserted_at
  ) VALUES (
    v_fact_old, p_same_name_a, 'synthetic.preference', '"old"'::jsonb, 'user_asserted', now()
  );
  INSERT INTO llm4life.person_facts (
    id, person_id, fact_key, value, source_kind, asserted_at, supersedes_id
  ) VALUES (
    v_fact_new, p_same_name_a, 'synthetic.preference', '"new"'::jsonb, 'user_asserted', now(), v_fact_old
  );
  BEGIN
    INSERT INTO llm4life.person_facts (
      person_id, fact_key, value, source_kind, asserted_at, supersedes_id
    ) VALUES (
      p_same_name_a, 'synthetic.preference', '"third"'::jsonb, 'user_asserted', now(), v_fact_old
    );
  EXCEPTION WHEN unique_violation THEN
    successor_blocked := true;
  END;
  IF NOT successor_blocked THEN
    RAISE EXCEPTION 'fact supersession allowed multiple direct successors';
  END IF;

  -- Sensitive model suggestions are never silently persisted as durable facts.
  BEGIN
    INSERT INTO llm4life.person_facts (
      person_id, fact_key, value, source_kind, sensitivity_class
    ) VALUES (
      p_same_name_a, 'synthetic.sensitive', 'true'::jsonb, 'model_suggestion', 'sensitive'
    );
  EXCEPTION WHEN check_violation THEN
    sensitive_model_blocked := true;
  END;
  IF NOT sensitive_model_blocked THEN
    RAISE EXCEPTION 'sensitive model suggestion was persisted';
  END IF;

  -- One interaction can link multiple people.
  INSERT INTO llm4life.interactions (
    id, interaction_key, occurred_on, interaction_type, source_kind
  ) VALUES (
    v_interaction_id, 'synthetic-interaction-1', current_date, 'synthetic_test', 'user_asserted'
  );
  INSERT INTO llm4life.interaction_people (interaction_id, person_id)
  VALUES (v_interaction_id, p_same_name_a), (v_interaction_id, p_same_name_b);
  SELECT count(*) INTO row_count
  FROM llm4life.interaction_people ip WHERE ip.interaction_id = v_interaction_id;
  IF row_count <> 2 THEN
    RAISE EXCEPTION 'multi-person interaction linkage failed';
  END IF;

  -- Follow-up linkage reuses one canonical action and creates no provider task
  -- or calendar ref as a side effect of relational linkage.
  INSERT INTO llm4life.actions (id, action_key, title, status, domain)
  VALUES (v_action_id, 'synthetic-people-action', 'Synthetic people follow-up', 'next', 'personal');
  INSERT INTO llm4life.action_people (action_id, person_id)
  VALUES (v_action_id, p_same_name_a)
  ON CONFLICT DO NOTHING;
  INSERT INTO llm4life.action_people (action_id, person_id)
  VALUES (v_action_id, p_same_name_a)
  ON CONFLICT DO NOTHING;

  SELECT count(*) INTO row_count
  FROM llm4life.action_people ap
  WHERE ap.action_id = v_action_id AND ap.person_id = p_same_name_a;
  IF row_count <> 1 THEN
    RAISE EXCEPTION 'action_people rerun duplicated linkage';
  END IF;

  IF EXISTS (
    SELECT 1 FROM llm4life.external_refs
    WHERE internal_type = 'action'
      AND internal_id = v_action_id
      AND system_id IN ('google_tasks', 'google_calendar')
  ) THEN
    RAISE EXCEPTION 'people linkage accidentally created provider task/calendar ref';
  END IF;

  -- Clean synthetic rows from the disposable branch after successful checks.
  DELETE FROM llm4life.action_people WHERE action_id = v_action_id;
  DELETE FROM llm4life.actions WHERE id = v_action_id;
  DELETE FROM llm4life.interaction_people WHERE interaction_id = v_interaction_id;
  DELETE FROM llm4life.interactions WHERE id = v_interaction_id;
  DELETE FROM llm4life.person_facts WHERE id IN (v_fact_new, v_fact_old);
  DELETE FROM llm4life.external_refs WHERE internal_type = 'person' AND internal_id IN (p_same_name_a, p_same_name_b);
  DELETE FROM llm4life.relationships WHERE person_id IN (p_same_name_a, p_same_name_b);
  DELETE FROM llm4life.people WHERE id IN (p_same_name_a, p_same_name_b);
END;
$$;
