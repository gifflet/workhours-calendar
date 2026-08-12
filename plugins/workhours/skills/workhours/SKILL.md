---
name: workhours
description: Guides the model on using the "workhours" MCP server to track worked hours by client, project and task. Use when the user asks to log hours, check hours spent on a project/client, get a monthly report, see how long a task took, or which tasks were worked on a given day.
---

# Workhours Calendar — MCP usage guide

The `workhours` MCP server wraps a REST API (FastAPI + MongoDB) that tracks worked
hours. All ids are opaque strings; all dates use `YYYY-MM-DD`.

## Prerequisites

The MCP server (a Docker container started automatically by this plugin) talks to
the Workhours API at `http://localhost:8001`. If tool calls return a connection
error, the API isn't running — offer the user this one-time setup (prebuilt
images, nothing to clone or build):

```bash
docker network create workhours 2>/dev/null || true
docker run -d --name workhours-mongo --network workhours \
  -v workhours_mongo:/data/db mongo:7
docker run -d --name workhours-api --network workhours -p 8001:8000 \
  -e MONGO_URL=mongodb://workhours-mongo:27017 \
  ghcr.io/gifflet/workhours-calendar-api:latest
```

On later sessions, `docker start workhours-mongo workhours-api` brings it back.

## Data model

```
Client (name)
  └── Project (name, client_id)
        └── Task (title, project_id, status: open|done)
              └── Time entry (date, hours, notes)
```

A time entry always belongs to a project and client (denormalized automatically).
Attaching it to a task is optional but preferred — task-level reports only see
entries logged with a `task_id`.

## Golden rules

1. **Never invent ids.** Resolve names to ids first with `list_clients`,
   `list_projects` or `list_tasks`. Match names case-insensitively.
2. **Create missing hierarchy on demand.** If the user logs hours against a
   client/project/task that doesn't exist yet, create it (client → project →
   task, in that order) and then log the hours. Tell the user what was created.
3. **Prefer `task_id` in `log_hours`.** Project and client are derived from the
   task. Only fall back to `project_id` when the work isn't tied to a task.
4. **Dates:** convert natural language ("today", "yesterday", "last Friday")
   to `YYYY-MM-DD` before calling tools. Hours are decimal (1h30 → 1.5).
5. **Errors:** tool results with an `"error"` key are API failures, not tool
   bugs. If the message says the API is unreachable, walk the user through the
   Prerequisites section above instead of retrying.

## Which tool for which question

| User asks | Tool |
|---|---|
| "log 3h on task X today" | `log_hours` (resolve task first) |
| "how many hours on project/client X this month?" | `monthly_report` with `project_id`/`client_id` filter |
| "monthly summary / where did my time go?" | `monthly_report` |
| "how long did task X take?" | `task_report` |
| "what did I work on <day>?" | `daily_report` |
| "list/fix/remove an entry" | `list_entries`, `update_entry`, `delete_entry` |
| "mark task as done" | `update_task_status` |

## Typical flow — "Log 2.5 hours yesterday on the CI pipeline task for ACME's ERP project"

1. `list_clients` → find "ACME" → `client_id`
2. `list_projects(client_id=...)` → find "ERP" → `project_id`
3. `list_tasks(project_id=...)` → find "CI pipeline" → `task_id`
4. `log_hours(date="<yesterday>", hours=2.5, task_id=...)`
5. Confirm to the user: client/project/task names, date and hours logged.

## Reporting tips

- `monthly_report` returns `total_hours` plus `by_client`, `by_project`,
  `by_task` and `by_day` breakdowns — usually one call answers the question.
- When presenting reports, show names (already included), not ids.
- For a custom date range, use `list_entries(date_from=..., date_to=...)` and
  aggregate the `hours` fields yourself.
