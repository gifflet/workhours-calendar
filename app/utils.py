from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from pymongo.collection import Collection


def oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=400, detail=f"Invalid id: {id_str}")


def serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


def get_or_404(collection: Collection, id_str: str, label: str) -> dict:
    doc = collection.find_one({"_id": oid(id_str)})
    if doc is None:
        raise HTTPException(status_code=404, detail=f"{label} not found: {id_str}")
    return doc


def names_by_id(collection: Collection, ids: set[str], field: str = "name") -> dict[str, str]:
    """Map id -> name to enrich responses without N+1 queries."""
    object_ids = []
    for id_str in ids:
        try:
            object_ids.append(ObjectId(id_str))
        except (InvalidId, TypeError):
            continue
    docs = collection.find({"_id": {"$in": object_ids}}, {field: 1})
    return {str(d["_id"]): d.get(field, "?") for d in docs}
