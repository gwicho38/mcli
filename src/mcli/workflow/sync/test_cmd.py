"""
Multi-cloud sync testing commands for mcli workflow system.
Provides comprehensive connectivity and validation testing.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import click

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


class McliSyncTester:
    """MCLI-integrated sync testing functionality."""

    def __init__(self, vault_path: str = "."):
        self.vault_path = Path(vault_path).resolve()
        self.test_script = self.vault_path / "test_sync_connectivity.py"

    def run_connectivity_test(self, quick: bool = False, output_file: Optional[str] = None) -> Dict:
        """Run connectivity tests using the standalone test script."""

        if not self.test_script.exists():
            raise FileNotFoundError(f"Test script not found: {self.test_script}")

        # Build command
        cmd = [sys.executable, str(self.test_script), "--vault-path", str(self.vault_path)]

        if quick:
            cmd.append("--quick")

        if output_file:
            cmd.extend(["--output", output_file])

        try:
            # Run the test script
            result = subprocess.run(
                cmd,
                cwd=self.vault_path,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            # Parse output if JSON report was generated
            report = None
            if output_file and Path(output_file).exists():
                try:
                    with open(output_file, "r") as f:
                        report = json.load(f)
                except Exception as e:
                    logger.warning(f"Could not parse test report: {e}")

            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "report": report,
                "success": result.returncode == 0,
            }

        except subprocess.TimeoutExpired:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": "Test timed out after 5 minutes",
                "report": None,
                "success": False,
            }
        except Exception as e:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "report": None,
                "success": False,
            }

    def validate_cloud_connectivity(self) -> Dict[str, bool]:
        """Quick validation of cloud service connectivity."""

        cloud_paths = {
            "onedrive": Path.home() / "Library/CloudStorage/OneDrive-Personal",
            "icloud": Path.home() / "Library/Mobile Documents/com~apple~CloudDocs",
            "googledrive": Path.home() / "Library/CloudStorage/GoogleDrive-luis@lefv.io/My Drive",
        }

        results = {}

        for service, path in cloud_paths.items():
            try:
                if path.exists() and path.is_dir():
                    # Test write access
                    test_file = path / ".mcli_connectivity_test"
                    test_file.write_text(f"Connectivity test - {datetime.now().isoformat()}")

                    if test_file.exists():
                        test_file.unlink()
                        results[service] = True
                    else:
                        results[service] = False
                else:
                    results[service] = False

            except Exception as e:
                logger.debug(f"Connectivity test failed for {service}: {e}")
                results[service] = False

        return results

    def check_sync_health(self) -> Dict[str, any]:
        """Check overall sync system health."""

        health = {
            "timestamp": datetime.now().isoformat(),
            "vault_path": str(self.vault_path),
            "system_ready": True,
            "issues": [],
        }

        # Check vault directory
        if not self.vault_path.exists():
            health["system_ready"] = False
            health["issues"].append(f"Vault directory not found: {self.vault_path}")

        # Check git repository
        git_dir = self.vault_path / ".git"
        if not git_dir.exists():
            health["issues"].append("Not a git repository")

        # Check sync configuration
        config_file = self.vault_path / ".vault_sync_config.json"
        if not config_file.exists():
            health["system_ready"] = False
            health["issues"].append("Sync configuration not found")

        # Check cloud connectivity
        cloud_status = self.validate_cloud_connectivity()
        health["cloud_connectivity"] = cloud_status

        offline_services = [service for service, online in cloud_status.items() if not online]
        if offline_services:
            health["issues"].extend([f"{service} not accessible" for service in offline_services])

        return health


@click.group(name="test")
def test():
    """Testing commands for sync functionality."""
    pass


@test.command()
@click.option("--vault-path", default=".", help="Path to vault directory")
@click.option("--quick", is_flag=True, help="Run quick tests only")
@click.option("--output", help="Save detailed report to JSON file")
def connectivity(vault_path, quick, output):
    """Run comprehensive connectivity tests for all cloud services."""

    tester = McliSyncTester(vault_path)

    click.echo("🧪 Running Multi-Cloud Sync Connectivity Tests...")
    click.echo("=" * 50)

    # Run the tests
    result = tester.run_connectivity_test(quick=quick, output_file=output)

    # Display results
    if result["stdout"]:
        click.echo(result["stdout"])

    if result["stderr"]:
        click.echo(f"\n❌ Errors:\n{result['stderr']}")

    # Show summary from report if available
    if result["report"]:
        report = result["report"]
        stats = report.get("statistics", {})
        success_rate = report.get("success_rate", 0)

        click.echo("\n" + "=" * 50)
        click.echo("📊 MCLI Test Summary")
        click.echo("=" * 50)
        click.echo(f"Success Rate: {success_rate:.1f}%")
        click.echo(f"Total Tests: {stats.get('total_tests', 0)}")
        click.echo(f"✅ Passed: {stats.get('passed', 0)}")
        click.echo(f"❌ Failed: {stats.get('failed', 0)}")

        if success_rate >= 90:
            click.echo("\n🎉 Excellent! Your sync system is working perfectly.")
        elif success_rate >= 70:
            click.echo("\n✅ Good! Minor issues may need attention.")
        else:
            click.echo("\n⚠️ Issues detected. Please review the detailed output above.")

    # Exit with appropriate code
    if not result["success"]:
        sys.exit(1)


@test.command()
@click.option("--vault-path", default=".", help="Path to vault directory")
def health(vault_path):
    """Check sync system health status."""

    tester = McliSyncTester(vault_path)

    click.echo("🏥 Checking Sync System Health...")

    health = tester.check_sync_health()

    # Display health status
    if health["system_ready"]:
        click.echo("✅ System Ready")
    else:
        click.echo("❌ System Issues Detected")

    click.echo(f"📁 Vault: {health['vault_path']}")
    click.echo(f"🕒 Checked: {health['timestamp']}")

    # Cloud connectivity status
    click.echo("\n☁️ Cloud Service Status:")
    cloud_status = health.get("cloud_connectivity", {})
    for service, online in cloud_status.items():
        status = "✅ Online" if online else "❌ Offline"
        click.echo(f"  {service.title()}: {status}")

    # Issues
    if health["issues"]:
        click.echo("\n⚠️ Issues Found:")
        for i, issue in enumerate(health["issues"], 1):
            click.echo(f"  {i}. {issue}")
    else:
        click.echo("\n🎉 No issues detected!")

    # Exit with error if system not ready
    if not health["system_ready"]:
        sys.exit(1)


@test.command()
@click.option("--vault-path", default=".", help="Path to vault directory")
@click.option(
    "--service",
    type=click.Choice(["github", "onedrive", "icloud", "googledrive", "all"]),
    default="all",
    help="Service to test",
)
def sync(vault_path, service):
    """Test sync functionality for specific service or all services."""

    # Import the sync functionality
    try:
        sys.path.insert(0, vault_path)
        from vault_sync_standalone import VaultSync
    except ImportError:
        click.echo(
            "❌ Could not import sync functionality. Ensure vault_sync_standalone.py is available."
        )
        sys.exit(1)

    syncer = VaultSync(vault_path)

    click.echo(f"🔄 Testing Sync Functionality - {service.title()}...")

    services_to_test = (
        [service] if service != "all" else ["github", "onedrive", "icloud", "googledrive"]
    )

    results = {}

    for svc in services_to_test:
        click.echo(f"\n🔄 Testing {svc.title()}...")

        try:
            if svc == "github":
                success = syncer.git_sync()
            else:
                success = syncer.cloud_sync(svc)

            if success:
                click.echo(f"✅ {svc.title()}: Sync successful")
                results[svc] = True
            else:
                click.echo(f"❌ {svc.title()}: Sync failed")
                results[svc] = False

        except Exception as e:
            click.echo(f"💥 {svc.title()}: Error - {e}")
            results[svc] = False

    # Summary
    successful = sum(results.values())
    total = len(results)

    click.echo(f"\n📊 Sync Test Results: {successful}/{total} successful")

    if successful == total:
        click.echo("🎉 All sync tests passed!")
    else:
        click.echo("⚠️ Some sync tests failed. Check configuration and connectivity.")
        sys.exit(1)


if __name__ == "__main__":
    test()
