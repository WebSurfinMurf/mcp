#!/bin/bash
# MCP Directory Migration Script
# Migrates from mcp-* to mcp/* structure
# Created: 2025-09-06

set -e

echo "========================================"
echo "    MCP Directory Migration Script     "
echo "========================================"
echo ""
echo "This script will migrate MCP directories from:"
echo "  /home/administrator/projects/mcp-*"
echo "to:"
echo "  /home/administrator/projects/mcp/*"
echo ""

# Confirmation
read -p "Do you want to proceed with migration? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Migration cancelled"
    exit 0
fi

echo ""
echo "Starting migration..."

# Create backup
BACKUP_DIR="/home/administrator/backups/mcp-migration-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
echo "✓ Created backup directory: $BACKUP_DIR"

# Backup configs
echo "Backing up configuration files..."
cp /home/administrator/.config/claude/mcp_servers.json "$BACKUP_DIR/" || {
    echo "✗ Failed to backup mcp_servers.json"
    exit 1
}
echo "✓ Backed up mcp_servers.json"

if [ -f /home/administrator/projects/admin/scripts/startclaude ]; then
    cp /home/administrator/projects/admin/scripts/startclaude "$BACKUP_DIR/"
    echo "✓ Backed up startclaude script"
fi

# Backup directories
echo "Creating archive of MCP directories..."
cd /home/administrator/projects
tar -czf "$BACKUP_DIR/mcp-directories.tar.gz" mcp-*/ 2>/dev/null || {
    echo "⚠ Warning: Some directories might not exist"
}
echo "✓ Archive created"

# Create rollback script
cat > "$BACKUP_DIR/rollback.sh" << 'ROLLBACK_SCRIPT'
#!/bin/bash
# Rollback script for MCP migration
echo "Rolling back MCP migration..."

# Stop Claude Code
pkill -f claude 2>/dev/null || true

# Restore directories
cd /home/administrator/projects
if [ -f "BACKUP_DIR_PLACEHOLDER/mcp-directories.tar.gz" ]; then
    # Remove new structure
    rm -rf mcp/
    # Extract old structure
    tar -xzf "BACKUP_DIR_PLACEHOLDER/mcp-directories.tar.gz"
    echo "✓ Directories restored"
fi

# Restore configs
cp "BACKUP_DIR_PLACEHOLDER/mcp_servers.json" /home/administrator/.config/claude/
echo "✓ Configuration restored"

if [ -f "BACKUP_DIR_PLACEHOLDER/startclaude" ]; then
    cp "BACKUP_DIR_PLACEHOLDER/startclaude" /home/administrator/projects/admin/scripts/
    echo "✓ startclaude script restored"
fi

# Restore internal file references
if [ -f "BACKUP_DIR_PLACEHOLDER/server.js.before" ]; then
    cp "BACKUP_DIR_PLACEHOLDER/server.js.before" /home/administrator/projects/mcp-memory-postgres/src/server.js
    echo "✓ Restored mcp-memory-postgres/src/server.js"
fi

if [ -f "BACKUP_DIR_PLACEHOLDER/memory-postgres-deploy.sh.before" ]; then
    cp "BACKUP_DIR_PLACEHOLDER/memory-postgres-deploy.sh.before" /home/administrator/projects/mcp-memory-postgres/deploy.sh
    echo "✓ Restored mcp-memory-postgres/deploy.sh"
fi

if [ -f "BACKUP_DIR_PLACEHOLDER/n8n-wrapper.sh.before" ]; then
    cp "BACKUP_DIR_PLACEHOLDER/n8n-wrapper.sh.before" /home/administrator/projects/mcp-n8n/mcp-wrapper.sh
    echo "✓ Restored mcp-n8n/mcp-wrapper.sh"
fi

echo "Rollback completed!"
echo "You can now restart Claude Code with: startclaude"
ROLLBACK_SCRIPT

sed -i "s|BACKUP_DIR_PLACEHOLDER|$BACKUP_DIR|g" "$BACKUP_DIR/rollback.sh"
chmod +x "$BACKUP_DIR/rollback.sh"
echo "✓ Created rollback script: $BACKUP_DIR/rollback.sh"

# Create mcp parent directory
mkdir -p /home/administrator/projects/mcp
echo "✓ Created /home/administrator/projects/mcp directory"

# Move directories
echo ""
echo "Moving directories..."
cd /home/administrator/projects

moved_count=0
for dir in mcp-*; do
    if [ -d "$dir" ] && [ "$dir" != "mcp" ]; then
        new_name=$(echo "$dir" | sed 's/^mcp-//')
        if [ -d "mcp/$new_name" ]; then
            echo "⚠ Warning: mcp/$new_name already exists, skipping $dir"
        else
            mv "$dir" "mcp/$new_name"
            echo "✓ Moved $dir → mcp/$new_name"
            ((moved_count++))
        fi
    fi
done

if [ $moved_count -eq 0 ]; then
    echo "⚠ No directories were moved. They may already be in the new structure."
else
    echo "✓ Moved $moved_count directories"
fi

# Update mcp_servers.json
echo ""
echo "Updating configuration files..."
cp /home/administrator/.config/claude/mcp_servers.json "$BACKUP_DIR/mcp_servers.json.before"

