# Local vs Global Commands in MCLI Framework

## Overview

The MCLI Framework now supports both **local** and **global** commands, similar to npm's local (`npm install`) and global (`npm install -g`) package management system. This allows you to create project-specific commands that are isolated to a git repository, as well as system-wide commands that are available globally.

## Key Concepts

### Global Commands
- **Location**: `~/.mcli/commands/`
- **Scope**: Available system-wide, across all projects
- **Use Case**: Commands you want to use everywhere (utilities, tools, scripts)
- **Persistence**: Persist across projects and system reboots
- **Sharing**: Can be shared by copying files to another machine's `~/.mcli/commands/` directory

### Local Commands
- **Location**: `.mcli/commands/` (in the git repository root)
- **Scope**: Available only within the specific git repository
- **Use Case**: Project-specific workflows, build scripts, deployment commands
- **Persistence**: Version controlled with your project (can be committed to git)
- **Sharing**: Automatically shared when repository is cloned

## Default Behavior

MCLI intelligently determines whether to use local or global commands:

1. **Inside a Git Repository**: Defaults to local commands (`.mcli/commands/`)
2. **Outside a Git Repository**: Defaults to global commands (`~/.mcli/commands/`)

## Using the `--global` Flag

All `mcli commands` subcommands support the `--global` (or `-g`) flag to override the default behavior:

```bash
# Force global mode (even if in a git repository)
mcli commands add my-command --global
mcli commands list --custom-only --global
mcli commands remove my-command -g
```

## Command Reference

### Creating Commands

#### Create a Local Command (project-specific)
```bash
# When in a git repository, this creates a local command
cd /path/to/your/project  # Must be a git repository
mcli commands add deploy-script --description "Deploy application"
```

#### Create a Global Command (system-wide)
```bash
# Use --global flag to create a global command
mcli commands add git-helper --description "Git utility" --global

# Or create from outside a git repository (defaults to global)
cd /tmp
mcli commands add my-tool --description "My global tool"
```

### Listing Commands

#### List Local Commands
```bash
# Shows local commands (if in git repo)
mcli commands list --custom-only

# Explicitly list local commands
mcli commands list --custom-only  # defaults to local in git repo
```

#### List Global Commands
```bash
# Shows global commands
mcli commands list --custom-only --global
```

### Managing Commands

#### Edit Commands
```bash
# Edit local command
mcli commands edit my-local-cmd

# Edit global command
mcli commands edit my-global-cmd --global
```

#### Remove Commands
```bash
# Remove local command
mcli commands remove deploy-script -y

# Remove global command
mcli commands remove git-helper --global -y
```

### Import/Export Commands

#### Export Commands
```bash
# Export local commands to JSON
mcli commands export local-commands.json

# Export global commands to JSON
mcli commands export global-commands.json --global
```

#### Import Commands
```bash
# Import to local commands
mcli commands import commands.json

# Import to global commands
mcli commands import commands.json --global
```

### Lockfile Management

Each scope (local/global) has its own lockfile:

- **Local lockfile**: `.mcli/commands/commands.lock.json` (in git repo)
- **Global lockfile**: `~/.mcli/commands/commands.lock.json`

```bash
# Verify local commands against lockfile
mcli commands verify

# Verify global commands against lockfile
mcli commands verify --global

# Update lockfiles
mcli commands update-lockfile        # Update local lockfile
mcli commands update-lockfile -g     # Update global lockfile
```

### Store Sync (Git Integration)

The store sync commands also support local vs global:

```bash
# Push local commands to git store
mcli commands store push

# Push global commands to git store
mcli commands store push --global

# Pull commands to local directory
mcli commands store pull

# Pull commands to global directory
mcli commands store pull -g

# Sync (bidirectional)
mcli commands store sync             # Sync local
mcli commands store sync --global    # Sync global
```

## Practical Examples

### Example 1: Project-Specific Build Command

Create a local command for building your project:

```bash
cd ~/projects/my-app
mcli commands add build --description "Build the application" --template
```

This creates `.mcli/commands/build.json` in your project, which you can:
- Commit to git for team members
- Version control alongside your code
- Keep separate from other projects

### Example 2: Global Utility Command

Create a global command for a system-wide utility:

```bash
mcli commands add git-clean-branches --description "Clean up old git branches" --global
```

This creates `~/.mcli/commands/git_clean_branches.json`, which is available in all your projects.

