"""IPFS management commands for mcli self.

Provides setup, status, and doctor subcommands for managing the
local IPFS (Kubo) installation used by ``mcli sync``.
"""

import subprocess
import time

import click
from rich.console import Console
from rich.table import Table

from mcli.lib.constants import IpfsDefaults, IpfsMessages
from mcli.lib.ipfs_utils import (
    check_port_available,
    detect_platform,
    ipfs_config_get,
    ipfs_daemon_running,
    ipfs_id_info,
    ipfs_initialized,
    ipfs_installed,
    ipfs_peer_count,
    ipfs_version,
    validate_ipfs_config,
    which_package_manager,
)
from mcli.lib.logger.logger import get_logger

logger = get_logger()
console = Console()


@click.group(name="ipfs")
def ipfs():
    """🌐 Manage IPFS daemon for workflow sync."""
    pass


# ------------------------------------------------------------------
# setup
# ------------------------------------------------------------------


@ipfs.command()
@click.option(
    "--auto", "auto_install", is_flag=True, help="Auto-install via detected package manager"
)
@click.option("--no-install", is_flag=True, help="Skip installation step")
def setup(auto_install: bool, no_install: bool):
    """🚀 Install, initialize, and start IPFS.

    Walks through the full IPFS setup:
    1. Detect OS and package manager
    2. Install IPFS (unless --no-install)
    3. Initialize the IPFS repository
    4. Start the daemon in the background

    Examples:
        mcli self ipfs setup              # Guided setup
        mcli self ipfs setup --auto       # Auto-install via package manager
        mcli self ipfs setup --no-install # Skip installation step
    """
    console.print(IpfsMessages.SETUP_HEADER)
    console.print()

    os_name, arch = detect_platform()

    # --- Step 1: Check / Install ---
    if ipfs_installed():
        ver = ipfs_version() or "unknown"
        console.print(f"{IpfsMessages.IPFS_INSTALLED} ({ver})")
    elif no_install:
        console.print(IpfsMessages.SETUP_SKIP_INSTALL)
        console.print(IpfsMessages.IPFS_NOT_INSTALLED)
        console.print()
        _show_manual_instructions(os_name)
        return
    else:
        console.print(IpfsMessages.IPFS_NOT_INSTALLED)
        pm = which_package_manager()

        if pm and auto_install:
            _do_install(pm)
            if not ipfs_installed():
                return
        elif pm:
            console.print(f"[dim]Detected package manager: {pm}[/dim]")
            console.print(
                f"[dim]Run with --auto to install automatically, " f"or install manually:[/dim]"
            )
            console.print()
            _show_manual_instructions(os_name)
            return
        else:
            console.print(IpfsMessages.SETUP_NO_PKG_MANAGER)
            console.print()
            _show_manual_instructions(os_name)
            return

    # --- Step 2: Initialize ---
    if ipfs_initialized():
        console.print(IpfsMessages.IPFS_INITIALIZED)
    else:
        console.print(IpfsMessages.SETUP_INITIALIZING)
        result = subprocess.run(
            ["ipfs", "init"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            console.print(IpfsMessages.SETUP_INIT_FAILED.format(error=result.stderr.strip()))
            return
        console.print(IpfsMessages.SETUP_INIT_SUCCESS)

    # --- Step 3: Start daemon ---
    if ipfs_daemon_running():
        console.print(IpfsMessages.IPFS_DAEMON_RUNNING)
        console.print()
        console.print(IpfsMessages.SETUP_ALREADY_COMPLETE)
        return

    console.print(IpfsMessages.SETUP_STARTING_DAEMON)
    process = subprocess.Popen(
        ["ipfs", "daemon"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    for _ in range(int(IpfsDefaults.DAEMON_POLL_TIMEOUT / IpfsDefaults.DAEMON_POLL_INTERVAL)):
        time.sleep(IpfsDefaults.DAEMON_POLL_INTERVAL)
        if ipfs_daemon_running():
            break

    if ipfs_daemon_running():
        console.print(IpfsMessages.SETUP_DAEMON_STARTED.format(pid=process.pid))
        console.print()
        console.print(IpfsMessages.SETUP_COMPLETE)
    else:
        console.print(IpfsMessages.SETUP_DAEMON_FAILED)
        console.print(IpfsMessages.SETUP_DAEMON_HINT)


def _do_install(pm: str):
    """Run the install command for the given package manager."""
    cmd = IpfsDefaults.INSTALL_COMMANDS.get(pm)
    if not cmd:
        console.print(IpfsMessages.SETUP_NO_PKG_MANAGER)
        return

    console.print(IpfsMessages.SETUP_INSTALLING.format(manager=pm))
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        console.print(IpfsMessages.SETUP_INSTALL_FAILED.format(manager=pm))
    else:
        console.print(IpfsMessages.SETUP_INSTALL_SUCCESS)


def _show_manual_instructions(os_name: str):
    """Print platform-appropriate manual install instructions."""
    console.print(IpfsMessages.SETUP_MANUAL_INSTRUCTIONS)
    if os_name == "darwin":
        console.print(IpfsMessages.SETUP_MACOS_INSTALL)
    elif os_name.startswith("linux"):
        console.print(IpfsMessages.SETUP_LINUX_APT_INSTALL)
        console.print(IpfsMessages.SETUP_LINUX_DNF_INSTALL)
    elif os_name == "win32":
        console.print(IpfsMessages.SETUP_WINDOWS_WINGET)
        console.print(IpfsMessages.SETUP_WINDOWS_CHOCO)
    else:
        console.print(f"  [dim]{IpfsMessages.SETUP_MANUAL_INSTALL}[/dim]")


# ------------------------------------------------------------------
# status
# ------------------------------------------------------------------


@ipfs.command()
def status():
    """📊 Show current IPFS installation and daemon status.

    Displays a summary table with installation state, version, daemon
    status, peer count, peer ID, and API/gateway endpoints.

    Examples:
        mcli self ipfs status
    """
    console.print(IpfsMessages.STATUS_HEADER)
    console.print()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="cyan")
    table.add_column("Value")

    installed = ipfs_installed()
    table.add_row("Installed", "[green]Yes[/green]" if installed else "[red]No[/red]")

    if not installed:
        console.print(table)
        console.print()
        console.print(IpfsMessages.STATUS_NOT_INSTALLED_HINT)
        return

    ver = ipfs_version()
    table.add_row("Version", ver or "[dim]unknown[/dim]")

    inited = ipfs_initialized()
    table.add_row("Initialized", "[green]Yes[/green]" if inited else "[yellow]No[/yellow]")

    if not inited:
        console.print(table)
        console.print()
        console.print(IpfsMessages.STATUS_NOT_INITIALIZED_HINT)
        return

    running = ipfs_daemon_running()
    table.add_row("Daemon running", "[green]Yes[/green]" if running else "[yellow]No[/yellow]")

    if running:
        peers = ipfs_peer_count()
        table.add_row("Peers", str(peers) if peers is not None else "[dim]unknown[/dim]")

        id_info = ipfs_id_info()
        if id_info:
            peer_id = id_info.get("ID", "unknown")
            table.add_row("Peer ID", f"[dim]{peer_id[:16]}...[/dim]")

        api_addr = ipfs_config_get("Addresses.API")
        gateway_addr = ipfs_config_get("Addresses.Gateway")
        table.add_row("API", api_addr or IpfsDefaults.API_ADDRESS)
        table.add_row("Gateway", gateway_addr or IpfsDefaults.GATEWAY_ADDRESS)
    else:
        console.print(table)
        console.print()
        console.print(IpfsMessages.STATUS_DAEMON_HINT)
        return

    console.print(table)


# ------------------------------------------------------------------
# doctor
# ------------------------------------------------------------------


@ipfs.command()
def doctor():
    """🩺 Run IPFS diagnostic checks.

    Performs six health checks and reports OK / WARN / FAIL for each:
    1. Binary in PATH
    2. Repository initialized
    3. Config file valid
    4. Port availability (API, gateway, swarm)
    5. Daemon responsiveness
    6. Peer connectivity

    Examples:
        mcli self ipfs doctor
    """
    console.print(IpfsMessages.DOCTOR_HEADER)
    console.print(IpfsMessages.DOCTOR_RUNNING)
    console.print()

    issues = 0

    # 1. Binary
    if ipfs_installed():
        _doctor_row(IpfsMessages.DOCTOR_CHECK_BINARY, IpfsMessages.DOCTOR_OK)
    else:
        _doctor_row(IpfsMessages.DOCTOR_CHECK_BINARY, IpfsMessages.DOCTOR_FAIL)
        console.print(IpfsMessages.DOCTOR_FIX_INSTALL)
        issues += 1
        # Cannot continue further checks without the binary
        console.print()
        console.print(IpfsMessages.DOCTOR_ISSUES_FOUND.format(count=issues))
        return

    # 2. Initialized
    if ipfs_initialized():
        _doctor_row(IpfsMessages.DOCTOR_CHECK_INIT, IpfsMessages.DOCTOR_OK)
    else:
        _doctor_row(IpfsMessages.DOCTOR_CHECK_INIT, IpfsMessages.DOCTOR_FAIL)
        console.print(IpfsMessages.DOCTOR_FIX_INIT)
        issues += 1

    # 3. Config valid
    if validate_ipfs_config():
        _doctor_row(IpfsMessages.DOCTOR_CHECK_CONFIG, IpfsMessages.DOCTOR_OK)
    else:
        _doctor_row(IpfsMessages.DOCTOR_CHECK_CONFIG, IpfsMessages.DOCTOR_WARN)
        console.print(IpfsMessages.DOCTOR_FIX_CONFIG)
        issues += 1

    # 4. Ports
    for label_tmpl, port in [
        (IpfsMessages.DOCTOR_CHECK_PORT_API, IpfsDefaults.API_PORT),
        (IpfsMessages.DOCTOR_CHECK_PORT_GATEWAY, IpfsDefaults.GATEWAY_PORT),
        (IpfsMessages.DOCTOR_CHECK_PORT_SWARM, IpfsDefaults.SWARM_PORT),
    ]:
        label = label_tmpl.format(port=port)
        port_free = check_port_available(port)
        daemon_up = ipfs_daemon_running()
        if port_free or daemon_up:
            # Port occupied by IPFS itself is fine
            _doctor_row(label, IpfsMessages.DOCTOR_OK)
        else:
            _doctor_row(label, IpfsMessages.DOCTOR_WARN)
            console.print(IpfsMessages.DOCTOR_FIX_PORT.format(port=port))
            issues += 1

    # 5. Daemon responsive
    if ipfs_daemon_running():
        _doctor_row(IpfsMessages.DOCTOR_CHECK_DAEMON, IpfsMessages.DOCTOR_OK)
    else:
        _doctor_row(IpfsMessages.DOCTOR_CHECK_DAEMON, IpfsMessages.DOCTOR_FAIL)
        console.print(IpfsMessages.DOCTOR_FIX_DAEMON)
        issues += 1

    # 6. Peer connectivity
    if ipfs_daemon_running():
        peers = ipfs_peer_count()
        if peers is not None and peers > 0:
            _doctor_row(
                IpfsMessages.DOCTOR_CHECK_PEERS,
                f"{IpfsMessages.DOCTOR_OK} ({peers} peers)",
            )
        else:
            _doctor_row(IpfsMessages.DOCTOR_CHECK_PEERS, IpfsMessages.DOCTOR_WARN)
            console.print(IpfsMessages.DOCTOR_FIX_PEERS)
            issues += 1
    else:
        _doctor_row(IpfsMessages.DOCTOR_CHECK_PEERS, IpfsMessages.DOCTOR_WARN)
        console.print(IpfsMessages.DOCTOR_FIX_DAEMON)
        issues += 1

    console.print()
    if issues == 0:
        console.print(IpfsMessages.DOCTOR_ALL_PASSED)
    else:
        console.print(IpfsMessages.DOCTOR_ISSUES_FOUND.format(count=issues))


def _doctor_row(label: str, result: str):
    """Print a single doctor check row."""
    console.print(f"  {result}  {label}")
