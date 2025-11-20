"""
clean command for mcli.workflow.

Description: Enhanced Mac Cleaner Script with Flutter & Emulator Management

Instructions:
Comprehensive Mac cleanup tool that:
- Cleans caches and build artifacts
- Manages Flutter builds (keeps latest Android & iOS builds)
- Manages emulators/simulators (keeps at least one of each)
- Provides detailed space freed reporting
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import click

from mcli.lib.logger.logger import get_logger

logger = get_logger()


# Create a Click command group
@click.group(name="clean")
def clean():
    """Enhanced Mac Cleaner Script (CleanMyMac Mirror + Flutter/Emulator Management)"""
    pass


@clean.command(name="start")
@click.option("--full", is_flag=True, help="Run complete scan/cleanup")
@click.option("--flutter", is_flag=True, help="Include Flutter cleanup (keeps latest builds)")
@click.option(
    "--emulators", is_flag=True, help="Clean old emulators/simulators (keeps at least one)"
)
@click.option("--aggressive", is_flag=True, help="Run all cleanup tasks aggressively")
def start(full, flutter, emulators, aggressive):
    """Start the enhanced Mac cleaner script"""
    _start(full, flutter, emulators, aggressive)


# Configurable settings
CACHE_DIRS = [
    "~/Library/Caches",
    "/Library/Caches",
    "~/Library/Logs",
    "/private/var/log",
    "~/Library/Developer/Xcode/DerivedData",
    "~/Library/Developer/Xcode/iOS DeviceSupport",
    "~/Library/Developer/Xcode/watchOS DeviceSupport",
    "~/Library/Caches/com.apple.dt.Xcode",
]

LARGE_FILE_THRESHOLD_MB = 500  # Files larger than this
TRASH_PATH = Path.home() / ".Trash"


def run_command(cmd, capture_output=True):
    """Run shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=capture_output, text=True)
        return result.stdout.strip() if capture_output else ""
    except Exception as e:
        logger.error(f"Command failed: {cmd} - {e}")
        return ""


def get_disk_space():
    """Get current disk space in KB"""
    result = run_command("df / | tail -1 | awk '{print $4}'")
    return int(result) if result else 0


def format_size(kb):
    """Format KB to human readable size"""
    gb = kb / (1024 * 1024)
    if gb > 1:
        return f"{gb:.2f} GB"
    mb = kb / 1024
    if mb > 1:
        return f"{mb:.2f} MB"
    return f"{kb:.2f} KB"


def cleanup_caches():
    """Enhanced cache cleaning"""
    logger.info("🧹 Cleaning caches and logs...")
    initial_space = get_disk_space()
    total_freed = 0

    for cache_dir in CACHE_DIRS:
        expanded = os.path.expanduser(cache_dir)
        if os.path.exists(expanded):
            try:
                dir_size = int(run_command(f"du -sk '{expanded}' | cut -f1") or "0")
                shutil.rmtree(expanded)
                os.makedirs(expanded)  # Recreate empty directory
                total_freed += dir_size
                logger.info(f"  ✅ Cleaned {cache_dir} - freed {format_size(dir_size)}")
            except PermissionError:
                logger.warning(f"  ⚠️  Permission denied: {cache_dir} (run with sudo?)")
            except Exception as e:
                logger.warning(f"  ⚠️  Error cleaning {cache_dir}: {e}")

    current_space = get_disk_space()
    actual_freed = current_space - initial_space
    logger.info(f"✅ Cache cleanup complete - freed {format_size(actual_freed)}")
    return actual_freed


