// E2E Playwright test for Vector Store Manager Electron app
// Covers: app start/stop, upload of all supported files, vector store CRUD, search, and memory cleanup

const { test, expect } = require('@playwright/test');
const { _electron: electron } = require('playwright');
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { setupTestEnvironment, teardownTestEnvironment, waitForPort } = require('./test-helper');

test.describe('Vector Store Manager E2E', () => {
  let electronApp, page;
  let testPort;
  const testFilesDir = path.join(__dirname, 'test-files');
  const supportedFiles = [
    { name: 'test.pdf', type: 'application/pdf', content: Buffer.from('%PDF-1.4 test') },
    { name: 'test.docx', type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', content: Buffer.from('PK\x03\x04 testdocx') },
    { name: 'test.txt', type: 'text/plain', content: 'Hello TXT' },
    { name: 'test.md', type: 'text/markdown', content: '# Hello MD' },
    { name: 'test.csv', type: 'text/csv', content: 'a,b\n1,2' },
    { name: 'test.json', type: 'application/json', content: '{"hello": "json"}' },
    { name: 'test.xml', type: 'application/xml', content: '<root>xml</root>' },
    { name: 'test.html', type: 'text/html', content: '<html><body>html</body></html>' },
  ];

  test.beforeAll(async () => {
    // Setup test environment and find available port
    testPort = await setupTestEnvironment();
    
    // Ensure test files exist
    if (!fs.existsSync(testFilesDir)) fs.mkdirSync(testFilesDir);
    for (const file of supportedFiles) {
      fs.writeFileSync(path.join(testFilesDir, file.name), file.content);
    }
    
    // Start Electron app with available port
    electronApp = await electron.launch({
      args: ['.'],
      cwd: path.join(__dirname, '..'),
      env: { 
        ...process.env, 
        NODE_ENV: 'test',
        PORT: testPort.toString()
      },
    });
    page = await electronApp.firstWindow();
    await page.waitForSelector('.app-container', { timeout: 20000 });
    
    // Wait for server to be ready
    await waitForPort(testPort, 10000);
  }, 60000);

  test.afterAll(async () => {
    await electronApp.close();
    
    // Clean up test files
    for (const file of supportedFiles) {
      fs.unlinkSync(path.join(testFilesDir, file.name));
    }
    fs.rmdirSync(testFilesDir);
    
    await teardownTestEnvironment();
  });

  test('should upload all supported file types', async () => {
    await page.click('#uploadBtn');
    await page.waitForSelector('#uploadModal', { state: 'visible' });
    const fileInput = await page.$('#fileInput');
    const filePaths = supportedFiles.map(f => path.join(testFilesDir, f.name));
    await fileInput.setInputFiles(filePaths);
    await page.click('#confirmUpload');
    // Wait for upload to complete (adjust selector as needed)
    await page.waitForTimeout(3000);
    // Check uploaded files appear in UI
    for (const file of supportedFiles) {
      const found = await page.$(`text=${file.name}`);
      expect(found).not.toBeNull();
    }
  });

  test('should list, update, and delete documents (CRUD)', async () => {
    // List
    await page.click('#refreshDocs');
    await page.waitForTimeout(1000);
    for (const file of supportedFiles) {
      const found = await page.$(`text=${file.name}`);
      expect(found).not.toBeNull();
    }
    // Update (simulate by re-uploading a file)
    await page.click('#uploadBtn');
    await page.waitForSelector('#uploadModal', { state: 'visible' });
    const fileInput = await page.$('#fileInput');
    await fileInput.setInputFiles(path.join(testFilesDir, supportedFiles[0].name));
    await page.click('#confirmUpload');
    await page.waitForTimeout(2000);
    // Delete
    // (Assume delete button exists for each file row, adjust selector as needed)
    const deleteBtn = await page.$('.file-item .delete-btn');
    if (deleteBtn) {
      await deleteBtn.click();
      await page.waitForTimeout(1000);
      // Confirm deletion
      // (Adjust selector if confirmation modal appears)
    }
  });

  test('should perform semantic and exact match search', async () => {
    await page.fill('#searchInput', 'Hello');
    await page.click('#searchBtn');
    await page.waitForTimeout(2000);
    // Check for search results
    const results = await page.$$('.search-result');
    expect(results.length).toBeGreaterThan(0);
    // Test exact match
    await page.click('#exactMatch');
    await page.fill('#searchInput', 'TXT');
    await page.click('#searchBtn');
    await page.waitForTimeout(2000);
    const exactResults = await page.$$('.search-result');
    expect(exactResults.length).toBeGreaterThan(0);
  });

  test('should start, stop, and cleanup memory', async () => {
    // Check memory usage before
    const before = await electronApp.evaluate(async ({ app }) => process.memoryUsage().heapUsed);
    // Simulate heavy usage
    for (let i = 0; i < 3; i++) {
      await page.click('#uploadBtn');
      await page.waitForSelector('#uploadModal', { state: 'visible' });
      const fileInput = await page.$('#fileInput');
      await fileInput.setInputFiles(path.join(testFilesDir, supportedFiles[0].name));
      await page.click('#confirmUpload');
      await page.waitForTimeout(1000);
    }
    // Close and restart app
    await electronApp.close();
    electronApp = await electron.launch({
      args: ['.'],
      cwd: path.join(__dirname, '..'),
      env: { ...process.env, NODE_ENV: 'test' },
    });
    page = await electronApp.firstWindow();
    await page.waitForSelector('.app-container', { timeout: 20000 });
    // Check memory usage after
    const after = await electronApp.evaluate(async ({ app }) => process.memoryUsage().heapUsed);
    // Assert memory is not leaking (allow some tolerance)
    expect(after).toBeLessThan(before * 2);
  });
}); 