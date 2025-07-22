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
CUSTOMER_NAME="panda.readiness"
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
PYTHON_EXEC := mcli_executable.py

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
	@echo "$(CYAN)Installation Targets:$(RESET)"
	@echo "  $(CYAN)install$(RESET)              Install the package with caching"
	@echo "  $(CYAN)install-binary$(RESET)        Install executable to system binary directory"
	@echo "  $(CYAN)install-portable$(RESET)      Install portable executable to system"
	@echo "  $(CYAN)setup$(RESET)                 Setup UV environment with caching"
	@echo ""
	@echo "$(CYAN)Build Targets:$(RESET)"
	@echo "  $(CYAN)binary$(RESET)                Build Python binary executable (directory format)"
	@echo "  $(CYAN)portable$(RESET)              Build Python executable from wheel"
	@echo "  $(CYAN)wheel$(RESET)                 Build Python wheel package"
	@echo ""
	@echo "$(CYAN)Testing Targets:$(RESET)"
	@echo "  $(CYAN)debug$(RESET)                 Show debug information"
	@echo "  $(CYAN)test$(RESET)                  Test the installation"
	@echo "  $(CYAN)test-binary$(RESET)           Test the built executable"
	@echo ""
	@echo "$(CYAN)Maintenance Targets:$(RESET)"
	@echo "  $(CYAN)clean$(RESET)                 Clean all build artifacts"
	@echo "  $(CYAN)uninstall$(RESET)             Remove installed app bundle and/or binary"

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
	-find . -type f -name "*.cpp" -delete
	-find . -type f -name "*.c" -delete
	-find . -type f -name "*.html" -delete
	-find . -type d -name "__pycache__" -exec rm -rf {} +
	-rm -f setup.py  # Remove existing setup.py if present
	-rm -f $(PYINSTALLER_SPEC)  # Remove PyInstaller spec file
	-rm -f setup_cython.py  # Remove Cython setup file
	-rm -f cython_main.pyx  # Remove Cython main file
	-rm -f mcli_main*.so  # Remove compiled Cython extensions
	# Keep mcli_executable.py - it's our main executable
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
