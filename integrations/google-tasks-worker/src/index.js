import { neon } from "@neondatabase/serverless";

const SYSTEM_GOOGLE_TASKS = "google_tasks";
const SYSTEM_NEON = "neon";
const JOB_KEY = "google-tasks-sync";
const TASK_MARKER_RE = /\[LLM4LIFE:ACTION_ID=([0-9a-f-]{36})\]/i;
const GOOGLE_BATCH_SIZE = 50;
const OVERLAP_MS = 5 * 60 * 1000;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") {
      return json({ ok: true, service: "llm4life-google-tasks-sync", version: "0.2.0" });
    }
    if (request.method === "POST" && url.pathname === "/sync") {
      if (!env.SYNC_ADMIN_TOKEN) return json({ ok: false, error: "manual_sync_disabled" }, 503);
      if (request.headers.get("authorization") !== `Bearer ${env.SYNC_ADMIN_TOKEN}`) {
        return json({ ok: false, error: "unauthorized" }, 401);
      }
      try {
        const result = await sync(env, `manual:${crypto.randomUUID()}`);
        return json({ ok: true, ...result });
      } catch (error) {
        console.error(error);
        return json({ ok: false, error: safeError(error) }, 500);
      }
    }
    return json({ ok: false, error: "not_found" }, 404);
  },

  async scheduled(controller, env, ctx) {
    ctx.waitUntil(sync(env, `cron:${controller.scheduledTime}`).catch((error) => {
      console.error("Google Tasks sync failed", error);
    }));
  },
};

async function sync(env, runKey) {
  requireSecrets(env);
  const sql = neon(env.DATABASE_URL);
  await ensureRuntimeRows(sql);
  const run = await beginRun(sql, runKey);
  if (run.skipped) return { skipped: true, reason: "run_already_succeeded" };

  const summary = {
    captured: 0,
    inboundUpdated: 0,
    created: 0,
    patched: 0,
    completed: 0,
    projectionDeleted: 0,
    conflicts: 0,
    googleBatchRequests: 0,
    dbBatchRequests: 0,
  };

  try {
    const accessToken = await getAccessToken(env);
    const taskList = await ensureGoogleTaskList(env, accessToken);
    let state = await loadState(sql);

    const updatedMin = state.checkpointAt
      ? new Date(new Date(state.checkpointAt).getTime() - OVERLAP_MS).toISOString()
      : null;
    const googleDelta = await listGoogleTasks(accessToken, taskList.id, updatedMin);

    const inbound = buildInboundQueries(sql, env, taskList.id, googleDelta, state.actions, summary);
    if (inbound.queries.length) {
      await sql.transaction(inbound.queries);
      summary.dbBatchRequests += 1;
      state = await loadState(sql);
    }

    const mutations = buildOutboundMutations(env, taskList.id, state.actions);
    if (mutations.length) {
      const mutationResults = await executeGoogleBatches(accessToken, mutations);
      summary.googleBatchRequests += Math.ceil(mutations.length / GOOGLE_BATCH_SIZE);
      const outboundQueries = buildOutboundResultQueries(sql, taskList.id, mutationResults, summary);
      if (outboundQueries.length) {
        await sql.transaction(outboundQueries);
        summary.dbBatchRequests += 1;
      }
    }

    await finishSuccess(sql, run.id, taskList, summary);
    summary.dbBatchRequests += 1;
    return summary;
  } catch (error) {
    await finishFailure(sql, run.id, summary, error);
    throw error;
  }
}

