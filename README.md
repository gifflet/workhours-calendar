# Workhours Calendar

Track worked hours by **client → project → task**. At the end of the month,
see how many hours went into each project or client, how long a task took, and
what was worked on any given day — via REST API, Swagger UI, or by just asking
Claude (MCP server + Claude Code plugin included).

## Install

The only requirement is [Docker](https://docs.docker.com/get-docker/).

**Linux / macOS / Raspberry Pi:**

```bash
curl -fsSL https://raw.githubusercontent.com/gifflet/workhours-calendar/main/install.sh | sh
```

**Windows (PowerShell):**

```powershell
irm https://raw.githubusercontent.com/gifflet/workhours-calendar/main/install.ps1 | iex
```

The script pulls the prebuilt multi-arch images (`amd64`, `arm64`, `arm/v7`),
starts MongoDB and the API, and waits until everything is healthy:

- **API**: http://localhost:8001 — **Swagger UI**: http://localhost:8001/docs
- Data persists in the `workhours_mongo` volume; containers restart with Docker on boot
- Re-run the script anytime to update (data is kept)
- `WORKHOURS_PORT` changes the API port; `MONGO_URL` points to an external
  MongoDB (required on 32-bit ARM). Raspberry Pi 3/4 automatically get
  `mongo:4.4`, since MongoDB 5+ needs ARMv8.2-A.

Uninstall: `docker rm -f workhours-api workhours-mongo && docker volume rm workhours_mongo`

## Use with Claude Code

Install the plugin once (user scope — available in every project):

```shell
/plugin marketplace add gifflet/workhours-calendar
/plugin install workhours@workhours-calendar
```

Then just ask in natural language:

> "Log 2.5 hours today on the CI pipeline task of ACME's ERP project"
>
> "How many hours did I work for ACME in August?"
>
> "Which tasks did I work on yesterday?"

The plugin bundles the MCP server (prebuilt Docker image — nothing to clone or
build) and a skill that teaches the model the workflows: resolve names to ids,
create missing clients/projects/tasks on demand, and answer report questions
with a single tool call. Source: [`plugins/workhours`](plugins/workhours).

## API

Interactive docs at [`/docs`](http://localhost:8001/docs) (Swagger UI) and `/redoc`.

| Resource | Endpoints |
|---|---|
| Clients | `POST/GET /clients`, `GET/PATCH/DELETE /clients/{id}` |
| Projects | `POST/GET /projects` (filter by `client_id`), `GET/PATCH/DELETE /projects/{id}` |
| Tasks | `POST/GET /tasks` (filter by `project_id`, `status`), `GET/PATCH/DELETE /tasks/{id}` |
| Time entries | `POST/GET /entries` (filter by dates, task, project, client), `GET/PATCH/DELETE /entries/{id}` |
| Reports | `GET /reports/monthly`, `GET /reports/daily`, `GET /reports/task/{task_id}` |
| Health | `GET /health` (includes MongoDB status) |

- Dates use `YYYY-MM-DD`; hours are decimal (`1.5` = 1h30).
- A time entry needs a `task_id` **or** a `project_id`; client and project are
  denormalized into the entry automatically for fast reporting.
- Deletes are guarded: a client/project/task with children or time entries
  can't be deleted (HTTP 409).

```bash
# Hours in August 2026, broken down by client, project, task and day
curl "http://localhost:8001/reports/monthly?year=2026&month=8"

# What was worked on a specific day
curl "http://localhost:8001/reports/daily?date=2026-08-12"

# Total effort spent on a task
curl "http://localhost:8001/reports/task/<task_id>"
```

## Other MCP clients

The MCP server exposes 14 tools over stdio (`create_client`, `log_hours`,
`monthly_report`, `daily_report`, `task_report`, ...). To register it outside
the Claude Code plugin, run the published image with `-i`:

```bash
claude mcp add workhours \
  -- docker run -i --rm \
     --add-host host.docker.internal:host-gateway \
     -e WORKHOURS_API_URL=http://host.docker.internal:8001 \
     ghcr.io/gifflet/workhours-calendar-mcp:latest
```

The `WORKHOURS_API_URL` environment variable points the server at the API.

## Development

```bash
# Everything in containers (builds locally)
docker compose up --build

# Or API on the host (needs MongoDB on localhost:27017 — uncomment the
# ports mapping in docker-compose.yaml to publish the mongodb service)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8001
```

The API reads `MONGO_URL` (default `mongodb://localhost:27017`) and `MONGO_DB`
(default `workhours`). The repo ships a project-scoped `.mcp.json` that runs
the MCP server from the local venv. Test it standalone with:

```bash
npx @modelcontextprotocol/inspector .venv/bin/python mcp_server/server.py
```

CI (`.github/workflows/docker-build.yml`) builds and publishes
`ghcr.io/gifflet/workhours-calendar-api` and `...-mcp` for `linux/amd64`,
`linux/arm64` and `linux/arm/v7` on every push to `main` and on `v*` tags;
pull requests build without publishing.

```
app/                 # FastAPI app (routers, schemas, Mongo access)
mcp_server/          # MCP stdio server calling the API
plugins/workhours/   # Claude Code plugin (skill + MCP via Docker image)
.claude-plugin/      # Plugin marketplace manifest
install.sh install.ps1              # One-command installers
Dockerfile Dockerfile.mcp           # API and MCP server images
docker-compose.yaml
.github/workflows/docker-build.yml  # Multi-arch build + publish to GHCR
```
