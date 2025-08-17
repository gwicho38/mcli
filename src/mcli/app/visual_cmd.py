"""
🎨 Visual Effects and Enhancement Commands for MCLI
Showcase stunning visual elements and interactive features
"""

import time

import click

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


@click.group()
def visual():
    """🎨 Visual effects and enhancements showcase"""
    pass


@visual.command()
@click.option(
    "--demo-type",
    type=click.Choice(["all", "banners", "tables", "animations", "progress"]),
    default="all",
    help="Type of visual demo to run",
)
def demo(demo_type: str):
    """🎭 Demonstrate MCLI's visual capabilities"""
    try:
        from rich.rule import Rule
        from rich.text import Text

        from mcli.lib.ui.styling import celebrate
        from mcli.lib.ui.visual_effects import (
            AnimatedSpinner,
            ColorfulOutput,
            MCLIBanner,
            MCLIProgressBar,
            StartupSequence,
            VisualTable,
            console,
            demo_visual_effects,
        )

        console.clear()

        if demo_type in ["all", "banners"]:
            console.print(Rule("🎨 Banner Showcase", style="bright_magenta"))
            console.print()

            MCLIBanner.show_main_banner("Visual Demo Mode")
            time.sleep(1)

            MCLIBanner.show_performance_banner()
            time.sleep(1)

            MCLIBanner.show_rust_banner()
            time.sleep(1)

        if demo_type in ["all", "animations"]:
            console.print(Rule("⚡ Animation Showcase", style="bright_yellow"))
            console.print()

            # Spinner demos
            spinner_types = ["rocket", "gears", "rust", "lightning", "dots"]
            for spinner_type in spinner_types:
                spinner = AnimatedSpinner(spinner_type, 0.15)
                spinner.start(f"Testing {spinner_type} spinner...")
                time.sleep(2)
                spinner.stop()
                ColorfulOutput.success(f"{spinner_type.title()} spinner complete!")
                time.sleep(0.5)

        if demo_type in ["all", "progress"]:
            console.print(Rule("📊 Progress Bar Showcase", style="bright_cyan"))
            console.print()

            # Fancy progress demo
            progress = MCLIProgressBar.create_fancy_progress()

            with progress:
                tasks = [
                    ("🚀 Initializing systems", 20),
                    ("🔧 Loading components", 15),
                    ("⚡ Optimizing performance", 25),
                    ("🎨 Applying visual effects", 18),
                    ("✨ Finalizing setup", 12),
                ]

                for task_name, duration in tasks:
                    task = progress.add_task(task_name, total=duration)

                    for i in range(duration):
                        progress.update(task, advance=1)
                        time.sleep(0.1)

                    progress.remove_task(task)

        if demo_type in ["all", "tables"]:
            console.print(Rule("📋 Table Showcase", style="bright_green"))
            console.print()

            # Sample data for tables
            sample_perf_data = {
                "uvloop": {"success": True, "reason": "Loaded successfully"},
                "rust": {
                    "success": True,
                    "extensions": {
                        "tfidf": True,
                        "file_watcher": True,
                        "command_matcher": True,
                        "process_manager": True,
                    },
                },
                "redis": {"success": False, "reason": "Redis server not available"},
                "python": {"success": True, "optimizations": {"gc_tuned": True}},
            }

            perf_table = VisualTable.create_performance_table(sample_perf_data)
            console.print(perf_table)
            console.print()

            rust_extensions = {
                "tfidf": True,
                "file_watcher": True,
                "command_matcher": False,
                "process_manager": True,
            }
            rust_table = VisualTable.create_rust_extensions_table(rust_extensions)
            console.print(rust_table)

        # Final celebration
        console.print()
        celebrate("Visual Demo Complete - MCLI looks amazing!")

        ColorfulOutput.info("Ready to experience the enhanced MCLI interface!")

    except ImportError as e:
        click.echo(f"❌ Visual effects not available: {e}")
        click.echo("💡 Try installing rich: pip install rich")


@visual.command()
def startup():
    """🚀 Show the full startup animation sequence"""
    try:
        from mcli.lib.ui.visual_effects import StartupSequence

        StartupSequence.run_startup_animation()

    except ImportError as e:
        click.echo(f"❌ Visual effects not available: {e}")


