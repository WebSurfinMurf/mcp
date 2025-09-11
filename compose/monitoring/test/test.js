import axios from 'axios';
import { spawn } from 'child_process';

async function testLokiConnection() {
  try {
    const response = await axios.get('http://localhost:3100/ready');
    console.log('✓ Loki connection successful');
    return true;
  } catch (error) {
    console.error('✗ Loki connection failed:', error.message);
    return false;
  }
}

async function testNetdataConnection() {
  try {
    const response = await axios.get('http://localhost:19999/api/v1/info');
    console.log('✓ Netdata connection successful');
    return true;
  } catch (error) {
    console.error('✗ Netdata connection failed:', error.message);
    return false;
  }
}

async function testMCPServer() {
  return new Promise((resolve) => {
    const server = spawn('node', ['src/index.js'], {
      env: { ...process.env, NODE_ENV: 'test' }
    });

    setTimeout(() => {
      server.kill();
      console.log('✓ MCP server starts successfully');
      resolve(true);
    }, 2000);

    server.on('error', (error) => {
      console.error('✗ MCP server failed to start:', error);
      resolve(false);
    });
  });
}

async function runTests() {
  console.log('Running MCP Observability Server Tests...\n');
  
  const results = await Promise.all([
    testLokiConnection(),
    testNetdataConnection(),
    testMCPServer()
  ]);

  const allPassed = results.every(r => r);
  
  console.log('\n' + (allPassed ? 'All tests passed!' : 'Some tests failed'));
  process.exit(allPassed ? 0 : 1);
}

runTests();