function requireSecrets(env) {
  for (const name of ["DATABASE_URL", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"]) {
    if (!env[name]) throw new Error(`Missing required Worker secret: ${name}`);
  }
}

async function ensureRuntimeRows(sql) {
  await sql.transaction([
    sql`
      INSERT INTO llm4life.systems (id, kind, canonical_role, lifecycle_status)
      VALUES
        (${SYSTEM_GOOGLE_TASKS}, 'external_client', 'personal_action_projection', 'active'),
        (${SYSTEM_NEON}, 'database', 'llm4life_machine_state', 'active')
      ON CONFLICT (id) DO UPDATE SET
        kind = excluded.kind,
        canonical_role = excluded.canonical_role,
        lifecycle_status = excluded.lifecycle_status
    `,
    sql`
      INSERT INTO llm4life.jobs (
        job_key, name, domain, handler, enabled, trigger_kind,
        schedule_expression, timezone, config
      )
      VALUES (
        ${JOB_KEY}, 'Google Tasks Projection Sync', 'personal_actions',
        'cloudflare_worker:llm4life-google-tasks-sync', true, 'schedule',
        '*/15 * * * *', 'UTC',
        ${JSON.stringify({ canonical: "neon", client: "google_tasks", transport: "batched_http_v2" })}::jsonb
      )
      ON CONFLICT (job_key) DO UPDATE SET
        name = excluded.name,
        handler = excluded.handler,
        enabled = excluded.enabled,
        schedule_expression = excluded.schedule_expression,
        config = excluded.config
    `,
  ]);
}

async function beginRun(sql, runKey) {
  const rows = await sql`
    WITH job AS (
      SELECT id FROM llm4life.jobs WHERE job_key = ${JOB_KEY}
    ), prior AS (
      SELECT id, status
      FROM llm4life.job_runs
      WHERE job_id = (SELECT id FROM job) AND run_key = ${runKey}
    ), upserted AS (
      INSERT INTO llm4life.job_runs (job_id, run_key, status, triggered_at, started_at, metadata)
      SELECT (SELECT id FROM job), ${runKey}, 'running', now(), now(), '{}'::jsonb
      WHERE NOT EXISTS (SELECT 1 FROM prior WHERE status = 'succeeded')
      ON CONFLICT (job_id, run_key) DO UPDATE SET
        status = 'running', started_at = now(), finished_at = null,
        error_code = null, error_summary = null
      WHERE llm4life.job_runs.status <> 'succeeded'
      RETURNING id, status
    )
    SELECT id::text, status, false AS skipped FROM upserted
    UNION ALL
    SELECT id::text, status, true AS skipped FROM prior WHERE status = 'succeeded'
    LIMIT 1
  `;
  if (!rows[0]) throw new Error("Could not create or resolve google-tasks-sync job run");
  return rows[0];
}

async function loadState(sql) {
  const [actions, checkpoints] = await sql.transaction([
    sql`
      SELECT
        a.id::text, a.action_key, a.title, a.status, a.priority,
        a.scheduling_rigidity, a.context, a.location_label,
        a.due_date::text, a.due_at::text, a.follow_up_date::text,
        a.follow_up_at::text, a.scheduled_for::text,
        a.planned_duration_min, a.completed_at::text, a.updated_at::text,
        a.metadata,
        er.id::text AS google_ref_id,
        er.external_id AS google_task_id,
        er.external_url AS google_task_url,
        er.metadata AS google_ref_metadata
      FROM llm4life.actions a
      LEFT JOIN llm4life.external_refs er
        ON er.internal_type = 'action'
       AND er.internal_id = a.id
       AND er.system_id = ${SYSTEM_GOOGLE_TASKS}
      ORDER BY a.created_at ASC
    `,
    sql`
      SELECT checkpoint_at::text
      FROM llm4life.sync_checkpoints
      WHERE integration_key = 'google_tasks_projection'
    `,
  ], { readOnly: true });
  return { actions, checkpointAt: checkpoints[0]?.checkpoint_at ?? null };
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
    throw new Error(`Google token refresh failed (${response.status}): ${JSON.stringify(body)}`);
  }
  return body.access_token;
}

async function googleRequest(accessToken, path, init = {}) {
  const response = await fetch(`https://tasks.googleapis.com${path}`, {
    ...init,
    headers: {
      authorization: `Bearer ${accessToken}`,
      "content-type": "application/json",
      ...(init.headers ?? {}),
    },
  });
  if (response.status === 204) return null;
  const text = await response.text();
  const body = text ? JSON.parse(text) : null;
  if (!response.ok) throw new Error(`Google Tasks API ${response.status}: ${text.slice(0, 1000)}`);
  return body;
}

