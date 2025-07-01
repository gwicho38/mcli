# Vector Store Manager - Puppeteer Test Suite

This directory contains comprehensive automated tests for the Vector Store Manager application using Puppeteer.

## Overview

The test suite provides automated testing for all major features of the Vector Store Manager, including:

- **App Loading**: Verifies the application starts correctly
- **File Upload**: Tests drag-and-drop file upload functionality
- **Search Functionality**: Tests semantic search capabilities
- **Document Management**: Tests document listing and operations
- **Vector Operations**: Tests embedding generation and similarity search
- **API Endpoints**: Tests backend API functionality
- **WebSocket Communication**: Tests real-time communication
- **Error Handling**: Tests error scenarios and edge cases
- **Performance Metrics**: Measures app performance and responsiveness

## Prerequisites

- Node.js 16 or higher
- npm or yarn
- The Vector Store Manager app must be installed and functional

## Installation

1. Navigate to the test directory:
   ```bash
   cd test
   ```

2. Install test dependencies:
   ```bash
   npm install
   ```

## Usage

### Using the Test Runner Script

The easiest way to run tests is using the provided shell script:

```bash
# Run all tests
./run-tests.sh

# Run basic tests only
./run-tests.sh basic

# Run advanced tests only
./run-tests.sh advanced

# Run API tests only
./run-tests.sh api

# Run UI tests only
./run-tests.sh ui

# Generate test report
./run-tests.sh --report

# Check environment only
./run-tests.sh --check

# Verbose output
./run-tests.sh --verbose
```

### Using the mcli Command

You can also run tests through the mcli webapp command:

```bash
# Run all tests for an app
mcli workflow webapp test My_Vector_Store

# Run specific test types
mcli workflow webapp test My_Vector_Store --test-type basic
mcli workflow webapp test My_Vector_Store --test-type advanced
mcli workflow webapp test My_Vector_Store --test-type api
mcli workflow webapp test My_Vector_Store --test-type ui

# Generate test report
mcli workflow webapp test My_Vector_Store --report

# Check environment only
mcli workflow webapp test My_Vector_Store --check

# Verbose output
mcli workflow webapp test My_Vector_Store --verbose
```

### Direct Node.js Execution

You can also run tests directly with Node.js:

```bash
# Run basic tests
node puppeteer-test.js

# Run advanced tests
node advanced-test-suite.js
```

## Test Types

### Basic Tests (`puppeteer-test.js`)

Basic functionality tests that verify core app features:

- App loading and initialization
- File upload with drag-and-drop
- Search functionality
- Document management
- Vector visualization
- Settings and configuration
- Error handling
- Performance metrics

### Advanced Tests (`advanced-test-suite.js`)

Comprehensive tests that include:

- API endpoint testing
- WebSocket communication
- Multi-format file upload
- Advanced search with different queries
- Vector operations (generation, similarity, export)
- Document operations (preview, metadata)
- Error scenarios (invalid files, network issues, large files)
- Performance metrics and benchmarking

### API Tests

Tests the backend API endpoints:

- Health check endpoint
- Document listing endpoint
- Upload endpoint validation
- Error handling for invalid requests

### UI Tests

Tests the user interface interactions:

- App loading and rendering
- UI element presence and functionality
- User interaction flows
- Responsive design elements

## Test Configuration

### Environment Variables

The tests use the following environment variables:

- `PUPPETEER_HEADLESS`: Set to `false` to run tests with visible browser (default: `false`)
- `PUPPETEER_TIMEOUT`: Timeout for test operations in milliseconds (default: `30000`)
- `TEST_APP_PORT`: Port for the app server (default: `3001`)

### Test Data

The tests create temporary test files:

- `test-document.txt`: Basic text document for testing
- `large-test-file.txt`: Large file for performance testing
- Various format files (JSON, Markdown) for multi-format testing

These files are automatically cleaned up after tests complete.

## Test Reports

When using the `--report` flag, a JSON test report is generated with:

- Timestamp of test execution
- App version information
- Node.js version
- Test results for each test type
- Success/failure status
- Error messages (if any)

Example report structure:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "app_version": "1.0.0",
  "node_version": "v18.17.0",
  "tests": {
    "basic": {
      "status": "PASS",
      "message": "Basic tests completed successfully"
    },
    "advanced": {
      "status": "PASS",
      "message": "Advanced tests completed successfully"
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **App not starting**: Ensure the app is properly installed and all dependencies are available
2. **Port conflicts**: The test runner will detect if port 3001 is in use and offer to stop conflicting processes
3. **Node.js version**: Ensure you're using Node.js 16 or higher
4. **Puppeteer installation**: If Puppeteer fails to install, try running `npm install puppeteer` manually

### Debug Mode

For debugging test issues:

```bash
# Run with verbose output
./run-tests.sh --verbose

# Run specific test with debugging
node --inspect puppeteer-test.js

# Check environment
./run-tests.sh --check
```

### Manual Testing

If automated tests fail, you can manually verify:

1. Start the app: `npm start`
2. Open browser to `http://localhost:3001`
3. Test file upload functionality
4. Test search functionality
5. Check console for errors

## Continuous Integration

The test suite is designed to work in CI/CD environments:

```yaml
# Example GitHub Actions workflow
- name: Run Vector Store Tests
  run: |
    cd test
    npm install
    ./run-tests.sh --report
```

## Contributing

When adding new features to the Vector Store Manager, please:

1. Add corresponding tests to the appropriate test file
2. Update this README with new test descriptions
3. Ensure all tests pass before submitting changes
4. Add new test types to the test runner script if needed

## Test Architecture

The test suite uses a modular architecture:

- **Base Tester Class**: Common functionality for app startup and cleanup
- **Basic Tester**: Simple functionality tests
- **Advanced Tester**: Comprehensive tests with API and WebSocket testing
- **Test Runner**: Shell script for easy execution and reporting
- **Configuration**: Environment-specific settings and timeouts

This architecture allows for easy extension and maintenance of the test suite. 