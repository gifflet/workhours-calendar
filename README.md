# Workhours Calendar

A small REST API to track worked hours by **client → project → task**, backed by
MongoDB. At the end of the month you can see how many hours went into a project
or client, how long a task took, and which tasks were worked on a given day.

Ships with:

- **FastAPI** app with interactive Swagger docs
- **MongoDB** persistence (local or via Docker)
- **MCP server** so AI assistants (Claude Code) can operate the API
- **Claude Code skill** teaching the model how to use the MCP tools

## Quick start (Docker)

```bash
docker compose up --build
```

- API: http://localhost:8001
- Swagger UI: http://localhost:8001/docs
- MongoDB: internal to the compose network only (volume-persisted); the API
  reaches it by service name. To access it from the host, uncomment the
  `ports` mapping in `docker-compose.yaml`.

## Quick start (prebuilt images — no build required)

Every push to `main` publishes multi-arch images to GitHub Container Registry
(`linux/amd64`, `linux/arm64`, `linux/arm/v7` — Intel/AMD Linux, Apple Silicon
and Raspberry Pi 3+ are all covered):

```bash
docker run -d --name workhours-api -p 8001:8000 \
  -e MONGO_URL=mongodb://host.docker.internal:27017 \
  --add-host host.docker.internal:host-gateway \
  ghcr.io/gifflet/workhours-calendar-api:latest
```

Or with compose, pointing `api` at the published image instead of `build`:

```yaml
services:
  mongodb:
    image: mongo:7
    volumes: [mongo_data:/data/db]
  api:
    image: ghcr.io/gifflet/workhours-calendar-api:latest
    ports: ["8001:8000"]
    environment:
      MONGO_URL: mongodb://mongodb:27017
    depends_on: [mongodb]
volumes:
  mongo_data:
```

> **Raspberry Pi 3/4 note:** MongoDB 5+ requires the ARMv8.2-A
> microarchitecture, which the Pi 3/4 CPUs lack, and there is no official
> 32-bit image. On a Pi, run the API image locally but point `MONGO_URL` at a
> MongoDB hosted elsewhere (or use `mongo:4.4` on a 64-bit Pi OS).

## Quick start (local Python)

Requires Python 3.11+ and a MongoDB instance on `localhost:27017` — e.g.
`docker compose up mongodb` after uncommenting the `ports` mapping in
`docker-compose.yaml` (the API running on the host needs the published port).

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8001
```

Environment variables:

| Variable | Default | Description |
|---|---|---|
| `MONGO_URL` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGO_DB` | `workhours` | Database name |

## API overview

Full interactive documentation lives at `/docs` (Swagger UI) and `/redoc`.

| Resource | Endpoints |
|---|---|
| Clients | `POST/GET /clients`, `GET/PATCH/DELETE /clients/{id}` |
| Projects | `POST/GET /projects` (filter by `client_id`), `GET/PATCH/DELETE /projects/{id}` |
| Tasks | `POST/GET /tasks` (filter by `project_id`, `status`), `GET/PATCH/DELETE /tasks/{id}` |
| Time entries | `POST/GET /entries` (filter by dates, task, project, client), `GET/PATCH/DELETE /entries/{id}` |
| Reports | `GET /reports/monthly`, `GET /reports/daily`, `GET /reports/task/{task_id}` |
| Health | `GET /health` (includes MongoDB status) |

Notes:

- Dates use `YYYY-MM-DD`; hours are decimal (`1.5` = 1h30).
- A time entry needs a `task_id` **or** a `project_id`; client and project are
  denormalized into the entry automatically for fast reporting.
- Deletes are guarded: you cannot delete a client/project/task that still has
  children or time entries (HTTP 409).

### Report examples

```bash
# Hours in August 2026, broken down by client, project, task and day
curl "http://localhost:8001/reports/monthly?year=2026&month=8"

# Same month, one client only
curl "http://localhost:8001/reports/monthly?year=2026&month=8&client_id=<id>"

# What was worked on a specific day
curl "http://localhost:8001/reports/daily?date=2026-08-12"

# Total effort spent on a task
curl "http://localhost:8001/reports/task/<task_id>"
```

## MCP server

