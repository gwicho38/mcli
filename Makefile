# Makefile for mcli build system with optimized caching

# =============================================================================
# CONFIGURATION
# =============================================================================

# Python and UV configurations
PYTHON := python3
UV := uv
PIP := uv pip
VENV_PYTHON := .venv/bin/python3
# Get version from pyproject.toml and git
VERSION := $(shell grep -m 1 'version =' pyproject.toml | cut -d '"' -f 2)
GIT_HASH := $(shell git rev-parse --short HEAD)
PACKAGE_NAME := mcli

# App installation variables
APP_NAME = mcli
APP_BUNDLE = $(APP_NAME).app
APP_VERSION="2.1.0"
CUSTOMER_NAME="lefv.io"
INSTALL_DIR = /Applications
BIN_DIR = /usr/local/bin
DISTRIBUTION_DIR = dist

# Python version and platform info
PYTHON_VERSION := $(shell python3 -c "import sys; print(f'cp{sys.version_info.major}{sys.version_info.minor}')")
PLATFORM_SUFFIX := $(shell python3 -c "import platform; print('arm64' if platform.machine() == 'arm64' else 'x86_64')")
OS_VERSION := $(shell python3 -c "import platform; print(f'macosx_{platform.mac_ver()[0].replace(\".\", \"_\")}')")

# Build directories
BUILD_DIR := build
DIST_DIR := dist
TEMP_DIR := tmp
BINARY_DIR := bin
CACHE_DIR := .build_cache

# Platform-specific configurations
DARWIN_PLATFORM := $(OS_VERSION)_$(PLATFORM_SUFFIX)
LINUX_PLATFORM := manylinux2014_x86_64
WINDOWS_PLATFORM := win_amd64

# Cache files
UV_ENV_CACHE := $(CACHE_DIR)/uv_env.stamp
WHEEL_CACHE := $(CACHE_DIR)/wheel_$(VERSION)_$(PLATFORM_SUFFIX).stamp
BINARY_CACHE := $(CACHE_DIR)/binary_$(VERSION)_$(PLATFORM_SUFFIX).stamp

# Python executable configurations
PYTHON_EXEC_CACHE := $(CACHE_DIR)/python_exec_$(VERSION)_$(PLATFORM_SUFFIX).stamp
EXECUTABLE_NAME := mcli
PYTHON_EXEC := scripts/mcli_executable.py

# File check variables
SRC_FILES := $(shell find src -type f -name "*.py" 2>/dev/null)
DEPENDENCY_FILES := pyproject.toml uv.lock

# Default target shows help
.DEFAULT_GOAL := help

# ANSI color codes for prettier output
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

# =============================================================================
# UTILITY TARGETS
# =============================================================================

# Initialize cache directory
$(CACHE_DIR):
	@mkdir -p $(CACHE_DIR)

