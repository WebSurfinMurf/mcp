# MCP Proxy Fix and Simplification Plan

**Date**: 2025-09-25
**Author**: Gemini
**Objective**: To establish a simple, reliable, and secure proxy for a single MCP service (`mcp-filesystem`) and verify its functionality using a command-line interface. This plan intentionally discards the complex, non-functional prior attempts in favor of a clean, maintainable, and reproducible solution.

## 1. Guiding Principles

Based on the issues identified in the `gemini`, `codex`, and `claude` reports, this plan will strictly adhere to the following principles:

- **Simplicity Over Complexity**: We will build the simplest possible thing that works. The monolithic, multi-service gateway approach is abandoned.
- **Reproducibility First**: All components will be defined in `docker-compose.yml` and deployment scripts. No manual `docker run` commands will be used for persistent services.
- **Security by Default**: Secrets will be managed exclusively through environment files stored in the `/home/administrator/secrets/` directory, with appropriate permissions. No secrets will be hardcoded in configs, scripts, or documentation.
- **Incremental Validation**: We will get one service working end-to-end before considering adding more.

## 2. The Plan

### Phase 1: A New, Simple Proxy Service

We will create a new, minimal proxy server instead of attempting to fix the old ones.

1.  **Create Project Directory**: A new directory will be created for the proxy to ensure a clean slate: `/home/administrator/projects/mcp-proxy`.
2.  **Implement Proxy Logic**: A minimal `Node.js` application using `express` and `http-proxy-middleware` will be written.
    - It will have a single purpose: Authenticate a request via an API key and proxy it to the upstream `mcp-filesystem` service.
    - The API key and the upstream URL will be read from environment variables.
3.  **Create `Dockerfile`**: A simple `Dockerfile` will be created to containerize the Node.js application.
4.  **Create `deploy.sh`**: A deployment script will be created to manage the lifecycle of the proxy.

### Phase 2: Deploy and Configure the Test Target (`mcp-filesystem`)

We need a working MCP service to test against. We will ensure `mcp-filesystem` is running correctly.

1.  **Locate Deployment Script**: Find the existing `deploy.sh` or `docker-compose.yml` for the `mcp-filesystem` service within `/home/administrator/projects/mcp/filesystem/`.
2.  **Verify Configuration**: Ensure it runs on a dedicated Docker network (e.g., `mcp-net`) and does not expose ports to the host directly. Its internal hostname will be `mcp-filesystem`.
3.  **Deploy Service**: Run its deployment script to ensure a clean, running instance is available for the proxy to target.

### Phase 3: Orchestrate and Secure the Proxy

This phase connects the proxy to the target service in a secure and reproducible manner.

1.  **Create `docker-compose.yml`**: Inside `/home/administrator/projects/mcp-proxy`, a `docker-compose.yml` file will define the `mcp-proxy` service.
    - The proxy will expose a port to the host (e.g., `4002:4002`) for testing.
    - It will be connected to the `mcp-net` network to communicate with the upstream `mcp-filesystem` service.
2.  **Create Secret File**: A secret file will be created at `/home/administrator/secrets/mcp-proxy.env`.
    - It will contain `PROXY_API_KEY` for authenticating clients and `UPSTREAM_FILESYSTEM_URL=http://mcp-filesystem:8000` (or the correct internal port).
    - Permissions will be set to `600`.
3.  **Update `deploy.sh`**: The deployment script for the proxy will use `docker-compose` and the `--env-file` flag to launch the service.

### Phase 4: CLI Integration and End-to-End Test

The final step is to configure a client to use the new proxy and verify that a tool call works.

1.  **Configure Gemini CLI**: I will create a configuration file for the Gemini CLI (e.g., `~/.config/gemini/mcp.json`) that defines the `filesystem` service.
    - **URL**: `http://localhost:4002`
    - **API Key**: The value of `PROXY_API_KEY` from the secrets file.
2.  **Perform Test**: I will execute a command to test the integration.
    - The command will be a simple, read-only operation, such as listing files in the root project directory.
    - Example: `gemini mcp filesystem list_files --path /home/administrator/projects`
3.  **Verify Result**: The expected output is a JSON object containing the list of files, confirming that the entire chain (CLI -> Proxy -> Filesystem Service) is working.

## 4. Success Criteria

This plan will be considered a success when:

- A single, simple proxy service is running via `docker-compose`.
- The proxy securely routes an authenticated request to the `mcp-filesystem` container.
- A command executed from the Gemini CLI successfully returns data from the `mcp-filesystem` service.
- The entire setup is reproducible from the scripts and configuration files created, with no manual steps required.
