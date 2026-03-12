# Gotchas

## Vikunja API Quirks
- PUT creates tasks, POST updates tasks (reversed from REST convention)
- `default_project_id` not available in `/api/v1/users` search response — must mint JWT and query `/api/v1/user` as that user
- Saved filter `filters` field expects TaskCollection object: `{"filters": {"filter": "priority >= 4"}}`

## _project_cache Init
- Must initialize `self._project_cache: dict[str, int] = {}` in `__init__` — was missing, caused AttributeError

## JWT Minting
- type=1 required in JWT claims (Vikunja rejects without it)
- jti and sid must be present (UUID format)
- Token cached at module level, not instance level

## User Auto-Creation
- Registration may be disabled on Vikunja instance — raises RuntimeError with helpful message
- Random password must meet Vikunja complexity: UUID + "Aa1!" suffix
- Email uses `@vikunja.local` domain (never actually used for email)

## Empty String vs None
- FastMCP tool params use empty string defaults (not None) for optional strings
- `effective_user = username or None` normalizes empty → None throughout

## Project Resolution Priority
- project_name always wins over project_id when both provided
- If neither provided + username present: use user's default project
- If neither provided + no username: fallback to project_id=1
