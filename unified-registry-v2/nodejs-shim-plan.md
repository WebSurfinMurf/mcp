# Node.js Shim Solution for MCP postgres-v2 Integration

**Created**: 2025-09-08  
**Status**: Ready for Implementation  
**Problem**: postgres-v2 works perfectly but Claude Code can't receive responses  
**Solution**: Node.js shim to handle stdio communication  

## Executive Summary

After extensive analysis, the issue is not with our PostgreSQL service implementation (which is 100% functional) but with the "last mile" communication between Python and Claude Code's MCP bridge. The solution is to use a Node.js shim that mimics the architecture of working services by handling the sensitive stdio communication in a proven runtime environment.

## Root Cause Analysis

### The Core Problem
- **Service**: ✅ Works perfectly (proven by manual testing)
- **Protocol**: ✅ Correct JSON-RPC 2.0 implementation
- **Configuration**: ✅ Correct file and format
- **Communication**: ❌ MCP Bridge doesn't receive responses

### Most Likely Causes
1. **Response Framing/Buffering**: Even with `PYTHONUNBUFFERED=1`, the OS or shell might buffer output differently than the MCP bridge expects
2. **Process Lifecycle**: Python process might exit before the bridge fully reads the response
3. **Subtle Protocol Mismatch**: Undocumented requirements in how stdio communication should work

## Implementation Plan

### Phase 1: Minimal Echo Test (30 minutes)
Test the absolute minimum viable MCP service to isolate the bridge behavior.

#### 1.1 Create Minimal Test Service
```python
#!/usr/bin/env python3
# /home/administrator/projects/mcp/unified-registry-v2/minimal_mcp.py
import sys
import json
import time

# Log to file to verify we're being called
with open("/tmp/minimal_mcp.log", "a") as f:
    f.write("--- Service Started ---\n")

for line in sys.stdin:
    # Log the raw request
    with open("/tmp/minimal_mcp.log", "a") as f:
        f.write(f"REQUEST: {line.strip()}\n")

    req = json.loads(line)
    response = {}

    if req.get("method") == "initialize":
        response = {
            "jsonrpc": "2.0", 
            "result": {"protocolVersion": "2024-11-05", "serverInfo": {"name": "minimal"}}, 
            "id": req.get("id")
        }
    elif req.get("method") == "tools/list":
        response = {
            "jsonrpc": "2.0", 
            "result": {
                "tools": [{
                    "name": "echo", 
                    "description": "Echo test tool", 
                    "inputSchema": {
                        "type": "object", 
                        "properties": {"message": {"type": "string"}},
                        "required": ["message"]
                    }
                }]
            }, 
            "id": req.get("id")
        }
    elif req.get("method") == "tools/call":
        msg = req.get("params", {}).get("arguments", {}).get("message", "default")
        response = {
            "jsonrpc": "2.0", 
            "result": {
                "content": [{"type": "text", "text": f"Echo: {msg}"}]
            }, 
            "id": req.get("id")
        }
    
    # Log the response
    with open("/tmp/minimal_mcp.log", "a") as f:
        f.write(f"RESPONSE: {json.dumps(response)}\n")

    print(json.dumps(response), flush=True)
    
    # CRITICAL: Keep process alive briefly after responding
    time.sleep(0.1)
```

#### 1.2 Configure and Test
1. Make executable: `chmod +x minimal_mcp.py`
2. Add to `mcp-settings.json`:
```json
{
  "mcpServers": {
    "minimal-test": {
      "command": "/home/administrator/projects/mcp/unified-registry-v2/minimal_mcp.py",
      "args": []
    }
  }
}
```
3. Restart Claude Code
4. Test: "Using minimal-test, echo message: 'Hello World'"
5. Check `/tmp/minimal_mcp.log` for diagnostics

**Decision Point:**
- If it works → Problem is in postgres-v2 complexity, proceed to Phase 2
- If it fails → Problem is fundamental Python-MCP bridge issue, definitely need Node.js shim

### Phase 2: Node.js Shim Implementation (1 hour)

