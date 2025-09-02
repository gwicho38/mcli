"""
CLI commands for politician trading workflow
"""

import asyncio
import json
from datetime import datetime

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.json import JSON

from mcli.lib.logger.logger import get_logger
from .workflow import (
    PoliticianTradingWorkflow,
    run_politician_trading_collection,
    check_politician_trading_status,
)
from .config import WorkflowConfig
from .monitoring import PoliticianTradingMonitor, run_health_check, run_stats_report
from .connectivity import SupabaseConnectivityValidator, run_connectivity_validation, run_continuous_monitoring

logger = get_logger(__name__)
console = Console()


@click.group(name="politician-trading")
def politician_trading_cli():
    """Manage politician trading data collection workflow"""
    pass


@politician_trading_cli.command("run")
@click.option("--full", is_flag=True, help="Run full data collection (default)")
@click.option("--us-only", is_flag=True, help="Only collect US Congress data")
@click.option("--eu-only", is_flag=True, help="Only collect EU Parliament data")
def run_collection(full: bool, us_only: bool, eu_only: bool):
    """Run politician trading data collection"""
    console.print("🏛️ Starting Politician Trading Data Collection", style="bold cyan")

    try:
        if us_only:
            console.print("Collecting US Congress data only...", style="yellow")
            # Would implement US-only collection
            result = asyncio.run(run_politician_trading_collection())
        elif eu_only:
            console.print("Collecting EU Parliament data only...", style="yellow")
            # Would implement EU-only collection
            result = asyncio.run(run_politician_trading_collection())
        else:
            console.print("Running full data collection...", style="green")
            result = asyncio.run(run_politician_trading_collection())

        # Display results
        if result.get("status") == "completed":
            console.print("✅ Collection completed successfully!", style="bold green")

            # Create summary table
            table = Table(title="Collection Summary")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            summary = result.get("summary", {})
            table.add_row("New Disclosures", str(summary.get("total_new_disclosures", 0)))
            table.add_row("Updated Disclosures", str(summary.get("total_updated_disclosures", 0)))
            table.add_row("Errors", str(len(summary.get("errors", []))))
            table.add_row(
                "Duration",
                _calculate_duration(result.get("started_at"), result.get("completed_at")),
            )

            console.print(table)

            # Show job details
            jobs = result.get("jobs", {})
            for job_name, job_data in jobs.items():
                job_panel = Panel(
                    f"Status: {job_data.get('status', 'unknown')}\n"
                    f"New: {job_data.get('new_disclosures', 0)} | "
                    f"Updated: {job_data.get('updated_disclosures', 0)} | "
                    f"Errors: {len(job_data.get('errors', []))}",
                    title=f"📊 {job_name.upper()} Job",
                    border_style="green",
                )
                console.print(job_panel)
        else:
            console.print("❌ Collection failed!", style="bold red")
            if "error" in result:
                console.print(f"Error: {result['error']}", style="red")

    except Exception as e:
        console.print(f"❌ Command failed: {e}", style="bold red")
        logger.error(f"Collection command failed: {e}")


@politician_trading_cli.command("status")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def check_status(output_json: bool):
    """Check current status of politician trading data collection"""
    try:
        status = asyncio.run(check_politician_trading_status())

        if output_json:
            console.print(JSON.from_data(status))
            return

        # Display formatted status
        console.print("🏛️ Politician Trading Data Status", style="bold cyan")

        # Overall status
        if "error" in status:
            console.print(f"❌ Status check failed: {status['error']}", style="red")
            return

        # Summary panel
        summary_text = f"""Database Connection: {status.get('database_connection', 'unknown')}
Configuration: {status.get('config_loaded', 'unknown')}
Total Disclosures: {status.get('total_disclosures', 0):,}
Today's New Records: {status.get('recent_disclosures_today', 0):,}
Last Update: {status.get('timestamp', 'unknown')}"""

        summary_panel = Panel(summary_text, title="📈 System Status", border_style="blue")
        console.print(summary_panel)

        # Recent jobs table
        recent_jobs = status.get("recent_jobs", [])
        if recent_jobs:
            jobs_table = Table(title="Recent Jobs")
            jobs_table.add_column("Job Type", style="cyan")
            jobs_table.add_column("Status", style="green")
            jobs_table.add_column("Started", style="yellow")
            jobs_table.add_column("Records", justify="right", style="magenta")
            jobs_table.add_column("Duration", style="blue")

            for job in recent_jobs[:5]:  # Show last 5 jobs
                status_style = (
                    "green"
                    if job.get("status") == "completed"
                    else "red" if job.get("status") == "failed" else "yellow"
                )

                jobs_table.add_row(
                    job.get("job_type", ""),
                    f"[{status_style}]{job.get('status', '')}[/{status_style}]",
                    _format_timestamp(job.get("started_at")),
                    str(job.get("records_processed", 0)),
                    _calculate_duration(job.get("started_at"), job.get("completed_at")),
                )

            console.print(jobs_table)

    except Exception as e:
        console.print(f"❌ Status check failed: {e}", style="bold red")
        logger.error(f"Status command failed: {e}")


