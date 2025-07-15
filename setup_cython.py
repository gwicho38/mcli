#!/usr/bin/env python3
"""
Cython setup for mcli executable.
This compiles the main application into a C extension for better performance.
"""

from setuptools import setup, Extension
from Cython.Build import cythonize
import os
import sys
from pathlib import Path

# Get the project root
project_root = Path(__file__).parent
src_path = project_root / "src"

# Define the main extension
main_extension = Extension(
    "mcli_main",
    sources=["cython_main.pyx"],
    extra_compile_args=["-O3", "-march=native"],
    extra_link_args=["-O3"],
    language="c++"
)

# Define extensions for key modules
extensions = [
    main_extension,
]

# Cythonize with optimizations
cythonized_extensions = cythonize(
    extensions,
    compiler_directives={
        'language_level': 3,
        'boundscheck': False,
        'wraparound': False,
        'initializedcheck': False,
        'nonecheck': False,
        'cdivision': True,
        'embedsignature': True,
    }
)

setup(
    name="mcli-cython",
    version="5.0.0",
    description="Cython-compiled mcli executable",
    ext_modules=cythonized_extensions,
    zip_safe=False,
    install_requires=[
        'click',
        'rich',
    ],
) 