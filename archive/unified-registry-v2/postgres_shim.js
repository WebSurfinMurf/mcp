#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Path to the Python MCP service wrapper
const mcpScriptPath = path.join(__dirname, 'run_postgres_mcp.sh');

// Log file for debugging
const logFile = '/tmp/postgres_shim.log';
fs.appendFileSync(logFile, `\n--- Shim Started at ${new Date().toISOString()} ---\n`);

// Spawn the Python MCP service
const child = spawn(mcpScriptPath, [], {
    stdio: ['pipe', 'pipe', 'pipe'], // stdin, stdout, stderr
    env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
        DATABASE_URL: process.env.DATABASE_URL || 'postgresql://admin:Pass123qp@localhost:5432/postgres'
    }
});

// Set up stdin forwarding
process.stdin.setEncoding('utf8');
process.stdin.on('data', (data) => {
    fs.appendFileSync(logFile, `STDIN→Child: ${data}`);
    child.stdin.write(data);
});

// Set up stdout forwarding  
child.stdout.setEncoding('utf8');
child.stdout.on('data', (data) => {
    fs.appendFileSync(logFile, `Child→STDOUT: ${data}`);
    process.stdout.write(data);
});

// Capture stderr for debugging
child.stderr.setEncoding('utf8');
child.stderr.on('data', (data) => {
    fs.appendFileSync(logFile, `STDERR: ${data}`);
});

// Handle child process exit
child.on('exit', (code, signal) => {
    fs.appendFileSync(logFile, `Child exited with code ${code}, signal ${signal}\n`);
    // Add small delay before exiting to ensure output is flushed
    setTimeout(() => {
        process.exit(code || 0);
    }, 100);
});

// Handle errors
child.on('error', (err) => {
    fs.appendFileSync(logFile, `Child error: ${err}\n`);
    console.error('Failed to start subprocess:', err);
    process.exit(1);
});

// Handle parent process signals
process.on('SIGINT', () => {
    child.kill('SIGINT');
});

process.on('SIGTERM', () => {
    child.kill('SIGTERM');
});