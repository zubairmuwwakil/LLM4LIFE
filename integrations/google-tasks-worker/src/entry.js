import worker from "./index.js";
import { neon } from "@neondatabase/serverless";

const GOOGLE_TASKS = "google_tasks";
const NEON = "neon";

export default {
  async fetch(request, env, ctx) {
    const response = await worker.fetch(request, env, ctx);
    const url = new URL(request.url);
    if (request.method === "POST" && url.pathname === "/sync" && response.ok) {
      ctx.waitUntil(cleanupArchivedProjections(env));
    }
    return response;
  },

  async scheduled(controller, env, ctx) {
    await worker.scheduled(controller, env, ctx);
    ctx.waitUntil(cleanupArchivedProjections(env));
  },
};

async function cleanupArchivedProjections(env) {
  if (!env.DATABASE_URL || !env.GOOGLE_CLIENT_ID || !env.GOOGLE_CLIENT_SECRET || !env.GOOGLE_REFRESH_TOKEN) {
    return;
  }

  const sql = neon(env.DATABASE_URL);
  await sql`
    INSERT INTO llm4life.systems (id, kind, canonical_role, lifecycle_status)
    VALUES
      (${GOOGLE_TASKS}, 'external_client', 'personal_action_projection', 'active'),
      (${NEON}, 'database', 'llm4life_machine_state', 'active')
    ON CONFLICT (id) DO NOTHING
  `;

  const rows = await sql`
    SELECT
      a.id::text AS action_id,
      a.updated_at::text AS action_updated_at,
      er.id::text AS ref_id,
      er.external_id AS google_task_id,
      er.metadata
    FROM llm4life.actions a
    JOIN llm4life.external_refs er
      ON er.internal_type = 'action'
     AND er.internal_id = a.id
     AND er.system_id = ${GOOGLE_TASKS}
    WHERE a.status = 'archived'
      AND er.external_id IS NOT NULL
      AND COALESCE((er.metadata ->> 'google_projection_disabled')::boolean, false) = false
  `;

  if (!rows.length) return;
  const accessToken = await getAccessToken(env);

  for (const row of rows) {
    const deleted = await deleteGoogleTask(accessToken, row.google_task_id);
    const metadata = {
      ...(row.metadata && typeof row.metadata === 'object' ? row.metadata : {}),
      google_projection_disabled: true,
      deleted_from_projection_at: new Date().toISOString(),
      archived_cleanup: true,
      google_delete_result: deleted,
    };

    await sql`
      UPDATE llm4life.external_refs
      SET metadata = ${JSON.stringify(metadata)}::jsonb,
          updated_at = now()
      WHERE id = ${row.ref_id}::uuid
    `;

    await sql`
      INSERT INTO llm4life.action_receipts (
        action_key, action_type, source_system_id, destination_system_id,
        subject_type, subject_id, status, reversible, summary,
        source_ref, destination_ref, metadata
      )
      VALUES (
        ${`neon:archived-projection-delete:${row.action_id}:${row.action_updated_at}`},
        'projection_deleted', ${NEON}, ${GOOGLE_TASKS},
        'action', ${row.action_id}::uuid, 'succeeded', true,
        'Removed an archived action from the Google Tasks projection while preserving canonical Neon state.',
        ${row.action_id}, ${row.google_task_id},
        ${JSON.stringify({ integration: 'google-tasks-sync', archived_cleanup: true })}::jsonb
      )
      ON CONFLICT (action_key) DO NOTHING
    `;
  }
}

async function getAccessToken(env) {
  const response = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: env.GOOGLE_CLIENT_ID,
      client_secret: env.GOOGLE_CLIENT_SECRET,
      refresh_token: env.GOOGLE_REFRESH_TOKEN,
      grant_type: "refresh_token",
    }),
  });
  const body = await response.json();
  if (!response.ok || !body.access_token) {
    throw new Error(`Google token refresh failed (${response.status})`);
  }
  return body.access_token;
}

async function deleteGoogleTask(accessToken, taskId) {
  const response = await fetch(
    `https://tasks.googleapis.com/tasks/v1/lists/@default/tasks/${encodeURIComponent(taskId)}`,
    {
      method: "DELETE",
      headers: { authorization: `Bearer ${accessToken}` },
    },
  );

  if (response.ok || response.status === 404 || response.status === 410) {
    return response.status;
  }

  const body = await response.text();
  throw new Error(`Google Tasks archived cleanup failed (${response.status}): ${body.slice(0, 500)}`);
}
