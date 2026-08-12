from fastapi import APIRouter, HTTPException

from app import database as db
from app.schemas import TaskIn, TaskStatus, TaskUpdate
from app.utils import get_or_404, oid, serialize

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("", status_code=201)
def create_task(payload: TaskIn):
    get_or_404(db.projects, payload.project_id, "Project")
    result = db.tasks.insert_one(payload.model_dump())
    return serialize(db.tasks.find_one({"_id": result.inserted_id}))


@router.get("")
def list_tasks(project_id: str | None = None, status: TaskStatus | None = None):
    query: dict = {}
    if project_id:
        query["project_id"] = project_id
    if status:
        query["status"] = status
    return [serialize(doc) for doc in db.tasks.find(query).sort("title")]


@router.get("/{task_id}")
def get_task(task_id: str):
    return serialize(get_or_404(db.tasks, task_id, "Task"))


@router.patch("/{task_id}")
def update_task(task_id: str, payload: TaskUpdate):
    get_or_404(db.tasks, task_id, "Task")
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    db.tasks.update_one({"_id": oid(task_id)}, {"$set": fields})
    return serialize(db.tasks.find_one({"_id": oid(task_id)}))


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: str):
    get_or_404(db.tasks, task_id, "Task")
    if db.entries.count_documents({"task_id": task_id}) > 0:
        raise HTTPException(status_code=409, detail="Task has time entries; delete them first")
    db.tasks.delete_one({"_id": oid(task_id)})
