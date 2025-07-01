const puppeteer = require('puppeteer');
const http = require('http');

async function testAPIEndpoints() {
  console.log('🔌 Testing API endpoints...');
  
  const endpoints = [
    { path: '/api/documents', method: 'GET', name: 'Documents API' },
    { path: '/api/vector-visualization', method: 'GET', name: 'Vector Visualization API' },
    { path: '/api/document/1', method: 'GET', name: 'Document Details API' }
  ];

  for (const endpoint of endpoints) {
    try {
      const response = await makeRequest(endpoint.path, endpoint.method);
      if (response.statusCode === 200) {
        console.log(`✅ ${endpoint.name} - ${response.statusCode}`);
      } else {
        throw new Error(`Expected status 200, got ${response.statusCode}`);
      }
    } catch (error) {
      console.error(`❌ ${endpoint.name} failed: ${error.message}`);
      throw error;
    }
  }
}

function makeRequest(path, method = 'GET') {
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

    req.end();
  });
}

async function testUIElements() {
  console.log('🔗 Testing UI elements...');
  
  const browser = await puppeteer.launch({
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

  try {
    const pages = await browser.pages();
    const page = pages[0];
    
    // Navigate to the app
    await page.goto('http://localhost:3001', { waitUntil: 'networkidle0' });
    console.log('✅ App loaded in browser');

    // Test basic UI elements
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

  } finally {
    await browser.close();
  }
}

async function runValidation() {
  console.log('🧪 Starting Vector Store Manager validation...\n');
  
  try {
    await testAPIEndpoints();
    await testUIElements();
    
    console.log('\n🎉 All tests passed! The Vector Store Manager app is working correctly.');
    console.log('\n📊 Validation Summary:');
    console.log('  ✅ API endpoints are responding');
    console.log('  ✅ App loads in browser');
    console.log('  ✅ All UI elements are present');
    console.log('  ✅ Button interactions work');
    console.log('  ✅ Search functionality works');
    console.log('  ✅ Modal dialogs work');
    console.log('  ✅ Default settings are correct');
    
  } catch (error) {
    console.error('\n❌ Validation failed:', error.message);
    process.exit(1);
  }
}

// Run validation
runValidation(); 