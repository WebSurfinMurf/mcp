# Centralized LangChain MCP Server Implementation Plan

**Project**: Centralized MCP Tool Server
**Date**: 2025-09-13
**Status**: Ready for Implementation
**Architecture**: LangChain + LangServe + OAuth2 Proxy

## Executive Summary

This plan implements a centralized MCP (Model Context Protocol) server that replaces the current distributed MCP approach with a single Python-based LangChain service. The server will provide both agent endpoints and direct tool access, integrate with existing infrastructure (PostgreSQL, Minio, LiteLLM), and follow established security and logging patterns.

## Architecture Overview

```
User → Traefik → OAuth2 Proxy → LangChain Server → Backend Services
                      ↓              ↓
                  Keycloak SSO    PostgreSQL
                                  Minio S3
                                  LiteLLM
```

### Key Design Decisions
1. **Technology Stack**: Python + LangChain + LangServe + FastAPI
2. **Authentication**: OAuth2 Proxy + Keycloak SSO (following existing pattern)
3. **Tool Implementation**: Native Python tools (no STDIO/SSE wrappers)
4. **Deployment**: Docker Compose with multi-network connectivity
5. **Logging**: Structured JSON to stdout for Promtail/Loki integration

## Implementation Phases

### Phase 1: Project Structure Setup

#### 1.1 Create Directory Structure
```bash
mkdir -p /home/administrator/projects/mcp/langchain/app
cd /home/administrator/projects/mcp/langchain
```

#### 1.2 Environment Configuration
Create `.env` file:
```env
# Domain Configuration
DOMAIN=ai-servicers.com
ADMIN_EMAIL=administrator@ai-servicers.com

# Service Connection Endpoints
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
LITELLM_URL=http://litellm:4000
MINIO_ENDPOINT_URL=http://minio:9000

# Credential References (from secrets files)
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=${POSTGRES_DB}
MINIO_ROOT_USER=${MINIO_ROOT_USER}
MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD}

# Derived Connection Strings
POSTGRES_CONNECTION_STRING=postgresql+psycopg2://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}

# OAuth2 Proxy Configuration (to be configured in Phase 2)
OAUTH2_PROXY_CLIENT_ID=mcp-server
OAUTH2_PROXY_CLIENT_SECRET=CHANGE_ME_IN_PHASE_2
OAUTH2_PROXY_COOKIE_SECRET=CHANGE_ME_IN_PHASE_2

# Application Settings
LOG_LEVEL=INFO
AGENT_MODEL=claude-3-5-sonnet-20241022
```

#### 1.3 Python Dependencies
Create `app/requirements.txt` (using latest stable versions as of September 2025):
```txt
langchain>=0.2.0
langserve>=0.2.0
langchain-community>=0.2.0
litellm>=1.44.0
psycopg2-binary>=2.9.9
boto3>=1.35.0
uvicorn>=0.30.0
fastapi>=0.110.0
pydantic>=2.8.0
python-json-logger>=2.0.7
```

### Phase 2: Application Development

