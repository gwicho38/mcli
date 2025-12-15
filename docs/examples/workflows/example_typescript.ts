#!/usr/bin/env bun
// @description: Example TypeScript workflow command
// @version: 1.0.0
// @group: examples
// @author: MCLI Team
// @tags: example, demo, typescript, bun

/**
 * Example TypeScript workflow command for mcli.
 *
 * This demonstrates how to create a TypeScript-based mcli command
 * executed with Bun runtime (which has native TypeScript support).
 *
 * The script will be automatically discovered and available as:
 *     mcli run example_typescript
 *
 * Arguments are available in Bun.argv (first two are bun and script path).
 * The command name is available in process.env.MCLI_COMMAND
 */

// Type definitions
interface Config {
    name: string;
    greeting: string;
    verbose: boolean;
}

// Parse arguments
const args: string[] = Bun.argv.slice(2);
const commandName: string = process.env.MCLI_COMMAND || 'example_typescript';

// Configuration with defaults
const config: Config = {
    name: args[0] || 'World',
    greeting: args[1] || 'Hello',
    verbose: process.env.VERBOSE === 'true' || args.includes('--verbose'),
};

// Helper function for verbose logging
function logDebug(...messages: unknown[]): void {
    if (config.verbose) {
        console.error('[DEBUG]', ...messages);
    }
}

// Show help if requested
function showHelp(): void {
    console.log(`Usage: mcli run ${commandName} [NAME] [GREETING]

An example TypeScript workflow command.

Arguments:
  NAME      Name to greet (default: World)
  GREETING  Greeting to use (default: Hello)

Options:
  --verbose  Enable debug output
  --help     Show this help message

Environment:
  VERBOSE=true  Enable debug output`);
}

// Main logic
function main(): void {
    if (args.includes('--help') || args.includes('-h')) {
        showHelp();
        process.exit(0);
    }

    logDebug(`config=${JSON.stringify(config)}`);
    logDebug(`MCLI_COMMAND=${commandName}`);

    const message: string = `${config.greeting}, ${config.name}!`;
    console.log(message);

    logDebug(`Message length: ${message.length}`);
}

main();
