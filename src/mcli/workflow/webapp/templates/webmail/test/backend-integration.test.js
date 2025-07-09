#!/usr/bin/env node

/**
 * Backend Integration Test Suite
 * Tests all backend functions and API endpoints
 */

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const sqlite3 = require('sqlite3').verbose();

class BackendIntegrationTest {
    constructor() {
        this.testResults = [];
        this.appProcess = null;
        this.apiBaseUrl = 'http://localhost:3001/api';
        this.testDataPath = path.join(__dirname, 'test-data');
        
        // Use the app's actual vector store path
        const userDataPath = require('os').homedir();
        this.vectorStorePath = path.join(userDataPath, '.local', 'mcli', 'webapps', 'My_Vector_Store', 'vector-store');
        
        // Ensure test directories exist
        fs.mkdirSync(this.testDataPath, { recursive: true });
        fs.mkdirSync(this.vectorStorePath, { recursive: true });
    }
    
    async run() {
        console.log('🚀 Starting Backend Integration Test Suite...\n');
        
        try {
            await this.startApp();
            await this.waitForAppReady();
            
            // Run all test suites
            await this.testDatabaseOperations();
            await this.testFileProcessing();
            await this.testEmbeddingGeneration();
            await this.testSearchFunctionality();
            await this.testAPIEndpoints();
            await this.testWebSocketCommunication();
            await this.testErrorHandling();
            
            await this.stopApp();
            this.printResults();
            
        } catch (error) {
            console.error('❌ Test suite failed:', error);
            await this.stopApp();
            process.exit(1);
        }
    }
    
    async startApp() {
        console.log('📱 Starting Vector Store app...');
        
        return new Promise((resolve, reject) => {
            this.appProcess = spawn('npm', ['start'], {
                cwd: path.dirname(__dirname),
                stdio: ['pipe', 'pipe', 'pipe']
            });
            
            let output = '';
            
            this.appProcess.stdout.on('data', (data) => {
                output += data.toString();
                if (output.includes('Vector Store API server running on port')) {
                    console.log('✅ App started successfully');
                    resolve();
                }
            });
            
            this.appProcess.stderr.on('data', (data) => {
                console.error('App stderr:', data.toString());
            });
            
            this.appProcess.on('error', reject);
            
            // Timeout after 30 seconds
            setTimeout(() => {
                if (!output.includes('Vector Store API server running on port')) {
                    reject(new Error('App failed to start within 30 seconds'));
                }
            }, 30000);
        });
    }
    