@visual.command()
@click.option(
    "--spinner-type",
    type=click.Choice(["rocket", "gears", "rust", "lightning", "dots", "arrows"]),
    default="rocket",
    help="Type of spinner to show",
)
@click.option("--duration", default=5, help="Duration in seconds")
@click.option("--message", default="Processing...", help="Loading message")
def spinner(spinner_type: str, duration: int, message: str):
    """⚡ Show an animated spinner"""
    try:
        from mcli.lib.ui.visual_effects import AnimatedSpinner

        spinner = AnimatedSpinner(spinner_type, 0.1)
        spinner.start(message)
        time.sleep(duration)
        spinner.stop()

        click.echo("✅ Spinner demo complete!")

    except ImportError as e:
        click.echo(f"❌ Visual effects not available: {e}")


@visual.command()
def performance():
    """📊 Show enhanced performance summary"""
    try:
        from mcli.lib.performance.rust_bridge import print_performance_summary

        print_performance_summary()

    except ImportError as e:
        click.echo(f"❌ Performance summary not available: {e}")


@visual.command()
@click.option(
    "--style",
    type=click.Choice(["success", "error", "warning", "info", "celebrate"]),
    default="info",
    help="Message style to demo",
)
@click.argument("message", default="This is a test message!")
def message(style: str, message: str):
    """💬 Show styled message examples"""
    try:
        from mcli.lib.ui.styling import celebrate
        from mcli.lib.ui.visual_effects import ColorfulOutput

        if style == "success":
            ColorfulOutput.success(message)
        elif style == "error":
            ColorfulOutput.error(message)
        elif style == "warning":
            ColorfulOutput.warning(message)
        elif style == "info":
            ColorfulOutput.info(message)
        elif style == "celebrate":
            celebrate(message)

    except ImportError as e:
        click.echo(f"❌ Visual effects not available: {e}")


@visual.command()
def banner():
    """🎯 Show all available banners"""
    try:
        from mcli.lib.ui.visual_effects import MCLIBanner

        MCLIBanner.show_main_banner("Banner Showcase")
        time.sleep(1)

        MCLIBanner.show_performance_banner()
        time.sleep(1)

        MCLIBanner.show_rust_banner()

    except ImportError as e:
        click.echo(f"❌ Visual effects not available: {e}")


@visual.command()
def interactive():
    """🎮 Interactive visual experience"""
    try:
        import random

        from rich.panel import Panel
        from rich.prompt import Confirm, Prompt
        from rich.text import Text

        from mcli.lib.ui.visual_effects import AnimatedSpinner, ColorfulOutput, MCLIBanner, console

        console.clear()

        # Welcome
        MCLIBanner.show_main_banner("Interactive Mode")

        # User interaction
        name = Prompt.ask("🎨 What's your name?", default="Developer")

        # Personalized greeting
        greeting = f"Welcome to MCLI, {name}! 🚀"
        ColorfulOutput.success(greeting)

        # Interactive spinner choice
        spinner_types = ["rocket", "gears", "rust", "lightning", "dots"]
        chosen_spinner = Prompt.ask(
            "Choose your favorite spinner", choices=spinner_types, default="rocket"
        )

        # Show chosen spinner
        spinner = AnimatedSpinner(chosen_spinner, 0.12)
        spinner.start(f"Loading {name}'s personalized experience...")
        time.sleep(3)
        spinner.stop()

        # Random fun fact
        fun_facts = [
            "MCLI is powered by Rust for maximum performance! 🦀",
            "The visual effects use Rich library for stunning output! 🎨",
            "You can customize all visual elements! ⚙️",
            "MCLI supports multiple themes and styles! 🌈",
            "Performance optimizations give 10-100x speedup! ⚡",
        ]

        fact = random.choice(fun_facts)
        panel = Panel(f"💡 Fun Fact: {fact}", title="Did You Know?", border_style="bright_blue")
        console.print(panel)

        # Final interaction
        if Confirm.ask("🎭 Would you like to see the full demo?"):
            from mcli.lib.ui.visual_effects import demo_visual_effects

            demo_visual_effects()

        ColorfulOutput.success(f"Thanks for exploring MCLI visuals, {name}! 🎉")

    except ImportError as e:
        click.echo(f"❌ Interactive mode not available: {e}")


# Add visual command group to main CLI
if __name__ == "__main__":
    visual()
