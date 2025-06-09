#!/usr/bin/env python
from Cython.Build import cythonize
import os
import sys
from pathlib import Path


def get_extension_modules():
    """Get all .py files in the lpy project for compilation."""
    # Get the src directory path
    src_dir = Path(__file__).parent / "src"
    
    # Check if src/lpy directory exists
    lpy_dir = src_dir / "mcli"
    if not lpy_dir.exists():
        logger.info(f"Warning: lpy directory not found at {lpy_dir}")
        return []
    
    # Files/directories to exclude from compilation
    excluded_paths = [
        "__pycache__",
        ".ipynb_checkpoints",
        "test",
        "tests",
    ]
    
    # Modules that might cause issues with Cython (typically GUI, plugin systems, etc.)
    # Add to this list if you encounter compilation problems
    excluded_modules = []
    
    # Find all Python files recursively
    all_py_files = []
    
    for root, dirs, files in os.walk(lpy_dir):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in excluded_paths]
        
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                
                # Check if file is in excluded modules
                if any(excluded in str(file_path) for excluded in excluded_modules):
                    continue
                
                # Skip __init__.py files as they're often not beneficial to compile
                if file == "__init__.py":
                    continue
                
                all_py_files.append(str(file_path))
    
    if not all_py_files:
        logger.info("Warning: No Python files found to compile")
        return []
    
    logger.info(f"Found {len(all_py_files)} Python files for compilation")
    return all_py_files


def build(setup_kwargs):
    """
    Build function for poetry/setup.py.
    """
    try:
        extension_modules = get_extension_modules()

        if extension_modules:
            logger.info(f"Building extensions for {len(extension_modules)} modules")
            # logger.info a few example modules for verification
            for module in extension_modules[:5]:
                logger.info(f"  - {module}")
            if len(extension_modules) > 5:
                logger.info(f"  - ... and {len(extension_modules) - 5} more")
                
            setup_kwargs.update(
                {
                    "ext_modules": cythonize(
                        extension_modules,
                        compiler_directives={
                            "language_level": sys.version_info[0],
                            "boundscheck": False,
                            "wraparound": False,
                            "initializedcheck": False,
                            "nonecheck": False,
                        },
                    )
                }
            )
        else:
            logger.info("No extensions to build")
    except Exception as e:
        logger.info(f"Error during build: {e}")
        if "ext_modules" in setup_kwargs:
            del setup_kwargs["ext_modules"]


if __name__ == "__main__":
    logger.info("This script is meant to be used by poetry/setup.py")
    
    # If run directly, logger.info the modules that would be compiled
    modules = get_extension_modules()
    logger.info(f"\nWould compile {len(modules)} modules:")
    for module in modules:
        logger.info(f"  {module}")