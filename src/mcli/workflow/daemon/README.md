# MCLI Daemon Service

A powerful daemon service for storing, managing, and executing commands written in various programming languages. The daemon runs as a background service without requiring sudo privileges and provides a client interface for command management.

## Features

### 🚀 **Multi-Language Support**
- **Python**: Full Python script execution with access to all installed packages
- **Node.js**: JavaScript/TypeScript execution with npm ecosystem
- **Lua**: Lightweight Lua script execution
- **Shell**: Bash/shell script execution with proper environment

### 🗄️ **Intelligent Storage**
- **SQLite Database**: Persistent storage with proper indexing
- **Embeddings**: TF-IDF based similarity search for finding related commands
- **Hierarchical Groups**: Organize commands into logical groups
- **Tags**: Flexible tagging system for command categorization

### 🔍 **Smart Search**
- **Text Search**: Search by name, description, or tags
- **Similarity Search**: Find similar commands using cosine similarity
- **Group Filtering**: Filter commands by group or language
- **Fuzzy Matching**: Intelligent command discovery

### ⚡ **Safe Execution**
- **Sandboxed Environment**: Commands run in isolated temporary directories
- **Timeout Protection**: 30-second execution timeout by default
- **Error Handling**: Comprehensive error capture and reporting
- **Execution History**: Track execution times and success rates

### 🎯 **User-Friendly Interface**
- **Interactive Mode**: Guided command creation with prompts
- **File Import**: Import commands from existing script files
- **Stdin Support**: Create commands from piped input
- **Batch Operations**: Execute multiple commands efficiently

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client CLI    │    │   Daemon        │    │   Database      │
│                 │    │   Service       │    │                 │
│ • add           │◄──►│ • Command       │◄──►│ • SQLite       │
│ • execute       │    │   Storage       │    │ • Embeddings   │
│ • search        │    │ • Execution     │    │ • Groups       │
│ • list          │    │ • Similarity    │    │ • History      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Installation

The daemon service is included with MCLI and requires no additional installation. Dependencies are automatically managed.

### Prerequisites

- Python 3.8+
- Node.js (for Node.js command execution)
- Lua (for Lua command execution)
- Required Python packages (installed automatically):
  - `scikit-learn` (for similarity search)
  - `numpy` (for embeddings)
  - `psutil` (for process management)

## Quick Start

### 1. Start the Daemon

```bash
# Start the daemon service
mcli workflow daemon start

# Check daemon status
mcli workflow daemon status
```

### 2. Add Your First Command

```bash
# Interactive command creation
mcli workflow daemon client add-interactive

# Or add from a file
mcli workflow daemon client add-file my-script my_script.py --language python --group utils

# Or add from stdin
echo "print('Hello, World!')" | mcli workflow daemon client add-stdin hello --language python
```

### 3. Execute Commands

```bash
# Execute a command by ID
mcli workflow daemon client execute <command-id>

# Execute with arguments
mcli workflow daemon client execute <command-id> arg1 arg2
```

### 4. Search and Discover

```bash
# Search for commands
mcli workflow daemon client search "data processing"

# Find similar commands
mcli workflow daemon client search "file operations" --similar

# List all commands
mcli workflow daemon client list

# List by group
mcli workflow daemon client list --group utils
```

## Command Reference

### Daemon Service Commands

```bash
# Start the daemon
mcli workflow daemon start [--config CONFIG]

# Stop the daemon
mcli workflow daemon stop

# Check daemon status
mcli workflow daemon status
```

### Client Commands

#### Adding Commands

```bash
# Interactive creation
mcli workflow daemon client add-interactive

# From file
mcli workflow daemon client add-file <name> <file-path> [options]

# From stdin
mcli workflow daemon client add-stdin <name> [options]

# Options:
#   --description TEXT    Command description
#   --language TEXT      python/node/lua/shell/auto
#   --group TEXT         Command group
#   --tags TEXT          Comma-separated tags
```

#### Executing Commands

```bash
# Execute command
mcli workflow daemon client execute <command-id> [args...]
```

#### Searching Commands

```bash
# Text search
mcli workflow daemon client search <query> [--limit N]

# Similarity search
mcli workflow daemon client search <query> --similar [--limit N]
```

#### Managing Commands

```bash
# List all commands
mcli workflow daemon client list [--group GROUP] [--language LANG]

# Show command details
mcli workflow daemon client show <command-id>

# Edit command
mcli workflow daemon client edit <command-id> [options]

# Delete command
mcli workflow daemon client delete <command-id>

# List groups
mcli workflow daemon client groups
```

## Examples

### Example 1: Data Processing Pipeline

