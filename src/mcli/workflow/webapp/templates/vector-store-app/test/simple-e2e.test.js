// Simple E2E Playwright test for Vector Store Manager Electron app
// Focuses on basic app startup and UI elements

const { test, expect } = require('@playwright/test');
const { _electron: electron } = require('playwright');
const fs = require('fs');
const path = require('path');
const { setupTestEnvironment, teardownTestEnvironment, waitForPort } = require('./test-helper');

test.describe('Vector Store Manager Basic E2E', () => {
  let electronApp, page;
  let testPort;

  test.beforeAll(async () => {
    // Setup test environment and find available port
    testPort = await setupTestEnvironment();
    
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
    await teardownTestEnvironment();
  });

  test('should load the app and display main UI elements', async () => {
    // Check that main UI elements are present
    await expect(page.locator('.app-container')).toBeVisible();
    await expect(page.locator('#uploadBtn')).toBeVisible();
    await expect(page.locator('#searchInput')).toBeVisible();
    await expect(page.locator('#searchBtn')).toBeVisible();
    await expect(page.locator('#refreshDocs')).toBeVisible();
    await expect(page.locator('#documentsList')).toBeVisible();
    await expect(page.locator('#chatContainer')).toBeVisible();
  });

  test('should open upload modal when upload button is clicked', async () => {
    await page.click('#uploadBtn');
    await expect(page.locator('#uploadModal')).toBeVisible();
    await expect(page.locator('#fileInput')).toBeAttached();
    await expect(page.locator('#confirmUpload')).toBeVisible();
    
    // Close modal
    await page.click('.close-modal');
    await expect(page.locator('#uploadModal')).not.toBeVisible();
  });

  test('should display welcome message initially', async () => {
    await expect(page.locator('.welcome-message')).toBeVisible();
    await expect(page.locator('.welcome-message h2')).toContainText('Welcome to Vector Store Manager');
  });

  test('should have search options available', async () => {
    await expect(page.locator('#semanticSearch')).toBeChecked();
    await expect(page.locator('#exactMatch')).not.toBeChecked();
  });

  test('should show status bar with document count', async () => {
    await expect(page.locator('#documentCount')).toBeVisible();
    await expect(page.locator('#documentCount')).toContainText('0 documents');
  });
}); 