#### 2.1 Main Application Code
Create `app/main.py`:
```python
"""
Centralized LangChain MCP Server
Provides unified tool access via agent and direct API endpoints
"""

import os
import logging
import sys
import psycopg2
import boto3
from botocore.client import Config
from pythonjsonlogger import jsonlogger
from langchain_core.tools import tool
from langchain_community.chat_models import ChatLiteLLM
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langserve import add_routes
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

# Structured JSON Logging Setup
log = logging.getLogger()
logHandler = logging.StreamHandler(sys.stdout)
formatter = jsonlogger.JsonFormatter(
    '%(asctime)s %(name)s %(levelname)s %(message)s %(module)s %(funcName)s'
)
logHandler.setFormatter(formatter)
log.addHandler(logHandler)
log.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# FastAPI Application
app = FastAPI(
    title="Centralized LangChain MCP Server",
    version="1.0.0",
    description="Unified MCP tool server for ai-servicers.com infrastructure",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Health Check Endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "mcp-server",
        "version": "1.0.0"
    }

# ====== MCP TOOLS IMPLEMENTATION ======

@tool
def postgres_query(query: str) -> str:
    """Execute read-only PostgreSQL query and return results"""
    log.info("Executing PostgreSQL query", extra={'query_type': 'read', 'query': query[:100]})

    # Security: Enforce read-only queries
    dangerous_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE', 'GRANT', 'REVOKE']
    if any(keyword in query.upper() for keyword in dangerous_keywords):
        log.warning("Blocked non-read query attempt", extra={'query': query[:100]})
        return "Error: Only read-only SELECT queries are allowed for security."

    try:
        conn = psycopg2.connect(os.environ["POSTGRES_CONNECTION_STRING"])
        cur = conn.cursor()
        cur.execute(query)

        # Handle different query types
        if cur.description:
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            result = {
                "columns": columns,
                "rows": rows,
                "count": len(rows)
            }
        else:
            result = {"message": "Query executed successfully", "rows_affected": cur.rowcount}

        cur.close()
        conn.close()

        log.info("PostgreSQL query completed", extra={'rows_returned': result.get('count', 0)})
        return str(result)

    except Exception as e:
        log.error("PostgreSQL query failed", exc_info=True, extra={'error': str(e)})
        return f"Database error: {str(e)}"

@tool
def minio_list_objects(bucket_name: str, prefix: str = "") -> str:
    """List objects in MinIO S3 bucket with optional prefix filter"""
    log.info("Listing MinIO objects", extra={'bucket': bucket_name, 'prefix': prefix})

    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=os.environ["MINIO_ENDPOINT_URL"],
            aws_access_key_id=os.environ["MINIO_ROOT_USER"],
            aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
            config=Config(signature_version='s3v4')
        )

        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        objects = []

        for obj in response.get('Contents', []):
            objects.append({
                'key': obj['Key'],
                'size': obj['Size'],
                'last_modified': obj['LastModified'].isoformat()
            })

        result = {
            "bucket": bucket_name,
            "prefix": prefix,
            "objects": objects,
            "count": len(objects)
        }

        log.info("MinIO list completed", extra={'objects_found': len(objects)})
        return str(result)

    except Exception as e:
        log.error("MinIO operation failed", exc_info=True, extra={'error': str(e)})
        return f"MinIO error: {str(e)}"

@tool
def minio_get_object(bucket_name: str, object_key: str) -> str:
    """Get object content from MinIO S3 bucket (text files only)"""
    log.info("Getting MinIO object", extra={'bucket': bucket_name, 'key': object_key})

    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=os.environ["MINIO_ENDPOINT_URL"],
            aws_access_key_id=os.environ["MINIO_ROOT_USER"],
            aws_secret_access_key=os.environ["MINIO_ROOT_PASSWORD"],
            config=Config(signature_version='s3v4')
        )

        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        content = response['Body'].read().decode('utf-8')

        log.info("MinIO object retrieved", extra={'content_length': len(content)})
        return content

    except Exception as e:
        log.error("MinIO get object failed", exc_info=True, extra={'error': str(e)})
        return f"MinIO error: {str(e)}"

# ====== LANGCHAIN AGENT SETUP ======

# Available tools
tools = [postgres_query, minio_list_objects, minio_get_object]

# LiteLLM client with configurable model
llm = ChatLiteLLM(
    model=os.environ.get("AGENT_MODEL", "claude-3-5-sonnet-20241022"),
    openai_api_base=os.environ["LITELLM_URL"],
    temperature=0.1
)

# Agent prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful assistant with access to database and storage tools.

Available tools:
- postgres_query: Execute read-only SQL queries against PostgreSQL
- minio_list_objects: List files in MinIO S3 buckets
- minio_get_object: Get content of text files from MinIO S3 buckets

Always provide clear, structured responses and explain what you're doing."""),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Create agent
agent = create_openai_functions_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=5
)

# Add agent endpoint
add_routes(app, agent_executor, path="/agent")

# ====== DIRECT TOOL API ======

class ToolRequest(BaseModel):
    input: Dict[str, Any]  # Changed to dictionary to support multiple arguments

@app.post("/tools/{tool_name}")
async def execute_tool(tool_name: str, request: ToolRequest):
    """Execute a specific tool directly with dictionary input"""
    log.info("Direct tool execution", extra={'tool': tool_name, 'input_args': list(request.input.keys())})

    # Find the requested tool
    tool_map = {tool.name: tool for tool in tools}

    if tool_name not in tool_map:
        available_tools = list(tool_map.keys())
        log.warning("Tool not found", extra={'requested_tool': tool_name, 'available_tools': available_tools})
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{tool_name}' not found. Available tools: {available_tools}"
        )

    try:
        tool = tool_map[tool_name]
        # LangChain tools can accept dictionary input
        result = tool.invoke(request.input)

        return {
            "tool": tool_name,
            "input": request.input,
            "result": result,
            "status": "success"
        }

    except Exception as e:
        log.error("Tool execution failed", exc_info=True, extra={'tool': tool_name, 'error': str(e)})
        raise HTTPException(
            status_code=500,
            detail=f"Tool execution failed: {str(e)}"
        )

@app.get("/tools")
async def list_tools():
    """List all available tools"""
    tool_info = []
    for tool in tools:
        tool_info.append({
            "name": tool.name,
            "description": tool.description,
            "args_schema": tool.args if hasattr(tool, 'args') else {}
        })

    return {
        "tools": tool_info,
        "count": len(tool_info)
    }

# ====== APPLICATION STARTUP ======

@app.on_event("startup")
async def startup_event():
    log.info("MCP Server starting up", extra={
        'tools_count': len(tools),
        'postgres_host': os.environ.get('POSTGRES_HOST'),
        'litellm_url': os.environ.get('LITELLM_URL'),
        'minio_endpoint': os.environ.get('MINIO_ENDPOINT_URL')
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Phase 3: Container Configuration

#### 3.1 Docker Compose Configuration
Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  mcp-server:
    image: python:3.11-slim-bookworm
    container_name: mcp-server
    restart: unless-stopped
    volumes:
      - ./app:/app:ro
    working_dir: /app
    command: >
      sh -c "pip install --no-cache-dir -r requirements.txt &&
             uvicorn main:app --host 0.0.0.0 --port 8000"
    env_file:
      - .env
      - /home/administrator/secrets/postgres.env
      - /home/administrator/secrets/minio.env
    networks:
      - litellm-net
      - postgres-net
      - traefik-proxy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  mcp-server-auth-proxy:
    image: quay.io/oauth2-proxy/oauth2-proxy:latest
    container_name: mcp-server-auth-proxy
    restart: unless-stopped
    depends_on:
      - mcp-server
    networks:
      - traefik-proxy
      - keycloak-net
    environment:
      # OAuth2 Proxy Configuration
      - OAUTH2_PROXY_HTTP_ADDRESS=0.0.0.0:4180
      - OAUTH2_PROXY_PROVIDER=keycloak-oidc
      - OAUTH2_PROXY_UPSTREAMS=http://mcp-server:8000

      # Keycloak Integration (verify realm - typically 'main' not 'master' for applications)
      - OAUTH2_PROXY_OIDC_ISSUER_URL=https://keycloak.ai-servicers.com/realms/main
      - OAUTH2_PROXY_REDIRECT_URL=https://mcp.ai-servicers.com/oauth2/callback

      # Authorization
      - OAUTH2_PROXY_ALLOWED_GROUPS=administrators
      - OAUTH2_PROXY_SCOPE=openid profile email groups

      # Security Settings
      - OAUTH2_PROXY_COOKIE_SECURE=true
      - OAUTH2_PROXY_COOKIE_HTTPONLY=true
      - OAUTH2_PROXY_COOKIE_SAMESITE=lax
      - OAUTH2_PROXY_COOKIE_EXPIRE=24h

      # From .env file
      - OAUTH2_PROXY_CLIENT_ID=${OAUTH2_PROXY_CLIENT_ID}
      - OAUTH2_PROXY_CLIENT_SECRET=${OAUTH2_PROXY_CLIENT_SECRET}
      - OAUTH2_PROXY_COOKIE_SECRET=${OAUTH2_PROXY_COOKIE_SECRET}

    labels:
      # Traefik Configuration
      - "traefik.enable=true"
      - "traefik.docker.network=traefik-proxy"
      - "traefik.http.routers.mcp-server.entrypoints=websecure"
      - "traefik.http.routers.mcp-server.rule=Host(`mcp.ai-servicers.com`)"
      - "traefik.http.routers.mcp-server.tls=true"
      - "traefik.http.routers.mcp-server.tls.certresolver=letsencrypt"
      - "traefik.http.services.mcp-server.loadbalancer.server.port=4180"

networks:
  litellm-net:
    external: true
  postgres-net:
    external: true
  traefik-proxy:
    external: true
  keycloak-net:
    external: true
```