async function ensureGoogleTaskList(env, accessToken) {
  const title = env.GOOGLE_TASKS_LIST_TITLE || "LLM4LIFE";
  const lists = [];
  let pageToken;
  do {
    const query = new URLSearchParams({ maxResults: "100" });
    if (pageToken) query.set("pageToken", pageToken);
    const page = await googleRequest(accessToken, `/tasks/v1/users/@me/lists?${query}`);
    lists.push(...(page.items ?? []));
    pageToken = page.nextPageToken;
  } while (pageToken);

  const matches = lists.filter((item) => item.title === title);
  if (matches.length > 1) throw new Error(`More than one Google Tasks list is named ${title}; refusing ambiguous projection.`);
  return matches[0] ?? googleRequest(accessToken, "/tasks/v1/users/@me/lists", {
    method: "POST",
    body: JSON.stringify({ title }),
  });
}

async function listGoogleTasks(accessToken, taskListId, updatedMin = null) {
  const tasks = [];
  let pageToken;
  do {
    const query = new URLSearchParams({
      maxResults: "100",
      showCompleted: "true",
      showDeleted: "true",
      showHidden: "true",
    });
    if (updatedMin) query.set("updatedMin", updatedMin);
    if (pageToken) query.set("pageToken", pageToken);
    const page = await googleRequest(accessToken, `/tasks/v1/lists/${encodeURIComponent(taskListId)}/tasks?${query}`);
    tasks.push(...(page.items ?? []));
    pageToken = page.nextPageToken;
  } while (pageToken);
  return tasks;
}

function buildInboundQueries(sql, env, taskListId, googleTasks, actions, summary) {
  const queries = [];
  const byGoogleId = new Map(actions.filter((a) => a.google_task_id).map((a) => [a.google_task_id, a]));
  const byActionId = new Map(actions.map((a) => [a.id, a]));

  for (const task of googleTasks) {
    let action = byGoogleId.get(task.id);
    if (!action && !task.deleted) {
      const marker = task.notes?.match(TASK_MARKER_RE)?.[1];
      if (marker && byActionId.has(marker)) action = byActionId.get(marker);
    }

    if (task.deleted) {
      if (!action) continue;
      const meta = objectMeta(action.google_ref_metadata);
      if (meta.google_projection_disabled) continue;
      queries.push(updateRefAndReceiptQuery(sql, action, {
        ...meta,
        tasklist_id: taskListId,
        google_projection_disabled: true,
        google_deleted_at: task.updated ?? new Date().toISOString(),
        google_updated: task.updated ?? null,
      }, {
        key: `google_tasks:deleted:${task.id}:${task.updated ?? "unknown"}`,
        type: "projection_deleted_by_user",
        summary: "Google Tasks projection was deleted; canonical Neon action was preserved.",
        sourceRef: task.id,
        destinationRef: action.id,
      }));
      continue;
    }

    if (!action && env.GOOGLE_TASKS_CAPTURE !== "false") {
      queries.push(captureTaskQuery(sql, taskListId, task));
      summary.captured += 1;
      continue;
    }
    if (!action) continue;

    const meta = objectMeta(action.google_ref_metadata);
    if (meta.google_projection_disabled) continue;
    if (!task.updated || task.updated === meta.google_updated) continue;

    const neonChangedSincePush = Boolean(meta.last_pushed_action_updated_at && action.updated_at !== meta.last_pushed_action_updated_at);
    const dueDate = task.due ? task.due.slice(0, 10) : null;
    let nextStatus = action.status;
    let completedAt = action.completed_at ?? null;
    let title = action.title;
    let nextDueDate = action.due_date ?? null;
    let nextFollowUpDate = action.follow_up_date ?? null;
    let receiptType = null;
    let receiptKey = null;
    let receiptSummary = null;

    if (task.status === "completed" && action.status !== "done") {
      nextStatus = "done";
      completedAt = task.completed ?? task.updated ?? new Date().toISOString();
      receiptType = "action_completed";
      receiptKey = `google_tasks:complete:${task.id}:${task.completed ?? task.updated}`;
      receiptSummary = "Google Tasks completion updated canonical Neon action state.";
      summary.completed += 1;
    } else if (task.status === "needsAction" && action.status === "done") {
      nextStatus = "next";
      completedAt = null;
      receiptType = "action_reopened";
      receiptKey = `google_tasks:reopen:${task.id}:${task.updated}`;
      receiptSummary = "Google Tasks reopen updated canonical Neon action state to Next.";
    }

    if (!neonChangedSincePush) {
      title = task.title || "Untitled task";
      if (nextStatus === "waiting") nextFollowUpDate = dueDate;
      else nextDueDate = dueDate;
    } else {
      summary.conflicts += 1;
      receiptType = receiptType ?? "sync_conflict";
      receiptKey = receiptKey ?? `google_tasks:conflict:${task.id}:${task.updated}`;
      receiptSummary = receiptSummary ?? "Google Task and Neon action both changed since the last projection; Neon retained canonical non-status fields.";
    }

    queries.push(inboundUpdateQuery(sql, action, {
      title,
      status: nextStatus,
      completedAt,
      dueDate: nextDueDate,
      followUpDate: nextFollowUpDate,
      refMeta: {
        ...meta,
        tasklist_id: taskListId,
        google_updated: task.updated,
        last_seen_at: new Date().toISOString(),
        google_projection_disabled: false,
      },
      googleTaskId: task.id,
      googleTaskUrl: task.webViewLink ?? null,
      receipt: receiptKey ? {
        key: receiptKey,
        type: receiptType,
        summary: receiptSummary,
        sourceRef: task.id,
        destinationRef: action.id,
      } : null,
    }));
    summary.inboundUpdated += 1;
  }
  return { queries };
}

