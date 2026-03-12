# Interfaces

## MCP Endpoint
- URL: `http://mcp-vikunja:8000/mcp`
- Transport: FastMCP streamable-http
- Server name: "vikunja"

## Tool Schemas

### create_task
| Param | Type | Required | Default |
|-------|------|----------|---------|
| title | str | yes | - |
| project_id | int | no | 0 (→ user default) |
| project_name | str | no | "" (takes priority over project_id) |
| bucket_id | int|None | no | None |
| description | str | no | "" |
| priority | int | no | 0 |
| due_date | str | no | "" |
| username | str | no | "" |

### list_tasks
| Param | Type | Required | Default |
|-------|------|----------|---------|
| project_id | int | no | 0 |
| project_name | str | no | "" |
| username | str | no | "" |

### update_task
| Param | Type | Required | Default |
|-------|------|----------|---------|
| task_id | int | yes | - |
| title | str|None | no | None |
| done | bool|None | no | None |
| description | str|None | no | None |
| priority | int|None | no | None |
| due_date | str | no | "" |
| username | str | no | "" |

### get_task
| Param | Type | Required | Default |
|-------|------|----------|---------|
| task_id | int | yes | - |
| username | str | no | "" |

## Vikunja REST API (consumed)
| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/v1/login | Service account auth |
| GET | /api/v1/users?s= | User search |
| POST | /api/v1/register | User creation |
| GET | /api/v1/user | Current user profile (default_project_id) |
| PUT | /api/v1/projects/{id}/tasks | Create task |
| POST | /api/v1/tasks/{id} | Update task |
| GET | /api/v1/projects/{id}/tasks | List tasks |
| GET | /api/v1/tasks/{id} | Get task |
| GET | /api/v1/projects | List projects |
| PUT | /api/v1/projects | Create project |
