# Operations

## Deployment
```bash
cd /home/administrator/projects/mcp/vikunja && ./deploy.sh
```

## Container
- Name: `mcp-vikunja`
- Port: 8000 (internal only)
- Network: mcp-net
- Image: custom build from Dockerfile

## Environment Variables
| Variable | Purpose |
|----------|---------|
| VIKUNJA_API_URL | Vikunja REST API base URL |
| VIKUNJA_SERVICE_USERNAME | Service account username |
| VIKUNJA_SERVICE_PASSWORD | Service account password |
| VIKUNJA_JWT_SECRET | Shared secret for JWT minting |

## Health Check
```bash
docker logs mcp-vikunja 2>&1 | tail -20
# Should show "Vikunja service JWT obtained"
```

## Dependencies
- Vikunja server must be running (vikunja:3456 on mcp-net or equivalent)
- VIKUNJA_JWT_SECRET must match Vikunja's JWTSECRET config
