"""
Model command stub - redirects to workflow command in ~/.mcli/workflows/model.json

This stub exists for backwards compatibility with tests and imports.
The actual model command implementation is now in ~/.mcli/workflows/model.json
"""

import sys
from pathlib import Path

from mcli.lib.constants.paths import DirNames

# Try to load the model command from the workflow system
try:
    # Load model command from ~/.mcli/workflows/model.json (new path)
    # Fallback to ~/.mcli/commands/model.json (old path) for backwards compatibility
    model_json_path = Path.home() / DirNames.MCLI / "workflows" / "model.json"
    if not model_json_path.exists():
        model_json_path = Path.home() / DirNames.MCLI / "commands" / "model.json"

    if model_json_path.exists():
        # SECURITY: Do not execute arbitrary code from JSON files (fixes #165)
        # The model command should be registered through the workflow system instead
        import logging

        _logger = logging.getLogger(__name__)
        _logger.warning(
            "model.json contains executable code - skipping exec() for security. "
            "Use workflow system instead."
        )
        model = list = download = start = recommend = status = stop = pull = delete = None
    else:
        # If the JSON file doesn't exist, create empty placeholders
        print(f"Warning: {model_json_path} not found", file=sys.stderr)
        model = list = download = start = recommend = status = stop = pull = delete = None

except Exception as e:
    print(f"Error loading model command from workflow: {e}", file=sys.stderr)
    import traceback

    traceback.print_exc()
    model = list = download = start = recommend = status = stop = pull = delete = None

# Export the commands for backwards compatibility
__all__ = ["model", "list", "download", "start", "recommend", "status", "stop", "pull", "delete"]
