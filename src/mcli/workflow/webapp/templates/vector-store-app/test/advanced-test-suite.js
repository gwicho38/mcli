const puppeteer = require('puppeteer');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const http = require('http');

class AdvancedVectorStoreTester {
  constructor() {
    this.appProcess = null;
    this.browser = null;
    this.page = null;
    this.testResults = [];
    this.appPath = path.join(__dirname, '..');
    this.apiBaseUrl = 'http://localhost:3001';
    this.testData = {
      documents: [],
      embeddings: [],
      searchQueries: []
    };
  }

  async startApp() {
    console.log('🚀 Starting Vector Store Manager app...');
    
    return new Promise((resolve, reject) => {
      this.appProcess = spawn('npm', ['start'], {
        cwd: this.appPath,
        stdio: 'pipe'
      });

      let appReady = false;
      const timeout = setTimeout(() => {
        if (!appReady) {
          reject(new Error('App failed to start within 30 seconds'));
        }
      }, 30000);

      this.appProcess.stdout.on('data', (data) => {
        const output = data.toString();
        console.log(`[APP] ${output.trim()}`);
        
        if (output.includes('Vector Store API server running on port 3001')) {
          appReady = true;
          clearTimeout(timeout);
          setTimeout(resolve, 3000); // Give app more time to initialize
        }
      });

      this.appProcess.stderr.on('data', (data) => {
        const error = data.toString();
        if (!error.includes('UnhandledPromiseRejectionWarning')) {
          console.error(`[APP ERROR] ${error.trim()}`);
        }
      });

      this.appProcess.on('error', (error) => {
        console.error('Failed to start app:', error);
        reject(error);
      });
    });
  }

  async connectToApp() {
    console.log('🔗 Connecting to Electron app...');
    
    this.browser = await puppeteer.launch({
      headless: false,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--no-first-run',
        '--no-zygote',
        '--disable-gpu',
        '--window-size=1400,900'
      ]
    });

    const pages = await this.browser.pages();
    this.page = pages[0];
    
