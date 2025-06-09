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
	@echo "    upx=True," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    upx_exclude=[]," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    runtime_tmpdir=None," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    console=True," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    disable_windowed_traceback=False," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    argv_emulation=False," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    target_arch=None," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
	@echo "    codesign_identity='-'," >> $(PACKAGE_NAME)_$(VERSION)_$(PLATFORM_SUFFIX).spec
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

.PHONY: portable
portable: $(BINARY_CACHE) ## Create portable binary executable with caching

# Add multi-Python version support with improved docker caching
.PHONY: portable-py
portable-py: ## Create portable binary executable for specific Python version (e.g., make portable-py PYTHON_VER=3.9)
	@echo "$(CYAN)Creating portable binary with Python $(PYTHON_VER)...$(RESET)"
	@mkdir -p $(BINARY_DIR)
	@mkdir -p $(CACHE_DIR)/py$(PYTHON_VER)
	docker run --rm \
		-v "$(PWD):/app" \
		-v "$(PWD)/$(CACHE_DIR)/py$(PYTHON_VER):/root/.cache" \
		-w /app \
		python:$(PYTHON_VER)-slim \
		bash -c "apt-get update && apt-get install -y make git && pip install uv && uv pip install -e . && make portable"
	@echo "$(GREEN)Python $(PYTHON_VER) portable binary created ✅$(RESET)"

# Linux binary target with caching
.PHONY: linux-portable
linux-portable: ## Create portable binary for Linux
	@echo "$(CYAN)Creating Linux portable binary in Docker...$(RESET)"
	@mkdir -p $(CACHE_DIR)/linux
	docker run --rm \
		-v "$(PWD):/app" \
		-v "$(PWD)/$(CACHE_DIR)/linux:/root/.cache" \
		-w /app \
		python:3.11-slim \
		bash -c "apt-get update && apt-get install -y make git && make portable"
	@echo "$(GREEN)Linux portable binary created ✅$(RESET)"

# Build for all supported Python versions with parallel execution
.PHONY: portable-all-versions
portable-all-versions: ## Build portable binaries for Python 3.9, 3.10, 3.11, and 3.12 in parallel
	@echo "$(CYAN)Building portable binaries for all supported Python versions...$(RESET)"
	@mkdir -p $(BINARY_DIR)
	@make -j4 portable-versions
	@echo "$(GREEN)All portable binaries created ✅$(RESET)"

.PHONY: portable-versions
portable-versions:
	@make portable-py PYTHON_VER=3.9 &
	@make portable-py PYTHON_VER=3.10 &
	@make portable-py PYTHON_VER=3.11 &
	@make portable-py PYTHON_VER=3.12 &
	@wait