    async waitForAppReady() {
        console.log('⏳ Waiting for app to be ready...');
        
        for (let i = 0; i < 30; i++) {
            try {
                const response = await fetch(`${this.apiBaseUrl}/health`);
                if (response.ok) {
                    console.log('✅ App is ready');
                    return;
                }
            } catch (error) {
                // Continue waiting
            }
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
        
        throw new Error('App failed to become ready');
    }
    
    async stopApp() {
        if (this.appProcess) {
            console.log('🛑 Stopping app...');
            this.appProcess.kill('SIGTERM');
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
    }
    
    async testDatabaseOperations() {
        console.log('\n🗄️  Testing Database Operations...');
        
        const dbPath = path.join(this.vectorStorePath, 'vector_store.db');
        
        // Test database initialization - check if tables exist
        try {
            const db = new sqlite3.Database(dbPath);
            const tables = await this.runQuery(db, "SELECT name FROM sqlite_master WHERE type='table'");
            if (tables.length > 0) {
                this.addResult('Database initialization', true, `Found ${tables.length} tables`);
            } else {
                this.addResult('Database initialization', false, 'No tables found');
            }
            db.close();
        } catch (error) {
            this.addResult('Database initialization', false, error.message);
        }
        
        // Test document insertion via API instead of direct DB access
        try {
            const response = await fetch(`${this.apiBaseUrl}/documents`);
            const data = await response.json();
            if (data.success !== undefined) {
                this.addResult('API document access', true, 'API endpoint working');
            } else {
                this.addResult('API document access', false, 'API response format unexpected');
            }
        } catch (error) {
            this.addResult('API document access', false, error.message);
        }
    }
    
    async testFileProcessing() {
        console.log('\n📄 Testing File Processing...');
        
        // Create test files
        const testFiles = [
            { name: 'test.txt', content: 'This is a test text file with some content for processing.', mime: 'text/plain' },
            { name: 'test.json', content: JSON.stringify({ test: 'data', number: 42 }), mime: 'application/json' },
            { name: 'test.csv', content: 'name,age,city\nJohn,30,NYC\nJane,25,LA', mime: 'text/csv' }
        ];
        
        for (const file of testFiles) {
            const filePath = path.join(this.testDataPath, file.name);
            fs.writeFileSync(filePath, file.content);
            
            try {
                const FormData = require('form-data');
                const form = new FormData();
                form.append('files', fs.createReadStream(filePath));
                
                const response = await fetch(`${this.apiBaseUrl}/upload`, {
                    method: 'POST',
                    body: form
                });
                
                const result = await response.json();
                console.log(`Upload response for ${file.name}:`, JSON.stringify(result, null, 2));
                if (result.success) {
                    this.addResult(`File processing: ${file.name}`, true, 'File processed successfully');
                } else {
                    this.addResult(`File processing: ${file.name}`, false, result.error || 'Upload failed');
                }
            } catch (error) {
                this.addResult(`File processing: ${file.name}`, false, error.message);
            }
        }
    }
    
    async testEmbeddingGeneration() {
        console.log('\n🧠 Testing Embedding Generation...');
        
        try {
            // Test embedding generation via Python backend
            const pythonScript = path.join(__dirname, '..', 'python', 'generate_embeddings.py');
            const testText = 'This is a test text for embedding generation.';
            
            const result = await this.runPythonScript(pythonScript, [testText, 'test-embedding-1', this.vectorStorePath]);
            
            if (result && result.embedding_count > 0) {
                this.addResult('Embedding generation', true, `Generated ${result.embedding_count} embeddings`);
            } else {
                this.addResult('Embedding generation', false, 'No embeddings generated');
            }
        } catch (error) {
            this.addResult('Embedding generation', false, error.message);
        }
    }
    
    async testSearchFunctionality() {
        console.log('\n🔍 Testing Search Functionality...');
        
        try {
            // Test semantic search
            const searchResponse = await fetch(`${this.apiBaseUrl}/search`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: 'test content',
                    top_k: 5,
                    exact_match: false
                })
            });
            
            const searchResult = await searchResponse.json();
            if (searchResult.success) {
                this.addResult('Semantic search', true, `Found ${searchResult.results.length} results`);
            } else {
                this.addResult('Semantic search', false, searchResult.error);
            }
        } catch (error) {
            this.addResult('Semantic search', false, error.message);
        }
        