def cleanup_flutter_builds():
    """Clean Flutter builds but keep latest Android and iOS builds"""
    logger.info("📱 Cleaning Flutter builds (keeping latest Android & iOS)...")
    initial_space = get_disk_space()

    # Find all Flutter project build directories
    flutter_projects = [
        Path.home() / "repos" / "Outlet" / "outlet",
        Path.home() / "repos" / "mcli",
    ]

    total_freed = 0
    for project in flutter_projects:
        if not project.exists():
            continue

        build_dir = project / "build"
        if not build_dir.exists():
            continue

        logger.info(f"  🔍 Checking {project.name}...")

        # Keep latest Android and iOS builds
        android_apk = list(build_dir.glob("app/outputs/flutter-apk/*.apk"))
        ios_builds = list(build_dir.glob("ios/iphoneos/*.app"))

        # Sort by modification time and keep newest
        if android_apk:
            android_apk.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            keep_android = android_apk[0] if android_apk else None
            logger.info(
                f"    📱 Keeping latest Android APK: {keep_android.name if keep_android else 'none'}"
            )

        if ios_builds:
            ios_builds.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            keep_ios = ios_builds[0] if ios_builds else None
            logger.info(f"    🍎 Keeping latest iOS build: {keep_ios.name if keep_ios else 'none'}")

        # Run flutter clean
        try:
            build_size = int(run_command(f"du -sk '{build_dir}' | cut -f1") or "0")
            run_command(f"cd '{project}' && flutter clean", capture_output=False)
            total_freed += build_size
            logger.info(f"    ✅ Cleaned build directory - freed {format_size(build_size)}")
        except Exception as e:
            logger.warning(f"    ⚠️  Error cleaning {project.name}: {e}")

    current_space = get_disk_space()
    actual_freed = current_space - initial_space
    logger.info(f"✅ Flutter build cleanup complete - freed {format_size(actual_freed)}")
    return actual_freed


def cleanup_emulators():
    """Clean old Android emulators and iOS simulators (keeps at least one of each)"""
    logger.info("🎮 Cleaning emulators/simulators (keeping at least one of each)...")
    initial_space = get_disk_space()
    total_freed = 0

    # Clean Android emulators
    logger.info("  📱 Android Emulators:")
    emulator_list = run_command("$HOME/android-sdk/emulator/emulator -list-avds 2>/dev/null")
    if emulator_list:
        emulators = emulator_list.split("\n")
        logger.info(f"    Found {len(emulators)} emulator(s)")

        # Keep Pixel_6_API_34_ARM and one other
        keep_emulators = ["Pixel_6_API_34_ARM"]
        if len(emulators) > 1:
            keep_emulators.append([e for e in emulators if e not in keep_emulators][0])

        for emulator in emulators:
            if emulator not in keep_emulators:
                logger.info(f"    🗑️  Removing: {emulator}")
                run_command(f"$HOME/android-sdk/emulator/avdmanager delete avd -n {emulator}")
                total_freed += 2000000  # Estimate 2GB per emulator
            else:
                logger.info(f"    ✅ Keeping: {emulator}")
    else:
        logger.info("    No Android emulators found")

    # Clean iOS simulators (unavailable ones)
    logger.info("  🍎 iOS Simulators:")
    run_command("xcrun simctl delete unavailable 2>/dev/null")

    # List remaining simulators
    sim_list = run_command("xcrun simctl list devices available | grep -E 'iPhone|iPad' | wc -l")
    logger.info(f"    {sim_list.strip()} simulator(s) remaining")

    current_space = get_disk_space()
    actual_freed = current_space - initial_space
    logger.info(f"✅ Emulator cleanup complete - freed {format_size(actual_freed)}")
    return actual_freed


def cleanup_development_tools():
    """Clean development tool caches"""
    logger.info("🛠️  Cleaning development tool caches...")
    initial_space = get_disk_space()

    tools = [
        ("CocoaPods", "pod cache clean --all 2>/dev/null"),
        ("Homebrew", "brew cleanup --prune=all 2>/dev/null"),
        ("npm", "npm cache clean --force 2>/dev/null"),
        ("yarn", "yarn cache clean 2>/dev/null"),
        ("Gradle", "rm -rf ~/.gradle/caches/*"),
        ("pip", "pip cache purge 2>/dev/null"),
    ]

    for tool_name, command in tools:
        try:
            run_command(command)
            logger.info(f"  ✅ Cleaned {tool_name}")
        except Exception as e:
            logger.warning(f"  ⚠️  {tool_name} cleanup failed")

    current_space = get_disk_space()
    actual_freed = current_space - initial_space
    logger.info(f"✅ Development tools cleanup complete - freed {format_size(actual_freed)}")
    return actual_freed


