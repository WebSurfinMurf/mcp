first read projects/AINotes/memoryfiles.md

I have tried to deploy litellm with mcp gateway and failed multiple times. This time i want to simplify the deploy by sticking to LAN access on server linuxserver.lan. PLEASE do some deep digging on best practices to register an MCP server to litellm for stdio, http, and sse. I want to avoide altering litellm and downloaded mcp's, but if its more straight forward to do so, that is OK. PLEASE summarize why and ASK me first. I am very fine with each mcp runs in a docker container, i dont view that as modifying, but as a wrapper. Please keep this in mind when reading below. ALSO please target litellm v1.77.3-stable
Below is soem requirements, a primer on litellm, and 3 different plans created by 3 different LLMS.
What I want you to do is using your access to my linuxserver.lan that you are running on to look at my server and refine this plan.
Also be sure to search internet for clarification if anything contradicts each other or if one option vs another isnt clear for best path.
Investigate all angles to come up with superiour plan.
At the VERY end of the plan, but an executive summary reflecting the plan.
If you have ANY questions you need answered to help improve the output from me, PLEASE stop and ask me.  I am looking for best plan possible for success.
Write output to projects/mcp/finalplan-{llm}.md   replace {llm} with  your name either claude, gemini, or chatgpt/codex.


LITELLM PRIMER:

Of course. Here is a comprehensive guide on LiteLLM's capabilities, including the latest information on Priority-Based Rate Limiting, created for your reference.

LiteLLM: The Universal LLM Gateway - A Technical Guide
This guide provides a comprehensive overview of LiteLLM, its core functionalities, and how to leverage its powerful features for building robust, scalable AI applications.

1. What is LiteLLM?
LiteLLM is an open-source library that acts as a universal adapter for over 100 Large Language Model (LLM) providers.[1, 2] Its primary purpose is to standardize interaction with a fragmented ecosystem of LLM APIs, allowing developers to write code once and seamlessly switch between different models (e.g., from OpenAI to Azure, Anthropic, Groq, or a local Ollama instance) with minimal to no code changes.[1, 3]

LiteLLM is available in two primary forms [4]:

Python SDK: A lightweight client library for developers to directly integrate multi-provider LLM access into their Python applications.
Proxy Server (LLM Gateway): A standalone, production-grade server that centralizes LLM access, management, and governance for teams and organizations.[4]
2. Core Capabilities
LiteLLM provides a unified interface, standardizing on the popular OpenAI API format for inputs and outputs. This allows you to use familiar tools, like the official OpenAI client, to interact with any supported model.[4, 5]

Key Functions (SDK & Proxy):

Chat Completions: The core litellm.completion() (and async acompletion()) function provides a consistent way to call any text-generation model.[6, 3]
Streaming: Full support for streaming responses from all providers by simply setting stream=True.[1, 6]
Multi-Modal & Advanced Functions: Unified functions for a range of AI tasks [7]:
image_generation()
embedding()
transcription() (Speech-to-Text)
speech() (Text-to-Speech)
Exception Handling: Automatically maps provider-specific errors to standard OpenAI exceptions, simplifying error handling logic.[4]
3. The LiteLLM Proxy Server: Enterprise-Grade LLM Management
The Proxy Server is designed for platform teams and production environments, offering a suite of powerful management features through a single API endpoint and a central config.yaml file.[4, 8]

Unified API Key Management: Create "virtual keys" that can be assigned to users, teams, or applications. These keys are managed within LiteLLM, abstracting away the underlying provider keys.[9]
Cost Tracking & Budgets: Automatically track spending for every request across all providers. Set budgets and spending limits on a per-key, per-team, or per-model basis to control costs effectively.[6, 9]
Advanced Routing & Reliability:
Load Balancing: Distribute traffic across multiple deployments of the same model (e.g., across different Azure regions).[10]
Fallbacks: Configure automatic retries to a secondary model or provider if a primary request fails.[1]
Observability: Integrates with popular logging and monitoring platforms like Langfuse, Helicone, and MLflow to provide a single pane of glass for all LLM operations.[4]
Admin UI: A web interface for managing keys, models, teams, viewing spend logs, and configuring the proxy.[8]
4. Model Context Protocol (MCP) Gateway
LiteLLM extends its universal adapter philosophy to AI tools through the Model Context Protocol (MCP), an open standard for connecting AI applications with external tools and data sources.[11, 12] The LiteLLM Proxy acts as a central MCP Gateway, making any MCP-compliant tool accessible to any LLM it supports.[6, 13, 14]

How it Works:

Configuration: You register MCP servers (which can be local stdio processes or remote http/sse services) in your config.yaml file.[14]
Discovery & Translation: The proxy connects to these servers, retrieves the list of available tools, and translates their MCP schemas into the OpenAI function-calling format.[15]
Unified Access: When you make a request to the proxy, it presents these translated tools to the target LLM (e.g., Claude, Llama, Gemini) in a format it understands. This makes the entire MCP ecosystem available to models that have no native MCP awareness.[6, 14]
Access Control: You can control which keys or teams have access to specific MCP tools, ensuring secure and governed tool usage.[14]
5. Priority-Based Rate Limiting (v1.77.3-stable and later)
In high-traffic environments, a single proxy may serve multiple workloads with varying importance (e.g., production vs. testing). Without prioritization, low-priority, high-volume traffic could exhaust rate limits or create queues, delaying or causing failures for critical requests.[16]

To solve this, LiteLLM introduced Request Prioritization, a beta feature that allows for priority-based handling of incoming requests.[17]

How it Works:

Priority Levels: Requests can be assigned a priority level. The lower the numerical value, the higher the priority (e.g., priority: 0 is higher than priority: 100).[17]
Priority Queuing: When under load, the LiteLLM proxy uses a priority queue to process requests. High-priority requests are processed before lower-priority ones, ensuring that critical services receive preferential treatment and are less likely to be rate-limited or delayed.[16, 17]
Use Cases: This is crucial for guaranteeing SLAs for customer-facing applications, preventing experimental workloads from impacting production traffic, and ensuring fair resource allocation across teams.[16]
Configuration:

Priority is assigned on a per-request basis by including a priority parameter in the API call body.

Example cURL Request with Priority:

