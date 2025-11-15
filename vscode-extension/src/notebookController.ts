/**
 * Notebook controller for executing MCLI workflow cells.
 */

import * as vscode from 'vscode';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';

const execAsync = promisify(exec);

// Common execution options
const COMMON_EXEC_OPTS = {
    maxBuffer: 1024 * 1024 * 10, // 10MB
    timeout: 30000, // 30 seconds
};

export class WorkflowNotebookController {
    private readonly controller: vscode.NotebookController;
    private readonly executionOrder = new Map<string, number>();

    constructor() {
        this.controller = vscode.notebooks.createNotebookController(
            'mcli-workflow-controller',
            'mcli-workflow-notebook',
            'MCLI Workflow'
        );

        this.controller.supportedLanguages = ['python', 'shell', 'bash', 'zsh', 'fish'];
        this.controller.supportsExecutionOrder = true;
        this.controller.description = 'Execute MCLI workflow cells';
        this.controller.executeHandler = this.execute.bind(this);
    }

    private async execute(
        cells: vscode.NotebookCell[],
        notebook: vscode.NotebookDocument,
        controller: vscode.NotebookController
    ): Promise<void> {
        for (const cell of cells) {
            await this.executeCell(cell, controller);
        }
    }

    private async executeCell(
        cell: vscode.NotebookCell,
        controller: vscode.NotebookController
    ): Promise<void> {
        const execution = controller.createNotebookCellExecution(cell);

        // Get next execution order
        const notebookUri = cell.notebook.uri.toString();
        const currentOrder = this.executionOrder.get(notebookUri) || 0;
        const executionOrder = currentOrder + 1;
        this.executionOrder.set(notebookUri, executionOrder);

        execution.executionOrder = executionOrder;
        execution.start(Date.now());

        try {
            const code = cell.document.getText();
            const language = cell.document.languageId;

            let result: { stdout: string; stderr: string };

            if (language === 'python') {
                result = await this.executePython(code);
            } else if (['shell', 'bash', 'zsh', 'fish'].includes(language)) {
                result = await this.executeShell(code, language);
            } else {
                throw new Error(`Unsupported language: ${language}`);
            }

            // Clear previous outputs
            execution.clearOutput(cell);

            // Add stdout output
            if (result.stdout) {
                execution.appendOutput(
                    new vscode.NotebookCellOutput([
                        vscode.NotebookCellOutputItem.text(
                            result.stdout,
                            'text/plain'
                        ),
                    ])
                );
            }

            // Add stderr output
            if (result.stderr) {
                execution.appendOutput(
                    new vscode.NotebookCellOutput([
                        vscode.NotebookCellOutputItem.stderr(result.stderr),
                    ])
                );
            }

            execution.end(true, Date.now());
        } catch (error: any) {
            execution.replaceOutput(
                new vscode.NotebookCellOutput([
                    vscode.NotebookCellOutputItem.error({
                        name: 'Execution Error',
                        message: error.message,
                        stack: error.stack || '',
                    }),
                ])
            );
            execution.end(false, Date.now());
        }
    }

    /**
     * Execute code in a temporary file to prevent command injection
     * @param code The code to execute
     * @param extension File extension for the temporary file
     * @param prepare Optional function to prepare the file (e.g., set permissions)
     * @param executor Function to execute the file
     * @returns stdout and stderr from execution
     */
    private async execWithTempFile(
        code: string,
        extension: string,
        prepare?: (file: string) => void,
        executor?: (file: string) => Promise<{ stdout: string; stderr: string }>
    ): Promise<{ stdout: string; stderr: string }> {
        const tmpFile = path.join(
            os.tmpdir(),
            `mcli-cell-${Date.now()}-${Math.random().toString(36).substring(7)}${extension}`
        );

        try {
            // Write code to temporary file
            fs.writeFileSync(tmpFile, code, 'utf8');

            // Optional preparation (e.g., chmod for shell scripts)
            if (prepare) {
                prepare(tmpFile);
            }

            // Execute with provided executor or default
            const defaultExecutor = async (file: string) => execAsync(file, COMMON_EXEC_OPTS);
            return await (executor || defaultExecutor)(tmpFile);
        } catch (error: any) {
            return {
                stdout: error.stdout || '',
                stderr: error.stderr || error.message,
            };
        } finally {
            // Clean up temporary file
            try {
                if (fs.existsSync(tmpFile)) {
                    fs.unlinkSync(tmpFile);
                }
            } catch (cleanupError: any) {
                // Log cleanup errors at debug level for diagnostics
                console.debug(`Temporary file cleanup failed for ${tmpFile}:`, cleanupError);
            }
        }
    }

    private async executePython(code: string): Promise<{ stdout: string; stderr: string }> {
        return this.execWithTempFile(
            code,
            '.py',
            undefined,
            (file) => execAsync(`python3 "${file}"`, COMMON_EXEC_OPTS)
        );
    }

    private async executeShell(
        code: string,
        shell: string
    ): Promise<{ stdout: string; stderr: string }> {
        const shellBin = shell === 'shell' ? 'bash' : shell;
        const extension = ['bash', 'zsh', 'fish'].includes(shellBin) ? '.sh' : '';

        return this.execWithTempFile(
            code,
            extension,
            (file) => fs.chmodSync(file, 0o755),
            (file) => execAsync(`${shellBin} "${file}"`, COMMON_EXEC_OPTS)
        );
    }

    dispose(): void {
        this.controller.dispose();
    }
}
