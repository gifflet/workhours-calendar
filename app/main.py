from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import ensure_indexes
from app.routers import clients, entries, projects, reports, tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        ensure_indexes()
    except Exception:
        # MongoDB may not be up yet; the API still boots and endpoints
        # will surface connection errors on use.
        pass
    yield


app = FastAPI(
    title="Workhours Calendar API",
    description=(
        "Track worked hours by client, project and task. "
        "Monthly, daily and per-task reports help you see where the time went."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(clients.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(entries.router)
app.include_router(reports.router)


@app.get("/health", tags=["Health"])
def health():
    try:
        db_ok = db_ping()
    except Exception:
        db_ok = False
    return {"status": "ok", "mongodb": "up" if db_ok else "down"}


def db_ping() -> bool:
    from app.database import client

    client.admin.command("ping")
    return True
