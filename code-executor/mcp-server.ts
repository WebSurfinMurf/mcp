#!/usr/bin/env node
/**
 * MCP Code Executor - MCP Server Integration
 *
 * Exposes the code executor as an MCP server for Claude Code CLI integration.
 * This allows Claude to execute complex workflows and multi-tool operations
 * with progressive disclosure for optimal context efficiency.
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

const API_URL = process.env.CODE_EXECUTOR_URL || 'http://localhost:9091';

interface ExecuteCodeArgs {
  code: string;
  timeout?: number;
}

interface SearchToolsArgs {
  query?: string;
  server?: string;
  detail?: 'name' | 'description' | 'full';
}

interface GetToolInfoArgs {
  server: string;
  tool: string;
  detail?: 'name' | 'description' | 'full';
}

interface SwarmDispatchArgs {
  prompt: string;
  target: 'gemini' | 'codex' | 'claude';
  timeout?: number;
}

const server = new Server(
  {
    name: 'code-executor',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'execute_code',
        description: 'Execute TypeScript/JavaScript code with access to all MCP tools. Supports multi-tool workflows, data filtering, and complex operations. Returns execution output and metrics.',
        inputSchema: {
          type: 'object',
          properties: {
            code: {
              type: 'string',
              description: 'TypeScript/JavaScript code to execute. Can import MCP tool wrappers from /workspace/servers/{server}/{tool}.js',
            },
            timeout: {
              type: 'number',
              description: 'Execution timeout in milliseconds (default: 30000)',
              default: 30000,
            },
          },
          required: ['code'],
        },
      },
      {
        name: 'search_tools',
        description: 'Search available MCP tools with progressive disclosure. Use detail="name" for minimal tokens, detail="description" for more context, detail="full" for complete source code.',
        inputSchema: {
          type: 'object',
          properties: {
            query: {
              type: 'string',
              description: 'Search query to filter tools by name or description',
            },
            server: {
              type: 'string',
              description: 'Filter by specific MCP server (e.g., "filesystem", "postgres", "timescaledb")',
            },
            detail: {
              type: 'string',
              enum: ['name', 'description', 'full'],
              description: 'Level of detail: name (minimal tokens), description (with docs), full (complete source)',
              default: 'name',
            },
          },
        },
      },
      {
        name: 'get_tool_info',
        description: 'Get detailed information about a specific MCP tool with progressive disclosure.',
        inputSchema: {
          type: 'object',
          properties: {
            server: {
              type: 'string',
              description: 'MCP server name (e.g., "filesystem", "postgres")',
            },
            tool: {
              type: 'string',
              description: 'Tool name (e.g., "read_file", "execute_query")',
            },
            detail: {
              type: 'string',
              enum: ['name', 'description', 'full'],
              description: 'Level of detail to retrieve',
              default: 'description',
            },
          },
          required: ['server', 'tool'],
        },
      },
      {
        name: 'list_mcp_tools',
        description: 'List all available MCP tools across all servers. Returns tool names and servers for discovery.',
        inputSchema: {
          type: 'object',
          properties: {},
        },
      },
      {
        name: 'dispatch_to_swarm',
        description: 'Dispatch a prompt to an AI swarm node (Gemini, Codex, or Claude) for execution. Each node runs in a Docker container with access to the /workspace directory. Use this to delegate tasks to other AI agents.',
        inputSchema: {
          type: 'object',
          properties: {
            prompt: {
              type: 'string',
              description: 'The prompt/task to send to the swarm node',
            },
            target: {
              type: 'string',
              enum: ['gemini', 'codex', 'claude'],
              description: 'Target AI: gemini (Google), codex (OpenAI), or claude (Anthropic)',
            },
            timeout: {
              type: 'number',
              description: 'Timeout in seconds (default: 900 = 15 minutes)',
              default: 900,
            },
          },
          required: ['prompt', 'target'],
        },
      },
      {
        name: 'swarm_health',
        description: 'Check health status of all AI swarm nodes (Gemini, Codex, Claude).',
        inputSchema: {
          type: 'object',
          properties: {},
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'execute_code': {
        const { code, timeout = 30000 } = args as ExecuteCodeArgs;

        const response = await fetch(`${API_URL}/execute`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code, timeout }),
        });

        if (!response.ok) {
          const error = await response.json();
          return {
            content: [
              {
                type: 'text',
                text: `Execution failed: ${error.error || error.message}`,
              },
            ],
            isError: true,
          };
        }

        const result = await response.json();

        return {
          content: [
            {
              type: 'text',
              text: result.error
                ? `Error: ${result.error}\n\nExecution time: ${result.executionTime}ms`
                : `${result.output}\n\nExecution time: ${result.executionTime}ms | Output: ${result.metrics.outputBytes} bytes (~${result.metrics.tokensEstimate} tokens)`,
            },
          ],
        };
      }

      case 'search_tools': {
        const { query, server: serverFilter, detail = 'name' } = args as SearchToolsArgs;

        const params = new URLSearchParams();
        if (query) params.set('query', query);
        if (serverFilter) params.set('server', serverFilter);
        params.set('detail', detail);

        const response = await fetch(`${API_URL}/tools/search?${params}`);
        const result = await response.json();

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case 'get_tool_info': {
        const { server: serverName, tool, detail = 'description' } = args as GetToolInfoArgs;

        const params = new URLSearchParams();
        params.set('detail', detail);

        const response = await fetch(`${API_URL}/tools/info/${serverName}/${tool}?${params}`);
        const result = await response.json();

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case 'list_mcp_tools': {
        const response = await fetch(`${API_URL}/health`);
        const health = await response.json();

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                servers: health.servers,
                totalTools: health.totalTools,
                toolsByServer: health.toolsByServer,
              }, null, 2),
            },
          ],
        };
      }

      case 'dispatch_to_swarm': {
        const { prompt, target, timeout = 900 } = args as SwarmDispatchArgs;

        const response = await fetch(`${API_URL}/swarm/dispatch`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt, target, timeout }),
        });

        const result = await response.json();

        if (!result.success) {
          return {
            content: [
              {
                type: 'text',
                text: `Swarm dispatch to ${target} failed: ${result.error}`,
              },
            ],
            isError: true,
          };
        }

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                target,
                success: result.success,
                result: result.result,
                metrics: result.metrics,
              }, null, 2),
            },
          ],
        };
      }

      case 'swarm_health': {
        const response = await fetch(`${API_URL}/swarm/health`);
        const health = await response.json();

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(health, null, 2),
            },
          ],
        };
      }

      default:
        return {
          content: [
            {
              type: 'text',
              text: `Unknown tool: ${name}`,
            },
          ],
          isError: true,
        };
    }
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error calling ${name}: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // Note: No logging here - stdio transport requires clean stdout/stderr
}

main().catch((error) => {
  console.error('Server error:', error);
  process.exit(1);
});
