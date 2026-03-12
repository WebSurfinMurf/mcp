# Security

## Service Account
- Username/password from environment (VIKUNJA_SERVICE_USERNAME/PASSWORD)
- Used for user search/creation and fallback operations
- JWT obtained via POST /api/v1/login, auto-refreshed 300s before expiry

## Per-User JWT Minting
- VIKUNJA_JWT_SECRET (shared with Vikunja server) enables forging valid JWTs
- HS256 algorithm, 1h expiry
- Claims: id (Vikunja user ID), username, exp, jti (UUID), sid (UUID), type=1
- Cached per-user with expiry tracking

## User Auto-Creation
- New users created via POST /api/v1/register
- Random password: UUID + "Aa1!" (meets Vikunja complexity requirements)
- Email: `{username}@vikunja.local` (placeholder)
- Safe because: registration API is internal (mcp-net), web UI behind Keycloak

## Secrets
- `$HOME/projects/secrets/mcp-vikunja.env` — service account credentials
- `$HOME/projects/secrets/vikunja.env` — VIKUNJA_JWT_SECRET
- Both sourced by deploy.sh

## Network
- Container on mcp-net only
- Not publicly exposed (no Traefik labels)
- Consumed by pipecat via http://mcp-vikunja:8000/mcp
