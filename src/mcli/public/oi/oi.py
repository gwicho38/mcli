import click

from mcli.lib.shell.shell import get_shell_script_path, shell_exec


@click.group(name="oi")
def oi():
    """Create an alpha tunnel using the instance"""
    scripts_path = get_shell_script_path("oi", __name__)
    shell_exec(scripts_path, "oi")
    pass


if __name__ == "__main__":
    oi()