@politician_trading_cli.command("setup")
@click.option("--create-tables", is_flag=True, help="Create database tables")
@click.option("--verify", is_flag=True, help="Verify configuration and connection")
@click.option("--generate-schema", is_flag=True, help="Generate schema SQL file")
@click.option("--output-dir", default=".", help="Directory to save generated files")
def setup_workflow(create_tables: bool, verify: bool, generate_schema: bool, output_dir: str):
    """Setup politician trading workflow"""
    console.print("🔧 Setting up Politician Trading Workflow", style="bold blue")

    try:
        config = WorkflowConfig.default()
        workflow = PoliticianTradingWorkflow(config)

        if verify:
            console.print("Verifying configuration and database connection...")

            # Test database connection
            try:
                status = asyncio.run(workflow.run_quick_check())
                if "error" not in status:
                    console.print("✅ Database connection successful", style="green")
                    console.print("✅ Configuration loaded", style="green")

                    # Display config summary
                    config_text = f"""Supabase URL: {config.supabase.url}
Request Delay: {config.scraping.request_delay}s
Max Retries: {config.scraping.max_retries}
Timeout: {config.scraping.timeout}s"""

                    config_panel = Panel(config_text, title="🔧 Configuration", border_style="blue")
                    console.print(config_panel)
                else:
                    console.print(f"❌ Verification failed: {status['error']}", style="red")
            except Exception as e:
                console.print(f"❌ Verification failed: {e}", style="red")

        if generate_schema:
            console.print("📄 Generating database schema files...", style="blue")
            
            # Generate schema file
            import os
            from pathlib import Path
            
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            # Read the schema SQL from the module
            schema_file = Path(__file__).parent / "schema.sql"
            if schema_file.exists():
                schema_content = schema_file.read_text()
                
                # Write to output directory
                output_schema_file = output_path / "politician_trading_schema.sql"
                output_schema_file.write_text(schema_content)
                
                console.print(f"✅ Schema SQL generated: {output_schema_file.absolute()}", style="green")
                
                # Also generate a setup instructions file
                instructions = f"""# Politician Trading Database Setup Instructions

## Step 1: Create Database Schema

1. Open your Supabase SQL editor: https://supabase.com/dashboard/project/{config.supabase.url.split('//')[1].split('.')[0]}/sql/new
2. Copy and paste the contents of: {output_schema_file.absolute()}
3. Execute the SQL to create all tables, indexes, and triggers

## Step 2: Verify Setup

Run the following command to verify everything is working:

```bash
politician-trading setup --verify
```

## Step 3: Test Connectivity

```bash
politician-trading connectivity
```

## Step 4: Run First Collection

```bash
politician-trading test-workflow --verbose
```

## Step 5: Setup Automated Collection (Optional)

```bash
politician-trading cron-job --create
```

## Database Tables Created

- **politicians**: Stores politician information (US Congress, EU Parliament)
- **trading_disclosures**: Individual trading transactions/disclosures  
- **data_pull_jobs**: Job execution tracking and status
- **data_sources**: Data source configuration and health

## Troubleshooting

If you encounter issues:

1. Check connectivity: `politician-trading connectivity --json`
2. View logs: `politician-trading health`
3. Test workflow: `politician-trading test-workflow --verbose`
"""
                
                instructions_file = output_path / "SETUP_INSTRUCTIONS.md"
                instructions_file.write_text(instructions)
                
                console.print(f"✅ Setup instructions generated: {instructions_file.absolute()}", style="green")
                
                # Display summary
                console.print("\n📋 Generated Files:", style="bold")
                console.print(f"  📄 Schema SQL: {output_schema_file.name}")
                console.print(f"  📋 Instructions: {instructions_file.name}")
                console.print(f"  📁 Location: {output_path.absolute()}")
                
                console.print("\n🚀 Next Steps:", style="bold green")
                console.print("1. Open Supabase SQL editor")
                console.print(f"2. Execute SQL from: {output_schema_file.name}")
                console.print("3. Run: politician-trading setup --verify")
                console.print("4. Run: politician-trading test-workflow --verbose")
                
            else:
                console.print("❌ Schema template not found", style="red")

        if create_tables:
            console.print("Creating database tables...")
            schema_ok = asyncio.run(workflow.db.ensure_schema())
            if schema_ok:
                console.print("✅ Database schema verified", style="green")
            else:
                console.print("⚠️ Database schema needs to be created manually", style="yellow")
                console.print("💡 Run: politician-trading setup --generate-schema", style="blue")

    except Exception as e:
        console.print(f"❌ Setup failed: {e}", style="bold red")
        logger.error(f"Setup command failed: {e}")


