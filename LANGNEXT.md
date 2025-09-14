# MCP Service Expansion Plan - Next Generation Tools Integration

**Project**: Centralized MCP Server Expansion
**Date**: 2025-09-14
**Status**: 🚧 **Planning Phase** - Adding 3 Major Service Integrations
**Target**: Expand from 12 to 40+ tools across n8n, Playwright, and TimescaleDB

## 🎯 Executive Summary

This plan outlines the integration of three major services into our centralized MCP server:
- **n8n**: Workflow automation and orchestration (8+ tools)
- **Playwright**: Browser automation and web scraping (15+ tools)
- **TimescaleDB**: Advanced time-series database operations (12+ tools)

**Expected Outcome**: Transform our MCP server into a comprehensive AI toolset with 40+ tools covering database operations, web automation, workflow orchestration, monitoring, file operations, and time-series analytics.

## 📊 Current State Analysis

### ✅ **Current MCP Server Status**
- **Location**: `/home/administrator/projects/mcp/server/`
- **Architecture**: Centralized LangChain + FastAPI + OAuth2 Proxy
- **Tools Available**: 12 (5 PostgreSQL, 2 MinIO, 2 Monitoring, 1 Web, 2 Filesystem)
- **Access Methods**: HTTP API + Claude Code MCP Bridge
- **Status**: ✅ 100% Operational (MinIO issue resolved 2025-09-14)

### 📂 **Existing Service Implementations**

#### 1. **n8n MCP Server** - `/home/administrator/projects/mcp/n8n/`
- **Status**: ✅ **Operational** (Node.js + MCP SDK 1.13.1)
- **Current Tools**: 8 workflow management tools
- **Integration**: Standalone MCP server (stdio-based)
- **Instance**: Connected to `https://n8n.ai-servicers.com`
- **API Access**: Via JWT token authentication

#### 2. **Playwright MCP Server** - `/home/administrator/projects/mcp/playwright/`
- **Status**: 🔄 **Partial Implementation** (Node.js structure exists)
- **Current Tools**: Unknown (requires evaluation)
- **Integration**: Standalone structure, needs completion
- **Dependencies**: Playwright, Chromium browser

#### 3. **TimescaleDB MCP Server** - `/home/administrator/projects/mcp/timescaledb/`
- **Status**: ✅ **Operational** (Python + asyncpg + MCP 1.13.1)
- **Current Tools**: 9 time-series database tools
- **Integration**: Standalone MCP server (stdio-based)
- **Database**: Connected to `timescaledb:5433`

## 🔍 Market Research Results

### **Best-in-Class MCP Implementations Found**

#### **n8n Integration Options**

**🏆 Recommended: czlonkowski/n8n-mcp**
- **Coverage**: 535+ n8n nodes with 99% property coverage
- **Performance**: 12ms average response time (SQLite-powered)
- **Compatibility**: Claude Code, Claude Desktop, Windsurf, Cursor
- **Features**: Complete node documentation, workflow management, execution control
- **Repository**: `https://github.com/czlonkowski/n8n-mcp`

**Alternative Options**:
- `kingler/n8n-mcp-server`: Comprehensive workflow management
- `eric050828/n8n-mcp-server`: Basic workflow automation
- `makafeli/n8n-workflow-builder`: Natural language workflow management

#### **Playwright Integration Options**

**🏆 Recommended: Microsoft/playwright-mcp (Official)**
- **Source**: Official Microsoft implementation
- **Package**: `@playwright/mcp@latest`
- **Features**: Fast accessibility tree-based automation (no screenshots needed)
- **Performance**: Deterministic browser control using structured DOM representation
- **Integration**: Works with Claude Desktop, VS Code via GitHub Copilot
- **Repository**: `https://github.com/microsoft/playwright-mcp`

**Alternative Options**:
- `executeautomation/mcp-playwright`: Screenshots + test generation
- `dennisgl/mcp-playwright-scraper`: Web scraping focused
- `automatalabs/mcp-server-playwright`: General browser automation

