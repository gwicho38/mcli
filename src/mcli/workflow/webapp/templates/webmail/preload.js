// Preload script for secure IPC communication
const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
    // File selection
    selectFiles: () => ipcRenderer.invoke('select-files'),
    
    // App information
    getAppVersion: () => ipcRenderer.invoke('get-app-version'),
    
    // System information
    getSystemInfo: () => ({
        platform: process.platform,
        arch: process.arch,
        version: process.version
    }),
    
    // Memory usage
    getMemoryUsage: () => {
        if (process.memoryUsage) {
            const usage = process.memoryUsage();
            return {
                rss: Math.round(usage.rss / 1024 / 1024), // MB
                heapUsed: Math.round(usage.heapUsed / 1024 / 1024), // MB
                heapTotal: Math.round(usage.heapTotal / 1024 / 1024), // MB
                external: Math.round(usage.external / 1024 / 1024) // MB
            };
        }
        return null;
    },
    
    // Performance monitoring
    getPerformanceMetrics: () => {
        const metrics = {};
        
        if (performance && performance.memory) {
            metrics.memory = {
                usedJSHeapSize: Math.round(performance.memory.usedJSHeapSize / 1024 / 1024),
                totalJSHeapSize: Math.round(performance.memory.totalJSHeapSize / 1024 / 1024),
                jsHeapSizeLimit: Math.round(performance.memory.jsHeapSizeLimit / 1024 / 1024)
            };
        }
        
        return metrics;
    }
});

// Handle window resize for vector visualization
window.addEventListener('resize', () => {
    // Notify main process of window resize
    ipcRenderer.send('window-resized');
});

// Handle beforeunload to clean up resources
window.addEventListener('beforeunload', () => {
    // Clean up any resources
    ipcRenderer.send('cleanup-resources');
}); 