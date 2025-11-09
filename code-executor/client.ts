#!/usr/bin/env tsx
/**
 * MCP Client Library - HTTP connection to MCP proxy
 *
 * Provides simple interface for calling MCP tools from execution sandbox
 */

const MCP_PROXY_URL = process.env.MCP_PROXY_URL || 'http://mcp-proxy:9090';
const REQUEST_TIMEOUT = 30000; // 30 seconds

interface MCPRequest {
  jsonrpc: '2.0';
  id: string;
  method: string;
  params: any;
}

interface MCPResponse<T = any> {
  jsonrpc: '2.0';
  id: string;
  result?: T;
  error?: {
    code: number;
    message: string;
    data?: any;
  };
}

/**
 * Call an MCP tool via the proxy
 */
export async function callMCPTool<T = any>(
  server: string,
  toolName: string,
  input: any
): Promise<T> {
  const requestId = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  const request: MCPRequest = {
    jsonrpc: '2.0',
    id: requestId,
    method: 'tools/call',
    params: {
      name: toolName,
      arguments: input
    }
  };

  const url = `${MCP_PROXY_URL}/${server}/mcp`;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const mcpResponse: MCPResponse<T> = await response.json();

    if (mcpResponse.error) {
      throw new Error(
        `MCP Error ${mcpResponse.error.code}: ${mcpResponse.error.message}`
      );
    }

    return mcpResponse.result as T;
  } catch (error: any) {
    if (error.name === 'AbortError') {
      throw new Error(`MCP tool call timed out after ${REQUEST_TIMEOUT}ms`);
    }
    throw new Error(`MCP tool call failed: ${error.message}`);
  }
}

/**
 * List available tools from an MCP server
 */
export async function listTools(server: string): Promise<any[]> {
  const requestId = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  const request: MCPRequest = {
    jsonrpc: '2.0',
    id: requestId,
    method: 'tools/list',
    params: {}
  };

  const url = `${MCP_PROXY_URL}/${server}/mcp`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request)
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const mcpResponse: MCPResponse = await response.json();

    if (mcpResponse.error) {
      throw new Error(
        `MCP Error ${mcpResponse.error.code}: ${mcpResponse.error.message}`
      );
    }

    return mcpResponse.result?.tools || [];
  } catch (error: any) {
    throw new Error(`Failed to list tools: ${error.message}`);
  }
}

/**
 * Initialize MCP session (optional, for servers that require it)
 */
export async function initializeSession(server: string): Promise<void> {
  const requestId = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  const request: MCPRequest = {
    jsonrpc: '2.0',
    id: requestId,
    method: 'initialize',
    params: {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: {
        name: 'mcp-code-executor',
        version: '1.0.0'
      }
    }
  };

  const url = `${MCP_PROXY_URL}/${server}/mcp`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request)
  });

  if (!response.ok) {
    console.warn(`Failed to initialize ${server}: ${response.statusText}`);
  }
}
