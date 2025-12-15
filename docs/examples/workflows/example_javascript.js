#!/usr/bin/env bun
// @description: Example JavaScript workflow command
// @version: 1.0.0
// @group: examples
// @author: MCLI Team
// @tags: example, demo, javascript, bun

/**
 * Example JavaScript workflow command for mcli.
 *
 * This demonstrates how to create a JavaScript-based mcli command
 * executed with Bun runtime.
 *
 * The script will be automatically discovered and available as:
 *     mcli run example_javascript
 *
 * Arguments are available in Bun.argv (first two are bun and script path).
 * The command name is available in process.env.MCLI_COMMAND
 */

// Parse arguments
const args = Bun.argv.slice(2);
const commandName = process.env.MCLI_COMMAND || 'example_javascript';

// Default values
const name = args[0] || 'World';
const greeting = args[1] || 'Hello';
const verbose = process.env.VERBOSE === 'true' || args.includes('--verbose');

// Helper function for verbose logging
function logDebug(...messages) {
    if (verbose) {
        console.error('[DEBUG]', ...messages);
    }
}

// Show help if requested
if (args.includes('--help') || args.includes('-h')) {
    console.log(`Usage: mcli run ${commandName} [NAME] [GREETING]

An example JavaScript workflow command.

Arguments:
  NAME      Name to greet (default: World)
  GREETING  Greeting to use (default: Hello)

Options:
  --verbose  Enable debug output
  --help     Show this help message

Environment:
  VERBOSE=true  Enable debug output`);
    process.exit(0);
}

// Main logic
function main() {
    logDebug(`name=${name}, greeting=${greeting}`);
    logDebug(`MCLI_COMMAND=${commandName}`);

    const message = `${greeting}, ${name}!`;
    console.log(message);

    logDebug(`Message length: ${message.length}`);
}

main();