#### **TimescaleDB Integration Options**

**🏆 Recommended: telegraph-it/timescaledb-mcp-server**
- **Features**: TimescaleDB-specific hypertable management
- **Tools**: Query execution, compression, continuous aggregates
- **Compatibility**: Modern MCP protocol support
- **Repository**: Available on LobeHub MCP Servers

**Alternative: Use Current Implementation**
- **Advantage**: Already operational and tested
- **Tools**: 9 comprehensive time-series tools
- **Integration**: Known working with our infrastructure

## 🏗️ Integration Architecture Plan

### **Phase 1: Service Evaluation & Selection**

#### **Download & Evaluate Best Implementations**
```bash
# Create evaluation workspace
mkdir -p /home/administrator/projects/mcp/evaluation

# Download best n8n MCP implementation
cd /home/administrator/projects/mcp/evaluation
git clone https://github.com/czlonkowski/n8n-mcp.git n8n-best

# Download Microsoft's official Playwright MCP
npm install @playwright/mcp@latest
git clone https://github.com/microsoft/playwright-mcp.git playwright-official

# Download TimescaleDB MCP if available
# (May need to use existing implementation)
```

#### **Tool Extraction Process**
For each service, extract the best tools to integrate into our centralized server:

**🔧 Tool Integration Methodology**:
1. **Analyze Tool Functions**: Extract function signatures and logic
2. **Convert to LangChain Tools**: Use `@tool` decorator pattern
3. **Integrate Configuration**: Add to centralized config system
4. **Test Integration**: Verify functionality via HTTP API
5. **Update MCP Bridge**: Add tool schemas for Claude Code integration

### **Phase 2: Centralized Server Enhancement**

#### **Enhanced Architecture**
```python
# /home/administrator/projects/mcp/server/app/main.py (enhanced)

# Tool Categories (Expanded):
tools = [
    # Existing tools (12)
    *postgres_tools,      # 5 tools
    *minio_tools,         # 2 tools
    *monitoring_tools,    # 2 tools
    *web_tools,          # 1 tool
    *filesystem_tools,   # 2 tools

    # New integrations (28+ tools)
    *n8n_tools,          # 8+ tools
    *playwright_tools,   # 15+ tools
    *timescaledb_tools,  # 12+ tools
]

# Total: 40+ tools across 6 service categories
```

#### **Configuration Management**
```bash
# Enhanced environment file structure
/home/administrator/secrets/mcp-server.env:
# Existing services...
# PostgreSQL, MinIO, Monitoring, Web, Filesystem configs...

# n8n Integration
N8N_URL=https://n8n.ai-servicers.com
N8N_API_KEY=${N8N_API_KEY}

# Playwright Integration
PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_BROWSER_TYPE=chromium
PLAYWRIGHT_TIMEOUT=30000

# TimescaleDB Integration
TIMESCALEDB_URL=postgresql://tsdbadmin:TimescaleSecure2025@timescaledb:5432/timescale
```

### **Phase 3: Tool Implementation Plan**

#### **n8n Tools (8+ Tools Expected)**
Based on research, implement these essential tools:
```python
@tool
def n8n_list_workflows(active_only: bool = None, tags: List[str] = None) -> str:
    """List workflows with optional filtering by status and tags"""

@tool
def n8n_get_workflow(workflow_id: str) -> str:
    """Get detailed information about a specific workflow"""

@tool
def n8n_execute_workflow(workflow_id: str, data: dict = None) -> str:
    """Execute a workflow with optional input data"""

@tool
def n8n_get_executions(workflow_id: str = None, limit: int = 10) -> str:
    """Get workflow execution history with filtering"""

@tool
def n8n_activate_workflow(workflow_id: str) -> str:
    """Activate a workflow"""

@tool
def n8n_deactivate_workflow(workflow_id: str) -> str:
    """Deactivate a workflow"""

@tool
def n8n_create_webhook_test(workflow_id: str) -> str:
    """Generate webhook test payloads for workflow testing"""

@tool
def n8n_get_workflow_status(workflow_id: str) -> str:
    """Get current status and statistics for a workflow"""
```