### Phase 4: Security Configuration

#### 4.1 Keycloak Client Setup
1. Access Keycloak admin console: https://keycloak.ai-servicers.com
2. **Important**: Verify the correct realm - typically applications use 'main' realm, not 'master'
3. Navigate to appropriate realm → Clients → Create Client
4. Configure client:
   - **Client ID**: `mcp-server`
   - **Client Type**: OpenID Connect
   - **Client Authentication**: On
   - **Valid Redirect URIs**: `https://mcp.ai-servicers.com/oauth2/callback`
   - **Web Origins**: `https://mcp.ai-servicers.com`

#### 4.2 Generate OAuth2 Secrets
```bash
# Generate cookie secret
echo "OAUTH2_PROXY_COOKIE_SECRET=$(openssl rand -base64 32)" >> .env.local

# Update .env file with actual client secret from Keycloak
```

#### 4.3 Secret Management
Create service-specific secrets file:
```bash
# /home/administrator/secrets/mcp-server.env
OAUTH2_PROXY_CLIENT_ID=mcp-server
OAUTH2_PROXY_CLIENT_SECRET=your-keycloak-client-secret-here
OAUTH2_PROXY_COOKIE_SECRET=your-generated-cookie-secret
```

### Phase 5: Deployment & Testing

#### 5.1 Pre-Deployment Checks
```bash
# Verify networks exist
docker network ls | grep -E "(litellm-net|postgres-net|traefik-proxy|keycloak-net)"

# Check service connectivity
docker run --rm --network postgres-net postgres:15 pg_isready -h postgres -p 5432
docker run --rm --network litellm-net curlimages/curl curl -f http://litellm:4000/health
```

