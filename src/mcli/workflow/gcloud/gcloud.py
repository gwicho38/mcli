import click

# from mcli.public.mcli.lib.shell.shell import shell_exec, get_shell_script_path
from mcli.lib.shell.shell import get_shell_script_path, shell_exec


# Click CLI group renamed to 'gcloud'
@click.group()
def gcloud():
    """gcloud utility - use this to interact with gcloud"""
    pass


@click.command()
def start():
    """Start a gcloud instance"""
    scripts_path = get_shell_script_path("gcloud", __file__)
    shell_exec(scripts_path, "start")


@gcloud.command()
def stop():
    """Start a gcloud instance"""
    scripts_path = get_shell_script_path("gcloud", __file__)
    shell_exec(scripts_path, "stop")


@gcloud.command()
def describe():
    """Start a gcloud instance"""
    scripts_path = get_shell_script_path("gcloud", __file__)
    shell_exec(scripts_path, "describe")


@gcloud.command()
@click.argument("remote-port", type=str)
@click.argument("local-port", type=str)
def tunnel(remote_port: str, local_port: str):
    """Create an alpha tunnel using the instance"""
    logger.info(f"Creating a tunnel at {remote_port} to local port {local_port}")
    scripts_path = get_shell_script_path("gcloud", __file__)
    shell_exec(scripts_path, "tunnel", remote_port, local_port)


@gcloud.command()
def login(remote_port: str, local_port: str):
    """Login to gcloud"""
    logger.info(f"Authenticating into gcloud")
    scripts_path = get_shell_script_path("gcloud", __file__)
    shell_exec(scripts_path, "login", remote_port, local_port)


gcloud.add_command(start)
gcloud.add_command(tunnel)


if __name__ == "__main__":
    gcloud()