    // Wait for the app to load
    await this.page.waitForSelector('.app-container', { timeout: 15000 });
    console.log('✅ Connected to Electron app');
  }

  async testAPIEndpoints() {
    console.log('🔌 Testing API endpoints...');
    
    const endpoints = [
      { path: '/api/documents', method: 'GET', expectedStatus: 200 },
      { path: '/api/vector-visualization', method: 'GET', expectedStatus: 200 },
      { path: '/api/document/1', method: 'GET', expectedStatus: 200 },
    ];

    for (const endpoint of endpoints) {
      try {
        const response = await this.makeAPIRequest(endpoint.path, endpoint.method);
        if (response.statusCode !== endpoint.expectedStatus) {
          throw new Error(`Expected status ${endpoint.expectedStatus}, got ${response.statusCode}`);
        }
        console.log(`✅ ${endpoint.method} ${endpoint.path} - ${response.statusCode}`);
      } catch (error) {
        throw new Error(`API test failed for ${endpoint.method} ${endpoint.path}: ${error.message}`);
      }
    }
  }

  async makeAPIRequest(path, method = 'GET', data = null) {
    return new Promise((resolve, reject) => {
      const options = {
        hostname: 'localhost',
        port: 3001,
        path: path,
        method: method,
        headers: {
          'Content-Type': 'application/json'
        }
      };

      const req = http.request(options, (res) => {
        let body = '';
        res.on('data', (chunk) => {
          body += chunk;
        });
        res.on('end', () => {
          resolve({
            statusCode: res.statusCode,
            headers: res.headers,
            body: body
          });
        });
      });

      req.on('error', (error) => {
        reject(error);
      });

      if (data) {
        req.write(JSON.stringify(data));
      }
      req.end();
    });
  }

  async testWebSocketCommunication() {
    console.log('📡 Testing WebSocket communication...');
    
    // Test WebSocket connection
    const wsConnected = await this.page.evaluate(() => {
      return new Promise((resolve) => {
        const ws = new WebSocket('ws://localhost:3001');
        ws.onopen = () => {
          ws.send(JSON.stringify({ type: 'ping' }));
          resolve(true);
        };
        ws.onerror = () => resolve(false);
        setTimeout(() => resolve(false), 5000);
      });
    });

    if (!wsConnected) {
      throw new Error('WebSocket connection failed');
    }
  }

  async testFileUploadWithMultipleFormats() {
    console.log('📁 Testing file upload with multiple formats...');
    
    const testFiles = [
      { name: 'test.txt', content: 'This is a plain text document for testing.', type: 'text/plain' },
      { name: 'test.md', content: '# Test Markdown\n\nThis is a **markdown** document for testing.', type: 'text/markdown' },
      { name: 'test.json', content: JSON.stringify({ title: 'Test JSON', content: 'This is a JSON document' }), type: 'application/json' }
    ];

    for (const file of testFiles) {
      await this.uploadTestFile(file);
      await this.page.waitForTimeout(1000);
    }

    // Verify files were uploaded
    const uploadedFiles = await this.page.$('#uploadedFiles');
    if (!uploadedFiles) {
      throw new Error('Upload area not found');
    }
  }

  async uploadTestFile(fileInfo) {
    const uploadArea = await this.page.$('#uploadArea');
    
    await this.page.evaluateHandle((uploadArea, fileInfo) => {
      const dataTransfer = new DataTransfer();
      const file = new File([fileInfo.content], fileInfo.name, { type: fileInfo.type });
      dataTransfer.items.add(file);
      
      const dropEvent = new Event('drop', { bubbles: true });
      dropEvent.dataTransfer = dataTransfer;
      uploadArea.dispatchEvent(dropEvent);
    }, uploadArea, fileInfo);
  }

  async testSearchWithDifferentQueries() {
    console.log('🔍 Testing search with different queries...');
    
    const searchQueries = [
      'test document',
      'markdown',
      'json',
      'vector',
      'embedding'
    ];

    for (const query of searchQueries) {
      const searchInput = await this.page.$('#searchInput');
      await searchInput.click();
      await searchInput.type(query);
      await this.page.keyboard.press('Enter');
      
      // Wait for search results
      await this.page.waitForTimeout(2000);
      
      // Check if search input has the value
      const inputValue = await searchInput.evaluate(el => el.value);
      console.log(`Query "${query}": input value = "${inputValue}"`);
    }
  }

  async testVectorOperations() {
    console.log('🧮 Testing vector operations...');
    
    // Test visualization button
    const vizButton = await this.page.$('#visualizeBtn');
    if (vizButton) {
      await vizButton.click();
      await this.page.waitForSelector('#visualizationPanel', { timeout: 5000 });
      
      // Test visualization controls
      const clusteringSelect = await this.page.$('#clusteringMethod');
      if (clusteringSelect) {
        await clusteringSelect.select('kmeans');
      }
      
      const dimensionSelect = await this.page.$('#dimensionReduction');
      if (dimensionSelect) {
        await dimensionSelect.select('pca');
      }
    }
  }

  async testDocumentOperations() {
    console.log('📄 Testing document operations...');
    
    // Test document list
    const documentsList = await this.page.$('#documentsList');
    if (documentsList) {
      const listContent = await documentsList.evaluate(el => el.textContent);
      console.log('Document list content:', listContent);
      
      // Test refresh button
      const refreshBtn = await this.page.$('#refreshDocs');
      if (refreshBtn) {
        await refreshBtn.click();
        await this.page.waitForTimeout(1000);
      }
    }
    
    // Test chat container
    const chatContainer = await this.page.$('#chatContainer');
    if (chatContainer) {
      const chatContent = await chatContainer.evaluate(el => el.textContent);
      if (!chatContent.includes('Welcome to Vector Store Manager')) {
        throw new Error('Welcome message not found in chat container');
      }
    }
  }

  async testErrorScenarios() {
    console.log('⚠️ Testing error scenarios...');
    
    // Test invalid file upload
    await this.testInvalidFileUpload();
    
    // Test network disconnection
    await this.testNetworkDisconnection();
    
    // Test large file handling
    await this.testLargeFileHandling();
  }

  async testInvalidFileUpload() {
    const uploadArea = await this.page.$('#uploadArea');
    
    await this.page.evaluateHandle((uploadArea) => {
      const dataTransfer = new DataTransfer();
      const file = new File(['Invalid content'], 'invalid.exe', { type: 'application/x-executable' });
      dataTransfer.items.add(file);
      
      const dropEvent = new Event('drop', { bubbles: true });
      dropEvent.dataTransfer = dataTransfer;
      uploadArea.dispatchEvent(dropEvent);
    }, uploadArea);
    
    // Wait a bit to see if any error handling occurs
    await this.page.waitForTimeout(2000);
    
    // Check if the upload area is still functional
    const uploadAreaExists = await this.page.$('#uploadArea');
    if (!uploadAreaExists) {
      throw new Error('Upload area should remain functional after invalid file');
    }
  }

  async testNetworkDisconnection() {
    // Simulate network issues by temporarily blocking API calls
    await this.page.evaluate(() => {
      // Override fetch to simulate network error
      const originalFetch = window.fetch;
      window.fetch = () => Promise.reject(new Error('Network error'));
      
      setTimeout(() => {
        window.fetch = originalFetch;
      }, 2000);
    });
    
    // Try to perform an operation that requires network
    const searchInput = await this.page.$('#searchInput');
    await searchInput.type('test');
    await this.page.waitForTimeout(1000);
  }

  async testLargeFileHandling() {
    // Create a large test file
    const largeContent = 'A'.repeat(1024 * 1024); // 1MB file
    const testFilePath = path.join(__dirname, 'large-test-file.txt');
    fs.writeFileSync(testFilePath, largeContent);
    
    const uploadArea = await this.page.$('#uploadArea');
    
    await this.page.evaluateHandle((uploadArea) => {
      const dataTransfer = new DataTransfer();
      const file = new File(['A'.repeat(1024 * 1024)], 'large-test-file.txt', { type: 'text/plain' });
      dataTransfer.items.add(file);
      
      const dropEvent = new Event('drop', { bubbles: true });
      dropEvent.dataTransfer = dataTransfer;
      uploadArea.dispatchEvent(dropEvent);
    }, uploadArea);
    
    // Wait for processing or error
    await this.page.waitForTimeout(5000);
    
    // Clean up
    if (fs.existsSync(testFilePath)) {
      fs.unlinkSync(testFilePath);
    }
  }

  async testPerformanceMetrics() {
    console.log('⚡ Testing performance metrics...');
    
    // Measure page load time
    const loadTime = await this.page.evaluate(() => {
      return performance.timing.loadEventEnd - performance.timing.navigationStart;
    });
    
    console.log(`Page load time: ${loadTime}ms`);
    
    // Measure memory usage
    const memoryInfo = await this.page.evaluate(() => {
      return performance.memory;
    });
    
    console.log(`Memory usage: ${Math.round(memoryInfo.usedJSHeapSize / 1024 / 1024)}MB`);
    
    // Test responsiveness
    const startTime = Date.now();
    
    // Test button interactions
    const uploadBtn = await this.page.$('#uploadBtn');
    if (uploadBtn) {
      await uploadBtn.click();
      await this.page.waitForTimeout(500);
    }
    
    const visualizeBtn = await this.page.$('#visualizeBtn');
    if (visualizeBtn) {
      await visualizeBtn.click();
      await this.page.waitForTimeout(500);
    }
    
    const navigationTime = Date.now() - startTime;
    
    console.log(`Navigation responsiveness: ${navigationTime}ms`);
    
    if (navigationTime > 5000) {
      throw new Error(`Navigation too slow: ${navigationTime}ms`);
    }
  }

  async runTest(testName, testFunction) {
    console.log(`\n🧪 Running test: ${testName}`);
    try {
      const startTime = Date.now();
      await testFunction();
      const duration = Date.now() - startTime;
      this.testResults.push({
        name: testName,
        status: 'PASS',
        duration: duration
      });
      console.log(`✅ ${testName} - PASSED (${duration}ms)`);
    } catch (error) {
      this.testResults.push({
        name: testName,
        status: 'FAIL',
        error: error.message,
        duration: Date.now() - Date.now()
      });
      console.log(`❌ ${testName} - FAILED: ${error.message}`);
    }
  }

  async runAllTests() {
    console.log('🧪 Starting advanced Vector Store Manager test suite...\n');
    
    await this.runTest('API Endpoints', () => this.testAPIEndpoints());
    await this.runTest('WebSocket Communication', () => this.testWebSocketCommunication());
    await this.runTest('Multi-Format File Upload', () => this.testFileUploadWithMultipleFormats());
    await this.runTest('Advanced Search', () => this.testSearchWithDifferentQueries());
    await this.runTest('Vector Operations', () => this.testVectorOperations());
    await this.runTest('Document Operations', () => this.testDocumentOperations());
    await this.runTest('Error Scenarios', () => this.testErrorScenarios());
    await this.runTest('Performance Metrics', () => this.testPerformanceMetrics());
    
    this.printResults();
  }

  printResults() {
    console.log('\n📊 Advanced Test Results Summary:');
    console.log('='.repeat(60));
    
    const passed = this.testResults.filter(r => r.status === 'PASS').length;
    const failed = this.testResults.filter(r => r.status === 'FAIL').length;
    const total = this.testResults.length;
    
    this.testResults.forEach(result => {
      const status = result.status === 'PASS' ? '✅' : '❌';
      console.log(`${status} ${result.name} (${result.duration}ms)`);
      if (result.error) {
        console.log(`   Error: ${result.error}`);
      }
    });
    
    console.log('\n' + '='.repeat(60));
    console.log(`Total: ${total} | Passed: ${passed} | Failed: ${failed}`);
    console.log(`Success Rate: ${((passed / total) * 100).toFixed(1)}%`);
    
    if (failed > 0) {
      process.exit(1);
    }
  }

  async cleanup() {
    console.log('\n🧹 Cleaning up...');
    
    if (this.browser) {
      await this.browser.close();
    }
    
    if (this.appProcess) {
      this.appProcess.kill('SIGTERM');
    }
    
    // Clean up test files
    const testFiles = [
      path.join(__dirname, 'test-document.txt'),
      path.join(__dirname, 'large-test-file.txt')
    ];
    
    testFiles.forEach(filePath => {
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
      }
    });
  }
}

// Main test execution
async function main() {
  const tester = new AdvancedVectorStoreTester();
  
  try {
    await tester.startApp();
    await tester.connectToApp();
    await tester.runAllTests();
  } catch (error) {
    console.error('❌ Advanced test suite failed:', error);
    process.exit(1);
  } finally {
    await tester.cleanup();
  }
}

// Run tests if this file is executed directly
if (require.main === module) {
  main();
}

module.exports = AdvancedVectorStoreTester; 