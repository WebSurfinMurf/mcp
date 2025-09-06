import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { 
  CallToolRequestSchema, 
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema 
} from '@modelcontextprotocol/sdk/types.js';
import axios from 'axios';
import WebSocket from 'ws';
import { v4 as uuidv4 } from 'uuid';
import { formatISO, subHours } from 'date-fns';

// Configuration from environment
const PLAYWRIGHT_URL = process.env.PLAYWRIGHT_URL || 'http://localhost:3000';
const PLAYWRIGHT_WS_URL = process.env.PLAYWRIGHT_WS_URL || 'ws://localhost:3000';
const DEFAULT_TIMEOUT = parseInt(process.env.DEFAULT_TIMEOUT || '30000');

class PlaywrightMCPServer {
  constructor() {
    this.server = new Server(
      {
        name: 'mcp-playwright',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
          resources: {}
        },
      }
    );

    this.wsConnections = new Map();
    this.setupHandlers();
  }

  setupHandlers() {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'run_browser_test',
          description: 'Execute a browser automation test with Playwright',
          inputSchema: {
            type: 'object',
            properties: {
              script: {
                type: 'string',
                description: 'JavaScript code to execute using Playwright'
              },
              browser: {
                type: 'string',
                description: 'Browser type: chromium, firefox, or webkit',
                enum: ['chromium', 'firefox', 'webkit'],
                default: 'chromium'
              },
              headless: {
                type: 'boolean',
                description: 'Run browser in headless mode',
                default: true
              },
              viewport: {
                type: 'object',
                description: 'Viewport size',
                properties: {
                  width: { type: 'number', default: 1280 },
                  height: { type: 'number', default: 720 }
                }
              },
              timeout: {
                type: 'number',
                description: 'Test timeout in milliseconds',
                default: 30000
              },
              takeScreenshot: {
                type: 'boolean',
                description: 'Take screenshot on completion',
                default: false
              },
              recordVideo: {
                type: 'boolean',
                description: 'Record video of the test',
                default: false
              }
            },
            required: ['script']
          }
        },
        {
          name: 'navigate_and_screenshot',
          description: 'Navigate to a URL and take a screenshot',
          inputSchema: {
            type: 'object',
            properties: {
              url: {
                type: 'string',
                description: 'URL to navigate to'
              },
              browser: {
                type: 'string',
                description: 'Browser type',
                enum: ['chromium', 'firefox', 'webkit'],
                default: 'chromium'
              },
              fullPage: {
                type: 'boolean',
                description: 'Take full page screenshot',
                default: false
              },
              selector: {
                type: 'string',
                description: 'CSS selector to screenshot specific element'
              },
              waitFor: {
                type: 'string',
                description: 'Wait condition: networkidle, load, domcontentloaded, or CSS selector',
                default: 'networkidle'
              }
            },
            required: ['url']
          }
        },
        {
          name: 'extract_page_data',
          description: 'Extract data from a web page using selectors',
          inputSchema: {
            type: 'object',
            properties: {
              url: {
                type: 'string',
                description: 'URL to scrape'
              },
              selectors: {
                type: 'object',
                description: 'Object mapping field names to CSS selectors',
                additionalProperties: { type: 'string' }
              },
              browser: {
                type: 'string',
                description: 'Browser type',
                enum: ['chromium', 'firefox', 'webkit'],
                default: 'chromium'
              },
              waitFor: {
                type: 'string',
                description: 'Wait condition before extraction',
                default: 'networkidle'
              }
            },
            required: ['url', 'selectors']
          }
        },
        {
          name: 'fill_form_and_submit',
          description: 'Fill out and submit a web form',
          inputSchema: {
            type: 'object',
            properties: {
              url: {
                type: 'string',
                description: 'URL of the page with the form'
              },
              formData: {
                type: 'object',
                description: 'Object mapping field selectors to values',
                additionalProperties: { type: 'string' }
              },
              submitSelector: {
                type: 'string',
                description: 'CSS selector for submit button',
                default: 'input[type="submit"], button[type="submit"]'
              },
              browser: {
                type: 'string',
                description: 'Browser type',
                enum: ['chromium', 'firefox', 'webkit'],
                default: 'chromium'
              },
              waitAfterSubmit: {
                type: 'number',
                description: 'Milliseconds to wait after form submission',
                default: 3000
              }
            },
            required: ['url', 'formData']
          }
        },
        {
          name: 'get_test_results',
          description: 'Get results from a previous test execution',
          inputSchema: {
            type: 'object',
            properties: {
              testId: {
                type: 'string',
                description: 'Test ID to get results for'
              }
            },
            required: ['testId']
          }
        },
        {
          name: 'list_test_reports',
          description: 'List available test reports',
          inputSchema: {
            type: 'object',
            properties: {
              limit: {
                type: 'number',
                description: 'Maximum number of reports to return',
                default: 10
              },
              browser: {
                type: 'string',
                description: 'Filter by browser type'
              }
            }
          }
        },
        {
          name: 'check_service_health',
          description: 'Check health status of Playwright service',
          inputSchema: {
            type: 'object',
            properties: {}
          }
        }
      ]
    }));

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case 'run_browser_test':
            return await this.runBrowserTest(args);
          case 'navigate_and_screenshot':
            return await this.navigateAndScreenshot(args);
          case 'extract_page_data':
            return await this.extractPageData(args);
          case 'fill_form_and_submit':
            return await this.fillFormAndSubmit(args);
          case 'get_test_results':
            return await this.getTestResults(args);
          case 'list_test_reports':
            return await this.listTestReports(args);
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
          uri: 'playwright://service/status',
          name: 'Service Status',
          description: 'Current status of Playwright service',
          mimeType: 'application/json'
        },
        {
          uri: 'playwright://browsers/available',
          name: 'Available Browsers',
          description: 'List of available browser engines',
          mimeType: 'application/json'
        },
        {
          uri: 'playwright://tests/recent',
          name: 'Recent Test Results',
          description: 'Recent test execution results',
          mimeType: 'application/json'
        }
      ]
    }));

    // Handle resource reads
    this.server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
      const { uri } = request.params;

      if (uri === 'playwright://service/status') {
        const status = await this.getServiceStatus();
        return {
          contents: [{
            uri,
            mimeType: 'application/json',
            text: JSON.stringify(status, null, 2)
          }]
        };
      } else if (uri === 'playwright://browsers/available') {
        const browsers = await this.getAvailableBrowsers();
        return {
          contents: [{
            uri,
            mimeType: 'application/json',
            text: JSON.stringify(browsers, null, 2)
          }]
        };
      } else if (uri === 'playwright://tests/recent') {
        const tests = await this.getRecentTests();
        return {
          contents: [{
            uri,
            mimeType: 'application/json',
            text: JSON.stringify(tests, null, 2)
          }]
        };
      }

      throw new Error(`Unknown resource: ${uri}`);
    });
  }

  // Tool implementations
  async runBrowserTest(args) {
    const {
      script,
      browser = 'chromium',
      headless = true,
      viewport = { width: 1280, height: 720 },
      timeout = DEFAULT_TIMEOUT,
      takeScreenshot = false,
      recordVideo = false
    } = args;

    const testId = uuidv4();
    const payload = {
      testId,
      script,
      browser,
      headless,
      viewport,
      timeout,
      takeScreenshot,
      recordVideo
    };

    try {
      const response = await axios.post(`${PLAYWRIGHT_URL}/api/tests/run`, payload, {
        timeout: timeout + 5000 // Add buffer to request timeout
      });

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            testId: response.data.testId,
            status: response.data.status,
            result: response.data.result,
            artifacts: response.data.artifacts,
            duration: response.data.duration,
            timestamp: response.data.timestamp
          }, null, 2)
        }]
      };
    } catch (error) {
      throw new Error(`Test execution failed: ${error.message}`);
    }
  }

  async navigateAndScreenshot(args) {
    const {
      url,
      browser = 'chromium',
      fullPage = false,
      selector,
      waitFor = 'networkidle'
    } = args;

    const testId = uuidv4();
    const payload = {
      testId,
      url,
      browser,
      fullPage,
      selector,
      waitFor,
      action: 'screenshot'
    };

    try {
      const response = await axios.post(`${PLAYWRIGHT_URL}/api/tests/screenshot`, payload);

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            testId: response.data.testId,
            url: url,
            screenshotPath: response.data.screenshotPath,
            screenshotUrl: response.data.screenshotUrl,
            timestamp: response.data.timestamp
          }, null, 2)
        }]
      };
    } catch (error) {
      throw new Error(`Screenshot failed: ${error.message}`);
    }
  }

  async extractPageData(args) {
    const {
      url,
      selectors,
      browser = 'chromium',
      waitFor = 'networkidle'
    } = args;

    const testId = uuidv4();
    const payload = {
      testId,
      url,
      selectors,
      browser,
      waitFor,
      action: 'extract'
    };

    try {
      const response = await axios.post(`${PLAYWRIGHT_URL}/api/tests/extract`, payload);

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            testId: response.data.testId,
            url: url,
            data: response.data.data,
            timestamp: response.data.timestamp
          }, null, 2)
        }]
      };
    } catch (error) {
      throw new Error(`Data extraction failed: ${error.message}`);
    }
  }

  async fillFormAndSubmit(args) {
    const {
      url,
      formData,
      submitSelector = 'input[type="submit"], button[type="submit"]',
      browser = 'chromium',
      waitAfterSubmit = 3000
    } = args;

    const testId = uuidv4();
    const payload = {
      testId,
      url,
      formData,
      submitSelector,
      browser,
      waitAfterSubmit,
      action: 'form_submit'
    };

    try {
      const response = await axios.post(`${PLAYWRIGHT_URL}/api/tests/form`, payload);

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            testId: response.data.testId,
            url: url,
            success: response.data.success,
            finalUrl: response.data.finalUrl,
            timestamp: response.data.timestamp
          }, null, 2)
        }]
      };
    } catch (error) {
      throw new Error(`Form submission failed: ${error.message}`);
    }
  }

  async getTestResults(args) {
    const { testId } = args;

    try {
      const response = await axios.get(`${PLAYWRIGHT_URL}/api/tests/${testId}`);
      
      return {
        content: [{
          type: 'text',
          text: JSON.stringify(response.data, null, 2)
        }]
      };
    } catch (error) {
      throw new Error(`Failed to get test results: ${error.message}`);
    }
  }

  async listTestReports(args) {
    const { limit = 10, browser } = args;

    try {
      const params = { limit };
      if (browser) params.browser = browser;

      const response = await axios.get(`${PLAYWRIGHT_URL}/api/reports`, { params });
      
      return {
        content: [{
          type: 'text',
          text: JSON.stringify(response.data, null, 2)
        }]
      };
    } catch (error) {
      throw new Error(`Failed to list test reports: ${error.message}`);
    }
  }

  async checkServiceHealth(args) {
    try {
      const response = await axios.get(`${PLAYWRIGHT_URL}/health`);
      
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            status: 'healthy',
            service: response.data,
            timestamp: new Date().toISOString()
          }, null, 2)
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            status: 'unhealthy',
            error: error.message,
            timestamp: new Date().toISOString()
          }, null, 2)
        }]
      };
    }
  }

  // Helper methods
  async getServiceStatus() {
    try {
      const response = await axios.get(`${PLAYWRIGHT_URL}/health`);
      return response.data;
    } catch (error) {
      return { status: 'unhealthy', error: error.message };
    }
  }

  async getAvailableBrowsers() {
    try {
      const response = await axios.get(`${PLAYWRIGHT_URL}/api/browsers`);
      return response.data;
    } catch (error) {
      return { error: error.message };
    }
  }

  async getRecentTests() {
    try {
      const response = await axios.get(`${PLAYWRIGHT_URL}/api/reports?limit=5`);
      return response.data;
    } catch (error) {
      return { error: error.message };
    }
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('MCP Playwright Server running on stdio');
  }
}

// Start the server
const server = new PlaywrightMCPServer();
server.run().catch(console.error);