curl -X POST http://localhost:4000/chat/completions \
-H "Authorization: Bearer sk-your-virtual-key" \
-H "Content-Type: application/json" \
-d '{
  "model": "gpt-4o",
  "messages":,
  "priority": 10 
}'
Example with OpenAI Python SDK:

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
6. Further Reading & Official Sources
Official Documentation: docs.litellm.ai [4]
GitHub Repository:(https://github.com/BerriAI/litellm) [6]
Proxy Configuration Details:(https://docs.litellm.ai/docs/proxy/config_settings) [18]
MCP Gateway Guide:(https://docs.litellm.ai/docs/mcp) [14]
Routing & Prioritization:(https://docs.litellm.ai/docs/routing) [10]
Release Notes:(https://github.com/BerriAI/litellm/releases) [19]

=== CLAUDE
# Comprehensive MCP Server Registration with LiteLLM v1.77.3-stable

## Configuration syntax for stdio, HTTP, and SSE servers

LiteLLM v1.77.3-stable uses a unified configuration structure in `config.yaml` with **two primary blocks** under `litellm_settings`:

### Core Configuration Structure

```yaml
litellm_settings:
  # Server definitions
  mcp_servers:
    # HTTP Streamable Server
    http_server:
      url: "https://api.example.com/mcp"
      transport: "http"  # Explicit HTTP transport
      auth_type: "api_key"
      spec_version: "2025-03-26"
      
    # SSE (Server-Sent Events) Server - Default transport
    sse_server:
      url: "https://actions.zapier.com/mcp/sk-xxxxx/sse"
      transport: "sse"  # Optional, SSE is default
      
    # Standard Input/Output (stdio) Server
    stdio_server:
      transport: "stdio"
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-filesystem", "/path"]
      env:
        API_KEY: "your-api-key"
        
  # Alias mapping for friendly names
  mcp_aliases:
    "files": "stdio_server"
    "zapier": "sse_server"
    "api": "http_server"
```

**Key discovery**: There is **no `mcp_tools` configuration block** - tools are automatically discovered from configured servers. The `mcp_settings` block mentioned in some documentation refers to the broader `litellm_settings` section.

## Common pitfalls and troubleshooting for registration failures

### Most frequent issues and solutions

**1. Stdio "No such file or directory" Error (Issue #13650)**
- **Cause**: Missing executables in Docker containers
- **Solution**: Ensure all dependencies are installed in container
```yaml
# Working stdio configuration
mcp_servers:
  circleci_mcp:
    transport: "stdio"
    command: "docker"
    args: ["exec", "-i", "mcp-container", "npx", "-y", "@circleci/mcp-server"]
    env:
      CIRCLECI_TOKEN: "your-token"
```

**2. Docker Network Resolution Issues (Issue #13132)**
- **Problem**: Container names not resolving within Docker networks
- **Solution**: Use explicit network configuration
```yaml
services:
  litellm:
    networks:
      - litellm_network
  mcp-server:
    networks:
      - litellm_network
```

**3. Configuration Syntax Errors**
- **Wrong**: JSON-style configuration
- **Correct**: YAML format under `mcp_servers` block

**4. Authentication Header Format**
- **Deprecated**: `x-mcp-auth`
- **Recommended**: `x-mcp-{server_alias}-{header_name}`

## Docker containerization approaches

### Complete Docker Compose Setup

```yaml
version: "3.9"
services:
  litellm:
    image: ghcr.io/berriai/litellm-database:main-stable
    container_name: litellm-proxy
    ports:
      - "4000:4000"
    environment:
      - LITELLM_MASTER_KEY=sk-1234
      - DATABASE_URL=postgresql://litellm:password@postgres:5432/litellm
    volumes:
      - ./litellm_config.yaml:/app/config.yaml
    command: ["--config", "/app/config.yaml", "--detailed_debug"]
    networks:
      - litellm_network
    depends_on:
      - postgres
      - mcp-memory

  # SSE MCP Server Example
  mcp-memory:
    image: oven/bun:1
    container_name: mcp-memory-server
    command: ["bunx", "mcp-proxy", "--port", "8080", "--shell", "bunx", "mcp-knowledge-graph"]
    ports:
      - "8080:8080"
    volumes:
      - mcp_memory_data:/data
    networks:
      - litellm_network

  # stdio MCP Server Requirements
  mcp-stdio:
    image: python:3.11-slim
    stdin_open: true  # Required for stdio
    tty: true        # Required for stdio
    networks:
      - litellm_network

networks:
  litellm_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

volumes:
  mcp_memory_data:
```

**Critical for stdio servers in Docker**:
- Set `stdin_open: true` and `tty: true`
- Use `docker exec -i` for command execution
- Ensure all dependencies available in container

## Network configuration for LAN access on linuxserver.lan

### LAN-Accessible Configuration

```yaml
# For linuxserver.lan domain access
services:
  litellm:
    image: ghcr.io/berriai/litellm:main-stable
    ports:
      - "4000:4000"
    environment:
      - LITELLM_HOST=0.0.0.0  # Accept external connections
    labels:
      # Traefik reverse proxy for domain access
      - "traefik.enable=true"
      - "traefik.http.routers.litellm.rule=Host(`litellm.linuxserver.lan`)"
      - "traefik.http.services.litellm.loadbalancer.server.port=4000"
    networks:
      - litellm_bridge

networks:
  litellm_bridge:
    driver: bridge
    driver_opts:
      com.docker.network.bridge.host_binding_ipv4: "0.0.0.0"
```

### DNS Resolution Setup
```bash
# Host network mode for direct LAN access
network_mode: "host"
environment:
  - LITELLM_HOST=192.168.1.100  # Specific LAN IP
  - LITELLM_PORT=4000
```

## Working PostgreSQL MCP server configurations

### Recommended: Postgres MCP Pro (crystaldba/postgres-mcp)

The official `modelcontextprotocol/servers postgres` is **archived**. Use Postgres MCP Pro instead:

**Development Mode (Full Access)**:
```yaml
mcp_servers:
  postgres_dev:
    transport: "stdio"
    command: "docker"
    args: [
      "run", "-i", "--rm",
      "-e", "DATABASE_URI",
      "crystaldba/postgres-mcp",
      "--access-mode=unrestricted"
    ]
    env:
      DATABASE_URI: "postgresql://user:password@localhost:5432/devdb"
    description: "PostgreSQL with full access"
```

**Production Mode (Restricted)**:
```yaml
mcp_servers:
  postgres_prod:
    transport: "stdio"
    command: "postgres-mcp"
    args: ["--access-mode=restricted"]
    env:
      DATABASE_URI: "postgresql://readonly:pass@db.example.com:5432/prod?sslmode=require"
    description: "Read-only PostgreSQL access"
```

**Key features of Postgres MCP Pro**:
- Performance analysis and query optimization
- Database health monitoring
- Index tuning recommendations
- Configurable access modes
- Required extensions: `pg_stat_statements`, `hypopg`

## How LiteLLM handles MCP server discovery and tool translation

### Discovery and Translation Process

1. **Automatic Tool Discovery**: LiteLLM fetches available tools from each configured MCP server at startup
2. **OpenAI Format Translation**: Tools are converted to OpenAI-compatible function definitions
3. **Alias Prefixing**: Tool names prefixed with server aliases for uniqueness
4. **Dynamic Registration**: No manual tool definition required

### Tool Execution Flow

```python
# 1. LiteLLM discovers tools from MCP servers
tools = await mcp_server.list_tools()

# 2. Converts to OpenAI format
openai_tools = convert_to_openai_format(tools)

# 3. LLM receives tools with user query
response = llm.complete(messages, tools=openai_tools)

# 4. LiteLLM routes tool calls back to appropriate MCP server
result = await mcp_server.execute_tool(tool_name, arguments)
```

### Access Control Methods

**URL-based Namespacing**:
```
/mcp/github           # Single server
/mcp/github,zapier    # Multiple servers
/mcp/dev_group        # Access group
```

**Header-based Namespacing**:
```
x-mcp-servers: "github,zapier,deepwiki"
```

## Authentication and security best practices

### OAuth 2.1 Implementation

```python
async def get_oauth_token(self) -> str:
    current_time = time.time()
    # 60-second buffer for token expiration
    if self.access_token and current_time < self.token_expires_at - 60:
        return self.access_token
    
    # Refresh token
    response = await self.http_client.post(
        self.oauth_config['token_url'],
        data={
            'grant_type': 'client_credentials',
            'client_id': self.oauth_config['client_id'],
            'client_secret': self.oauth_config['client_secret']
        }
    )
```

### Server-Specific Authentication Headers

```yaml
# Recommended approach
headers:
  x-mcp-github-authorization: "Bearer ghp_xxxxxxxxx"
  x-mcp-zapier-x-api-key: "sk-xxxxxxxxx"
  x-mcp-postgres-password: "secure_password"
```

### Guardrails Integration

```yaml
guardrails:
  - guardrail_name: "mcp-input-validation"
    litellm_params:
      guardrail: presidio
      mode: "pre_mcp_call"
      pii_entities_config:
        CREDIT_CARD: "BLOCK"
        EMAIL_ADDRESS: "MASK"
```

### Security Checklist
- ✅ Use TLS/SSL for all HTTP/SSE connections
- ✅ Implement JWT signature verification
- ✅ Validate token scopes against required permissions
- ✅ Run MCP servers in sandboxed environments
- ✅ Enable PII detection and masking
- ✅ Use restricted access modes in production

## Testing procedures to verify registration and tool availability

### MCP Inspector Testing

```bash
# Local testing with Inspector
npx @modelcontextprotocol/inspector node server.js

# Test published MCP packages
npx -y @modelcontextprotocol/inspector npx @modelcontextprotocol/server-filesystem /path

# Docker testing
docker run --rm -p 6274:6274 ghcr.io/modelcontextprotocol/inspector:latest
```

### API Testing

```bash
# List available tools
curl -X GET 'http://localhost:4000/mcp/list_tools' \
  -H 'x-litellm-api-key: Bearer sk-1234' \
  -H 'x-mcp-servers: github,zapier'

# Execute tool
curl -X POST 'http://localhost:4000/mcp/call_tool' \
  -H 'Content-Type: application/json' \
  -H 'x-litellm-api-key: Bearer sk-1234' \
  -d '{
    "name": "get_file",
    "server_name": "filesystem",
    "arguments": {"path": "/test.txt"}
  }'
```

### Testing Workflow
1. **Connection Test**: Verify server starts successfully
2. **Tool Discovery**: Confirm all expected tools are listed
3. **Execution Test**: Run each tool with valid parameters
4. **Error Handling**: Test with invalid inputs
5. **Performance Test**: Monitor `x-litellm-overhead-duration-ms` header

## Configuration block differences

### mcp_servers vs mcp_aliases

**`mcp_servers`**: Primary block for defining MCP server connections
- Contains server URL, transport type, authentication
- Each server has unique configuration
- Supports stdio, HTTP, and SSE transports

**`mcp_aliases`**: Maps friendly names to server definitions
- Simplifies tool references
- Enables cleaner access control
- Used in URL namespacing

**Note**: There is **no `mcp_tools` block** in current LiteLLM architecture. Tools are discovered automatically from servers, not defined separately.

### Access Groups Configuration

```yaml
mcp_servers:
  server_one:
    url: "https://api1.example.com/mcp"
    access_groups: ["dev_group", "production_group"]
  
  server_two:
    url: "https://api2.example.com/mcp"
    access_groups: ["dev_group"]
```

## Wrapper scripts and proxy containers for stdio servers

### Community Solutions

**1. MCP Proxy Pattern (Recommended)**
```yaml
# Wrapper container for stdio MCP servers
mcp-wrapper:
  image: oven/bun:1
  command: ["bunx", "mcp-proxy", "--port", "8080", "--shell", "bunx", "mcp-knowledge-graph"]
  ports:
    - "8080:8080"
```

**2. Direct Execution Pattern**
```yaml
mcp_servers:
  stdio_direct:
    transport: "stdio"
    command: "docker"
    args: ["exec", "-i", "mcp-container", "python", "mcp_server.py"]
```

**3. Community Wrapper Projects**:
- `itsDarianNgo/mcp-server-litellm`: Text completion wrapper
- `mNandhu/mcp-via-litellm`: Protocol-level CLI wrapper
- `dinhdobathi1992/mcp-server-litellm`: Production-ready wrapper with connection pooling

### Stdio Handling Requirements

**Container Requirements**:
- `stdin_open: true` and `tty: true` in Docker Compose
- Process management capabilities
- All dependencies available in container
- Proper environment variable passing

**Best Practice**: Convert stdio servers to HTTP/SSE when possible for better reliability and easier containerization. If stdio is required, use wrapper containers that expose HTTP/SSE endpoints.

## Key Recommendations

1. **Use Latest Stable Version**: v1.77.3-stable builds on v1.74.x MCP features with improved stdio support
2. **Prefer SSE/HTTP over stdio**: Better for containerization and network access
3. **Implement Server-Specific Auth**: Use `x-mcp-{server}-{header}` pattern
4. **Test with MCP Inspector**: Validate servers before production deployment
5. **Use Postgres MCP Pro**: Official PostgreSQL server is archived
6. **Enable Detailed Debugging**: Use `--detailed_debug` flag during setup
7. **Monitor Performance**: Track `x-litellm-overhead-duration-ms` header
8. **Implement Cost Tracking**: Configure per-tool costs for budget management
9. **Use Access Groups**: Simplify permission management at scale
10. **Container Best Practices**: Always set `stdin_open` and `tty` for stdio servers

This comprehensive guide provides everything needed to successfully register and operate MCP servers with LiteLLM v1.77.3-stable, from basic configuration to advanced troubleshooting and security considerations.

==== chatgpt

Got it—let’s lock down **how to register MCP servers to LiteLLM (v1.77.3-stable)** for **stdio**, **SSE**, and **HTTP** without modifying your MCPs (Docker wrappers are 👍). Below are the **battle-tested patterns**, pitfalls to avoid, and a **ready LAN recipe** for your `mcp-postgresql`.

---

# Best practices: registering MCP servers to LiteLLM

## 1) STDIO (local child process)

**When to use:** only when the MCP binary/script is on the same host/inside the same container as LiteLLM. Great for quick dev; awkward if you want each MCP in its own Docker container.

**Config shape (LiteLLM `config.yaml`):**

```yaml
mcp_servers:
  mcp_postgresql:
    transport: "stdio"
    command: "npx"
    args: ["-y", "@vendor/some-postgres-mcp"]  # or your local script/binary
    env:
      DATABASE_URI: "postgresql://user:pass@host:5432/db"
```

**Notes & gotchas**

* `mcp_servers` (not `mcp_settings`) is the correct key; `transport: stdio` requires `command` (and optional `args`, `env`). ([LiteLLM][1])
* If LiteLLM runs in Docker and the MCP is in a **different** container, stdio won’t reach it. Either mount the MCP code **into** the LiteLLM container or prefer SSE/HTTP. ([LiteLLM][1])
* You *can* launch a container via stdio by making LiteLLM run `docker run -i …` so STDIN/STDOUT stream through (example pattern shown in community docs/blogs). ([jamesmcm.github.io][2])

---

## 2) SSE (Server-Sent Events) – **recommended for LAN + Docker**

**When to use:** the MCP runs in its **own container** (your preference), and you want one LiteLLM to reach many MCPs over the LAN.

**Config shape (LiteLLM `config.yaml`):**

```yaml
mcp_servers:
  mcp_postgresql:
    url: "http://linuxserver.lan:48000/sse"
    transport: "sse"     # explicit; default is sse, but be clear
    description: "Postgres via CrystalDBA/Postgres MCP"
```

**Notes & gotchas**

* SSE and HTTP are first-class transports in LiteLLM’s MCP gateway. ([LiteLLM][1])
* Many community servers (e.g., **CrystalDBA/postgres-mcp**) officially document `--transport=sse` and expose `/sse`. Map that port and point LiteLLM at it. ([GitHub][3])
* Use **aliases** to keep tool prefixes clean:

```yaml
litellm_settings:
  mcp_aliases:
    db: mcp_postgresql
```

This yields tool names like `db_list_tables` instead of long server names. ([LiteLLM][1])

* You can **restrict** what the LLM sees per request with the `x-mcp-servers` header (or via URL namespacing). This prevents tool overload and is great for security segmentation. ([LiteLLM][1])

---

## 3) Streamable **HTTP** (when the server supports it)

**When to use:** the MCP explicitly implements **HTTP** transport (fewer do today than SSE).

**Config shape (LiteLLM `config.yaml`):**

```yaml
mcp_servers:
  my_http_mcp:
    url: "http://linuxserver.lan:48001/mcp"  # server-specific path
    transport: "http"
    auth_type: "bearer_token"                # or api_key/basic/authorization
    auth_value: "abc123"
```

* Valid transports: `sse`, `http`, `stdio`; `auth_type` maps to the right header automatically. ([LiteLLM][1])
* If your chosen MCP doesn’t implement HTTP, keep SSE. Converting SSE→HTTP via a separate gateway is possible but adds moving parts (not needed for your “simple LAN” goal). ([LiteLLM][1])

---

# LAN-focused, minimal recipe for **mcp-postgresql**

> Uses **Docker** for the MCP (no code changes), **SSE** for clean LAN access, and LiteLLM v1.77.3-stable as your gateway. If the tag isn’t published yet, fallback to the latest `*-stable` (e.g., v1.77.2-stable).

### A) Run the Postgres MCP (CrystalDBA) via SSE

```bash
# Expose SSE on linuxserver.lan:48000
docker run -d --name mcp-postgresql \
  -p 48000:8000 \
  -e DATABASE_URI="postgresql://user:pass@postgres:5432/dbname" \
  crystaldba/postgres-mcp \
  --access-mode=restricted \
  --transport=sse
```

(They document `--transport=sse` and `/sse` path.) ([GitHub][3])

### B) LiteLLM `config.yaml` (v1.77.3-stable target)

```yaml
model_list:
  - model_name: local-mock
    litellm_params:
      model: "mock-response"
      api_key: "any"

litellm_settings:
  mcp_aliases:
    db: mcp_postgresql

# register the MCP
mcp_servers:
  mcp_postgresql:
    url: "http://linuxserver.lan:48000/sse"
    transport: "sse"
    description: "Postgres tools over SSE"

# give a test virtual key
virtual_keys:
  - api_key: "test-key-1234"
    models: ["local-mock"]
```

Schema and examples match LiteLLM’s MCP docs. ([LiteLLM][1])

### C) Run LiteLLM on your LAN

```bash
docker run -d --name mcp-litellm \
  -p 4000:4000 \
  -v /home/administrator/projects/mcp/litellm/config/config.yaml:/app/config.yaml \
  ghcr.io/berriai/litellm:litellm_stable_release_branch-v1.77.3-stable \
  --config /app/config.yaml \
  --master_key sk-local-admin
```

(Use the exact `*-stable` tag available; v1.76.1-stable is documented publicly—replace with 1.77.3-stable when present.) ([New Releases][4])

### D) Quick verification (lists & calls tools through LiteLLM MCP gateway)

LiteLLM exposes an MCP gateway that converts MCP tools to OpenAI-style tools and serves them via **/v1/responses**:

```bash
curl -s http://linuxserver.lan:4000/v1/responses \
  -H "Authorization: Bearer test-key-1234" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local-mock",
    "input": [{"role":"user","type":"message","content":"List DB tables"}],
    "tools": [{
      "type": "mcp",
      "server_label": "litellm",
      "server_url": "litellm_proxy",
      "require_approval": "never",
      "headers": { "x-mcp-servers": "db" }   // only expose the db MCP
    }],
    "tool_choice": "required",
    "stream": false
  }'
```

That request pattern (with `server_url: "litellm_proxy"`, optional `x-mcp-servers`, and MCP conversion) is straight from the LiteLLM docs. ([LiteLLM][1])

---

## Extra tips that save hours

* **Use aliases + header namespacing** (`x-mcp-servers`) to keep an LLM’s tool list **small & relevant** per call (prevents tool overload). ([LiteLLM][1])
* **Per-server auth headers** from the client are supported (`x-mcp-{alias}-{header}`), e.g., `x-mcp-db-authorization: Bearer <token>`. Great for forwarding DB tokens without baking them into the config. ([LiteLLM][1])
* **Auth in config** for SSE/HTTP servers: `auth_type: api_key|bearer_token|basic|authorization` with `auth_value` → LiteLLM sets the right header. ([LiteLLM][1])
* **Keep stdio local.** If every MCP runs in its own container (your preference), **SSE is simpler** and more robust across the LAN than trying to pipe stdio through Docker. ([LiteLLM][1])

---

## Small corrections to your earlier draft

* Use **`mcp_servers`** instead of `mcp_settings` in `config.yaml`. ([LiteLLM][1])
* To **exercise tools**, use **`/v1/responses`** with the MCP block (not `/v1/models`). The docs show the exact request structure and how LiteLLM converts MCP tools to OpenAI-style functions. ([LiteLLM][1])

---

## Quick ask before I generate files

Given your “LAN-only, each MCP in its own Docker” goal, I recommend we **standardize on SSE containers for all MCPs** and register them in `mcp_servers` as above. It avoids modifying MCP code, sidesteps stdio/Docker quirks, and keeps LiteLLM as a clean central gateway.

**Shall I proceed with:**

* a two-service `docker-compose.yml` (LiteLLM v1.77.3-stable + `mcp-postgresql` on port 48000),
* the exact `/home/administrator/projects/mcp/litellm/config/config.yaml`, and
* a one-shot `verify.sh` that runs the `/v1/responses` MCP test?

(If `v1.77.3-stable` isn’t published yet, I’ll pin to the latest available `*-stable` and note it inline.) ([New Releases][4])

If you’d rather **keep stdio** for `mcp-postgresql`, I can also wire the **`docker run -i` stdio pattern**—just say the word. ([jamesmcm.github.io][2])

[1]: https://docs.litellm.ai/docs/mcp "/mcp - Model Context Protocol | liteLLM"
[2]: https://jamesmcm.github.io/blog/claude-data-engineer/?utm_source=chatgpt.com "I made an AI Agent take an old Data Engineering test"
[3]: https://github.com/crystaldba/postgres-mcp?utm_source=chatgpt.com "Postgres MCP Pro provides configurable read/write access ..."
[4]: https://newreleases.io/project/github/BerriAI/litellm/release/v1.76.1-stable?utm_source=chatgpt.com "BerriAI/litellm v1.76.1-stable on GitHub"

===== gemini
Architecting a Resilient LiteLLM MCP Gateway for Local Area Network DeploymentPart I: Foundational Architecture and Security PostureThis section details the architectural shift from a procedural, script-based deployment to a robust, declarative model using Docker Compose. The analysis of the initial deployment plan reveals potential points of failure, which are systematically addressed with industry-best-practices for security, networking, and service health management. The objective is to construct a resilient foundation that eliminates common failure modes and ensures predictable, stable operation.From Imperative Scripts to Declarative Stacks: Why docker-compose is Non-NegotiableThe initial project plan outlines a deployment strategy using an imperative shell script (deploy.sh) to orchestrate the startup of the LiteLLM container. While straightforward for single-container applications, this approach introduces significant fragility and unpredictability in a multi-service environment that includes a database dependency. An analysis of this script-based method reveals critical shortcomings in dependency management, health checking, and network isolation, which are common sources of deployment failure in distributed applications.1The core principle underpinning a resilient architecture is the transition to declarative infrastructure. Instead of providing a sequence of commands that must be executed in a specific order (an imperative approach), a declarative model defines the desired final state of the application stack. A docker-compose.yml file serves as this declarative manifest, specifying the services, networks, volumes, and dependencies required. The Docker engine then assumes the responsibility for the complex orchestration required to achieve and maintain this state, handling the startup order, networking, and health of each service automatically.A primary cause of repeated deployment failures in multi-container setups is the presence of race conditions during service initialization. The provided history of multiple failed deployment attempts strongly indicates that the LiteLLM proxy container is likely starting and attempting to connect to its PostgreSQL backend before the database service is fully initialized and ready to accept connections. This scenario is almost guaranteed when using sequential docker run commands. Although the docker run postgres command may exit and report a "running" state almost immediately, the PostgreSQL process inside the container requires several seconds to perform critical startup tasks, such as initializing its data directory, starting the server daemon, and opening the network socket to listen for incoming connections. A script that launches the LiteLLM container immediately after the PostgreSQL container will invariably attempt its database connection during this vulnerable initialization window. This results in connection failures, causing the LiteLLM proxy to either crash, enter a degraded state, or fail to enable features that depend on the database, such as logging and virtual key management.The definitive solution to this pervasive problem lies in the combination of Docker Compose's healthcheck directive and the depends_on condition. This mechanism provides a guarantee of service readiness, not just service startup. By defining a healthcheck for the PostgreSQL service that uses a reliable command like pg_isready, the Docker engine can actively poll the database until it confirms it is fully operational.3 Subsequently, the LiteLLM service definition can include depends_on: condition: service_healthy, which instructs the Docker engine to not even begin creating the LiteLLM container until the PostgreSQL container's health check has passed successfully. This fundamentally shifts the deployment logic from a fragile, timing-dependent script to a robust, state-aware orchestration, thereby eliminating the race condition entirely and forming the cornerstone of a stable deployment.Establishing a Secure and Isolated Network FoundationA critical security practice for any multi-container application is network isolation. By default, containers can communicate with each other over a default bridge network, but this provides no segmentation from other, unrelated applications running on the same host. To create a secure perimeter for the LiteLLM stack, the docker-compose.yml manifest will define a custom bridge network, for instance, mcp-net. This practice isolates the LiteLLM proxy, its MCP connectors, and the database from any other containers, preventing unauthorized network access and reducing the potential attack surface.6Within this custom network, Docker provides a built-in DNS service that is fundamental to creating a portable and robust configuration. Services can reliably communicate with one another using their defined service names (e.g., postgres, litellm-proxy) as hostnames. For example, the LiteLLM proxy's configuration can point to its database at the address postgres:5432. The Docker DNS resolver automatically maps the service name postgres to the correct internal IP address of the PostgreSQL container within the mcp-net network. This eliminates the need for fragile, hard-coded IP addresses, which can change whenever a container is restarted, and ensures that the service-to-service communication configuration is both stable and portable across different host environments.Hardening the Deployment: Secrets, Images, and HealthTo further harden the deployment, all sensitive data must be externalized from the configuration files. Best practices for managing secrets in a Docker environment strongly advise against hardcoding values like database passwords, API keys, or administrative master keys directly into the docker-compose.yml or application configuration files.6 Instead, these values will be stored in a dedicated .env file located in the same directory as the docker-compose.yml file. Docker Compose automatically reads this file at runtime and injects the values as environment variables into the appropriate containers. This .env file should be secured with strict file permissions (e.g., chmod 600) and must be explicitly excluded from version control systems (e.g., via .gitignore) to prevent accidental exposure of credentials.Predictability and stability in a production or stable-use environment demand the use of specific, versioned Docker image tags. The deployment will use the exact tag ghcr.io/berriai/litellm:v1.77.3-stable for the LiteLLM proxy. The use of mutable tags like latest or main-latest is strongly discouraged, as they can be updated at any time by the image publisher, introducing unexpected changes, new features, or even breaking changes into the deployment without a corresponding change in the configuration files.8 Pinning to a specific -stable version ensures that the deployment is reproducible and that the behavior of the application remains consistent over time.Finally, the implementation of the PostgreSQL health check is a critical component of the declarative stack. The docker-compose.yml file will include a healthcheck block within the postgres service definition. This block will utilize the pg_isready command-line utility, which is a standard tool included in the official PostgreSQL image specifically designed to check the connection status of a PostgreSQL server. It provides a reliable signal of the database's readiness to accept new connections, which is precisely the state required before dependent services can start.3 The configuration will specify an interval for polling, a timeout for the command, and a number of retries before the container is marked as unhealthy, providing a robust mechanism to manage the database startup sequence.Part II: Selecting and Integrating the Optimal MCP Connector for PostgreSQLThis section provides a formal analysis of the available Model Context Protocol (MCP) connectors for PostgreSQL. It delivers a definitive recommendation for a "best-of-breed" connector, justified by a detailed comparison of features, security posture, and community support. The recommended connector is then integrated into the Docker Compose architecture, establishing a secure and powerful tool for the LiteLLM Gateway.The MCP-PostgreSQL Ecosystem: A Landscape of Opportunity and RiskThe Model Context Protocol (MCP) is an open standard designed to create a universal interface for AI models to securely connect with external tools and data sources, effectively solving the "M x N problem" of integrating numerous AI systems with countless tools.10 This standard is transforming AI development by allowing models to access real-time context, such as codebases, documents, and APIs, through a standardized client-server architecture.10 However, as a relatively new protocol, the ecosystem of available MCP connectors is dynamic and fragmented. While numerous options for connecting to PostgreSQL exist, their quality, security, and feature sets vary dramatically, necessitating a careful evaluation before selection.12A critical finding from this evaluation is the significant security risk associated with the most easily discoverable connector. The mcp/postgres image on Docker Hub, which appears to be the official reference implementation from the Model Context Protocol maintainers, is both archived and contains a critical SQL injection vulnerability.13 A detailed security analysis from Datadog revealed that this vulnerability allows an attacker to bypass the intended read-only restrictions and execute arbitrary SQL statements, posing a severe threat to the integrity of the connected database.14 Despite being deprecated, this vulnerable package continues to see thousands of weekly downloads, indicating that many users may be unknowingly deploying a compromised component. Therefore, the most crucial best practice when selecting an MCP connector for PostgreSQL is to explicitly avoid this official reference implementation. The "best-of-breed" choice must be an actively maintained alternative that has addressed this vulnerability and offers a robust security posture.Comparative Analysis and RecommendationTo provide a clear, data-driven recommendation, the following table presents a comparative analysis of prominent MCP-PostgreSQL connectors. This matrix evaluates each option against criteria essential for a secure, functional, and maintainable deployment.Connector / ImageMaintainerTransport(s)Key FeaturesSecurity Notesmcp/postgresmodelcontextprotocolstdioBasic read-only query execution, schema inspection.Archived and Deprecated. Contains a critical SQL injection vulnerability. Should NOT be used.14crystaldba/postgres-mcpCrystalDBAstdio, sseRead/write modes, safe SQL parsing, query analysis, index recommendations, DB health checks, extension support (pg_stat_statements, hypopg).12Actively maintained. Configurable access control (read-only vs. unrestricted). Designed with security as a primary feature.12ahmedmustahid/postgres-mcp-serverahmedmustahidstdio, httpStateful, dual-transport implementation. Exposes database resources and tools.16Appears to be a more recent implementation. Security posture is less documented than CrystalDBA's offering.nihfix/postgres.mcpnihfixstdio, sseLightweight and efficient server designed for AI agent interaction.17Focuses on simplicity and performance. Less feature-rich compared to crystaldba/postgres-mcp.Based on this comprehensive analysis, the recommended connector is crystaldba/postgres-mcp.This recommendation is justified by several key factors:Superior Security Posture: The connector is actively maintained and has been designed with security as a core principle. It offers configurable access modes, allowing the deployment to enforce a strict read-only policy (restricted mode), which is essential for interacting with production or sensitive data. This directly mitigates the risks identified in the reference implementation.12Advanced Feature Set: crystaldba/postgres-mcp extends far beyond simple query execution. It provides a suite of advanced tools for database performance analysis, including the ability to analyze query execution statistics, recommend optimal indexes, and perform comprehensive database health checks. These capabilities align with a professional DevOps and database administration mindset, enabling the AI agent to not only query data but also assist in maintaining and optimizing the database itself.15Deployment Flexibility and Maintainability: The connector provides a well-documented Docker image and supports both stdio and networked (sse) transports. This flexibility simplifies integration into a containerized architecture like the one being built. Its active development and clear documentation suggest a higher likelihood of long-term support and community engagement.12Integrating the Recommended Connector into Docker ComposeThe crystaldba/postgres-mcp connector will be integrated as a dedicated service named mcp-postgres within the docker-compose.yml file. This service will utilize the official crystaldba/postgres-mcp:latest Docker image.Configuration will be managed through environment variables, which will be sourced from the central .env file to maintain a clean separation of configuration and secrets. The service will be configured to start in Server-Sent Events (sse) mode, which provides a networked HTTP endpoint. This allows it to function as a persistent, discoverable service within the isolated Docker network.The mcp-postgres service will be attached to the same mcp-net custom bridge network as the LiteLLM proxy and the PostgreSQL database. This ensures secure, internal communication. The LiteLLM proxy will be able to connect to the MCP server at the stable address http://mcp-postgres:8686, where mcp-postgres is the service name resolved by Docker's internal DNS and 8686 is the default port exposed by the crystaldba/postgres-mcp container for SSE transport.15 This networked approach creates a decoupled, microservices-style architecture that is more robust and easier to manage than tightly coupled file-based or process-based integrations.Part III: Mastering MCP Server Registration Across All TransportsThis section provides a comprehensive guide to the mcp_settings configuration block within LiteLLM's config.yaml. It presents detailed, annotated examples for registering MCP servers using all three supported transport mechanisms—stdio, http, and sse—explaining the precise syntax and ideal use case for each.The mcp_settings Block: LiteLLM's Central Nervous System for ToolsThe mcp_settings key in the config.yaml file is the central point for registering all external MCP tool servers with the LiteLLM proxy.18 This configuration block informs the proxy which tool servers are available, how to connect to them, and which clients are authorized to use them. The structure is a list of server objects, allowing for the registration of multiple, distinct tool providers.18Each entry in the mcp_settings list is an object with several key properties:name: A unique, descriptive string that identifies this specific MCP server registration within LiteLLM.transport: Specifies the communication protocol. Supported values are stdio, http (for Streamable HTTP), and sse (for Server-Sent Events). If omitted, it defaults to sse.18url: Required for http and sse transports, this is the network endpoint of the MCP server.command: Required for the stdio transport, this is the executable command that LiteLLM will run to start the tool server process.api_keys: This is a crucial list of LiteLLM virtual keys. Only requests made with an API key present in this list will be able to discover and use the tools provided by this MCP server. This mechanism provides granular, key-based access control for all integrated tools.18By correctly configuring this block, the LiteLLM proxy acts as a secure gateway, discovering tools from various sources and translating their schemas into a format compatible with any supported LLM, such as the OpenAI function-calling format.18 This allows models that have no native MCP awareness to leverage the entire ecosystem of MCP tools in a governed and secure manner.Registering Networked MCP Servers: http and sseThe http and sse transports are the standard and recommended methods for registering MCP servers that run as persistent, networked services. This is the ideal pattern for tools deployed as separate Docker containers, as it promotes a clean separation of concerns and leverages the robust networking capabilities of the container orchestrator. From LiteLLM's configuration perspective, Streamable HTTP (http) and Server-Sent Events (sse) are configured identically, requiring only the server's URL.18This approach is perfectly suited for integrating the recommended mcp-postgres container. The container runs as a long-lived process, exposing its services on a network port within the isolated Docker network. LiteLLM connects to it as a client, just as it would with any remote API.Annotated config.yaml Example for a Networked MCP Server:YAML# /path/to/your/config.yaml

mcp_settings:
  # Each entry in this list defines one MCP server connection.
  - name: "mcp_postgres_main"  # A unique, human-readable identifier for this server.
    # For networked services, specify the URL. Docker's internal DNS will
    # resolve the service name 'mcp-postgres' to the correct container IP.
    # The port '8686' is the default exposed by the crystaldba/postgres-mcp image.
    url: "http://mcp-postgres:8686"
    # 'sse' is a common choice for MCP servers and is supported by our chosen connector.
    # 'http' is also a valid transport for many networked servers.
    transport: "sse"
    # This is the access control list. Only requests using a virtual key
    # listed here can access the tools from this server.
    api_keys: ["test-key-1234"]
This configuration is robust, scalable, and aligns with modern microservices architecture. It decouples the lifecycle of the LiteLLM proxy from the lifecycle of its tools. The mcp-postgres server can be updated, restarted, or scaled independently without requiring any changes to the LiteLLM container, as long as its network address remains stable within the Docker network.Registering Local Processes: stdio (The Advanced Use Case)The stdio (Standard Input/Output) transport is designed for a different paradigm. It allows LiteLLM to spawn an MCP server as a child process and communicate with it directly over the stdin and stdout streams.20 This method is ideal for lightweight, stateless, or command-line-based tools that do not need to run as persistent network daemons. For example, a simple script that performs a calculation or a filesystem operation could be effectively integrated using stdio.However, using stdio in a containerized environment without modifying the base LiteLLM Docker image introduces complexity. The executable specified in the command field must exist and be runnable from within the LiteLLM container's filesystem and process environment. This typically requires using Docker volumes to mount the script or binary into the container at a known path. This approach creates a tight coupling between the container and the host filesystem, making the deployment less portable and harder to manage compared to the networked approach.While stdio is a valid transport, a superior architectural pattern for nearly all use cases is to wrap even stdio-based tools in their own minimal, dedicated Docker containers and expose them over the internal network via http or sse. This encapsulates all of the tool's dependencies (e.g., a Node.js or Python runtime) and allows Docker Compose to manage its entire lifecycle, including health checks and automated restarts. This strategy maintains a clean separation of concerns and leverages the full power of container orchestration.For illustrative purposes, the following example demonstrates how a hypothetical stdio tool could be configured. This assumes that a script, list_files.sh, has been mounted into the LiteLLM container.Annotated config.yaml Example for a stdio MCP Server:YAML# This configuration assumes the following volume mount is defined for the
# litellm-proxy service in the docker-compose.yml file:
#
# volumes:
#   -./tools/list_files.sh:/usr/local/bin/list_files.sh:ro
#   -./tools:/tools:ro # Mount a directory for the script to operate on

mcp_settings:
  - name: "local_file_lister"
    # Specifies that LiteLLM should run a local command.
    transport: "stdio"
    # The full path to the executable *inside* the LiteLLM container.
    command: "/usr/local/bin/list_files.sh"
    # Optional arguments to pass to the command.
    args: ["/tools"]
    # Access control remains consistent across all transport types.
    api_keys: ["admin-key-5678"]
Given the user's goal of simplicity and stability while avoiding modifications to the base LiteLLM image, the strong recommendation is to exclusively use the networked transports (http/sse) for all MCP server integrations. This approach provides a more resilient, maintainable, and scalable architecture.Part IV: Final Configuration, Verification, and Operational ReadinessThis final section consolidates all architectural decisions and configurations into a complete set of deployment artifacts. It provides a detailed, step-by-step protocol for deploying the stack and verifying that every component is functioning correctly. The section concludes with instructions for connecting local network clients to the newly operational LiteLLM MCP Gateway and performing an end-to-end tool-call test.The Complete, Production-Ready Deployment ArtifactsThe following files represent the final, declarative state of the application stack. They are designed to be saved in a single project directory on the linuxserver.lan host.File 1: docker-compose.ymlThis file defines the three core services (postgres, mcp-postgres, litellm-proxy), their interdependencies, networking, and health checks. It is the master manifest for the entire deployment.YAML# docker-compose.yml
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
      test:
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
      # Connection string for the MCP connector to reach the database.
      # 'postgres' is the service name resolved by Docker's internal DNS.
      - DATABASE_URL=${MCP_POSTGRES_DATABASE_URL}
      # Start the server in SSE mode on port 8686.
      - MCP_TRANSPORT=sse
      - MCP_PORT=8686
      # Enforce read-only mode for safety.
      - MCP_ALLOW_WRITE=false
    
  litellm-proxy:
    image: ghcr.io/berriai/litellm:v1.77.3-stable
    container_name: mcp-litellm-proxy
    restart: unless-stopped
    networks:
      - mcp-net
    ports:
      - "4000:4000"
    depends_on:
      postgres:
        condition: service_healthy
      mcp-postgres:
        condition: service_started # mcp-postgres does not have a healthcheck, so we wait for start.
    volumes:
      -./config.yaml:/app/config.yaml:ro
    env_file:
      -./.env
    command: ["--config", "/app/config.yaml"]

networks:
  mcp-net:
    driver: bridge

volumes:
  postgres_data:
File 2: .envThis file stores all secrets and sensitive configuration variables. It must be created in the same directory as the docker-compose.yml file.Code snippet#.env - Environment variables for the LiteLLM MCP Gateway stack
#
# --- PostgreSQL Database Settings ---
# Credentials for the main PostgreSQL database instance.
POSTGRES_USER=litellm_admin
POSTGRES_PASSWORD=a_very_secure_password_placeholder
POSTGRES_DB=litellm_db

# --- LiteLLM Proxy Settings ---
# Database URL for LiteLLM's internal logging and key management.
# This uses the credentials defined above.
DATABASE_URL=postgresql://litellm_admin:a_very_secure_password_placeholder@postgres:5432/litellm_db

# Master Key for administering the LiteLLM proxy (e.g., generating virtual keys).
# MUST start with 'sk-'.
LITELLM_MASTER_KEY=sk-litellm-master-key-placeholder

# --- MCP Connector Settings ---
# Database URL for the mcp-postgres connector to use.
# This can point to the same database or a different one you want the LLM to access.
MCP_POSTGRES_DATABASE_URL=postgresql://litellm_admin:a_very_secure_password_placeholder@postgres:5432/litellm_db

# --- Optional LLM Provider API Keys ---
# Add any real LLM API keys here if you plan to use non-mock models.
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
File 3: config.yamlThis is the core configuration for the LiteLLM proxy itself.YAML# config.yaml

# This section defines general settings for the LiteLLM library.
litellm_settings:
  # Instructs LiteLLM to use the PostgreSQL database for logging, key management,
  # and cost tracking. The value is loaded from the.env file.
  database_url: ${DATABASE_URL}

# This section defines the LLM models available through the proxy.
model_list:
  - model_name: gpt-4o-mock # This is the user-facing alias for the model.
    litellm_params:
      # For initial testing, we use LiteLLM's built-in mock response generator.
      # This allows us to verify the proxy and tool setup without needing a real LLM API key.
      model: "mock-response"
      api_key: "not-needed-for-mock"

# This section defines the virtual API keys that clients will use to authenticate.
virtual_keys:
  - api_key: "test-key-1234"
    # This key is granted access to the mock model defined above.
    models: ["gpt-4o-mock"]
    # A user identifier for logging and tracking purposes.
    user: "lan-test-user"

# This section registers and configures MCP tool servers.
mcp_settings:
  - name: "mcp_postgres_main"
    # The URL points to the mcp-postgres service running in our Docker Compose stack.
    url: "http://mcp-postgres:8686"
    transport: "sse"
    # This grants access to the postgres tools for any client using 'test-key-1234'.
    api_keys: ["test-key-1234"]
Step-by-Step Deployment and Verification ProtocolEnvironment Preparation:Create a project directory (e.g., /home/administrator/projects/mcp-gateway).Inside this directory, create the three files: docker-compose.yml, .env, and config.yaml with the content provided above.Edit the .env file and replace all placeholder values (a_very_secure_password_placeholder, sk-litellm-master-key-placeholder) with strong, unique credentials.Set secure permissions for the secrets file: chmod 600.env.Launching the Stack:Navigate to the project directory in your terminal.Execute the command to build and start all services in the background: docker compose up -d.Health Verification:Wait approximately 30-60 seconds for the services to initialize.Run docker compose ps to check the status of all containers.Expected Outcome: All three services (mcp-postgres-db, mcp-postgres-connector, mcp-litellm-proxy) should show a STATUS of running. Crucially, the mcp-postgres-db service should also show (healthy) in its status, confirming that the database is fully operational.LiteLLM Endpoint and Tool Discovery Check:Execute the following curl command from the host machine to query the proxy's /models endpoint using the virtual key.Bashcurl http://localhost:4000/v1/models -H "Authorization: Bearer test-key-1234" | jq
Expected Outcome: A JSON object will be returned. The critical element to verify is the presence of a tools array within the gpt-4o-mock model definition. This array will be populated with the tools discovered from the mcp-postgres server (e.g., execute_sql, list_schemas, analyze_db_health). The presence of this array is the definitive confirmation that the LiteLLM MCP Gateway has successfully connected to the MCP connector and registered its tools.Client Configuration and End-to-End Tool-Call TestClient Setup:On any machine on the local network (e.g., where VS Code, Open-WebUI, or various CLIs are running), configure the tool to use the LiteLLM proxy.Endpoint URL / Base URL: http://linuxserver.lan:4000API Key: test-key-1234End-to-End Test Scenario:Using a configured client that supports tool-calling, submit a prompt designed to trigger a database interaction.Sample Prompt: "Using your tools, list all available schemas in the database."Verification Protocol:Observe Logs: In a terminal on the server, monitor the logs of the services in real-time: docker compose logs -f.LiteLLM Proxy Logs: The logs for mcp-litellm-proxy will show the incoming request, the LLM's (mock) response indicating a tool call for list_schemas, and the subsequent request being forwarded to the MCP server at http://mcp-postgres:8686.MCP Connector Logs: The logs for mcp-postgres-connector will show the incoming tool call request from LiteLLM and the corresponding SQL query it executes against the database.Final Client Output: The client will receive a final response containing the results of the tool call, which in this case will be a list of schemas in the PostgreSQL database (e.g., public, information_schema). This confirms the entire request-tool-response chain is fully functional.Database Audit Log: As a final verification, connect to the PostgreSQL database and inspect the LiteLLM logs table to confirm the transaction was recorded.Bash# Connect to the running postgres container
docker compose exec -it postgres psql -U litellm_admin -d litellm_db

# Inside psql, run the query
SELECT start_time, model, user_id, cost, request_tags->'tool_calls' as tool_calls FROM litellm_logs ORDER BY start_time DESC LIMIT 1;
Expected Outcome: The query will return a record of the API call, including the tool call details in the tool_calls column, confirming that the persistence and auditing layer is working correctly. This completes the verification of the resilient, secure, and fully operational LiteLLM MCP Gateway.
