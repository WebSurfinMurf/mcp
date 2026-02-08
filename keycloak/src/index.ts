#!/usr/bin/env node
/**
 * MCP Keycloak Server
 * Provides Keycloak client credential management via MCP protocol
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

import { KeycloakClient, createClientFromEnv } from './keycloak/client.js';
import * as createClientTool from './tools/create-client.js';
import * as getClientSecretTool from './tools/get-client-secret.js';
import * as addGroupsMapperTool from './tools/add-groups-mapper.js';
import * as listClientsTool from './tools/list-clients.js';

// Tool definitions for registration
const tools = [
  {
    name: createClientTool.name,
    description: createClientTool.description,
    inputSchema: {
      type: 'object' as const,
      properties: {
        clientId: {
          type: 'string',
          description: 'Unique identifier for the client',
        },
        name: {
          type: 'string',
          description: 'Human-readable name (defaults to clientId)',
        },
        description: {
          type: 'string',
          description: 'Description of the client',
        },
        redirectUris: {
          type: 'array',
          items: { type: 'string' },
          description: 'Valid redirect URIs',
        },
        webOrigins: {
          type: 'array',
          items: { type: 'string' },
          description: 'Allowed CORS origins',
        },
        serviceAccountsEnabled: {
          type: 'boolean',
          description: 'Enable service account',
        },
        standardFlowEnabled: {
          type: 'boolean',
          description: 'Enable authorization code flow',
        },
        directAccessGrantsEnabled: {
          type: 'boolean',
          description: 'Enable direct access grants',
        },
      },
      required: ['clientId'],
    },
  },
  {
    name: getClientSecretTool.name,
    description: getClientSecretTool.description,
    inputSchema: {
      type: 'object' as const,
      properties: {
        clientId: {
          type: 'string',
          description: 'The clientId of the client',
        },
      },
      required: ['clientId'],
    },
  },
  {
    name: addGroupsMapperTool.name,
    description: addGroupsMapperTool.description,
    inputSchema: {
      type: 'object' as const,
      properties: {
        clientId: {
          type: 'string',
          description: 'The clientId to add mapper to',
        },
        mapperName: {
          type: 'string',
          description: 'Name for the mapper (default: groups)',
        },
        claimName: {
          type: 'string',
          description: 'Claim name in token (default: groups)',
        },
        fullPath: {
          type: 'boolean',
          description: 'Include full group path',
        },
      },
      required: ['clientId'],
    },
  },
  {
    name: listClientsTool.name,
    description: listClientsTool.description,
    inputSchema: {
      type: 'object' as const,
      properties: {
        search: {
          type: 'string',
          description: 'Search filter',
        },
        first: {
          type: 'number',
          description: 'Pagination offset',
        },
        max: {
          type: 'number',
          description: 'Maximum results',
        },
      },
      required: [],
    },
  },
];

/**
 * Main server initialization
 */
async function main() {
  // Create Keycloak client from environment variables
  let keycloakClient: KeycloakClient;
  try {
    keycloakClient = createClientFromEnv();
  } catch (error) {
    console.error('Failed to initialize Keycloak client:', error);
    process.exit(1);
  }

  // Create MCP server
  const server = new Server(
    {
      name: 'mcp-keycloak',
      version: '1.0.0',
    },
    {
      capabilities: {
        tools: {},
      },
    }
  );

  // Register tools/list handler
  server.setRequestHandler(ListToolsRequestSchema, async () => {
    return { tools };
  });

  // Register tools/call handler
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    try {
      let result: string;

      switch (name) {
        case createClientTool.name: {
          const validated = createClientTool.inputSchema.parse(args);
          result = await createClientTool.execute(keycloakClient, validated);
          break;
        }

        case getClientSecretTool.name: {
          const validated = getClientSecretTool.inputSchema.parse(args);
          result = await getClientSecretTool.execute(keycloakClient, validated);
          break;
        }

        case addGroupsMapperTool.name: {
          const validated = addGroupsMapperTool.inputSchema.parse(args);
          result = await addGroupsMapperTool.execute(keycloakClient, validated);
          break;
        }

        case listClientsTool.name: {
          const validated = listClientsTool.inputSchema.parse(args);
          result = await listClientsTool.execute(keycloakClient, validated);
          break;
        }

        default:
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify({ error: `Unknown tool: ${name}` }),
              },
            ],
            isError: true,
          };
      }

      return {
        content: [
          {
            type: 'text',
            text: result,
          },
        ],
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({ error: message }),
          },
        ],
        isError: true,
      };
    }
  });

  // Start server with stdio transport
  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error('MCP Keycloak server started');
}

// Run
main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
