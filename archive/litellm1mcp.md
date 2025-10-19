I have tried to deploy litellm with mcp gateway and failed multiple times.  This time i want to simplify the deploy by sticking to LAN access on server linuxserver.lan.
PLEASE do some deep digging on best practices to register an MCP server to litellm for stdio, http, and sse.
I want to avoide altering litellm and downloaded mcp's, but if its more straight forward to do so, that is OK.  PLEASE summarize why and ASK me first.
I am very fine with each mcp runs in a docker container, i dont view that as modifying, but as a wrapper.
Please keep this in mind when reading below.
ALSO please target litellm v1.77.3-stable 

LITELLM PRIMER:

Of course. Here is a comprehensive guide on LiteLLM's capabilities, including the latest information on Priority-Based Rate Limiting, created for your reference.

### **LiteLLM: The Universal LLM Gateway - A Technical Guide**

This guide provides a comprehensive overview of LiteLLM, its core functionalities, and how to leverage its powerful features for building robust, scalable AI applications.

-----

#### **1. What is LiteLLM?**

LiteLLM is an open-source library that acts as a universal adapter for over 100 Large Language Model (LLM) providers.[1, 2] Its primary purpose is to standardize interaction with a fragmented ecosystem of LLM APIs, allowing developers to write code once and seamlessly switch between different models (e.g., from OpenAI to Azure, Anthropic, Groq, or a local Ollama instance) with minimal to no code changes.[1, 3]

LiteLLM is available in two primary forms [4]:

  * **Python SDK:** A lightweight client library for developers to directly integrate multi-provider LLM access into their Python applications.
  * **Proxy Server (LLM Gateway):** A standalone, production-grade server that centralizes LLM access, management, and governance for teams and organizations.[4]

-----

#### **2. Core Capabilities**

LiteLLM provides a unified interface, standardizing on the popular OpenAI API format for inputs and outputs. This allows you to use familiar tools, like the official OpenAI client, to interact with any supported model.[4, 5]

**Key Functions (SDK & Proxy):**

  * **Chat Completions:** The core `litellm.completion()` (and async `acompletion()`) function provides a consistent way to call any text-generation model.[6, 3]
  * **Streaming:** Full support for streaming responses from all providers by simply setting `stream=True`.[1, 6]
  * **Multi-Modal & Advanced Functions:** Unified functions for a range of AI tasks [7]:
      * `image_generation()`
      * `embedding()`
      * `transcription()` (Speech-to-Text)
      * `speech()` (Text-to-Speech)
  * **Exception Handling:** Automatically maps provider-specific errors to standard OpenAI exceptions, simplifying error handling logic.[4]

-----

#### **3. The LiteLLM Proxy Server: Enterprise-Grade LLM Management**

The Proxy Server is designed for platform teams and production environments, offering a suite of powerful management features through a single API endpoint and a central `config.yaml` file.[4, 8]

  * **Unified API Key Management:** Create "virtual keys" that can be assigned to users, teams, or applications. These keys are managed within LiteLLM, abstracting away the underlying provider keys.[9]
  * **Cost Tracking & Budgets:** Automatically track spending for every request across all providers. Set budgets and spending limits on a per-key, per-team, or per-model basis to control costs effectively.[6, 9]
  * **Advanced Routing & Reliability:**
      * **Load Balancing:** Distribute traffic across multiple deployments of the same model (e.g., across different Azure regions).[10]
      * **Fallbacks:** Configure automatic retries to a secondary model or provider if a primary request fails.[1]
  * **Observability:** Integrates with popular logging and monitoring platforms like Langfuse, Helicone, and MLflow to provide a single pane of glass for all LLM operations.[4]
  * **Admin UI:** A web interface for managing keys, models, teams, viewing spend logs, and configuring the proxy.[8]

-----

#### **4. Model Context Protocol (MCP) Gateway**

LiteLLM extends its universal adapter philosophy to AI tools through the Model Context Protocol (MCP), an open standard for connecting AI applications with external tools and data sources.[11, 12] The LiteLLM Proxy acts as a central **MCP Gateway**, making any MCP-compliant tool accessible to any LLM it supports.[6, 13, 14]

**How it Works:**

1.  **Configuration:** You register MCP servers (which can be local `stdio` processes or remote `http/sse` services) in your `config.yaml` file.[14]
2.  **Discovery & Translation:** The proxy connects to these servers, retrieves the list of available tools, and translates their MCP schemas into the OpenAI function-calling format.[15]
3.  **Unified Access:** When you make a request to the proxy, it presents these translated tools to the target LLM (e.g., Claude, Llama, Gemini) in a format it understands. This makes the entire MCP ecosystem available to models that have no native MCP awareness.[6, 14]
4.  **Access Control:** You can control which keys or teams have access to specific MCP tools, ensuring secure and governed tool usage.[14]

