# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [8.0.7] - 2026-01-21

### Fixed
- **Async Test Configuration**: Fixed 32 failing async unit tests by ensuring `pytest-asyncio` is properly installed
- **Store Command Test**: Fixed `test_init_already_exists` by patching `DEFAULT_STORE_PATH` (evaluated at import time)
- **Test Suite**: Achieved 100% test pass rate (774 passing, 0 failing, 52 skipped)

### Changed
- Updated `uv.lock` to properly include `pytest-asyncio>=1.3.0`

## [8.0.6] - 2026-01-21

### Added
- **Python venv support**: Workflow scripts can now specify dependencies with `@requires` metadata
- Dependencies are automatically installed in isolated virtual environments

## [8.0.3] - 2025-12-28

### Added
- **Native Script Support in Edit Command**: `mcli edit` now supports editing Python and shell scripts directly

### Fixed
- CI/CD pipeline fixes (Bandit security scan, Python version matrix)
- Pre-commit hook cleanup (removed unsupported safety hook)
- Code formatting fixes

## [8.0.0] - 2025-12-22

### Added
- **Simplified CLI Structure**: Cleaner command hierarchy focused on workflow management
- **IPFS Sync**: Decentralized workflow sharing with immutable CIDs
- **Lockfile Management**: Version control for workflows with `commands.lock.json`
- **`mcli sync` command**: Merged lockfile and IPFS sync functionality

### Changed
- Reorganized top-level commands for better UX
- `mcli run` is now the primary command for executing workflows

### Added (2025-10-30)
- **Code Quality Infrastructure**: Complete linting and formatting configuration
  - Added comprehensive `.pylintrc` configuration
  - Enhanced mypy configuration with additional options and optional dependency handling
  - Added `make lint-pylint` target for optional pylint checking
  - Comprehensive linting documentation at `docs/development/LINTING.md`
- **Optional Dependencies**: Graceful handling system for optional dependencies
  - New `mcli/lib/optional_deps.py` utility module with multiple patterns
  - 21 comprehensive unit tests (100% pass rate)
  - Documentation guide at `docs/guides/OPTIONAL_DEPENDENCIES.md`
  - Updated ai_service.py to demonstrate graceful degradation
- **Testing Infrastructure**: Enhanced test infrastructure and documentation
  - Added performance and dependency-specific pytest markers
  - Comprehensive testing guide at `docs/development/TESTING.md`
  - 1,129 tests collecting successfully (847 passing, 75% pass rate)
- **Test Coverage**: Coverage configuration and CI integration
  - Set minimum coverage threshold to 30%
  - Integrated Codecov into CI/CD pipeline
  - Added coverage, CI/CD status, and Python version badges to README
- **Test Command Filtering**: Automatic filtering of test commands
  - Commands starting with `test_` or `test-` are filtered by default
  - `MCLI_INCLUDE_TEST_COMMANDS` environment variable for override
  - 8 comprehensive unit tests
- **Project Documentation**: Standard project documentation files
  - Added `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1)
  - Added `tox.ini` for multi-environment testing (Python 3.9-3.12)
  - Enhanced CI/CD with security scanning (Bandit, Safety, Trivy)
  - Added CodeQL security analysis workflow
  - Added Dependabot configuration for automated dependency updates

### Improved (2025-10-30)
- **Build System**: Cleaned up build artifacts and improved .gitignore
  - Removed all `__pycache__`, pytest cache, dist, and build directories
  - Added `*.vsix` to .gitignore for VS Code extension builds
  - Added repo-cleanup workflow documentation
- **CI/CD Pipeline**: Enhanced security and coverage reporting
  - Coverage reports uploaded to Codecov from all test runs
  - Bandit security linter integrated into CI
  - Safety dependency vulnerability checking
  - Trivy filesystem scanning for CRITICAL and HIGH severity issues
  - Security reports uploaded as artifacts
  - CodeQL analysis running weekly and on PRs

### Documentation (2025-10-30)
- `docs/development/LINTING.md` - Complete linting and code quality guide (400+ lines)
- `docs/development/TESTING.md` - Comprehensive testing guide (500+ lines)
- `docs/guides/OPTIONAL_DEPENDENCIES.md` - Optional dependency handling patterns
- `docs/features/REPO_CLEANUP.md` - Repository cleanup command documentation
- `docs/guides/REPO_CLEANUP_GUIDE.md` - Quick start guide for repo cleanup

### Fixed (2025-10-30)
- Test infrastructure now robust with proper fixtures and markers
- Import errors for optional dependencies handled gracefully
- Test command pollution in production command lists prevented

## [7.9.6] - 2025-10-18

### Improved
- **Document Conversion Workflow**: Enhanced Unicode support and dependency management
  - Switched to XeLaTeX engine for all PDF conversions (better Unicode/emoji handling)
  - Fixed conversion failures for documents containing special characters
  - All fallback strategies now support Unicode characters properly

### Added
- **Cleanup Command**: New `mcli workflow doc-convert cleanup` command
  - Generates uninstall script for all doc-convert dependencies
  - Safe removal with confirmation prompts and warnings
  - Script location: `~/.mcli/commands/doc-convert-cleanup.sh`
  - Removes: pandoc, basictex, LaTeX packages, jupyter, nbconvert

### Changed
- Updated init command documentation to mention XeLaTeX and cleanup command
- Improved conversion success rate for complex documents with Unicode content

### Tested
- Successfully converted 23 UIUC documents (20 IPYNB + 3 HTML files)
- 100% success rate with new XeLaTeX engine
- Verified fallback strategies handle edge cases

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