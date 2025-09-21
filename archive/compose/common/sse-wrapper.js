#!/usr/bin/env node
/**
 * SSE Wrapper for stdio-based MCP servers
 * Converts stdio MCP servers to SSE/HTTP endpoints
 */

const { spawn } = require('child_process');
const express = require('express');
const { v4: uuidv4 } = require('uuid');
const readline = require('readline');

class MCPSSEWrapper {
  constructor(command, args = [], env = {}) {
    this.command = command;
    this.args = args;
    this.env = { ...process.env, ...env };
    this.sessions = new Map();
    this.app = express();
    this.setupRoutes();
  }

  setupRoutes() {
    this.app.use(express.json());
    
    // CORS headers for browser clients
    this.app.use((req, res, next) => {
      res.header('Access-Control-Allow-Origin', '*');
      res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
      res.header('Access-Control-Allow-Headers', 'Content-Type, Accept');
      if (req.method === 'OPTIONS') {
        return res.sendStatus(200);
      }
      next();
    });
    
    // SSE endpoint - creates a new session
    this.app.get('/sse', (req, res) => {
      console.log('[SSE] New connection request');
      
      res.setHeader('Content-Type', 'text/event-stream');
      res.setHeader('Cache-Control', 'no-cache');
      res.setHeader('Connection', 'keep-alive');
      res.setHeader('X-Accel-Buffering', 'no'); // Disable nginx buffering
      
      const sessionId = uuidv4();
      const session = this.createSession(sessionId);
      
      if (!session) {
        console.error('[SSE] Failed to create session');
        res.status(500).end();
        return;
      }
      
      this.sessions.set(sessionId, session);
      
      // Send session endpoint
      res.write(`event: endpoint\n`);
      res.write(`data: /messages/${sessionId}\n\n`);
      
      // Keep connection alive
      const keepAlive = setInterval(() => {
        res.write(`:keepalive\n\n`);
      }, 30000);
      
      // Clean up on disconnect
      req.on('close', () => {
        console.log(`[SSE] Connection closed for session ${sessionId}`);
        clearInterval(keepAlive);
        this.closeSession(sessionId);
      });
    });
    
    // Message endpoint - handles JSON-RPC requests
    this.app.post('/messages/:sessionId', async (req, res) => {
      const { sessionId } = req.params;
      const session = this.sessions.get(sessionId);
      
      console.log(`[MSG] Request for session ${sessionId}:`, JSON.stringify(req.body).substring(0, 100));
      
      if (!session) {
        console.error(`[MSG] Session not found: ${sessionId}`);
        return res.status(404).json({ 
          jsonrpc: '2.0',
          error: { code: -32000, message: 'Session not found' },
          id: req.body.id 
        });
      }
      
      try {
        const result = await this.sendToMCP(session, req.body);
        console.log(`[MSG] Response:`, JSON.stringify(result).substring(0, 100));
        res.json(result);
      } catch (error) {
        console.error(`[MSG] Error:`, error);
        res.status(500).json({ 
          jsonrpc: '2.0',
          error: { code: -32603, message: error.message },
          id: req.body.id 
        });
      }
    });
    
    // Health check endpoint
    this.app.get('/health', (req, res) => {
      const health = {
        status: 'healthy',
        sessions: this.sessions.size,
        uptime: process.uptime(),
        command: this.command,
        args: this.args
      };
      res.json(health);
    });
    
    // Root endpoint
    this.app.get('/', (req, res) => {
      res.json({
        service: 'MCP SSE Wrapper',
        version: '1.0.0',
        endpoints: {
          sse: '/sse',
          health: '/health'
        },
        sessions: this.sessions.size
      });
    });
  }

