# LiteLLM MCP & Aggregation Reference

## Overview
LiteLLM is a lightweight gateway that normalizes access to multiple large language models (LLMs) and tool providers behind a single OpenAI-compatible API surface. The same process can also act as a Model Context Protocol (MCP) hub, launching upstream MCP servers (stdio or HTTP) and exposing them via `/mcp/*` endpoints. This document summarizes the capabilities that matter when LiteLLM is used to aggregate LLMs, surface MCP tools, and serve remote clients such as Codex CLI, Open WebUI, or VS Code running on the same network (including Windows hosts).

## LLM Aggregation Capabilities
- Wraps dozens of vendors (OpenAI, Anthropic, Google, Azure, open-source runtimes) behind the OpenAI REST schema (`/v1/chat/completions`, `/v1/responses`).
- Supports per-model configuration: API keys, request/response transforms, temperature limits, max tokens, and provider-specific parameters (e.g., Anthropic `thinking`, Google `safety_settings`).
- Routing strategies include round-robin (`simple-shuffle`), least-busy, latency-aware, or custom Python hooks; fallbacks and cascading retries may be enabled per model group.
- Provides cost tracking, rate limiting, caching (Redis/Postgres), streaming responses, and structured logging (JSON) for observability pipelines.
- Accepts a `master_key` (or scoped API keys) enforced via the `Authorization: Bearer <key>` header for every API call.

## MCP Gateway Functionality
- Registers upstream servers under `mcp_servers` in `config.yaml` with transports `stdio` (spawn a subprocess) or `http` (delegate to remote URL).
- Launches each server with optional `env`, `args`, and human-readable `description` fields; secrets are injected through environment variables or LiteLLM’s secret store.
- Maintains alias mappings (`litellm_settings.mcp_aliases`) so clients can reference tools by friendly names.
- Exposes two primary endpoints:
  - `POST /mcp/tools` – Server-Sent Events (SSE) stream that returns tool catalogs for the MCP servers listed in the `x-mcp-servers` header.
  - `POST /mcp/invoke` – Streams tool call execution payloads back to the client once LiteLLM is wired to an execution layer (planned extension). Currently LiteLLM forwards tool responses but does not execute nested actions for you.
- Enforces the same auth model as standard LLM traffic; requests lacking the `Bearer` prefix or the `x-mcp-servers` selector are rejected.

## Configuration Surfaces (key sections in `config.yaml`)
- `model_list`: declarative map of logical model names to provider-specific parameters.
- `litellm_settings`: global behavior (retry budget, timeout, log format, parameter dropping, MCP alias definitions).
- `router_settings`: choose routing or fallbacks for aggregated providers.
- `general_settings`: authentication, persistence, admin UI credentials, telemetry, CORS origins.
- `mcp_servers`: stdio/HTTP registrations for MCP tool backends, including command path, arguments, allowed filesystem paths, and future HTTP services.

## Authentication & Security
- API keys are supplied via environment (`os.environ/VARIABLE`) or secret files; LiteLLM validates every REST and MCP request against the configured keys.
- Supports per-client keys (`scoped_key=true`) with rate limits and quota tracking; master keys remain for administrative traffic.
- CORS controls allow explicit origins for browser-based clients (e.g., Open WebUI, custom dashboards).
- When exposing MCP endpoints, ensure TLS termination (Traefik/NGINX) and network ACLs restrict access to trusted subnets.

## Client Connectors & Remote Access
### Codex CLI
- Configure `~/.codex/config.toml` (Linux/macOS) or `%APPDATA%\codex\config.toml` (Windows) to point `api_base` at `http://<litellm-host>/mcp/` and include `Authorization = "Bearer <key>"` as well as `extra_headers = { "x-mcp-servers" = "mcp_postgres,mcp_filesystem" }`.
- For Windows machines on the same LAN, ensure the host name (e.g., `litellm.linuxserver.lan`) resolves via DNS or hosts file and that local firewalls allow outbound HTTP/HTTPS.

### Open WebUI
- Set `OPENAI_API_BASE_URL` (or UI equivalent) to `http://<litellm-host>/v1` so chat requests flow through LiteLLM.
- Provide the LiteLLM API key in `OPENAI_API_KEY`; Open WebUI can then call `/mcp/tools` by passing the same key and `x-mcp-servers` header when MCP support is enabled in the UI.

### VS Code (or other MCP-aware IDEs)
- Populate an `mcp_servers.json` (MCP extension convention) with entries targeting LiteLLM’s `/mcp/` endpoint, specifying the Authorization header and desired server aliases.
- On Windows, store secrets in Credential Manager or the VS Code `settings.json` secret store; avoid embedding keys directly in repo files.
- Remote tunnels must allow SSE traffic; ensure enterprise proxies do not strip the `x-mcp-servers` header.

## Tool Call Flow & Limitations
1. Client authenticates via Bearer token and lists desired backends in `x-mcp-servers`.
2. LiteLLM streams the tool catalog (SSE) gathered from each upstream MCP server.
3. Client selects a tool; invocation currently relays request/response payloads but assumes the client (or a downstream orchestrator) handles side-effectful execution.
4. Future enhancements add automatic execution, richer error propagation, and multi-hop tool orchestration.

## Operational Considerations
- Deploy LiteLLM behind Traefik/NGINX for TLS, hostname routing (internet vs LAN), and optional OAuth2 proxies.
- Persist usage data to Postgres by setting `general_settings.database_url`; enables dashboards and audit trails.
- Log aggregation: enable `json_logs` to integrate with Loki/ELK; adjust `log_level` per environment.
- Monitor performance (requests/sec, latency, error rate) to tune routing strategies or spin up additional replicas.
- Keep upstream MCP binaries unmodified; upgrades are handled by updating the package versions outside of LiteLLM.

This reference should serve as the starting point for configuring LiteLLM as a unified LLM and MCP gateway and for onboarding remote tools or clients on the same network.