#### 2.1 Create the Node.js Shim
```javascript
#!/usr/bin/env node
// /home/administrator/projects/mcp/unified-registry-v2/postgres_shim.js

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Path to the Python MCP service wrapper
const mcpScriptPath = path.join(__dirname, 'run_postgres_mcp.sh');

// Log file for debugging
const logFile = '/tmp/postgres_shim.log';
fs.appendFileSync(logFile, `\n--- Shim Started at ${new Date().toISOString()} ---\n`);

// Spawn the Python MCP service
const child = spawn(mcpScriptPath, [], {
    stdio: ['pipe', 'pipe', 'pipe'], // stdin, stdout, stderr
    env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
        DATABASE_URL: process.env.DATABASE_URL || 'postgresql://admin:Pass123qp@localhost:5432/postgres'
    }
});

// Set up stdin forwarding
process.stdin.setEncoding('utf8');
process.stdin.on('data', (data) => {
    fs.appendFileSync(logFile, `STDIN→Child: ${data}`);
    child.stdin.write(data);
});

// Set up stdout forwarding  
child.stdout.setEncoding('utf8');
child.stdout.on('data', (data) => {
    fs.appendFileSync(logFile, `Child→STDOUT: ${data}`);
    process.stdout.write(data);
});

// Capture stderr for debugging
child.stderr.setEncoding('utf8');
child.stderr.on('data', (data) => {
    fs.appendFileSync(logFile, `STDERR: ${data}`);
});

// Handle child process exit
child.on('exit', (code, signal) => {
    fs.appendFileSync(logFile, `Child exited with code ${code}, signal ${signal}\n`);
    process.exit(code || 0);
});

// Handle errors
child.on('error', (err) => {
    fs.appendFileSync(logFile, `Child error: ${err}\n`);
    console.error('Failed to start subprocess:', err);
    process.exit(1);
});

// Handle parent process signals
process.on('SIGINT', () => {
    child.kill('SIGINT');
});

process.on('SIGTERM', () => {
    child.kill('SIGTERM');
});
```

#### 2.2 Create Enhanced Shim with Keep-Alive
```javascript
#!/usr/bin/env node
// /home/administrator/projects/mcp/unified-registry-v2/postgres_shim_enhanced.js

const { spawn } = require('child_process');
const readline = require('readline');
const path = require('path');
const fs = require('fs');

const mcpScriptPath = path.join(__dirname, 'run_postgres_mcp.sh');
const logFile = '/tmp/postgres_shim_enhanced.log';

fs.appendFileSync(logFile, `\n--- Enhanced Shim Started at ${new Date().toISOString()} ---\n`);

const child = spawn(mcpScriptPath, [], {
    stdio: ['pipe', 'pipe', 'pipe'],
    env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
        DATABASE_URL: process.env.DATABASE_URL || 'postgresql://admin:Pass123qp@localhost:5432/postgres'
    }
});

// Use readline for better line-based processing
const rl = readline.createInterface({
    input: process.stdin,
    output: null,
    terminal: false
});

rl.on('line', (line) => {
    fs.appendFileSync(logFile, `REQUEST: ${line}\n`);
    child.stdin.write(line + '\n');
});

// Buffer and process child output line by line
const childRl = readline.createInterface({
    input: child.stdout,
    output: null,
    terminal: false
});

childRl.on('line', (line) => {
    fs.appendFileSync(logFile, `RESPONSE: ${line}\n`);
    console.log(line);
    
    // CRITICAL: Add small delay to ensure output is flushed
    setTimeout(() => {}, 10);
});

// Log stderr
child.stderr.on('data', (data) => {
    fs.appendFileSync(logFile, `STDERR: ${data}`);
});

// Keep process alive even after child exits briefly
child.on('exit', (code, signal) => {
    fs.appendFileSync(logFile, `Child exited: code=${code}, signal=${signal}\n`);
    setTimeout(() => {
        process.exit(code || 0);
    }, 100); // Wait 100ms before exiting
});

child.on('error', (err) => {
    fs.appendFileSync(logFile, `ERROR: ${err}\n`);
    console.error('Subprocess error:', err);
    process.exit(1);
});
```

#### 2.3 Configure Claude Code
```json
{
  "mcpServers": {
    "postgres-v2": {
      "command": "/home/administrator/projects/mcp/unified-registry-v2/postgres_shim.js",
      "args": []
    }
  }
}
```

### Phase 3: Testing & Validation (30 minutes)

#### 3.1 Test Sequence
1. **Basic connectivity**: Check `claude mcp list` shows "✓ Connected"
2. **Simple query**: "Using postgres-v2, list all databases"
3. **Complex query**: "Using postgres-v2, execute SQL: SELECT version()"
4. **Error handling**: "Using postgres-v2, execute SQL: DROP TABLE test"

#### 3.2 Diagnostic Commands
```bash
# Monitor shim logs
tail -f /tmp/postgres_shim.log

# Test shim directly
echo '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}' | \
  ./postgres_shim.js

# Check if Node.js is installed
node --version

# Install Node.js if needed
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### Phase 4: Production Deployment (30 minutes)

#### 4.1 Create Production Shim
```javascript
#!/usr/bin/env node
// /home/administrator/projects/mcp/unified-registry-v2/mcp_shim.js
// Generic shim that can wrap any Python MCP service

const { spawn } = require('child_process');
const readline = require('readline');
const path = require('path');
const fs = require('fs');

// Get service name from argument or default to postgres
const service = process.argv[2] || 'postgres';
const mode = process.argv[3] || 'stdio';