#### **Playwright Tools (15+ Tools Expected)**
Based on Microsoft's official MCP and research:
```python
@tool
def playwright_navigate(url: str, wait_for_load: bool = True) -> str:
    """Navigate to a URL and wait for page load"""

@tool
def playwright_click_element(selector: str, timeout: int = 30000) -> str:
    """Click on an element using CSS selector"""

@tool
def playwright_fill_form(selector: str, value: str) -> str:
    """Fill form field with specified value"""

@tool
def playwright_take_screenshot(full_page: bool = False) -> str:
    """Take screenshot of current page or full page"""

@tool
def playwright_get_page_content() -> str:
    """Get current page content as text or HTML"""

@tool
def playwright_wait_for_element(selector: str, timeout: int = 30000) -> str:
    """Wait for element to appear on page"""

@tool
def playwright_extract_links(filter_pattern: str = None) -> str:
    """Extract all links from current page with optional filtering"""

@tool
def playwright_execute_javascript(script: str) -> str:
    """Execute JavaScript code in browser context"""

@tool
def playwright_get_element_text(selector: str) -> str:
    """Get text content of specified element"""

@tool
def playwright_scroll_page(direction: str = "down", pixels: int = None) -> str:
    """Scroll page in specified direction"""

@tool
def playwright_handle_dialog(action: str = "accept", text: str = None) -> str:
    """Handle browser dialogs (accept, dismiss, or input text)"""

@tool
def playwright_upload_file(selector: str, file_path: str) -> str:
    """Upload file to file input element"""

@tool
def playwright_get_accessibility_tree() -> str:
    """Get structured accessibility representation of page"""

@tool
def playwright_generate_test_code(actions: List[str]) -> str:
    """Generate Playwright test code from recorded actions"""

@tool
def playwright_browser_context_new() -> str:
    """Create new browser context for isolated browsing"""
```

#### **TimescaleDB Tools (12+ Tools Expected)**
Enhanced from existing implementation:
```python
@tool
def tsdb_query(query: str) -> str:
    """Execute SELECT queries against TimescaleDB"""

@tool
def tsdb_create_hypertable(table_name: str, time_column: str = "time") -> str:
    """Convert regular table to TimescaleDB hypertable"""

@tool
def tsdb_show_hypertables() -> str:
    """List all hypertables with metadata"""

@tool
def tsdb_compression_stats(hypertable: str = None) -> str:
    """View compression statistics for hypertables"""

@tool
def tsdb_add_compression_policy(hypertable: str, compress_after: str = "7 days") -> str:
    """Add compression policy to hypertable"""

@tool
def tsdb_continuous_aggregate(view_name: str, query: str) -> str:
    """Create continuous aggregate view"""

@tool
def tsdb_time_bucket_query(table: str, bucket_interval: str = "1 hour") -> str:
    """Execute time-bucket aggregation queries"""

@tool
def tsdb_retention_policy(hypertable: str, older_than: str) -> str:
    """Add data retention policy"""

@tool
def tsdb_show_chunks(hypertable: str) -> str:
    """Show chunks for specified hypertable"""

@tool
def tsdb_database_stats() -> str:
    """Get comprehensive database statistics"""

@tool
def tsdb_performance_metrics() -> str:
    """Get performance metrics and query statistics"""

@tool
def tsdb_backup_hypertable(hypertable: str, backup_location: str) -> str:
    """Create backup of hypertable data"""
```

### **Phase 4: Testing & Validation**

#### **Tool Validation Matrix**
Create comprehensive testing for all 40+ tools:

```bash
# HTTP API Testing
for tool in n8n_list_workflows playwright_navigate tsdb_query; do
  echo "Testing $tool..."
  curl -X POST http://mcp.linuxserver.lan/tools/$tool \
    -H "Content-Type: application/json" \
    -d '{"input": {"test": "parameters"}}'
done

# Claude Code MCP Bridge Testing
# Test all tools via centralized-mcp-server integration
```