function captureTaskQuery(sql, taskListId, task) {
  const status = task.status === "completed" ? "done" : "inbox";
  const dueDate = task.due ? task.due.slice(0, 10) : null;
  const completedAt = task.status === "completed" ? (task.completed ?? task.updated ?? new Date().toISOString()) : null;
  const actionKey = `google_tasks:${taskListId}:${task.id}`;
  const refMeta = JSON.stringify({ tasklist_id: taskListId, google_updated: task.updated ?? null, captured_from_google_tasks: true });
  return sql`
    WITH action_row AS (
      INSERT INTO llm4life.actions (
        action_key, title, status, domain, priority, scheduling_rigidity,
        due_date, source_system_id, source_ref, completed_at, metadata
      ) VALUES (
        ${actionKey}, ${task.title || "Untitled task"}, ${status}, 'personal', 0, 'flexible',
        ${dueDate}::date, ${SYSTEM_GOOGLE_TASKS}, ${`${taskListId}:${task.id}`}, ${completedAt},
        ${JSON.stringify({ origin: "google_tasks", captured_at: new Date().toISOString() })}::jsonb
      )
      ON CONFLICT (action_key) DO UPDATE SET title = excluded.title
      RETURNING id
    ), ref_update AS (
      UPDATE llm4life.external_refs er
      SET external_id = ${task.id}, external_url = ${task.webViewLink ?? null},
          metadata = ${refMeta}::jsonb, updated_at = now()
      FROM action_row ar
      WHERE er.system_id = ${SYSTEM_GOOGLE_TASKS}
        AND er.internal_type = 'action' AND er.internal_id = ar.id
      RETURNING er.id
    ), ref_insert AS (
      INSERT INTO llm4life.external_refs (internal_type, internal_id, system_id, external_id, external_url, ref_kind, metadata)
      SELECT 'action', ar.id, ${SYSTEM_GOOGLE_TASKS}, ${task.id}, ${task.webViewLink ?? null}, 'projection', ${refMeta}::jsonb
      FROM action_row ar
      WHERE NOT EXISTS (SELECT 1 FROM ref_update)
      ON CONFLICT (system_id, internal_type, external_id) WHERE external_id IS NOT NULL
      DO UPDATE SET internal_id = excluded.internal_id, external_url = excluded.external_url, metadata = excluded.metadata, updated_at = now()
      RETURNING id
    ), receipt AS (
      INSERT INTO llm4life.action_receipts (
        action_key, action_type, source_system_id, destination_system_id,
        subject_type, subject_id, status, reversible, summary, source_ref, destination_ref, metadata
      )
      SELECT ${`google_tasks:capture:${task.id}`}, 'action_captured', ${SYSTEM_GOOGLE_TASKS}, ${SYSTEM_NEON},
             'action', ar.id, 'succeeded', true,
             'Captured a Google Task into canonical Neon action state.', ${task.id}, ar.id::text,
             ${JSON.stringify({ integration: JOB_KEY })}::jsonb
      FROM action_row ar
      ON CONFLICT (action_key) DO NOTHING
      RETURNING id
    )
    SELECT id::text FROM action_row
  `;
}

