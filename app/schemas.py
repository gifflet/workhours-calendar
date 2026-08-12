from datetime import date as date_type
from typing import Literal

from pydantic import BaseModel, Field

TaskStatus = Literal["open", "done"]


class ClientIn(BaseModel):
    name: str = Field(min_length=1, examples=["ACME Corp"])
    notes: str | None = None


class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    notes: str | None = None


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, examples=["ERP Migration"])
    client_id: str
    notes: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    client_id: str | None = None
    notes: str | None = None


class TaskIn(BaseModel):
    title: str = Field(min_length=1, examples=["Set up CI pipeline"])
    project_id: str
    description: str | None = None
    status: TaskStatus = "open"


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    status: TaskStatus | None = None


class EntryIn(BaseModel):
    date: date_type = Field(examples=["2026-08-12"])
    hours: float = Field(gt=0, le=24, examples=[3.5])
    task_id: str | None = Field(default=None, description="If given, project and client are derived from the task")
    project_id: str | None = Field(default=None, description="Required when task_id is not given")
    notes: str | None = None


class EntryUpdate(BaseModel):
    date: date_type | None = None
    hours: float | None = Field(default=None, gt=0, le=24)
    notes: str | None = None
