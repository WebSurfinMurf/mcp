#!/usr/bin/env tsx
/**
 * MCP Code Executor Service
 *
 * HTTP API for executing TypeScript code in sandboxed environment
 * with access to MCP tools via generated wrappers
 */

import Fastify from 'fastify';
import { writeFile, unlink, readdir, readFile } from 'fs/promises';
import { join } from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

const fastify = Fastify({
  logger: {
    level: 'info'
  }
});

const PORT = parseInt(process.env.PORT || '3000');
const EXECUTION_TIMEOUT = parseInt(process.env.EXECUTION_TIMEOUT || '300000'); // 5 minutes
const MAX_OUTPUT_SIZE = 100 * 1024; // 100KB

interface ExecuteRequest {
  code: string;
  timeout?: number;
  language?: 'typescript' | 'python';
}

interface ExecuteResponse {
  output: string;
  error?: string;
  executionTime: number;
  truncated?: boolean;
  metrics?: {
    outputBytes: number;
    tokensEstimate?: number;
  };
}

interface ToolInfo {
  server: string;
  name: string;
  description?: string;
  signature?: string;
  path: string;
  source?: string;
}

interface SearchToolsQuery {
  query?: string;
  server?: string;
  detail?: 'name' | 'description' | 'full';
}

/**
 * Execute TypeScript code
 */
