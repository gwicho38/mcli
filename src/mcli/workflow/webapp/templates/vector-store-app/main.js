const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const express = require('express');
const cors = require('cors');
const multer = require('multer');
const fs = require('fs-extra');
const { v4: uuidv4 } = require('uuid');
const { PythonShell } = require('python-shell');
const WebSocket = require('ws');
const net = require('net');

// Global variables
let mainWindow;
let server;
let wss;
let vectorStorePath;
let documentsPath;

// Port management utilities
function isPortAvailable(port) {
  return new Promise((resolve) => {
    const tester = net.createServer()
      .once('error', () => resolve(false))
      .once('listening', () => {
        tester.once('close', () => resolve(true))
          .close();
      })
      .listen(port);
  });
}

async function findAvailablePort(startPort = 3001) {
  let port = startPort;
  while (!(await isPortAvailable(port))) {
    port++;
    if (port > startPort + 100) { // Prevent infinite loop
      throw new Error('No available ports found');
    }
  }
  return port;
}

function cleanupPort(port) {
  return new Promise((resolve) => {
    const tester = net.createServer()
      .once('error', () => resolve()) // Port is already free
      .once('listening', () => {
        tester.close(() => resolve());
      })
      .listen(port);
  });
}

// Express app setup
const expressApp = express();
expressApp.use(cors());
expressApp.use(express.json({ limit: '50mb' }));
expressApp.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Multer configuration for file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, documentsPath);
  },
  filename: (req, file, cb) => {
    const uniqueName = `${Date.now()}-${uuidv4()}-${file.originalname}`;
    cb(null, uniqueName);
  }
});

const upload = multer({ 
  storage: storage,
  limits: {
    fileSize: 100 * 1024 * 1024, // 100MB limit
    files: 50 // Allow up to 50 files at once
  }
});

// Initialize paths
function initializePaths() {
  const userDataPath = app.getPath('userData');
  vectorStorePath = path.join(userDataPath, 'vector-store');
  documentsPath = path.join(userDataPath, 'documents');
  
  // Ensure directories exist
  fs.ensureDirSync(vectorStorePath);
  fs.ensureDirSync(documentsPath);
}