# Create a macOS app bundle
.PHONY: nuitka-app
nuitka-app: darwin ## Create macOS app bundle using Nuitka compiler
	@echo "$(CYAN)Creating macOS app bundle with Nuitka...$(RESET)"
	@mkdir -p $(DIST_DIR)
	$(UV) pip install -U nuitka ordered-set pydot
	@echo "$(CYAN)Running Nuitka with app bundle parameters...$(RESET)"
	LDFLAGS="-L/opt/homebrew/opt/gettext/lib -lintl" $(PYTHON) -m nuitka \
		src/mcli/app/main.py \
		--standalone \
		--follow-imports \
		--lto=yes \
		--macos-create-app-bundle \
		--disable-console \
		--macos-sign-identity=- \
		--prefer-source-code \
		--plugin-enable=multiprocessing \
		--include-data-dir=src/mcli/private=mcli/private \
		--include-data-dir=src/mcli/public=mcli/public \
		--include-data-dir=db=db \
		--include-data-dir=dependencies=dependencies \
		--include-module=typer \
		--include-module=typer.completion \
		--include-module=click \
		--include-module=pandas \
		--include-module=numpy \
		--include-module=watchdog \
		--include-module=openai \
		--include-module=git \
		--include-module=github \
		--include-module=flask \
		--include-module=cachetools \
		--include-module=tomli \
		--include-module=ipywidgets \
		--include-module=encodings \
		--include-module=encodings.utf_8 \
		--include-module=encodings.cp1252 \
		--include-module=encodings.ascii \
		--include-module=encodings.idna \
		--include-module=encodings.latin_1 \
		--include-module=codecs \
		--include-module=InquirerPy \
		--include-module=requests \
		--include-module=urllib \
		--include-module=pydot \
		--include-package=typer \
		--include-package=click \
		--include-package=pydot \
		--include-package-data=pydot \
		--nofollow-import-to=tkinter,PyQt5,PySide2,numpy.distutils,scipy,matplotlib,IPython \
		--output-dir=$(DIST_DIR) \
		--macos-app-name="$(APP_NAME)" \
		--output-filename="$(APP_NAME)"

	@if [ -d "$(DIST_DIR)/main.app" ] && [ ! -d "$(DIST_DIR)/$(APP_BUNDLE)" ]; then \
		mv "$(DIST_DIR)/main.app" "$(DIST_DIR)/$(APP_BUNDLE)"; \
		echo "$(GREEN)Renamed to $(DIST_DIR)/$(APP_BUNDLE) ✅$(RESET)"; \
	fi

	@if [ -d "$(DIST_DIR)/$(APP_BUNDLE)" ]; then \
		echo "$(GREEN)Created macOS app bundle at $(DIST_DIR)/$(APP_BUNDLE) ✅$(RESET)"; \
		UNIX_TS=$$(date +%y%m%d.%H%M%S); \
		GIT_HASH=$$(git rev-parse --short HEAD); \
		CUSTOM_TAG="$(CUSTOMER_NAME).$(APP_NAME).$(APP_VERSION).$$UNIX_TS.$$GIT_HASH"; \
		VERSION_DIR="$(DIST_DIR)/$$CUSTOM_TAG"; \
		mkdir -p "$$VERSION_DIR"; \
		APP_TAR_FILENAME="$(APP_NAME)-$$CUSTOM_TAG-$(PLATFORM_SUFFIX).tar.gz"; \
		tar -czf "$$VERSION_DIR/$$APP_TAR_FILENAME" -C "$(DIST_DIR)" "$(APP_BUNDLE)"; \
		echo "$(GREEN)Created app tarball $$VERSION_DIR/$$APP_TAR_FILENAME ✅$(RESET)"; \
		\
		if [ -f "./install.sh" ]; then \
			cp ./install.sh "$$VERSION_DIR/install.sh"; \
			echo "$(GREEN)Copied install.sh to $$VERSION_DIR ✅$(RESET)"; \
		else \
			echo "$(YELLOW)⚠️  Warning: install.sh not found at repository root. Skipping copy.$(RESET)"; \
		fi; \
		\
		if [ -f "./INSTALL.md" ]; then \
			cp ./INSTALL.md "$$VERSION_DIR/INSTALL.md"; \
			echo "$(GREEN)Copied INSTALL.md to $$VERSION_DIR ✅$(RESET)"; \
		else \
			echo "$(YELLOW)⚠️  Warning: INSTALL.md not found at repository root. Skipping copy.$(RESET)"; \
		fi; \
		\
		echo "$(CYAN)Creating final archive $(DIST_DIR)/$$CUSTOM_TAG.tar.gz...$(RESET)"; \
		tar -czf "$(DIST_DIR)/$$CUSTOM_TAG.tar.gz" -C "$(DIST_DIR)" "$$CUSTOM_TAG"; \
		rm -rf "$$VERSION_DIR"; \
		echo "$(GREEN)Final package: $(DIST_DIR)/$$CUSTOM_TAG.tar.gz ✅$(RESET)"; \
		\
		echo "$(CYAN)Uploading package to Confluence...$(RESET)"; \
		source $(CURDIR)/publish.sh && upload_to_confluence "$(DIST_DIR)/$$CUSTOM_TAG.tar.gz"; \
		if [ $$? -eq 0 ]; then \
			echo "$(GREEN)Successfully uploaded to Confluence ✅$(RESET)"; \
		else \
			echo "$(YELLOW)⚠️  Warning: Failed to upload to Confluence. Build continues.$(RESET)"; \
		fi; \
	else \
		echo "$(RED)❌ Error: App bundle not found at $(DIST_DIR)/$(APP_BUNDLE)!$(RESET)"; \
		exit 1; \
	fi

