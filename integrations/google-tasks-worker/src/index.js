import { neon } from "@neondatabase/serverless";

const SYSTEM_GOOGLE_TASKS = "google_tasks";
const SYSTEM_NEON = "neon";
const JOB_KEY = "google-tasks-sync";
const TASK_MARKER_RE = /\[LLM4LIFE:ACTION_ID=([0-9a-f-]{36})\]/i;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/health") {
      return json({ ok: true, service: "llm4life-google-tasks-sync" });
    }

    if (request.method === "POST" && url.pathname === "/sync") {
      if (!env.SYNC_ADMIN_TOKEN) {
        return json({ ok: false, error: "manual_sync_disabled" }, 503);
      }
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
    ctx.waitUntil(
      sync(env, `cron:${controller.scheduledTime}`).catch((error) => {
        console.error("Google Tasks sync failed", error);
      }),
    );
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
  };

  try {
    const accessToken = await getAccessToken(env);
    const taskList = await ensureTaskList(sql, env, accessToken);
    const googleTasks = await listGoogleTasks(accessToken, taskList.id);

    await ingestGoogleChanges(sql, env, taskList.id, googleTasks, summary);

    // Re-read after inbound writes so projection uses canonical post-ingest state.
    const actions = await loadActions(sql);
    const googleTasksAfterIngest = await listGoogleTasks(accessToken, taskList.id);
    const googleById = new Map(googleTasksAfterIngest.map((task) => [task.id, task]));

    for (const action of actions) {
      await projectAction(sql, env, accessToken, taskList.id, action, googleById, summary);
    }

    await sql`
      INSERT INTO llm4life.sync_checkpoints (integration_key, checkpoint_at, metadata)
      VALUES (
        'google_tasks_projection',
        now(),
        ${JSON.stringify({ tasklist_id: taskList.id, summary })}::jsonb
      )
      ON CONFLICT (integration_key) DO UPDATE SET
        checkpoint_at = excluded.checkpoint_at,
        metadata = excluded.metadata,
        updated_at = now()
    `;

    await finishRun(sql, run.id, "succeeded", summary, null);
    return summary;
  } catch (error) {
    await finishRun(sql, run.id, "failed", summary, safeError(error));
    throw error;
  }
}

