#!/usr/bin/env tsx
/**
 * TypeScript Wrapper Generator for MCP Tools
 *
 * Generates TypeScript wrapper functions for all MCP tools
 * organized by server in filesystem structure for progressive disclosure
 */

import { writeFile, mkdir } from 'fs/promises';
import { join } from 'path';
import { listTools } from './client.js';

const MCP_SERVERS = [
  'filesystem',
  'postgres',
  'playwright',
  'memory',
  'minio',
  'n8n',
  'timescaledb',
  'ib',
  'arangodb',
  'openmemory'
];

const OUTPUT_DIR = '/workspace/servers';

interface MCPTool {
  name: string;
  description?: string;
  inputSchema?: {
    type: string;
    properties?: Record<string, any>;
    required?: string[];
  };
}

/**
 * Convert JSON Schema type to TypeScript type
 */
function jsonSchemaToTsType(schema: any): string {
  if (!schema) return 'any';

  switch (schema.type) {
    case 'string':
      return 'string';
    case 'number':
    case 'integer':
      return 'number';
    case 'boolean':
      return 'boolean';
    case 'array':
      return `${jsonSchemaToTsType(schema.items)}[]`;
    case 'object':
      if (schema.properties) {
        const props = Object.entries(schema.properties)
          .map(([key, value]: [string, any]) => {
            const optional = !schema.required?.includes(key) ? '?' : '';
            return `  ${key}${optional}: ${jsonSchemaToTsType(value)};`;
          })
          .join('\n');
        return `{\n${props}\n}`;
      }
      return 'Record<string, any>';
    default:
      return 'any';
  }
}

/**
 * Generate TypeScript wrapper for a single tool
 */
function generateToolWrapper(server: string, tool: MCPTool): string {
  const functionName = tool.name;
  const inputTypeName = `${toPascalCase(functionName)}Input`;
  const responseTypeName = `${toPascalCase(functionName)}Response`;

  // Generate input interface
  const inputType = tool.inputSchema
    ? jsonSchemaToTsType(tool.inputSchema)
    : '{}';

  const description = tool.description
    ? `/** ${tool.description} */`
    : `/** ${functionName} tool from ${server} server */`;

  return `import { callMCPTool } from '/app/client.js';

export type ${inputTypeName} = ${inputType};

export type ${responseTypeName} = any;

${description}
export async function ${functionName}(input: ${inputTypeName}): Promise<${responseTypeName}> {
  return callMCPTool<${responseTypeName}>('${server}', '${tool.name}', input);
}
`;
}

/**
 * Convert snake_case or kebab-case to PascalCase
 */
function toPascalCase(str: string): string {
  return str
    .split(/[_-]/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join('');
}

/**
 * Generate index.ts that exports all tools for a server
 */
function generateServerIndex(tools: MCPTool[]): string {
  const exports = tools
    .map(tool => `export * from './${tool.name}.js';`)
    .join('\n');

  return `/**
 * Auto-generated exports for all tools in this server
 * Generated: ${new Date().toISOString()}
 */

${exports}
`;
}

/**
 * Generate discovery utilities
 */
function generateDiscoveryUtils(): string {
  return `import { readdir } from 'fs/promises';
import { join } from 'path';

const SERVERS_DIR = '/workspace/servers';

/**
 * List all available MCP servers
 */
export async function listServers(): Promise<string[]> {
  const entries = await readdir(SERVERS_DIR, { withFileTypes: true });
  return entries
    .filter(entry => entry.isDirectory())
    .map(entry => entry.name);
}

/**
 * List all tools for a given server
 */
export async function listServerTools(server: string): Promise<string[]> {
  const serverDir = join(SERVERS_DIR, server);
  const files = await readdir(serverDir);
  return files
    .filter(file => file.endsWith('.ts') && file !== 'index.ts')
    .map(file => file.replace('.ts', ''));
}

/**
 * Search for tools by keyword across all servers
 */
export async function searchTools(keyword: string): Promise<Array<{
  server: string;
  tool: string;
  path: string;
}>> {
  const servers = await listServers();
  const results: Array<{ server: string; tool: string; path: string }> = [];

  for (const server of servers) {
    const tools = await listServerTools(server);
    for (const tool of tools) {
      if (tool.toLowerCase().includes(keyword.toLowerCase())) {
        results.push({
          server,
          tool,
          path: join(SERVERS_DIR, server, \`\${tool}.ts\`)
        });
      }
    }
  }

  return results;
}
`;
}

/**
 * Main generation function
 */
async function generateAllWrappers() {
  console.log('🔧 MCP Tool Wrapper Generator');
  console.log('═══════════════════════════════\n');

  let totalTools = 0;

  for (const server of MCP_SERVERS) {
    console.log(`📦 Processing server: ${server}`);

    try {
      // Fetch tools from server
      const tools = await listTools(server);
      console.log(`   Found ${tools.length} tools`);

      if (tools.length === 0) {
        console.log(`   ⚠️  No tools found, skipping\n`);
        continue;
      }

      // Create server directory
      const serverDir = join(OUTPUT_DIR, server);
      await mkdir(serverDir, { recursive: true });

      // Generate wrapper for each tool
      for (const tool of tools) {
        const wrapper = generateToolWrapper(server, tool);
        const filePath = join(serverDir, `${tool.name}.ts`);
        await writeFile(filePath, wrapper);
        console.log(`   ✓ Generated ${tool.name}.ts`);
      }

      // Generate server index
      const indexContent = generateServerIndex(tools);
      await writeFile(join(serverDir, 'index.ts'), indexContent);
      console.log(`   ✓ Generated index.ts`);

      totalTools += tools.length;
      console.log(`   ✅ Completed ${server}\n`);

    } catch (error: any) {
      console.error(`   ❌ Failed to process ${server}: ${error.message}\n`);
    }
  }

  // Generate discovery utilities
  console.log('🔍 Generating discovery utilities...');
  const discoveryPath = join(OUTPUT_DIR, 'discovery.ts');
  await writeFile(discoveryPath, generateDiscoveryUtils());
  console.log('   ✓ Generated discovery.ts\n');

  console.log('═══════════════════════════════');
  console.log(`✅ Generated ${totalTools} tool wrappers`);
  console.log(`📁 Output directory: ${OUTPUT_DIR}`);
}

// Run generator
generateAllWrappers().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
