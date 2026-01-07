"""Context command for outputting agent documentation.

This command outputs documentation following the llms.txt convention,
designed for ML models and AI agents to quickly build context.
"""

import json as json_module
from functools import lru_cache
from pathlib import Path

import click

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


@lru_cache
def _get_version() -> str:
    """Get the current mcli version."""
    try:
        from importlib.metadata import version

        for pkg_name in ["mcli-framework", "mcli"]:
            try:
                return version(pkg_name)
            except Exception:
                continue
        return "unknown"
    except Exception:
        return "unknown"


def _generate_inline_llms_docs(full: bool = False) -> str:
    """Generate inline documentation if llms.txt files are not found."""
    version = _get_version()

    if full:
        return f"""# mcli-framework - Complete Agent Documentation

> Version {version} | Python >=3.10 | MIT License

## Quick Start for Agents

```bash
# 1. Verify installation
mcli self version

# 2. Initialize (if needed)
mcli init

# 3. List available workflows
mcli list --json

# 4. Run a workflow
mcli run <workflow_name> [args...]

# 5. Create new workflow if needed
mcli new my_task -l python --type command -d "Description" -t
```

## Core Commands

- `mcli run [opts] <cmd>`: Execute workflow commands (-g for global, -f for workspace)
- `mcli new <name>`: Create workflow (--type command|group, -l language)
- `mcli list`: List workflows (--json for machine-readable output)
- `mcli search <query>`: Search workflows
- `mcli sync`: IPFS sync and lockfile management

## Self-Management

- `mcli self version`: Show version info
- `mcli context`: This documentation
- `mcli self health`: Repository health
- `mcli self update`: Check for updates

## Best Practices for Agents

1. Always check `mcli list` first to see available workflows
2. Use `--json` flag for programmatic parsing
3. Capture stderr along with stdout for error messages
4. Check exit codes to determine success/failure

Repository: https://github.com/gwicho38/mcli
PyPI: https://pypi.org/project/mcli-framework/
"""
    else:
        return f"""# mcli-framework

> Portable workflow framework. Run `mcli context --full` for complete agent documentation.

Version: {version}

## Quick Reference

- `mcli run <cmd>`: Execute workflow commands
- `mcli list --json`: List workflows (JSON output)
- `mcli new <name> --type command -l python`: Create workflow
- `mcli context --full`: Full agent documentation
"""


@click.command("context")
@click.option("--full", "-f", is_flag=True, help="Output full documentation (llms-full.txt)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON for programmatic use")
def context(full: bool, as_json: bool):
    """🤖 Output comprehensive documentation for ML models and AI agents.

    Provides complete CRUD operations guide, language-specific examples,
    and workflow management instructions optimized for agent context building.
    Follows the llms.txt convention for AI-friendly documentation.

    Examples:
        mcli context           # Output llms.txt (index)
        mcli context --full    # Output complete documentation with all examples
        mcli context --json    # Output as JSON for programmatic use
    """
    # Find the llms.txt files relative to the package
    package_root = Path(__file__).parent.parent.parent.parent
    llms_txt = package_root / "llms.txt"
    llms_full_txt = package_root / "llms-full.txt"

    # Fallback to installed package location if not found
    if not llms_txt.exists():
        # Try site-packages location
        try:
            import mcli

            mcli_root = Path(mcli.__file__).parent.parent
            llms_txt = mcli_root / "llms.txt"
            llms_full_txt = mcli_root / "llms-full.txt"
        except Exception:
            pass

    target_file = llms_full_txt if full else llms_txt

    if as_json:
        # Output structured JSON for programmatic use
        output = {
            "version": _get_version(),
            "documentation_type": "full" if full else "index",
            "llms_txt_convention": "https://llmstxt.org/",
        }

        if target_file.exists():
            output["content"] = target_file.read_text()
            output["status"] = "success"
        else:
            output["content"] = _generate_inline_llms_docs(full)
            output["status"] = "generated"

        click.echo(json_module.dumps(output, indent=2))
    else:
        if target_file.exists():
            click.echo(target_file.read_text())
        else:
            # Generate inline documentation if files don't exist
            click.echo(_generate_inline_llms_docs(full))