```bash
# Create a Python script for data processing
cat > process_data.py << 'EOF'
import sys
import pandas as pd

def process_data(input_file, output_file):
    df = pd.read_csv(input_file)
    df['processed'] = df['value'] * 2
    df.to_csv(output_file, index=False)
    print(f"Processed {len(df)} rows")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: process_data.py <input.csv> <output.csv>")
        sys.exit(1)
    process_data(sys.argv[1], sys.argv[2])
EOF

# Add to daemon
mcli workflow daemon client add-file process-data process_data.py \
  --description "Process CSV data with pandas" \
  --language python \
  --group data-processing \
  --tags "csv,pandas,data"

# Execute
mcli workflow daemon client execute <command-id> input.csv output.csv
```

### Example 2: Node.js Web Scraper

```bash
# Create a Node.js scraper
cat > scrape.js << 'EOF'
const axios = require('axios');
const cheerio = require('cheerio');

async function scrape(url) {
    try {
        const response = await axios.get(url);
        const $ = cheerio.load(response.data);
        const title = $('title').text();
        console.log(`Title: ${title}`);
    } catch (error) {
        console.error('Error:', error.message);
    }
}

const url = process.argv[2] || 'https://example.com';
scrape(url);
EOF

# Add to daemon
mcli workflow daemon client add-file scrape scrape.js \
  --description "Web scraper using axios and cheerio" \
  --language node \
  --group web-tools \
  --tags "web,scraping,axios"

# Execute
mcli workflow daemon client execute <command-id> https://example.com
```

### Example 3: Shell Script

```bash
# Create a shell script
cat > backup.sh << 'EOF'
#!/bin/bash

SOURCE_DIR="$1"
BACKUP_DIR="$2"

if [ -z "$SOURCE_DIR" ] || [ -z "$BACKUP_DIR" ]; then
    echo "Usage: $0 <source_dir> <backup_dir>"
    exit 1
fi

if [ ! -d "$SOURCE_DIR" ]; then
    echo "Source directory does not exist: $SOURCE_DIR"
    exit 1
fi

mkdir -p "$BACKUP_DIR"
rsync -av "$SOURCE_DIR/" "$BACKUP_DIR/"
echo "Backup completed: $SOURCE_DIR -> $BACKUP_DIR"
EOF

# Add to daemon
mcli workflow daemon client add-file backup backup.sh \
  --description "Backup directory using rsync" \
  --language shell \
  --group system \
  --tags "backup,rsync,system"

# Execute
mcli workflow daemon client execute <command-id> /home/user/documents /backup/docs
```

## Database Schema

The daemon uses SQLite with the following schema:

### Commands Table
```sql
CREATE TABLE commands (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    code TEXT NOT NULL,
    language TEXT NOT NULL,
    group_name TEXT,
    tags TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execution_count INTEGER DEFAULT 0,
    last_executed TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);
```

### Groups Table
```sql
CREATE TABLE groups (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    parent_group_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_group_id) REFERENCES groups (id)
);
```

### Executions Table
```sql
CREATE TABLE executions (
    id TEXT PRIMARY KEY,
    command_id TEXT NOT NULL,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL,
    output TEXT,
    error TEXT,
    execution_time_ms INTEGER,
    FOREIGN KEY (command_id) REFERENCES commands (id)
);
```

## Configuration

The daemon stores its data in `~/.local/mcli/daemon/`:

```
~/.local/mcli/daemon/
├── commands.db          # SQLite database
├── daemon.pid          # Process ID file
└── daemon.sock         # Socket file (future use)
```

## Security Considerations

- **No Sudo Required**: The daemon runs with user privileges only
- **Sandboxed Execution**: Commands run in isolated temporary directories
- **Timeout Protection**: All executions have a 30-second timeout
- **Error Isolation**: Failed commands don't affect the daemon
- **Resource Limits**: Memory and CPU usage are monitored

## Troubleshooting

### Common Issues

1. **Daemon won't start**
   ```bash
   # Check if another daemon is running
   mcli workflow daemon status
   
   # Force stop if needed
   mcli workflow daemon stop
   ```

2. **Command execution fails**
   ```bash
   # Check command details
   mcli workflow daemon client show <command-id>
   
   # Verify language runtime is installed
   python --version  # for Python
   node --version    # for Node.js
   lua --version     # for Lua
   ```

3. **Search not finding commands**
   ```bash
   # Rebuild embeddings
   # (This happens automatically, but you can restart the daemon)
   mcli workflow daemon stop
   mcli workflow daemon start
   ```

### Debug Mode

Enable debug logging:
```bash
export MCLI_LOG_LEVEL=DEBUG
mcli workflow daemon start
```

## Future Enhancements

- **Web Interface**: Browser-based command management
- **API Endpoints**: REST API for remote access
- **Plugin System**: Extensible command types
- **Scheduling**: Cron-like command scheduling
- **Collaboration**: Shared command repositories
- **Versioning**: Command version control
- **Templates**: Command templates and snippets

## Contributing

The daemon system is designed to be extensible. Key extension points:

- **Language Support**: Add new execution languages
- **Storage Backends**: Support different databases
- **Search Algorithms**: Implement new similarity metrics
- **Execution Environments**: Add Docker/container support

## License

This daemon service is part of the MCLI project and follows the same license terms. 