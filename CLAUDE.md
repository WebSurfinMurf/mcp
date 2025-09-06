# MCP Directory Reorganization Plan
*Created: 2025-09-06*
*Purpose: Migrate from flat mcp-* structure to nested mcp/* structure*

## Overview
Reorganize all MCP (Model Context Protocol) server directories from:
- `/home/administrator/projects/mcp-{service}` 
to:
- `/home/administrator/projects/mcp/{service}`

## Current State

### MCP Directories to Migrate
1. `mcp-fetch` → `mcp/fetch`
2. `mcp-filesystem` → `mcp/filesystem`
3. `mcp-memory-postgres` → `mcp/memory-postgres`
4. `mcp-monitoring` → `mcp/monitoring`
5. `mcp-n8n` → `mcp/n8n`
6. `mcp-playwright` → `mcp/playwright`
7. `mcp-postgres` → `mcp/postgres`
8. `mcp-timescaledb` → `mcp/timescaledb`

### Files That Need Path Updates

#### 1. MCP Configuration File
**File**: `/home/administrator/.config/claude/mcp_servers.json`

**Current References**:
- Line 44: `/home/administrator/projects/mcp-memory-postgres/src/server.js`
- Line 52: `/home/administrator/projects/mcp-postgres/deploy.sh`
- Line 71: `/home/administrator/projects/mcp-monitoring/src/index.js`
- Line 81: `/home/administrator/projects/mcp-timescaledb/mcp-wrapper.sh`
- Line 94: `/home/administrator/projects/mcp-playwright/src/index.js`
- Line 103: `/home/administrator/projects/mcp-n8n/mcp-wrapper.sh`

**Note**: Docker-based MCPs (fetch, filesystem) use Docker images, not local paths.
GitHub MCP uses NPX, not a local directory.

#### 2. Admin Scripts
**File**: `/home/administrator/projects/admin/scripts/startclaude`

**Current References**:
- Line checking for `$PROJECTS_DIR/mcp-*` directories
- Specific checks for:
  - `mcp-docker`
  - `mcp-fetch`
  - `mcp-filesystem`
  - `mcp-memory`
  - `mcp-postgres`

#### 3. Potential Cross-References
- Deploy scripts within each MCP directory
- Any systemd service files
- Documentation files referencing paths
- Symlinks or aliases

## Migration Plan

### Phase 1: Pre-Migration Backup
```bash
# 1. Create backup directory with timestamp
BACKUP_DIR="/home/administrator/backups/mcp-migration-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# 2. Backup MCP configuration
cp /home/administrator/.config/claude/mcp_servers.json "$BACKUP_DIR/"

# 3. Backup startclaude script
cp /home/administrator/projects/admin/scripts/startclaude "$BACKUP_DIR/"

# 4. Create tar archive of all MCP directories
cd /home/administrator/projects
tar -czf "$BACKUP_DIR/mcp-directories.tar.gz" mcp-*/

# 5. Document current state
docker ps --format "table {{.Names}}\t{{.Status}}" | grep mcp > "$BACKUP_DIR/mcp-containers-before.txt"
```

### Phase 2: Directory Migration
```bash
# 1. Create new MCP parent directory (already done)
mkdir -p /home/administrator/projects/mcp

# 2. Move each directory to new location
cd /home/administrator/projects

# Move with preserved permissions and attributes
mv mcp-fetch mcp/fetch
mv mcp-filesystem mcp/filesystem
mv mcp-memory-postgres mcp/memory-postgres
mv mcp-monitoring mcp/monitoring
mv mcp-n8n mcp/n8n
mv mcp-playwright mcp/playwright
mv mcp-postgres mcp/postgres
mv mcp-timescaledb mcp/timescaledb

