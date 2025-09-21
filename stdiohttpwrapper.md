Of course. Here is a complete, step-by-step guide for your AI, Claude Code, on how to implement the `stdio`-to-HTTP wrapper for the `mcp-fetch` tool.

-----

**To:** Claude Code (Implementation Team)
**From:** Gemini (Project Architect)
**Subject:** Guide for Implementing the `mcp-fetch` HTTP Adapter

Hello Claude. This document provides the complete plan for containerizing the `stdio`-based `mcp-fetch` tool and wrapping it with a standard Node.js HTTP adapter. This will make it fully compatible with our LiteLLM MCP Gateway.

Please follow these steps precisely to create and deploy the service.

### \#\# 1. Objective & Architecture

**Objective:** To create a self-contained Docker service for `mcp-fetch` that exposes a simple, request/response HTTP API, hiding the underlying `stdio` protocol.

**Final Container Architecture:**

```plaintext
                  +----------------------------------------------+
(HTTP Request)    |           mcp-fetch Docker Container         |
 from LiteLLM ---->|                                              |
                  | +-----------------+      +-----------------+ |
                  | |  Adapter        |----->| Fetch Tool      | |
                  | | (Node.js/Express)|(stdio)| (Python Script) | |
                  | +-----------------+      +-----------------+ |
(HTTP Response)   |                                              |
 back to LiteLLM <----|                                              |
                  +----------------------------------------------+
```

### \#\# 2. Prerequisites

1.  Confirm the official `mcp-fetch` tool from the `modelcontextprotocol/servers` repository has been downloaded. We will assume the main script is named `fetch_server.py` and its dependencies are listed in `requirements.txt`.

### \#\# 3. Project Setup

**3.1. Create Directory Structure and Place Files:**

Execute the following commands to create the standardized project structure.

```bash
# Define the project directory
FETCH_DIR="/home/administrator/projects/mcp/fetch"

# Create the directory
mkdir -p "$FETCH_DIR"

# Instruction: Place the downloaded 'fetch_server.py' and its 'requirements.txt'
# into the FETCH_DIR. We will assume they are now present.
# Example: cp /path/to/download/fetch_server.py "$FETCH_DIR"/
# Example: cp /path/to/download/requirements.txt "$FETCH_DIR"/
```

### \#\# 4. Create the Adapter and Configuration Files

Create the following files inside the `/home/administrator/projects/mcp/fetch/` directory.

**4.1. `adapter.js` (The HTTP Wrapper):**
This is the universal adapter template, configured specifically for the Python-based fetch tool.

```javascript
// adapter.js
const express = require('express');
const { spawn } = require('child_process');
const app = express();
const PORT = 8080;

// --- CONFIGURATION for the stdio tool ---
const TOOL_COMMAND = 'python3';
const TOOL_ARGS = ['fetch_server.py'];
// -----------------------------------------

app.use(express.json());

app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok', service: 'mcp-fetch-adapter' });
});

app.post('/mcp', (req, res) => {
  console.log(`[FETCH] Adapter received request, spawning stdio process...`);
  const mcpProcess = spawn(TOOL_COMMAND, TOOL_ARGS);

  let stdoutData = '';
  let stderrData = '';

  mcpProcess.stdout.on('data', (data) => (stdoutData += data.toString()));
  mcpProcess.stderr.on('data', (data) => (stderrData += data.toString()));

  mcpProcess.on('close', (code) => {
    console.log(`[FETCH] Stdio process exited with code ${code}`);
    if (code !== 0) {
      return res.status(500).json({ error: 'MCP tool process failed', details: stderrData });
    }
    try {
      const responses = stdoutData.trim().split('\n');
      const lastResponse = responses[responses.length - 1];
      res.setHeader('Content-Type', 'application/json');
      res.send(lastResponse);
    } catch (e) {
      res.status(500).json({ error: 'Failed to parse MCP response', details: stdoutData });
    }
  });

  mcpProcess.stdin.write(JSON.stringify(req.body) + '\n');
  mcpProcess.stdin.end();
});

app.listen(PORT, () => {
  console.log(`[FETCH] Stdio-to-HTTP adapter listening on port ${PORT}`);
});
```

**4.2. `package.json` (Node.js Dependencies):**

```json
{
  "name": "mcp-fetch-adapter",
  "version": "1.0.0",
  "description": "HTTP adapter for stdio mcp-fetch tool",
  "main": "adapter.js",
  "scripts": {
    "start": "node adapter.js"
  },
  "dependencies": {
    "express": "^4.19.2"
  }
}
```

**4.3. `Dockerfile` (Container Definition):**
This `Dockerfile` builds a single container that includes both the Python runtime for the tool and the Node.js runtime for our adapter.

```dockerfile
# /home/administrator/projects/mcp/fetch/Dockerfile

# Use a Node.js base image as it's a good starting point
FROM node:22-bookworm-slim
WORKDIR /app

# --- Install Python and pip ---
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# --- Install the Python-based Fetch Tool ---
COPY requirements.txt fetch_server.py ./
RUN pip3 install --no-cache-dir -r requirements.txt

# --- Install the Node.js Adapter ---
COPY package.json package-lock.json* ./
RUN npm install

# Copy the adapter code itself
COPY adapter.js ./

# --- Finalization ---
# Expose the port the adapter listens on
EXPOSE 8080

# The command to start the container is to run our adapter server
CMD ["node", "adapter.js"]
```

### \#\#\# 5. Create the Deployment File

Create a `docker-compose.yml` file to manage this service as part of your tool fleet.

  * **File:** `/home/administrator/projects/mcp/docker-compose.yml` (or your central tools file)

<!-- end list -->

```yaml
services:
  # ... your other tool services (mcp-postgresql, etc.) ...

  mcp-fetch:
    build: ./fetch  # Tells Docker Compose to build from the 'fetch' directory
    container_name: mcp-fetch
    restart: unless-stopped
    networks:
      - mcp-tools-net
    ports:
      - "8083:8080" # Host port : Container port
```

### \#\#\# 6. Deploy & Verify

**6.1. Build and Run the Container:**
From the `/home/administrator/projects/mcp/` directory, run:

```bash
docker-compose up -d --build mcp-fetch
```

**6.2. Verify It's Running:**

```bash
docker ps | grep mcp-fetch
curl http://localhost:8083/health
```

You should see the container running and the health check should return `{"status":"ok"}`.

### \#\#\# 7. Integrate with LiteLLM

Finally, register the newly adapted and accessible tool in your LiteLLM `config.yaml`.

```yaml
# In /home/administrator/projects/litellm/config.yaml

mcp_servers:
  # ... your other mcp_servers (postgres, etc.) ...
  fetch:
    transport: http
    # The URL points to the internal Docker network address of the adapter
    url: http://mcp-fetch:8080/mcp 
    description: "Fetches and processes web content via a stdio adapter."
```

After restarting LiteLLM, the `fetch` tool will now be available to all your clients. This guide provides the complete pattern for wrapping any `stdio`-based tool.
