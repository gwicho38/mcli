# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [7.9.5] - 2025-10-18

### Improved
- **Document Conversion Workflow**: Enhanced LaTeX package management and conversion reliability
  - Added `collection-latexextra` and `collection-fontsrecommended` for comprehensive LaTeX support
  - Integrated `mktexlsr` step to automatically refresh font database after package installation
  - Implemented temp directory system (`~/.mcli/commands/temp/conversions/`) for safe file handling
  - Added hard link support with automatic fallback to file copying
  - Enhanced fallback strategies for Jupyter notebook → PDF conversions (4-tier strategy)
  - Improved error messages with detailed conversion failure information
  - Complete LaTeX package documentation in init command

### Fixed
- Resolved path issues with spaces and special characters through temp directory system
- Fixed font availability issues by adding `mktexlsr` to refresh font database
- Improved conversion success rate with multiple fallback strategies

### Added
- Comprehensive LaTeX font support via `collection-fontsrecommended`
- Temp directory cleanup after conversions
- Conversion method reporting in summary output

## [7.9.4] - 2025-10-18

### Added
- **Document Conversion Workflow (doc-convert)**: Comprehensive pandoc wrapper for converting documents between formats
  - `mcli workflow doc-convert init`: One-command dependency installation (pandoc + BasicTeX via Homebrew)
  - `mcli workflow doc-convert convert`: Convert documents with smart format detection and glob pattern support
  - Support for 20+ document formats including Markdown, HTML, PDF, DOCX, Jupyter notebooks, LaTeX, EPUB, and more
  - Format aliases for common abbreviations (md → markdown, doc → docx, etc.)
  - Batch conversion with glob patterns (e.g., `"docs/**/*.md"`)
  - Custom output directory support
  - Pass-through for additional pandoc arguments
- **macOS Finder Service**: "Convert File(s) Here" service for right-click document conversion in Finder
  - Automatic format detection from file extensions
  - Multi-file selection support
  - User-friendly dialog for output format selection

### Changed
- Added comprehensive test coverage for doc-convert workflow
- Updated documentation with doc-convert usage examples

## [7.5.1] - 2025-10-13

### Fixed
- Package rebuild for PyPI distribution

## [7.5.0] - 2025-10-13

### Changed
- **Major refactoring to eliminate code duplication (DRY principle)**
  - Created `CloudProviderManager` base class to consolidate AWS, GCP, and Azure credential managers (eliminated 163 lines of duplicate code)
  - Extracted dashboard common utilities into `common.py` and `styles.py` (consolidated 300+ lines across 4 dashboards)
  - Created `scripts/utils/supabase_helper.py` with reusable Supabase connection utilities (eliminated 150+ lines across 5 scripts)
  - Refactored 5 Supabase scripts to use centralized helper functions
  - Removed duplicate logs command implementation from `self_cmd.py` (eliminated 260 lines)
  - Removed 10 deprecated commands completely (eliminated 461 lines)
  - Total reduction: ~1,300+ lines of duplicate/deprecated code

### Added
- Comprehensive CLAUDE.md documentation for AI-assisted development
- Shared dashboard utilities for page config, CSS styles, and Supabase client creation
- Centralized Supabase helper functions for consistent credential management

### Improved
- Better code maintainability through centralized utilities
- Consistent error handling across Supabase scripts
- Cleaner dashboard implementations with shared styling

## [7.3.1] - 2025-01-09

### Fixed
- Fixed deprecated Pydantic `regex` parameter in Field definitions (now uses `pattern`)
- Fixed deprecated Pydantic `orm_mode` in model Config classes (now uses `from_attributes`)
- Fixed global variable declaration order in CLI config command
- Resolved `mcli self search` command errors and warnings

### Added
- Comprehensive environment configuration template (`.env.example`)
- Pre-commit hooks configuration for code quality
- Test coverage configuration and reporting
- Enhanced Makefile with development targets
- Comprehensive linting and formatting configuration
- Security scanning with bandit and safety
- Project documentation (CONTRIBUTING.md, CODE_OF_CONDUCT.md)
- Docker support for development and deployment
- Tox configuration for multi-environment testing
- Requirements.txt files for compatibility

### Changed
- Enhanced README.md with better setup instructions
- Improved .gitignore with comprehensive patterns
- Updated project structure and organization

