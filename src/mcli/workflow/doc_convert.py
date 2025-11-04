"""
Document conversion workflow with multiple fallback strategies and temp directory isolation.

A robust wrapper around pandoc, nbconvert, and other conversion tools
with automatic fallback to alternative methods when the primary method fails.
Uses temporary directory with hard links to avoid path issues.
"""

import os
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from glob import glob as file_glob
from pathlib import Path
from typing import List, Optional, Tuple

import click

from mcli.lib.logger.logger import get_logger
from mcli.lib.paths import get_custom_commands_dir
from mcli.lib.ui.styling import error, info, success, warning

logger = get_logger()

# Format aliases to handle common abbreviations and file extensions
FORMAT_ALIASES = {
    # Markdown variants
    "md": "markdown",
    "markdown": "markdown",
    "gfm": "gfm",  # GitHub Flavored Markdown
    # Document formats
    "doc": "docx",
    "docx": "docx",
    "odt": "odt",
    # Markup formats
    "html": "html",
    "htm": "html",
    "xhtml": "html",
    # PDF
    "pd": "pd",
    # LaTeX
    "tex": "latex",
    "latex": "latex",
    # Jupyter
    "ipynb": "ipynb",
    "notebook": "ipynb",
    # Text formats
    "txt": "plain",
    "text": "plain",
    "plain": "plain",
    # Presentation formats
    "pptx": "pptx",
    "ppt": "pptx",
    # Other formats
    "rst": "rst",
    "org": "org",
    "mediawiki": "mediawiki",
    "textile": "textile",
    "rt": "rt",
    "epub": "epub",
}


class ConversionMethod(Enum):
    """Available conversion methods."""

    PANDOC = "pandoc"
    NBCONVERT = "nbconvert"
    PANDOC_LATEX = "pandoc_latex"
    PANDOC_HTML_INTERMEDIATE = "pandoc_html_intermediate"


@dataclass
class ConversionStrategy:
    """Represents a conversion strategy with command and description."""

    method: ConversionMethod
    description: str
    check_command: Optional[str] = None


def get_temp_conversion_dir() -> Path:
    """Get or create temporary conversion directory in ~/.mcli/commands/temp/."""
    commands_dir = get_custom_commands_dir()
    temp_dir = commands_dir / "temp" / "conversions"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def create_temp_hardlink(source_path: Path) -> Tuple[Path, Path]:
    """
    Create a hard link to the source file in temp directory.

    Returns: (temp_file_path, temp_dir_path)
    """
    temp_base = get_temp_conversion_dir()

    # Create unique temp directory for this conversion
    temp_dir = temp_base / f"conv_{os.getpid()}_{source_path.stem}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Create hard link with simple name (avoids path issues)
    temp_file = temp_dir / source_path.name

    try:
        # Try hard link first (most efficient)
        os.link(source_path, temp_file)
        logger.debug(f"Created hard link: {temp_file}")
    except (OSError, NotImplementedError):
        # Fall back to copy if hard link not supported (e.g., across filesystems)
        shutil.copy2(source_path, temp_file)
        logger.debug(f"Created copy (hard link not available): {temp_file}")

    return temp_file, temp_dir


def cleanup_temp_conversion(temp_dir: Path, preserve_output: Optional[Path] = None):
    """
    Clean up temporary conversion directory.

    Args:
        temp_dir: Temporary directory to clean up
        preserve_output: If specified, copy this file out before cleanup
    """
    try:
        if preserve_output and preserve_output.exists():
            # Output file is already in temp_dir, we'll handle it separately
            pass

        # Remove the entire temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            logger.debug(f"Cleaned up temp directory: {temp_dir}")
    except Exception as e:
        logger.warning(f"Failed to clean up temp directory {temp_dir}: {e}")