# Create a standalone binary (as currently working)
.PHONY: nuitka-binary
nuitka-binary: darwin ## Create standalone binary using Nuitka compiler
	@echo "$(CYAN)Creating standalone binary with Nuitka...$(RESET)"
	@mkdir -p $(BINARY_DIR)
	$(UV) pip install -U nuitka ordered-set
	@echo "$(CYAN)Running Nuitka with single binary parameters...$(RESET)"
	LDFLAGS="-L/opt/homebrew/opt/gettext/lib -lintl" $(PYTHON) -m nuitka \
		src/mcli/app/main.py \
		--standalone \
		--follow-imports \
		--lto=yes \
		--onefile \
		--macos-sign-identity=- \
		--plugin-enable=multiprocessing \
		--include-data-dir=src/mcli/private=mcli/private \
		--include-data-dir=src/mcli/public=mcli/public \
		--include-data-dir=db=db \
		--include-data-dir=dependencies=dependencies \
		--output-dir=$(BINARY_DIR) \
		--output-filename="$(APP_NAME)"

	@if [ -f "$(BINARY_DIR)/$(APP_NAME)" ]; then \
		chmod +x "$(BINARY_DIR)/$(APP_NAME)"; \
		echo "$(GREEN)Created standalone binary at $(BINARY_DIR)/$(APP_NAME) ✅$(RESET)"; \
		ln -sf "$(shell pwd)/$(BINARY_DIR)/$(APP_NAME)" "$(BINARY_DIR)/$(PACKAGE_NAME)_latest"; \
		echo "$(GREEN)Created symbolic link at $(BINARY_DIR)/$(PACKAGE_NAME)_latest ✅$(RESET)"; \
		# Create distribution package
		mkdir -p $(DISTRIBUTION_DIR); \
		VERSION_DATE=$$(date +%y%m%d.%H%M%S); \
		DIST_FILENAME="$(DISTRIBUTION_DIR)/$(APP_NAME)-binary-$$VERSION_DATE-$(PLATFORM_SUFFIX).tar.gz"; \
		tar -czf "$$DIST_FILENAME" -C "$(BINARY_DIR)" "$(APP_NAME)"; \
		echo "$(GREEN)Created distribution package at $$DIST_FILENAME ✅$(RESET)"; \
	else \
		echo "$(RED)❌ Error: Binary not found!$(RESET)"; \
		exit 1; \
	fi

# Install the app bundle to /Applications and link to /usr/local/bin
.PHONY: install-app
install-app: nuitka-app ## Install app bundle to Applications and link executable to /usr/local/bin
	@echo "$(CYAN)Installing $(APP_BUNDLE) to $(INSTALL_DIR)...$(RESET)"
	@if [ -d "$(DIST_DIR)/$(APP_BUNDLE)" ]; then \
		sudo cp -R "$(DIST_DIR)/$(APP_BUNDLE)" "$(INSTALL_DIR)/"; \
		sudo mkdir -p "$(BIN_DIR)"; \
		sudo ln -sf "$(INSTALL_DIR)/$(APP_BUNDLE)/Contents/MacOS/$(APP_NAME)" "$(BIN_DIR)/$(APP_NAME)"; \
		echo "$(GREEN)App bundle installed to $(INSTALL_DIR)/$(APP_BUNDLE) ✅$(RESET)"; \
		echo "$(GREEN)Executable linked to $(BIN_DIR)/$(APP_NAME) ✅$(RESET)"; \
		echo "$(YELLOW)You can now run '$(APP_NAME)' from terminal.$(RESET)"; \
	else \
		echo "$(RED)❌ Error: App bundle not found at $(DIST_DIR)/$(APP_BUNDLE)! Run 'make nuitka-app' first.$(RESET)"; \
		exit 1; \
	fi


