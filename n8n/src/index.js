#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { 
  CallToolRequestSchema, 
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema 
} from '@modelcontextprotocol/sdk/types.js';
import axios from 'axios';

// Configuration from environment
const N8N_URL = process.env.N8N_URL || 'http://n8n:5678';
const N8N_API_KEY = process.env.N8N_API_KEY || '';

class N8nMCPServer {
  constructor() {
    this.server = new Server(
      {
        name: 'mcp-n8n',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
          resources: {}
        },
      }
    );

    this.setupHandlers();
  }

  setupHandlers() {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'list_workflows',
          description: 'List all workflows in n8n',
          inputSchema: {
            type: 'object',
            properties: {
              active: {
                type: 'boolean',
                description: 'Filter by active status'
              },
              limit: {
                type: 'number',
                description: 'Maximum number of workflows to return (default: 50)',
                default: 50
              }
            }
          }
        },
        {
          name: 'get_workflow',
          description: 'Get details of a specific workflow',
          inputSchema: {
            type: 'object',
            properties: {
              id: {
                type: 'string',
                description: 'Workflow ID or name'
              }
            },
            required: ['id']
          }
        },
        {
          name: 'execute_workflow',
          description: 'Execute a workflow by ID or name',
          inputSchema: {
            type: 'object',
            properties: {
              id: {
                type: 'string',
                description: 'Workflow ID or name to execute'
              },
              data: {
                type: 'object',
                description: 'Optional input data for the workflow',
                default: {}
              }
            },
            required: ['id']
          }
        },
        {
          name: 'get_executions',
          description: 'Get recent workflow executions',
          inputSchema: {
            type: 'object',
            properties: {
              workflow_id: {
                type: 'string',
                description: 'Filter by workflow ID'
              },
              status: {
                type: 'string',
                description: 'Filter by status (success, error, running)',
                enum: ['success', 'error', 'running', 'waiting']
              },
              limit: {
                type: 'number',
                description: 'Maximum number of executions (default: 20)',
                default: 20
              }
            }
          }
        },
        {
          name: 'get_execution_details',
          description: 'Get details of a specific execution',
          inputSchema: {
            type: 'object',
            properties: {
              execution_id: {
                type: 'string',
                description: 'Execution ID'
              }
            },
            required: ['execution_id']
          }
        },
        {
          name: 'create_webhook_test',
          description: 'Create a test payload for a webhook workflow',
          inputSchema: {
            type: 'object',
            properties: {
              webhook_path: {
                type: 'string',
                description: 'The webhook path (e.g., "my-webhook")'
              },
              method: {
                type: 'string',
                description: 'HTTP method (GET, POST, etc.)',
                default: 'POST',
                enum: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
              },
              data: {
                type: 'object',
                description: 'Payload data to send',
                default: {}
              }
            },
            required: ['webhook_path']
          }
        },
        {
          name: 'activate_workflow',
          description: 'Activate a workflow',
          inputSchema: {
            type: 'object',
            properties: {
              id: {
                type: 'string',
                description: 'Workflow ID to activate'
              }
            },
            required: ['id']
          }
        },
        {
          name: 'deactivate_workflow',
          description: 'Deactivate a workflow',
          inputSchema: {
            type: 'object',
            properties: {
              id: {
                type: 'string',
                description: 'Workflow ID to deactivate'
              }
            },
            required: ['id']
          }
        }
      ]
    }));

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case 'list_workflows':
            return await this.listWorkflows(args);
          case 'get_workflow':
            return await this.getWorkflow(args);
          case 'execute_workflow':
            return await this.executeWorkflow(args);
          case 'get_executions':
            return await this.getExecutions(args);
          case 'get_execution_details':
            return await this.getExecutionDetails(args);
          case 'create_webhook_test':
            return await this.createWebhookTest(args);
          case 'activate_workflow':
            return await this.activateWorkflow(args);
          case 'deactivate_workflow':
            return await this.deactivateWorkflow(args);
          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        return {
          content: [{
            type: 'text',
            text: `Error: ${error.message}`
          }]
        };
      }
    });

    // List available resources
    this.server.setRequestHandler(ListResourcesRequestSchema, async () => ({
      resources: [
        {
          uri: 'n8n://workflows',
          name: 'All Workflows',
          description: 'List of all workflows in n8n',
          mimeType: 'application/json'
        },
        {
          uri: 'n8n://executions/recent',
          name: 'Recent Executions',
          description: 'Recent workflow execution history',
          mimeType: 'application/json'
        },
        {
          uri: 'n8n://status',
          name: 'n8n Status',
          description: 'Current n8n instance status',
          mimeType: 'application/json'
        }
      ]
    }));

    // Handle resource reads
    this.server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
      const { uri } = request.params;

      if (uri === 'n8n://workflows') {
        const workflows = await this.listWorkflows({ limit: 100 });
        return {
          contents: [{
            uri,
            mimeType: 'application/json',
            text: JSON.stringify(JSON.parse(workflows.content[0].text), null, 2)
          }]
        };
      } else if (uri === 'n8n://executions/recent') {
        const executions = await this.getExecutions({ limit: 50 });
        return {
          contents: [{
            uri,
            mimeType: 'application/json',
            text: JSON.stringify(JSON.parse(executions.content[0].text), null, 2)
          }]
        };
      } else if (uri === 'n8n://status') {
        const status = await this.getSystemStatus();
        return {
          contents: [{
            uri,
            mimeType: 'application/json',
            text: JSON.stringify(status, null, 2)
          }]
        };
      }

      throw new Error(`Unknown resource: ${uri}`);
    });
  }

  // Helper method to make API requests
  async makeRequest(method, endpoint, data = null, params = null) {
    const config = {
      method,
      url: `${N8N_URL}/api/v1${endpoint}`,
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      },
      params,
      data
    };

    // Add API key if configured
    if (N8N_API_KEY) {
      config.headers['X-N8N-API-KEY'] = N8N_API_KEY;
    }

    try {
      const response = await axios(config);
      return response.data;
    } catch (error) {
      if (error.response) {
        throw new Error(`n8n API error: ${error.response.status} - ${error.response.statusText}`);
      } else if (error.request) {
        throw new Error(`Cannot connect to n8n at ${N8N_URL}. Is it running?`);
      }
      throw error;
    }
  }

  // Tool implementations
  async listWorkflows(args) {
    const { active, limit = 50 } = args;
    
    const params = { limit };
    if (active !== undefined) {
      params.active = active;
    }

    try {
      const workflows = await this.makeRequest('GET', '/workflows', null, params);
      
      // Format the response
      const formatted = workflows.data.map(w => ({
        id: w.id,
        name: w.name,
        active: w.active,
        createdAt: w.createdAt,
        updatedAt: w.updatedAt,
        nodes: w.nodes ? w.nodes.length : 0,
        tags: w.tags || []
      }));

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            count: formatted.length,
            workflows: formatted
          }, null, 2)
        }]
      };
    } catch (error) {
      throw new Error(`Failed to list workflows: ${error.message}`);
    }
  }

  async getWorkflow(args) {
    const { id } = args;

    try {
      const workflow = await this.makeRequest('GET', `/workflows/${id}`);
      
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            id: workflow.id,
            name: workflow.name,
            active: workflow.active,
            nodes: workflow.nodes,
            connections: workflow.connections,
            settings: workflow.settings,
            tags: workflow.tags
          }, null, 2)
        }]
      };
    } catch (error) {
      throw new Error(`Failed to get workflow: ${error.message}`);
    }
  }

  async executeWorkflow(args) {
    const { id, data = {} } = args;

    try {
      const execution = await this.makeRequest('POST', `/workflows/${id}/execute`, { data });
      
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            executionId: execution.data.id,
            status: 'started',
            message: `Workflow ${id} execution started`,
            checkStatusWith: `get_execution_details execution_id="${execution.data.id}"`
          }, null, 2)
        }]
      };
    } catch (error) {
      throw new Error(`Failed to execute workflow: ${error.message}`);
    }
  }

  async getExecutions(args) {
    const { workflow_id, status, limit = 20 } = args;
    
    const params = { limit };
    if (workflow_id) {
      params.workflowId = workflow_id;
    }
    if (status) {
      params.status = status;
    }

    try {
      const executions = await this.makeRequest('GET', '/executions', null, params);
      
      const formatted = executions.data.map(e => ({
        id: e.id,
        workflowId: e.workflowId,
        workflowName: e.workflowData?.name,
        status: e.finished ? (e.stoppedAt ? 'error' : 'success') : 'running',
        startedAt: e.startedAt,
        stoppedAt: e.stoppedAt,
        mode: e.mode,
        retryOf: e.retryOf
      }));

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            count: formatted.length,
            executions: formatted
          }, null, 2)
        }]
      };
    } catch (error) {
      throw new Error(`Failed to get executions: ${error.message}`);
    }
  }

  async getExecutionDetails(args) {
    const { execution_id } = args;

    try {
      const execution = await this.makeRequest('GET', `/executions/${execution_id}`);
      
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            id: execution.id,
            workflowId: execution.workflowId,
            status: execution.finished ? (execution.stoppedAt ? 'error' : 'success') : 'running',
            mode: execution.mode,
            startedAt: execution.startedAt,
            stoppedAt: execution.stoppedAt,
            data: execution.data,
            workflowData: {
              name: execution.workflowData?.name,
              nodes: execution.workflowData?.nodes?.length
            }
          }, null, 2)
        }]
      };
    } catch (error) {
      throw new Error(`Failed to get execution details: ${error.message}`);
    }
  }

  async createWebhookTest(args) {
    const { webhook_path, method = 'POST', data = {} } = args;

    // For webhook testing, we'll use the webhook endpoint
    const webhookUrl = `${N8N_URL}/webhook/${webhook_path}`;
    
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          test_url: webhookUrl,
          method: method,
          curl_command: `curl -X ${method} '${webhookUrl}' -H 'Content-Type: application/json' -d '${JSON.stringify(data)}'`,
          data: data,
          note: 'Execute this curl command or use execute_workflow to test the webhook'
        }, null, 2)
      }]
    };
  }

  async activateWorkflow(args) {
    const { id } = args;

    try {
      const workflow = await this.makeRequest('PATCH', `/workflows/${id}`, { active: true });
      
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            success: true,
            message: `Workflow ${workflow.name} (${id}) activated`,
            active: workflow.active
          }, null, 2)
        }]
      };
    } catch (error) {
      throw new Error(`Failed to activate workflow: ${error.message}`);
    }
  }

  async deactivateWorkflow(args) {
    const { id } = args;

    try {
      const workflow = await this.makeRequest('PATCH', `/workflows/${id}`, { active: false });
      
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            success: true,
            message: `Workflow ${workflow.name} (${id}) deactivated`,
            active: workflow.active
          }, null, 2)
        }]
      };
    } catch (error) {
      throw new Error(`Failed to deactivate workflow: ${error.message}`);
    }
  }

  async getSystemStatus() {
    try {
      // Try to get workflows as a health check
      const workflows = await this.makeRequest('GET', '/workflows', null, { limit: 1 });
      
      return {
        status: 'online',
        url: N8N_URL,
        api_configured: !!N8N_API_KEY,
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      return {
        status: 'error',
        url: N8N_URL,
        api_configured: !!N8N_API_KEY,
        error: error.message,
        timestamp: new Date().toISOString()
      };
    }
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('MCP n8n Server running on stdio');
  }
}

// Start the server
const server = new N8nMCPServer();
server.run().catch(console.error);