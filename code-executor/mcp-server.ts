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
const API_KEY = process.env.CODE_EXECUTOR_API_KEY || '';
const SENDER_NAME = process.env.MCP_SENDER_NAME || 'unknown';

// Cached role info from executor
let cachedRole: { name: string; allowed_mcp_tools: string[]; allowed_servers: string[] } | null = null;

async function getRole(): Promise<typeof cachedRole> {
  if (cachedRole) return cachedRole;
  if (!API_KEY) return null;
  try {
    const resp = await fetch(`${API_URL}/roles?key=${API_KEY}`);
    if (resp.ok) {
      cachedRole = await resp.json();
    }
  } catch {
    // Role endpoint not available, allow all
  }
  return cachedRole;
}

// Helper to add API key header to all executor requests
function apiHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (API_KEY) headers['X-API-Key'] = API_KEY;
  if (extra) Object.assign(headers, extra);
  return headers;
}

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

interface CreateGitLabIssueArgs {
  project_id: number;
  title: string;
  description?: string;
  labels?: string[];
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

// All tool definitions
const ALL_TOOLS = [
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
        description: `Send a message to the shared Matrix chat room. YOUR IDENTITY is "${SENDER_NAME}" — you are NOT any of the agents listed in chat_who (those are separate agent containers). Messages you send appear as the gateway user, not your own Matrix account. Addressing: "@username" for humans (e.g. "@websurfinmurf"), "@Agent name" for AI agents (e.g. "@Agent claude-administrator"), or no prefix for broadcast to all.`,
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
        description: `List online AI agent instances in the Matrix chat room. Shows instance names, types, and status. YOUR IDENTITY is "${SENDER_NAME}" — you are a CLI session, NOT one of the listed agent instances.`,
        inputSchema: {
          type: 'object',
          properties: {},
        },
      },
      {
        name: 'create_gitlab_issue',
        description: 'Create a new issue on a GitLab project. Returns issue URL, ID, and labels. Use for alignment fixes, task tracking, and automated issue creation on project boards.',
        inputSchema: {
          type: 'object',
          properties: {
            project_id: {
              type: 'number',
              description: 'GitLab project ID (e.g., 35 for aiagentchat)',
            },
            title: {
              type: 'string',
              description: 'Issue title',
            },
            description: {
              type: 'string',
              description: 'Issue description in markdown format',
            },
            labels: {
              type: 'array',
              items: { type: 'string' },
              description: 'Labels to apply (e.g., ["alignment-fix"])',
            },
          },
          required: ['project_id', 'title'],
        },
      },
];

// List available tools (filtered by role)
server.setRequestHandler(ListToolsRequestSchema, async () => {
  const role = await getRole();
  let tools = ALL_TOOLS;
  if (role && !role.allowed_mcp_tools.includes('*')) {
    tools = ALL_TOOLS.filter(t => role.allowed_mcp_tools.includes(t.name));
  }
  return { tools };
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
          headers: apiHeaders(),
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

        const response = await fetch(`${API_URL}/tools/search?${params}`, { headers: apiHeaders() });
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

        const response = await fetch(`${API_URL}/tools/info/${serverName}/${tool}?${params}`, { headers: apiHeaders() });
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
        const response = await fetch(`${API_URL}/health`, { headers: apiHeaders() });
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
          headers: apiHeaders(),
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
        const response = await fetch(`${API_URL}/reviewboard/health`, { headers: apiHeaders() });
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
          headers: apiHeaders(),
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

        const response = await fetch(`${API_URL}/chat/read?count=${clampedCount}`, { headers: apiHeaders() });
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
        const response = await fetch(`${API_URL}/chat/who`, { headers: apiHeaders() });
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

      case 'create_gitlab_issue': {
        const { project_id, title, description, labels } = args as CreateGitLabIssueArgs;

        const response = await fetch(`${API_URL}/gitlab/create-issue`, {
          method: 'POST',
          headers: apiHeaders(),
          body: JSON.stringify({ project_id, title, description, labels }),
        });

        const result = await response.json();

        if (!response.ok) {
          return {
            content: [
              {
                type: 'text',
                text: `GitLab issue creation failed: ${result.error || JSON.stringify(result)}`,
              },
            ],
            isError: true,
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
