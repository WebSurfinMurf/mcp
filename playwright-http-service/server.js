const express = require('express');
const cors = require('cors');
const { chromium } = require('playwright');

const app = express();
const PORT = process.env.PORT || 8080;

// Middleware
app.use(express.json({ limit: '10mb' }));
app.use(cors());

// Browser management
let browser = null;
let isInitializing = false;

// Initialize persistent browser instance
async function initializeBrowser() {
  if (browser || isInitializing) return browser;

  isInitializing = true;
  console.log('🎭 Initializing persistent Playwright browser...');

  try {
    browser = await chromium.launch({
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--no-first-run',
        '--no-zygote',
        '--disable-gpu'
      ]
    });

    console.log('✅ Browser initialized successfully');

    // Handle browser disconnection
    browser.on('disconnected', () => {
      console.log('⚠️ Browser disconnected, will reinitialize on next request');
      browser = null;
    });

    return browser;
  } catch (error) {
    console.error('❌ Failed to initialize browser:', error);
    browser = null;
    throw error;
  } finally {
    isInitializing = false;
  }
}

// Ensure browser is available for requests
async function ensureBrowser() {
  if (!browser) {
    await initializeBrowser();
  }
  return browser;
}

// Health check endpoint
app.get('/health', (req, res) => {
  const status = browser ? 'ready' : 'initializing';
  res.json({
    status: 'ok',
    service: 'playwright-http-service',
    browser: status,
    timestamp: new Date().toISOString()
  });
});

// Service info endpoint
app.get('/info', (req, res) => {
  res.json({
    service: 'playwright-http-service',
    description: 'Custom HTTP-native Playwright service with persistent browser management',
    version: '1.0.0',
    features: [
      'Persistent browser instance',
      'Isolated page contexts per request',
      'HTTP REST API',
      'Production-ready error handling',
      'Security-first design'
    ],
    endpoints: {
      'GET /health': 'Health check and browser status',
      'GET /info': 'Service information',
      'GET /tools': 'List available tools',
      'POST /tools/navigate': 'Navigate to URL',
      'POST /tools/screenshot': 'Take page screenshot',
      'POST /tools/click': 'Click element',
      'POST /tools/fill': 'Fill form field',
      'POST /tools/evaluate': 'Execute JavaScript',
      'POST /tools/get-content': 'Get page content',
      'POST /tools/wait-for-selector': 'Wait for element'
    }
  });
});

// List available tools
app.get('/tools', (req, res) => {
  res.json({
    service: 'playwright-http-service',
    tools: [
      {
        name: 'navigate',
        description: 'Navigate to a URL and wait for page load',
        parameters: ['url', 'wait_for_load', 'timeout']
      },
      {
        name: 'screenshot',
        description: 'Take a screenshot of the current page',
        parameters: ['full_page', 'clip', 'path']
      },
      {
        name: 'click',
        description: 'Click an element on the page',
        parameters: ['selector', 'timeout']
      },
      {
        name: 'fill',
        description: 'Fill a form field with text',
        parameters: ['selector', 'value', 'timeout']
      },
      {
        name: 'evaluate',
        description: 'Execute JavaScript in the page context',
        parameters: ['script', 'args']
      },
      {
        name: 'get-content',
        description: 'Get the text content of the page or an element',
        parameters: ['selector']
      },
      {
        name: 'wait-for-selector',
        description: 'Wait for an element to appear on the page',
        parameters: ['selector', 'timeout', 'state']
      }
    ]
  });
});

// Tool execution wrapper with context management
async function executeWithContext(toolName, handler, req, res) {
  const requestId = Date.now();
  console.log(`[${requestId}] Executing tool: ${toolName}`);

  let context = null;
  let page = null;

  try {
    // Ensure browser is available
    const browserInstance = await ensureBrowser();

    // Create isolated context for this request
    context = await browserInstance.newContext({
      viewport: { width: 1280, height: 720 },
      userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    });

    page = await context.newPage();

    // Execute the tool handler
    const result = await handler(page, req.body.input || {}, requestId);

    console.log(`[${requestId}] Tool ${toolName} completed successfully`);

    res.json({
      tool: toolName,
      result: result,
      requestId: requestId,
      timestamp: new Date().toISOString(),
      status: 'success'
    });

  } catch (error) {
    console.error(`[${requestId}] Tool ${toolName} failed:`, error.message);

    res.status(500).json({
      tool: toolName,
      error: error.message,
      requestId: requestId,
      timestamp: new Date().toISOString(),
      status: 'error'
    });

  } finally {
    // Always clean up context
    if (context) {
      try {
        await context.close();
        console.log(`[${requestId}] Context cleaned up`);
      } catch (cleanupError) {
        console.error(`[${requestId}] Context cleanup error:`, cleanupError.message);
      }
    }
  }
}

// Navigate tool
app.post('/tools/navigate', async (req, res) => {
  await executeWithContext('navigate', async (page, input, requestId) => {
    const { url, wait_for_load = true, timeout = 30000 } = input;

    if (!url) {
      throw new Error('URL parameter is required');
    }

    console.log(`[${requestId}] Navigating to: ${url}`);

    const response = await page.goto(url, {
      waitUntil: wait_for_load ? 'domcontentloaded' : 'commit',
      timeout: timeout
    });

    const title = await page.title();
    const finalUrl = page.url();

    return {
      success: true,
      url: finalUrl,
      title: title,
      status: response.status(),
      statusText: response.statusText()
    };
  }, req, res);
});

