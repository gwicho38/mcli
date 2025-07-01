// Test helper utilities for Vector Store Manager E2E tests
const net = require('net');
const { exec } = require('child_process');
const { promisify } = require('util');

const execAsync = promisify(exec);

// Port management for tests
async function isPortAvailable(port) {
  return new Promise((resolve) => {
    const tester = net.createServer()
      .once('error', () => resolve(false))
      .once('listening', () => {
        tester.once('close', () => resolve(true))
          .close();
      })
      .listen(port);
  });
}

async function findAvailablePort(startPort = 3001) {
  let port = startPort;
  while (!(await isPortAvailable(port))) {
    port++;
    if (port > startPort + 100) {
      throw new Error('No available ports found');
    }
  }
  return port;
}

async function killProcessOnPort(port) {
  try {
    // Find process using the port
    const { stdout } = await execAsync(`lsof -ti:${port}`);
    if (stdout.trim()) {
      const pids = stdout.trim().split('\n');
      for (const pid of pids) {
        try {
          await execAsync(`kill -9 ${pid}`);
          console.log(`Killed process ${pid} on port ${port}`);
        } catch (error) {
          console.log(`Failed to kill process ${pid}:`, error.message);
        }
      }
    }
  } catch (error) {
    // No process found on port, which is fine
    console.log(`No process found on port ${port}`);
  }
}

async function cleanupTestPorts() {
  // Clean up common test ports
  const testPorts = [3001, 3002, 3003, 3004, 3005];
  for (const port of testPorts) {
    await killProcessOnPort(port);
  }
}

// Test setup and teardown utilities
async function setupTestEnvironment() {
  await cleanupTestPorts();
  const testPort = await findAvailablePort(3001);
  return testPort;
}

async function teardownTestEnvironment() {
  await cleanupTestPorts();
}

// Wait utilities
function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function waitForPort(port, timeout = 10000) {
  const startTime = Date.now();
  while (Date.now() - startTime < timeout) {
    if (!(await isPortAvailable(port))) {
      return true; // Port is in use (server is running)
    }
    await wait(100);
  }
  return false; // Timeout
}

module.exports = {
  isPortAvailable,
  findAvailablePort,
  killProcessOnPort,
  cleanupTestPorts,
  setupTestEnvironment,
  teardownTestEnvironment,
  wait,
  waitForPort
}; 