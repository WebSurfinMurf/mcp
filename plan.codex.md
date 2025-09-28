# Feedback on MCP Service Enablement Plan (No Proxy)

## Positives
- 👍 Clearly states the no-proxy requirement and keeps stdio bridges intact for Codex support.
- 👍 Service-by-service sequencing with admin validation checkpoints matches the desired workflow.
- 👍 Phase 1 focuses on `mcp-filesystem`, ensuring a proven template before touching other services.
- 👍 Requirements capture the need for `/health`, `/sse`, `/mcp` endpoints and container DNS usage.

## Suggested Refinements
1. **Reinforce “No Proxy” Constraint**
   - Call out explicitly that the existing `proxy/` directory should remain unused for this rollout.
2. **Stdio Parity Check**
   - Add a reminder to re-run a quick stdio smoke test after each redeploy so we don’t break the current Codex flow.
3. **Claude CLI Commands**
   - Note that the registration commands must run from the host with Claude CLI configured; add a brief reminder to verify `claude mcp list` after each add/remove.
4. **Testing Matrix**
   - Consider adding a short checklist per service (Claude SSE command, stdio command, health curl) to make validation repeatable.

## All Clear
- ✅ Plan satisfies the direct stdio + SSE requirement.
- ✅ No MCP proxy usage anywhere in the workflow.
- ✅ Ready to begin with the `mcp-filesystem` phase once adjustments (if any) are applied.

_Last reviewed: 2025-09-27 (Codex)_
