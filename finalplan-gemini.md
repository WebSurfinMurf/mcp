# Superior Plan for Deploying LiteLLM with MCP Gateway

This document presents a comprehensive, production-ready plan for deploying the LiteLLM proxy with the Model Context Protocol (MCP) Gateway on your local network. It synthesizes best practices, resolves contradictions from previous plans, and provides a secure, resilient, and easy-to-manage solution.

This plan is designed to meet your specific requirements:
- **Simplicity:** A declarative `docker-compose` setup for easy management.
- **LAN Access:** Services accessible via `linuxserver.lan`.
- **No Code Changes:** Uses official Docker images without modification.
- **Target Version:** LiteLLM `v1.77.3-stable`.
- **Best Practices:** Clear guidance on `stdio`, `sse`, and `http` transports.

---

## Part I: Foundational Architecture

We will adopt a declarative, container-based architecture using Docker Compose. This is superior to imperative shell scripts as it provides:
- **Dependency Management:** Ensures services start in the correct order (e.g., database before the application).
- **Health Checks:** Automatically restarts services that become unhealthy.
- **Network Isolation:** Creates a dedicated virtual network for secure inter-service communication.
- **Reproducibility:** Guarantees a consistent deployment every time.

Our stack will consist of three core services:
1.  `postgres`: The PostgreSQL database for LiteLLM's internal data (logging, key management).
2.  `mcp-postgres`: The MCP server (`crystaldba/postgres-mcp`) that exposes database tools to the LLM.
3.  `litellm-proxy`: The LiteLLM proxy itself, acting as the central gateway.

## Part II: MCP Transport Protocols Explained

A clear understanding of the three transport protocols is crucial for choosing the right tool for the job.

### 1. SSE (Server-Sent Events) - **Recommended for LAN**
This is the **best choice** for your goal of running each MCP in its own Docker container.
- **How it works:** The MCP server runs as a persistent network service (e.g., in a Docker container) and LiteLLM connects to it as a client over the network.
- **Use Case:** A stateful or long-running tool, like the `postgres-mcp` server.
- **Pros:** Robust, scalable, and aligns perfectly with microservice architectures.

### 2. HTTP - **Alternative for LAN**
Similar to SSE, this is for networked services.
- **How it works:** The MCP server exposes a standard HTTP endpoint.
- **Use Case:** For MCP servers that specifically implement the HTTP transport.
- **Note:** SSE is more common in the current MCP ecosystem.

### 3. Stdio (Standard Input/Output) - **For Local Tools Only**
This protocol is for command-line tools that run locally on the same machine (or inside the same container) as LiteLLM.
- **How it works:** LiteLLM spawns the tool as a child process and communicates with it over `stdin` and `stdout`.
- **Use Case:** A simple, stateless script, e.g., a script to list local files.
- **Pitfall:** This becomes complex in a containerized environment if the tool is not part of the LiteLLM image. The recommended pattern is to **wrap the stdio tool in its own minimal Docker container that exposes an SSE or HTTP endpoint**, effectively converting it into a networked service.

---

## Part III: Deployment Artifacts

Create a new directory for your project, for example, `/home/administrator/projects/mcp-gateway`. Inside this directory, create the following three files.

### File 1: `docker-compose.yml`
This file is the heart of our deployment, defining all services, networks, and volumes.

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: mcp-postgres-db
    restart: unless-stopped
    networks:
      - mcp-net
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  mcp-postgres:
    image: crystaldba/postgres-mcp:latest
    container_name: mcp-postgres-connector
    restart: unless-stopped
    networks:
      - mcp-net
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      - DATABASE_URI=${MCP_POSTGRES_DATABASE_URL}
      - MCP_TRANSPORT=sse
      - MCP_PORT=8686
      - MCP_ALLOW_WRITE=false
    ports:
      - "48000:8686" # Expose MCP server on host port 48000

  litellm-proxy:
    image: ghcr.io/berriai/litellm:v1.77.3-stable
    container_name: mcp-litellm-proxy
    restart: unless-stopped
    networks:
      - mcp-net
    ports:
      - "4000:4000"
    depends_on:
      mcp-postgres:
        condition: service_started # mcp-postgres has no healthcheck
    volumes:
      - ./config.yaml:/app/config.yaml:ro
    env_file:
      - ./.env
    command: ["--config", "/app/config.yaml", "--detailed_debug"]

networks:
  mcp-net:
    driver: bridge

volumes:
  postgres_data:
