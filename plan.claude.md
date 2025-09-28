# MCP Service Enablement Plan - Claude Code Feedback

## Overall Assessment

**👍 Strengths:**
- Clear phase-by-phase approach with admin validation checkpoints
- Maintains backward compatibility by preserving stdio bridges
- Direct service integration without proxy complexity
- Proper container networking using Docker DNS
- Conservative rollout minimizing risk

**⚠️ Areas for Clarification:**

### 1. **Container DNS Registration Issues**
**Problem**: The plan assumes `http://mcp-filesystem:9073/mcp/sse` will work, but this creates a networking mismatch.

**Current Reality**:
- Containers expose ports to localhost (127.0.0.1:9073)
- Claude Code CLI runs on host, not in Docker network
- Docker DNS names only resolve within container networks

**Recommended Fix**:
```bash
# Phase 1 registration should use:
claude mcp add filesystem http://localhost:9073/sse --transport sse --scope user

# NOT: http://mcp-filesystem:9073/mcp/sse
```

### 2. **SSE Endpoint Path Inconsistency**
**Current Implementation**:
- filesystem: `/sse` (confirmed working)
- fetch: `/fetch/sse` (confirmed working)
- postgres: `/sse` (confirmed working)

**Plan Assumption**: All services use `/mcp/sse`

**Recommendation**: Audit actual endpoint paths before registration. The plan should use existing working endpoints, not assume `/mcp/sse`.

### 3. **Missing Prerequisites Check**
**Gap**: No verification that Claude Code CLI is properly installed and configured.

**Suggested Addition**:
```bash
# Phase 0: Environment Validation
- Verify `claude mcp list` command works
- Check ~/.config/claude/mcp-settings.json exists
- Confirm Claude CLI version supports SSE transport
```

### 4. **Incomplete Service Status**
**Current State** (from investigation):
- ✅ filesystem: Full SSE support (ready)
- ✅ fetch: Full SSE support (already registered)
- ✅ postgres: Full SSE support (ready)
- ⚠️ minio, n8n, playwright, timescaledb: SSE stubs only

**Plan Improvement**: Start with **three working services** (filesystem, postgres) before implementing SSE for stub services.

## Revised Implementation Sequence

### **Phase 0: Baseline Validation**
1. Verify Claude CLI functionality: `claude mcp list`
2. Test existing fetch service: `claude --no-web -c "Use fetch to check status"`
3. Document current working state

### **Phase 1: Register Working SSE Services**
**Priority Order**:
1. filesystem (confirmed SSE working)
2. postgres (confirmed SSE working)

**Registration Commands**:
```bash
# Remove any existing registrations
claude mcp remove filesystem --scope user || true
claude mcp remove postgres --scope user || true

# Add SSE-enabled services
claude mcp add filesystem http://localhost:9073/sse --transport sse --scope user
claude mcp add postgres http://localhost:48010/sse --transport sse --scope user
```

### **Phase 2-5: Implement SSE for Stub Services**
Follow plan as written, but:
- Use localhost URLs for registration
- Verify actual endpoint paths before registration
- Copy exact SSE implementation from filesystem service

## **Critical Corrections Needed**

### **Container Networking Reality**
```yaml
# Current working configuration:
services:
  mcp-filesystem:
    ports:
      - "127.0.0.1:9073:8000"  # Host access via localhost:9073
    networks:
      - default  # Internal container DNS: mcp-filesystem
```

**From Host (Claude CLI)**:
- ✅ `http://localhost:9073/sse` (works)
- ❌ `http://mcp-filesystem:9073/sse` (fails - no host access to Docker DNS)

**From Container**:
- ✅ `http://mcp-filesystem:8000/sse` (internal communication)
- ❌ `http://mcp-filesystem:9073/sse` (wrong port for internal)

### **Service-Specific Endpoint Verification**
Before registration, confirm actual endpoints:
```bash
# Test actual endpoints
curl -s http://localhost:9073/health     # filesystem health
curl -s http://localhost:48010/sse       # postgres SSE (will timeout - expected)
curl -s http://localhost:9074/health     # n8n health
```

## **Risk Mitigation Suggestions**

1. **Start with Known Working Services**: Register filesystem and postgres first (confirmed SSE support)
2. **Validate Endpoints Before Registration**: Test health and SSE endpoints before `claude mcp add`
3. **Incremental Testing**: Test each service individually with simple commands
4. **Rollback Plan**: Document how to revert to stdio bridges if SSE fails

## **Documentation Standards**

**Each service CLAUDE.md should document**:
- Confirmed working endpoint URLs (localhost-based)
- Exact registration commands that work
- Test commands that verify functionality
- Known limitations or issues

## **Final Recommendation**

The plan is solid but needs **immediate corrections** for:
1. **Use localhost URLs** for all Claude CLI registrations
2. **Verify actual SSE endpoint paths** before implementation
3. **Start with working services** (filesystem, postgres) before implementing stubs
4. **Add prerequisite validation** for Claude CLI setup

With these corrections, the phased approach will work reliably and provide clear progress checkpoints.

---
**Review Date**: 2025-09-28
**Status**: Ready for implementation with corrections
**Priority**: Fix networking assumptions before Phase 1