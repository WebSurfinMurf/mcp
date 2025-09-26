# MCP-Proxy Connection Failure Analysis

## Executive Summary

The `TBXark/mcp-proxy` Docker container is consistently returning an `HTTP 404 Not Found` error for a configured route. This issue persists even after verifying the health of the upstream service and trying numerous configurations on the proxy itself. The failure has been confirmed with both `curl` and a dedicated Python script, isolating the fault to the proxy. The Claude Code CLI, which was the initial client, is not the cause of the failure.

## System Components

1.  **Upstream Service:** `crystaldba/postgres-mcp`
    *   **Container Name:** `mcp-postgres`
    *   **Network:** `mcp-net`
    *   **Listening:** Port `8686` inside the Docker network.
    *   **Exposed to Host:** Port `48010`.
    *   **Authentication:** None.

2.  **Proxy Service:** `ghcr.io/tbxark/mcp-proxy:v0.39.1`
    *   **Container Name:** `mcp-proxy`
    *   **Network:** `mcp-net`
    *   **Listening:** Port `9090` inside the Docker network.
    *   **Exposed to Host:** Port `9090`.
    *   **Authentication:** Configured for a bearer token (`changeme-token`).

3.  **Client:** Claude Code CLI (and diagnostic scripts).
    *   **Target URL:** `http://localhost:9090/servers/postgres/sse`

## Factual Findings & Diagnostic Steps

The following tests were performed, and the results are repeatable.

### 1. Upstream Service (`mcp-postgres`) is Healthy

A direct connection to the `mcp-postgres` container from within the Docker network was successful.

*   **Command:** `docker run --rm --network=mcp-net curlimages/curl:latest -i --max-time 10 http://mcp-postgres:8686/sse`
*   **Result:** `HTTP/1.1 200 OK`. The service returned SSE data as expected.

A direct connection from the host machine via the exposed port was also successful using the Claude Code CLI.

*   **CLI Command:** `claude mcp add-json postgres-direct '{"type": "sse", "url": "http://localhost:48010/sse"}'`
*   **Result:** The `postgres-direct` server shows as `✔ connected` in the `/mcp` menu.

**Conclusion:** The upstream `mcp-postgres` service is functioning correctly and is accessible.

### 2. Proxy Service (`mcp-proxy`) is Unresponsive

Multiple tests from the host machine to the `mcp-proxy` have failed.

*   **Test 1: `curl` with Authentication**
    *   **Command:** `curl -i --max-time 5 -H "Authorization: Bearer changeme-token" http://localhost:9090/servers/postgres/sse`
    *   **Result:** `HTTP/1.1 404 Not Found`.

*   **Test 2: Python Script with Authentication**
    *   **Script:** A `requests`-based script was created to simulate the client.
    *   **Result:** `Status Code: 404`.

*   **Test 3: Disabling Authentication**
    *   The `authTokens` line was removed from the proxy's `config.json` and the container was restarted.
    *   The Python script was modified to send no `Authorization` header.
    *   **Result:** `Status Code: 404`.

### 3. Proxy Logs Show No Activity

Crucially, during all of the failed `curl` and Python script tests against the `mcp-proxy`, **no new log entries were generated** in the proxy's container logs. The logs show a successful startup and connection to the upstream `mcp-postgres` service, but no incoming requests are ever logged.

## Final, Confirmed State

*   The `mcp-postgres` service is healthy and reachable.
*   The `mcp-proxy` service starts successfully and reports a connection to the upstream service in its logs.
*   All HTTP requests from the host machine to the proxy's configured SSE route (`/servers/postgres/sse`) result in an `HTTP 404 Not Found`.
*   The proxy does not log these incoming 404 requests, indicating a failure happening before the request reaches the logging and routing logic.
*   The issue is independent of authentication.
*   The issue persists across container restarts and full container recreation.
