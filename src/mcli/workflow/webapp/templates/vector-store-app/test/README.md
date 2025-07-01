# Vector Store Manager E2E Tests

This directory contains comprehensive end-to-end tests for the Vector Store Manager Electron app.

## Test Files

- `simple-e2e.test.js` - Basic functionality tests (UI elements, modals, etc.)
- `e2e-vectorstore.test.js` - Full E2E tests (file upload, search, CRUD operations)
- `test-helper.js` - Port management and test utilities
- `playwright.config.js` - Playwright configuration

## Port Management Solution

The tests now include a robust port management system to handle the common issue of port conflicts:

### Features:
- **Automatic Port Detection**: Finds available ports starting from 3001
- **Process Cleanup**: Kills processes using test ports before running tests
- **Graceful Shutdown**: Properly closes server connections and cleans up ports
- **Test Isolation**: Each test runs on a unique port to prevent conflicts

### How it works:
1. `setupTestEnvironment()` - Cleans up existing processes and finds an available port
2. `teardownTestEnvironment()` - Cleans up after tests complete
3. `waitForPort()` - Waits for server to be ready on the specified port

## Running Tests

### Prerequisites
```bash
npm install
npx playwright install
```

### Run Simple Tests
```bash
npx playwright test simple-e2e.test.js --timeout=60000
```

### Run Full E2E Tests
```bash
npx playwright test e2e-vectorstore.test.js --timeout=180000
```

### Run All Tests
```bash
npx playwright test --timeout=180000
```

### View Test Reports
```bash
npx playwright show-report
```

## Test Coverage

### Simple E2E Tests
- ✅ App startup and UI element visibility
- ✅ Upload modal functionality
- ✅ Welcome message display
- ✅ Search options availability
- ✅ Status bar information

### Full E2E Tests
- ✅ File upload for all supported formats
- ✅ Document CRUD operations
- ✅ Semantic and exact match search
- ✅ Memory usage monitoring
- ✅ App restart and cleanup

## Troubleshooting

### Port Conflicts
If you encounter port conflicts, the test helper will automatically:
1. Detect processes using test ports (3001-3005)
2. Kill those processes
3. Find an available port
4. Clean up after tests complete

### Manual Cleanup
If needed, you can manually clean up ports:
```bash
# Kill processes on specific ports
lsof -ti:3001 | xargs kill -9
lsof -ti:3002 | xargs kill -9

# Or use the test helper
node -e "require('./test-helper').cleanupTestPorts().then(() => console.log('Cleanup complete'));"
```

## Environment Variables

- `PORT` - Starting port for server (default: 3001)
- `NODE_ENV` - Set to 'test' for test environment

## Dependencies

- `@playwright/test` - Test framework
- `playwright` - Browser automation
- `net` - Port management utilities
- `child_process` - Process management 