def get_conversion_strategies(
    input_path: Path, output_path: Path, from_format: str, to_format: str, pandoc_args: str = ""
) -> List[ConversionStrategy]:
    """
    Get ordered list of conversion strategies to try based on input/output formats.

    Returns strategies in priority order (most likely to succeed first).
    """
    strategies = []

    # Special handling for Jupyter notebook to PDF (notoriously problematic)
    if from_format == "ipynb" and to_format == "pd":
        # Strategy 1: nbconvert (most reliable for notebooks)
        strategies.append(
            ConversionStrategy(
                method=ConversionMethod.NBCONVERT,
                description="jupyter nbconvert (best for notebooks)",
                check_command="jupyter-nbconvert",
            )
        )

        # Strategy 2: pandoc with pdflatex
        strategies.append(
            ConversionStrategy(
                method=ConversionMethod.PANDOC_LATEX, description="pandoc with pdflatex engine"
            )
        )

        # Strategy 3: pandoc via HTML intermediate
        strategies.append(
            ConversionStrategy(
                method=ConversionMethod.PANDOC_HTML_INTERMEDIATE,
                description="pandoc via HTML intermediate (wkhtmltopdf)",
            )
        )

        # Strategy 4: standard pandoc
        strategies.append(
            ConversionStrategy(method=ConversionMethod.PANDOC, description="pandoc default method")
        )

    # Jupyter to other formats
    elif from_format == "ipynb":
        # Try nbconvert first for notebooks
        strategies.append(
            ConversionStrategy(
                method=ConversionMethod.NBCONVERT,
                description="jupyter nbconvert",
                check_command="jupyter-nbconvert",
            )
        )
        strategies.append(ConversionStrategy(method=ConversionMethod.PANDOC, description="pandoc"))

    # PDF output (general)
    elif to_format == "pd":
        strategies.append(
            ConversionStrategy(
                method=ConversionMethod.PANDOC_LATEX, description="pandoc with LaTeX"
            )
        )
        strategies.append(
            ConversionStrategy(method=ConversionMethod.PANDOC, description="pandoc default")
        )

    # Default: just use pandoc
    else:
        strategies.append(ConversionStrategy(method=ConversionMethod.PANDOC, description="pandoc"))

    return strategies


def execute_conversion_strategy(
    strategy: ConversionStrategy,
    input_path: Path,
    output_path: Path,
    from_format: str,
    to_format: str,
    pandoc_args: str = "",
) -> Tuple[bool, str]:
    """
    Execute a specific conversion strategy in a temp directory.

    Returns: (success: bool, error_message: str)
    """
    # Create temp hard link for conversion
    temp_input, temp_dir = create_temp_hardlink(input_path)
    temp_output = temp_dir / f"{input_path.stem}.{to_format.lower()}"

    try:
        if strategy.method == ConversionMethod.NBCONVERT:
            # Check if nbconvert is available
            check = subprocess.run(
                ["jupyter", "nbconvert", "--version"], capture_output=True, timeout=5
            )
            if check.returncode != 0:
                return False, "jupyter nbconvert not available"

            # Build nbconvert command (run in temp directory)
            cmd = [
                "jupyter",
                "nbconvert",
                "--to",
                to_format,
                "--output",
                str(temp_output),
                str(temp_input),
            ]

            # Run in temp directory
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, timeout=120, cwd=str(temp_dir)
            )

        elif strategy.method == ConversionMethod.PANDOC_LATEX:
            # Pandoc with explicit LaTeX engine (xelatex for better Unicode support)
            cmd = [
                "pandoc",
                str(temp_input),
                "-",
                from_format,
                "-o",
                str(temp_output),
                "--pdf-engine=xelatex",
            ]
            if pandoc_args:
                cmd.extend(pandoc_args.split())

            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, timeout=120, cwd=str(temp_dir)
            )

        elif strategy.method == ConversionMethod.PANDOC_HTML_INTERMEDIATE:
            # Convert to HTML first, then to PDF
            html_temp = temp_dir / f"{input_path.stem}_temp.html"

            # Step 1: Convert to HTML
            cmd_html = [
                "pandoc",
                str(temp_input),
                "-",
                from_format,
                "-t",
                "html",
                "-o",
                str(html_temp),
                "--standalone",
            ]
            result = subprocess.run(
                cmd_html, capture_output=True, text=True, timeout=120, cwd=str(temp_dir)
            )
            if result.returncode != 0:
                return False, f"HTML intermediate failed: {result.stderr}"

            # Step 2: Convert HTML to PDF
            cmd = ["pandoc", str(html_temp), "-", "html", "-t", "pd", "-o", str(temp_output)]

            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, timeout=120, cwd=str(temp_dir)
            )

        else:  # PANDOC
            # Standard pandoc conversion
            cmd = ["pandoc", str(temp_input), "-", from_format, "-o", str(temp_output)]
            # Use xelatex for PDF conversions (better Unicode support)
            if to_format == "pd":
                cmd.append("--pdf-engine=xelatex")
            if pandoc_args:
                cmd.extend(pandoc_args.split())

            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, timeout=120, cwd=str(temp_dir)
            )

        # Copy output file to final destination
        if temp_output.exists():
            shutil.copy2(temp_output, output_path)
            return True, ""
        else:
            return False, "Output file not created"

    except subprocess.TimeoutExpired:
        return False, "Conversion timed out (>120s)"
    except subprocess.CalledProcessError as e:
        return False, e.stderr or str(e)
    except Exception as e:
        return False, str(e)
    finally:
        # Always clean up temp directory
        cleanup_temp_conversion(temp_dir)


