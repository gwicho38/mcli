import importlib.util
import sys

import click


def import_public_module(module_name: str):
    prefix = "mcli.public."
    spec = importlib.util.find_spec(prefix + module_name)
    if spec is None:
        from mcli.lib.logger.logger import get_logger

        logger = get_logger()
        logger.error("Module is not available")
        logger.error("Please install the module or consult current import statements")
        sys.exit(1)

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@click.group(name="lib")
def lib():
    pass


if __name__ == "__main__":
    lib()
