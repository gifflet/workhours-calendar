from fastapi import APIRouter, HTTPException

from app import database as db
from app.schemas import ClientIn, ClientUpdate
from app.utils import get_or_404, oid, serialize

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.post("", status_code=201)
def create_client(payload: ClientIn):
    result = db.clients.insert_one(payload.model_dump())
    return serialize(db.clients.find_one({"_id": result.inserted_id}))


@router.get("")
def list_clients():
    return [serialize(doc) for doc in db.clients.find().sort("name")]


@router.get("/{client_id}")
def get_client(client_id: str):
    return serialize(get_or_404(db.clients, client_id, "Client"))


@router.patch("/{client_id}")
def update_client(client_id: str, payload: ClientUpdate):
    get_or_404(db.clients, client_id, "Client")
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    db.clients.update_one({"_id": oid(client_id)}, {"$set": fields})
    return serialize(db.clients.find_one({"_id": oid(client_id)}))


@router.delete("/{client_id}", status_code=204)
def delete_client(client_id: str):
    get_or_404(db.clients, client_id, "Client")
    if db.projects.count_documents({"client_id": client_id}) > 0:
        raise HTTPException(status_code=409, detail="Client has projects; delete them first")
    db.clients.delete_one({"_id": oid(client_id)})
