#!/usr/bin/env bash

# Vector Store Manager Installation Script
# Optimized for 16GB RAM and 2.5GHz octa-core systems

set -e
set -x

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    print_error "This script must be run from the vector-store-app directory"
    exit 1
fi

print_status "Starting Vector Store Manager installation..."

# Check system requirements
print_status "Checking system requirements..."

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1 | sed 's/^0*//')
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2 | sed 's/^0*//')
echo "DEBUG: PYTHON_VERSION=$PYTHON_VERSION, PYTHON_MAJOR=$PYTHON_MAJOR, PYTHON_MINOR=$PYTHON_MINOR"

if (( PYTHON_MAJOR > 3 )) || { (( PYTHON_MAJOR == 3 )) && (( PYTHON_MINOR >= 8 )); }; then
    print_success "Python $PYTHON_VERSION detected"
else
    print_error "Python 3.8 or higher is required. Found: $PYTHON_VERSION"
    exit 1
fi

# Check available memory
TOTAL_MEM=$(free -m | awk 'NR==2{printf "%.0f", $2/1024}')
if [ "$TOTAL_MEM" -ge 12 ]; then
    print_success "System memory: ${TOTAL_MEM}GB (sufficient for 16GB target)"
else
    print_warning "System memory: ${TOTAL_MEM}GB (less than recommended 16GB)"
fi

# Check CPU cores
CPU_CORES=$(nproc)
if [ "$CPU_CORES" -ge 4 ]; then
    print_success "CPU cores: $CPU_CORES (sufficient for octa-core target)"
else
    print_warning "CPU cores: $CPU_CORES (less than recommended 8 cores)"
fi

# Create virtual environment
print_status "Setting up Python virtual environment..."

if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
print_status "Installing Python dependencies..."
if [ -f "python/requirements.txt" ]; then
    cd python
    pip install -r requirements.txt
    cd ..
    print_success "Python dependencies installed"
else
    print_error "Python requirements.txt not found"
    exit 1
fi

# Install Node.js dependencies
print_status "Installing Node.js dependencies..."
npm install
print_success "Node.js dependencies installed"

# Create necessary directories
print_status "Creating application directories..."
mkdir -p data/documents
mkdir -p data/vector-store
mkdir -p logs
print_success "Directories created"

# Set up environment variables
print_status "Setting up environment configuration..."
cat > .env << EOF
# Vector Store Manager Environment Configuration
NODE_ENV=development
PORT=3001
VECTOR_STORE_PATH=./data/vector-store
DOCUMENTS_PATH=./data/documents
LOG_LEVEL=info
MAX_FILE_SIZE=104857600
MAX_FILES=50
BATCH_SIZE=32
MODEL_NAME=all-MiniLM-L6-v2
EOF
print_success "Environment configuration created"

# Create startup script
print_status "Creating startup script..."
cat > start.sh << 'EOF'
#!/bin/bash

# Vector Store Manager Startup Script

# Activate virtual environment
source venv/bin/activate

# Set environment variables
export NODE_ENV=production
export PORT=3001

# Start the application
npm start
EOF

chmod +x start.sh
print_success "Startup script created"

# Create development startup script
print_status "Creating development startup script..."
cat > start-dev.sh << 'EOF'
#!/bin/bash

# Vector Store Manager Development Startup Script

# Activate virtual environment
source venv/bin/activate

# Set environment variables
export NODE_ENV=development
export PORT=3001

# Start the application in development mode
npm run dev
EOF

chmod +x start-dev.sh
print_success "Development startup script created"

# Create systemd service file (optional)
if command -v systemctl &> /dev/null; then
    print_status "Creating systemd service file..."
    sudo tee /etc/systemd/system/vector-store-manager.service > /dev/null << EOF
[Unit]
Description=Vector Store Manager
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/start.sh
Restart=always
RestartSec=10
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
EOF
    print_success "Systemd service file created"
    print_status "To enable the service, run: sudo systemctl enable vector-store-manager"
fi

# Create desktop shortcut (Linux)
if [ "$(uname)" == "Linux" ] && command -v xdg-desktop-menu &> /dev/null; then
    print_status "Creating desktop shortcut..."
    cat > vector-store-manager.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Vector Store Manager
Comment=AI-powered document vector store management
Exec=$(pwd)/start.sh
Icon=$(pwd)/assets/icon.png
Terminal=false
Categories=Office;Documentation;
EOF
    
    if [ -d "$HOME/Desktop" ]; then
        cp vector-store-manager.desktop "$HOME/Desktop/"
        chmod +x "$HOME/Desktop/vector-store-manager.desktop"
        print_success "Desktop shortcut created"
    fi
fi

# Create macOS app bundle (if on macOS)
if [ "$(uname)" == "Darwin" ]; then
    print_status "Creating macOS app bundle..."
    
    # Create app bundle structure
    mkdir -p "Vector Store Manager.app/Contents/MacOS"
    mkdir -p "Vector Store Manager.app/Contents/Resources"
    
    # Create Info.plist
    cat > "Vector Store Manager.app/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>Vector Store Manager</string>
    <key>CFBundleIdentifier</key>
    <string>com.mcli.vectorstore</string>
    <key>CFBundleName</key>
    <string>Vector Store Manager</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.14</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF
    
    # Create launcher script
    cat > "Vector Store Manager.app/Contents/MacOS/Vector Store Manager" << EOF
#!/bin/bash
cd "$(dirname "$0")/../../../"
source venv/bin/activate
export NODE_ENV=production
npm start
EOF
    
    chmod +x "Vector Store Manager.app/Contents/MacOS/Vector Store Manager"
    print_success "macOS app bundle created"
fi

# Create Windows batch file (if on Windows or for cross-platform)
print_status "Creating Windows batch file..."
cat > start.bat << 'EOF'
@echo off
REM Vector Store Manager Windows Startup Script

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Set environment variables
set NODE_ENV=production
set PORT=3001

REM Start the application
npm start
pause
EOF
print_success "Windows batch file created"

# Create README
print_status "Creating README..."
cat > README.md << 'EOF'
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
EOF
print_success "README created"

# Final setup
print_status "Performing final setup..."

# Set proper permissions
chmod +x *.sh
chmod +x *.bat

# Create log directory
mkdir -p logs

# Test Python environment
print_status "Testing Python environment..."
python3 -c "import torch, transformers, sentence_transformers; print('Python dependencies OK')" || {
    print_error "Python dependencies test failed"
    exit 1
}

print_success "Vector Store Manager installation completed successfully!"

echo ""
echo "=========================================="
echo "  Vector Store Manager Installation Complete"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Start the application: ./start.sh"
echo "2. Open your browser to: http://localhost:3001"
echo "3. Upload documents and start exploring!"
echo ""
echo "For development: ./start-dev.sh"
echo "For Windows: start.bat"
echo ""
echo "Documentation: README.md"
echo ""

# Optional: Start the application
read -p "Would you like to start the application now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Starting Vector Store Manager..."
    ./start.sh
fi 