#### **Performance Benchmarking**
- **Target**: <100ms average response time for simple operations
- **Monitoring**: Track tool usage and performance metrics
- **Scaling**: Ensure server can handle 40+ tools without performance degradation

### **Phase 5: Documentation & Deployment**

#### **Enhanced CLAUDE.md Documentation**
Update `/home/administrator/projects/mcp/server/CLAUDE.md`:

```markdown
## Available Tools (40+ Total)

### Database Operations (17 tools)
**PostgreSQL (5)**: Query, list databases/tables, server info, database sizes
**TimescaleDB (12)**: Hypertables, compression, aggregates, retention policies

### Automation & Orchestration (8+ tools)
**n8n Workflow Management**: List, execute, manage workflows and executions

### Browser Automation (15+ tools)
**Playwright Web Automation**: Navigate, interact, scrape, test web applications

### Infrastructure & Monitoring (2 tools)
**System Monitoring**: Log search, system metrics

### File & Storage Operations (4 tools)
**MinIO S3**: Object listing and retrieval
**Filesystem**: Secure file operations

### Web & Content (1 tool)
**Web Fetch**: HTTP content retrieval with markdown conversion
```

## 🚦 Implementation Phases & Timeline

### **Phase 1: Evaluation & Setup** (Days 1-3)
- ✅ Research completed (2025-09-14)
- Download and evaluate best implementations
- Set up evaluation workspace
- Test individual service implementations

### **Phase 2: Tool Integration** (Days 4-7)
- Extract tools from best implementations
- Convert to centralized LangChain format
- Integrate configuration management
- Update environment files

### **Phase 3: Testing & Debugging** (Days 8-10)
- HTTP API testing for all tools
- Claude Code MCP bridge integration
- Performance testing and optimization
- Security validation

### **Phase 4: Documentation & Deployment** (Days 11-12)
- Update all documentation files
- Deploy enhanced server
- Complete integration testing
- Update SYSTEM-OVERVIEW.md

## 🔒 Security & Configuration

### **Enhanced Security Model**
```python
# Security controls for new tools
SECURITY_POLICIES = {
    "n8n": {
        "read_only": False,  # Workflows can be modified
        "allowed_operations": ["list", "get", "execute", "activate", "deactivate"],
        "restricted_workflows": [],  # Configurable workflow restrictions
    },
    "playwright": {
        "allowed_domains": ["*.ai-servicers.com", "localhost", "127.0.0.1"],
        "blocked_domains": ["*.banking.com", "*.financial.*"],
        "max_execution_time": 30000,  # 30 second timeout
        "headless_only": True,  # No GUI browsers in production
    },
    "timescaledb": {
        "read_only": False,  # Allow data modifications
        "allowed_operations": ["SELECT", "INSERT", "UPDATE", "CREATE", "ALTER"],
        "restricted_tables": [],  # Configurable table restrictions
    }
}
```

### **Configuration Management**
- **Secrets**: All credentials in `/home/administrator/secrets/mcp-server.env`
- **Network**: Internal Docker network communication preferred
- **Authentication**: Maintain OAuth2 proxy for external access
- **Logging**: Comprehensive structured logging for all new tools

## 📈 Expected Benefits

### **Capability Expansion**
- **From 12 to 40+ tools**: 233% increase in available functionality
- **Full-Stack Coverage**: Database, web, workflow, monitoring, files, time-series
- **AI Assistant Enhancement**: Comprehensive toolset for complex automation tasks

### **Use Case Examples**

#### **Complex Automation Workflows**
```
User: "Monitor our website performance, extract data to TimescaleDB, and trigger n8n workflow if issues detected"

AI Assistant:
1. playwright_navigate → check website performance
2. tsdb_time_bucket_query → analyze historical performance data
3. n8n_execute_workflow → trigger alerting workflow if thresholds exceeded
```

