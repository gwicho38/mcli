// Vector Store Manager - Renderer Process
// Handles frontend interactions, API calls, and vector visualization

class VectorStoreApp {
    constructor() {
        this.apiBaseUrl = 'http://localhost:3001/api';
        this.wsUrl = 'ws://localhost:3001';
        this.ws = null;
        this.documents = [];
        this.currentSearchResults = [];
        this.vectorScene = null;
        this.vectorRenderer = null;
        this.vectorCamera = null;
        this.vectorControls = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.connectWebSocket();
        this.loadDocuments();
        this.updateStatusBar();
        this.setupVectorVisualization();
    }
    
    setupEventListeners() {
        // Header buttons
        document.getElementById('uploadBtn').addEventListener('click', () => this.showUploadModal());
        document.getElementById('visualizeBtn').addEventListener('click', () => this.toggleVisualization());
        
        // Search functionality
        document.getElementById('searchInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.performSearch();
            }
        });
        document.getElementById('searchBtn').addEventListener('click', () => this.performSearch());
        
        // Document panel
        document.getElementById('refreshDocs').addEventListener('click', () => this.loadDocuments());
        document.getElementById('clearChat').addEventListener('click', () => this.clearChat());
        
        // Upload modal
        document.getElementById('fileInput').addEventListener('change', (e) => this.handleFileSelection(e));
        document.getElementById('confirmUpload').addEventListener('click', () => this.uploadFiles());
        document.getElementById('cancelUpload').addEventListener('click', () => this.hideUploadModal());
        
        // Modal close buttons
        document.querySelectorAll('.close-modal').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                if (modal) {
                    modal.classList.remove('show');
                }
            });
        });
        
        // Drag and drop
        this.setupDragAndDrop();
        
        // Visualization controls
        document.getElementById('closeViz').addEventListener('click', () => this.toggleVisualization());
        document.getElementById('clusteringMethod').addEventListener('change', () => this.updateVisualization());
        document.getElementById('dimensionReduction').addEventListener('change', () => this.updateVisualization());
        document.getElementById('colorBy').addEventListener('change', () => this.updateVisualization());
    }
    
    connectWebSocket() {
        try {
            this.ws = new WebSocket(this.wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
            };
            
            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                // Reconnect after 5 seconds
                setTimeout(() => this.connectWebSocket(), 5000);
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
            
        } catch (error) {
            console.error('Failed to connect WebSocket:', error);
        }
    }
    
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'document_processed':
                this.showNotification(`Document "${data.filename}" processed successfully`, 'success');
                this.loadDocuments(); // Refresh document list
                break;
            case 'processing_error':
                this.showNotification(`Error processing document: ${data.error}`, 'error');
                break;
        }
    }
    
    async loadDocuments() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/documents`);
            const data = await response.json();
            
            if (data.success) {
                this.documents = data.documents;
                this.renderDocumentsList();
                this.updateDocumentCount();
            } else {
                console.error('Failed to load documents:', data.error);
            }
        } catch (error) {
            console.error('Error loading documents:', error);
        }
    }
    
    renderDocumentsList() {
        const container = document.getElementById('documentsList');
        
        if (this.documents.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-folder-open"></i>
                    <p>No documents uploaded yet</p>
                    <button class="btn btn-primary" onclick="app.showUploadModal()">
                        Upload Documents
                    </button>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.documents.map(doc => `
            <div class="document-item" data-id="${doc.id}">
                <div class="document-icon">
                    <i class="fas ${this.getFileIcon(doc.mime_type)}"></i>
                </div>
                <div class="document-info">
                    <div class="document-name">${doc.original_name}</div>
                    <div class="document-meta">
                        ${this.formatFileSize(doc.file_size)} • 
                        ${doc.embedding_count} embeddings • 
                        ${this.formatDate(doc.upload_date)}
                    </div>
                </div>
                <div class="document-actions">
                    <button class="btn-icon" onclick="app.viewDocument('${doc.id}')" title="View Document">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn-icon" onclick="app.deleteDocument('${doc.id}')" title="Delete Document">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');
    }
    
    getFileIcon(mimeType) {
        const iconMap = {
            'application/pdf': 'fa-file-pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'fa-file-word',
            'text/plain': 'fa-file-alt',
            'text/markdown': 'fa-file-code',
            'text/csv': 'fa-file-csv',
            'application/json': 'fa-file-code',
            'application/xml': 'fa-file-code',
            'text/html': 'fa-file-code'
        };
        return iconMap[mimeType] || 'fa-file';
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }
    
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString();
    }
    
    async performSearch() {
        const query = document.getElementById('searchInput').value.trim();
        if (!query) return;
        
        const semanticSearch = document.getElementById('semanticSearch').checked;
        const exactMatch = document.getElementById('exactMatch').checked;
        
        try {
            // Show loading state
            this.showSearchLoading();
            
            const response = await fetch(`${this.apiBaseUrl}/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query,
                    semantic: semanticSearch,
                    exact: exactMatch,
                    limit: 20
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.currentSearchResults = data.results;
                this.renderSearchResults(data.results, query);
            } else {
                this.showSearchError(data.error);
            }
        } catch (error) {
            console.error('Search error:', error);
            this.showSearchError('Failed to perform search');
        }
    }
    
    renderSearchResults(results, query) {
        const container = document.getElementById('chatContainer');
        
        if (results.length === 0) {
            container.innerHTML = `
                <div class="search-results">
                    <div class="no-results">
                        <i class="fas fa-search"></i>
                        <h3>No results found</h3>
                        <p>Try different keywords or check your search options.</p>
                    </div>
                </div>
            `;
            return;
        }
        
        const resultsHtml = results.map(result => `
            <div class="search-result" data-document-id="${result.document_id}">
                <div class="result-header">
                    <div class="result-document">
                        <i class="fas ${this.getFileIcon(result.mime_type)}"></i>
                        <span>${result.document_name}</span>
                    </div>
                    <div class="result-score">
                        <span class="score-badge">${(result.similarity_score * 100).toFixed(1)}%</span>
                    </div>
                </div>
                <div class="result-content">
                    <p>${this.highlightQuery(result.text_chunk, query)}</p>
                </div>
                <div class="result-actions">
                    <button class="btn btn-sm btn-secondary" onclick="app.viewDocument('${result.document_id}')">
                        View Document
                    </button>
                    <button class="btn btn-sm btn-primary" onclick="app.viewEmbeddings('${result.document_id}')">
                        View Embeddings
                    </button>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = `
            <div class="search-results">
                <div class="search-header">
                    <h3>Search Results for "${query}"</h3>
                    <span>${results.length} results found</span>
                </div>
                ${resultsHtml}
            </div>
        `;
    }
    
    highlightQuery(text, query) {
        const regex = new RegExp(`(${query})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }
    
    showSearchLoading() {
        const container = document.getElementById('chatContainer');
        container.innerHTML = `
            <div class="search-loading">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Searching documents...</p>
            </div>
        `;
    }
    
    showSearchError(error) {
        const container = document.getElementById('chatContainer');
        container.innerHTML = `
            <div class="search-error">
                <i class="fas fa-exclamation-triangle"></i>
                <h3>Search Error</h3>
                <p>${error}</p>
            </div>
        `;
    }
    
    showUploadModal() {
        document.getElementById('uploadModal').classList.add('show');
    }
    
    hideUploadModal() {
        document.getElementById('uploadModal').classList.remove('show');
        this.resetUploadForm();
    }
    
    setupDragAndDrop() {
        const uploadArea = document.getElementById('uploadArea');
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = Array.from(e.dataTransfer.files);
            this.handleFiles(files);
        });
        
        uploadArea.addEventListener('click', () => {
            document.getElementById('fileInput').click();
        });
    }
    
    handleFileSelection(event) {
        const files = Array.from(event.target.files);
        this.handleFiles(files);
    }
    
    handleFiles(files) {
        const uploadedFilesContainer = document.getElementById('uploadedFiles');
        const confirmBtn = document.getElementById('confirmUpload');
        
        if (files.length === 0) return;
        
        const filesHtml = files.map(file => `
            <div class="uploaded-file">
                <div class="file-info">
                    <i class="fas ${this.getFileIcon(file.type)}"></i>
                    <span>${file.name}</span>
                    <span class="file-size">${this.formatFileSize(file.size)}</span>
                </div>
            </div>
        `).join('');
        
        uploadedFilesContainer.innerHTML = filesHtml;
        confirmBtn.disabled = false;
        
        // Store files for upload
        this.selectedFiles = files;
    }
    
    async uploadFiles() {
        if (!this.selectedFiles || this.selectedFiles.length === 0) return;
        
        const formData = new FormData();
        this.selectedFiles.forEach(file => {
            formData.append('files', file);
        });
        
        try {
            // Show progress
            this.showUploadProgress();
            
            const response = await fetch(`${this.apiBaseUrl}/upload`, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification(`${data.files.length} files uploaded successfully`, 'success');
                this.hideUploadModal();
                this.loadDocuments();
            } else {
                this.showNotification(`Upload failed: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Upload error:', error);
            this.showNotification('Upload failed', 'error');
        }
    }
    
    showUploadProgress() {
        document.getElementById('uploadProgress').style.display = 'block';
        document.getElementById('progressText').textContent = 'Uploading files...';
        
        // Simulate progress (in real app, this would be from actual upload progress)
        let progress = 0;
        const interval = setInterval(() => {
            progress += 10;
            document.getElementById('progressFill').style.width = `${progress}%`;
            
            if (progress >= 100) {
                clearInterval(interval);
                document.getElementById('progressText').textContent = 'Processing files...';
            }
        }, 200);
    }
    
    resetUploadForm() {
        document.getElementById('uploadedFiles').innerHTML = '';
        document.getElementById('confirmUpload').disabled = true;
        document.getElementById('uploadProgress').style.display = 'none';
        document.getElementById('progressFill').style.width = '0%';
        this.selectedFiles = null;
    }
    
    async viewDocument(documentId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/document/${documentId}`);
            const data = await response.json();
            
            if (data.success) {
                this.showDocumentModal(data.document);
            } else {
                this.showNotification('Failed to load document', 'error');
            }
        } catch (error) {
            console.error('Error loading document:', error);
            this.showNotification('Failed to load document', 'error');
        }
    }
    
    showDocumentModal(document) {
        const modal = document.getElementById('documentModal');
        const infoContainer = document.getElementById('documentInfo');
        const contentContainer = document.getElementById('documentContent');
        
        infoContainer.innerHTML = `
            <div class="document-details">
                <h4>${document.original_name}</h4>
                <div class="document-stats">
                    <span><i class="fas fa-file"></i> ${this.formatFileSize(document.file_size)}</span>
                    <span><i class="fas fa-brain"></i> ${document.embedding_count} embeddings</span>
                    <span><i class="fas fa-calendar"></i> ${this.formatDate(document.upload_date)}</span>
                </div>
            </div>
        `;
        
        contentContainer.innerHTML = `
            <div class="document-text">
                <h5>Document Content</h5>
                <pre>${document.text_content || 'No content available'}</pre>
            </div>
        `;
        
        modal.classList.add('show');
    }
    
    async deleteDocument(documentId) {
        if (!confirm('Are you sure you want to delete this document?')) return;
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/document/${documentId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Document deleted successfully', 'success');
                this.loadDocuments();
            } else {
                this.showNotification('Failed to delete document', 'error');
            }
        } catch (error) {
            console.error('Error deleting document:', error);
            this.showNotification('Failed to delete document', 'error');
        }
    }
    
    toggleVisualization() {
        const panel = document.getElementById('visualizationPanel');
        const isVisible = !panel.classList.contains('hidden');
        
        if (isVisible) {
            panel.classList.add('hidden');
        } else {
            panel.classList.remove('hidden');
            this.loadVectorVisualization();
        }
    }
    
    setupVectorVisualization() {
        const canvas = document.getElementById('vectorCanvas');
        
        // Initialize Three.js scene
        this.vectorScene = new THREE.Scene();
        this.vectorScene.background = new THREE.Color(0x1a1a1a);
        
        // Camera
        this.vectorCamera = new THREE.PerspectiveCamera(
            75, 
            canvas.clientWidth / canvas.clientHeight, 
            0.1, 
            1000
        );
        this.vectorCamera.position.z = 5;
        
        // Renderer
        this.vectorRenderer = new THREE.WebGLRenderer({ 
            canvas: canvas, 
            antialias: true 
        });
        this.vectorRenderer.setSize(canvas.clientWidth, canvas.clientHeight);
        
        // Controls
        this.vectorControls = new THREE.OrbitControls(this.vectorCamera, this.vectorRenderer.domElement);
        this.vectorControls.enableDamping = true;
        this.vectorControls.dampingFactor = 0.05;
        
        // Lighting
        const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
        this.vectorScene.add(ambientLight);
        
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(1, 1, 1);
        this.vectorScene.add(directionalLight);
        
        // Animation loop
        this.animate();
    }
    
    animate() {
        requestAnimationFrame(() => this.animate());
        
        if (this.vectorControls) {
            this.vectorControls.update();
        }
        
        if (this.vectorRenderer && this.vectorScene && this.vectorCamera) {
            this.vectorRenderer.render(this.vectorScene, this.vectorCamera);
        }
    }
    
    async loadVectorVisualization() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/vector-visualization`);
            const data = await response.json();
            
            if (data.success) {
                this.renderVectorVisualization(data.visualization);
            } else {
                console.error('Failed to load vector visualization:', data.error);
            }
        } catch (error) {
            console.error('Error loading vector visualization:', error);
        }
    }
    
    renderVectorVisualization(visualization) {
        // Clear existing visualization
        while (this.vectorScene.children.length > 0) {
            this.vectorScene.remove(this.vectorScene.children[0]);
        }
        
        // Add lighting back
        const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
        this.vectorScene.add(ambientLight);
        
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(1, 1, 1);
        this.vectorScene.add(directionalLight);
        
        // Render vector points
        if (visualization.points && visualization.points.length > 0) {
            const geometry = new THREE.BufferGeometry();
            const positions = new Float32Array(visualization.points.length * 3);
            const colors = new Float32Array(visualization.points.length * 3);
            
            visualization.points.forEach((point, index) => {
                positions[index * 3] = point.x;
                positions[index * 3 + 1] = point.y;
                positions[index * 3 + 2] = point.z;
                
                colors[index * 3] = point.color.r;
                colors[index * 3 + 1] = point.color.g;
                colors[index * 3 + 2] = point.color.b;
            });
            
            geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
            geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
            
            const material = new THREE.PointsMaterial({
                size: 0.05,
                vertexColors: true,
                transparent: true,
                opacity: 0.8
            });
            
            const points = new THREE.Points(geometry, material);
            this.vectorScene.add(points);
        }
        
        // Render connections between similar documents
        if (visualization.connections && visualization.connections.length > 0) {
            visualization.connections.forEach(connection => {
                const geometry = new THREE.BufferGeometry().setFromPoints([
                    new THREE.Vector3(connection.from.x, connection.from.y, connection.from.z),
                    new THREE.Vector3(connection.to.x, connection.to.y, connection.to.z)
                ]);
                
                const material = new THREE.LineBasicMaterial({
                    color: 0x666666,
                    transparent: true,
                    opacity: 0.3
                });
                
                const line = new THREE.Line(geometry, material);
                this.vectorScene.add(line);
            });
        }
    }
    
    updateVisualization() {
        // This would update the visualization based on control changes
        this.loadVectorVisualization();
    }
    
    clearChat() {
        const container = document.getElementById('chatContainer');
        container.innerHTML = `
            <div class="welcome-message">
                <div class="welcome-icon">
                    <i class="fas fa-brain"></i>
                </div>
                <h2>Welcome to Vector Store Manager</h2>
                <p>Upload documents to build your knowledge base, then search and explore your content with AI-powered semantic search.</p>
                <div class="welcome-features">
                    <div class="feature">
                        <i class="fas fa-upload"></i>
                        <span>Upload multiple file types</span>
                    </div>
                    <div class="feature">
                        <i class="fas fa-search"></i>
                        <span>Semantic search across documents</span>
                    </div>
                    <div class="feature">
                        <i class="fas fa-chart-network"></i>
                        <span>Visualize document relationships</span>
                    </div>
                </div>
            </div>
        `;
    }
    
    updateStatusBar() {
        // Update document count
        document.getElementById('documentCount').textContent = `${this.documents.length} documents`;
        
        // Update memory usage
        if (navigator.memory) {
            const memoryMB = Math.round(navigator.memory.usedJSHeapSize / 1024 / 1024);
            document.getElementById('memoryUsage').textContent = `Memory: ${memoryMB}MB`;
        }
        
        // Update last update time
        document.getElementById('lastUpdate').textContent = `Last update: ${new Date().toLocaleTimeString()}`;
    }
    
    updateDocumentCount() {
        document.getElementById('documentCount').textContent = `${this.documents.length} documents`;
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            <span>${message}</span>
        `;
        
        // Add to page
        document.body.appendChild(notification);
        
        // Show notification
        setTimeout(() => notification.classList.add('show'), 100);
        
        // Remove after 5 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new VectorStoreApp();
});

// Add notification styles
const notificationStyles = `
    .notification {
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        z-index: 10000;
        transform: translateX(100%);
        transition: transform 0.3s ease;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .notification.show {
        transform: translateX(0);
    }
    
    .notification-success {
        background-color: #10b981;
    }
    
    .notification-error {
        background-color: #ef4444;
    }
    
    .notification-info {
        background-color: #3b82f6;
    }
    
    .search-results {
        max-width: 800px;
        margin: 0 auto;
    }
    
    .search-header {
        margin-bottom: 20px;
        padding-bottom: 10px;
        border-bottom: 1px solid var(--border-color);
    }
    
    .search-result {
        background: var(--bg-elevated);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-lg);
        padding: var(--spacing-lg);
        margin-bottom: var(--spacing-md);
        transition: all var(--transition-fast);
    }
    
    .search-result:hover {
        border-color: var(--border-hover);
        box-shadow: var(--shadow-md);
    }
    
    .result-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: var(--spacing-md);
    }
    
    .result-document {
        display: flex;
        align-items: center;
        gap: var(--spacing-sm);
        font-weight: 500;
        color: var(--text-primary);
    }
    
    .score-badge {
        background: var(--primary-color);
        color: var(--text-inverse);
        padding: 4px 8px;
        border-radius: var(--radius-sm);
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    .result-content {
        margin-bottom: var(--spacing-md);
        line-height: 1.6;
    }
    
    .result-content mark {
        background: var(--accent-color);
        color: var(--text-inverse);
        padding: 2px 4px;
        border-radius: 2px;
    }
    
    .result-actions {
        display: flex;
        gap: var(--spacing-sm);
    }
    
    .btn-sm {
        padding: var(--spacing-xs) var(--spacing-md);
        font-size: 0.75rem;
    }
    
    .empty-state {
        text-align: center;
        padding: var(--spacing-2xl);
        color: var(--text-muted);
    }
    
    .empty-state i {
        font-size: 3rem;
        margin-bottom: var(--spacing-md);
    }
    
    .document-actions {
        display: flex;
        gap: var(--spacing-xs);
    }
    
    .document-details {
        margin-bottom: var(--spacing-lg);
    }
    
    .document-stats {
        display: flex;
        gap: var(--spacing-lg);
        margin-top: var(--spacing-sm);
        font-size: 0.875rem;
        color: var(--text-secondary);
    }
    
    .document-text pre {
        background: var(--bg-secondary);
        padding: var(--spacing-md);
        border-radius: var(--radius-md);
        overflow-x: auto;
        white-space: pre-wrap;
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        font-size: 0.875rem;
        line-height: 1.5;
    }
`;

// Add styles to document
const styleSheet = document.createElement('style');
styleSheet.textContent = notificationStyles;
document.head.appendChild(styleSheet); 