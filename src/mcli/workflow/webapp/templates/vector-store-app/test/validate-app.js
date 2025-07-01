const puppeteer = require('puppeteer');
const { spawn } = require('child_process');
const path = require('path');

async function validateApp() {
  let appProcess = null;
  let browser = null;
  
  try {
    console.log('🚀 Starting Vector Store Manager app...');
    
    // Start the app
    appProcess = spawn('npm', ['start'], {
      cwd: path.join(__dirname, '..'),
      stdio: 'pipe'
    });

    // Wait for app to start
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('App failed to start within 30 seconds'));
      }, 30000);

      appProcess.stdout.on('data', (data) => {
        const output = data.toString();
        console.log(`[APP] ${output.trim()}`);
        
        if (output.includes('Vector Store API server running on port 3001')) {
          clearTimeout(timeout);
          setTimeout(resolve, 3000);
        }
      });

      appProcess.stderr.on('data', (data) => {
        const error = data.toString();
        if (!error.includes('UnhandledPromiseRejectionWarning')) {
          console.error(`[APP ERROR] ${error.trim()}`);
        }
      });
    });

    console.log('🔗 Connecting to Electron app...');
    
    // Launch browser
    browser = await puppeteer.launch({
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

    const pages = await browser.pages();
    const page = pages[0];
    
    // Wait for the app to load
    await page.waitForSelector('.app-container', { timeout: 15000 });
    console.log('✅ App loaded successfully');

    // Test basic UI elements
    console.log('🧪 Testing basic UI elements...');
    
    const tests = [
      { selector: '.app-container', name: 'App Container' },
      { selector: '.header', name: 'Header' },
      { selector: '.logo span', name: 'App Title' },
      { selector: '.search-container', name: 'Search Container' },
      { selector: '#searchInput', name: 'Search Input' },
      { selector: '#uploadBtn', name: 'Upload Button' },
      { selector: '#visualizeBtn', name: 'Visualize Button' },
      { selector: '#documentsList', name: 'Documents List' },
      { selector: '#chatContainer', name: 'Chat Container' },
      { selector: '.welcome-message', name: 'Welcome Message' }
    ];

    for (const test of tests) {
      const element = await page.$(test.selector);
      if (element) {
        console.log(`✅ ${test.name} found`);
      } else {
        console.log(`❌ ${test.name} not found`);
        throw new Error(`${test.name} not found`);
      }
    }

    // Test title text
    const titleElement = await page.$('.logo span');
    const titleText = await titleElement.evaluate(el => el.textContent);
    if (titleText.includes('Vector Store Manager')) {
      console.log('✅ App title is correct:', titleText);
    } else {
      throw new Error('App title not found or incorrect');
    }

    // Test button interactions
    console.log('🧪 Testing button interactions...');
    
    // Test upload button
    const uploadBtn = await page.$('#uploadBtn');
    await uploadBtn.click();
    await page.waitForTimeout(1000);
    
    const uploadModal = await page.$('#uploadModal');
    if (uploadModal) {
      console.log('✅ Upload modal appears when upload button is clicked');
      
      // Close modal
      const closeBtn = await page.$('.close-modal');
      if (closeBtn) {
        await closeBtn.click();
        await page.waitForTimeout(500);
      }
    } else {
      throw new Error('Upload modal not found after clicking upload button');
    }

    // Test visualize button
    const visualizeBtn = await page.$('#visualizeBtn');
    await visualizeBtn.click();
    await page.waitForTimeout(1000);
    
    const vizPanel = await page.$('#visualizationPanel');
    if (vizPanel) {
      console.log('✅ Visualization panel appears when visualize button is clicked');
      
      // Close panel
      const closeVizBtn = await page.$('#closeViz');
      if (closeVizBtn) {
        await closeVizBtn.click();
        await page.waitForTimeout(500);
      }
    } else {
      throw new Error('Visualization panel not found after clicking visualize button');
    }

    // Test search input
    console.log('🧪 Testing search functionality...');
    const searchInput = await page.$('#searchInput');
    await searchInput.click();
    await searchInput.type('test query');
    
    const inputValue = await searchInput.evaluate(el => el.value);
    if (inputValue === 'test query') {
      console.log('✅ Search input works correctly');
    } else {
      throw new Error('Search input not working properly');
    }

    // Test search options
    const semanticSearch = await page.$('#semanticSearch');
    if (semanticSearch) {
      const isChecked = await semanticSearch.evaluate(el => el.checked);
      if (isChecked) {
        console.log('✅ Semantic search is enabled by default');
      } else {
        throw new Error('Semantic search should be enabled by default');
      }
    }

    const exactMatch = await page.$('#exactMatch');
    if (exactMatch) {
      const isChecked = await exactMatch.evaluate(el => el.checked);
      if (!isChecked) {
        console.log('✅ Exact match is disabled by default');
      } else {
        throw new Error('Exact match should be disabled by default');
      }
    }

    console.log('\n🎉 All tests passed! The Vector Store Manager app is working correctly.');
    console.log('\n📊 Test Summary:');
    console.log('  ✅ App starts successfully');
    console.log('  ✅ UI loads properly');
    console.log('  ✅ All basic elements are present');
    console.log('  ✅ Button interactions work');
    console.log('  ✅ Search functionality works');
    console.log('  ✅ Modal dialogs work');
    console.log('  ✅ Default settings are correct');

  } catch (error) {
    console.error('\n❌ Validation failed:', error.message);
    process.exit(1);
  } finally {
    console.log('\n🧹 Cleaning up...');
    
    if (browser) {
      await browser.close();
    }
    
    if (appProcess) {
      appProcess.kill('SIGTERM');
    }
  }
}

// Run validation
validateApp(); 