-----

#### **5. Priority-Based Rate Limiting (v1.77.3-stable and later)**

In high-traffic environments, a single proxy may serve multiple workloads with varying importance (e.g., production vs. testing). Without prioritization, low-priority, high-volume traffic could exhaust rate limits or create queues, delaying or causing failures for critical requests.[16]

To solve this, LiteLLM introduced **Request Prioritization**, a beta feature that allows for priority-based handling of incoming requests.[17]

**How it Works:**

  * **Priority Levels:** Requests can be assigned a priority level. The lower the numerical value, the higher the priority (e.g., `priority: 0` is higher than `priority: 100`).[17]
  * **Priority Queuing:** When under load, the LiteLLM proxy uses a priority queue to process requests. High-priority requests are processed before lower-priority ones, ensuring that critical services receive preferential treatment and are less likely to be rate-limited or delayed.[16, 17]
  * **Use Cases:** This is crucial for guaranteeing SLAs for customer-facing applications, preventing experimental workloads from impacting production traffic, and ensuring fair resource allocation across teams.[16]

**Configuration:**

Priority is assigned on a per-request basis by including a `priority` parameter in the API call body.

**Example cURL Request with Priority:**

```bash
curl -X POST http://localhost:4000/chat/completions \
-H "Authorization: Bearer sk-your-virtual-key" \
-H "Content-Type: application/json" \
-d '{
  "model": "gpt-4o",
  "messages":,
  "priority": 10 
}'
```

**Example with OpenAI Python SDK:**

```python
import openai

client = openai.OpenAI(
    base_url="http://localhost:4000",
    api_key="sk-your-virtual-key"
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=,
    extra_body={
        "priority": 10  # Lower number = higher priority
    }
)

print(response)
```

-----

#### **6. Further Reading & Official Sources**

  * **Official Documentation:** [docs.litellm.ai](https://docs.litellm.ai/) [4]
  * **GitHub Repository:**([https://github.com/BerriAI/litellm](https://github.com/BerriAI/litellm)) [6]
  * **Proxy Configuration Details:**([https://docs.litellm.ai/docs/proxy/config\_settings](https://docs.litellm.ai/docs/proxy/config_settings)) [18]
  * **MCP Gateway Guide:**([https://docs.litellm.ai/docs/mcp](https://docs.litellm.ai/docs/mcp)) [14]
  * **Routing & Prioritization:**([https://docs.litellm.ai/docs/routing](https://docs.litellm.ai/docs/routing)) [10]
  * **Release Notes:**([https://github.com/BerriAI/litellm/releases](https://github.com/BerriAI/litellm/releases)) [19]
  * 
# Project Plan: Standalone LiteLLM MCP Gateway Deployment

**Objective:** Deploy a standalone, internal-only LiteLLM proxy that acts as an MCP Gateway. This deployment will be simple, secure, and avoid external dependencies like Traefik and Keycloak. The initial focus is on integrating with the `mcp-postgres` service for tool-calling and using a PostgreSQL database for logging and auditing.
I want to deploy best of breed, pre-defined MCP connector,propritize mcp tool selection that have material community support and adoption, if there is more than one with similiar adoption, choose the one aligned with the core project if one exists.
Deploy mcp in  in respective directories. "projects/mcp/*" for postgresql "projects/mcp/postgresql" but name all assets at mcp-postgresql, like container or connector, etc.

I want to register them to a central mcp server to make them all available via a single connection.
I want the single central mcp server capability to be available on my linuxserver.lan for claude code cli, gemini cli, optionally chatgpt codex cli, open-webui, and vs code on a different machine on the local network.
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
Create the file `$HOME/projects/secrets/mcp-litellm.env` with the following content.

```env
# $HOME/projects/secrets/mcp-litellm.env

# PostgreSQL Database URL for LiteLLM's internal logging
DATABASE_URL="postgresql://litellm_user:a_very_secure_password_placeholder@postgres:5432/litellm_db"

# Master Key for LiteLLM - used for initial setup and admin tasks
LITELLM_MASTER_KEY="sk-litellm-master-key-placeholder"

# Add any real LLM provider API keys here if needed for testing
# OPENAI_API_KEY="sk-..."
```
**Actions:**
1.  Replace password and key placeholders with secure values.
2.  Set secure permissions for the file: `chmod 600 $HOME/projects/secrets/mcp-litellm.env`.

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
SECRETS_FILE="$HOME/projects/secrets/mcp-litellm.env"
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

