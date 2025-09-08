#!/usr/bin/env node

/**
 * Node.js shim for PostgreSQL MCP service
 * Bridges Claude Code's MCP protocol with Python service
 * 
 * This shim is necessary because direct Python-to-Claude MCP communication
 * has persistent issues, while Node.js works reliably with the MCP bridge.
 */

const { spawn } = require('child_process');
const readline = require('readline');
const fs = require('fs');
const path = require('path');

// Configuration
const PROJECT_DIR = path.join(__dirname, '..');
const PYTHON_SERVICE = path.join(PROJECT_DIR, 'services', 'mcp_postgres.py');
const PYTHON_BIN = path.join(PROJECT_DIR, 'venv', 'bin', 'python3');
const LOG_FILE = '/tmp/postgres_mcp.log';
const LOG_ENABLED = true;

// Create log stream
const logStream = LOG_ENABLED ? fs.createWriteStream(LOG_FILE, { flags: 'a' }) : null;

function log(message) {
    if (logStream) {
        const timestamp = new Date().toISOString();
        logStream.write(`${timestamp} - ${message}\n`);
    }
}

log('=== PostgreSQL MCP Shim Started ===');

// Environment setup
const env = {
    ...process.env,
    DATABASE_URL: process.env.DATABASE_URL || 'postgresql://admin:Pass123qp@localhost:5432/postgres',
    PYTHONUNBUFFERED: '1'
};

// Spawn Python service using venv
const pythonProcess = spawn(PYTHON_BIN, [PYTHON_SERVICE, '--mode', 'stdio'], {
    env: env,
    stdio: ['pipe', 'pipe', 'pipe']
});

// Create readline interface for stdin
const rl = readline.createInterface({
    input: process.stdin,
    output: null,
    terminal: false
});

// Handle input from Claude
rl.on('line', (line) => {
    log(`REQUEST: ${line}`);
    pythonProcess.stdin.write(line + '\n');
});

// Handle output from Python service
pythonProcess.stdout.on('data', (data) => {
    const output = data.toString();
    log(`RESPONSE: ${output.trim()}`);
    process.stdout.write(data);
});

// Handle stderr from Python service (logging)
pythonProcess.stderr.on('data', (data) => {
    log(`STDERR: ${data.toString().trim()}`);
});

// Handle Python process exit
pythonProcess.on('exit', (code, signal) => {
    log(`Python process exited with code ${code} and signal ${signal}`);
    process.exit(code || 0);
});

// Handle Python process errors
pythonProcess.on('error', (err) => {
    log(`ERROR: Failed to start Python process: ${err.message}`);
    console.error(JSON.stringify({
        jsonrpc: "2.0",
        error: {
            code: -32603,
            message: `Failed to start Python service: ${err.message}`
        },
        id: null
    }));
    process.exit(1);
});

// Handle process termination
process.on('SIGINT', () => {
    log('Received SIGINT, shutting down...');
    pythonProcess.kill('SIGINT');
    process.exit(0);
});

process.on('SIGTERM', () => {
    log('Received SIGTERM, shutting down...');
    pythonProcess.kill('SIGTERM');
    process.exit(0);
});

// Keep process alive
process.stdin.resume();