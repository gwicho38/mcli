const puppeteer = require('puppeteer');
const { spawn } = require('child_process');
const path = require('path');

class SimpleVectorStoreTester {
  constructor() {
    this.appProcess = null;
    this.browser = null;
    this.page = null;
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
          setTimeout(resolve, 3000); // Give app time to fully initialize
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

  async testBasicUI() {
    console.log('🧪 Testing basic UI elements...');
    
    // Test main container
    const appContainer = await this.page.$('.app-container');
    if (!appContainer) {
      throw new Error('App container not found');
    }
    console.log('✅ App container found');

    // Test header
    const header = await this.page.$('.header');
    if (!header) {
      throw new Error('Header not found');
    }
    console.log('✅ Header found');

    // Test logo/title
    const logo = await this.page.$('.logo span');
    if (!logo) {
      throw new Error('Logo/title not found');
    }
    const titleText = await logo.evaluate(el => el.textContent);
    if (!titleText.includes('Vector Store Manager')) {
      throw new Error('App title not found');
    }
    console.log('✅ App title found:', titleText);

    // Test search container
    const searchContainer = await this.page.$('.search-container');
    if (!searchContainer) {
      throw new Error('Search container not found');
    }
    console.log('✅ Search container found');

    // Test search input
    const searchInput = await this.page.$('#searchInput');
    if (!searchInput) {
      throw new Error('Search input not found');
    }
    console.log('✅ Search input found');

    // Test upload button
    const uploadBtn = await this.page.$('#uploadBtn');
    if (!uploadBtn) {
      throw new Error('Upload button not found');
    }
    console.log('✅ Upload button found');

    // Test visualize button
    const visualizeBtn = await this.page.$('#visualizeBtn');
    if (!visualizeBtn) {
      throw new Error('Visualize button not found');
    }
    console.log('✅ Visualize button found');

    // Test documents list
    const documentsList = await this.page.$('#documentsList');
    if (!documentsList) {
      throw new Error('Documents list not found');
    }
    console.log('✅ Documents list found');

    // Test chat container
    const chatContainer = await this.page.$('#chatContainer');
    if (!chatContainer) {
      throw new Error('Chat container not found');
    }
    console.log('✅ Chat container found');

    // Test welcome message
    const welcomeMessage = await this.page.$('.welcome-message');
    if (!welcomeMessage) {
      throw new Error('Welcome message not found');
    }
    console.log('✅ Welcome message found');
  }

  async testButtonInteractions() {
    console.log('🧪 Testing button interactions...');
    
    // Test upload button click
    const uploadBtn = await this.page.$('#uploadBtn');
    await uploadBtn.click();
    await this.page.waitForTimeout(1000);
    
    // Check if upload modal appears
    const uploadModal = await this.page.$('#uploadModal');
    if (!uploadModal) {
      throw new Error('Upload modal not found after clicking upload button');
    }
    console.log('✅ Upload modal appears');

    // Test upload area
    const uploadArea = await this.page.$('#uploadArea');
    if (!uploadArea) {
      throw new Error('Upload area not found');
    }
    console.log('✅ Upload area found');

    // Close modal
    const closeBtn = await this.page.$('.close-modal');
    if (closeBtn) {
      await closeBtn.click();
      await this.page.waitForTimeout(500);
    }

    // Test visualize button click
    const visualizeBtn = await this.page.$('#visualizeBtn');
    await visualizeBtn.click();
    await this.page.waitForTimeout(1000);
    
    // Check if visualization panel appears
    const vizPanel = await this.page.$('#visualizationPanel');
    if (!vizPanel) {
      throw new Error('Visualization panel not found after clicking visualize button');
    }
    console.log('✅ Visualization panel appears');

    // Test visualization controls
    const clusteringSelect = await this.page.$('#clusteringMethod');
    if (clusteringSelect) {
      await clusteringSelect.select('kmeans');
      console.log('✅ Clustering method selection works');
    }

    const dimensionSelect = await this.page.$('#dimensionReduction');
    if (dimensionSelect) {
      await dimensionSelect.select('pca');
      console.log('✅ Dimension reduction selection works');
    }

    // Close visualization panel
    const closeVizBtn = await this.page.$('#closeViz');
    if (closeVizBtn) {
      await closeVizBtn.click();
      await this.page.waitForTimeout(500);
    }
  }

  async testSearchFunctionality() {
    console.log('🧪 Testing search functionality...');
    
    // Test search input
    const searchInput = await this.page.$('#searchInput');
    await searchInput.click();
    await searchInput.type('test query');
    
    // Check if input has the value
    const inputValue = await searchInput.evaluate(el => el.value);
    if (inputValue !== 'test query') {
      throw new Error('Search input not working properly');
    }
    console.log('✅ Search input works');

    // Test search options
    const semanticSearch = await this.page.$('#semanticSearch');
    if (semanticSearch) {
      const isChecked = await semanticSearch.evaluate(el => el.checked);
      if (!isChecked) {
        throw new Error('Semantic search should be enabled by default');
      }
      console.log('✅ Semantic search is enabled by default');
    }

    const exactMatch = await this.page.$('#exactMatch');
    if (exactMatch) {
      const isChecked = await exactMatch.evaluate(el => el.checked);
      if (isChecked) {
        throw new Error('Exact match should be disabled by default');
      }
      console.log('✅ Exact match is disabled by default');
    }
  }

  async runTests() {
    console.log('🧪 Starting simple Vector Store Manager tests...\n');
    
    try {
      await this.testBasicUI();
      await this.testButtonInteractions();
      await this.testSearchFunctionality();
      
      console.log('\n✅ All tests passed!');
      console.log('📊 Test Summary:');
      console.log('  - Basic UI elements: ✅');
      console.log('  - Button interactions: ✅');
      console.log('  - Search functionality: ✅');
      
    } catch (error) {
      console.error('\n❌ Test failed:', error.message);
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
  }
}

// Main test execution
async function main() {
  const tester = new SimpleVectorStoreTester();
  
  try {
    await tester.startApp();
    await tester.connectToApp();
    await tester.runTests();
  } catch (error) {
    console.error('❌ Simple test suite failed:', error);
    process.exit(1);
  } finally {
    await tester.cleanup();
  }
}

// Run tests if this file is executed directly
if (require.main === module) {
  main();
}

module.exports = SimpleVectorStoreTester; 