        try {
            // Test exact search
            const exactSearchResponse = await fetch(`${this.apiBaseUrl}/search`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: 'test',
                    top_k: 5,
                    exact_match: true
                })
            });
            
            const exactResult = await exactSearchResponse.json();
            if (exactResult.success) {
                this.addResult('Exact search', true, `Found ${exactResult.results.length} results`);
            } else {
                this.addResult('Exact search', false, exactResult.error);
            }
        } catch (error) {
            this.addResult('Exact search', false, error.message);
        }
    }
    
    async testAPIEndpoints() {
        console.log('\n🌐 Testing API Endpoints...');
        
        const endpoints = [
            { path: '/health', method: 'GET', name: 'Health check' },
            { path: '/documents', method: 'GET', name: 'Get documents' },
            { path: '/stats', method: 'GET', name: 'Get stats' },
            { path: '/visualization', method: 'GET', name: 'Get visualization' }
        ];
        
        for (const endpoint of endpoints) {
            try {
                const response = await fetch(`${this.apiBaseUrl}${endpoint.path}`, {
                    method: endpoint.method
                });
                
                if (response.ok) {
                    const data = await response.json();
                    this.addResult(endpoint.name, true, 'Endpoint working correctly');
                } else {
                    this.addResult(endpoint.name, false, `HTTP ${response.status}`);
                }
            } catch (error) {
                this.addResult(endpoint.name, false, error.message);
            }
        }
    }
    
    async testWebSocketCommunication() {
        console.log('\n🔌 Testing WebSocket Communication...');
        
        try {
            const WebSocket = require('ws');
            const ws = new WebSocket('ws://localhost:3001');
            
            const messages = [];
            
            ws.on('open', () => {
                this.addResult('WebSocket connection', true, 'Connected successfully');
            });
            
            ws.on('message', (data) => {
                const message = JSON.parse(data);
                messages.push(message);
            });
            
            // Wait for some messages
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            if (messages.length > 0) {
                this.addResult('WebSocket messages', true, `Received ${messages.length} messages`);
            } else {
                this.addResult('WebSocket messages', false, 'No messages received');
            }
            
            ws.close();
        } catch (error) {
            this.addResult('WebSocket communication', false, error.message);
        }
    }
    
    async testErrorHandling() {
        console.log('\n⚠️  Testing Error Handling...');
        
        // Test invalid document ID
        try {
            const response = await fetch(`${this.apiBaseUrl}/document/invalid-id`);
            if (response.status === 404) {
                this.addResult('Invalid document handling', true, 'Properly handled invalid document ID');
            } else {
                this.addResult('Invalid document handling', false, 'Did not handle invalid document ID correctly');
            }
        } catch (error) {
            this.addResult('Invalid document handling', false, error.message);
        }
        
        // Test invalid search query
        try {
            const response = await fetch(`${this.apiBaseUrl}/search`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            
            const result = await response.json();
            if (response.status === 400) {
                this.addResult('Invalid search handling', true, 'Properly handled invalid search query');
            } else {
                this.addResult('Invalid search handling', false, 'Did not handle invalid search query correctly');
            }
        } catch (error) {
            this.addResult('Invalid search handling', false, error.message);
        }
    }
    
    // Helper methods
    async runQuery(db, sql, params = []) {
        return new Promise((resolve, reject) => {
            db.all(sql, params, (err, rows) => {
                if (err) reject(err);
                else resolve(rows);
            });
        });
    }
    
    async runPythonScript(scriptPath, args) {
        return new Promise((resolve, reject) => {
            // Use the virtual environment's Python
            const venvPython = path.join(__dirname, '..', 'venv', 'bin', 'python3');
            const pythonProcess = spawn(venvPython, [scriptPath, ...args]);
            
            let output = '';
            let errorOutput = '';
            
            pythonProcess.stdout.on('data', (data) => {
                output += data.toString();
            });
            
            pythonProcess.stderr.on('data', (data) => {
                errorOutput += data.toString();
            });
            
            pythonProcess.on('close', (code) => {
                if (code === 0) {
                    try {
                        const result = JSON.parse(output.trim());
                        resolve(result);
                    } catch (error) {
                        resolve(output.trim());
                    }
                } else {
                    reject(new Error(`Python script failed: ${errorOutput}`));
                }
            });
        });
    }
    
    // Removed createFormData method as it's no longer needed
    
    addResult(testName, passed, message) {
        this.testResults.push({ testName, passed, message });
        const status = passed ? '✅' : '❌';
        console.log(`${status} ${testName}: ${message}`);
    }
    
    printResults() {
        console.log('\n📊 Test Results Summary:');
        console.log('========================');
        
        const passed = this.testResults.filter(r => r.passed).length;
        const total = this.testResults.length;
        const failed = total - passed;
        
        console.log(`Total Tests: ${total}`);
        console.log(`Passed: ${passed}`);
        console.log(`Failed: ${failed}`);
        console.log(`Success Rate: ${((passed / total) * 100).toFixed(1)}%`);
        
        if (failed > 0) {
            console.log('\n❌ Failed Tests:');
            this.testResults.filter(r => !r.passed).forEach(result => {
                console.log(`  - ${result.testName}: ${result.message}`);
            });
        }
        
        console.log('\n🎉 Backend Integration Test Suite completed!');
    }
}

// Run the test suite
if (require.main === module) {
    const test = new BackendIntegrationTest();
    test.run().catch(console.error);
}

module.exports = BackendIntegrationTest; 