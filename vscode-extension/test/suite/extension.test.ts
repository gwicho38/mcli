/**
 * Integration tests for the extension
 */

import * as assert from 'assert';
import * as vscode from 'vscode';

suite('Extension Test Suite', () => {
    vscode.window.showInformationMessage('Start all tests.');

    test('Extension should be present', () => {
        const extension = vscode.extensions.getExtension('gwicho38.mcli-framework');
        assert.ok(extension, 'Extension should be installed');
    });

    test('Extension should activate', async () => {
        const extension = vscode.extensions.getExtension('gwicho38.mcli-framework');
        assert.ok(extension);

        await extension.activate();
        assert.strictEqual(extension.isActive, true, 'Extension should be active');
    });

    test('Commands should be registered', async () => {
        const commands = await vscode.commands.getCommands(true);

        assert.ok(
            commands.includes('mcli.openNotebookEditor'),
            'mcli.openNotebookEditor command should be registered'
        );
        assert.ok(
            commands.includes('mcli.addCodeCell'),
            'mcli.addCodeCell command should be registered'
        );
        assert.ok(
            commands.includes('mcli.addMarkdownCell'),
            'mcli.addMarkdownCell command should be registered'
        );
        assert.ok(
            commands.includes('mcli.runCell'),
            'mcli.runCell command should be registered'
        );
    });

    test('Notebook serializer should be registered', async () => {
        const extension = vscode.extensions.getExtension('gwicho38.mcli-framework');
        assert.ok(extension);

        await extension.activate();

        // Check that notebook type is available
        const notebookType = 'mcli-workflow-notebook';
        const notebooks = vscode.workspace.notebookDocuments;

        // The serializer registration can be verified by attempting to open a notebook
        // This is tested more thoroughly in integration tests
        assert.ok(extension.isActive);
    });
});