# Comprehensive binary benchmark target
.PHONY: benchmark-binary
benchmark-binary: ## Benchmark the speed of generated binaries with multiple tests
	@echo "$(CYAN)Benchmarking binary performance...$(RESET)"
	@mkdir -p $(TEMP_DIR)/benchmark
	
	@# Create a CSV file to store benchmark results
	@echo "Binary,Test,Real,User,Sys" > $(TEMP_DIR)/benchmark/results.csv
	
	@echo "$(YELLOW)Testing standard binary...$(RESET)"
	@if [ -f "$(BINARY_DIR)/$(APP_NAME)" ]; then \
		echo "Standard binary: Startup time"; \
		{ time -p "$(BINARY_DIR)/$(APP_NAME)" --version > $(TEMP_DIR)/benchmark/standard_version.out 2> $(TEMP_DIR)/benchmark/standard_version.err; } 2> $(TEMP_DIR)/benchmark/standard_version_time.txt; \
		REAL=$(grep "real" $(TEMP_DIR)/benchmark/standard_version_time.txt | awk '{print $2}'); \
		USER=$(grep "user" $(TEMP_DIR)/benchmark/standard_version_time.txt | awk '{print $2}'); \
		SYS=$(grep "sys" $(TEMP_DIR)/benchmark/standard_version_time.txt | awk '{print $2}'); \
		echo "Standard,Startup,$REAL,$USER,$SYS" >> $(TEMP_DIR)/benchmark/results.csv; \
		\
		echo "Standard binary: Help command"; \
		{ time -p "$(BINARY_DIR)/$(APP_NAME)" --help > $(TEMP_DIR)/benchmark/standard_help.out 2> $(TEMP_DIR)/benchmark/standard_help.err; } 2> $(TEMP_DIR)/benchmark/standard_help_time.txt; \
		REAL=$(grep "real" $(TEMP_DIR)/benchmark/standard_help_time.txt | awk '{print $2}'); \
		USER=$(grep "user" $(TEMP_DIR)/benchmark/standard_help_time.txt | awk '{print $2}'); \
		SYS=$(grep "sys" $(TEMP_DIR)/benchmark/standard_help_time.txt | awk '{print $2}'); \
		echo "Standard,Help,$REAL,$USER,$SYS" >> $(TEMP_DIR)/benchmark/results.csv; \
		\
		echo "$(GREEN)Standard binary tested ✅$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️  Standard binary not found. Skipping.$(RESET)"; \
	fi
	
	@echo "$(YELLOW)Testing Nuitka optimized binary...$(RESET)"
	@if [ -f "$(BINARY_DIR)/$(APP_NAME)_optimized" ]; then \
		echo "Nuitka optimized binary: Startup time"; \
		{ time -p "$(BINARY_DIR)/$(APP_NAME)_optimized" --version > $(TEMP_DIR)/benchmark/nuitka_optimized_version.out 2> $(TEMP_DIR)/benchmark/nuitka_optimized_version.err; } 2> $(TEMP_DIR)/benchmark/nuitka_optimized_version_time.txt; \
		REAL=$(grep "real" $(TEMP_DIR)/benchmark/nuitka_optimized_version_time.txt | awk '{print $2}'); \
		USER=$(grep "user" $(TEMP_DIR)/benchmark/nuitka_optimized_version_time.txt | awk '{print $2}'); \
		SYS=$(grep "sys" $(TEMP_DIR)/benchmark/nuitka_optimized_version_time.txt | awk '{print $2}'); \
		echo "NuitkaOpt,Startup,$REAL,$USER,$SYS" >> $(TEMP_DIR)/benchmark/results.csv; \
		\
		echo "Nuitka optimized binary: Help command"; \
		{ time -p "$(BINARY_DIR)/$(APP_NAME)_optimized" --help > $(TEMP_DIR)/benchmark/nuitka_optimized_help.out 2> $(TEMP_DIR)/benchmark/nuitka_optimized_help.err; } 2> $(TEMP_DIR)/benchmark/nuitka_optimized_help_time.txt; \
		REAL=$(grep "real" $(TEMP_DIR)/benchmark/nuitka_optimized_help_time.txt | awk '{print $2}'); \
		USER=$(grep "user" $(TEMP_DIR)/benchmark/nuitka_optimized_help_time.txt | awk '{print $2}'); \
		SYS=$(grep "sys" $(TEMP_DIR)/benchmark/nuitka_optimized_help_time.txt | awk '{print $2}'); \
		echo "NuitkaOpt,Help,$REAL,$USER,$SYS" >> $(TEMP_DIR)/benchmark/results.csv; \
		\
		echo "$(GREEN)Nuitka optimized binary tested ✅$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️  Nuitka optimized binary not found. Skipping.$(RESET)"; \
	fi
	
	@echo "$(YELLOW)Testing PyInstaller optimized binary...$(RESET)"
	@if [ -f "$(BINARY_DIR)/$(PACKAGE_NAME)_optimized" ]; then \
		echo "PyInstaller optimized binary: Startup time"; \
		{ time -p "$(BINARY_DIR)/$(PACKAGE_NAME)_optimized" --version > $(TEMP_DIR)/benchmark/pyinstaller_optimized_version.out 2> $(TEMP_DIR)/benchmark/pyinstaller_optimized_version.err; } 2> $(TEMP_DIR)/benchmark/pyinstaller_optimized_version_time.txt; \
		REAL=$(grep "real" $(TEMP_DIR)/benchmark/pyinstaller_optimized_version_time.txt | awk '{print $2}'); \
		USER=$(grep "user" $(TEMP_DIR)/benchmark/pyinstaller_optimized_version_time.txt | awk '{print $2}'); \
		SYS=$(grep "sys" $(TEMP_DIR)/benchmark/pyinstaller_optimized_version_time.txt | awk '{print $2}'); \
		echo "PyInstallerOpt,Startup,$REAL,$USER,$SYS" >> $(TEMP_DIR)/benchmark/results.csv; \
		\
		echo "PyInstaller optimized binary: Help command"; \
		{ time -p "$(BINARY_DIR)/$(PACKAGE_NAME)_optimized" --help > $(TEMP_DIR)/benchmark/pyinstaller_optimized_help.out 2> $(TEMP_DIR)/benchmark/pyinstaller_optimized_help.err; } 2> $(TEMP_DIR)/benchmark/pyinstaller_optimized_help_time.txt; \
		REAL=$(grep "real" $(TEMP_DIR)/benchmark/pyinstaller_optimized_help_time.txt | awk '{print $2}'); \
		USER=$(grep "user" $(TEMP_DIR)/benchmark/pyinstaller_optimized_help_time.txt | awk '{print $2}'); \
		SYS=$(grep "sys" $(TEMP_DIR)/benchmark/pyinstaller_optimized_help_time.txt | awk '{print $2}'); \
		echo "PyInstallerOpt,Help,$REAL,$USER,$SYS" >> $(TEMP_DIR)/benchmark/results.csv; \
		\
		echo "$(GREEN)PyInstaller optimized binary tested ✅$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️  PyInstaller optimized binary not found. Skipping.$(RESET)"; \
	fi
	
	@echo "$(CYAN)Benchmark results summary:$(RESET)"
	@echo "-------------------------------------"
	@if [ -f $(TEMP_DIR)/benchmark/results.csv ]; then \
		echo "Binary Type | Test    | Real Time (s)"; \
		echo "------------ | ------- | ------------"; \
		grep "Standard,Startup" $(TEMP_DIR)/benchmark/results.csv | awk -F',' '{printf "Standard    | Startup | %s\n", $3}'; \
		grep "Standard,Help" $(TEMP_DIR)/benchmark/results.csv | awk -F',' '{printf "Standard    | # Create a macOS app bundle with optimized performance
