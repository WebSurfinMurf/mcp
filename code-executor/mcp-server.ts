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
  requestor?: string;
  timeout?: number;
}

interface ChatSendArgs {
  message: string;
  to?: string;
}

interface ChatReadArgs {
  count?: number;
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
        name: 'dispatch_to_reviewboard',
        description: 'Dispatch a prompt to an AI Review Board node (Gemini, Codex, or Claude) for execution. Each node runs in a Docker container with read-only access to all user home directories under /workspace/{username}/. Use this to delegate tasks to other AI agents.',
        inputSchema: {
          type: 'object',
          properties: {
            prompt: {
              type: 'string',
              description: 'The prompt/task to send to the Review Board node',
            },
            target: {
              type: 'string',
              enum: ['gemini', 'codex', 'claude'],
              description: 'Target AI: gemini (Google), codex (OpenAI), or claude (Anthropic)',
            },
            requestor: {
              type: 'string',
              description: 'Linux username of the requestor (e.g. "administrator", "websurfinmurf"). Sets the working directory to /workspace/{requestor}/projects/.',
              default: 'administrator',
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
        name: 'reviewboard_health',
        description: 'Check health status of all AI Review Board nodes (Gemini, Codex, Claude).',
        inputSchema: {
          type: 'object',
          properties: {},
        },
      },
      {
        name: 'chat_send',
        description: 'Send a message to the shared Matrix chat room. Use this for inter-session communication with humans and AI agents. Addressing: "@username" for humans (e.g. "@websurfinmurf"), "@Agent name" for AI agents (e.g. "@Agent claude-administrator"), or no prefix for broadcast to all.',
        inputSchema: {
          type: 'object',
          properties: {
            message: {
              type: 'string',
              description: 'The message to send. Include @username or @Agent name prefix to direct to a specific recipient.',
            },
            to: {
              type: 'string',
              description: 'Optional: target agent name for direct room delivery (e.g. "claude-administrator"). If omitted, sends to the shared broadcast room.',
            },
          },
          required: ['message'],
        },
      },
      {
        name: 'chat_read',
        description: 'Read recent messages from the shared Matrix chat room. Returns messages from all participants (humans and AI agents).',
        inputSchema: {
          type: 'object',
          properties: {
            count: {
              type: 'number',
              description: 'Number of recent messages to retrieve (default: 20, max: 100)',
              default: 20,
            },
          },
        },
      },
      {
        name: 'chat_who',
        description: 'List online AI agent instances in the Matrix chat room. Shows instance names, types, and status.',
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

      case 'dispatch_to_reviewboard': {
        const { prompt, target, requestor = 'administrator', timeout = 900 } = args as SwarmDispatchArgs;
        const working_dir = `/workspace/${requestor}/projects`;

        const response = await fetch(`${API_URL}/reviewboard/dispatch`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt, target, timeout, working_dir }),
        });

        const result = await response.json();

        if (!result.success) {
          return {
            content: [
              {
                type: 'text',
                text: `Review Board dispatch to ${target} failed: ${result.error}`,
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

      case 'reviewboard_health': {
        const response = await fetch(`${API_URL}/reviewboard/health`);
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

      case 'chat_send': {
        const { message, to } = args as ChatSendArgs;

        const body: Record<string, string> = { message };
        if (to) body.to = to;

        const response = await fetch(`${API_URL}/chat/send`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });

        const result = await response.json();

        if (!response.ok) {
          return {
            content: [
              {
                type: 'text',
                text: `Chat send failed: ${result.error || JSON.stringify(result)}`,
              },
            ],
            isError: true,
          };
        }

        return {
          content: [
            {
              type: 'text',
              text: `Message sent. Event ID: ${result.event_id}`,
            },
          ],
        };
      }

      case 'chat_read': {
        const { count = 20 } = args as ChatReadArgs;
        const clampedCount = Math.min(Math.max(1, count), 100);

        const response = await fetch(`${API_URL}/chat/read?count=${clampedCount}`);
        const result = await response.json();

        if (!result.messages || result.messages.length === 0) {
          return {
            content: [
              {
                type: 'text',
                text: 'No recent messages.',
              },
            ],
          };
        }

        const formatted = result.messages.map((msg: any) => {
          const sender = msg.sender || msg.user_id || 'unknown';
          const body = msg.body || msg.content?.body || '';
          const time = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : '';
          return `[${time}] ${sender}: ${body}`;
        }).join('\n');

        return {
          content: [
            {
              type: 'text',
              text: `Recent messages (${result.messages.length}):\n\n${formatted}`,
            },
          ],
        };
      }

      case 'chat_who': {
        const response = await fetch(`${API_URL}/chat/who`);
        const result = await response.json();

        if (!result.instances || result.instances.length === 0) {
          return {
            content: [
              {
                type: 'text',
                text: 'No online instances found.',
              },
            ],
          };
        }

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2),
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
