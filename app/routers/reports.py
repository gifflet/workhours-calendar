from collections import defaultdict
from datetime import date as date_type

from fastapi import APIRouter, Query

from app import database as db
from app.utils import get_or_404, names_by_id

router = APIRouter(prefix="/reports", tags=["Reports"])


def _grouped_totals(docs: list[dict]) -> dict:
    """Group entries by client, project, task and day, resolving names."""
    by_client: dict[str, float] = defaultdict(float)
    by_project: dict[str, float] = defaultdict(float)
    by_task: dict[str, float] = defaultdict(float)
    by_day: dict[str, float] = defaultdict(float)
    for d in docs:
        by_client[d["client_id"]] += d["hours"]
        by_project[d["project_id"]] += d["hours"]
        if d.get("task_id"):
            by_task[d["task_id"]] += d["hours"]
        by_day[d["date"]] += d["hours"]

    client_names = names_by_id(db.clients, set(by_client))
    project_names = names_by_id(db.projects, set(by_project))
    task_names = names_by_id(db.tasks, set(by_task), "title")

    return {
        "total_hours": round(sum(d["hours"] for d in docs), 2),
        "entry_count": len(docs),
        "by_client": [
            {"client_id": k, "client_name": client_names.get(k), "hours": round(v, 2)}
            for k, v in sorted(by_client.items(), key=lambda i: -i[1])
        ],
        "by_project": [
            {"project_id": k, "project_name": project_names.get(k), "hours": round(v, 2)}
            for k, v in sorted(by_project.items(), key=lambda i: -i[1])
        ],
        "by_task": [
            {"task_id": k, "task_title": task_names.get(k), "hours": round(v, 2)}
            for k, v in sorted(by_task.items(), key=lambda i: -i[1])
        ],
        "by_day": [
            {"date": k, "hours": round(v, 2)} for k, v in sorted(by_day.items())
        ],
    }


@router.get("/monthly")
def monthly_report(
    year: int = Query(ge=2000, le=2100),
    month: int = Query(ge=1, le=12),
    client_id: str | None = None,
    project_id: str | None = None,
):
    """Hours worked in a month, broken down by client, project, task and day."""
    prefix = f"{year:04d}-{month:02d}"
    query: dict = {"date": {"$gte": f"{prefix}-01", "$lte": f"{prefix}-31"}}
    if client_id:
        query["client_id"] = client_id
    if project_id:
        query["project_id"] = project_id
    docs = list(db.entries.find(query))
    return {"period": prefix, **_grouped_totals(docs)}


@router.get("/daily")
def daily_report(date: date_type):
    """Tasks and hours worked on a specific day."""
    docs = list(db.entries.find({"date": date.isoformat()}))
    report = _grouped_totals(docs)
    report.pop("by_day")
    return {"date": date.isoformat(), "tasks_worked": len(report["by_task"]), **report}


@router.get("/task/{task_id}")
def task_report(task_id: str):
    """Total effort spent on a task: hours, entries and date range."""
    task = get_or_404(db.tasks, task_id, "Task")
    docs = list(db.entries.find({"task_id": task_id}).sort("date"))
    dates = [d["date"] for d in docs]
    return {
        "task_id": task_id,
        "task_title": task["title"],
        "status": task["status"],
        "total_hours": round(sum(d["hours"] for d in docs), 2),
        "entry_count": len(docs),
        "first_date": dates[0] if dates else None,
        "last_date": dates[-1] if dates else None,
        "by_day": [{"date": d["date"], "hours": d["hours"], "notes": d.get("notes")} for d in docs],
    }