```

### File 2: `.env`
This file stores all your secrets. **Remember to replace the placeholder values.**

```
# .env - Environment variables for the LiteLLM MCP Gateway stack

# ---
# PostgreSQL Database Settings ---
POSTGRES_USER=litellm_admin
POSTGRES_PASSWORD=a_very_secure_password_placeholder
POSTGRES_DB=litellm_db

# ---
# LiteLLM Proxy Settings ---
DATABASE_URL=postgresql://litellm_admin:a_very_secure_password_placeholder@postgres:5432/litellm_db
LITELLM_MASTER_KEY=sk-litellm-master-key-placeholder

# ---
# MCP Connector Settings ---
MCP_POSTGRES_DATABASE_URL=postgresql://litellm_admin:a_very_secure_password_placeholder@postgres:5432/litellm_db
```

### File 3: `config.yaml`
This is the core configuration for LiteLLM.

```yaml
# General settings for the LiteLLM library
litellm_settings:
  database_url: ${DATABASE_URL}

# Definition of LLM models available through the proxy
model_list:
  - model_name: gpt-4o-mock
    litellm_params:
      model: "mock-response"
      api_key: "not-needed-for-mock"

# Virtual API keys for client authentication
virtual_keys:
  - api_key: "test-key-1234"
    models: ["gpt-4o-mock"]
    user: "lan-test-user"

# Alias mapping for friendly tool names
mcp_aliases:
  db: mcp_postgres_main

# Registration of MCP tool servers
mcp_servers:
  mcp_postgres_main:
    url: "http://mcp-postgres:8686" # Internal Docker network URL
    transport: "sse"
    api_keys: ["test-key-1234"]
```

---

## Part IV: Deployment and Verification

### Step 1: Prepare the Environment
1.  SSH into `linuxserver.lan`.
2.  Create the project directory: `mkdir -p /home/administrator/projects/mcp-gateway`
3.  `cd /home/administrator/projects/mcp-gateway`
4.  Create the three files (`docker-compose.yml`, `.env`, `config.yaml`) with the content above.
5.  **Crucially, edit the `.env` file** and replace the placeholder passwords and keys with strong, unique values.
6.  Set secure permissions for the secrets file: `chmod 600 .env`.

### Step 2: Launch the Stack
1.  From the project directory, run: `docker compose up -d`
2.  This command will download the images, create the network and volume, and start the services in the correct order.

### Step 3: Verify Service Health
1.  Wait about a minute for the services to initialize.
2.  Check the status of the containers: `docker compose ps`
3.  **Expected Outcome:** All three services should show a `STATUS` of `running`. The `mcp-postgres-db` service should additionally show `(healthy)`.

### Step 4: Verify Tool Discovery
Run this command from the `linuxserver.lan` host to confirm that LiteLLM has discovered the tools from the MCP server.

```bash
curl http://localhost:4000/v1/models -H "Authorization: Bearer test-key-1234" | jq
```
**Expected Outcome:** You will see a JSON response. Inside the entry for `gpt-4o-mock`, there should be a `tools` array populated with the tools from the postgres MCP (e.g., `db_execute_sql`, `db_list_tables`). This confirms the gateway is working.

### Step 5: End-to-End Tool Call Test
This is the final and most important test.

1.  **Create a test script `verify.sh`** in your project directory:
    ```bash
    #!/bin/bash
    curl -s http://linuxserver.lan:4000/chat/completions \
      -H "Authorization: Bearer test-key-1234" \
      -H "Content-Type: application/json" \
      -d '{ 
        "model": "gpt-4o-mock",
        "messages": [{"role": "user", "content": "List all tables in the database"}],
        "tool_choice": "auto"
      }' | jq
    ```
2.  Make it executable: `chmod +x verify.sh`
3.  Run it: `./verify.sh`

**Expected Outcome:** Since we are using `mock-response`, LiteLLM will simulate an LLM response. You should see a JSON object in the output containing a `tool_calls` array. This demonstrates that LiteLLM correctly interpreted the prompt, matched it to an available tool, and is ready to execute it. This confirms the entire chain is functional.

---

## Executive Summary

This plan establishes a robust, secure, and maintainable LiteLLM MCP Gateway. By leveraging Docker Compose, we create a declarative and reproducible deployment. We standardize on the `sse` transport protocol for containerized MCPs, which is the best practice for a LAN environment. The plan provides a complete set of configuration artifacts and a clear, step-by-step verification process to ensure a successful deployment. This architecture is scalable, allowing for the easy addition of new MCP servers in the future, and provides a solid foundation for building powerful AI applications on your local network.