// Screenshot tool
app.post('/tools/screenshot', async (req, res) => {
  await executeWithContext('screenshot', async (page, input, requestId) => {
    const { full_page = false, clip = null, format = 'png' } = input;

    console.log(`[${requestId}] Taking screenshot (full_page: ${full_page})`);

    const screenshotOptions = {
      fullPage: full_page,
      type: format
    };

    if (clip) {
      screenshotOptions.clip = clip;
    }

    const screenshot = await page.screenshot(screenshotOptions);
    const base64 = screenshot.toString('base64');

    return {
      success: true,
      screenshot: `data:image/${format};base64,${base64}`,
      format: format,
      size: screenshot.length
    };
  }, req, res);
});

// Click tool
app.post('/tools/click', async (req, res) => {
  await executeWithContext('click', async (page, input, requestId) => {
    const { selector, timeout = 30000 } = input;

    if (!selector) {
      throw new Error('Selector parameter is required');
    }

    console.log(`[${requestId}] Clicking element: ${selector}`);

    await page.click(selector, { timeout: timeout });

    return {
      success: true,
      selector: selector,
      action: 'clicked'
    };
  }, req, res);
});

// Fill tool
app.post('/tools/fill', async (req, res) => {
  await executeWithContext('fill', async (page, input, requestId) => {
    const { selector, value, timeout = 30000 } = input;

    if (!selector || value === undefined) {
      throw new Error('Selector and value parameters are required');
    }

    console.log(`[${requestId}] Filling element ${selector} with: ${value.substring(0, 50)}...`);

    await page.fill(selector, value, { timeout: timeout });

    return {
      success: true,
      selector: selector,
      action: 'filled',
      valueLength: value.length
    };
  }, req, res);
});

// Evaluate JavaScript tool
app.post('/tools/evaluate', async (req, res) => {
  await executeWithContext('evaluate', async (page, input, requestId) => {
    const { script, args = [] } = input;

    if (!script) {
      throw new Error('Script parameter is required');
    }

    console.log(`[${requestId}] Evaluating JavaScript: ${script.substring(0, 100)}...`);

    const result = await page.evaluate(script, ...args);

    return {
      success: true,
      result: result,
      script: script.substring(0, 100) + (script.length > 100 ? '...' : '')
    };
  }, req, res);
});

// Get content tool
app.post('/tools/get-content', async (req, res) => {
  await executeWithContext('get-content', async (page, input, requestId) => {
    const { selector = null } = input;

    console.log(`[${requestId}] Getting content${selector ? ` for selector: ${selector}` : ' (full page)'}`);

    let content;
    if (selector) {
      content = await page.textContent(selector);
    } else {
      content = await page.textContent('body');
    }

    return {
      success: true,
      content: content,
      selector: selector || 'body',
      length: content ? content.length : 0
    };
  }, req, res);
});

// Wait for selector tool
app.post('/tools/wait-for-selector', async (req, res) => {
  await executeWithContext('wait-for-selector', async (page, input, requestId) => {
    const { selector, timeout = 30000, state = 'visible' } = input;

    if (!selector) {
      throw new Error('Selector parameter is required');
    }

    console.log(`[${requestId}] Waiting for selector: ${selector} (state: ${state})`);

    const element = await page.waitForSelector(selector, {
      state: state,
      timeout: timeout
    });

    const isVisible = await element.isVisible();
    const isEnabled = await element.isEnabled();

    return {
      success: true,
      selector: selector,
      found: true,
      visible: isVisible,
      enabled: isEnabled,
      state: state
    };
  }, req, res);
});

// Global error handler
app.use((error, req, res, next) => {
  console.error('Unhandled error:', error);
  res.status(500).json({
    error: 'Internal server error',
    message: error.message,
    timestamp: new Date().toISOString()
  });
});

// Graceful shutdown
async function gracefulShutdown() {
  console.log('🛑 Shutting down gracefully...');

  if (browser) {
    try {
      await browser.close();
      console.log('✅ Browser closed successfully');
    } catch (error) {
      console.error('❌ Error closing browser:', error);
    }
  }

  process.exit(0);
}

process.on('SIGTERM', gracefulShutdown);
process.on('SIGINT', gracefulShutdown);

// Start server
app.listen(PORT, async () => {
  console.log(`🎭 Playwright HTTP Service running on port ${PORT}`);
  console.log(`📡 Health check: http://localhost:${PORT}/health`);
  console.log(`ℹ️  Service info: http://localhost:${PORT}/info`);
  console.log(`🔧 Tools list: http://localhost:${PORT}/tools`);
  console.log(`⚙️  Features: Persistent browser, isolated contexts, production-ready`);

  // Initialize browser on startup
  try {
    await initializeBrowser();
    console.log('🚀 Service ready for requests');
  } catch (error) {
    console.error('❌ Failed to initialize browser on startup:', error);
    console.log('⚠️  Browser will initialize on first request');
  }
});