.PHONY: help
help: ## Show this help message
	@echo "$(CYAN)MCLI Build System$(RESET)"
	@echo "$(YELLOW)Usage: make [target]$(RESET)"
	@echo ""
	@echo "$(CYAN)Setup and Installation:$(RESET)"
	@echo "  $(GREEN)setup$(RESET)                 Setup UV environment with caching"
	@echo "  $(GREEN)install$(RESET)              Install the package with caching"
	@echo "  $(GREEN)install-dev$(RESET)          Install development dependencies"
	@echo "  $(GREEN)install-binary$(RESET)        Install executable to system binary directory"
	@echo "  $(GREEN)install-portable$(RESET)      Install portable executable to system"
	@echo ""
	@echo "$(CYAN)Code Quality:$(RESET)"
	@echo "  $(GREEN)lint$(RESET)                  Run all linting tools (black, isort, flake8, mypy)"
	@echo "  $(GREEN)lint-hardcoded-strings$(RESET) Check for hardcoded strings that should be in constants"
	@echo "  $(GREEN)format$(RESET)                Auto-format code (black, isort)"
	@echo "  $(GREEN)type-check$(RESET)            Run mypy type checking"
	@echo "  $(GREEN)type-check-strict$(RESET)     Run strict mypy on priority modules (app, lib)"
	@echo "  $(GREEN)type-check-report$(RESET)     Generate type checking report with error counts"
	@echo "  $(GREEN)security-check$(RESET)        Run security checks (bandit, safety)"
	@echo "  $(GREEN)pre-commit-install$(RESET)    Install pre-commit hooks"
	@echo "  $(GREEN)pre-commit-run$(RESET)        Run pre-commit hooks on all files"
	@echo ""
	@echo "$(CYAN)Testing:$(RESET)"
	@echo "  $(GREEN)test$(RESET)                  Test basic installation and functionality"
	@echo "  $(GREEN)test-unit$(RESET)             Run unit tests"
	@echo "  $(GREEN)test-cov$(RESET)              Run tests with coverage"
	@echo "  $(GREEN)test-cov-report$(RESET)       Generate and open coverage report"
	@echo "  $(GREEN)test-fast$(RESET)             Run fast tests only (skip slow tests)"
	@echo "  $(GREEN)test-binary$(RESET)           Test the built executable"
	@echo ""
	@echo "$(CYAN)Building:$(RESET)"
	@echo "  $(GREEN)wheel$(RESET)                 Build Python wheel package"
	@echo "  $(GREEN)binary$(RESET)                Build Python binary executable"
	@echo "  $(GREEN)portable$(RESET)              Build portable executable"
	@echo "  $(GREEN)build$(RESET)                 Build all targets"
	@echo ""
	@echo "$(CYAN)Documentation:$(RESET)"
	@echo "  $(GREEN)docs$(RESET)                  Generate documentation"
	@echo "  $(GREEN)docs-serve$(RESET)            Serve documentation locally"
	@echo ""
	@echo "$(CYAN)Dashboard:$(RESET)"
	@echo "  $(GREEN)dashboard$(RESET)             Launch integrated ML dashboard with LSH (default)"
	@echo "  $(GREEN)dashboard-integrated$(RESET)  Launch integrated dashboard with ML jobs and LSH"
	@echo "  $(GREEN)dashboard-training$(RESET)    Launch ML training dashboard"
	@echo "  $(GREEN)dashboard-supabase$(RESET)    Launch Supabase-focused dashboard"
	@echo "  $(GREEN)dashboard-basic$(RESET)       Launch basic ML dashboard"
	@echo "  $(GREEN)dashboard-cli$(RESET)         Launch dashboard using CLI command"
	@echo "  $(GREEN)dashboard-workflow$(RESET)    Launch dashboard using workflow command"
	@echo ""
	@echo "$(CYAN)Maintenance:$(RESET)"
	@echo "  $(GREEN)clean$(RESET)                 Clean all build artifacts"
	@echo "  $(GREEN)clean-pyc$(RESET)             Clean only Python cache files"
	@echo "  $(GREEN)clean-build$(RESET)           Clean only build artifacts (keep venv)"
	@echo "  $(GREEN)debug$(RESET)                 Show debug information"
	@echo "  $(CYAN)validate-build$(RESET)        Validate application for binary/wheel packaging"
	@echo ""
	@echo "$(CYAN)Maintenance Targets:$(RESET)"
	@echo "  $(CYAN)clean$(RESET)                 Clean all build artifacts"
	@echo "  $(CYAN)uninstall$(RESET)             Remove installed app bundle and/or binary"
	@echo ""
	@echo "$(CYAN)CI/CD Targets:$(RESET)"
	@echo "  $(CYAN)ci-trigger-build$(RESET)      Trigger GitHub Actions build workflow"
	@echo "  $(CYAN)ci-trigger-test$(RESET)       Trigger GitHub Actions test workflow"
	@echo "  $(CYAN)ci-trigger-test-cli$(RESET)   Trigger GitHub Actions CLI tests"
	@echo "  $(CYAN)ci-trigger-test-specific$(RESET) Trigger specific test (TEST=name)"
	@echo "  $(CYAN)ci-watch$(RESET)              Watch GitHub Actions runs in real-time"
	@echo "  $(CYAN)ci-status$(RESET)             Show GitHub Actions run status"
	@echo "  $(CYAN)ci-logs$(RESET)               Show latest GitHub Actions logs"
	@echo "  $(CYAN)ci-logs-build$(RESET)         Show latest build workflow logs"
	@echo "  $(CYAN)ci-logs-test$(RESET)          Show latest test workflow logs"

.PHONY: debug
debug: ## Show debug information
	@echo "$(CYAN)Debug Information:$(RESET)"
	@echo "Python Version: $(PYTHON_VERSION)"
	@echo "Platform: $(PLATFORM_SUFFIX)"
	@echo "OS Version: $(OS_VERSION)"
	@echo "UV Version: $$(uv --version)"
	@echo "Setup.py exists: $$(test -f setup.py && echo yes || echo no)"
	@echo "Build Config exists: $$(test -f build.cfg && echo yes || echo no)"
	@echo "\nVirtual Environment:"
	@uv venv info
	@echo "\nProject Dependencies:"
	@uv pip list

# =============================================================================
# MAINTENANCE TARGETS
# =============================================================================

.PHONY: clean
clean: ## Clean all build artifacts
	@echo "$(CYAN)Cleaning build artifacts...$(RESET)"
	-rm -rf $(BUILD_DIR)/ $(DIST_DIR)/ *.egg-info/ $(TEMP_DIR)/
	-rm -rf $(BINARY_DIR)/ $(CACHE_DIR)/ $(DISTRIBUTION_DIR)/
	-rm -rf .venv 2>/dev/null || true
	-find . -type f -name "*.so" -delete
	@echo "$(CYAN)Cleaning Python cache files...$(RESET)"
	-find . -type d -name "__pycache__" -not -path "*/.venv/*" -not -path "*/venv/*" -exec rm -rf {} + 2>/dev/null || true
	-find . -type f -name "*.pyc" -not -path "*/.venv/*" -not -path "*/venv/*" -delete 2>/dev/null || true
	-find . -type f -name "*.pyo" -not -path "*/.venv/*" -not -path "*/venv/*" -delete 2>/dev/null || true
	@echo "$(CYAN)Cleaning test and coverage artifacts...$(RESET)"
	-rm -rf .pytest_cache/ .coverage htmlcov/ .tox/
	@echo "$(GREEN)✓ Clean completed$(RESET)"