#### 5.2 Deployment
```bash
cd /home/administrator/projects/mcp/langchain

# Start services
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f
```

#### 5.3 Verification Steps
1. **Container Health**: `docker ps | grep mcp-server`
2. **Traefik Integration**: Check https://mcp.ai-servicers.com (should redirect to Keycloak)
3. **API Documentation**: https://mcp.ai-servicers.com/docs (after authentication)
4. **Health Check**: https://mcp.ai-servicers.com/health
5. **Tools List**: https://mcp.ai-servicers.com/tools

#### 5.4 Functional Testing
**Note**: All API endpoints are protected by OAuth2 proxy, so you'll need a valid Bearer token from Keycloak.

```bash
# First, obtain a valid JWT token from Keycloak (replace with actual token)
TOKEN="your-valid-keycloak-jwt-token-here"

# Test PostgreSQL tool (note: input is now a dictionary)
curl -X POST https://mcp.ai-servicers.com/tools/postgres_query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": {"query": "SELECT version(), current_database();"}}'

# Test MinIO tool with both bucket name and prefix
curl -X POST https://mcp.ai-servicers.com/tools/minio_list_objects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": {"bucket_name": "mcp-storage", "prefix": ""}}'

# Test Agent endpoint
curl -X POST https://mcp.ai-servicers.com/agent/invoke \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": {"input": "What databases are available?"}}'

# Alternative: Test via browser (will redirect to Keycloak for authentication)
# https://mcp.ai-servicers.com/docs - Interactive API documentation
```

### Phase 6: Integration & Monitoring

#### 6.1 Logging Integration
- Logs automatically collected by Promtail (no additional configuration needed)
- Structured JSON format for easy querying in Grafana/Loki
- Query examples: `{compose_service="mcp-server"}`, `{container="mcp-server"}`

#### 6.2 Monitoring Setup
- Health checks configured for container monitoring
- Traefik dashboard shows service status
- Grafana dashboards can be created for performance metrics

#### 6.3 Documentation Updates
Update the following files:
- `mcp/CLAUDE.md`: Document the new centralized approach
- `AINotes/SYSTEM-OVERVIEW.md`: Add MCP server to services list
- `AINotes/security.md`: Document new OAuth2 client configuration

## Success Criteria

- [ ] Service accessible at https://mcp.ai-servicers.com
- [ ] Keycloak authentication working
- [ ] PostgreSQL queries executing successfully
- [ ] MinIO operations working
- [ ] Agent conversations functional
- [ ] Structured logs appearing in Loki
- [ ] Health checks passing
- [ ] API documentation accessible

## Rollback Plan

If deployment fails:
1. Stop services: `docker-compose down`
2. Remove containers: `docker rm mcp-server mcp-server-auth-proxy`
3. Remove from Traefik: Containers auto-removed from routing
4. Remove Keycloak client (optional)
5. Clean up files: `rm -rf /home/administrator/projects/mcp/langchain`

## Post-Deployment Tasks

1. **Performance Tuning**: Monitor resource usage and adjust container limits
2. **Security Hardening**: Review OAuth2 proxy settings and add rate limiting
3. **Feature Expansion**: Add additional MCP tools as needed
4. **Documentation**: Create user guide for accessing the service
5. **Backup Strategy**: Include in regular backup procedures

## Security & Production Enhancements

This plan incorporates several critical security and production refinements:

### Security Improvements
- **Read-Only Query Enforcement**: PostgreSQL tool blocks destructive SQL commands (INSERT, UPDATE, DELETE, etc.)
- **Updated Dependencies**: Latest stable versions for security patches and performance improvements
- **Proper Authentication**: All curl examples include required Bearer token authentication
- **Keycloak Realm Verification**: Notes to confirm correct realm usage ('main' vs 'master')

### Production Readiness
- **Removed Development Features**: `--reload` flag removed from production uvicorn command
- **Configurable Model**: Agent model configurable via `AGENT_MODEL` environment variable
- **Enhanced Tool API**: Direct tool endpoints now accept dictionary inputs for multi-parameter tools
- **Comprehensive Testing**: Updated test commands with proper authentication and input formats

### API Improvements
- **Flexible Tool Invocation**: Tools can now receive complex parameter dictionaries
- **Better Error Handling**: Enhanced logging and error responses
- **Security Logging**: Blocked query attempts are logged for security monitoring

---

*Production-ready implementation plan with enterprise-grade security and flexibility*