@click.group(name="doc-convert")
def doc_convert():
    """Document conversion with automatic fallback strategies."""


@doc_convert.command()
def init():
    """
    Install all necessary dependencies for document conversion via Homebrew.

    This will install:
    - pandoc: Universal document converter
    - basictex: LaTeX distribution for PDF generation
    - jupyter & nbconvert: Best for converting Jupyter notebooks
    """
    info("=" * 60)
    info("📦 Installing doc-convert dependencies")
    info("=" * 60)
    info("")

    # Check if Homebrew is installed
    try:
        subprocess.run(["brew", "--version"], capture_output=True, check=True)
        success("✅ Homebrew is installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        error("❌ Homebrew is not installed. Install it from https://brew.sh")
        return

    info("")

    # Install pandoc
    info("📥 Installing pandoc...")
    try:
        result = subprocess.run(["brew", "install", "pandoc"], capture_output=True, text=True)
        if result.returncode == 0:
            success("   ✅ pandoc installed successfully")
        else:
            check = subprocess.run(["which", "pandoc"], capture_output=True)
            if check.returncode == 0:
                info("   ℹ️  pandoc is already installed")
            else:
                error(f"   ❌ Failed to install pandoc: {result.stderr}")
    except Exception as e:
        error(f"   ❌ Error installing pandoc: {e}")

    info("")

    # Install Jupyter and nbconvert
    info("📥 Installing Jupyter & nbconvert (for notebook conversion)...")
    try:
        # Check if already installed
        check = subprocess.run(["jupyter", "nbconvert", "--version"], capture_output=True)
        if check.returncode == 0:
            info("   ℹ️  jupyter nbconvert is already installed")
        else:
            # Try installing via pip
            result = subprocess.run(
                ["pip3", "install", "jupyter", "nbconvert"], capture_output=True, text=True
            )
            if result.returncode == 0:
                success("   ✅ jupyter & nbconvert installed successfully")
            else:
                warning("   ⚠️  Could not install jupyter via pip")
                info("   ℹ️  You can install manually: pip3 install jupyter nbconvert")
    except Exception as e:
        warning(f"   ⚠️  Error installing jupyter: {e}")
        info("   ℹ️  Jupyter is optional but recommended for .ipynb conversions")

    info("")

    # Install BasicTeX (lightweight LaTeX for PDF support)
    info("📥 Installing BasicTeX (for PDF generation)...")
    info("   ℹ️  This is a large download (~100MB) and may take a few minutes")
    try:
        result = subprocess.run(
            ["brew", "install", "--cask", "basictex"], capture_output=True, text=True
        )
        if result.returncode == 0:
            success("   ✅ BasicTeX installed successfully")
            info(
                "   ℹ️  You may need to restart your terminal or run: eval $(/usr/libexec/path_helper)"
            )
            info("")
            info("   📦 Installing LaTeX packages for document conversion...")
            info("   ℹ️  This requires sudo access and may take a few minutes")
            info("")
            info("   RECOMMENDED (installs all common packages + fonts):")
            info("   sudo tlmgr install collection-latexextra collection-fontsrecommended")
            info("   sudo mktexlsr")
            info("")
            info("   OR install individual packages:")
            info("   sudo tlmgr install tcolorbox environ pgf tools pdfcol \\")
            info("                       adjustbox collectbox xkeyval \\")
            info("                       booktabs ulem titling enumitem soul \\")
            info("                       jknapltx rsfs")
            info("   sudo tlmgr install collection-fontsrecommended")
            info("   sudo mktexlsr")
        else:
            check = subprocess.run(["which", "pdflatex"], capture_output=True)
            if check.returncode == 0:
                info("   ℹ️  LaTeX is already installed")
            else:
                warning("   ⚠️  BasicTeX installation may have failed")
                info("   ℹ️  You can skip this for non-PDF conversions")
    except Exception as e:
        warning(f"   ⚠️  Error installing BasicTeX: {e}")
        info("   ℹ️  BasicTeX is only needed for PDF conversions")

    info("")
    info("=" * 60)
    success("✨ Installation complete!")
    info("=" * 60)
    info("")
    info("Installed tools:")
    info("  • pandoc - Universal document converter (with XeLaTeX for Unicode support)")
    info("  • jupyter nbconvert - Best for Jupyter notebooks")
    info("  • basictex - LaTeX for PDF generation")
    info("")
    info("⚠️  IMPORTANT: For Jupyter notebook → PDF conversions:")
    info("   Install required LaTeX packages (requires sudo):")
    info("")
    info("   RECOMMENDED (installs all common packages + fonts):")
    info("   sudo tlmgr install collection-latexextra collection-fontsrecommended")
    info("   sudo mktexlsr")
    info("")
    info("   OR install individual packages:")
    info("   sudo tlmgr install tcolorbox environ pgf tools pdfcol \\")
    info("                       adjustbox collectbox xkeyval \\")
    info("                       booktabs ulem titling enumitem soul \\")
    info("                       jknapltx rsfs")
    info("   sudo tlmgr install collection-fontsrecommended")
    info("   sudo mktexlsr")
    info("")
    info("💡 NOTE: The converter uses XeLaTeX for better Unicode/emoji support")
    info("   in documents. Fallback strategies handle most edge cases.")
    info("")
    info("You can now use: mcli workflow doc-convert convert <from> <to> <file>")
    info("Example: mcli workflow doc-convert convert ipynb pdf notebook.ipynb")
    info("")
    info("To uninstall dependencies later:")
    info("  mcli workflow doc-convert cleanup")
    info("")


@doc_convert.command()
@click.argument("from_format")
@click.argument("to_format")
@click.argument("path")
@click.option("--output-dir", "-o", help="Output directory (defaults to same directory as input)")
@click.option("--pandoc-args", "-a", help="Additional pandoc arguments", default="")
@click.option(
    "--no-fallback", is_flag=True, help="Disable fallback strategies (use only primary method)"
)
def convert(from_format, to_format, path, output_dir, pandoc_args, no_fallback):
    """
    Convert documents with automatic fallback strategies.

    FROM_FORMAT: Source format (e.g., ipynb, md, docx, html)

    TO_FORMAT: Target format (e.g., pdf, html, md, docx)

    PATH: File path or glob pattern (e.g., "*.ipynb" or "./notebook.ipynb")

    The converter will try multiple conversion methods automatically:
    - For Jupyter notebooks: tries nbconvert, then pandoc with various engines
    - For PDF output: tries LaTeX engine, then alternative methods
    - Falls back gracefully when primary method fails

    All conversions are performed in a temporary directory to avoid path issues
    with spaces or special characters.

    Examples:

        # Convert Jupyter notebook to PDF (tries nbconvert first)
        mcli workflow doc-convert convert ipynb pdf notebook.ipynb

        # Convert markdown to HTML
        mcli workflow doc-convert convert md html README.md

        # Convert all markdown files with custom output directory
        mcli workflow doc-convert convert md pdf "*.md" -o ./pdfs
    """
    # Check if pandoc is installed (primary tool)
    has_pandoc = False
    try:
        subprocess.run(["pandoc", "--version"], capture_output=True, check=True)
        has_pandoc = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Check if nbconvert is available
    has_nbconvert = False
    try:
        subprocess.run(["jupyter", "nbconvert", "--version"], capture_output=True, check=True)
        has_nbconvert = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Require at least one conversion tool
    if not has_pandoc and not has_nbconvert:
        error("❌ No conversion tools found!")
        error("   Install with: mcli workflow doc-convert init")
        error("   Or: brew install pandoc")
        return

    # Map format aliases
    from_format_mapped = FORMAT_ALIASES.get(from_format.lower(), from_format)
    to_format_mapped = FORMAT_ALIASES.get(to_format.lower(), to_format)
    output_ext = to_format.lower()

    # Expand path
    expanded_path = os.path.expanduser(path)

    # Handle glob patterns
    if "*" in expanded_path or "?" in expanded_path or "[" in expanded_path:
        files = file_glob(expanded_path, recursive=True)
        if not files:
            error(f"❌ No files found matching pattern: {path}")
            return
        info(f"📁 Found {len(files)} file(s) matching pattern: {path}")
    else:
        files = [expanded_path]

    # Process each file
    success_count = 0
    error_count = 0
    conversion_methods_used = {}

    for input_file in files:
        input_path = Path(input_file).resolve()  # Get absolute path

        if not input_path.exists():
            warning(f"⚠️  File not found: {input_file}")
            error_count += 1
            continue

        # Determine output path
        if output_dir:
            output_path = Path(output_dir) / f"{input_path.stem}.{output_ext}"
            os.makedirs(output_dir, exist_ok=True)
        else:
            output_path = input_path.parent / f"{input_path.stem}.{output_ext}"

        info(f"🔄 Converting: {input_path.name} → {output_path.name}")
        info("   📁 Using temp directory: ~/.mcli/commands/temp/conversions/")

        # Get conversion strategies
        strategies = get_conversion_strategies(
            input_path, output_path, from_format_mapped, to_format_mapped, pandoc_args
        )

        # Limit to first strategy if no-fallback is set
        if no_fallback:
            strategies = strategies[:1]

        # Try each strategy in order
        conversion_succeeded = False
        last_error = ""

        for i, strategy in enumerate(strategies):
            if i > 0:
                info(f"   ⚙️  Trying fallback method: {strategy.description}")
            else:
                info(f"   ⚙️  Using: {strategy.description}")

            success_flag, error_msg = execute_conversion_strategy(
                strategy, input_path, output_path, from_format_mapped, to_format_mapped, pandoc_args
            )

            if success_flag:
                conversion_succeeded = True
                method_name = strategy.description
                conversion_methods_used[method_name] = (
                    conversion_methods_used.get(method_name, 0) + 1
                )
                success(f"   ✅ Created: {output_path}")
                if i > 0:
                    info(f"   ℹ️  Succeeded with fallback method #{i + 1}")
                break
            else:
                last_error = error_msg
                if i < len(strategies) - 1:
                    warning(f"   ⚠️  {strategy.description} failed, trying next method...")

        if conversion_succeeded:
            success_count += 1
        else:
            error("   ❌ All conversion methods failed")
            if last_error:
                error(f"   ℹ️  Last error: {last_error[:200]}")
            error_count += 1

    # Summary
    info("")
    info("=" * 60)
    success("✨ Conversion complete!")
    info(f"   ✅ Successful: {success_count}")
    if error_count > 0:
        error(f"   ❌ Failed: {error_count}")

    # Show which methods were used
    if conversion_methods_used:
        info("")
        info("Methods used:")
        for method, count in conversion_methods_used.items():
            info(f"  • {method}: {count} file(s)")

    info("=" * 60)


@doc_convert.command()
def cleanup():
    """
    Generate a cleanup script to uninstall doc-convert dependencies.

    This command creates a shell script that you can review and run to
    uninstall all the dependencies installed by the init command.

    The script will be created at: ~/.mcli/commands/doc-convert-cleanup.sh
    """
    import os

    info("=" * 60)
    info("📦 Generating cleanup script")
    info("=" * 60)
    info("")

    cleanup_script = """#!/bin/bash
# doc-convert Cleanup Script
# This script uninstalls dependencies installed by 'mcli workflow doc-convert init'
#
# WARNING: Review this script before running it!
# Some of these tools may be used by other applications.

set -e

echo "================================"
echo "doc-convert Dependency Cleanup"
echo "================================"
echo ""
echo "This will uninstall the following:"
echo "  • pandoc (universal document converter)"
echo "  • basictex (LaTeX distribution)"
echo "  • jupyter & nbconvert (Jupyter tools)"
echo "  • LaTeX packages (collection-latexextra, collection-fontsrecommended)"
echo ""
read -p "Continue with uninstall? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 0
fi

echo ""
echo "Uninstalling Homebrew packages..."

# Uninstall pandoc
if brew list pandoc &>/dev/null; then
    echo "  Uninstalling pandoc..."
    brew uninstall pandoc
else
    echo "  pandoc not installed via Homebrew"
fi

# Uninstall BasicTeX
if brew list basictex &>/dev/null; then
    echo "  Uninstalling basictex..."
    brew uninstall --cask basictex

    # Remove LaTeX distribution directory
    if [ -d "/usr/local/texlive/2025basic" ]; then
        echo "  Removing LaTeX directory..."
        sudo rm -rf /usr/local/texlive/2025basic
    fi
else
    echo "  basictex not installed via Homebrew"
fi

echo ""
echo "Uninstalling Python packages..."

# Uninstall jupyter and nbconvert from pyenv Python
PYENV_VERSION=$(pyenv version-name 2>/dev/null || echo "")
if [ -n "$PYENV_VERSION" ]; then
    echo "  Current pyenv version: $PYENV_VERSION"
    if command -v pip &> /dev/null; then
        echo "  Uninstalling jupyter..."
        pip uninstall -y jupyter jupyter-core jupyterlab nbconvert 2>/dev/null || true
    fi
else
    echo "  pyenv not active or not installed"
fi

echo ""
echo "================================"
echo "Cleanup Complete!"
echo "================================"
echo ""
echo "The following may still exist:"
echo "  • ~/.mcli/commands/temp/ (conversion temp directory)"
echo "  • Other LaTeX installations (if installed separately)"
echo ""
echo "To remove the temp directory:"
echo "  rm -rf ~/.mcli/commands/temp/"
echo ""
"""

    # Write cleanup script
    commands_dir = get_custom_commands_dir()
    cleanup_path = commands_dir / "doc-convert-cleanup.sh"

    with open(cleanup_path, "w") as f:
        f.write(cleanup_script)

    # Make it executable
    os.chmod(cleanup_path, 0o755)

    success(f"✅ Cleanup script created: {cleanup_path}")
    info("")
    info("To review the script:")
    info(f"  cat {cleanup_path}")
    info("")
    info("To run the cleanup:")
    info(f"  bash {cleanup_path}")
    info("")
    warning("⚠️  IMPORTANT: Review the script before running it!")
    warning("   Some dependencies may be used by other applications.")
    info("")
    info("=" * 60)


if __name__ == "__main__":
    doc_convert()
