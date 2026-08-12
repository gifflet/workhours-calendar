from datetime import date as date_type

from fastapi import APIRouter, HTTPException

from app import database as db
from app.schemas import EntryIn, EntryUpdate
from app.utils import get_or_404, names_by_id, oid, serialize

router = APIRouter(prefix="/entries", tags=["Time entries"])


def _enrich(docs: list[dict]) -> list[dict]:
    """Attach task/project/client names so consumers don't need extra lookups."""
    task_names = names_by_id(db.tasks, {d["task_id"] for d in docs if d.get("task_id")}, "title")
    project_names = names_by_id(db.projects, {d["project_id"] for d in docs})
    client_names = names_by_id(db.clients, {d["client_id"] for d in docs})
    for d in docs:
        d["task_title"] = task_names.get(d.get("task_id") or "")
        d["project_name"] = project_names.get(d["project_id"])
        d["client_name"] = client_names.get(d["client_id"])
    return docs


@router.post("", status_code=201)
def create_entry(payload: EntryIn):
    if payload.task_id:
        task = get_or_404(db.tasks, payload.task_id, "Task")
        project = get_or_404(db.projects, task["project_id"], "Project")
    elif payload.project_id:
        project = get_or_404(db.projects, payload.project_id, "Project")
    else:
        raise HTTPException(status_code=400, detail="Either task_id or project_id is required")

    doc = {
        "date": payload.date.isoformat(),
        "hours": payload.hours,
        "notes": payload.notes,
        "task_id": payload.task_id,
        # Denormalized for cheap filtering/aggregation on reports.
        "project_id": str(project["_id"]),
        "client_id": project["client_id"],
    }
    result = db.entries.insert_one(doc)
    return _enrich([serialize(db.entries.find_one({"_id": result.inserted_id}))])[0]


@router.get("")
def list_entries(
    date_from: date_type | None = None,
    date_to: date_type | None = None,
    task_id: str | None = None,
    project_id: str | None = None,
    client_id: str | None = None,
):
    query: dict = {}
    date_filter = {}
    if date_from:
        date_filter["$gte"] = date_from.isoformat()
    if date_to:
        date_filter["$lte"] = date_to.isoformat()
    if date_filter:
        query["date"] = date_filter
    if task_id:
        query["task_id"] = task_id
    if project_id:
        query["project_id"] = project_id
    if client_id:
        query["client_id"] = client_id
    docs = [serialize(doc) for doc in db.entries.find(query).sort("date", -1)]
    return _enrich(docs)


@router.get("/{entry_id}")
def get_entry(entry_id: str):
    return _enrich([serialize(get_or_404(db.entries, entry_id, "Entry"))])[0]


@router.patch("/{entry_id}")
def update_entry(entry_id: str, payload: EntryUpdate):
    get_or_404(db.entries, entry_id, "Entry")
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    if "date" in fields:
        fields["date"] = fields["date"].isoformat()
    db.entries.update_one({"_id": oid(entry_id)}, {"$set": fields})
    return _enrich([serialize(db.entries.find_one({"_id": oid(entry_id)}))])[0]


@router.delete("/{entry_id}", status_code=204)
def delete_entry(entry_id: str):
    get_or_404(db.entries, entry_id, "Entry")
    db.entries.delete_one({"_id": oid(entry_id)})