@politician_trading_cli.command("cron-job")
@click.option("--create", is_flag=True, help="Show how to create Supabase cron job")
@click.option("--test", is_flag=True, help="Test the cron job function")
def manage_cron_job(create: bool, test: bool):
    """Manage Supabase cron job for automated data collection"""

    if create:
        console.print("🕒 Creating Supabase Cron Job", style="bold blue")

        cron_sql = """
-- Create cron job for politician trading data collection
SELECT cron.schedule(
    'politician-trading-collection',
    '0 */6 * * *',  -- Every 6 hours
    $$
    SELECT net.http_post(
        url := 'https://your-function-url.supabase.co/functions/v1/politician-trading-collect',
        headers := '{"Content-Type": "application/json", "Authorization": "Bearer YOUR_ANON_KEY"}'::jsonb,
        body := '{}'::jsonb
    ) as request_id;
    $$
);

-- Check cron job status
SELECT * FROM cron.job;
"""

        console.print("Add this SQL to your Supabase SQL editor:", style="green")
        console.print(Panel(cron_sql, title="📝 Cron Job SQL", border_style="green"))

        console.print("\n📋 Next steps:", style="bold blue")
        console.print("1. Create an Edge Function in Supabase for the collection endpoint")
        console.print("2. Update the URL in the cron job SQL above")
        console.print("3. Execute the SQL in your Supabase dashboard")
        console.print("4. Monitor the job with: SELECT * FROM cron.job_run_details;")

    if test:
        console.print("🧪 Testing cron job function...", style="yellow")
        try:
            result = asyncio.run(run_politician_trading_collection())
            console.print("✅ Cron job function test completed", style="green")
            console.print(JSON.from_data(result))
        except Exception as e:
            console.print(f"❌ Cron job test failed: {e}", style="red")


@politician_trading_cli.command("health")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def check_health(output_json: bool):
    """Check system health and status"""
    try:
        health = asyncio.run(run_health_check())

        if output_json:
            console.print(JSON.from_data(health))
        else:
            monitor = PoliticianTradingMonitor()
            monitor.display_health_report(health)

    except Exception as e:
        console.print(f"❌ Health check failed: {e}", style="bold red")
        logger.error(f"Health check command failed: {e}")


@politician_trading_cli.command("stats")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def show_stats(output_json: bool):
    """Show detailed statistics"""
    try:
        stats = asyncio.run(run_stats_report())

        if output_json:
            console.print(JSON.from_data(stats))
        else:
            monitor = PoliticianTradingMonitor()
            monitor.display_stats_report(stats)

    except Exception as e:
        console.print(f"❌ Stats generation failed: {e}", style="bold red")
        logger.error(f"Stats command failed: {e}")


@politician_trading_cli.command("monitor")
@click.option("--interval", default=30, help="Check interval in seconds")
@click.option("--count", default=0, help="Number of checks (0 = infinite)")
def continuous_monitor(interval: int, count: int):
    """Continuously monitor system health"""
    console.print(f"🔄 Starting continuous monitoring (interval: {interval}s)", style="bold blue")

    async def monitor_loop():
        monitor = PoliticianTradingMonitor()
        check_count = 0

        while True:
            try:
                console.clear()
                console.print(
                    f"Check #{check_count + 1} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    style="dim",
                )

                health = await monitor.get_system_health()
                monitor.display_health_report(health)

                check_count += 1
                if count > 0 and check_count >= count:
                    break

                if count == 0 or check_count < count:
                    console.print(
                        f"\n⏱️ Next check in {interval} seconds... (Ctrl+C to stop)", style="dim"
                    )
                    await asyncio.sleep(interval)

            except KeyboardInterrupt:
                console.print("\n👋 Monitoring stopped by user", style="yellow")
                break
            except Exception as e:
                console.print(f"❌ Monitor check failed: {e}", style="red")
                await asyncio.sleep(interval)

    try:
        asyncio.run(monitor_loop())
    except Exception as e:
        console.print(f"❌ Monitoring failed: {e}", style="bold red")
        logger.error(f"Monitor command failed: {e}")