The MCP server (`mcp_server/server.py`) exposes the API as tools for AI
assistants over stdio: `create_client`, `list_clients`, `create_project`,
`list_projects`, `create_task`, `list_tasks`, `update_task_status`,
`log_hours`, `list_entries`, `update_entry`, `delete_entry`,
`monthly_report`, `daily_report` and `task_report`.

### Install

The server needs the `mcp` and `httpx` packages, already included in
`requirements.txt`:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

It talks to the API over HTTP, so **the API must be running** (Docker or
local) before the tools work. The API base URL is configured via the
`WORKHOURS_API_URL` environment variable (default `http://localhost:8001`).

### Register in Claude Code

The repository ships a project-scoped `.mcp.json`, so opening Claude Code in
this directory picks the server up automatically (approve it when prompted).
To register it manually — or from another directory — use:

```bash
claude mcp add workhours \
  --env WORKHOURS_API_URL=http://localhost:8001 \
  -- /absolute/path/to/workhours-calendar/.venv/bin/python \
     /absolute/path/to/workhours-calendar/mcp_server/server.py
```

Verify with `claude mcp list` (the server should show as connected) or `/mcp`
inside a Claude Code session.

### Run via Docker (no Python required)

The MCP server is also published as a prebuilt image
(`ghcr.io/gifflet/workhours-calendar-mcp`). Since MCP talks over stdio, the
container must run with `-i`:

```bash
claude mcp add workhours \
  -- docker run -i --rm \
     --add-host host.docker.internal:host-gateway \
     -e WORKHOURS_API_URL=http://host.docker.internal:8001 \
     ghcr.io/gifflet/workhours-calendar-mcp:latest
```

`host.docker.internal` lets the container reach the API on your host. On
macOS/Windows it works out of the box; the `--add-host` flag makes it work on
Linux too.

### Use

With the API up and the server registered, just ask Claude in natural language:

> "Log 2.5 hours today on the CI pipeline task of ACME's ERP project"
>
> "How many hours did I work for ACME in August?"
>
> "Which tasks did I work on yesterday?"

The **`workhours` skill** (`.claude/skills/workhours/SKILL.md`) is loaded
automatically in this project and teaches the model the workflow: resolve
names to ids via the `list_*` tools, create missing clients/projects/tasks on
demand, prefer `task_id` when logging hours, and answer report questions with
a single `monthly_report`/`daily_report`/`task_report` call.

### Test the server standalone

```bash
# Requires the API running on localhost:8001
npx @modelcontextprotocol/inspector .venv/bin/python mcp_server/server.py
```

## CI/CD

`.github/workflows/docker-build.yml` builds and publishes both images on every
push to `main` (tag `latest`), on version tags `v*` (semver tags), and builds
without publishing on pull requests. Multi-arch builds use QEMU + Buildx for:

| Platform | Covers |
|---|---|
| `linux/amd64` | Linux/Windows on Intel/AMD, Intel Macs |
| `linux/arm64` | Apple Silicon Macs, Raspberry Pi 3+ (64-bit OS) |
| `linux/arm/v7` | Raspberry Pi 3+ (32-bit OS) |

Images land at `ghcr.io/gifflet/workhours-calendar-api` and
`ghcr.io/gifflet/workhours-calendar-mcp`. No secrets to configure — the
workflow authenticates with the built-in `GITHUB_TOKEN`.

> **First publish:** GHCR packages start private. To allow anonymous
> `docker pull`, open the package page on GitHub → *Package settings* →
> *Change visibility* → *Public* (once per image).

## Project layout

```
app/
  main.py            # FastAPI app, Swagger metadata, health check
  database.py        # MongoDB connection and indexes
  schemas.py         # Pydantic request models
  utils.py           # ObjectId helpers, serialization
  routers/
    clients.py projects.py tasks.py entries.py reports.py
mcp_server/
  server.py          # MCP stdio server (FastMCP) calling the API
.claude/skills/workhours/SKILL.md   # Claude Code skill
.mcp.json            # Project-scoped MCP registration
Dockerfile           # API image
Dockerfile.mcp       # MCP server image
docker-compose.yaml
.github/workflows/docker-build.yml  # Multi-arch build + publish to GHCR
```
