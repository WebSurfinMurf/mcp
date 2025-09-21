# Project Plan: Standalone LiteLLM MCP Gateway Deployment

**Objective:** Deploy a standalone, internal-only LiteLLM proxy that acts as an MCP Gateway. This deployment will be simple, secure, and avoid external dependencies like Traefik and Keycloak. The initial focus is on integrating with the `mcp-postgres` service for tool-calling and using a PostgreSQL database for logging and auditing.

---

## Phase 1: Environment Setup & Configuration

This phase ensures the underlying database and configuration files are in place before deploying the application.

### 1.1: Directory Structure
Create the necessary directory structure for the LiteLLM project.

```bash
mkdir -p /home/administrator/projects/mcp/litellm/config
```

### 1.2: Database Preparation
Prepare the PostgreSQL database by creating a dedicated user and database for LiteLLM's internal logging and auditing.

**Action:**
Execute the following SQL commands by connecting to the main PostgreSQL instance as an admin.

```sql
-- Connect as admin user to the main postgres database
-- PGPASSWORD='Pass123qp' psql -h localhost -p 5432 -U admin -d postgres

-- Create a dedicated user for LiteLLM
CREATE USER litellm_user WITH PASSWORD 'a_very_secure_password_placeholder';

-- Create the database for LiteLLM logging
CREATE DATABASE litellm_db OWNER litellm_user;

-- Grant privileges to the new user
GRANT ALL PRIVILEGES ON DATABASE litellm_db TO litellm_user;
```
**Note:** Replace `a_very_secure_password_placeholder` with a securely generated password.

### 1.3: Create Environment File
Create a centralized environment file to store secrets. Per the coding standards, this will be outside the project directory.

**Action:**
Create the file `/home/administrator/secrets/mcp-litellm.env` with the following content.

```env
# /home/administrator/secrets/mcp-litellm.env

# PostgreSQL Database URL for LiteLLM's internal logging
DATABASE_URL="postgresql://litellm_user:a_very_secure_password_placeholder@postgres:5432/litellm_db"

# Master Key for LiteLLM - used for initial setup and admin tasks
LITELLM_MASTER_KEY="sk-litellm-master-key-placeholder"

# Add any real LLM provider API keys here if needed for testing
# OPENAI_API_KEY="sk-..."
```
**Actions:**
1.  Replace password and key placeholders with secure values.
2.  Set secure permissions for the file: `chmod 600 /home/administrator/secrets/mcp-litellm.env`.

---

## Phase 2: LiteLLM Deployment Configuration

This phase involves configuring the LiteLLM proxy and creating the script to deploy it.

### 2.1: LiteLLM Configuration (`config.yaml`)
This file is the core of the LiteLLM proxy setup. It defines models, enables database logging, creates virtual keys, and registers the `mcp-postgres` tool server.

**Action:**
Create the file `/home/administrator/projects/mcp/litellm/config/config.yaml` with the following content.

```yaml
# /home/administrator/projects/mcp/litellm/config/config.yaml

# General settings for the LiteLLM proxy
litellm_settings:
  database_url: ${DATABASE_URL} # Load from env for logging/auditing

# Define the list of available models. We can start with a mock model.
model_list:
  - model_name: gpt-3.5-turbo # Virtual model name
    litellm_params:
      model: "mock-response" # Use LiteLLM's built-in mock response
      api_key: "any"

# Define virtual keys for clients to use.
virtual_keys:
  - api_key: "test-key-1234"
    models: ["gpt-3.5-turbo"] # Access to the mock model
    max_budget: 1 # in USD
    user: "test-user"

# Register the mcp-postgres service as a tool provider
mcp_settings:
  - mcp_server:
      # Assumes mcp-postgres is a stdio service
      command: "node /home/administrator/projects/mcp/postgres/src/index.js"
      # Assign a name for this toolset
      name: "mcp_postgres_tools"
      # Make these tools available to requests using "test-key-1234"
      api_keys: ["test-key-1234"]
```

### 2.2: Deployment Script (`deploy.sh`)
Create a shell script to automate the deployment of the LiteLLM container.

**Action:**
Create the file `/home/administrator/projects/mcp/litellm/deploy.sh` with the following content.

