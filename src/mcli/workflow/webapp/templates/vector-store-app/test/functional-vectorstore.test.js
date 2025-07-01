// Functional tests for Vector Store Manager - Tests actual vector operations and database functionality
const { test, expect } = require('@playwright/test');
const { _electron: electron } = require('playwright');
const fs = require('fs');
const path = require('path');
const { setupTestEnvironment, teardownTestEnvironment, waitForPort } = require('./test-helper');

test.describe('Vector Store Functional Tests', () => {
  let electronApp, page;
  let testPort;
  const testFilesDir = path.join(__dirname, 'test-files');
  
  // Test documents with known content for verification
  const testDocuments = [
    {
      name: 'sample.txt',
      content: 'This is a sample text document about artificial intelligence and machine learning. It contains information about neural networks, deep learning, and natural language processing.',
      type: 'text/plain'
    },
    {
      name: 'research.md',
      content: '# Research Paper\n\nThis document discusses vector embeddings and their applications in information retrieval. Key topics include:\n\n- Semantic search\n- Document similarity\n- Vector databases\n- Embedding models',
      type: 'text/markdown'
    },
    {
      name: 'data.json',
      content: JSON.stringify({
        title: 'Sample Data',
        description: 'This JSON document contains structured data about technology topics',
        topics: ['AI', 'ML', 'NLP', 'Vector Search'],
        metadata: {
          author: 'Test User',
          date: '2024-01-01'
        }
      }),
      type: 'application/json'
    }
  ];

  test.beforeAll(async () => {
    // Setup test environment and find available port
    testPort = await setupTestEnvironment();
    
    // Create test files
    if (!fs.existsSync(testFilesDir)) fs.mkdirSync(testFilesDir);
    for (const doc of testDocuments) {
      fs.writeFileSync(path.join(testFilesDir, doc.name), doc.content);
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
  }, 120000);

  test.afterAll(async () => {
    await electronApp.close();
    
    // Clean up test files
    for (const doc of testDocuments) {
      const filePath = path.join(testFilesDir, doc.name);
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
      }
    }
    if (fs.existsSync(testFilesDir)) {
      fs.rmdirSync(testFilesDir);
    }
    
    await teardownTestEnvironment();
  });

  test('should create vector database and store documents', async () => {
    // Upload test documents
    await page.click('#uploadBtn');
    await page.waitForSelector('#uploadModal', { state: 'visible' });
    
    const fileInput = await page.$('#fileInput');
    const filePaths = testDocuments.map(doc => path.join(testFilesDir, doc.name));
    await fileInput.setInputFiles(filePaths);
    
    await page.click('#confirmUpload');
    
    // Wait for upload and processing to complete
    await page.waitForTimeout(5000);
    
    // Check that documents appear in the UI
    for (const doc of testDocuments) {
      const docElement = await page.$(`text=${doc.name}`);
      expect(docElement).not.toBeNull();
    }
    
    // Verify database was created by checking API response
    const response = await page.evaluate(async (port) => {
      const res = await fetch(`http://localhost:${port}/api/documents`);
      return await res.json();
    }, testPort);
    
    expect(response.success).toBe(true);
    expect(response.documents.length).toBeGreaterThanOrEqual(testDocuments.length);
  });

  test('should generate embeddings and store them in database', async () => {
    // Get the first document ID from the API
    const documentsResponse = await page.evaluate(async (port) => {
      const res = await fetch(`http://localhost:${port}/api/documents`);
      return await res.json();
    }, testPort);
    
    expect(documentsResponse.success).toBe(true);
    expect(documentsResponse.documents.length).toBeGreaterThan(0);
    
    const firstDoc = documentsResponse.documents[0];
    
    // Check that embeddings were generated
    const embeddingsResponse = await page.evaluate(async (port, docId) => {
      const res = await fetch(`http://localhost:${port}/api/embeddings/${docId}`);
      return await res.json();
    }, testPort, firstDoc.id);
    
    expect(embeddingsResponse.success).toBe(true);
    expect(embeddingsResponse.embeddings.length).toBeGreaterThan(0);
    
    // Verify embedding structure
    const embedding = embeddingsResponse.embeddings[0];
    expect(embedding).toHaveProperty('chunk_index');
    expect(embedding).toHaveProperty('text_chunk');
    expect(embedding).toHaveProperty('embedding_vector');
  });

  test('should perform semantic search and return relevant results', async () => {
    // Perform a semantic search
    await page.fill('#searchInput', 'artificial intelligence');
    await page.click('#searchBtn');
    
    // Wait for search results
    await page.waitForTimeout(3000);
    
    // Check that search results are displayed
    const searchResults = await page.$$('.search-result');
    expect(searchResults.length).toBeGreaterThan(0);
    
    // Verify search results contain relevant content
    const resultText = await page.textContent('.search-result');
    expect(resultText).toContain('sample.txt'); // Should find the AI-related document
    
    // Test API search endpoint
    const searchResponse = await page.evaluate(async (port) => {
      const res = await fetch(`http://localhost:${port}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: 'machine learning', top_k: 5 })
      });
      return await res.json();
    }, testPort);
    
    expect(searchResponse.success).toBe(true);
    expect(searchResponse.results.length).toBeGreaterThan(0);
  });

  test('should update UI to reflect current document state', async () => {
    // Refresh document list
    await page.click('#refreshDocs');
    await page.waitForTimeout(2000);
    
    // Check document count in status bar
    const docCount = await page.textContent('#documentCount');
    expect(docCount).toContain(testDocuments.length.toString());
    
    // Verify all test documents are listed
    for (const doc of testDocuments) {
      const docElement = await page.$(`text=${doc.name}`);
      expect(docElement).not.toBeNull();
    }
    
    // Check that processing status is complete
    const processingStatus = await page.$$('.document-status.completed');
    expect(processingStatus.length).toBeGreaterThan(0);
  });

  test('should handle document deletion and update database', async () => {
    // Get current document count
    const initialCount = await page.evaluate(async (port) => {
      const res = await fetch(`http://localhost:${port}/api/documents`);
      const data = await res.json();
      return data.documents.length;
    }, testPort);
    
    // Delete the first document
    const deleteResponse = await page.evaluate(async (port) => {
      const res = await fetch(`http://localhost:${port}/api/documents`);
      const data = await res.json();
      if (data.documents.length > 0) {
        const deleteRes = await fetch(`http://localhost:${port}/api/document/${data.documents[0].id}`, {
          method: 'DELETE'
        });
        return await deleteRes.json();
      }
      return { success: false };
    }, testPort);
    
    expect(deleteResponse.success).toBe(true);
    
    // Verify document count decreased
    const finalCount = await page.evaluate(async (port) => {
      const res = await fetch(`http://localhost:${port}/api/documents`);
      const data = await res.json();
      return data.documents.length;
    }, testPort);
    
    expect(finalCount).toBe(initialCount - 1);
    
    // Refresh UI and verify update
    await page.click('#refreshDocs');
    await page.waitForTimeout(2000);
    
    const newDocCount = await page.textContent('#documentCount');
    expect(newDocCount).toContain(finalCount.toString());
  });

  test('should generate vector visualization data', async () => {
    // Request vector visualization
    const vizResponse = await page.evaluate(async (port) => {
      const res = await fetch(`http://localhost:${port}/api/vector-visualization`);
      return await res.json();
    }, testPort);
    
    expect(vizResponse.success).toBe(true);
    expect(vizResponse.visualization).toBeDefined();
    
    // Verify visualization data structure
    const viz = vizResponse.visualization;
    expect(viz).toHaveProperty('points');
    expect(viz).toHaveProperty('clusters');
    expect(viz).toHaveProperty('metadata');
  });

  test('should handle WebSocket communication for real-time updates', async () => {
    // Listen for WebSocket messages
    const wsMessages = [];
    
    await page.evaluate(async (port) => {
      const ws = new WebSocket(`ws://localhost:${port}`);
      ws.onmessage = (event) => {
        window.wsMessages = window.wsMessages || [];
        window.wsMessages.push(JSON.parse(event.data));
      };
    }, testPort);
    
    // Upload a new document to trigger WebSocket message
    await page.click('#uploadBtn');
    await page.waitForSelector('#uploadModal', { state: 'visible' });
    
    const fileInput = await page.$('#fileInput');
    await fileInput.setInputFiles(path.join(testFilesDir, testDocuments[0].name));
    await page.click('#confirmUpload');
    
    // Wait for WebSocket message
    await page.waitForTimeout(3000);
    
    // Check for WebSocket messages
    const messages = await page.evaluate(() => {
      return window.wsMessages || [];
    });
    
    expect(messages.length).toBeGreaterThan(0);
    
    // Verify message structure
    const message = messages[0];
    expect(message).toHaveProperty('type');
    expect(message.type).toBe('document_processed');
  });

  test('should maintain data persistence across app restarts', async () => {
    // Get current document count
    const docCountBefore = await page.evaluate(async (port) => {
      const res = await fetch(`http://localhost:${port}/api/documents`);
      const data = await res.json();
      return data.documents.length;
    }, testPort);
    
    // Restart the app
    await electronApp.close();
    
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
    await waitForPort(testPort, 10000);
    
    // Verify documents persist
    const docCountAfter = await page.evaluate(async (port) => {
      const res = await fetch(`http://localhost:${port}/api/documents`);
      const data = await res.json();
      return data.documents.length;
    }, testPort);
    
    expect(docCountAfter).toBe(docCountBefore);
    
    // Verify UI reflects persisted data
    await page.waitForTimeout(2000);
    const statusText = await page.textContent('#documentCount');
    expect(statusText).toContain(docCountAfter.toString());
  });
}); 