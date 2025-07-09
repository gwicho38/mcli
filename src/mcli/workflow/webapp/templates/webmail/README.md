# Vector Store Manager

A high-performance Electron application for dynamic vector store management with ChatGPT-like interface.

## Features

- **Document Processing**: Upload and process multiple file types (PDF, DOCX, TXT, MD, CSV, JSON, XML, HTML)
- **Vector Embeddings**: High-performance semantic embeddings using state-of-the-art models
- **Semantic Search**: AI-powered search across your document collection
- **Vector Visualization**: Interactive 3D visualization of document relationships
- **Memory Optimized**: Designed for 16GB RAM and 2.5GHz octa-core systems
- **Cross-Platform**: Works on Windows, macOS, and Linux

## System Requirements

- **RAM**: 16GB recommended (8GB minimum)
- **CPU**: 2.5GHz octa-core recommended (quad-core minimum)
- **Storage**: 2GB free space
- **Python**: 3.8 or higher
- **Node.js**: 16 or higher

## Quick Start

1. **Start the application**:
   ```bash
   ./start.sh          # Production mode
   ./start-dev.sh      # Development mode
   ```

2. **Upload documents** using the web interface

3. **Search and explore** your document collection

## Performance Optimization

The application is optimized for systems with:
- 16GB RAM for handling large document collections
- 2.5GHz octa-core CPU for fast embedding generation
- SSD storage for quick vector index operations

## File Structure

```
vector-store-app/
├── main.js              # Electron main process
├── index.html           # Main application interface
├── styles.css           # Application styling
├── renderer.js          # Frontend logic
├── preload.js           # Secure IPC communication
├── python/              # Python backend
│   ├── generate_embeddings.py
│   └── requirements.txt
├── data/                # Application data
│   ├── documents/       # Uploaded documents
│   └── vector-store/    # Vector database
└── venv/                # Python virtual environment
```

## Configuration

Edit `.env` file to customize:
- Port number
- File size limits
- Batch processing size
- Model selection

## Troubleshooting

1. **Memory issues**: Reduce batch size in `.env`
2. **Slow performance**: Check CPU usage and consider upgrading
3. **Import errors**: Ensure Python dependencies are installed

## Support

For issues and questions, please refer to the project documentation.