  createSession(sessionId) {
    console.log(`[SESSION] Creating session ${sessionId}`);
    console.log(`[SESSION] Command: ${this.command} ${this.args.join(' ')}`);
    
    try {
      const mcpProcess = spawn(this.command, this.args, {
        env: this.env,
        stdio: ['pipe', 'pipe', 'pipe']
      });
      
      const session = {
        id: sessionId,
        process: mcpProcess,
        buffer: '',
        callbacks: new Map(),
        initialized: false
      };
      
      // Create readline interface for parsing JSON responses
      const rl = readline.createInterface({
        input: mcpProcess.stdout,
        crlfDelay: Infinity
      });
      
      rl.on('line', (line) => {
        console.log(`[STDOUT] ${sessionId}:`, line.substring(0, 200));
        
        try {
          const response = JSON.parse(line);
          
          // Check if this is a response to one of our requests
          if (response.id && session.callbacks.has(response.id)) {
            const callback = session.callbacks.get(response.id);
            session.callbacks.delete(response.id);
            callback.resolve(response);
          }
        } catch (e) {
          // Not JSON or not a complete response
          session.buffer += line + '\n';
        }
      });
      
      // Handle stderr
      mcpProcess.stderr.on('data', (data) => {
        console.error(`[STDERR] ${sessionId}:`, data.toString());
      });
      
      // Handle process exit
      mcpProcess.on('exit', (code, signal) => {
        console.log(`[PROCESS] ${sessionId} exited with code ${code}, signal ${signal}`);
        // Don't immediately close session for stdio servers that exit normally
        if (code !== 0) {
          this.closeSession(sessionId);
        }
      });
      
      mcpProcess.on('error', (error) => {
        console.error(`[PROCESS] ${sessionId} error:`, error);
        this.closeSession(sessionId);
      });
      
      // Send initialization
      setTimeout(() => {
        this.initializeSession(session);
      }, 100);
      
      return session;
      
    } catch (error) {
      console.error(`[SESSION] Failed to create session:`, error);
      return null;
    }
  }
  
  async initializeSession(session) {
    console.log(`[INIT] Initializing session ${session.id}`);
    
    // Send initialize request
    const initRequest = {
      jsonrpc: '2.0',
      method: 'initialize',
      params: {
        protocolVersion: '0.1.0',
        capabilities: {}
      },
      id: 'init-' + session.id
    };
    
    try {
      const response = await this.sendToMCP(session, initRequest);
      console.log(`[INIT] Session ${session.id} initialized:`, response);
      session.initialized = true;
    } catch (error) {
      console.error(`[INIT] Failed to initialize session ${session.id}:`, error);
    }
  }

  async sendToMCP(session, message) {
    return new Promise((resolve, reject) => {
      const messageId = message.id || uuidv4();
      const timeout = setTimeout(() => {
        if (session.callbacks.has(messageId)) {
          session.callbacks.delete(messageId);
          reject(new Error('MCP request timeout'));
        }
      }, 30000); // 30 second timeout
      
      session.callbacks.set(messageId, { 
        resolve: (response) => {
          clearTimeout(timeout);
          resolve(response);
        },
        reject: (error) => {
          clearTimeout(timeout);
          reject(error);
        }
      });
      
      // Ensure message has an ID
      const messageWithId = { ...message, id: messageId };
      
      console.log(`[SEND] ${session.id}:`, JSON.stringify(messageWithId).substring(0, 200));
      session.process.stdin.write(JSON.stringify(messageWithId) + '\n');
    });
  }

  closeSession(sessionId) {
    console.log(`[SESSION] Closing session ${sessionId}`);
    const session = this.sessions.get(sessionId);
    if (session) {
      try {
        session.process.kill('SIGTERM');
        setTimeout(() => {
          if (!session.process.killed) {
            session.process.kill('SIGKILL');
          }
        }, 5000);
      } catch (error) {
        console.error(`[SESSION] Error closing session ${sessionId}:`, error);
      }
      this.sessions.delete(sessionId);
    }
  }

  start(port = 8080, host = '0.0.0.0') {
    this.app.listen(port, host, () => {
      console.log(`[WRAPPER] MCP SSE Wrapper listening on ${host}:${port}`);
      console.log(`[WRAPPER] Command: ${this.command} ${this.args.join(' ')}`);
      console.log(`[WRAPPER] Endpoints:`);
      console.log(`[WRAPPER]   SSE: http://${host}:${port}/sse`);
      console.log(`[WRAPPER]   Health: http://${host}:${port}/health`);
    });
  }
}

// Export for use as module
module.exports = MCPSSEWrapper;

// If run directly, start a wrapper based on command line args
if (require.main === module) {
  const args = process.argv.slice(2);
  
  if (args.length < 1) {
    console.error('Usage: node sse-wrapper.js <command> [args...]');
    console.error('Example: node sse-wrapper.js node /path/to/mcp-server.js');
    process.exit(1);
  }
  
  const command = args[0];
  const commandArgs = args.slice(1);
  const port = process.env.PORT || 8080;
  const host = process.env.HOST || '0.0.0.0';
  
  const wrapper = new MCPSSEWrapper(command, commandArgs);
  wrapper.start(port, host);
}