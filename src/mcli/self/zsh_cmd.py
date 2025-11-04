"""
ZSH-specific commands and utilities for MCLI.
"""

import os
import subprocess
from pathlib import Path

import click

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)
from mcli.lib.ui.styling import error, info, success, warning


@click.group(name="zsh", help="ZSH shell integration and utilities")
def zsh_group():
    """ZSH-specific commands and utilities."""


@zsh_group.command(name="config", help="Configure ZSH for optimal MCLI experience")
@click.option("--force", is_flag=True, help="Force reconfiguration even if already set up")
def zsh_config(force: bool):
    """Configure ZSH with MCLI-specific settings."""
    zshrc = Path.home() / ".zshrc"

    if not zshrc.exists():
        if click.confirm("No .zshrc found. Create one?"):
            zshrc.touch()
        else:
            warning("Configuration cancelled")
            return

    configs_added = []  # noqa: F841

    # Read existing content
    content = zshrc.read_text()

    # MCLI configuration block
    mcli_block_start = "# BEGIN MCLI ZSH CONFIG"
    mcli_block_end = "# END MCLI ZSH CONFIG"

    if mcli_block_start in content and not force:
        info("MCLI ZSH configuration already exists. Use --force to reconfigure.")
        return

    # Remove old block if forcing
    if mcli_block_start in content and force:
        lines = content.split("\n")
        new_lines = []
        in_block = False

        for line in lines:
            if line.strip() == mcli_block_start:
                in_block = True
            elif line.strip() == mcli_block_end:
                in_block = False
                continue
            elif not in_block:
                new_lines.append(line)

        content = "\n".join(new_lines)

    # Build configuration
    config_lines = [
        "",
        mcli_block_start,
        "# MCLI aliases",
        "alias m='mcli'",
        "alias mc='mcli chat'",
        "alias mw='mcli workflow'",
        "alias ms='mcli self'",
        "alias mls='mcli lib secrets'",
        "alias mlsr='mcli lib secrets repl'",
        "",
        "# MCLI environment",
        'export MCLI_HOME="$HOME/.mcli"',
        'export PATH="$MCLI_HOME/bin:$PATH"',
        "",
        "# MCLI completion",
        'fpath=("$HOME/.config/zsh/completions" $fpath)',
        "autoload -U compinit && compinit",
        "",
        "# MCLI prompt integration (optional)",
        '# PS1="%{$fg[cyan]%}[mcli]%{$reset_color%} $PS1"',
        "",
        mcli_block_end,
        "",
    ]

    # Append configuration
    with zshrc.open("a") as f:
        f.write("\n".join(config_lines))

    success("ZSH configuration added successfully!")

    # Install completion if not already installed
    completion_dir = Path.home() / ".config" / "zsh" / "completions"
    completion_file = completion_dir / "_mcli"

    if not completion_file.exists():
        info("Installing ZSH completion...")
        try:
            subprocess.run(["mcli", "self", "completion", "install", "--shell=zsh"], check=True)
            configs_added.append("completion")
        except subprocess.CalledProcessError:
            warning("Failed to install completion automatically")

    info("\nConfigured:")
    info("  • Aliases: m, mc, mw, ms, mls, mlsr")
    info("  • Environment variables: MCLI_HOME, PATH")
    info("  • Shell completion support")
    info("\nReload your shell configuration:")
    info("  source ~/.zshrc")


@zsh_group.command(name="aliases", help="Show available ZSH aliases")
def zsh_aliases():
    """Display MCLI ZSH aliases."""
    aliases = [
        ("m", "mcli", "Main MCLI command"),
        ("mc", "mcli chat", "Open chat interface"),
        ("mw", "mcli workflow", "Workflow commands"),
        ("ms", "mcli self", "Self management commands"),
        ("mls", "mcli lib secrets", "Secrets management"),
        ("mlsr", "mcli lib secrets repl", "Secrets REPL"),
    ]

    info("MCLI ZSH Aliases:")
    for alias, command, desc in aliases:
        click.echo(f"  {alias:<6} → {command:<25} # {desc}")