function inboundUpdateQuery(sql, action, change) {
  const receipt = change.receipt;
  return sql`
    WITH updated AS (
      UPDATE llm4life.actions
      SET title = ${change.title}, status = ${change.status}, completed_at = ${change.completedAt},
          due_date = ${change.dueDate}::date, follow_up_date = ${change.followUpDate}::date
      WHERE id = ${action.id}::uuid
      RETURNING id
    ), ref_update AS (
      UPDATE llm4life.external_refs
      SET external_id = ${change.googleTaskId}, external_url = ${change.googleTaskUrl},
          metadata = ${JSON.stringify(change.refMeta)}::jsonb, updated_at = now()
      WHERE system_id = ${SYSTEM_GOOGLE_TASKS}
        AND internal_type = 'action' AND internal_id = ${action.id}::uuid
      RETURNING id
    ), ref_insert AS (
      INSERT INTO llm4life.external_refs (internal_type, internal_id, system_id, external_id, external_url, ref_kind, metadata)
      SELECT 'action', ${action.id}::uuid, ${SYSTEM_GOOGLE_TASKS}, ${change.googleTaskId}, ${change.googleTaskUrl}, 'projection', ${JSON.stringify(change.refMeta)}::jsonb
      WHERE NOT EXISTS (SELECT 1 FROM ref_update)
      ON CONFLICT (system_id, internal_type, external_id) WHERE external_id IS NOT NULL
      DO UPDATE SET internal_id = excluded.internal_id, external_url = excluded.external_url,
                    metadata = excluded.metadata, updated_at = now()
      RETURNING id
    ), receipt AS (
      INSERT INTO llm4life.action_receipts (
        action_key, action_type, source_system_id, destination_system_id,
        subject_type, subject_id, status, reversible, summary, source_ref, destination_ref, metadata
      )
      SELECT ${receipt?.key ?? `google_tasks:seen:${action.id}:${change.refMeta.google_updated}`},
             ${receipt?.type ?? 'projection_seen'}, ${SYSTEM_GOOGLE_TASKS}, ${SYSTEM_NEON},
             'action', ${action.id}::uuid, 'succeeded', true,
             ${receipt?.summary ?? 'Observed Google Tasks projection update.'},
             ${receipt?.sourceRef ?? action.google_task_id}, ${receipt?.destinationRef ?? action.id},
             ${JSON.stringify({ integration: JOB_KEY, bookkeeping: !receipt })}::jsonb
      WHERE ${Boolean(receipt)}
      ON CONFLICT (action_key) DO NOTHING
      RETURNING id
    )
    SELECT id::text FROM updated
  `;
}

function updateRefAndReceiptQuery(sql, action, refMeta, receipt) {
  return sql`
    WITH ref AS (
      UPDATE llm4life.external_refs
      SET metadata = ${JSON.stringify(refMeta)}::jsonb, updated_at = now()
      WHERE id = ${action.google_ref_id}::uuid
      RETURNING id
    ), receipt AS (
      INSERT INTO llm4life.action_receipts (
        action_key, action_type, source_system_id, destination_system_id,
        subject_type, subject_id, status, reversible, summary, source_ref, destination_ref, metadata
      ) VALUES (
        ${receipt.key}, ${receipt.type}, ${SYSTEM_GOOGLE_TASKS}, ${SYSTEM_NEON},
        'action', ${action.id}::uuid, 'succeeded', true, ${receipt.summary},
        ${receipt.sourceRef ?? null}, ${receipt.destinationRef ?? null},
        ${JSON.stringify({ integration: JOB_KEY })}::jsonb
      ) ON CONFLICT (action_key) DO NOTHING RETURNING id
    ) SELECT id::text FROM ref
  `;
}

