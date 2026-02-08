# MCP Keycloak Server

## Overview
MCP server for Keycloak client credential management, providing 4 tools for automating OAuth2 client operations via the Keycloak Admin REST API.

**Status**: ✅ Operational

## Architecture

```
Claude Code CLI
    ↓ (stdio)
MCP Keycloak Server
    ↓ (HTTPS)
Keycloak Admin REST API
    └── Token endpoint (master realm)
    └── Client management (ai-servicers realm)
```

### Key Design Decisions
- **Token Management**: Mutex-protected with 30-second refresh buffer
- **Idempotent Operations**: 409 Conflict treated as success for mapper creation
- **Single Realm**: All operations target `ai-servicers` realm
- **Admin Auth**: Service account in `master` realm

## Tools (4 total)

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `create_client` | Create confidential OIDC client | clientId, redirectUris, serviceAccountsEnabled |
| `get_client_secret` | Retrieve client secret | clientId |
| `add_groups_mapper` | Add groups claim to tokens | clientId, mapperName, claimName |
| `list_clients` | List/search clients | search, first, max |

## Project Structure

```
src/
├── index.ts              # MCP server entry point
├── keycloak/
│   ├── types.ts          # TypeScript interfaces
│   ├── endpoints.ts      # URL builders
│   ├── client.ts         # HTTP client with token management
│   └── operations.ts     # High-level API operations
└── tools/
    ├── create-client.ts
    ├── get-client-secret.ts
    ├── add-groups-mapper.ts
    └── list-clients.ts
```

## Configuration

### Environment Variables
```bash
KEYCLOAK_URL=https://keycloak.ai-servicers.com
KEYCLOAK_REALM=ai-servicers
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=<from secrets>
```

### Secrets Location
- **File**: `$HOME/projects/secrets/keycloak-admin.env`
- **Permissions**: 600 (owner read/write only)

## Development

### Prerequisites
- Node.js >= 18.0.0
- TypeScript 5.x
- MCP SDK ^1.0.0

### Build & Run
```bash
cd /home/administrator/projects/mcp/keycloak

# Install dependencies
npm install

# Build
npm run build

# Development mode
npm run dev

# Run tests
npm test
```

### Testing
```bash
# Unit tests
npm run test:run

# With coverage
npm test -- --coverage
```

## Integration

### MCP Proxy Registration
After build, add to `/home/administrator/projects/mcp/proxy/config.json`:

```json
{
  "keycloak": {
    "command": "node",
    "args": ["/workspace/mcp/keycloak/dist/index.js"],
    "env": {
      "KEYCLOAK_URL": "https://keycloak.ai-servicers.com",
      "KEYCLOAK_REALM": "ai-servicers",
      "KEYCLOAK_ADMIN_USERNAME": "admin",
      "KEYCLOAK_ADMIN_PASSWORD": "<secret>"
    }
  }
}
```

### Claude Code CLI
```bash
# Register via proxy
claude mcp add keycloak http://localhost:9090/keycloak/mcp -t http

# Test
claude mcp list
```

## API Reference

### Keycloak Admin REST API
- **Base URL**: `https://keycloak.ai-servicers.com/admin/realms/ai-servicers`
- **Auth**: Bearer token from master realm token endpoint
- **Docs**: https://www.keycloak.org/docs-api/latest/rest-api/index.html

### Key Endpoints Used
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/realms/master/protocol/openid-connect/token` | POST | Admin token |
| `/admin/realms/{realm}/clients` | GET/POST | List/Create clients |
| `/admin/realms/{realm}/clients/{id}/client-secret` | GET | Get secret |
| `/admin/realms/{realm}/clients/{id}/protocol-mappers/models` | POST | Add mapper |

## Error Handling

| HTTP Code | Handling |
|-----------|----------|
| 401 | Token expired → refresh and retry |
| 404 | Client not found → return error |
| 409 | Already exists → treat as success (idempotent) |
| 5xx | Server error → return error with details |

## Related Documentation
- **Implementation Plan**: `/home/administrator/projects/ainotes/createplan/mcp-keycloak.plan.final.md`
- **Solution Design**: `/home/administrator/projects/ainotes/createsolution/mcp-keycloak.final.md`
- **MCP Proxy**: `/home/administrator/projects/mcp/proxy/CLAUDE.md`
- **Keycloak**: `/home/administrator/projects/keycloak/CLAUDE.md`

---
**Last Updated**: 2026-01-25
**Implementation Phase**: Complete