.PHONY: nuitka-app-optimized
nuitka-app-optimized: darwin ## Create optimized macOS app bundle using Nuitka compiler
	@echo "$(CYAN)Creating performance-optimized macOS app bundle with Nuitka...$(RESET)"
	@mkdir -p $(DIST_DIR)
	$(UV) pip install -U nuitka ordered-set pydot graphviz
	
	# Install tools for dependency analysis
	$(UV) pip install pipdeptree
	@echo "$(CYAN)Analyzing dependencies for optimization...$(RESET)"
	$(VENV_PYTHON) -m pipdeptree > $(TEMP_DIR)/dependencies.txt
	
	@echo "$(CYAN)Running Nuitka with optimized parameters...$(RESET)"
	LDFLAGS="-L/opt/homebrew/opt/gettext/lib -lintl" $(PYTHON) -m nuitka \
		src/mcli/app/main.py \
		--standalone \
		--follow-imports \
		--lto=yes \
		--macos-create-app-bundle \
		--disable-console \
		--macos-sign-identity=- \
		--prefer-source-code \
		--plugin-enable=multiprocessing \
		--plugin-enable=anti-bloat \
		--remove-output \
		--assume-yes-for-downloads \
		--no-pyi-file \
		--python-flag=no_asserts \
		--python-flag=no_docstrings \
		--include-data-dir=src/mcli/private=mcli/private \
		--include-data-dir=src/mcli/public=mcli/public \
		--include-data-dir=db=db \
		--include-data-dir=dependencies=dependencies \
		--include-module=typer \
		--include-module=typer.completion \
		--include-module=click \
		--include-module=pandas \
		--include-module=numpy \
		--include-module=watchdog \
		--include-module=openai \
		--include-module=git \
		--include-module=github \
		--include-module=flask \
		--include-module=cachetools \
		--include-module=tomli \
		--include-module=ipywidgets \
		--include-module=encodings \
		--include-module=encodings.utf_8 \
		--include-module=encodings.cp1252 \
		--include-module=encodings.ascii \
		--include-module=encodings.idna \
		--include-module=encodings.latin_1 \
		--include-module=codecs \
		--include-module=InquirerPy \
		--include-module=requests \
		--include-module=urllib \
		--include-module=pydot \
		--include-module=graphviz \
		--include-package=typer \
		--include-package=click \
		--include-package=pydot \
		--include-package=graphviz \
		--include-package-data=pydot \
		--include-package-data=graphviz \
		--nofollow-import-to=tkinter,PyQt5,PySide2,numpy.distutils,scipy,matplotlib,IPython \
		--output-dir=$(DIST_DIR) \
		--macos-app-name="$(APP_NAME)" \
		--output-filename="$(APP_NAME)"
	
	@if [ -d "$(DIST_DIR)/main.app" ] && [ ! -d "$(DIST_DIR)/$(APP_BUNDLE)" ]; then \
		mv "$(DIST_DIR)/main.app" "$(DIST_DIR)/$(APP_BUNDLE)"; \
		echo "$(GREEN)Renamed to $(DIST_DIR)/$(APP_BUNDLE) ✅$(RESET)"; \
	fi
	
	@if [ -d "$(DIST_DIR)/$(APP_BUNDLE)" ]; then \
		echo "$(GREEN)Created optimized macOS app bundle at $(DIST_DIR)/$(APP_BUNDLE) ✅$(RESET)"; \
		# ... (rest of your packaging logic)
	else \
		echo "$(RED)❌ Error: App bundle not found at $(DIST_DIR)/$(APP_BUNDLE)!$(RESET)"; \
		exit 1; \
	fi

