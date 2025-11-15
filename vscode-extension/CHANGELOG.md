# Change Log

All notable changes to the "MCLI Workflow Notebooks" extension will be documented in this file.

## [1.1.0] - 2024-11-15

### 🔒 Security (CRITICAL)
- **Fixed command injection vulnerability in Python cell execution** - Now uses temporary files instead of command-line string interpolation
- **Fixed command injection vulnerability in Shell cell execution** - Now uses temporary files for secure execution
- **Improved file cleanup** - Temporary files are now properly removed after execution

### ✨ New Features
- **Added comprehensive unit test suite** - 20+ tests covering serializer, controller, and utilities
- **Added integration tests** - Tests for extension activation and command registration
- **Added example workflows** - 3 ready-to-use examples (hello-world, data-processing, devops-automation)
- **Added TROUBLESHOOTING.md** - Comprehensive guide for common issues and solutions
- **Added TUTORIAL_VIDEO_OUTLINE.md** - Complete outline for creating tutorial videos

### 🐛 Bug Fixes
- Removed unused notebookEditor.ts file (legacy code cleanup)
- Improved error handling in cell execution with proper try-catch blocks
- Better cleanup of temporary files with finally blocks
- Fixed potential resource leaks

### 📚 Documentation
- **Enhanced README** - Expanded FAQ section with more Q&A
- **Comprehensive troubleshooting guide** - Covers installation, execution, and performance issues
- **Tutorial video outline** - 3-5 minute video script with scene breakdown
- **Example workflows** - Well-documented examples for different use cases

### 🔧 Technical Improvements
- **Updated package.json** - Added mocha, @types/mocha, glob for testing
- **Improved .vscodeignore** - Excludes test files, build artifacts, and temporary files
- **Security-first execution** - All code execution now uses temporary files (prevents injection)
- **Proper file permissions** - Shell scripts are made executable (chmod 755)
- **Better resource cleanup** - Ensures temporary files are always deleted

### 📦 Package Improvements
- Reduced package size by excluding unnecessary files
- Cleaner distribution with better .vscodeignore rules
- Added test infrastructure without bloating the extension

### 🎯 Marketplace Ready
- **All security issues resolved** - Safe for public use
- **Comprehensive testing** - Full test coverage for core functionality
- **Professional documentation** - README, FAQ, Troubleshooting, Examples
- **Clean package** - Optimized size, proper exclusions

## [2.0.0] - 2025-10-28

### 🚀 Major Release: Full MCLI Command Integration!

This is a **major release** that transforms the extension from a simple notebook editor into a complete visual editing solution for all MCLI commands.

#### 🎯 Breaking Through: Auto-Format Conversion

- **Automatic format detection and conversion** - Seamlessly converts between old mcli command format and notebook format
- **Bidirectional compatibility** - Opens old format, edits visually, saves back to original format
- **Zero migration required** - Works with existing `~/.mcli/commands/*.json` files out of the box
- **Format preservation** - Maintains all metadata, structure, and compatibility with `mcli workflow`

#### ✨ What's New in 2.0

**Core Features:**
- 🔄 **Smart Format Conversion** - Automatically detects and converts old mcli command JSON to notebook format
- 💾 **Round-Trip Compatibility** - Saves back to original format when closing
- 🎨 **Visual Cell Editing** - Edit code and documentation in separate, manageable cells
- ⚡ **Live Execution** - Run Python/Shell code directly in VS Code
- 📝 **Rich Documentation** - Add markdown cells for inline documentation
- 🔧 **Metadata Preservation** - Maintains all original command metadata

**Enhanced Description:**
- Better explanation of MCLI Framework context
- Clear use cases for different audiences (DevOps, Data Science, Automation)
- Installation instructions for both framework and extension

**Bug Fixes:**
- Fixed crash when opening non-notebook JSON files
- Added validation and helpful error messages
- Type safety improvements

### 🎯 Why This is a Major Release:

This version fundamentally changes how you interact with MCLI commands. Instead of editing raw JSON, you now have a **visual, cell-based interface** that makes workflow creation and maintenance dramatically easier while maintaining 100% compatibility with existing workflows.

**Before v2.0:** Edit raw JSON files manually
**After v2.0:** Visual notebook interface with live execution

This is a **game-changer** for MCLI workflow development!

### 📦 Complete Feature Set (v1.0 + v2.0):

1. ✅ **Visual cell-based editing** - Jupyter-style interface
2. ✅ **Live code execution** - Python, Shell, Bash, Zsh, Fish
3. ✅ **Smart auto-conversion** - Old format ↔ Notebook format
4. ✅ **Monaco editor integration** - IntelliSense, syntax highlighting
5. ✅ **Rich markdown support** - Document your workflows
6. ✅ **Git-friendly format** - Clean JSON diffs
7. ✅ **Format preservation** - Maintains original structure
8. ✅ **Zero migration cost** - Works with existing files

### 🚀 Upgrade Path:

No action required! Simply update the extension and start using it with your existing `~/.mcli/commands/*.json` files.

## [1.0.2] - 2025-10-28

### 📝 Documentation Improvements

- **Enhanced description with MCLI Framework context** - Updated extension description to explain what MCLI Framework is and why you would use this extension
- **Added MCLI Framework installation guide** - New section explaining how to install and use mcli-framework PyPI package
- **Improved README** - Added "Why Use This?" section with use cases for different audiences
- **Added FAQ entry** - Clarified when the "cells array" error appears and which files the extension works with

### 🎯 What's New

- Better explanation of relationship between MCLI Framework and this extension
- Clear guidance on which JSON files work with the extension (notebook format vs command files)
- Installation instructions now include mcli-framework setup

## [1.0.1] - 2025-10-28

### 🐛 Bug Fixes

- **Fixed crash when opening non-notebook JSON files** - Added validation to check if JSON contains a `cells` array before attempting to parse as notebook
- Now shows a helpful error message when opening incompatible JSON files

## [1.0.0] - 2025-10-26

### 🎉 Initial Release

Transform your workflow JSON files into beautiful, interactive notebooks!

#### ✨ Features

- **🎨 Visual Cell-Based Editing** - Edit workflows with Jupyter-like interface
- **⚡ Live Cell Execution** - Run Python and Shell code directly in VSCode
- **🎯 Monaco Editor Integration** - Full IntelliSense, autocomplete, and syntax highlighting
- **📝 Markdown Support** - Document your workflows with rich text
- **💾 JSON Transparency** - Files remain as `.json` for git-friendly diffs
- **🔄 Bidirectional Sync** - Edit visually or as JSON, changes sync automatically
- **⌨️ Keyboard Shortcuts** - Familiar Jupyter shortcuts (Shift+Enter, etc.)
- **🎭 Multiple Languages** - Support for Python, Shell, Bash, Zsh, Fish

#### 🚀 What You Can Do

1. **Open** any workflow `.json` file
2. **Edit** with cell-based interface
3. **Run** cells and see output inline
4. **Document** with markdown cells
5. **Save** back to JSON automatically

#### 🛠️ Technical

- Uses VSCode's Native Notebook API
- Jupyter nbformat 4 compatible
- Zero configuration needed
- 100% backward compatible

#### 📚 Documentation

- [Quick Start Guide](https://github.com/gwicho38/mcli/blob/main/README-VISUAL-EDITING.md)
- [Installation](https://github.com/gwicho38/mcli/blob/main/vscode-extension/INSTALL.md)
- [Complete Guide](https://github.com/gwicho38/mcli/blob/main/docs/workflow-notebooks.md)

---

**Enjoy your new visual workflow editing superpowers! 🚀**
