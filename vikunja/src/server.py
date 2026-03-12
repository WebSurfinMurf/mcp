"""
MCP Vikunja Server

Exposes Vikunja task management operations via FastMCP streamable-http transport.
Endpoint: http://mcp-vikunja:8000/mcp

Per-user auth: When VIKUNJA_JWT_SECRET is set, tools accept an optional `username`
parameter. The server mints per-user JWTs so tasks are created under the correct
user's account. If the user doesn't exist in Vikunja, they are auto-created.
When no username is provided, falls back to the service account.
"""
import json
import logging
import os

from mcp.server.fastmcp import FastMCP

from vikunja_client import VikunjaClient

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}',
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (injected via environment variables)
# ---------------------------------------------------------------------------
VIKUNJA_API_URL = os.environ["VIKUNJA_API_URL"]
VIKUNJA_SERVICE_USERNAME = os.environ["VIKUNJA_SERVICE_USERNAME"]
VIKUNJA_SERVICE_PASSWORD = os.environ["VIKUNJA_SERVICE_PASSWORD"]
VIKUNJA_JWT_SECRET = os.environ.get("VIKUNJA_JWT_SECRET", "")

# One shared client instance; the client handles JWT refresh internally.
_client = VikunjaClient(
    VIKUNJA_API_URL,
    VIKUNJA_SERVICE_USERNAME,
    VIKUNJA_SERVICE_PASSWORD,
    jwt_secret=VIKUNJA_JWT_SECRET or None,
)

mcp = FastMCP("vikunja", host="0.0.0.0", port=8000)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_tasks(
    project_id: int = 0,
    project_name: str = "",
    username: str = "",
) -> str:
    """List all tasks in a Vikunja project.

    Args:
        project_id: Numeric Vikunja project ID. If 0 or omitted, uses the user's default project.
        project_name: Project name (e.g. "Work", "Home"). Resolved to ID automatically. Takes priority over project_id.
        username: Vikunja username to authenticate as. Tasks are listed from this user's perspective.

    Returns:
        JSON array of task objects.
    """
    effective_user = username or None
    if project_name:
        project_id = await _client.resolve_project_by_name(project_name, username=effective_user)
    elif project_id == 0 and effective_user:
        pid = await _client.get_user_default_project(effective_user)
        project_id = pid or 1
    elif project_id == 0:
        project_id = 1
    tasks = await _client.list_tasks(project_id, username=effective_user)
    return json.dumps(tasks, indent=2)


@mcp.tool()
async def create_task(
    title: str,
    project_id: int = 0,
    project_name: str = "",
    bucket_id: int | None = None,
    description: str = "",
    priority: int = 0,
    due_date: str = "",
    username: str = "",
) -> str:
    """Create a new task in a Vikunja project.

    Args:
        title: Task title (required).
        project_id: Numeric Vikunja project ID. If 0 or omitted, uses the user's default project.
        project_name: Project name (e.g. "Work", "Home", "Tech"). Resolved to ID automatically. Takes priority over project_id.
        bucket_id: Kanban bucket/column ID to place the task in (optional).
        description: Task description in plain text or Markdown (default empty).
        priority: Priority level 0-5. 0=unset, 1=low/backlog, 2=below-normal, 3=normal/this-week, 4=high/tomorrow, 5=urgent/today. Optional.
        due_date: Due date in ISO 8601 format (e.g. "2026-03-15T00:00:00Z"). Optional — only set when a date is mentioned.
        username: Vikunja username to authenticate as. Task will be owned by this user.

    Returns:
        JSON object of the newly created task.
    """
    effective_user = username or None
    if project_name:
        project_id = await _client.resolve_project_by_name(project_name, username=effective_user)
    elif project_id == 0 and effective_user:
        pid = await _client.get_user_default_project(effective_user)
        project_id = pid or 1
    elif project_id == 0:
        project_id = 1
    task = await _client.create_task(
        project_id=project_id,
        title=title,
        description=description,
        bucket_id=bucket_id,
        priority=priority if priority > 0 else None,
        due_date=due_date or None,
        username=effective_user,
    )
    return json.dumps(task, indent=2)


@mcp.tool()
async def update_task(
    task_id: int,
    title: str | None = None,
    done: bool | None = None,
    description: str | None = None,
    priority: int | None = None,
    due_date: str = "",
    username: str = "",
) -> str:
    """Update fields of an existing Vikunja task.

    Provide only the fields you want to change; omit the rest.

    Args:
        task_id: Numeric task ID (required).
        title: New title for the task (optional).
        done: Set True to mark the task complete, False to reopen (optional).
        description: New description text (optional).
        priority: Priority level 0-5. 0=unset, 1=low/backlog, 2=below-normal, 3=normal/this-week, 4=high/tomorrow, 5=urgent/today.
        due_date: Due date in ISO 8601 format (e.g. "2026-03-15T00:00:00Z"). Optional.
        username: Vikunja username to authenticate as.

    Returns:
        JSON object of the updated task.
    """
    if title is None and done is None and description is None and priority is None and not due_date:
        return json.dumps({"error": "At least one field must be provided to update."})
    effective_user = username or None
    task = await _client.update_task(
        task_id=task_id,
        title=title,
        done=done,
        description=description,
        priority=priority,
        due_date=due_date or None,
        username=effective_user,
    )
    return json.dumps(task, indent=2)


@mcp.tool()
async def get_task(task_id: int, username: str = "") -> str:
    """Retrieve details for a single Vikunja task.

    Args:
        task_id: Numeric task ID.
        username: Vikunja username to authenticate as.

    Returns:
        JSON object with full task details.
    """
    effective_user = username or None
    task = await _client.get_task(task_id, username=effective_user)
    return json.dumps(task, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
