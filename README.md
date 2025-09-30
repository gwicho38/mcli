# MCLI

A modern CLI framework with chat capabilities, command management, and extensible architecture.

## Features

- 🚀 **Modern CLI Framework**: Built with Click and Rich for beautiful command-line interfaces
- 💬 **AI Chat Integration**: Built-in chat capabilities with OpenAI and Anthropic support
- 🔧 **Command Management**: Dynamic command discovery and registration
- 🎨 **Rich UI**: Colorful, interactive command-line experience
- 📦 **Easy Extension**: Simple framework for adding custom commands
- 🛠️ **Developer Tools**: IPython integration for interactive development
- ⚡ **Shell Completion**: Full tab completion for bash, zsh, and fish shells

## Quick Start

### Prerequisites

- Python 3.9 or higher
- [UV](https://docs.astral.sh/uv/) (recommended) or pip

### Installation from PyPI (Recommended)

The easiest way to install mcli is from PyPI:

```bash
# Install latest version (includes all features)
pip install mcli-framework

# Or with UV (recommended)
uv pip install mcli-framework

# Optional: GPU support (CUDA required)
pip install "mcli-framework[gpu]"
```

**Note:** As of v7.0.0, all features are included by default. GPU support is optional as it requires CUDA.

**Self-Update Feature:** Once installed from PyPI, you can update mcli to the latest version with:

```bash
# Check for updates
mcli self update --check

# Install updates automatically
mcli self update

# Install with confirmation
mcli self update --yes
```

### Installation from Source

For development or if you want to customize mcli:

#### With UV

```bash
# Clone the repository
git clone https://github.com/gwicho38/mcli.git
cd mcli

# Install with UV (recommended)
uv venv
uv pip install -e .

# Or install development dependencies
uv pip install -e ".[dev]"
```

#### With pip

```bash
# Clone the repository
git clone https://github.com/gwicho38/mcli.git
cd mcli

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install -e .
```

### Usage

```bash
# Show available commands
mcli --help

# Start a chat session
mcli chat

# Get version information
mcli version

# Manage the application
mcli self --help

# List available commands
mcli commands
```

### Shell Completion (Optional)

Enable tab completion for faster command discovery:

```bash
# Install completion for your shell (auto-detects bash/zsh/fish)
mcli completion install

# Check completion status
mcli completion status
```

After installation, you'll have full tab completion:
- `mcli <TAB>` → shows all available commands
- `mcli workflow <TAB>` → shows workflow subcommands  
- `mcli workflow politician-trading <TAB>` → shows politician-trading options

See [SHELL_COMPLETION.md](SHELL_COMPLETION.md) for detailed setup and troubleshooting.

## Development Workflow

This project uses [UV](https://docs.astral.sh/uv/) for fast, reliable Python package management.

### Setup Development Environment

```bash
# 1. Set up the development environment
make setup

# Or manually with UV
uv venv
uv pip install -e ".[dev]"

# 2. Configure environment variables
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Available Make Commands

```bash
# Setup and Installation
make setup                  # Setup UV environment with caching
make install               # Install the package with caching

# Building
make wheel                 # Build Python wheel package
make portable              # Build portable executable
make validate-build        # Validate application for distribution

# Testing
make test                  # Test basic installation and functionality
make test-all              # Run complete test suite (if available)
make validate-build        # Comprehensive build validation

# CI/CD
make ci-trigger-build      # Trigger GitHub Actions build workflow
make ci-trigger-test       # Trigger GitHub Actions test workflow
make ci-watch              # Watch GitHub Actions runs in real-time
make ci-status             # Show GitHub Actions run status

# Maintenance
make clean                 # Clean all build artifacts
make debug                 # Show debug information
```

### Project Structure

```
mcli/
├── src/mcli/              # Main package source
│   ├── app/               # Application modules
│   │   ├── main.py        # Main CLI entry point
│   │   ├── chat_cmd.py    # Chat command implementation
│   │   └── commands_cmd.py # Command management
│   ├── chat/              # Chat system
│   ├── lib/               # Shared libraries
│   │   ├── api/           # API functionality
│   │   ├── ui/            # UI components
│   │   └── logger/        # Logging utilities
│   └── self/              # Self-management commands
├── tests/                 # Test suite
├── .github/workflows/     # CI/CD workflows
├── pyproject.toml         # Project configuration
├── Makefile              # Build and development commands
└── README.md             # This file
```

## Dependencies

### Core Dependencies
- **click**: Command-line interface creation
- **rich**: Rich text and beautiful formatting
- **requests**: HTTP library
- **tomli**: TOML parser

### AI & Chat
- **openai**: OpenAI API integration
- **anthropic**: Anthropic API integration

### Development Tools
- **ipython**: Interactive Python shell
- **inquirerpy**: Interactive command-line prompts

### Optional Dependencies

MCLI has been optimized with minimal core dependencies. Install only what you need:

```bash
# Chat and AI features
uv pip install -e ".[chat]"

# Video processing
uv pip install -e ".[video]"

# Document processing (PDF, Excel, etc.)
uv pip install -e ".[documents]"

# ML/Trading features
uv pip install -e ".[ml]"

# Database support
uv pip install -e ".[database]"

# Web dashboards
uv pip install -e ".[dashboard]"

# Development tools
uv pip install -e ".[dev]"

# Everything
uv pip install -e ".[all]"
```

Available extras:
- `chat` - OpenAI, Anthropic, Ollama support
- `async-extras` - FastAPI, Redis, advanced async features
- `video` - OpenCV, image processing
- `documents` - PDF, Excel processing
- `viz` - Matplotlib, Plotly visualization
- `database` - Supabase, SQLAlchemy, PostgreSQL
- `ml` - PyTorch, MLflow, DVC, trading features
- `gpu` - CUDA support
- `monitoring` - Prometheus, Datadog
- `streaming` - Kafka support
- `dashboard` - Streamlit dashboards
- `web` - Flask, FastAPI web frameworks
- `dev` - Testing, linting, type checking
- `all` - All optional features

## Configuration

MCLI can be configured through environment variables and configuration files.

### Environment Setup

1. **Copy the environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit the `.env` file with your configuration:**
   ```bash
   # Required for AI chat functionality
   OPENAI_API_KEY=your-openai-api-key-here
   ANTHROPIC_API_KEY=your-anthropic-api-key-here

   # Required for politician trading features
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-supabase-anon-key-here
   SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key-here
   ```

3. **Optional development settings:**
   ```bash
   # Enable debug logging
   MCLI_TRACE_LEVEL=1
   MCLI_DEBUG=true

   # Performance optimization
   MCLI_AUTO_OPTIMIZE=true
   ```

See `.env.example` for a complete list of configuration options.

## Creating Custom Commands

MCLI supports dynamic command discovery. Add your commands to the appropriate modules:

```python
import click
from mcli.lib.ui.styling import success

@click.command()
def my_command():
    """My custom command."""
    success("Hello from my custom command!")
```

## CI/CD

The project includes comprehensive CI/CD with GitHub Actions:

- **Build Workflow**: Multi-platform builds (Ubuntu, macOS)
- **Test Workflow**: Multi-Python version testing (3.9-3.12)
- **Automatic Triggers**: Runs on push/PR to main branch
- **Manual Triggers**: Use `make ci-trigger-*` commands

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Run tests: `make test`
5. Validate build: `make validate-build`
6. Commit your changes: `git commit -am 'Add feature'`
7. Push to your fork: `git push origin feature-name`
8. Create a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Built with [Click](https://click.palletsprojects.com/) for CLI interfaces
- Styled with [Rich](https://github.com/Textualize/rich) for beautiful output
- Managed with [UV](https://docs.astral.sh/uv/) for fast Python packaging