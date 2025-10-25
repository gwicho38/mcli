/**
 * Custom editor provider for MCLI workflow notebooks.
 */

import * as vscode from 'vscode';
import { getNonce } from './util';

interface NotebookDocument {
    nbformat: number;
    nbformat_minor: number;
    metadata: {
        mcli: {
            name: string;
            description?: string;
            group?: string;
            version?: string;
            language?: string;
        };
        kernelspec?: any;
        language_info?: any;
    };
    cells: NotebookCell[];
}

interface NotebookCell {
    cell_type: 'code' | 'markdown' | 'raw';
    source: string | string[];
    metadata: {
        language?: string;
        [key: string]: any;
    };
    execution_count?: number | null;
    outputs?: any[];
    id?: string;
}

export class WorkflowNotebookEditorProvider implements vscode.CustomTextEditorProvider {
    private currentPanel: vscode.WebviewPanel | undefined;
    private currentDocument: vscode.TextDocument | undefined;

    constructor(private readonly context: vscode.ExtensionContext) {}

    public async resolveCustomTextEditor(
        document: vscode.TextDocument,
        webviewPanel: vscode.WebviewPanel,
        _token: vscode.CancellationToken
    ): Promise<void> {
        this.currentPanel = webviewPanel;
        this.currentDocument = document;

        // Setup webview options
        webviewPanel.webview.options = {
            enableScripts: true,
            localResourceRoots: [this.context.extensionUri],
        };

        // Set initial HTML content
        webviewPanel.webview.html = this.getHtmlForWebview(webviewPanel.webview, document);

        // Handle messages from webview
        webviewPanel.webview.onDidReceiveMessage(async (message) => {
            switch (message.type) {
                case 'update':
                    await this.updateDocument(document, message.content);
                    break;
                case 'addCell':
                    await this.handleAddCell(document, message.cellType, message.index);
                    break;
                case 'deleteCell':
                    await this.handleDeleteCell(document, message.index);
                    break;
                case 'moveCell':
                    await this.handleMoveCell(document, message.fromIndex, message.toIndex);
                    break;
                case 'runCell':
                    await this.handleRunCell(document, message.index);
                    break;
            }
        });

        // Update webview when document changes
        const changeDocumentSubscription = vscode.workspace.onDidChangeTextDocument((e) => {
            if (e.document.uri.toString() === document.uri.toString()) {
                webviewPanel.webview.postMessage({
                    type: 'update',
                    content: document.getText(),
                });
            }
        });

        webviewPanel.onDidDispose(() => {
            changeDocumentSubscription.dispose();
        });

        // Send initial content
        webviewPanel.webview.postMessage({
            type: 'init',
            content: document.getText(),
        });
    }

    private async updateDocument(document: vscode.TextDocument, content: string): Promise<void> {
        const edit = new vscode.WorkspaceEdit();
        edit.replace(
            document.uri,
            new vscode.Range(0, 0, document.lineCount, 0),
            content
        );
        await vscode.workspace.applyEdit(edit);
    }

    private async handleAddCell(
        document: vscode.TextDocument,
        cellType: 'code' | 'markdown',
        index: number
    ): Promise<void> {
        const notebook = JSON.parse(document.getText()) as NotebookDocument;

        const newCell: NotebookCell = {
            cell_type: cellType,
            source: cellType === 'code' ? '# New code cell\n' : '# New markdown cell\n',
            metadata: cellType === 'code' ? { language: 'python' } : {},
            execution_count: cellType === 'code' ? null : undefined,
            outputs: cellType === 'code' ? [] : undefined,
        };

        notebook.cells.splice(index + 1, 0, newCell);
        await this.updateDocument(document, JSON.stringify(notebook, null, 2));
    }

    private async handleDeleteCell(document: vscode.TextDocument, index: number): Promise<void> {
        const notebook = JSON.parse(document.getText()) as NotebookDocument;
        notebook.cells.splice(index, 1);
        await this.updateDocument(document, JSON.stringify(notebook, null, 2));
    }