# Update all path references
sed -i 's|/projects/mcp-memory-postgres/|/projects/mcp/memory-postgres/|g' /home/administrator/.config/claude/mcp_servers.json
sed -i 's|/projects/mcp-postgres/|/projects/mcp/postgres/|g' /home/administrator/.config/claude/mcp_servers.json
sed -i 's|/projects/mcp-monitoring/|/projects/mcp/monitoring/|g' /home/administrator/.config/claude/mcp_servers.json
sed -i 's|/projects/mcp-timescaledb/|/projects/mcp/timescaledb/|g' /home/administrator/.config/claude/mcp_servers.json
sed -i 's|/projects/mcp-playwright/|/projects/mcp/playwright/|g' /home/administrator/.config/claude/mcp_servers.json
sed -i 's|/projects/mcp-n8n/|/projects/mcp/n8n/|g' /home/administrator/.config/claude/mcp_servers.json

echo "✓ Updated mcp_servers.json"

# Update startclaude script if it exists
if [ -f /home/administrator/projects/admin/scripts/startclaude ]; then
    cp /home/administrator/projects/admin/scripts/startclaude "$BACKUP_DIR/startclaude.before"
    
    # Update path references in startclaude
    sed -i 's|/mcp-|/mcp/|g' /home/administrator/projects/admin/scripts/startclaude
    sed -i 's|"mcp-|"mcp/|g' /home/administrator/projects/admin/scripts/startclaude
    sed -i 's|mcp-\*|mcp/\*|g' /home/administrator/projects/admin/scripts/startclaude
    
    echo "✓ Updated startclaude script"
fi

# Update internal file references
echo ""
echo "Updating internal file references..."

# Fix mcp-memory-postgres server.js
if [ -f "mcp/memory-postgres/src/server.js" ]; then
    cp "mcp/memory-postgres/src/server.js" "$BACKUP_DIR/server.js.before"
    sed -i "s|/home/administrator/projects/secrets/mcp-memory-postgres.env|/home/administrator/projects/secrets/mcp-memory-postgres.env|g" \
        "mcp/memory-postgres/src/server.js"
    echo "✓ Updated mcp/memory-postgres/src/server.js"
fi

# Fix mcp-memory-postgres deploy.sh
if [ -f "mcp/memory-postgres/deploy.sh" ]; then
    cp "mcp/memory-postgres/deploy.sh" "$BACKUP_DIR/memory-postgres-deploy.sh.before"
    sed -i "s|/home/administrator/projects/mcp-memory-postgres|/home/administrator/projects/mcp/memory-postgres|g" \
        "mcp/memory-postgres/deploy.sh"
    echo "✓ Updated mcp/memory-postgres/deploy.sh"
fi

# Fix mcp-n8n wrapper script
if [ -f "mcp/n8n/mcp-wrapper.sh" ]; then
    cp "mcp/n8n/mcp-wrapper.sh" "$BACKUP_DIR/n8n-wrapper.sh.before"
    sed -i "s|/home/administrator/projects/mcp-n8n/src/index.js|/home/administrator/projects/mcp/n8n/src/index.js|g" \
        "mcp/n8n/mcp-wrapper.sh"
    echo "✓ Updated mcp/n8n/mcp-wrapper.sh"
fi

# Verify JSON is still valid
if jq . /home/administrator/.config/claude/mcp_servers.json > /dev/null 2>&1; then
    echo "✓ Configuration file is valid JSON"
else
    echo "✗ Error: Configuration file is not valid JSON!"
    echo "  Please check /home/administrator/.config/claude/mcp_servers.json"
    echo "  Backup available at: $BACKUP_DIR/mcp_servers.json"
    exit 1
fi

# List final structure
echo ""
echo "New directory structure:"
echo "------------------------"
ls -la /home/administrator/projects/mcp/ 2>/dev/null | grep "^d" | awk '{print "  mcp/" $NF}' | grep -v "^\.$\|^\.\.$" || echo "  (no directories found)"

# Create verification script
cat > "$BACKUP_DIR/verify.sh" << 'VERIFY_SCRIPT'
#!/bin/bash
echo "Verifying MCP migration..."

errors=0

# Check directories
for service in fetch filesystem memory-postgres monitoring n8n playwright postgres timescaledb; do
    if [ -d "/home/administrator/projects/mcp/$service" ]; then
        echo "✓ mcp/$service exists"
    else
        echo "✗ mcp/$service missing"
        ((errors++))
    fi
done

# Check old directories are gone
for old_dir in /home/administrator/projects/mcp-*; do
    if [ -d "$old_dir" ]; then
        echo "⚠ Old directory still exists: $(basename $old_dir)"
        ((errors++))
    fi
done

# Check config file
if grep -q "/projects/mcp-" /home/administrator/.config/claude/mcp_servers.json; then
    echo "⚠ Old paths still in mcp_servers.json"
    ((errors++))
else
    echo "✓ mcp_servers.json updated correctly"
fi

if [ $errors -eq 0 ]; then
    echo ""
    echo "✓ All checks passed!"
else
    echo ""
    echo "✗ Found $errors issues"
fi
VERIFY_SCRIPT

chmod +x "$BACKUP_DIR/verify.sh"

# Run verification
echo ""
echo "Running verification..."
echo "------------------------"
"$BACKUP_DIR/verify.sh"

# Final instructions
echo ""
echo "========================================"
echo "        Migration Completed!            "
echo "========================================"
echo ""
echo "Backup location: $BACKUP_DIR"
echo ""
echo "Next steps:"
echo "1. Exit Claude Code (if running)"
echo "2. Restart Claude Code with: startclaude"
echo "3. Test all MCP servers are working"
echo ""
echo "If you encounter issues:"
echo "  Run rollback: $BACKUP_DIR/rollback.sh"
echo ""
echo "To verify migration:"
echo "  Run: $BACKUP_DIR/verify.sh"
echo ""

# Update documentation
echo "[$(date '+%Y-%m-%d %H:%M')] Migrated MCP directories from mcp-* to mcp/* structure" >> \
    /home/administrator/projects/AINotes/SYSTEM-OVERVIEW.md