### Example 3: Mixed Usage

You can have both local and global commands with the same name - they won't conflict:

```bash
# Local "deploy" command for this project
cd ~/projects/project-a
mcli commands add deploy --description "Deploy Project A"

# Global "deploy" command for general use
mcli commands add deploy --description "General deployment tool" --global

# When in project-a, "mcli workflow deploy" uses local version
# When outside git repos, "mcli workflow deploy" uses global version
```

## Identifying Scope

When listing commands, MCLI clearly indicates the scope:

```
Custom Commands
┌─────────────┬──────────┬─────────────────────┬─────────┬────────────┐
│ Name        │ Group    │ Description         │ Version │ Updated    │
├─────────────┼──────────┼─────────────────────┼─────────┼────────────┤
│ deploy      │ workflow │ Deploy application  │ 1.0     │ 2025-10-30 │
└─────────────┴──────────┴─────────────────────┴─────────┴────────────┘

Scope: local                                    ← Yellow highlight
Git repository: /Users/you/projects/my-app
Commands directory: /Users/you/projects/my-app/.mcli/commands
Lockfile: /Users/you/projects/my-app/.mcli/commands/commands.lock.json
```

**Scope Indicators**:
- `Scope: local` - Shown in **yellow**
- `Scope: global` - Shown in **cyan**

## Version Control Considerations

### Should You Commit Local Commands?

**Yes**, local commands should be committed to git:

```bash
# Add .mcli directory to git
git add .mcli/
git commit -m "Add project-specific MCLI commands"
```

**Benefits**:
- Team members automatically get project commands when they clone
- Commands are versioned with your code
- Reproducible development environment

### .gitignore Recommendations

If you want to keep some local commands private:

```gitignore
# Commit the structure and shared commands
.mcli/

# But ignore specific private commands
.mcli/commands/my-private-cmd.json
```

## Migration from Existing Commands

If you have existing global commands and want to convert them to local:

```bash
# Export global command
mcli commands export my-command -s -o /tmp/my-command.py --global

# Import as local command
cd /path/to/project
mcli commands import /tmp/my-command.py -s --name my-command
```

## Best Practices

### When to Use Local Commands

✅ **Use local commands for**:
- Project-specific build scripts
- Deployment workflows
- Database migration commands
- Testing utilities specific to the project
- CI/CD integration scripts

### When to Use Global Commands

✅ **Use global commands for**:
- General-purpose utilities
- Cross-project tools
- System administration scripts
- Personal productivity commands
- Reusable templates

### Organizing Commands

**Local Commands**:
```
my-project/
├── .mcli/
│   └── commands/
│       ├── build.json
│       ├── test.json
│       ├── deploy.json
│       └── commands.lock.json
├── src/
└── ...
```

**Global Commands**:
```
~/.mcli/
└── commands/
    ├── git-helper.json
    ├── doc-convert.json
    ├── clean.json
    └── commands.lock.json
```

## Troubleshooting

### Command Not Found

If a command isn't showing up:

1. **Check the scope**:
   ```bash
   mcli commands list --custom-only          # Local
   mcli commands list --custom-only --global # Global
   ```

2. **Verify you're in a git repository** (for local commands):
   ```bash
   git status  # Should show you're in a git repo
   ```

3. **Check the file exists**:
   ```bash
   ls .mcli/commands/          # Local
   ls ~/.mcli/commands/        # Global
   ```

### Command in Wrong Scope

If you created a command in the wrong scope:

```bash
# Export from current scope
mcli commands export my-command -s -o /tmp/my-command.py

# Remove from current scope
mcli commands remove my-command -y

# Import to correct scope
mcli commands import /tmp/my-command.py -s --global  # Or without --global
```

### Lockfile Out of Sync

```bash
# Update the lockfile
mcli commands update-lockfile        # Local
mcli commands update-lockfile -g     # Global

# Verify
mcli commands verify                 # Local
mcli commands verify -g              # Global
```

## Summary

The local vs global command feature provides:

- **Flexibility**: Choose between project-specific and system-wide commands
- **Isolation**: Keep project commands separate from global utilities
- **Version Control**: Local commands can be committed with your code
- **Intuitive**: Defaults to local when in git repos, global otherwise
- **Explicit Control**: Use `--global/-g` flag to override defaults

Start using local commands today to make your projects more reproducible and your workflows more organized!