    private async handleMoveCell(
        document: vscode.TextDocument,
        fromIndex: number,
        toIndex: number
    ): Promise<void> {
        const notebook = JSON.parse(document.getText()) as NotebookDocument;
        const [cell] = notebook.cells.splice(fromIndex, 1);
        notebook.cells.splice(toIndex, 0, cell);
        await this.updateDocument(document, JSON.stringify(notebook, null, 2));
    }

    private async handleRunCell(document: vscode.TextDocument, index: number): Promise<void> {
        const notebook = JSON.parse(document.getText()) as NotebookDocument;
        const cell = notebook.cells[index];

        if (cell.cell_type !== 'code') {
            return;
        }

        // TODO: Implement cell execution via MCLI
        vscode.window.showInformationMessage(
            'Cell execution will be implemented in the next phase'
        );
    }

    public addCell(cellType: 'code' | 'markdown'): void {
        if (!this.currentPanel || !this.currentDocument) {
            return;
        }

        this.currentPanel.webview.postMessage({
            type: 'addCell',
            cellType,
        });
    }

    public runCell(): void {
        if (!this.currentPanel || !this.currentDocument) {
            return;
        }

        this.currentPanel.webview.postMessage({
            type: 'runCell',
        });
    }

    private getHtmlForWebview(webview: vscode.Webview, document: vscode.TextDocument): string {
        const nonce = getNonce();

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';">
    <title>MCLI Workflow Notebook</title>
    <style>
        body {
            padding: 0;
            margin: 0;
            font-family: var(--vscode-font-family);
            background-color: var(--vscode-editor-background);
            color: var(--vscode-editor-foreground);
        }
        .notebook-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .notebook-header {
            padding: 20px;
            border-bottom: 1px solid var(--vscode-panel-border);
            margin-bottom: 20px;
        }
        .notebook-title {
            font-size: 24px;
            font-weight: 600;
            margin: 0 0 10px 0;
        }
        .notebook-description {
            color: var(--vscode-descriptionForeground);
            margin: 0;
        }
        .cell {
            margin-bottom: 20px;
            border: 1px solid var(--vscode-panel-border);
            border-radius: 4px;
            overflow: hidden;
        }
        .cell-toolbar {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            background-color: var(--vscode-editorGroupHeader-tabsBackground);
            border-bottom: 1px solid var(--vscode-panel-border);
        }
        .cell-type {
            font-size: 11px;
            text-transform: uppercase;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 3px;
            background-color: var(--vscode-badge-background);
            color: var(--vscode-badge-foreground);
        }
        .cell-controls {
            margin-left: auto;
            display: flex;
            gap: 4px;
        }
        .btn {
            padding: 4px 8px;
            border: none;
            background-color: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border-radius: 3px;
            cursor: pointer;
            font-size: 11px;
        }
        .btn:hover {
            background-color: var(--vscode-button-hoverBackground);
        }
        .btn-icon {
            padding: 4px 8px;
            background: transparent;
            border: 1px solid var(--vscode-panel-border);
        }
        .cell-content {
            padding: 12px;
        }
        .cell-editor {
            width: 100%;
            min-height: 100px;
            background-color: var(--vscode-editor-background);
            color: var(--vscode-editor-foreground);
            border: none;
            font-family: var(--vscode-editor-font-family);
            font-size: var(--vscode-editor-font-size);
            resize: vertical;
            padding: 8px;
        }
        .cell-output {
            margin-top: 12px;
            padding: 8px;
            background-color: var(--vscode-terminal-background);
            border-radius: 3px;
            font-family: monospace;
            font-size: 12px;
        }
        .markdown-preview {
            padding: 12px;
            line-height: 1.6;
        }
        .add-cell-section {
            display: flex;
            gap: 8px;
            justify-content: center;
            padding: 20px;
        }
    </style>
</head>
<body>
    <div class="notebook-container">
        <div class="notebook-header">
            <h1 class="notebook-title" id="notebook-title">Loading...</h1>
            <p class="notebook-description" id="notebook-description"></p>
        </div>
        <div id="cells-container"></div>
        <div class="add-cell-section">
            <button class="btn" onclick="addCell('code')">+ Code Cell</button>
            <button class="btn" onclick="addCell('markdown')">+ Markdown Cell</button>
        </div>
    </div>

    <script nonce="${nonce}">
        const vscode = acquireVsCodeApi();
        let notebookData = null;

        // Message handler
        window.addEventListener('message', event => {
            const message = event.data;
            switch (message.type) {
                case 'init':
                case 'update':
                    loadNotebook(message.content);
                    break;
                case 'addCell':
                    addCell(message.cellType);
                    break;
                case 'runCell':
                    runFocusedCell();
                    break;
            }
        });

        function loadNotebook(content) {
            try {
                notebookData = JSON.parse(content);
                renderNotebook();
            } catch (e) {
                console.error('Failed to parse notebook:', e);
            }
        }

        function renderNotebook() {
            if (!notebookData) return;

            // Update header
            document.getElementById('notebook-title').textContent =
                notebookData.metadata.mcli.name || 'Untitled';
            document.getElementById('notebook-description').textContent =
                notebookData.metadata.mcli.description || '';

            // Render cells
            const container = document.getElementById('cells-container');
            container.innerHTML = '';

            notebookData.cells.forEach((cell, index) => {
                container.appendChild(renderCell(cell, index));
            });
        }

        function renderCell(cell, index) {
            const cellDiv = document.createElement('div');
            cellDiv.className = 'cell';
            cellDiv.dataset.index = index;

            const source = Array.isArray(cell.source) ? cell.source.join('') : cell.source;

            cellDiv.innerHTML = \`
                <div class="cell-toolbar">
                    <span class="cell-type">\${cell.cell_type}</span>
                    <span style="font-size: 11px; color: var(--vscode-descriptionForeground);">
                        \${cell.metadata.language || ''}
                    </span>
                    <div class="cell-controls">
                        \${cell.cell_type === 'code' ? '<button class="btn-icon btn" onclick="runCell(' + index + ')">▶ Run</button>' : ''}
                        <button class="btn-icon btn" onclick="moveCell(' + index + ', ' + (index - 1) + ')">↑</button>
                        <button class="btn-icon btn" onclick="moveCell(' + index + ', ' + (index + 1) + ')">↓</button>
                        <button class="btn-icon btn" onclick="deleteCell(' + index + ')">✕</button>
                    </div>
                </div>
                <div class="cell-content">
                    <textarea class="cell-editor"
                              data-index="\${index}"
                              onchange="updateCellContent(' + index + ', this.value)">\${source}</textarea>
                    \${cell.cell_type === 'code' && cell.outputs && cell.outputs.length > 0
                        ? '<div class="cell-output">' + renderOutputs(cell.outputs) + '</div>'
                        : ''}
                </div>
            \`;

            return cellDiv;
        }

        function renderOutputs(outputs) {
            return outputs.map(output => {
                if (output.output_type === 'stream') {
                    return (output.text || []).join('');
                }
                return JSON.stringify(output, null, 2);
            }).join('\\n');
        }

        function updateCellContent(index, newContent) {
            if (!notebookData) return;
            notebookData.cells[index].source = newContent.split('\\n').map(line => line + '\\n');
            saveNotebook();
        }

        function addCell(cellType) {
            const focusedCell = document.querySelector('.cell-editor:focus');
            const index = focusedCell
                ? parseInt(focusedCell.dataset.index)
                : notebookData.cells.length - 1;

            vscode.postMessage({
                type: 'addCell',
                cellType,
                index
            });
        }

        function deleteCell(index) {
            vscode.postMessage({
                type: 'deleteCell',
                index
            });
        }

        function moveCell(fromIndex, toIndex) {
            if (toIndex < 0 || toIndex >= notebookData.cells.length) return;
            vscode.postMessage({
                type: 'moveCell',
                fromIndex,
                toIndex
            });
        }

        function runCell(index) {
            vscode.postMessage({
                type: 'runCell',
                index
            });
        }

        function runFocusedCell() {
            const focusedCell = document.querySelector('.cell-editor:focus');
            if (focusedCell) {
                runCell(parseInt(focusedCell.dataset.index));
            }
        }

        function saveNotebook() {
            vscode.postMessage({
                type: 'update',
                content: JSON.stringify(notebookData, null, 2)
            });
        }
    </script>
</body>
</html>`;
    }
}