// API Routes
expressApp.post('/api/upload', upload.array('files', 50), async (req, res) => {
  try {
    const uploadedFiles = req.files.map(file => ({
      id: uuidv4(),
      originalName: file.originalname,
      filename: file.filename,
      path: file.path,
      size: file.size,
      mimetype: file.mimetype,
      uploadDate: new Date().toISOString()
    }));

    // Process files for vector embeddings
    const processingResults = await processFilesForEmbeddings(uploadedFiles);
    
    res.json({
      success: true,
      files: uploadedFiles,
      embeddings: processingResults
    });
  } catch (error) {
    console.error('Upload error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

expressApp.get('/api/documents', async (req, res) => {
  try {
    const documents = await getDocumentsList();
    res.json({ success: true, documents });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

expressApp.get('/api/document/:id', async (req, res) => {
  try {
    const document = await getDocumentById(req.params.id);
    res.json({ success: true, document });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

expressApp.get('/api/embeddings/:id', async (req, res) => {
  try {
    const embeddings = await getDocumentEmbeddings(req.params.id);
    res.json({ success: true, embeddings });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

expressApp.delete('/api/document/:id', async (req, res) => {
  try {
    await deleteDocument(req.params.id);
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

expressApp.get('/api/vector-visualization', async (req, res) => {
  try {
    const visualization = await generateVectorVisualization();
    res.json({ success: true, visualization });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

expressApp.post('/api/search', async (req, res) => {
  try {
    const { query, top_k = 10, exact_match = false } = req.body;
    
    if (!query) {
      return res.status(400).json({ success: false, error: 'Query is required' });
    }
    
    const results = await performSearch(query, top_k, exact_match);
    res.json({ success: true, results });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

expressApp.get('/api/stats', async (req, res) => {
  try {
    const dbPath = path.join(vectorStorePath, 'vector_store.db');
    const sqlite3 = require('sqlite3').verbose();
    
    const stats = await new Promise((resolve, reject) => {
      const db = new sqlite3.Database(dbPath);
      
      db.get(`
        SELECT 
          COUNT(*) as total_documents,
          SUM(embedding_count) as total_embeddings,
          SUM(file_size) as total_size,
          COUNT(CASE WHEN processing_status = 'completed' THEN 1 END) as completed_documents,
          COUNT(CASE WHEN processing_status = 'pending' THEN 1 END) as pending_documents,
          COUNT(CASE WHEN processing_status = 'failed' THEN 1 END) as failed_documents
        FROM documents
      `, [], (err, row) => {
        db.close();
        if (err) {
          reject(err);
        } else {
          resolve(row || {});
        }
      });
    });
    
    res.json({ success: true, stats });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Vector processing functions
async function processFilesForEmbeddings(files) {
  const results = [];
  
  for (const file of files) {
    try {
      // Notify processing start
      if (wss) {
        wss.clients.forEach(client => {
          if (client.readyState === WebSocket.OPEN) {
            client.send(JSON.stringify({
              type: 'processing_started',
              fileId: file.id,
              filename: file.originalName,
              status: 'processing'
            }));
          }
        });
      }
      
      // Extract text content based on file type
      const textContent = await extractTextFromFile(file.path, file.mimetype);
      
      // Notify text extraction complete
      if (wss) {
        wss.clients.forEach(client => {
          if (client.readyState === WebSocket.OPEN) {
            client.send(JSON.stringify({
              type: 'text_extracted',
              fileId: file.id,
              filename: file.originalName,
              textLength: textContent.length,
              status: 'text_extracted'
            }));
          }
        });
      }
      
      // Generate embeddings using Python backend
      const embeddings = await generateEmbeddings(textContent, file.id);
      
      // Notify embedding generation complete
      if (wss) {
        wss.clients.forEach(client => {
          if (client.readyState === WebSocket.OPEN) {
            client.send(JSON.stringify({
              type: 'embeddings_generated',
              fileId: file.id,
              filename: file.originalName,
              embeddingCount: embeddings.embedding_count || 0,
              status: 'embeddings_generated'
            }));
          }
        });
      }
      
      // Store document metadata and embeddings
      await storeDocumentMetadata(file, textContent, embeddings);
      
      results.push({
        fileId: file.id,
        success: true,
        embeddingCount: embeddings.length
      });
      
      // Notify frontend via WebSocket
      if (wss) {
        wss.clients.forEach(client => {
          if (client.readyState === WebSocket.OPEN) {
            client.send(JSON.stringify({
              type: 'document_processed',
              fileId: file.id,
              filename: file.originalName,
              embeddingCount: embeddings.embedding_count || 0,
              status: 'completed'
            }));
          }
        });
      }
    } catch (error) {
      console.error(`Error processing file ${file.originalName}:`, error);
      
      // Notify error via WebSocket
      if (wss) {
        wss.clients.forEach(client => {
          if (client.readyState === WebSocket.OPEN) {
            client.send(JSON.stringify({
              type: 'processing_error',
              fileId: file.id,
              filename: file.originalName,
              error: error.message,
              status: 'failed'
            }));
          }
        });
      }
      
      results.push({
        fileId: file.id,
        success: false,
        error: error.message
      });
    }
  }
  
  return results;
}

async function extractTextFromFile(filePath, mimetype) {
  try {
    const options = {
      mode: 'text',
      pythonPath: 'python3',
      pythonOptions: ['-u'],
      scriptPath: path.join(__dirname, 'python'),
      args: [filePath, mimetype, vectorStorePath]
    };

    return new Promise((resolve, reject) => {
      PythonShell.run('extract_text.py', options, (err, results) => {
        if (err) {
          console.error('Text extraction error:', err);
          resolve(""); // Return empty string on error
        } else {
          try {
            const result = JSON.parse(results[0]);
            resolve(result.text || "");
          } catch (parseError) {
            console.error('Text extraction parse error:', parseError);
            resolve("");
          }
        }
      });
    });
  } catch (error) {
    console.error('Error in extractTextFromFile:', error);
    return "";
  }
}

async function generateEmbeddings(text, fileId) {
  try {
    const options = {
      mode: 'text',
      pythonPath: 'python3',
      pythonOptions: ['-u'],
      scriptPath: path.join(__dirname, 'python'),
      args: [text, fileId, vectorStorePath]
    };

    return new Promise((resolve, reject) => {
      PythonShell.run('generate_embeddings.py', options, (err, results) => {
        if (err) {
          console.error('Embedding generation error:', err);
          reject(err);
        } else {
          try {
            const result = JSON.parse(results[0]);
            resolve(result);
          } catch (parseError) {
            console.error('Embedding generation parse error:', parseError);
            reject(parseError);
          }
        }
      });
    });
  } catch (error) {
    console.error('Error in generateEmbeddings:', error);
    throw error;
  }
}

async function storeDocumentMetadata(file, textContent, embeddings) {
  try {
    const dbPath = path.join(vectorStorePath, 'vector_store.db');
    const sqlite3 = require('sqlite3').verbose();
    
    return new Promise((resolve, reject) => {
      const db = new sqlite3.Database(dbPath);
      
      const documentData = {
        id: file.id,
        filename: file.filename,
        original_name: file.originalName,
        file_path: file.path,
        file_size: file.size,
        mime_type: file.mimetype,
        upload_date: file.uploadDate,
        text_content: textContent,
        embedding_count: embeddings.embedding_count || 0,
        processing_status: 'completed'
      };
      
      db.run(`
        INSERT OR REPLACE INTO documents 
        (id, filename, original_name, file_path, file_size, mime_type, 
         upload_date, text_content, embedding_count, processing_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `, [
        documentData.id, documentData.filename, documentData.original_name,
        documentData.file_path, documentData.file_size, documentData.mime_type,
        documentData.upload_date, documentData.text_content,
        documentData.embedding_count, documentData.processing_status
      ], function(err) {
        db.close();
        if (err) {
          reject(err);
        } else {
          resolve({
            success: true,
            document_id: documentData.id,
            embedding_count: documentData.embedding_count
          });
        }
      });
    });
  } catch (error) {
    console.error('Error storing document metadata:', error);
    throw error;
  }
}

async function getDocumentsList() {
  try {
    const dbPath = path.join(vectorStorePath, 'vector_store.db');
    const sqlite3 = require('sqlite3').verbose();
    
    return new Promise((resolve, reject) => {
      const db = new sqlite3.Database(dbPath);
      
      db.all(`
        SELECT id, filename, original_name, file_size, mime_type, 
               upload_date, embedding_count, processing_status, created_at
        FROM documents 
        ORDER BY created_at DESC
      `, [], (err, rows) => {
        db.close();
        if (err) {
          reject(err);
        } else {
          resolve(rows || []);
        }
      });
    });
  } catch (error) {
    console.error('Error getting documents list:', error);
    return [];
  }
}

async function getDocumentById(id) {
  try {
    const dbPath = path.join(vectorStorePath, 'vector_store.db');
    const sqlite3 = require('sqlite3').verbose();
    
    return new Promise((resolve, reject) => {
      const db = new sqlite3.Database(dbPath);
      
      db.get(`
        SELECT id, filename, original_name, file_path, file_size, 
               mime_type, upload_date, text_content, embedding_count, 
               processing_status, created_at
        FROM documents 
        WHERE id = ?
      `, [id], (err, row) => {
        db.close();
        if (err) {
          reject(err);
        } else {
          resolve(row || {});
        }
      });
    });
  } catch (error) {
    console.error('Error getting document by ID:', error);
    return {};
  }
}

async function getDocumentEmbeddings(id) {
  try {
    const dbPath = path.join(vectorStorePath, 'vector_store.db');
    const sqlite3 = require('sqlite3').verbose();
    
    return new Promise((resolve, reject) => {
      const db = new sqlite3.Database(dbPath);
      
      db.all(`
        SELECT id, document_id, chunk_index, text_chunk, 
               embedding_vector, embedding_hash, created_at
        FROM embeddings 
        WHERE document_id = ?
        ORDER BY chunk_index
      `, [id], (err, rows) => {
        db.close();
        if (err) {
          reject(err);
        } else {
          resolve(rows || []);
        }
      });
    });
  } catch (error) {
    console.error('Error getting document embeddings:', error);
    return [];
  }
}

async function deleteDocument(id) {
  try {
    const dbPath = path.join(vectorStorePath, 'vector_store.db');
    const sqlite3 = require('sqlite3').verbose();
    
    return new Promise((resolve, reject) => {
      const db = new sqlite3.Database(dbPath);
      
      // Get document info first
      db.get('SELECT file_path FROM documents WHERE id = ?', [id], (err, doc) => {
        if (err) {
          db.close();
          reject(err);
          return;
        }
        
        // Delete embeddings first (foreign key constraint)
        db.run('DELETE FROM embeddings WHERE document_id = ?', [id], function(err) {
          if (err) {
            db.close();
            reject(err);
            return;
          }
          
          // Delete document record
          db.run('DELETE FROM documents WHERE id = ?', [id], function(err) {
            db.close();
            if (err) {
              reject(err);
            } else {
              // Delete physical file if it exists
              if (doc && doc.file_path && fs.existsSync(doc.file_path)) {
                fs.unlinkSync(doc.file_path);
              }
              resolve({ success: true, deletedRows: this.changes });
            }
          });
        });
      });
    });
  } catch (error) {
    console.error('Error deleting document:', error);
    throw error;
  }
}

async function generateVectorVisualization() {
  try {
    const dbPath = path.join(vectorStorePath, 'vector_store.db');
    const sqlite3 = require('sqlite3').verbose();
    
    return new Promise((resolve, reject) => {
      const db = new sqlite3.Database(dbPath);
      
      // Get all embeddings for visualization
      db.all(`
        SELECT e.document_id, e.chunk_index, e.embedding_vector,
               d.original_name, d.mime_type
        FROM embeddings e
        JOIN documents d ON e.document_id = d.id
        ORDER BY e.id
      `, [], (err, rows) => {
        db.close();
        if (err) {
          reject(err);
        } else {
          // Convert binary embeddings to arrays
          const embeddings = rows.map(row => ({
            document_id: row.document_id,
            chunk_index: row.chunk_index,
            document_name: row.original_name,
            mime_type: row.mime_type,
            embedding: Array.from(new Float32Array(row.embedding_vector))
          }));
          
          // Generate visualization data
          const visualization = {
            points: embeddings.map((emb, index) => ({
              id: index,
              document_id: emb.document_id,
              document_name: emb.document_name,
              chunk_index: emb.chunk_index,
              mime_type: emb.mime_type,
              // Simple 2D projection (in real implementation, use PCA/t-SNE)
              x: Math.random() * 100,
              y: Math.random() * 100
            })),
            clusters: [],
            metadata: {
              total_embeddings: embeddings.length,
              total_documents: new Set(embeddings.map(e => e.document_id)).size,
              generated_at: new Date().toISOString()
            }
          };
          
          resolve(visualization);
        }
      });
    });
  } catch (error) {
    console.error('Error generating vector visualization:', error);
    return {
      points: [],
      clusters: [],
      metadata: { error: error.message }
    };
  }
}

async function performSearch(query, top_k = 10, exact_match = false) {
  try {
    // Call Python backend for search
    const options = {
      mode: 'text',
      pythonPath: 'python3',
      pythonOptions: ['-u'],
      scriptPath: path.join(__dirname, 'python'),
      args: [query, top_k.toString(), exact_match.toString(), vectorStorePath]
    };

    return new Promise((resolve, reject) => {
      PythonShell.run('search_embeddings.py', options, (err, results) => {
        if (err) reject(err);
        else resolve(JSON.parse(results[0]));
      });
    });
  } catch (error) {
    console.error('Search error:', error);
    return [];
  }
}

// Electron app lifecycle
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, 'assets', 'icon.png'),
    titleBarStyle: 'default',
    show: false
  });

  mainWindow.loadFile('index.html');
  
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// IPC handlers
ipcMain.handle('select-files', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile', 'multiSelections'],
    filters: [
      { name: 'Documents', extensions: ['pdf', 'docx', 'txt', 'md', 'csv', 'json', 'xml', 'html'] },
      { name: 'All Files', extensions: ['*'] }
    ]
  });
  return result.filePaths;
});

ipcMain.handle('get-app-version', () => {
  return app.getVersion();
});

// App event handlers
app.whenReady().then(async () => {
  initializePaths();
  
  try {
    // Find available port
    const startPort = parseInt(process.env.PORT) || 3001;
    const PORT = await findAvailablePort(startPort);
    
    // Start Express server
    server = expressApp.listen(PORT, () => {
      console.log(`Vector Store API server running on port ${PORT}`);
    });
    
    // Start WebSocket server
    wss = new WebSocket.Server({ server });
    
    wss.on('connection', (ws) => {
      console.log('Client connected to WebSocket');
      
      ws.on('close', () => {
        console.log('Client disconnected from WebSocket');
      });
    });
    
    createWindow();
  } catch (error) {
    console.error('Failed to start server:', error);
    app.quit();
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

app.on('before-quit', async () => {
  console.log('Cleaning up server connections...');
  
  if (wss) {
    wss.close();
  }
  
  if (server) {
    server.close();
  }
  
  // Additional cleanup for any remaining connections
  if (server && server.address()) {
    await cleanupPort(server.address().port);
  }
}); 