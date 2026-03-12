# Requirements

## Core Product
- MCP server exposing Vikunja task management via FastMCP streamable-http transport
- Per-user authentication via JWT minting (VIKUNJA_JWT_SECRET)
- Auto-creation of users and projects on first use

## Tools
- [IMPLEMENTED] create_task — title, project_name, project_id, bucket_id, description, priority, due_date, username
- [IMPLEMENTED] list_tasks — project_name, project_id, username
- [IMPLEMENTED] update_task — task_id, title, done, description, priority, due_date, username
- [IMPLEMENTED] get_task — task_id, username

## Project Resolution
- [IMPLEMENTED] project_name resolved to ID via case-insensitive title match
- [IMPLEMENTED] Auto-create project if name not found
- [IMPLEMENTED] project_name takes priority over project_id

## User Resolution
- [IMPLEMENTED] Look up user by username via `/api/v1/users?s=` search
- [IMPLEMENTED] Auto-create user via `/api/v1/register` if not found
- [IMPLEMENTED] Random password (UUID+complexity chars) — auth via minted JWT, not password

## Priority & Due Date
- [IMPLEMENTED] priority: int 0-5 (0=unset, 1=low, 2=below-normal, 3=normal, 4=high, 5=urgent)
- [IMPLEMENTED] due_date: ISO 8601 string, optional
- [IMPLEMENTED] Both optional on create_task and update_task
