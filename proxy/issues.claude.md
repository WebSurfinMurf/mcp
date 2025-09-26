# MCP Proxy Issues Report - Analysis of CODEX Implementation

**Date**: 2025-09-25
**Analyzer**: Claude
**Subject**: Issues found in CODEX's MCP proxy implementation

## Executive Summary

After analyzing the MCP proxy implementation by CODEX, I've identified **12 critical issues** that explain why the system isn't functioning properly. While the architecture is sound, there are significant operational and configuration problems that need immediate attention.

**Overall Status**: 🔴 **SYSTEM NON-FUNCTIONAL**
- Proxy responds with 404 on health endpoint
- SSE endpoints hang/timeout
- All bridge containers report "unhealthy"
- Multiple configuration inconsistencies

---

## 🚨 Critical Issues (Immediate Action Required)

### Issue #1: Health Check Failures Across All Containers
**Severity**: Critical
**Impact**: All containers marked "unhealthy" by Docker

**Evidence**:
```bash
$ docker ps --filter "name=mcp"
mcp-fetch-bridge        Up 37 hours (unhealthy)
mcp-filesystem-bridge   Up 37 hours (unhealthy)
mcp-proxy               Up 36 hours (unhealthy)
mcp-postgres            Up 47 hours (unhealthy)
```

**Root Cause**: Health check commands use Python urllib in containers that may not have Python installed, or wrong base images.

**Impact**: Docker considers all services failed, external orchestration will restart containers unnecessarily.

### Issue #2: Proxy Health Endpoint Returns 404
**Severity**: Critical
**Impact**: Central proxy not responding to basic health checks

**Evidence**:
```bash
$ curl -f http://localhost:9090/
curl: (22) The requested URL returned error: 404
```

**Root Cause**: TBXark/mcp-proxy may not expose a root health endpoint, health checks target wrong path.

**Impact**: Cannot verify proxy is operational, monitoring systems will report failures.

### Issue #3: SSE Endpoints Hanging/Non-Responsive
**Severity**: Critical
**Impact**: Core MCP functionality completely broken

**Evidence**:
```bash
$ curl -s http://localhost:9090/filesystem/sse -H "Accept: text/event-stream" -H "Authorization: Bearer [token]"
# Command times out after 2 minutes with no response
```

**Root Cause**: SSE streams not properly established between bridges and central proxy.

**Impact**: No tools are accessible to clients, entire MCP system non-functional.

### Issue #4: Package Version Inconsistencies
**Severity**: High
**Impact**: Runtime failures due to version mismatches

**Evidence**:
- Filesystem bridge: `@modelcontextprotocol/server-filesystem@2025.8.21`
- Fetch bridge: `mcp-server-fetch==2025.4.7`
- Status document claims: `@modelcontextprotocol/server-filesystem@0.2.3`

**Root Cause**: CODEX used non-existent future versions instead of actual published versions.

**Impact**: Containers likely failing to install packages, tools not available.

### Issue #5: Inconsistent Tool Registration Status
**Severity**: High
**Impact**: System status reporting is unreliable

**Evidence**:
- Status.md claims: "filesystem → 14 tools available ✅"
- Health checks show: all containers unhealthy
- SSE endpoints: completely unresponsive

**Root Cause**: Status document not reflecting actual system state, possibly outdated.

**Impact**: False confidence in system status, debugging hampered by incorrect information.

---

## ⚠️ Architectural Issues (Design Problems)

### Issue #6: Docker Health Check Implementation Problems
**Severity**: Medium
**Impact**: Incorrect health monitoring

**Evidence**:
```dockerfile
# In filesystem bridge Dockerfile
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:9071/', timeout=5).close()"]
```

**Root Cause**:
1. Base image `ghcr.io/tbxark/mcp-proxy:v0.39.1` may not include Python
2. Health check assumes proxy exposes HTTP endpoint on expected port

**Impact**: Health checks fail even when service might be working.

### Issue #7: Bridge Configuration Path Issues
**Severity**: Medium
**Impact**: Potential runtime configuration loading problems

**Evidence**:
```dockerfile
# Filesystem bridge copies config to root
COPY config/config.json ./config.json
# But docker-compose mounts to /config
volumes:
  - ./config:/config:ro
```

**Root Cause**: Inconsistent configuration path handling between build-time and runtime.

**Impact**: Services may not load correct configuration, behavior unpredictable.

### Issue #8: Memory Resource Limits Too Restrictive
**Severity**: Low
**Impact**: Potential OOM kills under load

**Evidence**:
```yaml
deploy:
  resources:
    limits:
      memory: 256M  # Same limit for all services
```

**Root Cause**: All services use same 256MB limit regardless of actual resource needs.

**Impact**: Services may be killed under normal operation, especially filesystem with large directory trees.

---

## 🔧 Configuration Issues (Correctable Problems)

