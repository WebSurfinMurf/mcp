import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { 
  CallToolRequestSchema, 
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema 
} from '@modelcontextprotocol/sdk/types.js';
import axios from 'axios';
import { subHours, formatISO } from 'date-fns';

// Configuration from environment
const LOKI_URL = process.env.LOKI_URL || 'http://localhost:3100';
const NETDATA_URL = process.env.NETDATA_URL || 'http://localhost:19999';
const DEFAULT_LIMIT = parseInt(process.env.DEFAULT_LIMIT || '100');
const DEFAULT_HOURS = parseInt(process.env.DEFAULT_HOURS || '24');

class ObservabilityServer {
  constructor() {
    this.server = new Server(
      {
        name: 'mcp-observability',
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
          name: 'search_logs',
          description: 'Search logs using LogQL query language',
          inputSchema: {
            type: 'object',
            properties: {
              query: {
                type: 'string',
                description: 'LogQL query (e.g., {container_name="nginx"} |= "error")'
              },
              hours: {
                type: 'number',
                description: 'Hours to look back (default: 24)',
                default: 24
              },
              limit: {
                type: 'number',
                description: 'Maximum results to return (default: 100)',
                default: 100
              }
            },
            required: ['query']
          }
        },
        {
          name: 'get_recent_errors',
          description: 'Get recent error-level logs from all containers',
          inputSchema: {
            type: 'object',
            properties: {
              hours: {
                type: 'number',
                description: 'Hours to look back (default: 1)',
                default: 1
              },
              container: {
                type: 'string',
                description: 'Optional: specific container name'
              }
            }
          }
        },
        {
          name: 'get_container_logs',
          description: 'Get logs for a specific container',
          inputSchema: {
            type: 'object',
            properties: {
              container_name: {
                type: 'string',
                description: 'Name of the container'
              },
              hours: {
                type: 'number',
                description: 'Hours to look back (default: 1)',
                default: 1
              },
              filter: {
                type: 'string',
                description: 'Optional text filter'
              }
            },
            required: ['container_name']
          }
        },
        {
          name: 'get_system_metrics',
          description: 'Get current system metrics from Netdata',
          inputSchema: {
            type: 'object',
            properties: {
              charts: {
                type: 'array',
                items: { type: 'string' },
                description: 'Specific charts to retrieve (default: ["system.cpu", "system.ram", "disk.util"])',
                default: ['system.cpu', 'system.ram', 'disk.util']
              },
              after: {
                type: 'number',
                description: 'Seconds to look back (default: 300)',
                default: 300
              }
            }
          }
        },
        {
          name: 'check_service_health',
          description: 'Check health of a specific service using logs and metrics',
          inputSchema: {
            type: 'object',
            properties: {
              service_name: {
                type: 'string',
                description: 'Name of the service/container'
              },
              check_errors: {
                type: 'boolean',
                description: 'Check for recent errors (default: true)',
                default: true
              },
              check_restarts: {
                type: 'boolean',
                description: 'Check for recent restarts (default: true)',
                default: true
              }
            },
            required: ['service_name']
          }
        }
      ]
    }));

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case 'search_logs':
            return await this.searchLogs(args);
          case 'get_recent_errors':
            return await this.getRecentErrors(args);
          case 'get_container_logs':
            return await this.getContainerLogs(args);
          case 'get_system_metrics':
            return await this.getSystemMetrics(args);
          case 'check_service_health':
            return await this.checkServiceHealth(args);
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
          uri: 'logs://recent',
          name: 'Recent Logs',
          description: 'Stream of recent log entries from all containers',
          mimeType: 'application/json'
        },
        {
          uri: 'metrics://current',
          name: 'Current Metrics',
          description: 'Current system metrics snapshot',
          mimeType: 'application/json'
        }
      ]
    }));

    // Handle resource reads
    this.server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
      const { uri } = request.params;

      if (uri === 'logs://recent') {
        const logs = await this.getRecentLogs();
        return {
          contents: [{
            uri,
            mimeType: 'application/json',
            text: JSON.stringify(logs, null, 2)
          }]
        };
      } else if (uri === 'metrics://current') {
        const metrics = await this.getCurrentMetrics();
        return {
          contents: [{
            uri,
            mimeType: 'application/json',
            text: JSON.stringify(metrics, null, 2)
          }]
        };
      }

      throw new Error(`Unknown resource: ${uri}`);
    });
  }

  // Tool implementations
  async searchLogs(args) {
    const { query, hours = DEFAULT_HOURS, limit = DEFAULT_LIMIT } = args;
    
    const end = new Date();
    const start = subHours(end, hours);
    
    const params = {
      query,
      start: start.getTime() * 1000000, // nanoseconds
      end: end.getTime() * 1000000,
      limit,
      direction: 'backward'
    };

    try {
      const response = await axios.get(`${LOKI_URL}/loki/api/v1/query_range`, { params });
      const results = this.formatLokiResults(response.data);
      
      return {
        content: [{
          type: 'text',
          text: JSON.stringify(results, null, 2)
        }]
      };
    } catch (error) {
      throw new Error(`Loki query failed: ${error.message}`);
    }
  }

  async getRecentErrors(args) {
    const { hours = 1, container } = args;
    
    let query = '{job="containerlogs"}';
    if (container) {
      query += ` |= "${container}"`;
    }
    query += ' |~ "(?i)(error|exception|fatal|critical|fail)"';
    
    return this.searchLogs({ query, hours, limit: 200 });
  }

  async getContainerLogs(args) {
    const { container_name, hours = 1, filter } = args;
    
    let query = `{container_name="${container_name}"}`;
    if (filter) {
      query += ` |= "${filter}"`;
    }
    
    return this.searchLogs({ query, hours });
  }

  async getSystemMetrics(args) {
    const { charts = ['system.cpu', 'system.ram', 'disk.util'], after = 300 } = args;
    
    try {
      const results = {};
      
      for (const chart of charts) {
        const response = await axios.get(`${NETDATA_URL}/api/v1/data`, {
          params: {
            chart,
            after: -after,
            format: 'json',
            points: 60
          }
        });
        
        results[chart] = {
          labels: response.data.labels,
          data: response.data.data,
          min: response.data.min,
          max: response.data.max,
          latest: response.data.latest_values
        };
      }
      
      return {
        content: [{
          type: 'text',
          text: JSON.stringify(results, null, 2)
        }]
      };
    } catch (error) {
      throw new Error(`Netdata query failed: ${error.message}`);
    }
  }

  async checkServiceHealth(args) {
    const { service_name, check_errors = true, check_restarts = true } = args;
    
    const health = {
      service: service_name,
      timestamp: new Date().toISOString(),
      checks: {}
    };

    // Check for recent errors
    if (check_errors) {
      const errors = await this.getRecentErrors({ hours: 1, container: service_name });
      const errorData = JSON.parse(errors.content[0].text);
      health.checks.recent_errors = {
        count: errorData.total_entries || 0,
        status: errorData.total_entries > 0 ? 'warning' : 'healthy'
      };
    }

    // Check for restarts
    if (check_restarts) {
      const restartQuery = `{container_name="${service_name}"} |= "started" | json`;
      const restarts = await this.searchLogs({ query: restartQuery, hours: 24 });
      const restartData = JSON.parse(restarts.content[0].text);
      health.checks.recent_restarts = {
        count: restartData.total_entries || 0,
        status: restartData.total_entries > 1 ? 'warning' : 'healthy'
      };
    }

    // Overall health
    const hasWarnings = Object.values(health.checks).some(c => c.status === 'warning');
    health.overall_status = hasWarnings ? 'degraded' : 'healthy';

    return {
      content: [{
        type: 'text',
        text: JSON.stringify(health, null, 2)
      }]
    };
  }

  // Helper methods
  formatLokiResults(data) {
    if (!data.data || !data.data.result) {
      return { total_entries: 0, streams: [] };
    }

    let totalEntries = 0;
    const streams = data.data.result.map(stream => {
      const entries = stream.values.map(([timestamp, line]) => ({
        timestamp: new Date(parseInt(timestamp) / 1000000).toISOString(),
        line
      }));
      totalEntries += entries.length;
      
      return {
        labels: stream.stream,
        entries
      };
    });

    return {
      total_entries: totalEntries,
      streams
    };
  }

  async getRecentLogs() {
    const query = '{job="containerlogs"}';
    const result = await this.searchLogs({ query, hours: 1, limit: 50 });
    return JSON.parse(result.content[0].text);
  }

  async getCurrentMetrics() {
    const result = await this.getSystemMetrics({});
    return JSON.parse(result.content[0].text);
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('MCP Observability Server running on stdio');
  }
}

// Start the server
const server = new ObservabilityServer();
server.run().catch(console.error);