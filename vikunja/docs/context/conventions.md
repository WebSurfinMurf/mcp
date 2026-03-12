# Conventions

## Code Organization
- `src/server.py` — FastMCP tool definitions (~190 LOC)
- `src/vikunja_client.py` — HTTP client + auth (~380 LOC)
- Single `_client` instance shared across all tool calls

## Naming
- Container: `mcp-vikunja`, network: `mcp-net`
- Project cache key: `"{username or '_service'}:{name.lower()}"`
- User token cache: module-level dict (not instance-level)

## Patterns
- `effective_user = username or None` — empty string → None normalization
- project_name resolution before project_id (priority)
- Default project fallback: user's default_project_id → project 1
- JWT claims: id, username, exp, jti, sid, type=1

## Dependencies
- `fastmcp` (via mcp SDK)
- `httpx` — async HTTP client
- `PyJWT` — JWT minting (HS256)