function buildOutboundMutations(env, taskListId, actions) {
  const ops = [];
  const timeZone = env.GOOGLE_TASKS_TIME_ZONE || "America/Toronto";
  for (const action of actions) {
    const meta = objectMeta(action.google_ref_metadata);
    if (action.status === "cancelled" || action.status === "archived") {
      if (action.google_task_id && !meta.google_projection_disabled) {
        ops.push({
          key: `delete:${action.id}`,
          kind: "delete",
          action,
          method: "DELETE",
          path: `/tasks/v1/lists/${encodeURIComponent(taskListId)}/tasks/${encodeURIComponent(action.google_task_id)}`,
        });
      }
      continue;
    }
    if (action.status === "done" && !action.google_task_id) continue;
    if (meta.google_projection_disabled) continue;

    const desired = desiredGoogleTask(action, timeZone);
    if (!action.google_task_id) {
      ops.push({
        key: `create:${action.id}`,
        kind: "create",
        action,
        method: "POST",
        path: `/tasks/v1/lists/${encodeURIComponent(taskListId)}/tasks`,
        body: desired,
      });
      continue;
    }

    if (meta.last_pushed_action_updated_at !== action.updated_at) {
      ops.push({
        key: `patch:${action.id}`,
        kind: "patch",
        action,
        method: "PATCH",
        path: `/tasks/v1/lists/${encodeURIComponent(taskListId)}/tasks/${encodeURIComponent(action.google_task_id)}`,
        body: desired,
      });
    }
  }
  return ops;
}

async function executeGoogleBatches(accessToken, operations) {
  const results = [];
  for (let i = 0; i < operations.length; i += GOOGLE_BATCH_SIZE) {
    const chunk = operations.slice(i, i + GOOGLE_BATCH_SIZE);
    const boundary = `llm4life_${crypto.randomUUID().replaceAll('-', '')}`;
    const body = buildMultipartBatch(boundary, chunk);
    const response = await fetch("https://tasks.googleapis.com/batch", {
      method: "POST",
      headers: {
        authorization: `Bearer ${accessToken}`,
        "content-type": `multipart/mixed; boundary=${boundary}`,
      },
      body,
    });
    const text = await response.text();
    if (!response.ok) throw new Error(`Google Tasks batch API ${response.status}: ${text.slice(0, 1500)}`);
    const parsed = parseMultipartBatchResponse(response.headers.get("content-type"), text);
    if (parsed.length !== chunk.length) {
      throw new Error(`Google Tasks batch response count mismatch: sent ${chunk.length}, received ${parsed.length}`);
    }
    for (let j = 0; j < chunk.length; j += 1) {
      const op = chunk[j];
      const part = parsed[j];
      if (part.status < 200 || part.status >= 300) {
        throw new Error(`Google Tasks batch item failed (${part.status}) for ${op.kind}:${op.action.id}: ${part.rawBody.slice(0, 1000)}`);
      }
      results.push({ ...op, response: part.jsonBody });
    }
  }
  return results;
}

function buildMultipartBatch(boundary, operations) {
  const parts = [];
  for (const op of operations) {
    const lines = [
      `--${boundary}`,
      "Content-Type: application/http",
      `Content-ID: <${op.key}>`,
      "",
      `${op.method} ${op.path} HTTP/1.1`,
    ];
    if (op.body !== undefined) lines.push("Content-Type: application/json; charset=UTF-8");
    lines.push("");
    if (op.body !== undefined) lines.push(JSON.stringify(op.body));
    parts.push(lines.join("\r\n"));
  }
  parts.push(`--${boundary}--`);
  return `${parts.join("\r\n")}\r\n`;
}

