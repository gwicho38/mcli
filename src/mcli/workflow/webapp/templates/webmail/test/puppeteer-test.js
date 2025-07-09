const puppeteer = require('puppeteer');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

class VectorStoreAppTester {
  constructor() {
    this.appProcess = null;
    this.browser = null;
    this.page = null;
    this.testResults = [];
    this.appPath = path.join(__dirname, '..');
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
          setTimeout(resolve, 2000); // Give app time to fully initialize
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
        '--disable-gpu'
      ]
    });

    const pages = await this.browser.pages();
    this.page = pages[0];
    
    // Wait for the app to load
    await this.page.waitForSelector('#app', { timeout: 10000 });
    console.log('✅ Connected to Electron app');
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

  async testAppLoading() {
    // Test that the app loads properly
    await this.page.waitForSelector('.app-container', { timeout: 10000 });
    await this.page.waitForSelector('.search-container', { timeout: 5000 });
    await this.page.waitForSelector('#uploadArea', { timeout: 5000 });
    
    // Check for main UI elements
    const title = await this.page.$eval('.logo span', el => el.textContent);
    if (!title.includes('Vector Store Manager')) {
      throw new Error('App title not found');
    }
  }

  async testFileUpload() {
    // Test drag and drop file upload
    const uploadArea = await this.page.$('#uploadArea');
    
    // Create a test file
    const testFilePath = path.join(__dirname, 'test-document.txt');
    fs.writeFileSync(testFilePath, 'This is a test document for vector store testing.');
    
    // Simulate file drop
    await this.page.evaluateHandle((uploadArea) => {
      const dataTransfer = new DataTransfer();
      const file = new File(['Test content'], 'test-document.txt', { type: 'text/plain' });
      dataTransfer.items.add(file);
      
      const dropEvent = new Event('drop', { bubbles: true });
      dropEvent.dataTransfer = dataTransfer;
      uploadArea.dispatchEvent(dropEvent);
    }, uploadArea);
    
    // Wait for upload processing
    await this.page.waitForSelector('.uploaded-files', { timeout: 10000 });
  }

  async testSearchFunctionality() {
    // Test search input
    const searchInput = await this.page.$('#searchInput');
    await searchInput.type('test document');
    
    // Wait for search results
    await this.page.waitForTimeout(2000);
    
    // Check if search input has the value
    const inputValue = await searchInput.evaluate(el => el.value);
    if (inputValue !== 'test document') {
      throw new Error('Search input not working properly');
    }
  }

  async testDocumentManagement() {
    // Test document list
    await this.page.waitForSelector('#documentsList', { timeout: 5000 });
    
    // Test document list loading
    const documentsList = await this.page.$('#documentsList');
    const listContent = await documentsList.evaluate(el => el.textContent);
    if (!listContent.includes('Loading documents')) {
      throw new Error('Document list not loading properly');
    }
  }

  async testVectorVisualization() {
    // Test vector visualization button
    const vizButton = await this.page.$('#visualizeBtn');
    if (vizButton) {
      await vizButton.click();
      await this.page.waitForSelector('#visualizationPanel', { timeout: 5000 });
    }
  }

  async testSettingsAndConfiguration() {
    // Test search options
    const semanticSearch = await this.page.$('#semanticSearch');
    if (semanticSearch) {
      const isChecked = await semanticSearch.evaluate(el => el.checked);
      if (!isChecked) {
        throw new Error('Semantic search should be enabled by default');
      }
    }
    
    // Test exact match option
    const exactMatch = await this.page.$('#exactMatch');
    if (exactMatch) {
      const isChecked = await exactMatch.evaluate(el => el.checked);
      if (isChecked) {
        throw new Error('Exact match should be disabled by default');
      }
    }
  }

  async testErrorHandling() {
    // Test error handling by trying to upload an invalid file
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

  async testPerformance() {
    // Test app performance by measuring load times
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
    
    const totalTime = Date.now() - startTime;
    if (totalTime > 5000) {
      throw new Error(`Performance test failed: Button interactions took ${totalTime}ms`);
    }
  }

  async runAllTests() {
    console.log('🧪 Starting comprehensive Vector Store Manager tests...\n');
    
    await this.runTest('App Loading', () => this.testAppLoading());
    await this.runTest('File Upload', () => this.testFileUpload());
    await this.runTest('Search Functionality', () => this.testSearchFunctionality());
    await this.runTest('Document Management', () => this.testDocumentManagement());
    await this.runTest('Vector Visualization', () => this.testVectorVisualization());
    await this.runTest('Settings and Configuration', () => this.testSettingsAndConfiguration());
    await this.runTest('Error Handling', () => this.testErrorHandling());
    await this.runTest('Performance', () => this.testPerformance());
    
    this.printResults();
  }

  printResults() {
    console.log('\n📊 Test Results Summary:');
    console.log('='.repeat(50));
    
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
    
    console.log('\n' + '='.repeat(50));
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
    const testFilePath = path.join(__dirname, 'test-document.txt');
    if (fs.existsSync(testFilePath)) {
      fs.unlinkSync(testFilePath);
    }
  }
}

// Main test execution
async function main() {
  const tester = new VectorStoreAppTester();
  
  try {
    await tester.startApp();
    await tester.connectToApp();
    await tester.runAllTests();
  } catch (error) {
    console.error('❌ Test suite failed:', error);
    process.exit(1);
  } finally {
    await tester.cleanup();
  }
}

// Run tests if this file is executed directly
if (require.main === module) {
  main();
}

module.exports = VectorStoreAppTester; 