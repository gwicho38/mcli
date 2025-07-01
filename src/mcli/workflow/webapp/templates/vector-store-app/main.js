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

// Vector processing functions
async function processFilesForEmbeddings(files) {
  const results = [];
  
  for (const file of files) {
    try {
      // Extract text content based on file type
      const textContent = await extractTextFromFile(file.path, file.mimetype);
      
      // Generate embeddings using Python backend
      const embeddings = await generateEmbeddings(textContent, file.id);
      
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
              filename: file.originalName
            }));
          }
        });
      }
    } catch (error) {
      console.error(`Error processing file ${file.originalName}:`, error);
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
  // Implementation for text extraction based on file type
  // This will be implemented with proper file type handlers
  return "Extracted text content";
}

async function generateEmbeddings(text, fileId) {
  return new Promise((resolve, reject) => {
    const options = {
      mode: 'text',
      pythonPath: 'python3',
      pythonOptions: ['-u'],
      scriptPath: path.join(__dirname, 'python'),
      args: [text, fileId, vectorStorePath]
    };

    PythonShell.run('generate_embeddings.py', options, (err, results) => {
      if (err) reject(err);
      else resolve(JSON.parse(results[0]));
    });
  });
}

async function storeDocumentMetadata(file, textContent, embeddings) {
  // Store in SQLite database
  const dbPath = path.join(vectorStorePath, 'documents.db');
  // Implementation for database storage
}

async function getDocumentsList() {
  // Retrieve documents from database
  return [];
}

async function getDocumentById(id) {
  // Retrieve specific document
  return {};
}

async function getDocumentEmbeddings(id) {
  // Retrieve embeddings for specific document
  return [];
}

async function deleteDocument(id) {
  // Delete document and its embeddings
}

async function generateVectorVisualization() {
  // Generate vector proximity visualization
  return {};
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