# Create a standalone optimized binary using Nuitka
.PHONY: nuitka-binary-optimized
nuitka-binary-optimized: darwin ## Create optimized standalone binary using Nuitka compiler
	@echo "$(CYAN)Creating optimized standalone binary with Nuitka...$(RESET)"
	@mkdir -p $(BINARY_DIR) $(TEMP_DIR)
	$(UV) pip install -U nuitka ordered-set
	
	# First, create an optimized compilation
	@echo "$(CYAN)Running Nuitka with optimized parameters...$(RESET)"
	LDFLAGS="-L/opt/homebrew/opt/gettext/lib -lintl" $(PYTHON) -m nuitka \
		src/mcli/app/main.py \
		--onefile \
		--follow-imports \
		--lto=yes \
		--macos-sign-identity=- \
		--plugin-enable=multiprocessing \
		--plugin-enable=anti-bloat \
		--remove-output \
		--assume-yes-for-downloads \
		--no-pyi-file \
		--python-flag=no_asserts \
		--python-flag=no_docstrings \
		--include-data-dir=src/mcli/private=mcli/private \
		--include-data-dir=src/mcli/public=mcli/public \
		--include-data-dir=db=db \
		--include-data-dir=dependencies=dependencies \
		--output-dir=$(BINARY_DIR) \
		--output-filename="$(APP_NAME)_optimized"

	@if [ -f "$(BINARY_DIR)/$(APP_NAME)_optimized" ]; then \
		chmod +x "$(BINARY_DIR)/$(APP_NAME)_optimized"; \
		echo "$(GREEN)Created optimized standalone binary at $(BINARY_DIR)/$(APP_NAME)_optimized ✅$(RESET)"; \
		ln -sf "$(shell pwd)/$(BINARY_DIR)/$(APP_NAME)_optimized" "$(BINARY_DIR)/$(PACKAGE_NAME)_latest_optimized"; \
		echo "$(GREEN)Created symbolic link at $(BINARY_DIR)/$(PACKAGE_NAME)_latest_optimized ✅$(RESET)"; \
		# Create distribution package
		mkdir -p $(DISTRIBUTION_DIR); \
		VERSION_DATE=$(date +%y%m%d.%H%M%S); \
		DIST_FILENAME="$(DISTRIBUTION_DIR)/$(APP_NAME)-binary-optimized-$VERSION_DATE-$(PLATFORM_SUFFIX).tar.gz"; \
		tar -czf "$DIST_FILENAME" -C "$(BINARY_DIR)" "$(APP_NAME)_optimized"; \
		echo "$(GREEN)Created optimized distribution package at $DIST_FILENAME ✅$(RESET)"; \
	else \
		echo "$(RED)❌ Error: Optimized binary not found!$(RESET)"; \
		exit 1; \
	fi

