import os

from pymongo import ASCENDING, MongoClient

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB", "workhours")

client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000)
db = client[DB_NAME]

clients = db.clients
projects = db.projects
tasks = db.tasks
entries = db.entries


def ensure_indexes() -> None:
    entries.create_index([("date", ASCENDING)])
    entries.create_index([("task_id", ASCENDING)])
    entries.create_index([("project_id", ASCENDING)])
    entries.create_index([("client_id", ASCENDING)])
    projects.create_index([("client_id", ASCENDING)])
    tasks.create_index([("project_id", ASCENDING)])
