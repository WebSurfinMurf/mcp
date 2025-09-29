# MCP Service Documentation Template

## 📋 Project Overview
- Service name:
- Purpose:
- Primary transports: stdio / SSE

## 🟢 Current State
- Status (✅ / ⚠️ / ❌):
- Last validated:
- SSE endpoint:
- Stdio entry point:

## 📝 Recent Work & Changes
- YYYY-MM-DD: summary of change / deployment

## 🏗️ Architecture
- Containers and images:
- Networks:
- Ports (host → container):

## ⚙️ Configuration
- Environment file: `secrets/<service>.env`
- Key settings:

## 🌐 Access & Management
- Health check command:
- Claude CLI registration command:
- Stdio smoke test command:

## 🔗 Integration Points
- Upstream dependencies:
- Downstream clients (Claude, Codex, etc.):

## 🛠️ Operations
- Deploy/restart commands:
- Log locations:
- Backup/restore notes:

## 🔧 Troubleshooting
- Common issues and fixes:

## 📋 Standards & Best Practices
- Security notes:
- Coding guidelines:

## 🔐 Backup & Security
- Secrets handled:
- Rotation procedure:

## 🔄 Related Services
- Other MCP services using similar pattern:

---
*Copy this template to `mcp/<service>/CLAUDE.md` and populate after each deployment.*