```bash
#!/bin/bash
set -e

PROJECT_NAME="mcp-litellm"
CONTAINER_NAME="mcp-litellm"
SECRETS_FILE="/home/administrator/secrets/mcp-litellm.env"
CONFIG_PATH="/home/administrator/projects/mcp/litellm/config/config.yaml"

echo "Stopping and removing existing container..."
docker stop ${CONTAINER_NAME} 2>/dev/null || true
docker rm ${CONTAINER_NAME} 2>/dev/null || true

echo "Deploying ${PROJECT_NAME}..."
docker run -d \
  --name ${CONTAINER_NAME} \
  --restart unless-stopped \
  --network postgres-net \
  --env-file ${SECRETS_FILE} \
  -v ${CONFIG_PATH}:/app/config.yaml \
  -p 4000:4000 \
  ghcr.io/berriai/litellm:main-latest \
  --config /app/config.yaml \
  --master_key ${LITELLM_MASTER_KEY}

echo "Deployment of ${PROJECT_NAME} complete."
echo "LiteLLM Proxy should be available internally at http://localhost:4000"
```
**Action:**
Make the script executable: `chmod +x /home/administrator/projects/mcp/litellm/deploy.sh`.

---

## Phase 3: Deployment & Verification

Execute the deployment and perform initial checks to ensure all components are running and connected.

### 3.1: Deploy Services
Run the deployment script to start the LiteLLM proxy.

**Action:**
`./home/administrator/projects/mcp/litellm/deploy.sh`

### 3.2: Initial Verification
Check that the proxy is running and that it has loaded the configuration, including the tools from `mcp-postgres`.

**Action:**
Run the following `curl` command.

```bash
curl http://localhost:4000/v1/models -H "Authorization: Bearer test-key-1234"
```

**Expected Outcome:**
A JSON response containing the `gpt-3.5-turbo` model. The model definition should also include a `tools` section listing the functions provided by the `mcp-postgres` server (e.g., `query`, `list_tables`).

---

## Phase 4: Testing Plan

This phase outlines the steps to test the deployment from the specified client environments.

### 4.1: Test Setup
For each client (Gemini CLI, Claude CLI, ChatGPT CLI, WSL), configure the tool to use the internal LiteLLM proxy as its endpoint. This typically involves setting an environment variable or a flag.

*   **Endpoint URL:** `http://<host_ip>:4000` (replace `<host_ip>` with the server's actual IP address on the local network).
*   **API Key:** `test-key-1234`

### 4.2: Test Case 1: Basic LLM Request
Verify that the proxy can handle a standard chat completion request.

**Action:**
From any configured client, send a simple prompt.

**Expected Outcome:**
The client should receive a mock response like "This is a mock response" from LiteLLM, confirming the proxy is handling requests.

### 4.3: Test Case 2: MCP Tool Usage
Verify that the proxy correctly exposes and calls a tool from the `mcp-postgres` service.

**Action:**
From a client that supports tool-calling, send a prompt that should trigger a database tool, such as "List all the tables in the database."

**Expected Outcome:**
1.  The LLM should respond with a request to call the `list_tables` tool (or equivalent).
2.  The LiteLLM proxy should execute this tool via the `mcp-postgres` stdio process.
3.  The final response should contain a list of tables from the PostgreSQL database.

### 4.4: Test Case 3: Database Audit Verification
Confirm that LiteLLM is logging requests to the PostgreSQL database.

**Action:**
1.  After running the above tests, connect to the `litellm_db` database.
2.  Run `SELECT * FROM litellm_logs ORDER BY start_time DESC LIMIT 5;`.

**Expected Outcome:**
The `litellm_logs` table should contain records corresponding to the API calls made in the previous test cases, including the model used, cost, and user associated with `test-key-1234`.

---

## Phase 5: Documentation

Create a `CLAUDE.md` file to document the final, working state of the deployment for future reference.

### 5.1: Create Documentation File
**Action:**
Create the file `/home/administrator/projects/mcp/litellm/CLAUDE.md`.

### 5.2: Document Final State
**Action:**
Populate the `CLAUDE.md` with:
*   An overview of the internal LiteLLM setup.
*   The full `config.yaml` and `deploy.sh` content.
*   The SQL commands for database setup.
*   The verification and testing steps.
*   The internal access URL (`http://localhost:4000`).

