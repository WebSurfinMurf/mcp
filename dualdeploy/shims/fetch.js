#!/usr/bin/env node

/**
 * Node.js shim for Fetch MCP service
 * Bridges Claude Code's MCP protocol with Python service
 */

const { spawn } = require('child_process');
const readline = require('readline');
const fs = require('fs');
const path = require('path');

// Configuration
const PROJECT_DIR = path.join(__dirname, '..');
const PYTHON_SERVICE = path.join(PROJECT_DIR, 'services', 'mcp_fetch.py');
const PYTHON_BIN = path.join(PROJECT_DIR, 'venv', 'bin', 'python3');
const LOG_FILE = '/tmp/fetch_mcp.log';

// Check if virtual environment exists, fallback to system python
const pythonExecutable = fs.existsSync(PYTHON_BIN) ? PYTHON_BIN : 'python3';

// Configure logging
const logStream = fs.createWriteStream(LOG_FILE, { flags: 'a' });
const log = (message) => {
    const timestamp = new Date().toISOString();
    logStream.write(`[${timestamp}] ${message}\n`);
};

log('=== Fetch MCP Shim Started ===');
log(`Working directory: ${PROJECT_DIR}`);
log(`Python service: ${PYTHON_SERVICE}`);
log(`Python executable: ${pythonExecutable}`);

// Start the Python service
const pythonProcess = spawn(pythonExecutable, [PYTHON_SERVICE, '--mode', 'stdio'], {
    cwd: PROJECT_DIR,
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
    stdio: ['pipe', 'pipe', 'pipe']
});

// Handle Python process errors
pythonProcess.on('error', (err) => {
    log(`Failed to start Python service: ${err.message}`);
    console.error(JSON.stringify({
        jsonrpc: '2.0',
        error: {
            code: -32603,
            message: `Failed to start fetch service: ${err.message}`
        },
        id: null
    }));
    process.exit(1);
});

pythonProcess.on('exit', (code, signal) => {
    log(`Python service exited with code ${code}, signal ${signal}`);
    process.exit(code || 0);
});

// Capture Python stderr for debugging
pythonProcess.stderr.on('data', (data) => {
    log(`Python stderr: ${data.toString().trim()}`);
});

// Setup stdio communication
const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false
});

// Forward stdin to Python service
rl.on('line', (line) => {
    log(`Request: ${line}`);
    pythonProcess.stdin.write(line + '\n');
});

// Forward Python output to stdout
pythonProcess.stdout.on('data', (data) => {
    const lines = data.toString().split('\n').filter(line => line.trim());
    lines.forEach(line => {
        log(`Response: ${line}`);
        console.log(line);
    });
});

// Handle process termination
process.on('SIGINT', () => {
    log('Received SIGINT, shutting down...');
    pythonProcess.kill('SIGTERM');
    process.exit(0);
});

process.on('SIGTERM', () => {
    log('Received SIGTERM, shutting down...');
    pythonProcess.kill('SIGTERM');
    process.exit(0);
});

log('Fetch MCP shim ready, forwarding stdio...');