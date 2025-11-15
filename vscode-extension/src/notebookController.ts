/**
 * Notebook controller for executing MCLI workflow cells.
 */

import * as vscode from 'vscode';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

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

    private async executePython(code: string): Promise<{ stdout: string; stderr: string }> {
        const fs = require('fs');
        const os = require('os');
        const path = require('path');

        // Create temporary file for secure execution
        const tmpDir = os.tmpdir();
        const tmpFile = path.join(tmpDir, `mcli-cell-${Date.now()}-${Math.random().toString(36).substring(7)}.py`);

        try {
            // Write code to temporary file
            fs.writeFileSync(tmpFile, code, 'utf8');

            // Execute via file (prevents command injection)
            const { stdout, stderr } = await execAsync(`python3 "${tmpFile}"`, {
                maxBuffer: 1024 * 1024 * 10, // 10MB
                timeout: 30000, // 30 seconds
            });

            return { stdout, stderr };
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
            } catch (cleanupError) {
                // Ignore cleanup errors
            }
        }
    }

    private async executeShell(
        code: string,
        shell: string
    ): Promise<{ stdout: string; stderr: string }> {
        const fs = require('fs');
        const os = require('os');
        const path = require('path');

        const shellBin = shell === 'shell' ? 'bash' : shell;

        // Create temporary file for secure execution
        const tmpDir = os.tmpdir();
        const extension = shellBin === 'bash' || shellBin === 'zsh' || shellBin === 'fish' ? '.sh' : '';
        const tmpFile = path.join(tmpDir, `mcli-cell-${Date.now()}-${Math.random().toString(36).substring(7)}${extension}`);

        try {
            // Write code to temporary file
            fs.writeFileSync(tmpFile, code, 'utf8');

            // Make file executable
            fs.chmodSync(tmpFile, '755');

            // Execute via file (prevents command injection)
            const { stdout, stderr } = await execAsync(`${shellBin} "${tmpFile}"`, {
                maxBuffer: 1024 * 1024 * 10,
                timeout: 30000,
            });

            return { stdout, stderr };
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
            } catch (cleanupError) {
                // Ignore cleanup errors
            }
        }
    }

    dispose(): void {
        this.controller.dispose();
    }
}
