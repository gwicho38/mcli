/**
 * MCLI Workflow Notebook VSCode Extension
 *
 * Provides visual notebook editing for MCLI workflow JSON files using VSCode's Native Notebook API.
 */

import * as vscode from 'vscode';
import { WorkflowNotebookSerializer } from './notebookSerializer';
import { WorkflowNotebookController } from './notebookController';

export function activate(context: vscode.ExtensionContext) {
    console.log('MCLI Workflow Notebooks extension activated');

    // Register notebook serializer
    const serializer = new WorkflowNotebookSerializer();
    context.subscriptions.push(
        vscode.workspace.registerNotebookSerializer(
            'mcli-workflow-notebook',
            serializer,
            {
                transientOutputs: false,
                transientCellMetadata: {
                    inputCollapsed: true,
                    outputCollapsed: true,
                }
            }
        )
    );

    // Register notebook controller (for cell execution)
    const controller = new WorkflowNotebookController();
    context.subscriptions.push(controller);

    // Register command to open JSON as notebook
    context.subscriptions.push(
        vscode.commands.registerCommand('mcli.openNotebookEditor', async () => {
            const editor = vscode.window.activeTextEditor;
            if (editor && editor.document.uri.fsPath.endsWith('.json')) {
                await vscode.commands.executeCommand(
                    'vscode.openWith',
                    editor.document.uri,
                    'mcli-workflow-notebook'
                );
            }
        })
    );

    console.log('MCLI Workflow Notebooks extension ready');
}

export function deactivate() {
    console.log('MCLI Workflow Notebooks extension deactivated');
}
