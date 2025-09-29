import express from 'express';
import cors from 'cors';
import { spawn } from 'child_process';
import readline from 'readline';
import { SseServer } from '@modelcontextprotocol/server-sse';

const BRIDGE_PATH = process.env.MCP_STDIO_BRIDGE || '/workspace/mcp/filesystem/mcp-bridge.py';
const PORT = Number(process.env.MCP_SSE_PORT || 9073);

function log(level, message, extra = {}) {
  const entry = { level, message, timestamp: new Date().toISOString(), ...extra };
  console.log(JSON.stringify(entry));
}

function createBridgeProcess() {
  const child = spawn('python3', [BRIDGE_PATH], {
    stdio: ['pipe', 'pipe', 'inherit'],
  });
  child.on('error', (error) => {
    log('error', 'Failed to start python bridge', { error: error.message });
  });
  return child;
}

async function main() {
  let bridge = createBridgeProcess();
  let rl = readline.createInterface({ input: bridge.stdout });

  const sseServer = new SseServer({
    async onMessage(message) {
      try {
        bridge.stdin.write(JSON.stringify(message) + '\n');
      } catch (error) {
        log('error', 'Failed to write to bridge stdin', { error: error.message });
      }
    },
  });

  const rewireBridge = () => {
    bridge = createBridgeProcess();
    rl = readline.createInterface({ input: bridge.stdout });
    rl.on('line', handleBridgeLine);
  };

  const handleBridgeLine = (line) => {
    try {
      const data = JSON.parse(line);
      sseServer.broadcast('mcp-json-rpc-2.0', data);
    } catch (error) {
      log('error', 'Failed to parse bridge output', { error: error.message, line });
    }
  };

  rl.on('line', handleBridgeLine);

  bridge.on('exit', (code, signal) => {
    log('warn', 'Bridge exited, restarting', { code, signal });
    rewireBridge();
  });

  const app = express();
  app.use(cors());
  app.use(express.json());

  app.get('/health', (_req, res) => {
    const healthy = bridge.exitCode === null;
    res.json({
      status: healthy ? 'healthy' : 'degraded',
      bridgePath: BRIDGE_PATH,
      port: PORT,
    });
  });

  app.get('/sse', (req, res) => sseServer.handleRequest(req, res));
  app.post('/messages', (req, res) => sseServer.handleMessage(req, res));

  app.listen(PORT, '0.0.0.0', () => {
    log('info', 'Filesystem SSE wrapper listening', { port: PORT, bridgePath: BRIDGE_PATH });
  });
}

main().catch((error) => {
  log('error', 'Failed to start filesystem SSE wrapper', { error: error.message });
  process.exit(1);
});