### Issue #9: Hardcoded Authentication Token in Config
**Severity**: High
**Impact**: Security risk, token exposed in multiple files

**Evidence**:
```json
// config/config.json contains plaintext token
"authTokens": ["c86f696c4efbb4a7e5f2fa6b84cd3550dde84cfc457f0664a402e59be2d79346"]
```

**Root Cause**: Token rendered into config file but also visible in status document.

**Impact**: Authentication token compromise, violates security best practices.

### Issue #10: Missing PostgreSQL Service Integration
**Severity**: Medium
**Impact**: Incomplete service coverage

**Evidence**:
- Container `mcp-postgres` exists and running
- Not registered in central proxy configuration
- Status document mentions postgres service but not in active config

**Root Cause**: PostgreSQL service deployed but not properly integrated into proxy.

**Impact**: Database tools unavailable to clients, functionality gap.

### Issue #11: Command Flag Usage Inconsistency
**Severity**: Low
**Impact**: Configuration may not be loaded correctly

**Evidence**:
```yaml
# docker-compose.yml
command: ["-config", "/config/config.json"]
```

**Root Cause**: TBXark/mcp-proxy may not use `-config` flag, documentation not checked.

**Impact**: Proxy might use default config instead of custom configuration.

### Issue #12: Network Isolation May Be Too Restrictive
**Severity**: Low
**Impact**: Potential connectivity issues between services

**Evidence**:
```yaml
# All services only on mcp-net, no external network access
networks: ["mcp-net"]
```

**Root Cause**: Bridge services may need external network access for HTTP fetching or other operations.

**Impact**: Fetch service may fail to access external URLs, functionality limited.

---

## 📊 Evidence of Non-Functional State

### Container Logs Analysis
- **mcp-proxy**: Shows successful service registration but returns 404 on health check
- **mcp-filesystem-bridge**: Receiving POST requests every 30 seconds (likely failed health checks)
- **mcp-fetch-bridge**: Same pattern as filesystem bridge
- **System Integration**: Complete failure of SSE communication

### Status Document vs Reality
| Status Document Claim | Actual Reality | Discrepancy |
|-----------------------|----------------|-------------|
| "✅ FULLY OPERATIONAL" | All containers unhealthy | Complete mismatch |
| "14 tools available" | SSE endpoints timeout | Tools not accessible |
| "All SSE streams stable" | 404 errors, timeouts | Communication broken |
| "Ready for client connections" | No working endpoints | System non-functional |

---

## 🔍 Root Cause Analysis

The primary failure modes appear to be:

1. **Wrong Base Image Assumptions**: Health checks assume Python/curl availability in containers that may not have them
2. **Incorrect Package Versions**: Using non-existent future package versions
3. **Configuration Path Problems**: Inconsistent handling of config file locations
4. **Proxy Endpoint Misunderstanding**: Assuming health endpoints that don't exist
5. **Status Document Drift**: Documentation not reflecting actual system state

## 💡 Immediate Remediation Steps

### Priority 1 (Critical)
1. **Fix health checks**: Use correct base image capabilities or simpler health tests
2. **Verify proxy endpoints**: Check TBXark/mcp-proxy documentation for correct endpoints
3. **Use real package versions**: Replace future versions with actual published versions
4. **Test SSE connectivity**: Debug why streams are not establishing

### Priority 2 (High)
1. **Synchronize status documentation**: Update to reflect actual system state
2. **Complete PostgreSQL integration**: Register postgres service in central proxy
3. **Secure authentication token**: Remove hardcoded token from documentation
4. **Standardize configuration paths**: Ensure consistent config loading

### Priority 3 (Medium)
1. **Right-size resource limits**: Set appropriate memory limits per service
2. **Add network access where needed**: Allow external access for fetch service
3. **Verify command flags**: Ensure proxy uses correct configuration flags

---

## 📋 Recommendations

1. **Start Fresh with Working Examples**: Use known-good configurations from TBXark documentation
2. **Implement Incremental Testing**: Deploy one bridge service at a time with verification
3. **Automate Health Verification**: Create scripts to verify each component independently
4. **Maintain Status Documentation**: Keep documentation synchronized with actual system state
5. **Follow Version Constraints**: Use only published package versions, not future dates

## 🎯 Success Criteria for Fixes

- [ ] All containers report "healthy" status
- [ ] Proxy responds successfully to health checks
- [ ] SSE endpoints establish connections within 5 seconds
- [ ] Tool catalog accessible via API calls
- [ ] Status documentation matches actual system state
- [ ] PostgreSQL service fully integrated and available

---

**Conclusion**: While the architectural approach is sound, the implementation has multiple critical issues that render the system completely non-functional. The problems are correctable but require systematic remediation starting with health checks and package versions.

**Estimated Recovery Time**: 4-6 hours with proper debugging and testing approach.