@zsh_group.command(name="prompt", help="Configure ZSH prompt with MCLI integration")
@click.option("--style", type=click.Choice(["simple", "powerline", "minimal"]), default="simple")
def zsh_prompt(style: str):
    """Add MCLI status to ZSH prompt."""
    zshrc = Path.home() / ".zshrc"

    if not zshrc.exists():
        error("No .zshrc found")
        return

    prompt_configs = {
        "simple": 'PS1="%{$fg[cyan]%}[mcli]%{$reset_color%} $PS1"',
        "powerline": 'PS1="%{$fg[cyan]%} mcli %{$reset_color%}$PS1"',
        "minimal": 'PS1="◆ $PS1"',
    }

    config = prompt_configs[style]

    # Check if prompt section exists
    content = zshrc.read_text()
    prompt_marker = "# MCLI prompt integration"

    if prompt_marker in content:
        # Update existing prompt
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.strip() == prompt_marker:  # noqa: SIM102
                if i + 1 < len(lines) and lines[i + 1].startswith("PS1="):
                    lines[i + 1] = config
                    content = "\n".join(lines)
                    zshrc.write_text(content)
                    success(f"Updated prompt to {style} style")
                    break
    else:
        warning("MCLI ZSH configuration not found. Run 'mcli self zsh config' first.")


@zsh_group.command(name="functions", help="Install useful ZSH functions")
def zsh_functions():
    """Install MCLI-specific ZSH functions."""
    functions_dir = Path.home() / ".config" / "zsh" / "functions"
    functions_dir.mkdir(parents=True, exist_ok=True)

    # Create mcli-quick function
    quick_func = functions_dir / "mcli-quick"
    quick_func.write_text(
        """# Quick MCLI command runner
mcli-quick() {
    local cmd=$1
    shift
    mcli $cmd "$@" | head -20
}"""
    )

    # Create mcli-fzf function for fuzzy finding
    fzf_func = functions_dir / "mcli-fzf"
    fzf_func.write_text(
        """# Fuzzy find MCLI commands
mcli-fzf() {
    local cmd=$(mcli --help | grep -E '^  [a-z]' | awk '{print $1}' | fzf)
    if [[ -n $cmd ]]; then
        print -z "mcli $cmd "
    fi
}"""
    )

    # Add to zshrc
    zshrc = Path.home() / ".zshrc"
    if zshrc.exists():
        content = zshrc.read_text()
        fpath_line = f'fpath=("{functions_dir}" $fpath)'

        if str(functions_dir) not in content:
            with zshrc.open("a") as f:
                f.write(f"\n# MCLI ZSH functions\n{fpath_line}\nautoload -U mcli-quick mcli-fzf\n")

    success("ZSH functions installed:")
    info("  • mcli-quick: Run MCLI commands with truncated output")
    info("  • mcli-fzf: Fuzzy find MCLI commands (requires fzf)")


@zsh_group.command(name="test", help="Test ZSH integration")
def zsh_test():
    """Test ZSH integration and configuration."""
    checks = []

    # Check if running in ZSH
    shell = os.environ.get("SHELL", "")
    if "zsh" in shell:
        checks.append(("ZSH shell detected", True))
    else:
        checks.append(("ZSH shell detected", False))

    # Check completion
    completion_file = Path.home() / ".config" / "zsh" / "completions" / "_mcli"
    checks.append(("Completion installed", completion_file.exists()))

    # Check zshrc
    zshrc = Path.home() / ".zshrc"
    if zshrc.exists():
        content = zshrc.read_text()
        checks.append(("MCLI config in .zshrc", "BEGIN MCLI ZSH CONFIG" in content))
        checks.append(("Completion in fpath", ".config/zsh/completions" in content))
    else:
        checks.append((".zshrc exists", False))

    # Check aliases
    try:
        result = subprocess.run(["zsh", "-c", "alias | grep mcli"], capture_output=True, text=True)
        checks.append(("Aliases configured", result.returncode == 0))
    except Exception:
        checks.append(("Aliases configured", False))

    # Display results
    info("ZSH Integration Test Results:")
    for check, passed in checks:
        status = "✅" if passed else "❌"
        click.echo(f"  {status} {check}")

    if all(passed for _, passed in checks):
        success("\nAll checks passed! ZSH integration is working correctly.")
    else:
        warning("\nSome checks failed. Run 'mcli self zsh config' to set up integration.")
