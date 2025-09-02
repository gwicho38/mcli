# MCLI Shell Completion

MCLI provides comprehensive tab completion support for bash, zsh, and fish shells. This feature enables fast and efficient command discovery without needing to remember complex command structures.

## Features

- ✅ **Multi-shell support**: bash, zsh, fish
- ✅ **Deep completion**: Works with nested subcommands (e.g., `mcli workflow politician-trading cron-job`)
- ✅ **Fast performance**: Uses static completion data for lazy-loaded commands
- ✅ **Options completion**: Completes command options and flags
- ✅ **Auto-installation**: One-command setup for your shell

## Quick Start

### Install completion for your current shell:
```bash
mcli completion install
```

### Generate completion script manually:
```bash
# For bash
mcli completion bash

# For zsh  
mcli completion zsh

# For fish
mcli completion fish
```

### Check completion status:
```bash
mcli completion status
```

## Manual Installation

### Bash
1. Generate the completion script:
   ```bash
   mcli completion bash > ~/.mcli-completion.bash
   ```

2. Add to your `~/.bashrc`:
   ```bash
   echo "source ~/.mcli-completion.bash" >> ~/.bashrc
   ```

3. Reload your shell:
   ```bash
   source ~/.bashrc
   ```

### Zsh
1. Generate the completion script:
   ```bash
   mcli completion zsh > ~/.config/zsh/completions/_mcli
   ```

2. Add to your `~/.zshrc`:
   ```bash
   echo 'fpath=(~/.config/zsh/completions $fpath)' >> ~/.zshrc
   echo 'autoload -U compinit && compinit' >> ~/.zshrc
   ```

3. Reload your shell:
   ```bash
   source ~/.zshrc
   ```

### Fish
1. Generate the completion script:
   ```bash
   mcli completion fish > ~/.config/fish/completions/mcli.fish
   ```

2. Fish will automatically load the completion on next shell start.

## Usage Examples

Once installed, you can use tab completion throughout the MCLI command structure:

```bash
# Top-level commands
mcli <TAB>
# → chat, commands, completion, cron-test, logs, model, redis, self, version, visual, workflow

# Workflow subcommands
mcli workflow <TAB>
# → api-daemon, daemon, file, politician-trading, scheduler, sync, videos

# Deep nesting works too
mcli workflow politician-trading <TAB>
# → connectivity, cron-job, health, monitor, run, schema, setup, stats, status, test-workflow

# Options and flags
mcli workflow politician-trading cron-job <TAB>
# → --create, --test

# Other command groups
mcli redis <TAB>
# → flush, start, status, stop

mcli completion <TAB>
# → bash, fish, install, status, zsh
```

## Architecture

MCLI's completion system is designed for performance and maintainability:

### Lazy Loading with Completion
- **Problem**: Traditional lazy loading breaks shell completion because commands aren't discoverable until loaded
- **Solution**: Static completion data provides instant completions without loading heavy modules
- **Files**: 
  - `completion_cmd.py` - Completion management commands
  - `completion_helpers.py` - Static completion data and completion-aware lazy loading

### Static Completion Data
The completion system maintains a comprehensive map of all commands and their options:

```python
LAZY_COMMAND_COMPLETIONS = {
    "workflow": {
        "subcommands": ["api-daemon", "daemon", "politician-trading", ...],
        "politician-trading": {
            "subcommands": ["run", "status", "cron-job", ...],
            "cron-job": {
                "options": ["--create", "--test"]
            }
        }
    }
}
```

### Performance Benefits
- ⚡ **Instant completions**: No module loading required for common completions
- 🚀 **Fast startup**: Core CLI remains lightweight
- 🎯 **Accurate completions**: Always reflects current command structure

## Troubleshooting

### Completion not working
1. Check installation status:
   ```bash
   mcli completion status
   ```

2. Reinstall completion:
   ```bash
   mcli completion install
   ```

3. Restart your shell or source your profile

### Completions are outdated
If you've updated MCLI and completions seem outdated:

```bash
# Reinstall to get the latest completion data
mcli completion install
```

### Shell-specific issues

**Bash**: Make sure `bash-completion` package is installed on your system.

**Zsh**: Ensure `compinit` is being called in your `.zshrc`.

**Fish**: Check that `~/.config/fish/completions/` directory exists.

## Development

### Adding New Commands
When adding new commands or options to MCLI, update the static completion data in `completion_helpers.py`:

```python
LAZY_COMMAND_COMPLETIONS = {
    "your-command": {
        "subcommands": ["sub1", "sub2"],
        "sub1": {
            "options": ["--option1", "--option2"]
        }
    }
}
```

### Testing Completions
Test completions manually using environment variables:

```bash
export _MCLI_COMPLETE=bash_complete
export COMP_WORDS="mcli workflow "
export COMP_CWORD=2
mcli
```

This will output the available completions for `mcli workflow`.

## Contributing

To improve shell completion:

1. Test completions thoroughly across all supported shells
2. Update static completion data when adding new commands
3. Ensure completion performance remains fast
4. Add completion tests for new command groups

## Supported Commands

All MCLI commands support completion:

- **workflow**: Full deep completion for all workflow subcommands
- **politician-trading**: Complete subcommand and option completion  
- **completion**: Self-documenting completion commands
- **model**: Model management with subcommand completion
- **redis**: Redis service management
- **logs**: Log management utilities
- **chat**: Interactive chat options
- **cron-test**: Testing utilities
- **visual**: Visual effects commands

## Performance Notes

- Static completion data is loaded only when needed
- Heavy modules are never loaded during completion
- Completion response time is typically < 50ms
- Memory usage during completion is minimal

For more help with specific commands, use:
```bash
mcli <command> --help
mcli completion --help
```