/**
 * Electron Integration Example for MCLI Model Service
 * 
 * This file demonstrates how to integrate the model service
 * with an Electron frontend application.
 */

const { ipcMain, ipcRenderer } = require('electron');

class ModelServiceClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }

    /**
     * Generate text using a loaded model
     */
    async generateText(modelId, prompt, options = {}) {
        try {
            const response = await fetch(`${this.baseUrl}/models/${modelId}/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    prompt,
                    max_length: options.maxLength,
                    temperature: options.temperature,
                    top_p: options.topP,
                    top_k: options.topK
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            return {
                success: true,
                generatedText: result.generated_text,
                executionTime: result.execution_time_ms
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Classify text using a loaded model
     */
    async classifyText(modelId, text) {
        try {
            const response = await fetch(`${this.baseUrl}/models/${modelId}/classify`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            return {
                success: true,
                classifications: result.classifications,
                executionTime: result.execution_time_ms
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Translate text using a loaded model
     */
    async translateText(modelId, text, sourceLang = 'en', targetLang = 'fr') {
        try {
            const response = await fetch(`${this.baseUrl}/models/${modelId}/translate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text,
                    source_lang: sourceLang,
                    target_lang: targetLang
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            return {
                success: true,
                translatedText: result.translated_text,
                executionTime: result.execution_time_ms
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * List all available models
     */
    async listModels() {
        try {
            const response = await fetch(`${this.baseUrl}/models`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const models = await response.json();
            return {
                success: true,
                models
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Get service status
     */
    async getStatus() {
        try {
            const response = await fetch(`${this.baseUrl}/health`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const status = await response.json();
            return {
                success: true,
                status
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Load a new model
     */
    async loadModel(modelConfig) {
        try {
            const response = await fetch(`${this.baseUrl}/models`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(modelConfig)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            return {
                success: true,
                modelId: result.model_id
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Unload a model
     */
    async unloadModel(modelId) {
        try {
            const response = await fetch(`${this.baseUrl}/models/${modelId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return {
                success: true
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }
}

// Main process (main.js) - Set up IPC handlers
function setupModelServiceHandlers() {
    const modelClient = new ModelServiceClient();

    // Handle text generation requests
    ipcMain.handle('model-service:generate-text', async (event, modelId, prompt, options) => {
        return await modelClient.generateText(modelId, prompt, options);
    });

    // Handle text classification requests
    ipcMain.handle('model-service:classify-text', async (event, modelId, text) => {
        return await modelClient.classifyText(modelId, text);
    });

    // Handle translation requests
    ipcMain.handle('model-service:translate-text', async (event, modelId, text, sourceLang, targetLang) => {
        return await modelClient.translateText(modelId, text, sourceLang, targetLang);
    });

    // Handle model listing
    ipcMain.handle('model-service:list-models', async () => {
        return await modelClient.listModels();
    });

    // Handle status requests
    ipcMain.handle('model-service:get-status', async () => {
        return await modelClient.getStatus();
    });

    // Handle model loading
    ipcMain.handle('model-service:load-model', async (event, modelConfig) => {
        return await modelClient.loadModel(modelConfig);
    });

    // Handle model unloading
    ipcMain.handle('model-service:unload-model', async (event, modelId) => {
        return await modelClient.unloadModel(modelId);
    });
}

// Renderer process (renderer.js) - API for renderer
class ModelServiceAPI {
    constructor() {
        this.isRenderer = typeof window !== 'undefined';
    }

    async generateText(modelId, prompt, options = {}) {
        if (this.isRenderer) {
            return await ipcRenderer.invoke('model-service:generate-text', modelId, prompt, options);
        } else {
            const client = new ModelServiceClient();
            return await client.generateText(modelId, prompt, options);
        }
    }

    async classifyText(modelId, text) {
        if (this.isRenderer) {
            return await ipcRenderer.invoke('model-service:classify-text', modelId, text);
        } else {
            const client = new ModelServiceClient();
            return await client.classifyText(modelId, text);
        }
    }

    async translateText(modelId, text, sourceLang = 'en', targetLang = 'fr') {
        if (this.isRenderer) {
            return await ipcRenderer.invoke('model-service:translate-text', modelId, text, sourceLang, targetLang);
        } else {
            const client = new ModelServiceClient();
            return await client.translateText(modelId, text, sourceLang, targetLang);
        }
    }

    async listModels() {
        if (this.isRenderer) {
            return await ipcRenderer.invoke('model-service:list-models');
        } else {
            const client = new ModelServiceClient();
            return await client.listModels();
        }
    }

    async getStatus() {
        if (this.isRenderer) {
            return await ipcRenderer.invoke('model-service:get-status');
        } else {
            const client = new ModelServiceClient();
            return await client.getStatus();
        }
    }

    async loadModel(modelConfig) {
        if (this.isRenderer) {
            return await ipcRenderer.invoke('model-service:load-model', modelConfig);
        } else {
            const client = new ModelServiceClient();
            return await client.loadModel(modelConfig);
        }
    }

    async unloadModel(modelId) {
        if (this.isRenderer) {
            return await ipcRenderer.invoke('model-service:unload-model', modelId);
        } else {
            const client = new ModelServiceClient();
            return await client.unloadModel(modelId);
        }
    }
}

// Example usage in renderer process
async function exampleUsage() {
    const modelAPI = new ModelServiceAPI();

    try {
        // Check service status
        const status = await modelAPI.getStatus();
        console.log('Service status:', status);

        // List available models
        const modelsResult = await modelAPI.listModels();
        if (modelsResult.success) {
            console.log('Available models:', modelsResult.models);
        }

        // Load a model (if you have one)
        const loadResult = await modelAPI.loadModel({
            name: "GPT-2 Test",
            model_type: "text-generation",
            model_path: "gpt2",
            temperature: 0.7,
            max_length: 50
        });

        if (loadResult.success) {
            const modelId = loadResult.modelId;
            console.log('Model loaded with ID:', modelId);

            // Generate text
            const generateResult = await modelAPI.generateText(
                modelId,
                "Hello, how are you?",
                { temperature: 0.8, maxLength: 30 }
            );

            if (generateResult.success) {
                console.log('Generated text:', generateResult.generatedText);
                console.log('Execution time:', generateResult.executionTime, 'ms');
            } else {
                console.error('Generation failed:', generateResult.error);
            }

            // Unload the model
            await modelAPI.unloadModel(modelId);
        }

    } catch (error) {
        console.error('Error:', error);
    }
}

// Example React component
function ModelServiceComponent() {
    const [models, setModels] = useState([]);
    const [loading, setLoading] = useState(false);
    const [generatedText, setGeneratedText] = useState('');
    const [prompt, setPrompt] = useState('');

    const modelAPI = new ModelServiceAPI();

    useEffect(() => {
        loadModels();
    }, []);

    const loadModels = async () => {
        setLoading(true);
        try {
            const result = await modelAPI.listModels();
            if (result.success) {
                setModels(result.models);
            }
        } catch (error) {
            console.error('Error loading models:', error);
        }
        setLoading(false);
    };

    const generateText = async (modelId) => {
        if (!prompt.trim()) return;

        setLoading(true);
        try {
            const result = await modelAPI.generateText(modelId, prompt);
            if (result.success) {
                setGeneratedText(result.generatedText);
            } else {
                console.error('Generation failed:', result.error);
            }
        } catch (error) {
            console.error('Error generating text:', error);
        }
        setLoading(false);
    };

    return (
        <div className="model-service">
            <h2>Model Service</h2>
            
            <div className="models-list">
                <h3>Available Models</h3>
                {loading ? (
                    <p>Loading models...</p>
                ) : (
                    <ul>
                        {models.map(model => (
                            <li key={model.id}>
                                {model.name} ({model.model_type})
                                {model.is_loaded && ' ✅'}
                            </li>
                        ))}
                    </ul>
                )}
            </div>

            <div className="text-generation">
                <h3>Text Generation</h3>
                <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="Enter your prompt..."
                    rows={4}
                />
                <button 
                    onClick={() => generateText(models[0]?.id)}
                    disabled={loading || !models.length}
                >
                    {loading ? 'Generating...' : 'Generate Text'}
                </button>
                
                {generatedText && (
                    <div className="generated-text">
                        <h4>Generated Text:</h4>
                        <p>{generatedText}</p>
                    </div>
                )}
            </div>
        </div>
    );
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        ModelServiceClient,
        ModelServiceAPI,
        setupModelServiceHandlers,
        exampleUsage
    };
} 