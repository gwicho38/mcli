/**
 * Unit tests for WorkflowNotebookSerializer
 */

import * as assert from 'assert';
import * as vscode from 'vscode';
import { WorkflowNotebookSerializer } from '../../src/notebookSerializer';

suite('WorkflowNotebookSerializer Test Suite', () => {
    let serializer: WorkflowNotebookSerializer;

    setup(() => {
        serializer = new WorkflowNotebookSerializer();
    });

    suite('deserializeNotebook', () => {
        test('should deserialize valid notebook JSON', async () => {
            const notebook = {
                nbformat: 4,
                nbformat_minor: 5,
                metadata: {
                    mcli: {
                        name: 'test-workflow',
                        description: 'Test workflow',
                        language: 'python',
                    },
                },
                cells: [
                    {
                        cell_type: 'code',
                        source: ['print("hello")'],
                        metadata: { language: 'python' },
                        execution_count: null,
                        outputs: [],
                    },
                ],
            };

            const content = new TextEncoder().encode(JSON.stringify(notebook));
            const result = await serializer.deserializeNotebook(
                content,
                new vscode.CancellationTokenSource().token
            );

            assert.strictEqual(result.cells.length, 1);
            assert.strictEqual(result.cells[0].kind, vscode.NotebookCellKind.Code);
            assert.strictEqual(result.cells[0].value, 'print("hello")');
        });

        test('should handle empty content', async () => {
            const content = new TextEncoder().encode('');
            const result = await serializer.deserializeNotebook(
                content,
                new vscode.CancellationTokenSource().token
            );

            assert.strictEqual(result.cells.length, 0);
        });

        test('should convert old mcli command format to notebook', async () => {
            const oldCommand = {
                name: 'test-command',
                code: 'echo "hello"',
                description: 'Test command',
                language: 'shell',
                group: 'test',
                version: '1.0',
            };

            const content = new TextEncoder().encode(JSON.stringify(oldCommand));
            const result = await serializer.deserializeNotebook(
                content,
                new vscode.CancellationTokenSource().token
            );

            // Should create 2 cells: markdown for description, code for the command
            assert.strictEqual(result.cells.length, 2);
            assert.strictEqual(result.cells[0].kind, vscode.NotebookCellKind.Markup);
            assert.strictEqual(result.cells[1].kind, vscode.NotebookCellKind.Code);
        });

        test('should handle markdown cells', async () => {
            const notebook = {
                nbformat: 4,
                nbformat_minor: 5,
                metadata: { mcli: { name: 'test' } },
                cells: [
                    {
                        cell_type: 'markdown',
                        source: ['# Header\n', 'Text'],
                        metadata: {},
                    },
                ],
            };

            const content = new TextEncoder().encode(JSON.stringify(notebook));
            const result = await serializer.deserializeNotebook(
                content,
                new vscode.CancellationTokenSource().token
            );

            assert.strictEqual(result.cells[0].kind, vscode.NotebookCellKind.Markup);
            assert.strictEqual(result.cells[0].languageId, 'markdown');
        });

        test('should handle invalid JSON gracefully', async () => {
            const content = new TextEncoder().encode('{ invalid json }');
            const result = await serializer.deserializeNotebook(
                content,
                new vscode.CancellationTokenSource().token
            );

            // Should return empty notebook on parse error
            assert.strictEqual(result.cells.length, 0);
        });

        test('should handle JSON without cells array', async () => {
            const content = new TextEncoder().encode('{"nbformat": 4}');
            const result = await serializer.deserializeNotebook(
                content,
                new vscode.CancellationTokenSource().token
            );

            assert.strictEqual(result.cells.length, 0);
        });
    });

    suite('serializeNotebook', () => {
        test('should serialize notebook to JSON', async () => {
            const cells = [
                new vscode.NotebookCellData(
                    vscode.NotebookCellKind.Code,
                    'print("hello")',
                    'python'
                ),
            ];

            const notebookData = new vscode.NotebookData(cells);
            notebookData.metadata = {
                mcli: {
                    name: 'test-workflow',
                    description: 'Test',
                    language: 'python',
                },
                nbformat: 4,
                nbformat_minor: 5,
            };

            const result = await serializer.serializeNotebook(
                notebookData,
                new vscode.CancellationTokenSource().token
            );

            const json = JSON.parse(new TextDecoder().decode(result));

            assert.strictEqual(json.nbformat, 4);
            assert.strictEqual(json.cells.length, 1);
            assert.strictEqual(json.cells[0].cell_type, 'code');
        });

        test('should preserve metadata during serialization', async () => {
            const cells = [
                new vscode.NotebookCellData(
                    vscode.NotebookCellKind.Code,
                    'code',
                    'python'
                ),
            ];

            const notebookData = new vscode.NotebookData(cells);
            notebookData.metadata = {
                mcli: {
                    name: 'test',
                    description: 'Test workflow',
                    version: '2.0',
                },
                nbformat: 4,
                nbformat_minor: 5,
            };

            const result = await serializer.serializeNotebook(
                notebookData,
                new vscode.CancellationTokenSource().token
            );

            const json = JSON.parse(new TextDecoder().decode(result));

            assert.strictEqual(json.metadata.mcli.name, 'test');
            assert.strictEqual(json.metadata.mcli.version, '2.0');
        });

        test('should serialize markdown cells correctly', async () => {
            const cells = [
                new vscode.NotebookCellData(
                    vscode.NotebookCellKind.Markup,
                    '# Header',
                    'markdown'
                ),
            ];

            const notebookData = new vscode.NotebookData(cells);
            notebookData.metadata = {
                mcli: { name: 'test' },
                nbformat: 4,
                nbformat_minor: 5,
            };

            const result = await serializer.serializeNotebook(
                notebookData,
                new vscode.CancellationTokenSource().token
            );

            const json = JSON.parse(new TextDecoder().decode(result));

            assert.strictEqual(json.cells[0].cell_type, 'markdown');
        });
    });

    suite('Round-trip conversion', () => {
        test('should preserve data through deserialize -> serialize cycle', async () => {
            const original = {
                nbformat: 4,
                nbformat_minor: 5,
                metadata: {
                    mcli: {
                        name: 'test-workflow',
                        description: 'Test',
                    },
                },
                cells: [
                    {
                        cell_type: 'code',
                        source: ['print("hello")'],
                        metadata: { language: 'python' },
                        execution_count: null,
                        outputs: [],
                    },
                ],
            };

            // Deserialize
            const content = new TextEncoder().encode(JSON.stringify(original));
            const notebookData = await serializer.deserializeNotebook(
                content,
                new vscode.CancellationTokenSource().token
            );

            // Serialize back
            const serialized = await serializer.serializeNotebook(
                notebookData,
                new vscode.CancellationTokenSource().token
            );

            const result = JSON.parse(new TextDecoder().decode(serialized));

            assert.strictEqual(result.nbformat, original.nbformat);
            assert.strictEqual(result.cells.length, original.cells.length);
            assert.strictEqual(
                result.metadata.mcli.name,
                original.metadata.mcli.name
            );
        });
    });
});
