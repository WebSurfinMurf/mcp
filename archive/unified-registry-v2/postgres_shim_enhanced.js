#!/usr/bin/env node

const { spawn } = require('child_process');
const readline = require('readline');
const path = require('path');
const fs = require('fs');

const mcpScriptPath = path.join(__dirname, 'run_postgres_mcp.sh');
const logFile = '/tmp/postgres_shim_enhanced.log';

fs.appendFileSync(logFile, `\n--- Enhanced Shim Started at ${new Date().toISOString()} ---\n`);

const child = spawn(mcpScriptPath, [], {
    stdio: ['pipe', 'pipe', 'pipe'],
    env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
        DATABASE_URL: process.env.DATABASE_URL || 'postgresql://admin:Pass123qp@localhost:5432/postgres'
    }
});

// Use readline for better line-based processing
const rl = readline.createInterface({
    input: process.stdin,
    output: null,
    terminal: false
});

rl.on('line', (line) => {
    fs.appendFileSync(logFile, `REQUEST: ${line}\n`);
    child.stdin.write(line + '\n');
});

// Buffer and process child output line by line
const childRl = readline.createInterface({
    input: child.stdout,
    output: null,
    terminal: false
});

childRl.on('line', (line) => {
    fs.appendFileSync(logFile, `RESPONSE: ${line}\n`);
    console.log(line);
    
    // CRITICAL: Add small delay to ensure output is flushed
    // This helps with any potential race conditions
    setTimeout(() => {}, 10);
});

// Log stderr but don't forward it
child.stderr.on('data', (data) => {
    fs.appendFileSync(logFile, `STDERR: ${data}`);
});

// Keep process alive even after child exits briefly
child.on('exit', (code, signal) => {
    fs.appendFileSync(logFile, `Child exited: code=${code}, signal=${signal}\n`);
    // Wait 100ms before exiting to ensure all output is flushed
    setTimeout(() => {
        process.exit(code || 0);
    }, 100);
});

child.on('error', (err) => {
    fs.appendFileSync(logFile, `ERROR: ${err}\n`);
    console.error('Subprocess error:', err);
    process.exit(1);
});

// Handle signals gracefully
process.on('SIGINT', () => {
    fs.appendFileSync(logFile, 'Parent received SIGINT\n');
    child.kill('SIGINT');
});

process.on('SIGTERM', () => {
    fs.appendFileSync(logFile, 'Parent received SIGTERM\n');
    child.kill('SIGTERM');
});