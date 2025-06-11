# Makefile for mcli build system with optimized caching

# Python and UV configurations
PYTHON := python3
UV := uv
PIP := uv pip
VENV_PYTHON := .venv/bin/python3
# Get version from pyproject.toml and git
VERSION := $(shell grep -m 1 'version =' pyproject.toml | cut -d '"' -f 2)
GIT_HASH := $(shell git rev-parse --short HEAD)
PACKAGE_NAME := mcli

# New variables for app installation
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

# Initialize cache directory
$(CACHE_DIR):
	@mkdir -p $(CACHE_DIR)

# Debug target
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

# Clean target with levels
.PHONY: clean
clean: ## Clean all build artifacts
	@echo "$(CYAN)Cleaning build artifacts...$(RESET)"
	-rm -rf $(BUILD_DIR)/ $(DIST_DIR)/ *.egg-info/ $(TEMP_DIR)/
	-find . -type f -name "*.so" -delete
	-find . -type f -name "*.cpp" -delete
	-find . -type f -name "*.c" -delete
	-find . -type f -name "*.html" -delete
	-find . -type d -name "__pycache__" -exec rm -rf {} +
	-rm -f setup.py  # Remove existing setup.py if present
	@echo "$(GREEN)Clean completed ✅$(RESET)"

.PHONY: clean-all
clean-all: clean ## Complete clean including cache and binaries
	@echo "$(CYAN)Performing complete clean...$(RESET)"
	-rm -rf $(BINARY_DIR)/ $(CACHE_DIR)/ $(DISTRIBUTION_DIR)/
	-rm -rf .venv 2>/dev/null || true
	@echo "$(GREEN)Complete clean finished ✅$(RESET)"

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

.PHONY: darwin
darwin: $(WHEEL_CACHE) ## Build for macOS with caching

# Binary build with caching
$(BINARY_CACHE): $(WHEEL_CACHE) | $(CACHE_DIR)
	@echo "$(CYAN)Creating portable binary executable with all dependencies...$(RESET)"
	@mkdir -p $(BINARY_DIR)
	@mkdir -p $(DIST_DIR)

	# Ensure required directories exist
	@mkdir -p db dependencies src/mcli/private src/mcli/public
	@touch db/.gitkeep dependencies/.gitkeep

	# Install PyInstaller in the UV environment
	$(UV) pip install -U pyinstaller

	# Create a PyInstaller spec file
	@echo "$(CYAN)Creating PyInstaller spec file...$(RESET)"
	@echo '# -*- mode: python ; coding: utf-8 -*-' > $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo 'from PyInstaller.utils.hooks import collect_all' >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo '' >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "datas = [('src/mcli/private', 'mcli/private'), ('src/mcli/public', 'mcli/public'), ('db', 'db'), ('dependencies', 'dependencies')]" >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo 'binaries = []' >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "hiddenimports = ['typer', 'typer.completion', 'click', 'pandas', 'numpy', 'watchdog', 'openai', 'git', 'flask', 'cachetools', 'tomli', 'ipywidgets', 'encodings', 'encodings.utf_8', 'encodings.cp1252', 'encodings.ascii', 'encodings.idna', 'encodings.latin_1', 'codecs', 'InquirerPy', 'requests']" >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "tmp_ret = collect_all('typer')" >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]" >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "tmp_ret = collect_all('click')" >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]" >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo '' >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "a = Analysis(" >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    ['src/mcli/app/main.py']," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    pathex=[]," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    binaries=binaries," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    datas=datas," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    hiddenimports=hiddenimports," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    hookspath=[]," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    hooksconfig={}," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    runtime_hooks=[]," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    excludes=[]," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    noarchive=False," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo ")" >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "pyz = PYZ(a.pure)" >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo '' >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "exe = EXE(" >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    pyz," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    a.scripts," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    a.binaries," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    a.zipfiles," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    a.datas," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    []," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    name='$(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX)'," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    debug=False," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    bootloader_ignore_signals=False," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    strip=False," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    upx=False," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    upx_exclude=[]," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    runtime_tmpdir=None," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    console=True," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    disable_windowed_traceback=False," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    argv_emulation=False," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    target_arch=None," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    codesign_identity=None," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    entitlements_file=None," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo ")" >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec

	# Run PyInstaller using the UV environment's Python
	@echo "$(CYAN)Running PyInstaller with the spec file...$(RESET)"
	.venv/bin/python -m PyInstaller $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec --clean --noconfirm

	# Handle the output file
	@if [ -f "$(DIST_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX)" ]; then \
		mkdir -p $(BINARY_DIR); \
		mv "$(DIST_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX)" "$(BINARY_DIR)/"; \
		echo "$(GREEN)Portable binary created at $(BINARY_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX) ✅$(RESET)"; \
	else \
		echo "$(RED)❌ Error: PyInstaller failed to build the binary.$(RESET)"; \
		echo "$(YELLOW)Checking for output files in the dist directory:$(RESET)"; \
		ls -la $(DIST_DIR) || echo "No dist directory found"; \
		exit 1; \
	fi

	@mkdir -p $(dir $@)
	@touch $@


