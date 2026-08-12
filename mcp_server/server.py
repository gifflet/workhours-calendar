"""MCP server exposing the Workhours Calendar API as tools.

Runs over stdio. The API must be reachable at WORKHOURS_API_URL
(default http://localhost:8001).
"""

import os

import httpx
from mcp.server import MCPServer

API_URL = os.getenv("WORKHOURS_API_URL", "http://localhost:8001")

mcp = MCPServer("workhours")


def _request(method: str, path: str, **kwargs) -> dict | list:
    try:
        response = httpx.request(method, f"{API_URL}{path}", timeout=15.0, **kwargs)
    except httpx.HTTPError as exc:
        return {"error": f"Could not reach the API at {API_URL}: {exc}. Is it running?"}
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        return {"error": f"HTTP {response.status_code}", "detail": detail}
    if response.status_code == 204:
        return {"ok": True}
    return response.json()


# ---------------------------------------------------------------- clients

@mcp.tool()
def create_client(name: str, notes: str | None = None) -> dict | list:
    """Create a client (customer) to group projects under."""
    return _request("POST", "/clients", json={"name": name, "notes": notes})


@mcp.tool()
def list_clients() -> dict | list:
    """List all clients with their ids."""
    return _request("GET", "/clients")


# ---------------------------------------------------------------- projects

@mcp.tool()
def create_project(name: str, client_id: str, notes: str | None = None) -> dict | list:
    """Create a project belonging to a client. Use list_clients to find the client_id."""
    return _request("POST", "/projects", json={"name": name, "client_id": client_id, "notes": notes})


@mcp.tool()
def list_projects(client_id: str | None = None) -> dict | list:
    """List projects, optionally filtered by client_id."""
    params = {"client_id": client_id} if client_id else None
    return _request("GET", "/projects", params=params)


# ---------------------------------------------------------------- tasks

@mcp.tool()
def create_task(title: str, project_id: str, description: str | None = None) -> dict | list:
    """Create a task inside a project. Use list_projects to find the project_id."""
    return _request(
        "POST", "/tasks", json={"title": title, "project_id": project_id, "description": description}
    )


@mcp.tool()
def list_tasks(project_id: str | None = None, status: str | None = None) -> dict | list:
    """List tasks, optionally filtered by project_id and/or status ('open' or 'done')."""
    params = {}
    if project_id:
        params["project_id"] = project_id
    if status:
        params["status"] = status
    return _request("GET", "/tasks", params=params or None)


@mcp.tool()
def update_task_status(task_id: str, status: str) -> dict | list:
    """Set a task's status to 'open' or 'done'."""
    return _request("PATCH", f"/tasks/{task_id}", json={"status": status})


# ---------------------------------------------------------------- time entries

@mcp.tool()
def log_hours(
    date: str,
    hours: float,
    task_id: str | None = None,
    project_id: str | None = None,
    notes: str | None = None,
) -> dict | list:
    """Log worked hours on a date (YYYY-MM-DD). Provide task_id (preferred) or project_id.

    When task_id is given, project and client are derived automatically.
    """
    return _request(
        "POST",
        "/entries",
        json={"date": date, "hours": hours, "task_id": task_id, "project_id": project_id, "notes": notes},
    )


@mcp.tool()
def list_entries(
    date_from: str | None = None,
    date_to: str | None = None,
    task_id: str | None = None,
    project_id: str | None = None,
    client_id: str | None = None,
) -> dict | list:
    """List time entries with optional filters. Dates in YYYY-MM-DD format."""
    params = {
        k: v
        for k, v in {
            "date_from": date_from,
            "date_to": date_to,
            "task_id": task_id,
            "project_id": project_id,
            "client_id": client_id,
        }.items()
        if v
    }
    return _request("GET", "/entries", params=params or None)


@mcp.tool()
def update_entry(
    entry_id: str, date: str | None = None, hours: float | None = None, notes: str | None = None
) -> dict | list:
    """Fix a time entry: change its date (YYYY-MM-DD), hours or notes."""
    payload = {k: v for k, v in {"date": date, "hours": hours, "notes": notes}.items() if v is not None}
    return _request("PATCH", f"/entries/{entry_id}", json=payload)


@mcp.tool()
def delete_entry(entry_id: str) -> dict | list:
    """Delete a time entry logged by mistake."""
    return _request("DELETE", f"/entries/{entry_id}")


# ---------------------------------------------------------------- reports

@mcp.tool()
def monthly_report(
    year: int, month: int, client_id: str | None = None, project_id: str | None = None
) -> dict | list:
    """Hours worked in a month, broken down by client, project, task and day."""
    params = {"year": year, "month": month}
    if client_id:
        params["client_id"] = client_id
    if project_id:
        params["project_id"] = project_id
    return _request("GET", "/reports/monthly", params=params)


@mcp.tool()
def daily_report(date: str) -> dict | list:
    """Tasks and hours worked on a specific day (YYYY-MM-DD)."""
    return _request("GET", "/reports/daily", params={"date": date})


@mcp.tool()
def task_report(task_id: str) -> dict | list:
    """Total effort spent on a task: hours, entry count, date range and per-day detail."""
    return _request("GET", f"/reports/task/{task_id}")


if __name__ == "__main__":
    mcp.run()