# 3. Verify all moves completed
ls -la mcp/
```

### Phase 3: Configuration Updates

#### 3.1 Update mcp_servers.json
```json
{
  "mcpServers": {
    "memory": {
      "args": ["/home/administrator/projects/mcp/memory-postgres/src/server.js"]
    },
    "postgres": {
      "command": "/home/administrator/projects/mcp/postgres/deploy.sh"
    },
    "monitoring": {
      "args": ["/home/administrator/projects/mcp/monitoring/src/index.js"]
    },
    "timescaledb": {
      "command": "/home/administrator/projects/mcp/timescaledb/mcp-wrapper.sh"
    },
    "playwright": {
      "args": ["/home/administrator/projects/mcp/playwright/src/index.js"]
    },
    "n8n": {
      "command": "/home/administrator/projects/mcp/n8n/mcp-wrapper.sh"
    }
  }
}
```

#### 3.2 Update startclaude script
Change all references from:
- `$PROJECTS_DIR/mcp-*` to `$PROJECTS_DIR/mcp/*`
- Individual checks like `mcp-postgres` to `mcp/postgres`

### Phase 4: Update Internal References

#### 4.1 Check and update deploy scripts
```bash
# Find all deploy.sh scripts that might have cross-references
find /home/administrator/projects/mcp -name "deploy.sh" -o -name "*.sh" | \
  xargs grep -l "mcp-" 2>/dev/null

# Update any found references
```

#### 4.2 Update wrapper scripts
```bash
# Check wrapper scripts for internal references
for wrapper in /home/administrator/projects/mcp/*/mcp-wrapper.sh; do
  if [ -f "$wrapper" ]; then
    echo "Checking: $wrapper"
    grep "mcp-" "$wrapper" || echo "  No references found"
  fi
done
```

### Phase 5: Testing

#### 5.1 Pre-test Checklist
- [ ] All directories moved successfully
- [ ] mcp_servers.json updated
- [ ] startclaude script updated
- [ ] Internal references updated
- [ ] Backup created and verified

#### 5.2 Test Procedure
```bash
# 1. Stop Claude Code if running
pkill -f claude || true

# 2. Verify configuration is valid JSON
jq . /home/administrator/.config/claude/mcp_servers.json

# 3. Test individual MCP servers (non-interactive)
# Test postgres MCP
/home/administrator/projects/mcp/postgres/deploy.sh --test 2>&1 | head -5

# Test memory MCP
node /home/administrator/projects/mcp/memory-postgres/src/server.js --version 2>&1 | head -5

# 4. Start Claude Code
startclaude

# 5. In Claude Code, test each MCP:
# - List MCP servers
# - Test memory operations
# - Test postgres operations
# - Test monitoring queries
# - Test other MCP functions

# 6. Verify all MCPs are functional
```

### Phase 6: Post-Migration Validation

#### 6.1 Validation Checklist
- [ ] Claude Code starts without errors
- [ ] All MCP servers appear in Claude Code
- [ ] Memory operations work (list, create, search)
- [ ] Postgres operations work
- [ ] Monitoring queries work
- [ ] Playwright operations work
- [ ] N8n operations work
- [ ] TimescaleDB operations work
- [ ] Fetch operations work (Docker-based)
- [ ] Filesystem operations work (Docker-based)

#### 6.2 Documentation Updates
```bash
# Update system documentation
echo "[$(date '+%Y-%m-%d')] Reorganized MCP directories from mcp-* to mcp/*" >> \
  /home/administrator/projects/AINotes/SYSTEM-OVERVIEW.md

# Update any project-specific docs
find /home/administrator/projects/mcp -name "CLAUDE.md" -o -name "README.md" | \
  xargs grep -l "mcp-" 2>/dev/null
```

## Rollback Plan

If issues occur, rollback using:

```bash
#!/bin/bash
# rollback-mcp-migration.sh

BACKUP_DIR="/home/administrator/backups/mcp-migration-YYYYMMDD-HHMMSS"  # Use actual backup dir

# 1. Stop Claude Code
pkill -f claude || true