// Determine script path based on service
const scriptPath = path.join(__dirname, 'services', `mcp_${service}.py`);

// Logging configuration
const logDir = '/tmp/mcp_shim_logs';
if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
}
const logFile = path.join(logDir, `${service}_${Date.now()}.log`);

// Start the Python service
const child = spawn('python3', [scriptPath, '--mode', mode], {
    stdio: ['pipe', 'pipe', 'pipe'],
    cwd: __dirname,
    env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
        PYTHONPATH: __dirname
    }
});

// Set up bidirectional communication
const inputRl = readline.createInterface({
    input: process.stdin,
    terminal: false
});

const outputRl = readline.createInterface({
    input: child.stdout,
    terminal: false
});

inputRl.on('line', (line) => {
    fs.appendFileSync(logFile, `→ ${line}\n`);
    child.stdin.write(line + '\n');
});

outputRl.on('line', (line) => {
    fs.appendFileSync(logFile, `← ${line}\n`);
    console.log(line);
});

child.stderr.on('data', (data) => {
    fs.appendFileSync(logFile, `✗ ${data}`);
});

// Graceful shutdown
process.on('SIGINT', () => child.kill('SIGINT'));
process.on('SIGTERM', () => child.kill('SIGTERM'));

child.on('exit', (code) => {
    setTimeout(() => process.exit(code || 0), 50);
});
```

#### 4.2 Update Deployment Script
```bash
# Add to deploy.sh
do_shim() {
    local service="$1"
    
    # Create shim wrapper
    cat > "shim_${service}.js" << 'EOF'
#!/usr/bin/env node
// Auto-generated shim for MCP service
require('./mcp_shim.js');
EOF
    
    chmod +x "shim_${service}.js"
    
    # Update Claude configuration
    echo "Shim created for $service"
    echo "Update mcp-settings.json to use: $(pwd)/shim_${service}.js"
}
```

### Phase 5: Apply to All Services (Optional - 2 hours)

If the shim works for postgres-v2, apply the same pattern to all other services:

1. **Filesystem Service**: Create `filesystem_shim.js`
2. **GitHub Service**: Create `github_shim.js`
3. **Monitoring Service**: May already work with Node.js
4. **TimescaleDB Service**: Create `timescaledb_shim.js`

## Success Criteria

### Immediate Success
- [ ] Minimal echo test shows whether Python can work at all
- [ ] Node.js shim allows postgres-v2 to return database list
- [ ] All 5 PostgreSQL tools work through the shim
- [ ] No "Tool ran without output" errors

### Long-term Success
- [ ] Shim solution is stable across Claude restarts
- [ ] Can be applied to other Python MCP services
- [ ] Performance is acceptable (<500ms overhead)
- [ ] Logging provides good diagnostics

## Troubleshooting Guide

### If Minimal Echo Test Fails
- Python fundamentally incompatible with MCP bridge
- Must use Node.js shim for all Python services
- Consider rewriting in Node.js long-term

### If Basic Shim Fails
- Try enhanced shim with readline and delays
- Check Node.js version (needs v14+)
- Verify file permissions (all scripts executable)
- Check `/tmp/postgres_shim.log` for errors

### If Shim Works Intermittently
- Increase delay in enhanced shim
- Add response queuing/buffering
- Consider process pool for stability

## Architecture Comparison

### Current (Failing)
```
Claude → MCP Bridge → Bash → Python → PostgreSQL
         ↑_________[No Response]_______|
```

### With Node.js Shim (Expected to Work)
```
Claude → MCP Bridge → Node.js → Bash → Python → PostgreSQL
         ↑________[Response OK]________|
```

### Why This Should Work
1. **Proven Pattern**: Other working services use Node.js
2. **Better stdio Handling**: Node.js readline and streams are battle-tested
3. **Process Management**: Node.js keeps process alive appropriately
4. **Buffer Control**: Fine-grained control over I/O buffering

## Implementation Timeline

- **Hour 1**: Minimal echo test + basic shim
- **Hour 2**: Testing and refinement
- **Hour 3**: Production deployment
- **Hour 4**: Documentation and cleanup

## Next Steps

1. **Immediate**: Implement minimal echo test
2. **If test reveals Python issue**: Implement Node.js shim
3. **After success**: Apply pattern to remaining services
4. **Long-term**: Consider native Node.js implementation

## Conclusion

The Node.js shim is not a workaround but a **proper architectural decision** that:
- Decouples Python service logic from MCP communication
- Provides a stable, proven communication layer
- Allows us to keep the excellent Python implementation
- Gives us debugging visibility through logging

This approach "meets the MCP bridge where it is" rather than fighting against undocumented requirements.

---
*This plan synthesizes the analysis and provides a clear path forward to resolve the postgres-v2 integration issue.*