"""
Shell completion commands for MCLI

Provides commands to generate and install shell completion scripts
for bash, zsh, and fish shells.
"""

import os
from pathlib import Path

import click

from mcli.lib.ui.styling import success


@click.group(name="completion")
def completion():
    """Shell completion utilities"""
    pass


@completion.command(name="bash")
@click.pass_context
def bash_completion(ctx):
    """Generate bash completion script"""
    from click.shell_completion import BashComplete

    # Get the root CLI app
    app = ctx.find_root().command
    complete = BashComplete(app, {}, "mcli", "_MCLI_COMPLETE")
    script = complete.source()

    click.echo("# Bash completion script for MCLI")
    click.echo("# Add this to your ~/.bashrc or ~/.bash_profile:")
    click.echo()
    click.echo(script)


@completion.command(name="zsh")
@click.pass_context
def zsh_completion(ctx):
    """Generate zsh completion script"""
    from click.shell_completion import ZshComplete

    # Get the root CLI app
    app = ctx.find_root().command
    complete = ZshComplete(app, {}, "mcli", "_MCLI_COMPLETE")
    script = complete.source()

    click.echo("# Zsh completion script for MCLI")
    click.echo("# Add this to your ~/.zshrc:")
    click.echo()
    click.echo(script)


@completion.command(name="fish")
@click.pass_context
def fish_completion(ctx):
    """Generate fish completion script"""
    from click.shell_completion import FishComplete

    # Get the root CLI app
    app = ctx.find_root().command
    complete = FishComplete(app, {}, "mcli", "_MCLI_COMPLETE")
    script = complete.source()

    click.echo("# Fish completion script for MCLI")
    click.echo("# Add this to ~/.config/fish/completions/mcli.fish:")
    click.echo()
    click.echo(script)


@completion.command(name="install")
@click.option(
    "--shell",
    type=click.Choice(["bash", "zsh", "fish"]),
    help="Shell to install for (auto-detected if not specified)",
)
@click.pass_context
def install_completion(ctx, shell):
    """Install shell completion for the current user"""
    import subprocess

    # Auto-detect shell if not specified
    if not shell:
        shell_path = os.environ.get("SHELL", "")
        if "bash" in shell_path:
            shell = "bash"
        elif "zsh" in shell_path:
            shell = "zsh"
        elif "fish" in shell_path:
            shell = "fish"
        else:
            click.echo("❌ Could not auto-detect shell. Please specify --shell")
            return

    # Get the root CLI app
    app = ctx.find_root().command

    try:
        if shell == "bash":
            from click.shell_completion import BashComplete

            complete = BashComplete(app, {}, "mcli", "_MCLI_COMPLETE")
            script = complete.source()

            # Install to bash completion directory
            bash_completion_dir = Path.home() / ".bash_completion.d"
            bash_completion_dir.mkdir(exist_ok=True)
            completion_file = bash_completion_dir / "mcli"
            completion_file.write_text(script)

            # Add sourcing to .bashrc if needed
            bashrc = Path.home() / ".bashrc"
            source_line = f"[ -f {completion_file} ] && source {completion_file}"

            if bashrc.exists():
                content = bashrc.read_text()
                if source_line not in content:
                    with bashrc.open("a") as f:
                        f.write(f"\n# MCLI completion\n{source_line}\n")
                    click.echo("✅ Added completion sourcing to ~/.bashrc")
                else:
                    click.echo("ℹ️  Completion already configured in ~/.bashrc")
            else:
                click.echo(f"✅ Completion installed to {completion_file}")
                click.echo("💡 Add this to your ~/.bashrc:")
                click.echo(source_line)

        elif shell == "zsh":
            from click.shell_completion import ZshComplete

            complete = ZshComplete(app, {}, "mcli", "_MCLI_COMPLETE")
            script = complete.source()

            # Install to zsh completion directory
            zsh_completion_dir = Path.home() / ".config" / "zsh" / "completions"
            zsh_completion_dir.mkdir(parents=True, exist_ok=True)
            completion_file = zsh_completion_dir / "_mcli"
            completion_file.write_text(script)

            # Add to fpath in .zshrc if needed
            zshrc = Path.home() / ".zshrc"
            fpath_line = f'fpath=("{zsh_completion_dir}" $fpath)'

            if zshrc.exists():
                content = zshrc.read_text()
                if str(zsh_completion_dir) not in content:
                    with zshrc.open("a") as f:
                        f.write(
                            f"\n# MCLI completion\n{fpath_line}\nautoload -U compinit && compinit\n"
                        )
                    click.echo("✅ Added completion to ~/.zshrc")
                else:
                    click.echo("ℹ️  Completion already configured in ~/.zshrc")
            else:
                click.echo(f"✅ Completion installed to {completion_file}")
                click.echo("💡 Add this to your ~/.zshrc:")
                click.echo(f"{fpath_line}\nautoload -U compinit && compinit")

        elif shell == "fish":
            from click.shell_completion import FishComplete

            complete = FishComplete(app, {}, "mcli", "_MCLI_COMPLETE")
            script = complete.source()

            # Install to fish completion directory
            fish_completion_dir = Path.home() / ".config" / "fish" / "completions"
            fish_completion_dir.mkdir(parents=True, exist_ok=True)
            completion_file = fish_completion_dir / "mcli.fish"
            completion_file.write_text(script)
            click.echo(f"✅ Completion installed to {completion_file}")

        click.echo(f"🎉 Shell completion for {shell} installed successfully!")
        click.echo("💡 Restart your shell or source your profile to enable completions")

    except Exception as e:
        click.echo(f"❌ Failed to install completion: {e}")


@completion.command(name="status")
def completion_status():
    """Check current shell completion status"""
    current_shell = os.environ.get("SHELL", "unknown")
    shell_name = Path(current_shell).name if current_shell != "unknown" else "unknown"

    click.echo(f"🐚 Current shell: {shell_name} ({current_shell})")
    click.echo()

    # Check for existing completions
    completions_found = []

    # Check bash
    bash_completion = Path.home() / ".bash_completion.d" / "mcli"
    if bash_completion.exists():
        completions_found.append(f"✅ Bash completion: {bash_completion}")
    else:
        completions_found.append("❌ Bash completion: Not installed")

    # Check zsh
    zsh_completion = Path.home() / ".config" / "zsh" / "completions" / "_mcli"
    if zsh_completion.exists():
        completions_found.append(f"✅ Zsh completion: {zsh_completion}")
    else:
        completions_found.append("❌ Zsh completion: Not installed")

    # Check fish
    fish_completion = Path.home() / ".config" / "fish" / "completions" / "mcli.fish"
    if fish_completion.exists():
        completions_found.append(f"✅ Fish completion: {fish_completion}")
    else:
        completions_found.append("❌ Fish completion: Not installed")

    for status in completions_found:
        click.echo(status)

    click.echo()
    click.echo("💡 To install completion for your shell:")
    click.echo("   mcli completion install")
    click.echo()
    click.echo("💡 To generate completion script manually:")
    click.echo(f"   mcli completion {shell_name}")


# Export the CLI group for registration
cli = completion
