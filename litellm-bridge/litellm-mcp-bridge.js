#!/usr/bin/env node

/**
 * LiteLLM MCP Bridge for Claude Code
 * Bridges Claude Code's stdio interface to LiteLLM's MCP SSE endpoints
 */

const { spawn } = require('child_process');
const readline = require('readline');
const https = require('https');
const http = require('http');

// Configuration
const LITELLM_HOST = 'litellm.ai-servicers.com';
const LITELLM_API_KEY = 'sk-e0b742bc6575adf26c7d356c49c78d8fd08119fcde1d6e188d753999b5f956fc';

// Log to file for debugging
const fs = require('fs');
const logFile = '/tmp/litellm-mcp-bridge.log';
const log = (msg) => {
  const timestamp = new Date().toISOString();
  fs.appendFileSync(logFile, `[${timestamp}] ${msg}\n`);
};

log('LiteLLM MCP Bridge starting...');

// Set up readline interface for stdio
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

// Handle incoming JSON-RPC requests from Claude Code
rl.on('line', async (line) => {
  try {
    const request = JSON.parse(line);
    log(`Received request: ${JSON.stringify(request)}`);
    
    // Handle different MCP methods
    switch(request.method) {
      case 'initialize':
        handleInitialize(request);
        break;
      case 'notifications/initialized':
        handleInitialized(request);
        break;
      case 'tools/list':
        handleToolsList(request);
        break;
      case 'tools/call':
        handleToolCall(request);
        break;
      case 'prompts/list':
        handlePromptsList(request);
        break;
      default:
        sendError(request.id, -32601, `Method not found: ${request.method}`);
    }
  } catch (error) {
    log(`Error processing request: ${error.message}`);
    sendError(null, -32700, 'Parse error');
  }
});

function handleInitialize(request) {
  const response = {
    jsonrpc: '2.0',
    id: request.id,
    result: {
      protocolVersion: '2024-11-05',
      capabilities: {
        tools: {},
        prompts: {}
      },
      serverInfo: {
        name: 'litellm-mcp-bridge',
        version: '1.0.0'
      }
    }
  };
  
  sendResponse(response);
}

function handleInitialized(request) {
  // This is a notification, no response needed
  log('Received initialization notification');
}

function handlePromptsList(request) {
  // Return empty prompts list
  const response = {
    jsonrpc: '2.0',
    id: request.id,
    result: {
      prompts: []
    }
  };
  
  sendResponse(response);
}

function handleToolsList(request) {
  // Return available MCP tools from LiteLLM
  const tools = [
    {
      name: 'postgres_list_databases',
      description: 'List all PostgreSQL databases',
      inputSchema: {
        type: 'object',
        properties: {
          include_size: { type: 'boolean', default: true }
        }
      }
    },
    {
      name: 'postgres_execute_sql',
      description: 'Execute SQL query',
      inputSchema: {
        type: 'object',
        properties: {
          query: { type: 'string' },
          database: { type: 'string', default: 'postgres' }
        },
        required: ['query']
      }
    },
    {
      name: 'postgres_list_tables',
      description: 'List tables in a database',
      inputSchema: {
        type: 'object',
        properties: {
          database: { type: 'string', default: 'postgres' }
        }
      }
    },
    {
      name: 'postgres_table_info',
      description: 'Get detailed table information',
      inputSchema: {
        type: 'object',
        properties: {
          table: { type: 'string' },
          database: { type: 'string', default: 'postgres' }
        },
        required: ['table']
      }
    },
    {
      name: 'postgres_query_stats',
      description: 'Get query performance statistics',
      inputSchema: {
        type: 'object',
        properties: {
          database: { type: 'string', default: 'postgres' }
        }
      }
    }
  ];
  
  const response = {
    jsonrpc: '2.0',
    id: request.id,
    result: {
      tools: tools
    }
  };
  
  sendResponse(response);
}

async function handleToolCall(request) {
  const { name, arguments: args } = request.params;
  log(`Calling tool: ${name} with args: ${JSON.stringify(args)}`);
  
  try {
    // Call LiteLLM API with MCP tool
    const result = await callLiteLLMTool(name, args);
    
    const response = {
      jsonrpc: '2.0',
      id: request.id,
      result: {
        content: [
          {
            type: 'text',
            text: JSON.stringify(result, null, 2)
          }
        ]
      }
    };
    
    sendResponse(response);
  } catch (error) {
    sendError(request.id, -32603, `Tool execution failed: ${error.message}`);
  }
}

// Store tool schemas for proper LiteLLM calls
const TOOL_SCHEMAS = {
  postgres_list_databases: {
    type: 'object',
    properties: {
      include_size: { type: 'boolean', default: true }
    }
  },
  postgres_execute_sql: {
    type: 'object',
    properties: {
      query: { type: 'string' },
      database: { type: 'string', default: 'postgres' }
    },
    required: ['query']
  },
  postgres_list_tables: {
    type: 'object',
    properties: {
      database: { type: 'string', default: 'postgres' }
    }
  },
  postgres_table_info: {
    type: 'object',
    properties: {
      table: { type: 'string' },
      database: { type: 'string', default: 'postgres' }
    },
    required: ['table']
  },
  postgres_query_stats: {
    type: 'object',
    properties: {
      database: { type: 'string', default: 'postgres' }
    }
  }
};

async function callLiteLLMTool(toolName, args) {
  return new Promise((resolve, reject) => {
    const schema = TOOL_SCHEMAS[toolName];
    if (!schema) {
      reject(new Error(`No schema found for tool: ${toolName}`));
      return;
    }

    const postData = JSON.stringify({
      model: 'gpt-4o-mini',
      messages: [
        {
          role: 'user',
          content: `Use the MCP tool ${toolName} with these arguments: ${JSON.stringify(args)}`
        }
      ],
      tools: [
        {
          type: 'function',
          function: {
            name: toolName,
            parameters: schema
          }
        }
      ],
      tool_choice: {
        type: 'function',
        function: { name: toolName }
      }
    });
    
    const options = {
      hostname: LITELLM_HOST,
      path: '/v1/chat/completions',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': postData.length,
        'Authorization': `Bearer ${LITELLM_API_KEY}`
      }
    };
    
    const req = https.request(options, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        try {
          const response = JSON.parse(data);
          if (response.choices && response.choices[0].message.tool_calls) {
            const toolResult = response.choices[0].message.tool_calls[0].function.arguments;
            resolve(JSON.parse(toolResult));
          } else {
            resolve(response);
          }
        } catch (error) {
          reject(error);
        }
      });
    });
    
    req.on('error', (error) => {
      reject(error);
    });
    
    req.write(postData);
    req.end();
  });
}

function sendResponse(response) {
  const responseStr = JSON.stringify(response);
  log(`Sending response: ${responseStr}`);
  console.log(responseStr);
}

function sendError(id, code, message) {
  const error = {
    jsonrpc: '2.0',
    id: id,
    error: {
      code: code,
      message: message
    }
  };
  sendResponse(error);
}

// Handle process termination
process.on('SIGINT', () => {
  log('Bridge shutting down...');
  process.exit(0);
});

process.on('uncaughtException', (error) => {
  log(`Uncaught exception: ${error.stack}`);
  process.exit(1);
});

log('LiteLLM MCP Bridge ready');