### Fixed
- Cleaned up build artifacts and Python cache files
- Organized untracked files into proper directories

## [5.5.1] - 2024-09-22

### Added
- Comprehensive shell completion and fix Supabase connectivity
- Enhanced git commit workflow with AI service integration
- Politician trading data collection and monitoring features
- RAG and other AI functionality improvements

### Changed
- Updated version to 5.5.1 for dot release
- Enhanced CI/CD workflows and testing

### Fixed
- Various bug fixes and improvements

## [5.5.0] - 2024-09-20

### Added
- AI chat integration with OpenAI and Anthropic support
- Command management and dynamic discovery
- Rich UI with colorful command-line experience
- IPython integration for interactive development
- Shell completion for bash, zsh, and fish
- Daemon and scheduler functionality
- Video processing capabilities
- Performance optimizations with Rust extensions

### Changed
- Migrated to UV for package management
- Enhanced project structure and organization
- Improved CLI interface and user experience

### Fixed
- Multiple performance and stability improvements

## [5.0.0] - 2024-09-01

### Added
- Initial release of MCLI framework
- Core CLI functionality with Click and Rich
- Basic command structure and extensibility
- Foundation for future enhancements

### Changed
- Complete rewrite of the CLI framework
- Modern Python packaging with pyproject.toml

## Migration Guide

### From 5.5.0 to 5.5.1

No breaking changes. Update normally:

```bash
uv pip install -U mcli
```

### From 5.0.x to 5.5.x

1. **Environment setup:** Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Dependencies:** If you have custom dependencies, review the new dependency structure in `pyproject.toml`

3. **Commands:** No breaking changes to existing commands

## Development Changes

### Development Setup Changes

Starting from version 5.5.1, development setup includes:

1. **Environment configuration:** Required `.env` file setup
2. **Pre-commit hooks:** Automatic code quality checks
3. **Enhanced testing:** Coverage reporting and multiple test types
4. **Comprehensive linting:** Multiple tools for code quality

### New Development Commands

```bash
# New Makefile targets
make lint                   # Run all linting tools
make format                # Auto-format code
make test-cov              # Run tests with coverage
make pre-commit-install    # Install pre-commit hooks
make security-check        # Run security checks
```

### Breaking Changes

None in recent releases. All changes are backward compatible.

## Upgrade Instructions

### Standard Upgrade

```bash
# With UV (recommended)
uv pip install -U mcli

# With pip
pip install -U mcli
```

### Development Environment Upgrade

```bash
# Update dependencies
make setup

# Install new development tools
make install-dev

# Setup pre-commit hooks
make pre-commit-install

# Configure environment
cp .env.example .env
# Edit .env with your configuration
```

## Support and Compatibility

### Supported Python Versions

- Python 3.9+
- Python 3.10+
- Python 3.11+
- Python 3.12+

### Supported Platforms

- macOS (Intel and Apple Silicon)
- Linux (Ubuntu, CentOS, Debian)
- Windows 10/11

### Dependencies

See `pyproject.toml` for complete dependency information.

## Security Updates

### 5.5.1
- Added security scanning with bandit
- Enhanced input validation
- Improved secret management guidelines

## Performance Improvements

### 5.5.1
- Enhanced Rust extensions integration
- Improved async performance with uvloop
- Optimized memory usage

### 5.5.0
- Initial Rust extensions for performance
- Async/await optimization
- Caching improvements

## Known Issues

### Current Issues

None reported for latest version.

### Fixed Issues

- Build artifacts cleanup (fixed in 5.5.1)
- Environment configuration (improved in 5.5.1)
- Test coverage reporting (added in 5.5.1)

## Credits

### Contributors

- Luis Fernandez de la Vara (@lefv) - Project Creator and Maintainer

### Acknowledgments

- Built with [Click](https://click.palletsprojects.com/) for CLI interfaces
- Styled with [Rich](https://github.com/Textualize/rich) for beautiful output
- Managed with [UV](https://docs.astral.sh/uv/) for fast Python packaging
- AI integration with OpenAI and Anthropic APIs

## Release Process

Releases are automated through GitHub Actions:

1. Version bumping via `make bump-version VERSION=x.y.z`
2. Automated testing across multiple Python versions
3. Automated building and publishing to PyPI
4. GitHub release creation with changelog

For detailed release information, see [GitHub Releases](https://github.com/gwicho38/mcli/releases).