function parseMultipartBatchResponse(contentType, text) {
  const match = contentType?.match(/boundary=(?:"([^"]+)"|([^;]+))/i);
  const boundary = match?.[1] ?? match?.[2]?.trim();
  if (!boundary) throw new Error("Google Tasks batch response missing multipart boundary");
  const rawParts = text
    .split(`--${boundary}`)
    .map((part) => part.trim())
    .filter((part) => part && part !== "--");
  return rawParts.map((part) => {
    const httpIndex = part.search(/HTTP\/1\.[01] \d{3}/);
    if (httpIndex < 0) throw new Error(`Malformed Google Tasks batch response part: ${part.slice(0, 500)}`);
    const http = part.slice(httpIndex);
    const headerEnd = http.indexOf("\r\n\r\n");
    const separatorLength = headerEnd >= 0 ? 4 : 2;
    const fallbackEnd = headerEnd >= 0 ? headerEnd : http.indexOf("\n\n");
    const headerText = fallbackEnd >= 0 ? http.slice(0, fallbackEnd) : http;
    const rawBody = fallbackEnd >= 0 ? http.slice(fallbackEnd + separatorLength).trim() : "";
    const statusMatch = headerText.match(/^HTTP\/1\.[01]\s+(\d{3})/m);
    const status = Number(statusMatch?.[1] ?? 0);
    let jsonBody = null;
    if (rawBody && status !== 204) {
      try { jsonBody = JSON.parse(rawBody); } catch { jsonBody = null; }
    }
    return { status, rawBody, jsonBody };
  });
}

function buildOutboundResultQueries(sql, taskListId, results, summary) {
  const queries = [];
  for (const result of results) {
    const { action, kind, response } = result;
    const meta = objectMeta(action.google_ref_metadata);
    if (kind === "create") {
      queries.push(bindGoogleTaskQuery(sql, action, taskListId, response, {
        google_updated: response?.updated ?? null,
        last_pushed_action_updated_at: action.updated_at,
        last_synced_at: new Date().toISOString(),
        google_projection_disabled: false,
      }));
      summary.created += 1;
    } else if (kind === "patch") {
      queries.push(updateRefMetaQuery(sql, action, {
        ...meta,
        tasklist_id: taskListId,
        google_updated: response?.updated ?? meta.google_updated ?? null,
        last_pushed_action_updated_at: action.updated_at,
        last_synced_at: new Date().toISOString(),
        google_projection_disabled: false,
      }));
      summary.patched += 1;
    } else if (kind === "delete") {
      queries.push(updateRefAndReceiptQuery(sql, action, {
        ...meta,
        tasklist_id: taskListId,
        google_projection_disabled: true,
        deleted_from_projection_at: new Date().toISOString(),
      }, {
        key: `neon:projection-delete:${action.id}:${action.updated_at}`,
        type: "projection_deleted",
        summary: "Removed a cancelled/archived action from the Google Tasks projection.",
        sourceRef: action.id,
        destinationRef: action.google_task_id,
      }));
      summary.projectionDeleted += 1;
    }
  }
  return queries;
}

function bindGoogleTaskQuery(sql, action, taskListId, task, metadata) {
  const finalMetadata = JSON.stringify({ tasklist_id: taskListId, ...metadata });
  return sql`
    WITH updated AS (
      UPDATE llm4life.external_refs
      SET external_id = ${task.id}, external_url = ${task.webViewLink ?? null},
          metadata = ${finalMetadata}::jsonb, updated_at = now()
      WHERE system_id = ${SYSTEM_GOOGLE_TASKS}
        AND internal_type = 'action' AND internal_id = ${action.id}::uuid
      RETURNING id
    )
    INSERT INTO llm4life.external_refs (internal_type, internal_id, system_id, external_id, external_url, ref_kind, metadata)
    SELECT 'action', ${action.id}::uuid, ${SYSTEM_GOOGLE_TASKS}, ${task.id}, ${task.webViewLink ?? null}, 'projection', ${finalMetadata}::jsonb
    WHERE NOT EXISTS (SELECT 1 FROM updated)
    ON CONFLICT (system_id, internal_type, external_id) WHERE external_id IS NOT NULL
    DO UPDATE SET internal_id = excluded.internal_id, external_url = excluded.external_url,
                  metadata = excluded.metadata, updated_at = now()
  `;
}