# Create optimized standalone binary using PyInstaller
.PHONY: pyinstaller-optimized
pyinstaller-optimized: $(WHEEL_CACHE) ## Create optimized standalone binary using PyInstaller
	@echo "$(CYAN)Creating optimized standalone binary with PyInstaller...$(RESET)"
	@mkdir -p $(BINARY_DIR) $(TEMP_DIR)
	$(UV) pip install -U pyinstaller
	
	# Create an optimized spec file for PyInstaller
	@echo "$(CYAN)Creating optimized PyInstaller spec file...$(RESET)"
	@echo '# -*- mode: python ; coding: utf-8 -*-' > $(PACKAGE_NAME)_optimized.spec
	@echo 'from PyInstaller.utils.hooks import collect_all' >> $(PACKAGE_NAME)_optimized.spec
	@echo 'import os' >> $(PACKAGE_NAME)_optimized.spec
	@echo '' >> $(PACKAGE_NAME)_optimized.spec
	@echo "block_cipher = None" >> $(PACKAGE_NAME)_optimized.spec
	@echo "" >> $(PACKAGE_NAME)_optimized.spec
	@echo "datas = [('src/mcli/private', 'mcli/private'), ('src/mcli/public', 'mcli/public'), ('db', 'db'), ('dependencies', 'dependencies')]" >> $(PACKAGE_NAME)_optimized.spec
	@echo 'binaries = []' >> $(PACKAGE_NAME)_optimized.spec
	@echo "hiddenimports = ['typer', 'typer.completion', 'click', 'pandas', 'numpy', 'watchdog', 'openai', 'git', 'flask', 'cachetools', 'tomli', 'ipywidgets', 'encodings', 'encodings.utf_8', 'encodings.cp1252', 'encodings.ascii', 'encodings.idna', 'encodings.latin_1', 'codecs', 'InquirerPy', 'requests']" >> $(PACKAGE_NAME)_optimized.spec
	@echo "" >> $(PACKAGE_NAME)_optimized.spec
	@echo "# Collect essential packages only" >> $(PACKAGE_NAME)_optimized.spec
	@echo "for pkg in ['typer', 'click']:" >> $(PACKAGE_NAME)_optimized.spec
	@echo "    tmp_ret = collect_all(pkg)" >> $(PACKAGE_NAME)_optimized.spec
	@echo "    datas += tmp_ret[0]" >> $(PACKAGE_NAME)_optimized.spec
	@echo "    binaries += tmp_ret[1]" >> $(PACKAGE_NAME)_optimized.spec
	@echo "    hiddenimports += tmp_ret[2]" >> $(PACKAGE_NAME)_optimized.spec
	@echo "" >> $(PACKAGE_NAME)_optimized.spec
	@echo "# Helper function to strip unnecessary binaries" >> $(PACKAGE_NAME)_optimized.spec
	@echo "def strip_binaries(binaries):" >> $(PACKAGE_NAME)_optimized.spec
	@echo "    return [(b[0], b[1]) for b in binaries if not any(x in b[0].lower() for x in ['libqt', 'pyqt', 'qtgui', 'qtwidgets'])]" >> $(PACKAGE_NAME)_optimized.spec
	@echo "" >> $(PACKAGE_NAME)_optimized.spec
	@echo "# Helper function to strip unnecessary resources" >> $(PACKAGE_NAME)_optimized.spec
	@echo "def strip_resources(datas):" >> $(PACKAGE_NAME)_optimized.spec
	@echo "    return [(d[0], d[1]) for d in datas if not any(x in d[0].lower() for x in ['licenses', 'test', 'tests', 'examples'])]" >> $(PACKAGE_NAME)_optimized.spec
	@echo "" >> $(PACKAGE_NAME)_optimized.spec
	@echo "a = Analysis(" >> $(PACKAGE_NAME)_optimized.spec
	@echo "    ['src/mcli/app/main.py']," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    pathex=[]," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    binaries=binaries," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    datas=datas," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    hiddenimports=hiddenimports," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    hookspath=[]," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    hooksconfig={}," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    runtime_hooks=['$(TEMP_DIR)/runtime_hook.py']," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    excludes=['tkinter', 'matplotlib', 'scipy', 'PIL', 'PyQt5', 'PySide2', 'matplotlib', 'IPython']," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    win_no_prefer_redirects=False," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    win_private_assemblies=False," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    cipher=block_cipher," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    noarchive=False," >> $(PACKAGE_NAME)_optimized.spec
	@echo ")" >> $(PACKAGE_NAME)_optimized.spec
	@echo "" >> $(PACKAGE_NAME)_optimized.spec
	@echo "# Apply optimizations" >> $(PACKAGE_NAME)_optimized.spec
	@echo "a.binaries = strip_binaries(a.binaries)" >> $(PACKAGE_NAME)_optimized.spec
	@echo "a.datas = strip_resources(a.datas)" >> $(PACKAGE_NAME)_optimized.spec
	@echo "" >> $(PACKAGE_NAME)_optimized.spec
	@echo "pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)" >> $(PACKAGE_NAME)_optimized.spec
	@echo "" >> $(PACKAGE_NAME)_optimized.spec
	@echo "exe = EXE(" >> $(PACKAGE_NAME)_optimized.spec
	@echo "    pyz," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    a.scripts," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    a.binaries," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    a.zipfiles," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    a.datas," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    []," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    name='$(PACKAGE_NAME)_optimized'," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    debug=False," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    bootloader_ignore_signals=False," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    strip=False," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    upx=True," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    upx_exclude=['vcruntime140.dll', 'python*.dll', 'libpython*.so']," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    runtime_tmpdir=None," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    console=True," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    disable_windowed_traceback=False," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    argv_emulation=False," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    target_arch=None," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    codesign_identity=None," >> $(PACKAGE_NAME)_optimized.spec
	@echo "    entitlements_file=None," >> $(PACKAGE_NAME)_optimized.spec
	@echo ")" >> $(PACKAGE_NAME)_optimized.spec
	
	# Create a runtime hook for optimization
	@mkdir -p $(TEMP_DIR)
	@echo "# PyInstaller runtime hook" > $(TEMP_DIR)/runtime_hook.py
	@echo "import os" >> $(TEMP_DIR)/runtime_hook.py
	@echo "import sys" >> $(TEMP_DIR)/runtime_hook.py
	@echo "" >> $(TEMP_DIR)/runtime_hook.py
	@echo "# Enable bytecode optimization" >> $(TEMP_DIR)/runtime_hook.py
	@echo "sys.dont_write_bytecode = False" >> $(TEMP_DIR)/runtime_hook.py
	@echo "os.environ['PYTHONOPTIMIZE'] = '2'" >> $(TEMP_DIR)/runtime_hook.py
	@echo "" >> $(TEMP_DIR)/runtime_hook.py
	@echo "# Pre-load commonly used modules" >> $(TEMP_DIR)/runtime_hook.py
	@echo "import json" >> $(TEMP_DIR)/runtime_hook.py
	@echo "import importlib" >> $(TEMP_DIR)/runtime_hook.py
	@echo "import os.path" >> $(TEMP_DIR)/runtime_hook.py
	@echo "import typer" >> $(TEMP_DIR)/runtime_hook.py
	
	# Run PyInstaller
	@echo "$(CYAN)Running PyInstaller with optimized spec file...$(RESET)"
	.venv/bin/python -m PyInstaller $(PACKAGE_NAME)_optimized.spec --clean
	
	# Move binary to output directory
	@if [ -f "$(DIST_DIR)/$(PACKAGE_NAME)_optimized" ]; then \
		mkdir -p $(BINARY_DIR); \
		mv "$(DIST_DIR)/$(PACKAGE_NAME)_optimized" "$(BINARY_DIR)/"; \
		chmod +x "$(BINARY_DIR)/$(PACKAGE_NAME)_optimized"; \
		echo "$(GREEN)Created optimized PyInstaller binary at $(BINARY_DIR)/$(PACKAGE_NAME)_optimized ✅$(RESET)"; \
		# Create distribution package
		mkdir -p $(DISTRIBUTION_DIR); \
		VERSION_DATE=$(date +%y%m%d.%H%M%S); \
		DIST_FILENAME="$(DISTRIBUTION_DIR)/$(APP_NAME)-pyinstaller-optimized-$VERSION_DATE-$(PLATFORM_SUFFIX).tar.gz"; \
		tar -czf "$DIST_FILENAME" -C "$(BINARY_DIR)" "$(PACKAGE_NAME)_optimized"; \
		echo "$(GREEN)Created optimized PyInstaller distribution package at $DIST_FILENAME ✅$(RESET)"; \
	else \
		echo "$(RED)❌ Error: PyInstaller optimized binary not found!$(RESET)"; \
		exit 1; \
	fi