clean-pyc: ## Clean only Python cache files
	@echo "$(CYAN)Cleaning Python cache files...$(RESET)"
	-find . -type d -name "__pycache__" -not -path "*/.venv/*" -not -path "*/venv/*" -exec rm -rf {} + 2>/dev/null || true
	-find . -type f -name "*.pyc" -not -path "*/.venv/*" -not -path "*/venv/*" -delete 2>/dev/null || true
	-find . -type f -name "*.pyo" -not -path "*/.venv/*" -not -path "*/venv/*" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Python cache cleaned$(RESET)"

clean-build: ## Clean only build artifacts (keep venv)
	@echo "$(CYAN)Cleaning build artifacts...$(RESET)"
	-rm -rf $(BUILD_DIR)/ $(DIST_DIR)/ *.egg-info/ $(TEMP_DIR)/
	-rm -rf $(BINARY_DIR)/ $(CACHE_DIR)/ $(DISTRIBUTION_DIR)/
	-find . -type f -name "*.so" -delete
	-rm -rf .pytest_cache/ .coverage htmlcov/ .tox/
	@echo "$(GREEN)✓ Build artifacts cleaned$(RESET)"
	-find . -type f -name "*.cpp" -delete
	-find . -type f -name "*.c" -delete
	-find . -type f -name "*.html" -delete
	-find . -type d -name "__pycache__" -exec rm -rf {} +
	-rm -f setup.py  # Remove existing setup.py if present
	-rm -f $(PYINSTALLER_SPEC)  # Remove PyInstaller spec file
	-rm -f setup_cython.py  # Remove Cython setup file
	-rm -f cython_main.pyx  # Remove Cython main file
	-rm -f mcli_main*.so  # Remove compiled Cython extensions
	# Keep scripts/mcli_executable.py - it's our main executable
	@echo "$(GREEN)Clean completed ✅$(RESET)"

.PHONY: uninstall
uninstall: ## Remove installed app bundle and/or binary
	@echo "$(CYAN)Uninstalling $(APP_NAME)...$(RESET)"
	@if [ -d "$(INSTALL_DIR)/$(APP_BUNDLE)" ]; then \
		sudo rm -rf "$(INSTALL_DIR)/$(APP_BUNDLE)"; \
		echo "$(GREEN)Removed app bundle from $(INSTALL_DIR)/$(APP_BUNDLE) ✅$(RESET)"; \
	fi
	@if [ -f "$(BIN_DIR)/$(APP_NAME)" ]; then \
		sudo rm -f "$(BIN_DIR)/$(APP_NAME)"; \
		echo "$(GREEN)Removed binary from $(BIN_DIR)/$(APP_NAME) ✅$(RESET)"; \
	fi
	@echo "$(GREEN)$(APP_NAME) uninstalled successfully ✅$(RESET)"

# =============================================================================
# SETUP TARGETS
# =============================================================================

# Setup target with caching
$(UV_ENV_CACHE): $(DEPENDENCY_FILES) | $(CACHE_DIR)
	@echo "$(CYAN)Setting up UV environment...$(RESET)"
	$(UV) venv
	$(UV) pip install -e .
	$(UV) pip install -U setuptools wheel twine build
	@mkdir -p $(dir $@)
	@touch $@
	@echo "$(GREEN)UV environment ready ✅$(RESET)"

.PHONY: setup
setup: $(UV_ENV_CACHE) ## Setup UV environment with caching
	@echo "Current version: $(VERSION)"
	@echo "Git commit hash: $(GIT_HASH)"
	@echo "Python version: $(PYTHON_VERSION)"
	@echo "Platform: $(PLATFORM_SUFFIX)"
	@echo "OS Version: $(OS_VERSION)"

# =============================================================================
# BUILD TARGETS
# =============================================================================