#### **Data Pipeline Automation**
```
User: "Extract data from web form, process it, and store in time-series format"

AI Assistant:
1. playwright_fill_form → submit data extraction request
2. playwright_get_page_content → extract response data
3. tsdb_query → insert processed data into hypertable
4. n8n_list_workflows → trigger data processing workflow
```

#### **Comprehensive Testing & Monitoring**
```
User: "Generate test scenarios, execute them, and store results for analysis"

AI Assistant:
1. playwright_generate_test_code → create test automation
2. playwright_execute_javascript → run test scenarios
3. tsdb_create_hypertable → store test results over time
4. search_logs → analyze system logs for issues
5. n8n_activate_workflow → enable continuous testing workflow
```

## 🎯 Success Criteria

### **Technical Metrics**
- ✅ **40+ tools operational**: All major service categories represented
- ✅ **<100ms average response time**: Fast tool execution
- ✅ **100% HTTP API coverage**: All tools accessible via direct API
- ✅ **100% MCP bridge compatibility**: All tools work via Claude Code
- ✅ **Zero security vulnerabilities**: Comprehensive security validation
- ✅ **Complete documentation**: All tools documented with examples

### **Functional Validation**
- ✅ **n8n Integration**: Workflow management and execution working
- ✅ **Playwright Integration**: Browser automation and web scraping operational
- ✅ **TimescaleDB Integration**: Advanced time-series operations functional
- ✅ **Cross-Service Workflows**: Complex multi-tool operations successful
- ✅ **Performance Stable**: No degradation with expanded tool set

### **User Experience**
- ✅ **Natural Language Operations**: AI can perform complex multi-step tasks
- ✅ **Error Handling**: Clear error messages and recovery suggestions
- ✅ **Documentation**: Comprehensive usage examples and troubleshooting
- ✅ **Monitoring**: Complete observability of all tool operations

## 🔄 Migration Strategy

### **Backward Compatibility**
- **Existing Tools**: All 12 current tools remain functional
- **Configuration**: Existing environment files extended, not replaced
- **API Endpoints**: No breaking changes to current endpoints
- **Documentation**: Current docs preserved, enhanced with new content

### **Rollback Plan**
```bash
# If expansion fails, rollback to current state
cd /home/administrator/projects/mcp/server
git checkout main  # Revert to working implementation
docker compose restart  # Restart with original 12 tools
```

### **Gradual Rollout**
1. **Phase A**: Deploy n8n tools first (lowest risk)
2. **Phase B**: Add TimescaleDB tools (using existing implementation base)
3. **Phase C**: Integrate Playwright tools (highest complexity)
4. **Phase D**: Complete cross-service testing and optimization

## 📋 Resource Requirements

### **Development Resources**
- **Implementation Time**: 12 days estimated
- **Testing Resources**: Comprehensive tool validation matrix
- **Documentation Updates**: Multiple files across project

### **Infrastructure Impact**
- **Container Resources**: Minimal increase (same container, more tools)
- **Network Requirements**: Additional service connections (n8n, TimescaleDB)
- **Storage**: Configuration and log storage increase

### **Dependencies**
- **External Services**: n8n instance, TimescaleDB instance (both operational)
- **Browser Dependencies**: Chromium/Playwright for browser automation
- **Network Connectivity**: All target services accessible via Docker networks

## 🚀 Implementation Priority

### **High Priority**
1. **n8n Integration** - Workflow automation adds immediate value
2. **TimescaleDB Enhancement** - Extend existing working implementation

### **Medium Priority**
3. **Playwright Integration** - Browser automation for web tasks

### **Post-Implementation**
4. **Performance Optimization** - Fine-tune 40+ tool performance
5. **Advanced Features** - Cross-service orchestration capabilities

---

**Expected Result**: Transform our centralized MCP server into a comprehensive 40+ tool AI assistant platform, providing full-stack automation capabilities across databases, workflows, web interactions, monitoring, file operations, and time-series analytics.

**Status**: 🚧 **Ready for Implementation** - All research completed, best implementations identified, integration plan defined.

---
*Created: 2025-09-14*
*Research Phase: Complete*
*Next Step: Begin Phase 1 Implementation*