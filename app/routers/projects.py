from fastapi import APIRouter, HTTPException

from app import database as db
from app.schemas import ProjectIn, ProjectUpdate
from app.utils import get_or_404, oid, serialize

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", status_code=201)
def create_project(payload: ProjectIn):
    get_or_404(db.clients, payload.client_id, "Client")
    result = db.projects.insert_one(payload.model_dump())
    return serialize(db.projects.find_one({"_id": result.inserted_id}))


@router.get("")
def list_projects(client_id: str | None = None):
    query = {"client_id": client_id} if client_id else {}
    return [serialize(doc) for doc in db.projects.find(query).sort("name")]


@router.get("/{project_id}")
def get_project(project_id: str):
    return serialize(get_or_404(db.projects, project_id, "Project"))


@router.patch("/{project_id}")
def update_project(project_id: str, payload: ProjectUpdate):
    get_or_404(db.projects, project_id, "Project")
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    if "client_id" in fields:
        get_or_404(db.clients, fields["client_id"], "Client")
    db.projects.update_one({"_id": oid(project_id)}, {"$set": fields})
    return serialize(db.projects.find_one({"_id": oid(project_id)}))


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str):
    get_or_404(db.projects, project_id, "Project")
    if db.tasks.count_documents({"project_id": project_id}) > 0:
        raise HTTPException(status_code=409, detail="Project has tasks; delete them first")
    if db.entries.count_documents({"project_id": project_id}) > 0:
        raise HTTPException(status_code=409, detail="Project has time entries; delete them first")
    db.projects.delete_one({"_id": oid(project_id)})
