#!/usr/bin/env node

/**
 * Simple Vector Store Test
 * Tests basic functionality without full app startup
 */

const fs = require('fs');
const path = require('path');
const sqlite3 = require('sqlite3').verbose();

class SimpleTest {
    constructor() {
        this.testResults = [];
        this.vectorStorePath = path.join(__dirname, 'test-vector-store');
        
        // Ensure test directory exists
        fs.mkdirSync(this.vectorStorePath, { recursive: true });
    }
    
    async run() {
        console.log('🧪 Running Simple Vector Store Tests...\n');
        
        try {
            await this.testDatabaseOperations();
            await this.testPythonBackend();
            await this.testFileOperations();
            
            this.printResults();
            
        } catch (error) {
            console.error('❌ Test failed:', error);
            process.exit(1);
        }
    }
    
    async testDatabaseOperations() {
        console.log('🗄️  Testing Database Operations...');
        
        const dbPath = path.join(this.vectorStorePath, 'vector_store.db');
        
        try {
            // Test database initialization
            const db = new sqlite3.Database(dbPath);
            
            // Create tables
            await this.runQuery(db, `
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    original_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER,
                    mime_type TEXT,
                    upload_date TEXT,
                    text_content TEXT,
                    embedding_count INTEGER DEFAULT 0,
                    processing_status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            `);
            
            await this.runQuery(db, `
                CREATE TABLE IF NOT EXISTS embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT,
                    chunk_index INTEGER,
                    text_chunk TEXT,
                    embedding_vector BLOB,
                    embedding_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (document_id) REFERENCES documents (id)
                )
            `);
            
            this.addResult('Database initialization', true, 'Database tables created successfully');
            
            // Test document insertion
            await this.runQuery(db, `
                INSERT OR REPLACE INTO documents (id, filename, original_name, file_path, file_size, mime_type, upload_date, text_content, embedding_count, processing_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            `, ['test-doc-1', 'test.txt', 'test.txt', '/tmp/test.txt', 1024, 'text/plain', new Date().toISOString(), 'Test content', 0, 'pending']);
            
            this.addResult('Document insertion', true, 'Document inserted successfully');
            
            // Test document retrieval
            const docs = await this.runQuery(db, 'SELECT * FROM documents WHERE id = ?', ['test-doc-1']);
            if (docs.length > 0) {
                this.addResult('Document retrieval', true, 'Document retrieved successfully');
            } else {
                this.addResult('Document retrieval', false, 'Document not found');
            }
            
            db.close();
            
        } catch (error) {
            this.addResult('Database operations', false, error.message);
        }
    }
    
    async testPythonBackend() {
        console.log('\n🐍 Testing Python Backend...');
        
        try {
            const { spawn } = require('child_process');
            const pythonScript = path.join(__dirname, 'python', 'generate_embeddings.py');
            const testText = 'This is a test text for embedding generation.';
            
            const result = await this.runPythonScript(pythonScript, [testText, 'test-embedding-1', this.vectorStorePath]);
            
            if (result && result.embedding_count > 0) {
                this.addResult('Embedding generation', true, `Generated ${result.embedding_count} embeddings`);
            } else {
                this.addResult('Embedding generation', false, 'No embeddings generated');
            }
            
        } catch (error) {
            this.addResult('Python backend', false, error.message);
        }
    }
    
    async testFileOperations() {
        console.log('\n📄 Testing File Operations...');
        
        try {
            const { spawn } = require('child_process');
            const pythonScript = path.join(__dirname, 'python', 'extract_text.py');
            
            // Create test file
            const testFile = path.join(this.vectorStorePath, 'test.txt');
            fs.writeFileSync(testFile, 'This is a test text file with some content for processing.');
            
            const result = await this.runPythonScript(pythonScript, [testFile, 'text/plain', this.vectorStorePath]);
            
            if (result && result.text) {
                this.addResult('Text extraction', true, `Extracted ${result.text_length} characters`);
            } else {
                this.addResult('Text extraction', false, 'No text extracted');
            }
            
        } catch (error) {
            this.addResult('File operations', false, error.message);
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
            const pythonProcess = spawn('python3', [scriptPath, ...args]);
            
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
        
        console.log('\n🎉 Simple Vector Store Tests completed!');
    }
}

// Run the test
if (require.main === module) {
    const test = new SimpleTest();
    test.run().catch(console.error);
}

module.exports = SimpleTest; 