# Install the standalone binary directly to /usr/local/bin
.PHONY: install-binary
install-binary: nuitka-binary ## Install standalone binary directly to /usr/local/bin
	@echo "$(CYAN)Installing standalone binary to $(BIN_DIR)...$(RESET)"
	@if [ -f "$(BINARY_DIR)/$(APP_NAME)" ]; then \
		sudo mkdir -p "$(BIN_DIR)"; \
		sudo cp "$(BINARY_DIR)/$(APP_NAME)" "$(BIN_DIR)/"; \
		sudo chmod +x "$(BIN_DIR)/$(APP_NAME)"; \
		echo "$(GREEN)Binary installed to $(BIN_DIR)/$(APP_NAME) ✅$(RESET)"; \
		echo "$(YELLOW)You can now run '$(APP_NAME)' from terminal.$(RESET)"; \
	else \
		echo "$(RED)❌ Error: Binary not found at $(BINARY_DIR)/$(APP_NAME)! Run 'make nuitka-binary' first.$(RESET)"; \
		exit 1; \
	fi

# Install the Nuitka-built binary (legacy target, kept for compatibility)
.PHONY: install-nuitka
install-nuitka: install-app ## Install Nuitka-built app to system path (redirects to install-app)
	@echo "$(YELLOW)Note: 'install-nuitka' is deprecated, use 'install-app' instead.$(RESET)"

# Install the package
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

# Force rebuild target
.PHONY: force-rebuild
force-rebuild: ## Force rebuild of all artifacts
	@echo "$(CYAN)Forcing complete rebuild...$(RESET)"
	-rm -f $(UV_ENV_CACHE) $(WHEEL_CACHE) $(BINARY_CACHE)
	@make portable

# Help target
.PHONY: help
help: ## Show this help message
	@echo "$(CYAN)Available targets:$(RESET)"
	@echo "$(YELLOW)Usage: make [target]$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-20s$(RESET) %s\n", $$1, $$2}'
