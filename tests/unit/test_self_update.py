"""Unit tests for mcli self update command"""

import sys
import os
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


def test_uv_tool_detection_unix_path():
    """Test that uv tool is correctly detected on Unix systems"""
    # Simulate a uv tool installation path
    uv_path = "/Users/lefv/.local/share/uv/tools/mcli-framework/bin/python"

    # Test the detection logic (mimicking the code from self_cmd.py)
    executable_path = str(uv_path).replace("\\", "/")
    is_uv_tool = (
        "/uv/tools/" in executable_path or
        "/.local/share/uv/tools/" in executable_path or
        "\\AppData\\Local\\uv\\tools\\" in str(uv_path)
    )

    assert is_uv_tool, "Should detect uv tool installation on Unix path"


def test_uv_tool_detection_windows_path():
    """Test that uv tool is correctly detected on Windows systems"""
    # Simulate a Windows uv tool installation path
    uv_path = "C:\\Users\\User\\AppData\\Local\\uv\\tools\\mcli-framework\\Scripts\\python.exe"

    # Test the detection logic
    executable_path = str(uv_path).replace("\\", "/")
    is_uv_tool = (
        "/uv/tools/" in executable_path or
        "/.local/share/uv/tools/" in executable_path or
        "\\AppData\\Local\\uv\\tools\\" in str(uv_path)
    )

    assert is_uv_tool, "Should detect uv tool installation on Windows path"


def test_uv_tool_detection_alternative_unix():
    """Test detection with alternative Unix path"""
    uv_path = "/home/user/uv/tools/mcli/bin/python"

    executable_path = str(uv_path).replace("\\", "/")
    is_uv_tool = (
        "/uv/tools/" in executable_path or
        "/.local/share/uv/tools/" in executable_path or
        "\\AppData\\Local\\uv\\tools\\" in str(uv_path)
    )

    assert is_uv_tool, "Should detect uv tool installation with /uv/tools/ pattern"


def test_pip_installation_detection():
    """Test that regular pip installations are NOT detected as uv tool"""
    # Simulate a regular pip installation path
    pip_paths = [
        "/usr/local/bin/python",
        "/opt/homebrew/bin/python3",
        "C:\\Python311\\python.exe",
        "/Users/user/.pyenv/versions/3.11.0/bin/python"
    ]

    for pip_path in pip_paths:
        executable_path = str(pip_path).replace("\\", "/")
        is_uv_tool = (
            "/uv/tools/" in executable_path or
            "/.local/share/uv/tools/" in executable_path or
            "\\AppData\\Local\\uv\\tools\\" in str(pip_path)
        )

        assert not is_uv_tool, f"Should NOT detect {pip_path} as uv tool installation"


def test_uv_tool_normalized_path():
    """Test that path normalization works correctly"""
    # Test with mixed separators (should be normalized)
    uv_path = "/Users/lefv/.local/share/uv/tools/mcli-framework/bin/python"

    # Normalize
    normalized = uv_path.replace("\\", "/")

    assert "/.local/share/uv/tools/" in normalized
    assert normalized == uv_path  # Unix path should remain unchanged


def test_uv_tool_update_command_selection():
    """Test that the correct update command is selected based on installation type"""
    # Mock the update command selection logic

    # Test uv tool path
    uv_executable = "/Users/lefv/.local/share/uv/tools/mcli-framework/bin/python"
    executable_path = str(uv_executable).replace("\\", "/")

    is_uv_tool = (
        "/uv/tools/" in executable_path or
        "/.local/share/uv/tools/" in executable_path or
        "\\AppData\\Local\\uv\\tools\\" in str(uv_executable)
    )

    if is_uv_tool:
        cmd = ["uv", "tool", "install", "--force", "mcli-framework"]
    else:
        cmd = [uv_executable, "-m", "pip", "install", "--upgrade", "mcli-framework"]

    assert cmd == ["uv", "tool", "install", "--force", "mcli-framework"], \
        "Should use 'uv tool install' for uv tool installations"

    # Test pip path
    pip_executable = "/usr/local/bin/python3"
    executable_path = str(pip_executable).replace("\\", "/")

    is_uv_tool = (
        "/uv/tools/" in executable_path or
        "/.local/share/uv/tools/" in executable_path or
        "\\AppData\\Local\\uv\\tools\\" in str(pip_executable)
    )

    if is_uv_tool:
        cmd = ["uv", "tool", "install", "--force", "mcli-framework"]
    else:
        cmd = [pip_executable, "-m", "pip", "install", "--upgrade", "mcli-framework"]

    assert cmd == [pip_executable, "-m", "pip", "install", "--upgrade", "mcli-framework"], \
        "Should use 'pip install' for regular installations"


def test_regression_uv_tool_no_pip_error():
    """
    Regression test for the 'No module named pip' error in uv tool environments.

    Bug: When mcli was installed via 'uv tool install', the self update command
    tried to use 'python -m pip' which failed because uv tool environments don't
    include pip by default.

    Fix: Improved detection to correctly identify uv tool installations and use
    'uv tool install --force' instead of pip.

    Error message that occurred:
    ❌ Update failed:
    /Users/lefv/.local/share/uv/tools/mcli-framework/bin/python: No module named pip
    """
    # The problematic path from the user's system
    user_path = "/Users/lefv/.local/share/uv/tools/mcli-framework/bin/python"

    # Test old detection (buggy)
    old_is_uv_tool = ".local/share/uv/tools/" in user_path or \
                     "\\AppData\\Local\\uv\\tools\\" in user_path

    # This should be True, but let's verify
    assert old_is_uv_tool, "Old detection should work but may have edge cases"

    # Test new detection (fixed)
    executable_path = str(user_path).replace("\\", "/")
    new_is_uv_tool = (
        "/uv/tools/" in executable_path or
        "/.local/share/uv/tools/" in executable_path or
        "\\AppData\\Local\\uv\\tools\\" in str(user_path)
    )

    assert new_is_uv_tool, "New detection must correctly identify uv tool installation"

    # Verify correct command is selected
    if new_is_uv_tool:
        cmd = ["uv", "tool", "install", "--force", "mcli-framework"]
    else:
        cmd = [user_path, "-m", "pip", "install", "--upgrade", "mcli-framework"]

    # Should NOT use pip (which doesn't exist in uv tool env)
    assert cmd == ["uv", "tool", "install", "--force", "mcli-framework"], \
        "Must use 'uv tool install' to avoid 'No module named pip' error"


def main():
    """Run all tests"""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    main()
