/**
 * Notebook serializer for MCLI workflow notebooks.
 *
 * Converts between Jupyter notebook JSON format and VSCode's NotebookData.
 */

import * as vscode from 'vscode';
import { TextDecoder, TextEncoder } from 'util';

interface WorkflowNotebook {
    nbformat: number;
    nbformat_minor: number;
    metadata: {
        mcli: {
            name: string;
            description?: string;
            group?: string;
            version?: string;
            language?: string;
            created_at?: string;
            updated_at?: string;
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
    outputs?: CellOutput[];
    id?: string;
}

interface CellOutput {
    output_type: string;
    data?: any;
    text?: string[];
    name?: string;
    execution_count?: number;
    ename?: string;
    evalue?: string;
    traceback?: string[];
}

export class WorkflowNotebookSerializer implements vscode.NotebookSerializer {
    /**
     * Convert old mcli command format to notebook format
     */
    private convertMcliCommandToNotebook(command: any): WorkflowNotebook {
        const cells: NotebookCell[] = [];

        // Add description as markdown cell if present
        if (command.description) {
            cells.push({
                cell_type: 'markdown',
                source: [`# ${command.name}\n\n${command.description}`],
                metadata: {},
            });
        }

        // Add the code as a code cell
        if (command.code) {
            cells.push({
                cell_type: 'code',
                source: typeof command.code === 'string' ? [command.code] : command.code,
                metadata: {
                    language: command.language || 'python',
                },
                execution_count: null,
                outputs: [],
            });
        }

        // Return notebook format
        return {
            nbformat: 4,
            nbformat_minor: 5,
            metadata: {
                mcli: {
                    name: command.name || 'untitled',
                    description: command.description || '',
                    group: command.group || 'workflow',
                    version: command.version || '1.0',
                    language: command.language || 'python',
                    created_at: command.created_at,
                    updated_at: command.updated_at,
                    original_format: 'mcli_command', // Mark as converted from old format
                    ...command.metadata,
                },
            },
            cells,
        };
    }

    async deserializeNotebook(
        content: Uint8Array,
        _token: vscode.CancellationToken
    ): Promise<vscode.NotebookData> {
        const contents = new TextDecoder().decode(content);

        // Handle empty file
        if (!contents.trim()) {
            return new vscode.NotebookData([]);
        }

        let raw: any;
        try {
            raw = JSON.parse(contents);
        } catch (e: any) {
            vscode.window.showErrorMessage(
                `Failed to parse workflow notebook: ${e.message}`
            );
            return new vscode.NotebookData([]);
        }

        // Auto-convert old mcli command format to notebook format
        if (!raw.cells && raw.code) {
            raw = this.convertMcliCommandToNotebook(raw);
        }

        // Check if this is a valid notebook with cells
        if (!raw.cells || !Array.isArray(raw.cells)) {
            vscode.window.showErrorMessage(
                'This JSON file is not a valid notebook format. It must contain a "cells" array.'
            );
            return new vscode.NotebookData([]);
        }

        // Convert cells
        const cells = raw.cells.map((cell: NotebookCell) => this.convertCell(cell));

        const notebookData = new vscode.NotebookData(cells);

        // Preserve notebook metadata
        notebookData.metadata = {
            mcli: raw.metadata.mcli,
            nbformat: raw.nbformat,
            nbformat_minor: raw.nbformat_minor,
        };

        return notebookData;
    }

    async serializeNotebook(
        data: vscode.NotebookData,
        _token: vscode.CancellationToken
    ): Promise<Uint8Array> {
        const cells = data.cells.map((cell) => this.convertCellToJson(cell));

        // Check if this was originally an old mcli command format
        // If so, convert back to that format for compatibility
        const mcliMetadata = data.metadata?.mcli;
        if (mcliMetadata && mcliMetadata.original_format === 'mcli_command') {
            return this.serializeAsMcliCommand(data, cells);
        }

        const notebook: WorkflowNotebook = {
            nbformat: data.metadata?.nbformat || 4,
            nbformat_minor: data.metadata?.nbformat_minor || 5,
            metadata: {
                mcli: data.metadata?.mcli || {
                    name: 'untitled',
                    description: '',
                    version: '1.0',
                    language: 'python',
                },
                kernelspec: {
                    display_name: 'Python 3',
                    language: 'python',
                    name: 'python3',
                },
                language_info: {
                    name: 'python',
                    version: '3.11.0',
                    mimetype: 'text/x-python',
                    file_extension: '.py',
                },
            },
            cells,
        };

        const json = JSON.stringify(notebook, null, 2);
        return new TextEncoder().encode(json);
    }

    /**
     * Serialize back to old mcli command format
     */
    private serializeAsMcliCommand(
        data: vscode.NotebookData,
        cells: NotebookCell[]
    ): Uint8Array {
        const mcliMetadata = data.metadata?.mcli || {};

        // Combine all code cells into one code block
        const codeCells = cells.filter(c => c.cell_type === 'code');
        const code = codeCells
            .map(c => Array.isArray(c.source) ? c.source.join('') : c.source)
            .join('\n\n');

        const command = {
            name: mcliMetadata.name || 'untitled',
            code: code,
            description: mcliMetadata.description || '',
            group: mcliMetadata.group || 'workflow',
            language: mcliMetadata.language || 'python',
            created_at: mcliMetadata.created_at,
            updated_at: new Date().toISOString(),
            version: mcliMetadata.version || '1.0',
            metadata: {
                ...mcliMetadata.metadata,
                source: mcliMetadata.source,
                original_file: mcliMetadata.original_file,
                imported_at: mcliMetadata.imported_at,
            },
        };

        const json = JSON.stringify(command, null, 2);
        return new TextEncoder().encode(json);
    }

    private convertCell(cell: NotebookCell): vscode.NotebookCellData {
        // Determine cell kind
        let kind: vscode.NotebookCellKind;
        if (cell.cell_type === 'code') {
            kind = vscode.NotebookCellKind.Code;
        } else if (cell.cell_type === 'markdown') {
            kind = vscode.NotebookCellKind.Markup;
        } else {
            kind = vscode.NotebookCellKind.Markup; // Treat raw as markup
        }

        // Get source as string
        const source = Array.isArray(cell.source)
            ? cell.source.join('')
            : cell.source;

        // Determine language ID
        let languageId = 'python';
        if (cell.cell_type === 'markdown') {
            languageId = 'markdown';
        } else if (cell.metadata.language) {
            languageId = cell.metadata.language;
        }

        const cellData = new vscode.NotebookCellData(kind, source, languageId);

        // Convert outputs
        if (cell.outputs && cell.outputs.length > 0) {
            cellData.outputs = cell.outputs.map((output) =>
                this.convertOutput(output)
            );
        }

        // Preserve execution count
        if (cell.execution_count !== undefined && cell.execution_count !== null) {
            cellData.executionSummary = {
                executionOrder: cell.execution_count,
            };
        }

        // Preserve metadata
        cellData.metadata = cell.metadata;

        return cellData;
    }

    private convertCellToJson(cell: vscode.NotebookCellData): NotebookCell {
        const cell_type =
            cell.kind === vscode.NotebookCellKind.Code ? 'code' : 'markdown';

        // Split source into lines
        const source = cell.value.split('\n').map((line) => line + '\n');

        const jsonCell: NotebookCell = {
            cell_type,
            source,
            metadata: cell.metadata || {},
            execution_count: cell.executionSummary?.executionOrder ?? null,
        };

        // Add language metadata for code cells
        if (cell_type === 'code') {
            jsonCell.metadata.language = cell.languageId;
            jsonCell.outputs = cell.outputs
                ? cell.outputs.map((output) => this.convertOutputToJson(output))
                : [];
        }

        return jsonCell;
    }

    private convertOutput(output: CellOutput): vscode.NotebookCellOutput {
        const items: vscode.NotebookCellOutputItem[] = [];

        if (output.output_type === 'stream') {
            const text = Array.isArray(output.text)
                ? output.text.join('')
                : output.text || '';
            items.push(
                vscode.NotebookCellOutputItem.text(text, 'text/plain')
            );
        } else if (output.output_type === 'execute_result' || output.output_type === 'display_data') {
            if (output.data) {
                for (const [mime, value] of Object.entries(output.data)) {
                    if (mime === 'text/plain') {
                        const text = Array.isArray(value) ? value.join('') : String(value || '');
                        items.push(
                            vscode.NotebookCellOutputItem.text(text, mime)
                        );
                    } else if (mime === 'application/json') {
                        items.push(
                            vscode.NotebookCellOutputItem.json(value, mime)
                        );
                    } else {
                        const text = typeof value === 'string' ? value : JSON.stringify(value);
                        items.push(
                            vscode.NotebookCellOutputItem.text(text, mime)
                        );
                    }
                }
            }
        } else if (output.output_type === 'error') {
            items.push(
                vscode.NotebookCellOutputItem.error({
                    name: output.ename || 'Error',
                    message: output.evalue || '',
                    stack: output.traceback?.join('\n') || '',
                })
            );
        }

        return new vscode.NotebookCellOutput(items);
    }

    private convertOutputToJson(output: vscode.NotebookCellOutput): CellOutput {
        const item = output.items[0];
        if (!item) {
            return { output_type: 'stream', text: [] };
        }

        const mime = item.mime;
        const data = new TextDecoder().decode(item.data);

        if (mime === 'text/plain') {
            return {
                output_type: 'stream',
                name: 'stdout',
                text: data.split('\n'),
            };
        } else if (mime === 'application/json') {
            return {
                output_type: 'execute_result',
                data: { [mime]: JSON.parse(data) },
            };
        } else if (mime === 'application/vnd.code.notebook.error') {
            const error = JSON.parse(data);
            return {
                output_type: 'error',
                ename: error.name,
                evalue: error.message,
                traceback: error.stack?.split('\n') || [],
            };
        }

        return {
            output_type: 'display_data',
            data: { [mime]: data },
        };
    }
}
