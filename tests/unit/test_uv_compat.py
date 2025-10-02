#!/usr/bin/env python3
"""
Test UV compatibility with the build system.
This script checks if the build system is properly configured for UV.
"""

import os
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class Colors:
    """Terminal colors for output formatting."""
    GREEN = "\033[0;32m"
    YELLOW = "\033[0;33m"
    RED = "\033[0;31m"
    CYAN = "\033[0;36m"
    RESET = "\033[0m"


def log(message, color=None):
    """logger.info a log message with optional color."""
    if color:
        logger.info(f"{color}{message}{Colors.RESET}")
    else:
        logger.info(message)


def check_command(command):
    """Check if a command is available."""
    try:
        subprocess.run(
            command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def run_command(command, description, timeout=60, check=True):
    """Run a command and return the result."""
    log(f"Running: {description}...", Colors.CYAN)
    try:
        result = subprocess.run(
            command,
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        log(f"✅ {description} completed successfully", Colors.GREEN)
        return True, result.stdout
    except subprocess.SubprocessError as e:
        log(f"❌ {description} failed: {e}", Colors.RED)
        return False, str(e)


def check_build_files():
    """Check if build files are properly configured for UV."""
    issues = []
    
    # Check pyproject.toml
    if os.path.exists("pyproject.toml"):
        with open("pyproject.toml", "r") as f:
            content = f.read()
            if "poetry" in content.lower() and "build-backend = \"poetry.core.masonry.api\"" in content:
                issues.append("pyproject.toml still references poetry build backend")
    else:
        issues.append("pyproject.toml not found")
    
    # Check Makefile
    if os.path.exists("Makefile"):
        with open("Makefile", "r") as f:
            content = f.read()
            if "poetry" in content.lower():
                issues.append("Makefile still contains 'poetry' references")
            if "uv" not in content.lower():
                issues.append("Makefile doesn't contain 'uv' references")
    else:
        issues.append("Makefile not found")
    
    # Check if uv.lock exists
    if not os.path.exists("uv.lock"):
        issues.append("uv.lock file not found")
    
    return issues


def test_virtual_env():
    """Test if UV can create and manage a virtual environment."""
    # Create a temporary directory
    test_dir = tempfile.mkdtemp()
    try:
        os.chdir(test_dir)
        
        # Create a minimal pyproject.toml
        with open("pyproject.toml", "w") as f:
            f.write("""
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "uvtest"
version = "0.1.0"
description = "Test UV compatibility"
requires-python = ">=3.9"
            """)
        
        # Test UV venv creation
        success, _ = run_command(["uv", "venv"], "Create virtual environment")
        if not success:
            return False
        
        # Test UV pip install
        success, _ = run_command(["uv", "pip", "install", "rich"], "Install package")
        if not success:
            return False
        
        return True
    finally:
        # Clean up
        os.chdir(Path(__file__).parent.absolute())
        shutil.rmtree(test_dir)


def main():
    """Main function."""
    log("Testing UV compatibility with build system", Colors.CYAN)
    log("-" * 50)
    
    # Check if UV is installed
    if not check_command(["uv", "--version"]):
        log("❌ UV is not installed or not in PATH", Colors.RED)
        return 1
    
    success, output = run_command(["uv", "--version"], "Check UV version")
    log(f"UV version: {output.strip()}")
    
    # Check Python version
    success, output = run_command(["python", "--version"], "Check Python version")
    if success:
        python_version = output.strip()
        log(f"Python version: {python_version}")
    
    # Check for issues in build files
    issues = check_build_files()
    if issues:
        log("Issues found in build files:", Colors.YELLOW)
        for issue in issues:
            log(f"  - {issue}", Colors.YELLOW)
    else:
        log("✅ Build files are properly configured for UV", Colors.GREEN)
    
    # Test virtual environment management
    log("Testing UV virtual environment management...", Colors.CYAN)
    if test_virtual_env():
        log("✅ UV virtual environment management works correctly", Colors.GREEN)
    else:
        log("❌ Issues with UV virtual environment management", Colors.RED)
        issues.append("UV virtual environment management failed")
    
    # Test compilation with build
    log("Testing build package with UV...", Colors.CYAN)
    success, _ = run_command(
        ["uv", "pip", "install", "build"], "Install build package", check=False
    )
    if success:
        build_success, _ = run_command(
            ["python", "-m", "build", "--wheel", "--no-isolation", "--skip-dependency-check", "--outdir", "test_dist"],
            "Build wheel (dry run)",
            check=False,
        )
        # Clean up test build directory
        if os.path.exists("test_dist"):
            shutil.rmtree("test_dist")
        
        if build_success:
            log("✅ Build command works with UV", Colors.GREEN)
        else:
            log("❌ Build command failed with UV", Colors.RED)
            issues.append("Build command failed")
    
    # Summary
    log("-" * 50)
    if issues:
        log(f"❌ Found {len(issues)} issues that need to be addressed:", Colors.RED)
        for i, issue in enumerate(issues, 1):
            log(f"  {i}. {issue}", Colors.RED)
        return 1
    else:
        log("✅ All tests passed! UV compatibility looks good.", Colors.GREEN)
        return 0


if __name__ == "__main__":
    sys.exit(main())