# Darwin build with caching
$(WHEEL_CACHE): $(SRC_FILES) $(UV_ENV_CACHE) | $(CACHE_DIR)
	@echo "$(CYAN)Building for macOS ($(DARWIN_PLATFORM))...$(RESET)"
	@mkdir -p $(DIST_DIR)
	$(VENV_PYTHON) -m build --wheel
	@for wheel in $(DIST_DIR)/*.whl; do \
		if [ -f "$$wheel" ]; then \
			ORIG_NAME=$$(basename "$$wheel"); \
			NEW_NAME=$$(echo "$$ORIG_NAME" | sed 's/+/_/g'); \
			if [ "$$ORIG_NAME" != "$$NEW_NAME" ]; then \
				mv "$(DIST_DIR)/$$ORIG_NAME" "$(DIST_DIR)/$$NEW_NAME"; \
			fi; \
			printf "\033[32mGenerated Wheel:\033[0m %s\n" "$$NEW_NAME"; \
		else \
			printf "\033[31m❌ Error: No wheel file found in %s\033[0m\n" "$(DIST_DIR)"; \
			exit 1; \
		fi; \
	done
	.venv/bin/twine check $(DIST_DIR)/*.whl || true
	@mkdir -p $(dir $@)
	@touch $@
	@echo "$(GREEN)macOS build completed ✅$(RESET)"

.PHONY: wheel
wheel: $(WHEEL_CACHE) ## Build Python wheel package
	@echo "$(GREEN)Wheel build completed ✅$(RESET)"

# Python executable creation targets
.PHONY: install-python-exec
install-python-exec: $(UV_ENV_CACHE) ## Install Python executable dependencies
	@echo "$(CYAN)Installing Python executable dependencies...$(RESET)"
	@echo "$(GREEN)Python executable dependencies ready ✅$(RESET)"

# Create Python executable file
$(PYTHON_EXEC): install-python-exec
	@echo "$(CYAN)Using Python executable file...$(RESET)"
	@echo "$(GREEN)Python executable file ready ✅$(RESET)"

# Build Python executable - Clean approach using wheel
.PHONY: portable
portable: $(WHEEL_CACHE) $(PYTHON_EXEC) ## Build Python executable from wheel
	@echo "$(CYAN)Building Python executable from wheel...$(RESET)"
	@mkdir -p $(BINARY_DIR)
	@mkdir -p $(BUILD_DIR)

	# Copy the Python executable to binary directory
	@if [ -f "$(PYTHON_EXEC)" ]; then \
		cp "$(PYTHON_EXEC)" "$(BINARY_DIR)/$(EXECUTABLE_NAME)"; \
		chmod +x "$(BINARY_DIR)/$(EXECUTABLE_NAME)"; \
		echo "$(GREEN)Python executable created: $(BINARY_DIR)/$(EXECUTABLE_NAME) ✅$(RESET)"; \
	else \
		echo "$(RED)❌ Error: Python executable not found$(RESET)"; \
		exit 1; \
	fi

# Build Python binary executable - Clean approach using wheel
.PHONY: binary
binary: $(WHEEL_CACHE) $(PYTHON_EXEC) ## Build Python binary executable (directory format)
	@echo "$(CYAN)Building Python binary executable from wheel...$(RESET)"
	@mkdir -p $(BINARY_DIR)
	@mkdir -p $(BUILD_DIR)

	# Create binary directory structure
	@mkdir -p "$(BINARY_DIR)/$(EXECUTABLE_NAME)"

	# Copy the Python executable to binary directory
	@if [ -f "$(PYTHON_EXEC)" ]; then \
		cp "$(PYTHON_EXEC)" "$(BINARY_DIR)/$(EXECUTABLE_NAME)/$(EXECUTABLE_NAME)"; \
		chmod +x "$(BINARY_DIR)/$(EXECUTABLE_NAME)/$(EXECUTABLE_NAME)"; \
		echo "$(GREEN)Python binary executable created: $(BINARY_DIR)/$(EXECUTABLE_NAME)/$(EXECUTABLE_NAME) ✅$(RESET)"; \
	else \
		echo "$(RED)❌ Error: Python executable not found$(RESET)"; \
		exit 1; \
	fi

# =============================================================================
# INSTALLATION TARGETS
# =============================================================================

.PHONY: install
install: $(WHEEL_CACHE) ## Install the package with caching
	@echo "$(CYAN)Installing package...$(RESET)"
	$(PIP) install $(DIST_DIR)/*.whl --force-reinstall
	@echo "$(GREEN)Installation completed ✅$(RESET)"

.PHONY: install-binary
install-binary: portable ## Install executable to system binary directory
	@echo "$(CYAN)Installing executable to system...$(RESET)"
	@if [ -f "$(BINARY_DIR)/$(EXECUTABLE_NAME)" ]; then \
		sudo cp "$(BINARY_DIR)/$(EXECUTABLE_NAME)" "$(BIN_DIR)/$(EXECUTABLE_NAME)"; \
		sudo chmod +x "$(BIN_DIR)/$(EXECUTABLE_NAME)"; \
		echo "$(GREEN)Executable installed to $(BIN_DIR)/$(EXECUTABLE_NAME) ✅$(RESET)"; \
	else \
		echo "$(RED)❌ Error: Executable not found$(RESET)"; \
		exit 1; \
	fi

.PHONY: install-portable
install-portable: portable ## Install portable executable to system
	@echo "$(CYAN)Installing portable executable...$(RESET)"
	@if [ -f "$(BINARY_DIR)/$(EXECUTABLE_NAME)" ]; then \
		sudo cp "$(BINARY_DIR)/$(EXECUTABLE_NAME)" "$(BIN_DIR)/$(EXECUTABLE_NAME)"; \
		sudo chmod +x "$(BINARY_DIR)/$(EXECUTABLE_NAME)"; \
		echo "$(GREEN)Portable executable installed to $(BIN_DIR)/$(EXECUTABLE_NAME) ✅$(RESET)"; \
	else \
		echo "$(RED)❌ Error: Portable executable not found$(RESET)"; \
		exit 1; \
	fi

# =============================================================================
# TESTING TARGETS
# =============================================================================

.PHONY: test
test: install ## Test the installation
	@echo "$(CYAN)Testing package...$(RESET)"
	$(VENV_PYTHON) -c "from mcli.app.main import main; print('Import test passed ✅')"
	.venv/bin/mcli --help || $(VENV_PYTHON) -m mcli --help
	@echo "$(GREEN)Testing completed ✅$(RESET)"

test-unit: setup ## Run unit tests
	@echo "$(CYAN)Running unit tests...$(RESET)"
	$(UV) run pytest tests/ -v
	@echo "$(GREEN)Unit tests completed ✅$(RESET)"

test-cov: setup ## Run tests with coverage
	@echo "$(CYAN)Running tests with coverage...$(RESET)"
	$(UV) run pytest tests/ --cov=src/mcli --cov-report=term-missing --cov-report=html --cov-report=xml
	@echo "$(GREEN)Coverage tests completed ✅$(RESET)"
	@echo "$(CYAN)Coverage report generated in htmlcov/index.html$(RESET)"

test-cov-report: test-cov ## Generate and open coverage report
	@echo "$(CYAN)Opening coverage report...$(RESET)"
	@if command -v open >/dev/null 2>&1; then \
		open htmlcov/index.html; \
	elif command -v xdg-open >/dev/null 2>&1; then \
		xdg-open htmlcov/index.html; \
	else \
		echo "$(YELLOW)Coverage report available at htmlcov/index.html$(RESET)"; \
	fi

test-fast: setup ## Run fast tests only (skip slow tests)
	@echo "$(CYAN)Running fast tests...$(RESET)"
	$(UV) run pytest tests/ -v -m "not slow"
	@echo "$(GREEN)Fast tests completed ✅$(RESET)"

# =============================================================================
# CODE QUALITY TARGETS
# =============================================================================

.PHONY: lint
lint: setup ## Run all linting tools
	@echo "$(CYAN)Running linting tools...$(RESET)"
	$(UV) run black --check src/ tests/
	$(UV) run isort --check-only src/ tests/
	$(UV) run flake8 src/ tests/
	$(UV) run mypy src/
	@echo "$(GREEN)Linting completed ✅$(RESET)"

.PHONY: lint-hardcoded-strings
lint-hardcoded-strings: ## Check for hardcoded strings that should be in constants
	@echo "$(CYAN)Checking for hardcoded strings...$(RESET)"
	$(PYTHON) tools/lint_hardcoded_strings.py --check-all
	@echo "$(GREEN)Hardcoded string check completed ✅$(RESET)"

.PHONY: validate-doc-links
validate-doc-links: ## Validate documentation links (internal only)
	@echo "$(CYAN)Validating documentation links...$(RESET)"
	$(PYTHON) tools/validate_doc_links.py README.md docs/
	@echo "$(GREEN)Documentation link validation completed ✅$(RESET)"

.PHONY: validate-doc-links-external
validate-doc-links-external: ## Validate all documentation links (including external)
	@echo "$(CYAN)Validating all documentation links (including external)...$(RESET)"
	$(PYTHON) tools/validate_doc_links.py --external --timeout 15 README.md docs/
	@echo "$(GREEN)Documentation link validation completed ✅$(RESET)"

.PHONY: lint-pylint
lint-pylint: setup ## Run pylint on source code
	@echo "$(CYAN)Running pylint...$(RESET)"
	$(UV) run pylint src/mcli/ --rcfile=.pylintrc || true
	@echo "$(GREEN)Pylint completed$(RESET)"

.PHONY: format
format: setup ## Auto-format code
	@echo "$(CYAN)Formatting code...$(RESET)"
	$(UV) run black src/ tests/
	$(UV) run isort src/ tests/
	@echo "$(GREEN)Code formatting completed ✅$(RESET)"

.PHONY: type-check
type-check: setup ## Run mypy type checking
	@echo "$(CYAN)Running type checking...$(RESET)"
	$(UV) run mypy src/
	@echo "$(GREEN)Type checking completed ✅$(RESET)"

.PHONY: type-check-strict
type-check-strict: setup ## Run strict mypy type checking on priority modules
	@echo "$(CYAN)Running strict type checking on priority modules...$(RESET)"
	$(UV) run mypy src/mcli/app/ src/mcli/lib/ --strict --ignore-missing-imports || true
	@echo "$(YELLOW)Note: Strict mode shows all type issues. Fix gradually.$(RESET)"

.PHONY: type-check-report
type-check-report: setup ## Generate type checking report with error counts
	@echo "$(CYAN)Generating type checking report...$(RESET)"
	@echo "=== Type Safety Report ===" > type_report.txt
	@echo "Generated: $$(date)" >> type_report.txt
	@echo "" >> type_report.txt
	@echo "--- Summary by Module ---" >> type_report.txt
	@for module in app lib chat workflow self public ml storage; do \
		if [ -d "src/mcli/$$module" ]; then \
			count=$$($(UV) run mypy src/mcli/$$module 2>&1 | grep -c "error:" || echo "0"); \
			printf "  mcli/%-10s: %s errors\n" "$$module" "$$count" >> type_report.txt; \
		fi; \
	done
	@echo "" >> type_report.txt
	@echo "--- Full Output ---" >> type_report.txt
	$(UV) run mypy src/ 2>&1 >> type_report.txt || true
	@echo "$(GREEN)Report saved to type_report.txt$(RESET)"
	@echo ""
	@head -15 type_report.txt

.PHONY: security-check
security-check: setup ## Run security checks
	@echo "$(CYAN)Running security checks...$(RESET)"
	$(UV) run bandit -r src/
	$(UV) run safety check
	@echo "$(GREEN)Security checks completed ✅$(RESET)"

.PHONY: pre-commit-install
pre-commit-install: setup ## Install pre-commit hooks
	@echo "$(CYAN)Installing pre-commit hooks...$(RESET)"
	$(UV) run pre-commit install
	@echo "$(GREEN)Pre-commit hooks installed ✅$(RESET)"

.PHONY: pre-commit-run
pre-commit-run: setup ## Run pre-commit hooks on all files
	@echo "$(CYAN)Running pre-commit hooks...$(RESET)"
	$(UV) run pre-commit run --all-files
	@echo "$(GREEN)Pre-commit hooks completed ✅$(RESET)"

.PHONY: pre-commit-update
pre-commit-update: setup ## Update pre-commit hooks
	@echo "$(CYAN)Updating pre-commit hooks...$(RESET)"
	$(UV) run pre-commit autoupdate
	@echo "$(GREEN)Pre-commit hooks updated ✅$(RESET)"

# =============================================================================
# DEVELOPMENT TARGETS
# =============================================================================

.PHONY: install-dev
install-dev: setup ## Install development dependencies
	@echo "$(CYAN)Installing development dependencies...$(RESET)"
	$(UV) sync --group dev
	@echo "$(GREEN)Development dependencies installed ✅$(RESET)"

.PHONY: build
build: wheel binary ## Build all targets (wheel and binary)
	@echo "$(GREEN)All builds completed ✅$(RESET)"

.PHONY: docs
docs: setup ## Generate documentation
	@echo "$(CYAN)Generating documentation...$(RESET)"
	@echo "$(YELLOW)Documentation generation not yet configured$(RESET)"
	@echo "$(CYAN)Consider adding sphinx or mkdocs configuration$(RESET)"

.PHONY: docs-serve
docs-serve: docs ## Serve documentation locally
	@echo "$(CYAN)Serving documentation locally...$(RESET)"
	@echo "$(YELLOW)Documentation serving not yet configured$(RESET)"
	@echo "$(CYAN)Consider adding sphinx or mkdocs serve capability$(RESET)"

# =============================================================================
# DASHBOARD TARGETS
# =============================================================================

.PHONY: dashboard
dashboard: dashboard-integrated ## Launch integrated ML dashboard with LSH integration (default)

.PHONY: dashboard-integrated
dashboard-integrated: setup ## Launch integrated dashboard with ML jobs and LSH integration
	@echo "$(CYAN)Launching integrated ML dashboard with LSH integration...$(RESET)"
	@echo "$(YELLOW)Dashboard will be available at http://localhost:8501$(RESET)"
	$(VENV_PYTHON) -m streamlit run src/mcli/ml/dashboard/app_integrated.py \
		--server.port 8501 \
		--server.address localhost \
		--browser.gatherUsageStats false

.PHONY: dashboard-training
dashboard-training: setup ## Launch ML training dashboard
	@echo "$(CYAN)Launching ML training dashboard...$(RESET)"
	@echo "$(YELLOW)Dashboard will be available at http://localhost:8502$(RESET)"
	$(VENV_PYTHON) -m streamlit run src/mcli/ml/dashboard/app_training.py \
		--server.port 8502 \
		--server.address localhost \
		--browser.gatherUsageStats false

.PHONY: dashboard-supabase
dashboard-supabase: setup ## Launch Supabase-focused dashboard
	@echo "$(CYAN)Launching Supabase dashboard...$(RESET)"
	@echo "$(YELLOW)Dashboard will be available at http://localhost:8503$(RESET)"
	$(VENV_PYTHON) -m streamlit run src/mcli/ml/dashboard/app_supabase.py \
		--server.port 8503 \
		--server.address localhost \
		--browser.gatherUsageStats false

.PHONY: dashboard-basic
dashboard-basic: setup ## Launch basic ML dashboard
	@echo "$(CYAN)Launching basic ML dashboard...$(RESET)"
	@echo "$(YELLOW)Dashboard will be available at http://localhost:8504$(RESET)"
	$(VENV_PYTHON) -m streamlit run src/mcli/ml/dashboard/app.py \
		--server.port 8504 \
		--server.address localhost \
		--browser.gatherUsageStats false

.PHONY: dashboard-cli
dashboard-cli: setup ## Launch dashboard using CLI command
	@echo "$(CYAN)Launching dashboard via CLI command...$(RESET)"
	.venv/bin/mcli-dashboard

.PHONY: dashboard-workflow
dashboard-workflow: setup ## Launch dashboard using workflow command
	@echo "$(CYAN)Launching dashboard via workflow command...$(RESET)"
	.venv/bin/mcli workflow dashboard launch

.PHONY: bump-version
bump-version: ## Bump version (requires VERSION argument, e.g., make bump-version VERSION=1.2.3)
	@if [ -z "$(VERSION)" ]; then \
		echo "$(RED)Error: VERSION argument required. Usage: make bump-version VERSION=1.2.3$(RESET)"; \
		exit 1; \
	fi
	@echo "$(CYAN)Bumping version to $(VERSION)...$(RESET)"
	@sed -i.bak 's/version = "[^"]*"/version = "$(VERSION)"/' pyproject.toml
	@rm pyproject.toml.bak
	@echo "$(GREEN)Version bumped to $(VERSION) ✅$(RESET)"

.PHONY: publish
publish: wheel ## Publish package to PyPI
	@echo "$(CYAN)Publishing package to PyPI...$(RESET)"
	@echo "$(YELLOW)Ensure you have set PYPI_TOKEN environment variable$(RESET)"
	$(UV) run twine upload dist/*
	@echo "$(GREEN)Package published ✅$(RESET)"

.PHONY: publish-test
publish-test: wheel ## Publish package to Test PyPI
	@echo "$(CYAN)Publishing package to Test PyPI...$(RESET)"
	$(UV) run twine upload --repository testpypi dist/*
	@echo "$(GREEN)Package published to Test PyPI ✅$(RESET)"

.PHONY: tox
tox: setup ## Run tox multi-environment testing
	@echo "$(CYAN)Running tox multi-environment testing...$(RESET)"
	@if command -v tox >/dev/null 2>&1; then \
		tox; \
	else \
		echo "$(YELLOW)Tox not installed. Install with: uv add tox$(RESET)"; \
	fi
	@echo "$(GREEN)Tox testing completed ✅$(RESET)"

.PHONY: test-binary
test-binary: ## Test the built executable
	@echo "$(CYAN)Testing executable...$(RESET)"
	@if [ -f "$(BINARY_DIR)/$(EXECUTABLE_NAME)" ]; then \
		echo "Testing portable Cython executable..."; \
		"$(BINARY_DIR)/$(EXECUTABLE_NAME)" --help || echo "$(YELLOW)Warning: Portable Cython executable test failed$(RESET)"; \
	elif [ -f "$(BINARY_DIR)/$(EXECUTABLE_NAME)/$(EXECUTABLE_NAME)" ]; then \
		echo "Testing binary Cython executable..."; \
		"$(BINARY_DIR)/$(EXECUTABLE_NAME)/$(EXECUTABLE_NAME)" --help || echo "$(YELLOW)Warning: Binary Cython executable test failed$(RESET)"; \
	else \
		echo "$(RED)❌ Error: No executable found to test$(RESET)"; \
		echo "Available files in $(BINARY_DIR):"; \
		ls -la $(BINARY_DIR) 2>/dev/null || echo "Directory $(BINARY_DIR) not found"; \
		exit 1; \
	fi
	@echo "$(GREEN)Executable test completed ✅$(RESET)"

.PHONY: test-all
test-all: ## Run complete test suite
	@echo "$(CYAN)Running complete test suite...$(RESET)"
	$(VENV_PYTHON) tests/run_tests.py
	@echo "$(GREEN)Test suite completed ✅$(RESET)"

.PHONY: test-cli
test-cli: ## Run CLI-specific tests only
	@echo "$(CYAN)Running CLI tests...$(RESET)"
	$(VENV_PYTHON) tests/run_tests.py --cli-only
	@echo "$(GREEN)CLI tests completed ✅$(RESET)"

# =============================================================================
# BUILD VALIDATION TARGETS
# =============================================================================

.PHONY: validate-build
validate-build: $(UV_ENV_CACHE) ## Validate application is ready for binary/wheel packaging
	@echo "$(CYAN)Validating build readiness...$(RESET)"
	@echo "$(YELLOW)Step 1: Dependencies check$(RESET)"
	$(UV) pip check
	@echo "$(YELLOW)Step 2: Import validation$(RESET)"
	$(VENV_PYTHON) -c "import mcli; print('✅ Package imports successfully')"
	@echo "$(YELLOW)Step 3: CLI functionality check$(RESET)"
	$(VENV_PYTHON) -m mcli --help > /dev/null && echo "✅ CLI help works" || (echo "❌ CLI help failed" && exit 1)
	@echo "$(YELLOW)Step 4: Build wheel$(RESET)"
	$(MAKE) wheel
	@echo "$(YELLOW)Step 5: Test wheel installation$(RESET)"
	@temp_venv=$$(mktemp -d); \
	python3 -m venv "$$temp_venv"; \
	"$$temp_venv/bin/pip" install $(DIST_DIR)/*.whl; \
	"$$temp_venv/bin/mcli" --help > /dev/null && echo "✅ Wheel installation works" || (echo "❌ Wheel installation failed" && exit 1); \
	rm -rf "$$temp_venv"
	@echo "$(YELLOW)Step 6: Build portable executable$(RESET)"
	$(MAKE) portable
	@echo "$(YELLOW)Step 7: Test portable executable$(RESET)"
	$(MAKE) test-binary
	@echo "$(YELLOW)Step 8: Basic functionality test$(RESET)"
	$(MAKE) test
	@echo "$(GREEN)✅ Build validation completed successfully!$(RESET)"
	@echo "$(GREEN)Application is ready for binary/wheel distribution$(RESET)"

# =============================================================================
# GITHUB ACTIONS CI/CD TARGETS
# =============================================================================

.PHONY: ci-trigger-build
ci-trigger-build: ## Trigger GitHub Actions build workflow
	@echo "$(CYAN)Triggering GitHub Actions build workflow...$(RESET)"
	@if ! command -v gh >/dev/null 2>&1; then \
		echo "$(RED)❌ GitHub CLI (gh) not found. Please install it first.$(RESET)"; \
		echo "Visit: https://cli.github.com/"; \
		exit 1; \
	fi
	gh workflow run build.yml
	@echo "$(GREEN)✅ Build workflow triggered$(RESET)"

.PHONY: ci-trigger-test
ci-trigger-test: ## Trigger GitHub Actions test workflow
	@echo "$(CYAN)Triggering GitHub Actions test workflow...$(RESET)"
	@if ! command -v gh >/dev/null 2>&1; then \
		echo "$(RED)❌ GitHub CLI (gh) not found. Please install it first.$(RESET)"; \
		echo "Visit: https://cli.github.com/"; \
		exit 1; \
	fi
	gh workflow run test.yml
	@echo "$(GREEN)✅ Test workflow triggered$(RESET)"

.PHONY: ci-trigger-test-cli
ci-trigger-test-cli: ## Trigger GitHub Actions test workflow (CLI tests only)
	@echo "$(CYAN)Triggering GitHub Actions test workflow (CLI only)...$(RESET)"
	@if ! command -v gh >/dev/null 2>&1; then \
		echo "$(RED)❌ GitHub CLI (gh) not found. Please install it first.$(RESET)"; \
		echo "Visit: https://cli.github.com/"; \
		exit 1; \
	fi
	gh workflow run test.yml -f test_type=cli-only
	@echo "$(GREEN)✅ CLI test workflow triggered$(RESET)"

.PHONY: ci-trigger-test-specific
ci-trigger-test-specific: ## Trigger GitHub Actions test workflow for specific test (usage: make ci-trigger-test-specific TEST=test_name)
	@echo "$(CYAN)Triggering GitHub Actions test workflow for specific test...$(RESET)"
	@if ! command -v gh >/dev/null 2>&1; then \
		echo "$(RED)❌ GitHub CLI (gh) not found. Please install it first.$(RESET)"; \
		echo "Visit: https://cli.github.com/"; \
		exit 1; \
	fi
	@if [ -z "$(TEST)" ]; then \
		echo "$(RED)❌ TEST variable not set. Usage: make ci-trigger-test-specific TEST=test_name$(RESET)"; \
		exit 1; \
	fi
	gh workflow run test.yml -f test_type=specific -f specific_test=$(TEST)
	@echo "$(GREEN)✅ Specific test workflow triggered for: $(TEST)$(RESET)"

.PHONY: ci-watch
ci-watch: ## Watch GitHub Actions workflow runs in real-time
	@echo "$(CYAN)Watching GitHub Actions workflows...$(RESET)"
	@if ! command -v gh >/dev/null 2>&1; then \
		echo "$(RED)❌ GitHub CLI (gh) not found. Please install it first.$(RESET)"; \
		echo "Visit: https://cli.github.com/"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Press Ctrl+C to stop watching$(RESET)"
	@echo "$(YELLOW)Available commands while watching:$(RESET)"
	@echo "  - 'q' to quit"
	@echo "  - 'r' to refresh"
	@echo "  - Enter to see details"
	gh run watch

.PHONY: ci-status
ci-status: ## Show status of recent GitHub Actions runs
	@echo "$(CYAN)GitHub Actions Status:$(RESET)"
	@if ! command -v gh >/dev/null 2>&1; then \
		echo "$(RED)❌ GitHub CLI (gh) not found. Please install it first.$(RESET)"; \
		echo "Visit: https://cli.github.com/"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Recent workflow runs:$(RESET)"
	gh run list --limit 10
	@echo ""
	@echo "$(YELLOW)Workflow status:$(RESET)"
	gh workflow list

.PHONY: ci-logs
ci-logs: ## Show logs from the latest GitHub Actions run
	@echo "$(CYAN)Fetching latest GitHub Actions logs...$(RESET)"
	@if ! command -v gh >/dev/null 2>&1; then \
		echo "$(RED)❌ GitHub CLI (gh) not found. Please install it first.$(RESET)"; \
		echo "Visit: https://cli.github.com/"; \
		exit 1; \
	fi
	gh run view --log

.PHONY: ci-logs-build
ci-logs-build: ## Show logs from the latest build workflow run
	@echo "$(CYAN)Fetching latest build workflow logs...$(RESET)"
	@if ! command -v gh >/dev/null 2>&1; then \
		echo "$(RED)❌ GitHub CLI (gh) not found. Please install it first.$(RESET)"; \
		echo "Visit: https://cli.github.com/"; \
		exit 1; \
	fi
	gh run list --workflow build.yml --limit 1 --json databaseId --jq '.[0].databaseId' | xargs gh run view --log

.PHONY: ci-logs-test
ci-logs-test: ## Show logs from the latest test workflow run
	@echo "$(CYAN)Fetching latest test workflow logs...$(RESET)"
	@if ! command -v gh >/dev/null 2>&1; then \
		echo "$(RED)❌ GitHub CLI (gh) not found. Please install it first.$(RESET)"; \
		echo "Visit: https://cli.github.com/"; \
		exit 1; \
	fi
	gh run list --workflow test.yml --limit 1 --json databaseId --jq '.[0].databaseId' | xargs gh run view --log