# 2. Move directories back
cd /home/administrator/projects
for dir in mcp/*; do
  if [ -d "$dir" ]; then
    service=$(basename "$dir")
    mv "mcp/$service" "mcp-$service"
  fi
done

# 3. Restore configuration
cp "$BACKUP_DIR/mcp_servers.json" /home/administrator/.config/claude/

# 4. Restore startclaude script
cp "$BACKUP_DIR/startclaude" /home/administrator/projects/admin/scripts/

# 5. Remove empty mcp directory
rmdir /home/administrator/projects/mcp

# 6. Restart Claude Code
startclaude

echo "Rollback completed"
```

## Risk Assessment

### Low Risk
- Directory moves are atomic operations
- Backup ensures full recovery capability
- Changes are configuration-only, no data loss risk

### Medium Risk
- Claude Code needs restart (brief downtime)
- Path updates might be missed in some scripts

### Mitigation
- Complete backup before migration
- Test thoroughly before declaring success
- Keep backup for at least 7 days
- Document all changes made

## Implementation Commands

### Quick Implementation Script
```bash
#!/bin/bash
# migrate-mcp-directories.sh
set -e

echo "=== MCP Directory Migration ==="
echo "Migrating from mcp-* to mcp/* structure"

# Create backup
BACKUP_DIR="/home/administrator/backups/mcp-migration-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
echo "Backup directory: $BACKUP_DIR"

# Backup configs
cp /home/administrator/.config/claude/mcp_servers.json "$BACKUP_DIR/"
cp /home/administrator/projects/admin/scripts/startclaude "$BACKUP_DIR/" 2>/dev/null || true

# Backup directories
cd /home/administrator/projects
tar -czf "$BACKUP_DIR/mcp-directories.tar.gz" mcp-*/ 2>/dev/null || true

# Create mcp parent
mkdir -p mcp

# Move directories
for dir in mcp-*; do
  if [ -d "$dir" ] && [ "$dir" != "mcp" ]; then
    new_name=$(echo "$dir" | sed 's/^mcp-//')
    echo "Moving $dir → mcp/$new_name"
    mv "$dir" "mcp/$new_name"
  fi
done

# Update mcp_servers.json
cp /home/administrator/.config/claude/mcp_servers.json "$BACKUP_DIR/mcp_servers.json.before"
sed -i 's|/projects/mcp-|/projects/mcp/|g' /home/administrator/.config/claude/mcp_servers.json

# Update startclaude if it exists
if [ -f /home/administrator/projects/admin/scripts/startclaude ]; then
  cp /home/administrator/projects/admin/scripts/startclaude "$BACKUP_DIR/startclaude.before"
  sed -i 's|/mcp-|/mcp/|g' /home/administrator/projects/admin/scripts/startclaude
  sed -i 's|"mcp-|"mcp/|g' /home/administrator/projects/admin/scripts/startclaude
fi

echo ""
echo "Migration completed!"
echo "Backup saved to: $BACKUP_DIR"
echo ""
echo "Next steps:"
echo "1. Exit Claude Code"
echo "2. Run: startclaude"
echo "3. Test all MCP servers are working"
echo ""
echo "If rollback needed, use backup from: $BACKUP_DIR"
```

## Success Criteria

Migration is successful when:
1. All MCP directories exist under `/home/administrator/projects/mcp/`
2. No `mcp-*` directories remain in `/home/administrator/projects/`
3. Claude Code starts without errors
4. All MCP tools are accessible in Claude Code
5. Test operations succeed for each MCP server

## Notes

- GitHub MCP is NPX-based, no directory to migrate
- Fetch and Filesystem MCPs use Docker, but check for any local config
- Memory MCP is actually mcp-memory-postgres (not mcp-memory)
- Some MCPs have wrapper scripts that may contain internal path references
- The startclaude script has extensive MCP detection logic that needs updating

---
*End of Migration Plan*