.PHONY: install
install: $(WHEEL_CACHE) ## Install the package with caching
	@echo "$(CYAN)Installing package...$(RESET)"
	$(PIP) install $(DIST_DIR)/*.whl --force-reinstall
	@echo "$(GREEN)Installation completed ✅$(RESET)"

# Install portable binary
.PHONY: install-portable
install-portable: $(BINARY_CACHE) ## Install portable binary to system path
	@echo "$(CYAN)Installing binary to /usr/local/bin/$(PACKAGE_NAME)...$(RESET)"
	@if [ -f "$(BINARY_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX)" ]; then \
		sudo cp "$(BINARY_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX)" /usr/local/bin/$(PACKAGE_NAME); \
		sudo chmod +x /usr/local/bin/$(PACKAGE_NAME); \
		echo "$(GREEN)Binary installed successfully at /usr/local/bin/$(PACKAGE_NAME) ✅$(RESET)"; \
		echo "$(CYAN)Adding shell completion for $(SHELL)...$(RESET)"; \
		case "$(SHELL)" in \
			*/bash) \
				SHELL_RC="$${HOME}/.bashrc"; \
				[ -f "$${HOME}/.bash_profile" ] && SHELL_RC="$${HOME}/.bash_profile"; \
				echo "$(PACKAGE_NAME) completion --bash > /tmp/$(PACKAGE_NAME)_completion.bash && source /tmp/$(PACKAGE_NAME)_completion.bash" >> "$${SHELL_RC}"; \
				;; \
			*/zsh) \
				echo "$(PACKAGE_NAME) completion --zsh > $${HOME}/.zsh_$(PACKAGE_NAME)_completion"; \
				echo "source $${HOME}/.zsh_$(PACKAGE_NAME)_completion" >> "$${HOME}/.zshrc"; \
				;; \
			*/fish) \
				FISH_DIR="$${HOME}/.config/fish/completions"; \
				mkdir -p "$${FISH_DIR}"; \
				$(PACKAGE_NAME) completion --fish > "$${FISH_DIR}/$(PACKAGE_NAME).fish"; \
				;; \
			*) \
				echo "$(YELLOW)Shell completion not configured: Unsupported shell $(SHELL)$(RESET)"; \
				;; \
		esac; \
		echo "$(GREEN)Shell completion configuration added for $(SHELL) ✅$(RESET)"; \
	else \
		echo "$(RED)❌ Error: Binary not found! Run 'make portable' first.$(RESET)"; \
		exit 1; \
	fi

# Uninstall either the app bundle or standalone binary based on what's installed
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

# Test the installation
.PHONY: test
test: install ## Test the installation
	@echo "$(CYAN)Testing package...$(RESET)"
	$(VENV_PYTHON) -c "from mcli.app.main import main; print('Import test passed ✅')"
	.venv/bin/mcli --help || $(VENV_PYTHON) -m mcli --help
	@echo "$(GREEN)Testing completed ✅$(RESET)"

# Test the binary
.PHONY: test-binary
test-binary: $(BINARY_CACHE) ## Test the portable binary
	@echo "$(CYAN)Testing portable binary...$(RESET)"
	@if [ -f "$(BINARY_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX)" ]; then \
		echo "$(YELLOW)Binary found at: $(BINARY_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX)$(RESET)"; \
		chmod +x "$(BINARY_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX)"; \
		echo "$(CYAN)Running with --version flag:$(RESET)"; \
		"$(BINARY_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX)" --version; \
		RESULT=$$?; \
		if [ $$RESULT -eq 0 ]; then \
			echo "$(GREEN)Binary executed successfully with exit code 0 ✅$(RESET)"; \
		else \
			echo "$(YELLOW)Binary executed with non-zero exit code: $$RESULT$(RESET)"; \
			echo "$(YELLOW)This might not be an error if --version is not implemented.$(RESET)"; \
			echo "$(CYAN)Testing with --help flag:$(RESET)"; \
			"$(BINARY_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX)" --help; \
			HELP_RESULT=$$?; \
			if [ $$HELP_RESULT -eq 0 ]; then \
				echo "$(GREEN)Binary executed successfully with --help flag ✅$(RESET)"; \
			else \
				echo "$(RED)❌ Binary --help test failed with exit code: $$HELP_RESULT$(RESET)"; \
			fi; \
		fi; \
		echo "$(GREEN)Binary test completed ✅$(RESET)"; \
	else \
		echo "$(RED)❌ Error: Binary not found at $(BINARY_DIR)/$(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX)$(RESET)"; \
		echo "$(CYAN)Searching for binary in other locations...$(RESET)"; \
		echo "Checking build directory:"; \
		find build -type f -name "$(PACKAGE_NAME)*" -o -name "main*" 2>/dev/null | grep -v "__pycache__" || echo "No matching files found in build/"; \
		echo "Checking dist directory:"; \
		find dist -type f -name "$(PACKAGE_NAME)*" -o -name "main*" 2>/dev/null || echo "No matching files found in dist/"; \
		echo "Checking bin directory:"; \
		find bin -type f -name "$(PACKAGE_NAME)*" 2>/dev/null || echo "No matching files found in bin/"; \
		echo "$(YELLOW)To rebuild the binary, run: make clean portable$(RESET)"; \
		exit 1; \
	fi

.PHONY: help
help: ## Show this help message
	@echo "$(CYAN)Available targets:$(RESET)"
	@echo "$(YELLOW)Usage: make [target]$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-20s$(RESET) %s\n", $$1, $$2}'
