"""
File system utilities for MCLI
Provides basic file system operations with path normalization
"""

import json
import os
import shutil
from pathlib import Path

import click


def get_absolute_path(pth):
    """Convert path to absolute path with user expansion"""
    pth = os.path.expanduser(pth)
    pth = os.path.abspath(pth)
    return pth


def ensure_directory_exists(dirpath):
    """Create directory if it doesn't exist"""
    dirpath = get_absolute_path(dirpath)
    os.makedirs(dirpath, exist_ok=True)


def delete_directory(dirpath):
    """Delete directory if it exists"""
    dirpath = get_absolute_path(dirpath)
    if os.path.exists(dirpath):
        shutil.rmtree(dirpath)  # Use rmtree for non-empty directories


def delete_file(filepath):
    """Delete file if it exists"""
    filepath = get_absolute_path(filepath)
    if os.path.exists(filepath):
        os.remove(filepath)


def get_user_home():
    """Get user home directory"""
    return os.path.expanduser("~")


def read_line_from_file(filepath):
    """Read first line from file"""
    filepath = get_absolute_path(filepath)
    if not os.path.exists(filepath):
        raise Exception("File does not exist at: " + filepath)
    with open(filepath) as f:
        return f.readline().strip()


def copy_file(srcpath, dstpath):
    """Copy a file from source to destination"""
    srcpath = get_absolute_path(srcpath)
    dstpath = get_absolute_path(dstpath)
    if os.path.exists(srcpath):
        # Ensure destination directory exists
        os.makedirs(os.path.dirname(dstpath), exist_ok=True)
        shutil.copy2(srcpath, dstpath)
        return True
    return False


def file_exists(path):
    """Check if a file exists at the given path"""
    path = get_absolute_path(path)
    return os.path.exists(path)


def get_file_size(path):
    """Get the size of a file in bytes"""
    path = get_absolute_path(path)
    if file_exists(path):
        return os.path.getsize(path)
    return 0


def list_files(directory, pattern="*"):
    """List files in a directory matching a pattern"""
    import glob

    directory = get_absolute_path(directory)
    if os.path.exists(directory):
        pattern_path = os.path.join(directory, pattern)
        return glob.glob(pattern_path)
    return []


# Configuration management
CONFIG_FILE = os.path.join(click.get_app_dir("mcli"), "config.json")


def save_global_value(value):
    """Save a global configuration value"""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump({"GLOBAL_VALUE": value}, f)


def load_global_value():
    """Load a global configuration value"""
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f).get("GLOBAL_VALUE")
    except FileNotFoundError:
        return None