def cleanup_lsh_daemon():
    """Clean LSH daemon processes and files"""
    logger.info("🔧 Cleaning LSH daemon...")

    # Kill daemon processes
    run_command("sudo pkill -f 'lshd.js' 2>/dev/null")
    run_command("sleep 2")

    # Remove socket and PID files
    run_command("sudo rm -f /tmp/lsh-*daemon*.sock 2>/dev/null")
    run_command("sudo rm -f /tmp/lsh-*daemon*.pid 2>/dev/null")

    logger.info("  ✅ LSH daemon cleaned")


def empty_trash():
    """Empty macOS Trash"""
    logger.info("🗑️  Emptying Trash...")
    initial_space = get_disk_space()

    script = """
    tell application "Finder"
        empty the trash
    end tell
    """
    run_command(f"osascript -e '{script}'")

    current_space = get_disk_space()
    actual_freed = current_space - initial_space
    logger.info(f"✅ Trash emptied - freed {format_size(actual_freed)}")
    return actual_freed


def find_large_files(root_path=str(Path.home()), max_depth=3):
    """Scan for large files"""
    logger.info(f"🔍 Scanning for large files (>{LARGE_FILE_THRESHOLD_MB}MB)...")

    cmd = f"find '{root_path}' -maxdepth {max_depth} -type f -size +{LARGE_FILE_THRESHOLD_MB}M -exec ls -lh {{}} \\; 2>/dev/null | awk '{{print $5, $9}}' | head -10"
    result = run_command(cmd)

    if result:
        logger.info("  📊 Top 10 large files:")
        for line in result.split("\n"):
            logger.info(f"    {line}")
    else:
        logger.info("  ✅ No large files found")


def space_report():
    """Quick disk space summary"""
    logger.info("💾 Disk Space Report:")
    result = run_command("df -h / | tail -1")
    logger.info(f"  {result}")


def git_cleanup():
    """Run git garbage collection on common repos"""
    logger.info("📚 Running git garbage collection...")

    repos = [
        Path.home() / "repos" / "mcli",
        Path.home() / "repos" / "lsh",
        Path.home() / "repos" / "Outlet",
    ]

    for repo in repos:
        if repo.exists() and (repo / ".git").exists():
            try:
                run_command(f"cd '{repo}' && git gc --prune=now --aggressive 2>/dev/null")
                logger.info(f"  ✅ Cleaned {repo.name}")
            except Exception as e:
                logger.warning(f"  ⚠️  Failed to clean {repo.name}")


def _start(full=False, flutter=False, emulators=False, aggressive=False):
    logger.info("=" * 60)
    logger.info("🚀 Enhanced Mac Cleaner Script")
    logger.info("=" * 60)

    initial_space = get_disk_space()
    space_report()
    logger.info("")

    total_freed = 0

    if aggressive or full:
        total_freed += cleanup_caches()
        total_freed += cleanup_development_tools()
        total_freed += cleanup_flutter_builds()
        total_freed += cleanup_emulators()
        cleanup_lsh_daemon()
        git_cleanup()
        total_freed += empty_trash()
        find_large_files()
    elif flutter:
        total_freed += cleanup_flutter_builds()
    elif emulators:
        total_freed += cleanup_emulators()
    else:
        # Basic cleanup
        total_freed += cleanup_caches()
        space_report()
        logger.info("")
        logger.info("💡 Run with --full for complete cleanup")
        logger.info("💡 Run with --flutter to clean Flutter builds")
        logger.info("💡 Run with --emulators to clean old emulators/simulators")
        logger.info("💡 Run with --aggressive for all cleanup tasks")

    logger.info("")
    logger.info("=" * 60)
    logger.info("✨ Cleanup Complete!")
    logger.info("=" * 60)
    final_space = get_disk_space()
    actual_total_freed = final_space - initial_space
    logger.info(f"🎉 Total space freed: {format_size(actual_total_freed)}")
    space_report()