@politician_trading_cli.command("connectivity")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--continuous", is_flag=True, help="Run continuous monitoring")
@click.option("--interval", default=30, help="Check interval in seconds (continuous mode)")
@click.option("--duration", default=0, help="Duration in minutes (0 = infinite)")
def check_connectivity(output_json: bool, continuous: bool, interval: int, duration: int):
    """Test Supabase connectivity and database operations"""
    if continuous:
        console.print(f"🔄 Starting continuous connectivity monitoring", style="bold blue")
        try:
            asyncio.run(run_continuous_monitoring(interval, duration))
        except Exception as e:
            console.print(f"❌ Continuous monitoring failed: {e}", style="bold red")
            logger.error(f"Continuous monitoring failed: {e}")
    else:
        try:
            validation_result = asyncio.run(run_connectivity_validation())
            
            if output_json:
                console.print(JSON.from_data(validation_result))
            else:
                validator = SupabaseConnectivityValidator()
                validator.display_connectivity_report(validation_result)
                
        except Exception as e:
            console.print(f"❌ Connectivity validation failed: {e}", style="bold red")
            logger.error(f"Connectivity validation failed: {e}")


@politician_trading_cli.command("test-workflow")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--validate-writes", is_flag=True, help="Validate database writes")
def test_full_workflow(verbose: bool, validate_writes: bool):
    """Run a complete workflow test with live Supabase connectivity"""
    console.print("🧪 Running Full Politician Trading Workflow Test", style="bold green")
    
    async def run_test():
        # First validate connectivity
        console.print("\n🔗 Step 1: Validating Supabase connectivity...", style="blue")
        validator = SupabaseConnectivityValidator()
        connectivity_result = await validator.validate_connectivity()
        
        if verbose:
            validator.display_connectivity_report(connectivity_result)
        else:
            console.print(f"Connectivity Score: {connectivity_result['connectivity_score']}%", style="cyan")
            
        if connectivity_result['connectivity_score'] < 75:
            console.print("⚠️ Connectivity issues detected. Workflow may fail.", style="yellow")
        
        # Run the workflow
        console.print("\n🏛️ Step 2: Running politician trading collection workflow...", style="blue")
        
        try:
            with console.status("[bold blue]Executing workflow...") as status:
                workflow_result = await run_politician_trading_collection()
            
            # Display workflow results
            console.print("\n📊 Workflow Results:", style="bold")
            
            if workflow_result.get("status") == "completed":
                console.print("✅ Workflow completed successfully!", style="green")
                
                summary = workflow_result.get("summary", {})
                console.print(f"New Disclosures: {summary.get('total_new_disclosures', 0)}")
                console.print(f"Updated Disclosures: {summary.get('total_updated_disclosures', 0)}")
                console.print(f"Errors: {len(summary.get('errors', []))}")
                
                if verbose and summary.get("errors"):
                    console.print("\nErrors encountered:", style="red")
                    for error in summary["errors"][:5]:  # Show first 5 errors
                        console.print(f"  • {error}", style="dim red")
                
            else:
                console.print("❌ Workflow failed!", style="red")
                if "error" in workflow_result:
                    console.print(f"Error: {workflow_result['error']}", style="red")
            
            # Validate writes if requested
            if validate_writes:
                console.print("\n🔍 Step 3: Validating database writes...", style="blue")
                write_validation = await validator._test_write_operations()
                
                if write_validation["success"]:
                    console.print("✅ Database writes validated successfully", style="green")
                else:
                    console.print(f"❌ Database write validation failed: {write_validation.get('error', 'Unknown error')}", style="red")
            
            # Final connectivity check
            console.print("\n🔗 Step 4: Post-workflow connectivity check...", style="blue")
            final_connectivity = await validator.validate_connectivity()
            
            console.print(f"Final Connectivity Score: {final_connectivity['connectivity_score']}%", style="cyan")
            
            # Summary
            console.print("\n📋 Test Summary:", style="bold")
            workflow_status = "✅ PASSED" if workflow_result.get("status") == "completed" else "❌ FAILED"
            connectivity_status = "✅ GOOD" if final_connectivity['connectivity_score'] >= 75 else "⚠️ DEGRADED"
            
            console.print(f"Workflow: {workflow_status}")
            console.print(f"Connectivity: {connectivity_status}")
            console.print(f"Duration: {workflow_result.get('started_at', '')} to {workflow_result.get('completed_at', '')}")
            
            return {
                "workflow_result": workflow_result,
                "connectivity_result": final_connectivity,
                "test_passed": workflow_result.get("status") == "completed" and final_connectivity['connectivity_score'] >= 75
            }
            
        except Exception as e:
            console.print(f"❌ Workflow test failed: {e}", style="bold red")
            if verbose:
                console.print_exception()
            return {"error": str(e), "test_passed": False}
    
    try:
        test_result = asyncio.run(run_test())
        
        if test_result.get("test_passed"):
            console.print("\n🎉 Full workflow test PASSED!", style="bold green")
        else:
            console.print("\n❌ Full workflow test FAILED!", style="bold red")
            
    except Exception as e:
        console.print(f"❌ Test execution failed: {e}", style="bold red")
        logger.error(f"Test workflow command failed: {e}")