function updateRefMetaQuery(sql, action, metadata) {
  return sql`
    UPDATE llm4life.external_refs
    SET metadata = ${JSON.stringify(metadata)}::jsonb, updated_at = now()
    WHERE id = ${action.google_ref_id}::uuid
  `;
}

async function finishSuccess(sql, runId, taskList, summary) {
  await sql.transaction([
    sql`
      INSERT INTO llm4life.sync_checkpoints (integration_key, cursor_value, checkpoint_at, metadata)
      VALUES ('google_tasks_tasklist', ${taskList.id}, now(), ${JSON.stringify({ title: taskList.title ?? "LLM4LIFE" })}::jsonb)
      ON CONFLICT (integration_key) DO UPDATE SET cursor_value = excluded.cursor_value,
        checkpoint_at = excluded.checkpoint_at, metadata = excluded.metadata, updated_at = now()
    `,
    sql`
      INSERT INTO llm4life.sync_checkpoints (integration_key, checkpoint_at, metadata)
      VALUES ('google_tasks_projection', now(), ${JSON.stringify({ tasklist_id: taskList.id, summary, worker_version: "0.2.0" })}::jsonb)
      ON CONFLICT (integration_key) DO UPDATE SET checkpoint_at = excluded.checkpoint_at,
        metadata = excluded.metadata, updated_at = now()
    `,
    sql`
      UPDATE llm4life.job_runs
      SET status = 'succeeded', finished_at = now(), output_summary = ${JSON.stringify(summary)},
          error_code = null, error_summary = null,
          metadata = ${JSON.stringify({ summary, worker_version: "0.2.0" })}::jsonb
      WHERE id = ${runId}::uuid
    `,
  ]);
}

async function finishFailure(sql, runId, summary, error) {
  try {
    await sql`
      UPDATE llm4life.job_runs
      SET status = 'failed', finished_at = now(), output_summary = ${JSON.stringify(summary)},
          error_summary = ${safeError(error)}, metadata = ${JSON.stringify({ summary, worker_version: "0.2.0" })}::jsonb
      WHERE id = ${runId}::uuid
    `;
  } catch (loggingError) {
    console.error("Could not persist failed run telemetry", loggingError);
  }
}

function desiredGoogleTask(action, timeZone) {
  const dueDay = projectedDueDay(action, timeZone);
  const lines = [`[LLM4LIFE:ACTION_ID=${action.id}]`, `Canonical status: ${action.status}`];
  if (action.context) lines.push(`Context: ${action.context}`);
  if (action.scheduling_rigidity) lines.push(`Scheduling: ${action.scheduling_rigidity}`);
  if (action.scheduled_for) lines.push("Execution time is managed in Google Calendar; Google Tasks does not store task time-of-day via API.");
  if (action.status === "waiting") lines.push("Task date represents the next follow-up/attention day while this action is waiting.");
  lines.push("Canonical state: LLM4LIFE / Neon.");
  return {
    title: action.title,
    notes: lines.join("\n"),
    status: action.status === "done" ? "completed" : "needsAction",
    ...(dueDay ? { due: `${dueDay}T00:00:00.000Z` } : { due: null }),
  };
}

function projectedDueDay(action, timeZone) {
  if (action.status === "waiting") {
    if (action.follow_up_date) return action.follow_up_date.slice(0, 10);
    if (action.follow_up_at) return localDate(action.follow_up_at, timeZone);
    return null;
  }
  if (action.due_date) return action.due_date.slice(0, 10);
  if (action.due_at) return localDate(action.due_at, timeZone);
  return null;
}

function localDate(value, timeZone) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date(value));
  const map = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${map.year}-${map.month}-${map.day}`;
}

function objectMeta(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function safeError(error) {
  if (error instanceof Error) return error.message.slice(0, 1000);
  return String(error).slice(0, 1000);
}

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}
