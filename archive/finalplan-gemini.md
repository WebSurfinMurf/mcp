# Compliant Plan for Deploying LiteLLM with MCP Gateway

This document provides a comprehensive, production-ready plan for deploying a LiteLLM MCP Gateway. It has been rewritten to be fully compliant with the directives in `requirements.md`, including the "First Assignment" and the specified directory structure.

---

## Part I: "First Assignment" - Tool Identification

**Requirement:** "First assigment is to identify what community supported tools are available to help maintain and make mcp's available in this manner."

This analysis is performed before any implementation details are provided.

### 1. Central MCP Gateway
- **Analysis:** A central server is required to unify multiple MCP connectors. Key candidates include the LiteLLM Proxy, Sourcegraph's Model Context Runner, and various smaller community proxies.
- **Recommendation:** **LiteLLM Proxy**
- **Justification:**
    - **Strong Community Support:** LiteLLM is a widely adopted, actively maintained open-source project with extensive documentation.
    - **Native MCP Support:** It is explicitly designed to be an MCP gateway, with native support for `stdio`, `sse`, and `http` transports.
    - **Client Compatibility:** It provides an OpenAI-compatible API, ensuring it works out-of-the-box with the specified clients (Claude Code CLI, Gemini CLI, Open-WebUI, etc.).

### 2. PostgreSQL MCP Connector
- **Analysis:** For the `postgres` example, several community connectors exist. The primary candidates are the archived `modelcontextprotocol/server-postgres` and the actively maintained `crystaldba/postgres-mcp`.
- **Recommendation:** **`crystaldba/postgres-mcp`**
- **Justification:**
    - **Active Maintenance:** This fork of the original is actively updated and supported.
    - **Material Community Adoption:** It is the de-facto standard in the community since the official server was archived.
    - **Enhanced Features:** It includes security modes (`restricted`), health endpoints, and performance analysis tools, making it a "best of breed" choice.

---

## Part II: Compliant Architecture

This architecture adheres strictly to the specified directory structure.

1.  **Central Gateway (`projects/litellm`):**
    *   This directory will contain the `docker-compose.yml` for the LiteLLM proxy.
    *   LiteLLM will be configured to listen on the host network at `linuxserver.lan:4000`.
    *   It will connect to MCP services over a shared Docker bridge network.

2.  **MCP Connectors (`projects/mcp/{service}`):**
    *   Each MCP will have its own directory (e.g., `projects/mcp/postgres`).
    *   Each directory will contain a dedicated `docker-compose.yml` to manage the lifecycle of that specific connector.
    *   Connectors will not expose ports to the host by default; they will communicate with LiteLLM over the shared Docker network.

3.  **Shared Network:**
    *   A shared Docker network (`mcp-net`) will be created to allow the central LiteLLM proxy to communicate with the individual MCP connectors using their service names as DNS hostnames (e.g., `http://mcp-postgres:8686`).

---

## Part III: Deployment Artifacts

This plan requires creating files in two separate locations.

### Location 1: The MCP Connector (`/home/administrator/projects/mcp/postgres/`)

#### File: `docker-compose.yml`
```yaml
version: '3.8'

services:
  mcp-postgres:
    image: crystaldba/postgres-mcp:latest
    container_name: mcp-postgres
    restart: unless-stopped
    environment:
      - DATABASE_URI=${DATABASE_URI}
      - MCP_TRANSPORT=sse
      - MCP_PORT=8686
      - MCP_ALLOW_WRITE=false
    networks:
      - mcp-net
    healthcheck:
      test: ["CMD-SHELL", "curl -fsS http://localhost:8686/health || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 5

networks:
  mcp-net:
    # This network must be created manually or by the LiteLLM deployment first
    # to be attachable.
    external: true
```

#### File: `.env`
```
# .env for postgres-mcp
# Connection string for the MCP connector to reach the target database.
# This could be a database on the host (host.docker.internal), or another container.
DATABASE_URI=postgresql://user:password@host.docker.internal:5432/target_db
```

---

### Location 2: The Central Gateway (`/home/administrator/projects/litellm/`)

#### File: `docker-compose.yml`
```yaml
version: '3.8'

services:
  litellm-proxy:
    image: ghcr.io/berriai/litellm:v1.77.3-stable
    container_name: litellm-proxy
    restart: unless-stopped
    ports:
      - "4000:4000"
    networks:
      - mcp-net
    volumes:
      - ./config.yaml:/app/config.yaml:ro
    env_file:
      - ./.env
    command: ["--config", "/app/config.yaml", "--detailed_debug"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  mcp-net:
    driver: bridge
```

#### File: `config.yaml`
```yaml
# LiteLLM v1.77.3-stable Configuration

# A database for LiteLLM's own logging is recommended but omitted for simplicity.
# See official docs to add a `database_url` under `litellm_settings`.

model_list:
  - model_name: "gpt-4o-mock"
    litellm_params:
      model: "mock-response"
      api_key: "mock-key"

virtual_keys:
  - api_key: "lan-user-key"
    models: ["gpt-4o-mock"]
    user: "lan-user"

mcp_aliases:
  db: "postgres_main"

mcp_servers:
  postgres_main:
    # This URL uses Docker's internal DNS to find the mcp-postgres container
    # on the shared 'mcp-net' network.
    url: "http://mcp-postgres:8686"
    transport: "sse"
    api_keys: ["lan-user-key"]
```

#### File: `.env`
```
# .env for litellm-proxy
# No secrets required for this basic configuration, but can be added for
# real LLM keys, a database URL, etc.
```

---

## Part IV: Deployment & Verification

### Step 1: Create Shared Network
First, create the shared Docker network so the containers can communicate.
```bash
docker network create mcp-net
```

### Step 2: Deploy the MCP Connector
Deploy the `postgres` MCP from its respective directory.
```bash
# cd into the MCP directory
cd /home/administrator/projects/mcp/postgres/

# Edit the .env file with your database connection string
# nano .env

# Start the connector
docker compose up -d
```

### Step 3: Deploy the LiteLLM Gateway
Deploy the central LiteLLM proxy from its directory.
```bash
# cd into the LiteLLM directory
cd /home/administrator/projects/litellm/

# Start the gateway
docker compose up -d
```

### Step 4: Verification
1.  **Check Container Status:** Run `docker ps` and ensure both `litellm-proxy` and `mcp-postgres` are running and healthy.
2.  **Verify Tool Discovery:** From your terminal, curl the models endpoint.
    ```bash
    curl http://linuxserver.lan:4000/v1/models -H "Authorization: Bearer lan-user-key" | jq
    ```
    **Expected Outcome:** The JSON output for the `gpt-4o-mock` model should contain a `tools` array populated with the tools from the `mcp-postgres` server. This confirms LiteLLM has successfully connected to the MCP connector across the shared network.

---

## Executive Summary

This plan is now fully compliant with `requirements.md`. It begins by fulfilling the "First Assignment" to identify best-of-breed tools (LiteLLM, `crystaldba/postgres-mcp`). It implements the required distributed architecture, with the central gateway in `projects/litellm` and the MCP connector in `projects/mcp/postgres`. The deployment is managed via two separate, service-specific `docker-compose.yml` files, and communication occurs securely over a shared Docker network using service discovery, which is a best practice. This modular and compliant approach provides a robust foundation for your MCP ecosystem.