async function executeTypeScript(code: string, timeout: number): Promise<ExecuteResponse> {
  const startTime = Date.now();
  const tempFile = join('/tmp/executions', `exec-${Date.now()}-${Math.random().toString(36).substr(2, 9)}.mts`);

  try {
    // Check if code needs async wrapping (has top-level await but no async wrapper)
    const needsAsyncWrap = /\bawait\s/.test(code) && !/^\s*\(?\s*async\s*\(/.test(code.trim());

    let wrappedCode = code;
    if (needsAsyncWrap) {
      // Split imports from rest of code
      const lines = code.split('\n');
      const imports: string[] = [];
      const rest: string[] = [];

      for (const line of lines) {
        if (line.trim().startsWith('import ') || line.trim().startsWith('export ')) {
          imports.push(line);
        } else {
          rest.push(line);
        }
      }

      // Wrap only the non-import code
      if (imports.length > 0) {
        wrappedCode = `${imports.join('\n')}\n\n(async () => {\n${rest.join('\n')}\n})().catch(err => { console.error(err); process.exit(1); })`;
      } else {
        wrappedCode = `(async () => {\n${code}\n})().catch(err => { console.error(err); process.exit(1); })`;
      }
    }

    // Write code to temp file (use .mts extension for ESM)
    await writeFile(tempFile, wrappedCode);

    // Log wrapped code for debugging
    if (wrappedCode !== code) {
      fastify.log.debug({ wrappedCode: wrappedCode.substring(0, 200) }, 'Code was wrapped');
    }

    // Execute with tsx using workspace as base directory
    const timeoutMs = Math.min(timeout, EXECUTION_TIMEOUT);
    const { stdout, stderr } = await execAsync(
      `cd /workspace && timeout ${Math.floor(timeoutMs / 1000)} tsx ${tempFile}`,
      {
        maxBuffer: MAX_OUTPUT_SIZE,
        cwd: '/workspace',
        env: {
          ...process.env,
          NODE_PATH: '/workspace/node_modules:/app/node_modules'
        }
      }
    );

    const executionTime = Date.now() - startTime;
    let output = stdout || stderr || '';
    let truncated = false;

    if (output.length > MAX_OUTPUT_SIZE) {
      output = output.substring(0, MAX_OUTPUT_SIZE) + '\n\n[OUTPUT TRUNCATED]';
      truncated = true;
    }

    return {
      output,
      executionTime,
      truncated,
      metrics: {
        outputBytes: output.length,
        tokensEstimate: estimateTokens(output)
      }
    };

  } catch (error: any) {
    const executionTime = Date.now() - startTime;

    // Check if timeout
    if (error.killed || error.signal === 'SIGTERM') {
      fastify.log.warn(`Execution timed out after ${timeout}ms`);
      return {
        output: error.stdout || '',
        error: `Execution timed out after ${timeout}ms`,
        executionTime
      };
    }

    // Runtime error
    fastify.log.error({ error: error.message, stderr: error.stderr }, 'Execution failed');
    return {
      output: error.stdout || '',
      error: error.stderr || error.message,
      executionTime
    };

  } finally {
    // Cleanup temp file
    try {
      await unlink(tempFile);
    } catch (cleanupError) {
      fastify.log.warn({ tempFile, error: cleanupError }, 'Failed to cleanup temp file');
    }
  }
}

/**
 * Execute Python code (basic support)
 */
async function executePython(code: string, timeout: number): Promise<ExecuteResponse> {
  const startTime = Date.now();
  const tempFile = join('/tmp/executions', `exec-${Date.now()}-${Math.random().toString(36).substr(2, 9)}.py`);

  try {
    await writeFile(tempFile, code);

    const timeoutMs = Math.min(timeout, EXECUTION_TIMEOUT);
    const { stdout, stderr } = await execAsync(
      `timeout ${Math.floor(timeoutMs / 1000)} python3 ${tempFile}`,
      {
        maxBuffer: MAX_OUTPUT_SIZE,
        cwd: '/workspace'
      }
    );

    const executionTime = Date.now() - startTime;
    let output = stdout || stderr || '';
    let truncated = false;

    if (output.length > MAX_OUTPUT_SIZE) {
      output = output.substring(0, MAX_OUTPUT_SIZE) + '\n\n[OUTPUT TRUNCATED]';
      truncated = true;
    }

    return {
      output,
      executionTime,
      truncated,
      metrics: {
        outputBytes: output.length,
        tokensEstimate: estimateTokens(output)
      }
    };

  } catch (error: any) {
    const executionTime = Date.now() - startTime;

    if (error.killed || error.signal === 'SIGTERM') {
      return {
        output: '',
        error: `Execution timed out after ${timeout}ms`,
        executionTime
      };
    }

    return {
      output: error.stdout || '',
      error: error.stderr || error.message,
      executionTime
    };

  } finally {
    try {
      await unlink(tempFile);
    } catch {
      // Ignore
    }
  }
}

/**
 * List available tool wrappers
 */
async function listAvailableTools() {
  const serversDir = '/workspace/servers';
  const tools: Record<string, string[]> = {};

  try {
    const servers = await readdir(serversDir, { withFileTypes: true });

    for (const server of servers) {
      if (server.isDirectory()) {
        const serverPath = join(serversDir, server.name);
        const files = await readdir(serverPath);

        tools[server.name] = files
          .filter(file => file.endsWith('.ts') && file !== 'index.ts')
          .map(file => file.replace('.ts', ''));
      }
    }
  } catch (error) {
    // Servers directory may not exist yet
  }

  return tools;
}

/**
 * Extract tool information from source code
 */
async function getToolInfo(server: string, toolName: string, detail: string = 'description'): Promise<ToolInfo | null> {
  const path = join('/workspace/servers', server, `${toolName}.ts`);

  try {
    const source = await readFile(path, 'utf-8');
    const info: ToolInfo = {
      server,
      name: toolName,
      path
    };

    // Extract JSDoc comment (description)
    const docMatch = source.match(/\/\*\*\s*([^*]|\*(?!\/))*\*\//);
    if (docMatch) {
      info.description = docMatch[0]
        .replace(/\/\*\*|\*\//g, '')
        .replace(/^\s*\*\s*/gm, '')
        .trim();
    }

    // Extract function signature
    const sigMatch = source.match(/export async function (\w+)\(([^)]*)\):\s*Promise<([^>]+)>/);
    if (sigMatch) {
      info.signature = `${sigMatch[1]}(${sigMatch[2]}): Promise<${sigMatch[3]}>`;
    }

    // Include full source if requested
    if (detail === 'full') {
      info.source = source;
    }

    return info;
  } catch (error) {
    return null;
  }
}

/**
 * Search tools by keyword
 */
async function searchTools(query: string, server?: string, detail: string = 'description'): Promise<ToolInfo[]> {
  const results: ToolInfo[] = [];
  const serversDir = '/workspace/servers';

  try {
    const servers = server
      ? [server]
      : (await readdir(serversDir, { withFileTypes: true }))
          .filter(entry => entry.isDirectory())
          .map(entry => entry.name);

    for (const srv of servers) {
      const serverPath = join(serversDir, srv);
      const files = await readdir(serverPath);

      for (const file of files) {
        if (!file.endsWith('.ts') || file === 'index.ts' || file === 'discovery.ts') continue;

        const toolName = file.replace('.ts', '');

        // Search in tool name or source code
        if (query) {
          const lowerQuery = query.toLowerCase();
          const source = await readFile(join(serverPath, file), 'utf-8');

          if (!toolName.toLowerCase().includes(lowerQuery) &&
              !source.toLowerCase().includes(lowerQuery)) {
            continue;
          }
        }

        const info = await getToolInfo(srv, toolName, detail);
        if (info) {
          results.push(info);
        }
      }
    }
  } catch (error) {
    fastify.log.error({ error }, 'Failed to search tools');
  }

  return results;
}

/**
 * Estimate token count (rough approximation: 1 token ≈ 4 characters)
 */
function estimateTokens(text: string): number {
  return Math.ceil(text.length / 4);
}

// Routes

/**
 * POST /execute - Execute code
 */
fastify.post<{ Body: ExecuteRequest }>('/execute', async (request, reply) => {
  const { code, timeout = 60000, language = 'typescript' } = request.body;

  // Validation
  if (!code || typeof code !== 'string') {
    return reply.code(400).send({ error: 'Code is required and must be a string' });
  }

  if (code.length > 1024 * 1024) { // 1MB max
    return reply.code(400).send({ error: 'Code size exceeds 1MB limit' });
  }

  if (timeout < 1000 || timeout > EXECUTION_TIMEOUT) {
    return reply.code(400).send({
      error: `Timeout must be between 1000ms and ${EXECUTION_TIMEOUT}ms`
    });
  }

  if (!['typescript', 'python'].includes(language)) {
    return reply.code(400).send({ error: 'Language must be "typescript" or "python"' });
  }

  fastify.log.info({
    language,
    codeLength: code.length,
    timeout,
    preview: code.substring(0, 100)
  }, 'Executing code');

  try {
    const result = language === 'python'
      ? await executePython(code, timeout)
      : await executeTypeScript(code, timeout);

    fastify.log.info({
      executionTime: result.executionTime,
      outputSize: result.output.length,
      hasError: !!result.error,
      truncated: result.truncated
    }, 'Execution completed');

    return result;
  } catch (error: any) {
    fastify.log.error({ error: error.message }, 'Execution failed with exception');
    return reply.code(500).send({
      error: 'Internal execution error',
      message: error.message
    });
  }
});

/**
 * GET /health - Health check
 */
fastify.get('/health', async () => {
  const tools = await listAvailableTools();
  const totalTools = Object.values(tools).reduce((sum, arr) => sum + arr.length, 0);

  return {
    status: 'healthy',
    version: '1.0.0',
    uptime: process.uptime(),
    servers: Object.keys(tools).length,
    totalTools,
    toolsByServer: tools
  };
});

/**
 * GET /tools - List available tools
 */
fastify.get('/tools', async () => {
  const tools = await listAvailableTools();
  return {
    servers: Object.keys(tools).length,
    totalTools: Object.values(tools).reduce((sum, arr) => sum + arr.length, 0),
    tools
  };
});

/**
 * GET /tools/search - Search tools with progressive disclosure
 * Query params:
 *   - query: search keyword (optional, returns all if omitted)
 *   - server: filter by server name (optional)
 *   - detail: 'name' | 'description' | 'full' (default: 'description')
 */
fastify.get<{ Querystring: SearchToolsQuery }>('/tools/search', async (request, reply) => {
  const { query = '', server, detail = 'description' } = request.query;

  fastify.log.info({ query, server, detail }, 'Searching tools');

  const results = await searchTools(query, server, detail);

  // Calculate token savings
  // Need to load full source for accurate comparison
  const fullSources = await Promise.all(
    results.map(r => getToolInfo(r.server, r.name, 'full'))
  );
  const fullTokens = estimateTokens(fullSources.map(r => r?.source || '').join('\n'));
  const descTokens = estimateTokens(results.map(r => r.description || '').join('\n'));
  const nameTokens = estimateTokens(results.map(r => r.name).join('\n'));

  const currentTokens = detail === 'full' ? fullTokens : (detail === 'description' ? descTokens : nameTokens);

  return {
    results,
    count: results.length,
    tokenSavings: {
      name: nameTokens,
      description: descTokens,
      full: fullTokens,
      currentLevel: detail,
      current: currentTokens,
      savingsVsFull: fullTokens > 0 ? Math.round(((fullTokens - currentTokens) / fullTokens) * 100) : 0
    }
  };
});

/**
 * GET /tools/info/:server/:tool - Get detailed tool information
 * Query params:
 *   - detail: 'name' | 'description' | 'full' (default: 'description')
 */
fastify.get<{
  Params: { server: string; tool: string };
  Querystring: { detail?: string };
}>('/tools/info/:server/:tool', async (request, reply) => {
  const { server, tool } = request.params;
  const { detail = 'description' } = request.query;

  const info = await getToolInfo(server, tool, detail);

  if (!info) {
    return reply.code(404).send({ error: 'Tool not found' });
  }

  return {
    tool: info,
    tokenEstimate: detail === 'full' ? estimateTokens(info.source || '') : estimateTokens(info.description || '')
  };
});

// Start server
const start = async () => {
  try {
    await fastify.listen({ port: PORT, host: '0.0.0.0' });
    fastify.log.info(`🚀 MCP Code Executor running on port ${PORT}`);
    fastify.log.info(`⏱️  Max execution timeout: ${EXECUTION_TIMEOUT}ms`);
    fastify.log.info(`📦 Max output size: ${MAX_OUTPUT_SIZE} bytes`);
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();