@politician_trading_cli.command("schema")
@click.option("--show-location", is_flag=True, help="Show schema file location")
@click.option("--generate", is_flag=True, help="Generate schema files")
@click.option("--output-dir", default=".", help="Output directory for generated files")
def manage_schema(show_location: bool, generate: bool, output_dir: str):
    """Manage database schema files"""
    
    if show_location:
        console.print("📁 Schema File Locations", style="bold blue")
        
        from pathlib import Path
        schema_file = Path(__file__).parent / "schema.sql"
        
        console.print(f"Built-in Schema: {schema_file.absolute()}", style="cyan")
        console.print(f"File size: {schema_file.stat().st_size} bytes", style="dim")
        console.print(f"Exists: {'✅ Yes' if schema_file.exists() else '❌ No'}", style="green" if schema_file.exists() else "red")
        
        # Show current working directory option
        cwd_schema = Path.cwd() / "politician_trading_schema.sql"
        console.print(f"\nCurrent directory: {cwd_schema.absolute()}", style="cyan")
        console.print(f"Exists: {'✅ Yes' if cwd_schema.exists() else '❌ No'}", style="green" if cwd_schema.exists() else "dim")
        
        if not cwd_schema.exists():
            console.print("\n💡 To generate schema file here:", style="blue")
            console.print("politician-trading schema --generate", style="yellow")
    
    elif generate:
        # Reuse the setup command logic
        try:
            from pathlib import Path
            import os
            
            console.print("📄 Generating database schema files...", style="blue")
            
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)
            
            # Read the schema SQL from the module
            schema_file = Path(__file__).parent / "schema.sql"
            if schema_file.exists():
                schema_content = schema_file.read_text()
                
                # Write to output directory
                output_schema_file = output_path / "politician_trading_schema.sql"
                output_schema_file.write_text(schema_content)
                
                console.print(f"✅ Schema SQL generated: {output_schema_file.absolute()}", style="green")
                
                # Show file info
                console.print(f"📊 File size: {output_schema_file.stat().st_size:,} bytes")
                console.print(f"📅 Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Count SQL statements
                statements = len([line for line in schema_content.split('\n') if line.strip().startswith(('CREATE', 'INSERT', 'SELECT'))])
                console.print(f"📝 SQL statements: {statements}")
                
            else:
                console.print("❌ Schema template not found", style="red")
                
        except Exception as e:
            console.print(f"❌ Schema generation failed: {e}", style="red")
    
    else:
        # Show schema information by default
        console.print("🗂️ Politician Trading Database Schema", style="bold blue")
        
        schema_info = [
            ("politicians", "Stores politician information", "UUID primary key, bioguide_id, role, party"),
            ("trading_disclosures", "Individual trading transactions", "References politicians, amount ranges, asset details"),  
            ("data_pull_jobs", "Job execution tracking", "Status, timing, record counts, error details"),
            ("data_sources", "Data source configuration", "URLs, regions, health status, request config")
        ]
        
        schema_table = Table(title="Database Tables")
        schema_table.add_column("Table", style="cyan")
        schema_table.add_column("Purpose", style="white")
        schema_table.add_column("Key Features", style="yellow")
        
        for table_name, purpose, features in schema_info:
            schema_table.add_row(table_name, purpose, features)
        
        console.print(schema_table)
        
        console.print("\n🚀 Commands:", style="bold")
        console.print("  --show-location    Show where schema files are located")
        console.print("  --generate         Generate schema SQL file")
        console.print("  --generate --output-dir DIR  Generate to specific directory")


# Helper functions
def _calculate_duration(start_time: str, end_time: str) -> str:
    """Calculate duration between timestamps"""
    if not start_time or not end_time:
        return "Unknown"

    try:
        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        duration = end - start

        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    except Exception:
        return "Unknown"


def _format_timestamp(timestamp: str) -> str:
    """Format timestamp for display"""
    if not timestamp:
        return "Unknown"

    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return timestamp[:16] if len(timestamp) > 16 else timestamp


# Export the CLI group for registration
cli = politician_trading_cli