function requireSecrets(env) {
  for (const name of ["DATABASE_URL", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"]) {
    if (!env[name]) throw new Error(`Missing required Worker secret: ${name}`);
  }
}

async function ensureRuntimeRows(sql) {
  await sql`
    INSERT INTO llm4life.systems (id, kind, canonical_role, lifecycle_status)
    VALUES
      (${SYSTEM_GOOGLE_TASKS}, 'external_client', 'personal_action_projection', 'active'),
      (${SYSTEM_NEON}, 'database', 'llm4life_machine_state', 'active')
    ON CONFLICT (id) DO UPDATE SET
      kind = excluded.kind,
      canonical_role = excluded.canonical_role,
      lifecycle_status = excluded.lifecycle_status
  `;

  await sql`
    INSERT INTO llm4life.jobs (
      job_key, name, domain, handler, enabled, trigger_kind,
      schedule_expression, timezone, config
    )
    VALUES (
      ${JOB_KEY}, 'Google Tasks Projection Sync', 'personal_actions',
      'cloudflare_worker:llm4life-google-tasks-sync', true, 'schedule',
      '*/15 * * * *', 'UTC', ${JSON.stringify({ canonical: "neon", client: "google_tasks" })}::jsonb
    )
    ON CONFLICT (job_key) DO UPDATE SET
      name = excluded.name,
      handler = excluded.handler,
      enabled = excluded.enabled,
      schedule_expression = excluded.schedule_expression,
      config = excluded.config
  `;
}

async function beginRun(sql, runKey) {
  const jobs = await sql`SELECT id FROM llm4life.jobs WHERE job_key = ${JOB_KEY}`;
  const jobId = jobs[0]?.id;
  if (!jobId) throw new Error("google-tasks-sync job registry row is missing");

  const prior = await sql`
    SELECT id, status
    FROM llm4life.job_runs
    WHERE job_id = ${jobId} AND run_key = ${runKey}
  `;
  if (prior[0]?.status === "succeeded") return { id: prior[0].id, skipped: true };

  const rows = await sql`
    INSERT INTO llm4life.job_runs (job_id, run_key, status, triggered_at, started_at, metadata)
    VALUES (${jobId}, ${runKey}, 'running', now(), now(), '{}'::jsonb)
    ON CONFLICT (job_id, run_key) DO UPDATE SET
      status = 'running',
      started_at = now(),
      finished_at = null,
      error_code = null,
      error_summary = null
    RETURNING id
  `;
  return { id: rows[0].id, skipped: false };
}

async function finishRun(sql, runId, status, summary, errorSummary) {
  await sql`
    UPDATE llm4life.job_runs
    SET status = ${status},
        finished_at = now(),
        output_summary = ${JSON.stringify(summary)},
        error_summary = ${errorSummary},
        metadata = ${JSON.stringify({ summary })}::jsonb
    WHERE id = ${runId}
  `;
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
  if (!response.ok) {
    throw new Error(`Google Tasks API ${response.status}: ${text.slice(0, 1000)}`);
  }
  return body;
}

async function ensureTaskList(sql, env, accessToken) {
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
  if (matches.length > 1) {
    throw new Error(`More than one Google Tasks list is named ${title}; refusing ambiguous projection.`);
  }

  const taskList = matches[0] ?? await googleRequest(accessToken, "/tasks/v1/users/@me/lists", {
    method: "POST",
    body: JSON.stringify({ title }),
  });

  await sql`
    INSERT INTO llm4life.sync_checkpoints (integration_key, cursor_value, checkpoint_at, metadata)
    VALUES (
      'google_tasks_tasklist', ${taskList.id}, now(),
      ${JSON.stringify({ title })}::jsonb
    )
    ON CONFLICT (integration_key) DO UPDATE SET
      cursor_value = excluded.cursor_value,
      checkpoint_at = excluded.checkpoint_at,
      metadata = excluded.metadata,
      updated_at = now()
  `;

  return taskList;
}

async function listGoogleTasks(accessToken, taskListId) {
  const tasks = [];
  let pageToken;
  do {
    const query = new URLSearchParams({
      maxResults: "100",
      showCompleted: "true",
      showDeleted: "true",
      showHidden: "true",
    });
    if (pageToken) query.set("pageToken", pageToken);
    const page = await googleRequest(
      accessToken,
      `/tasks/v1/lists/${encodeURIComponent(taskListId)}/tasks?${query}`,
    );
    tasks.push(...(page.items ?? []));
    pageToken = page.nextPageToken;
  } while (pageToken);
  return tasks;
}

async function loadActions(sql) {
  return await sql`
    SELECT
      a.id::text,
      a.action_key,
      a.title,
      a.status,
      a.priority,
      a.scheduling_rigidity,
      a.context,
      a.location_label,
      a.due_date::text,
      a.due_at::text,
      a.follow_up_date::text,
      a.follow_up_at::text,
      a.scheduled_for::text,
      a.planned_duration_min,
      a.completed_at::text,
      a.updated_at::text,
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
    WHERE a.status <> 'archived'
    ORDER BY a.created_at ASC
  `;
}

async function ingestGoogleChanges(sql, env, taskListId, googleTasks, summary) {
  const actions = await loadActions(sql);
  const byGoogleId = new Map(actions.filter((a) => a.google_task_id).map((a) => [a.google_task_id, a]));
  const byActionId = new Map(actions.map((a) => [a.id, a]));

  for (const task of googleTasks) {
    let action = byGoogleId.get(task.id);

    if (!action && !task.deleted) {
      const marker = task.notes?.match(TASK_MARKER_RE)?.[1];
      if (marker && byActionId.has(marker)) {
        action = byActionId.get(marker);
        await bindGoogleTask(sql, action.id, taskListId, task, {
          google_updated: task.updated ?? null,
          last_pushed_action_updated_at: null,
          rebound_from_marker: true,
        });
        byGoogleId.set(task.id, action);
        continue;
      }
    }

    if (task.deleted) {
      if (action) {
        const meta = objectMeta(action.google_ref_metadata);
        if (!meta.google_projection_disabled) {
          await updateGoogleRefMeta(sql, action, {
            ...meta,
            google_projection_disabled: true,
            google_deleted_at: task.updated ?? new Date().toISOString(),
            google_updated: task.updated ?? null,
          });
          await receipt(sql, {
            key: `google_tasks:deleted:${task.id}:${task.updated ?? "unknown"}`,
            type: "projection_deleted_by_user",
            source: SYSTEM_GOOGLE_TASKS,
            destination: SYSTEM_NEON,
            actionId: action.id,
            summary: "Google Tasks projection was deleted; canonical Neon action was preserved.",
            sourceRef: task.id,
            destinationRef: action.id,
          });
        }
      }
      continue;
    }

    if (!action && env.GOOGLE_TASKS_CAPTURE !== "false") {
      const actionId = await captureGoogleTask(sql, taskListId, task);
      await bindGoogleTask(sql, actionId, taskListId, task, {
        google_updated: task.updated ?? null,
        captured_from_google_tasks: true,
      });
      await receipt(sql, {
        key: `google_tasks:capture:${task.id}`,
        type: "action_captured",
        source: SYSTEM_GOOGLE_TASKS,
        destination: SYSTEM_NEON,
        actionId,
        summary: "Captured a Google Task into canonical Neon action state.",
        sourceRef: task.id,
        destinationRef: actionId,
      });
      summary.captured += 1;
      continue;
    }

    if (!action) continue;
    const meta = objectMeta(action.google_ref_metadata);
    if (meta.google_projection_disabled) continue;
    if (!task.updated || task.updated === meta.google_updated) continue;

    const neonChangedSincePush = Boolean(
      meta.last_pushed_action_updated_at && action.updated_at !== meta.last_pushed_action_updated_at,
    );

    let stateChanged = false;
    if (task.status === "completed" && action.status !== "done") {
      await sql`
        UPDATE llm4life.actions
        SET status = 'done', completed_at = ${task.completed ?? task.updated ?? new Date().toISOString()}
        WHERE id = ${action.id}
      `;
      await receipt(sql, {
        key: `google_tasks:complete:${task.id}:${task.completed ?? task.updated}`,
        type: "action_completed",
        source: SYSTEM_GOOGLE_TASKS,
        destination: SYSTEM_NEON,
        actionId: action.id,
        summary: "Google Tasks completion updated canonical Neon action state.",
        sourceRef: task.id,
        destinationRef: action.id,
      });
      stateChanged = true;
      summary.completed += 1;
    } else if (task.status === "needsAction" && action.status === "done") {
      await sql`
        UPDATE llm4life.actions
        SET status = 'next', completed_at = null
        WHERE id = ${action.id}
      `;
      await receipt(sql, {
        key: `google_tasks:reopen:${task.id}:${task.updated}`,
        type: "action_reopened",
        source: SYSTEM_GOOGLE_TASKS,
        destination: SYSTEM_NEON,
        actionId: action.id,
        summary: "Google Tasks reopen updated canonical Neon action state to Next.",
        sourceRef: task.id,
        destinationRef: action.id,
      });
      stateChanged = true;
    }

    if (!neonChangedSincePush) {
      const dueDate = task.due ? task.due.slice(0, 10) : null;
      if (task.title !== action.title) {
        await sql`UPDATE llm4life.actions SET title = ${task.title || "Untitled task"} WHERE id = ${action.id}`;
        stateChanged = true;
      }

      if (action.status === "waiting") {
        if ((action.follow_up_date ?? null) !== dueDate) {
          await sql`UPDATE llm4life.actions SET follow_up_date = ${dueDate}::date WHERE id = ${action.id}`;
          stateChanged = true;
        }
      } else if ((action.due_date ?? null) !== dueDate) {
        await sql`UPDATE llm4life.actions SET due_date = ${dueDate}::date WHERE id = ${action.id}`;
        stateChanged = true;
      }
    } else {
      summary.conflicts += 1;
      await receipt(sql, {
        key: `google_tasks:conflict:${task.id}:${task.updated}`,
        type: "sync_conflict",
        source: SYSTEM_GOOGLE_TASKS,
        destination: SYSTEM_NEON,
        actionId: action.id,
        summary: "Google Task and Neon action both changed since the last projection; Neon retained canonical non-status fields.",
        sourceRef: task.id,
        destinationRef: action.id,
      });
    }

    await updateGoogleRefMeta(sql, action, {
      ...meta,
      google_updated: task.updated,
      last_seen_at: new Date().toISOString(),
    });
    if (stateChanged) summary.inboundUpdated += 1;
  }
}

async function captureGoogleTask(sql, taskListId, task) {
  const status = task.status === "completed" ? "done" : "inbox";
  const dueDate = task.due ? task.due.slice(0, 10) : null;
  const completedAt = task.status === "completed" ? (task.completed ?? task.updated ?? new Date().toISOString()) : null;
  const actionKey = `google_tasks:${taskListId}:${task.id}`;

  const rows = await sql`
    INSERT INTO llm4life.actions (
      action_key, title, status, domain, priority, scheduling_rigidity,
      due_date, source_system_id, source_ref, completed_at, metadata
    )
    VALUES (
      ${actionKey}, ${task.title || "Untitled task"}, ${status}, 'personal', 0, 'flexible',
      ${dueDate}::date, ${SYSTEM_GOOGLE_TASKS}, ${`${taskListId}:${task.id}`}, ${completedAt},
      ${JSON.stringify({ origin: "google_tasks", captured_at: new Date().toISOString() })}::jsonb
    )
    ON CONFLICT (action_key) DO UPDATE SET
      title = excluded.title
    RETURNING id::text
  `;
  return rows[0].id;
}

async function projectAction(sql, env, accessToken, taskListId, action, googleById, summary) {
  const meta = objectMeta(action.google_ref_metadata);

  if (action.status === "cancelled" || action.status === "archived") {
    if (action.google_task_id && !meta.google_projection_disabled) {
      const current = googleById.get(action.google_task_id);
      if (current && !current.deleted) {
        await googleRequest(
          accessToken,
          `/tasks/v1/lists/${encodeURIComponent(taskListId)}/tasks/${encodeURIComponent(action.google_task_id)}`,
          { method: "DELETE" },
        );
        await updateGoogleRefMeta(sql, action, {
          ...meta,
          google_projection_disabled: true,
          deleted_from_projection_at: new Date().toISOString(),
        });
        await receipt(sql, {
          key: `neon:projection-delete:${action.id}:${action.updated_at}`,
          type: "projection_deleted",
          source: SYSTEM_NEON,
          destination: SYSTEM_GOOGLE_TASKS,
          actionId: action.id,
          summary: "Removed a cancelled/archived action from the Google Tasks projection.",
          sourceRef: action.id,
          destinationRef: action.google_task_id,
        });
        summary.projectionDeleted += 1;
      }
    }
    return;
  }

  // Do not create historical completed tasks that never existed in the projection.
  if (action.status === "done" && !action.google_task_id) return;
  if (meta.google_projection_disabled) return;

  const desired = desiredGoogleTask(action, env.GOOGLE_TASKS_TIME_ZONE || "America/Toronto");

  if (!action.google_task_id) {
    const created = await googleRequest(
      accessToken,
      `/tasks/v1/lists/${encodeURIComponent(taskListId)}/tasks`,
      { method: "POST", body: JSON.stringify(desired) },
    );
    await bindGoogleTask(sql, action.id, taskListId, created, {
      google_updated: created.updated ?? null,
      last_pushed_action_updated_at: action.updated_at,
      last_synced_at: new Date().toISOString(),
    });
    summary.created += 1;
    return;
  }

  const current = googleById.get(action.google_task_id);
  if (!current || current.deleted) {
    await updateGoogleRefMeta(sql, action, {
      ...meta,
      google_projection_disabled: true,
      google_deleted_at: current?.updated ?? new Date().toISOString(),
    });
    return;
  }

  if (!googleTaskDiffers(current, desired)) {
    if (meta.google_updated !== current.updated || meta.last_pushed_action_updated_at !== action.updated_at) {
      await updateGoogleRefMeta(sql, action, {
        ...meta,
        google_updated: current.updated ?? null,
        last_pushed_action_updated_at: action.updated_at,
        last_synced_at: new Date().toISOString(),
      });
    }
    return;
  }

  const patched = await googleRequest(
    accessToken,
    `/tasks/v1/lists/${encodeURIComponent(taskListId)}/tasks/${encodeURIComponent(action.google_task_id)}`,
    { method: "PATCH", body: JSON.stringify(desired) },
  );
  await updateGoogleRefMeta(sql, action, {
    ...meta,
    google_updated: patched.updated ?? null,
    last_pushed_action_updated_at: action.updated_at,
    last_synced_at: new Date().toISOString(),
  });
  summary.patched += 1;
}

function desiredGoogleTask(action, timeZone) {
  const dueDay = projectedDueDay(action, timeZone);
  const lines = [
    `[LLM4LIFE:ACTION_ID=${action.id}]`,
    `Canonical status: ${action.status}`,
  ];
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

function googleTaskDiffers(current, desired) {
  const currentDue = current.due ? current.due.slice(0, 10) : null;
  const desiredDue = desired.due ? desired.due.slice(0, 10) : null;
  return current.title !== desired.title
    || (current.notes ?? "") !== (desired.notes ?? "")
    || current.status !== desired.status
    || currentDue !== desiredDue;
}

async function bindGoogleTask(sql, actionId, taskListId, task, metadata) {
  const existing = await sql`
    SELECT id::text
    FROM llm4life.external_refs
    WHERE system_id = ${SYSTEM_GOOGLE_TASKS}
      AND internal_type = 'action'
      AND internal_id = ${actionId}::uuid
    LIMIT 1
  `;

  const finalMetadata = {
    tasklist_id: taskListId,
    ...metadata,
  };

  if (existing.length) {
    await sql`
      UPDATE llm4life.external_refs
      SET external_id = ${task.id},
          external_url = ${task.webViewLink ?? null},
          metadata = ${JSON.stringify(finalMetadata)}::jsonb
      WHERE id = ${existing[0].id}::uuid
    `;
    return;
  }

  await sql`
    INSERT INTO llm4life.external_refs (
      internal_type, internal_id, system_id, external_id, external_url, ref_kind, metadata
    )
    VALUES (
      'action', ${actionId}::uuid, ${SYSTEM_GOOGLE_TASKS}, ${task.id},
      ${task.webViewLink ?? null}, 'projection', ${JSON.stringify(finalMetadata)}::jsonb
    )
  `;
}

async function updateGoogleRefMeta(sql, action, metadata) {
  if (!action.google_ref_id) return;
  await sql`
    UPDATE llm4life.external_refs
    SET metadata = ${JSON.stringify(metadata)}::jsonb,
        updated_at = now()
    WHERE id = ${action.google_ref_id}::uuid
  `;
}

async function receipt(sql, { key, type, source, destination, actionId, summary, sourceRef, destinationRef }) {
  await sql`
    INSERT INTO llm4life.action_receipts (
      action_key, action_type, source_system_id, destination_system_id,
      subject_type, subject_id, status, reversible, summary, source_ref, destination_ref, metadata
    )
    VALUES (
      ${key}, ${type}, ${source}, ${destination},
      'action', ${actionId}::uuid, 'succeeded', true, ${summary}, ${sourceRef ?? null}, ${destinationRef ?? null},
      ${JSON.stringify({ integration: JOB_KEY })}::jsonb
    )
    ON CONFLICT (action_key) DO NOTHING
  `;
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
