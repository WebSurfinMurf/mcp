# Architecture

## Components
```
Pipecat (consumer)
    → http://mcp-vikunja:8000/mcp (FastMCP streamable-http)
        → Vikunja REST API (http://vikunja:3456)
```

## Files
- `src/server.py` — FastMCP server, 4 tool definitions, project/user resolution logic
- `src/vikunja_client.py` — Async httpx client, JWT minting, user/project CRUD

## Authentication Flow
1. Service account login: POST `/api/v1/login` → service JWT
2. Per-user JWT minting: HS256 with VIKUNJA_JWT_SECRET, 1h expiry
3. User resolution: search by username → auto-create if not found
4. Minted JWT used for all per-user API calls

## Caching
- `_user_cache`: username → {id, username, default_project_id}
- `_user_token_cache`: username → (token, expiry) — module-level
- `_project_cache`: "user:name" → project_id
- Token refresh: 300s margin before expiry

## Vikunja API Semantics
- PUT `/api/v1/projects/{id}/tasks` → create task (returns 200)
- POST `/api/v1/tasks/{id}` → update task (returns 200)
- GET `/api/v1/projects/{id}/tasks` → list tasks
- GET `/api/v1/tasks/{id}` → get single task
- PUT `/api/v1/projects` → create project
- GET `/api/v1/projects` → list projects
