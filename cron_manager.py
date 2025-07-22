#!/usr/bin/env python3
"""
Standalone MCLI Cron Manager

This script provides cron job management for MCLI commands without integrating
with the main Click application to avoid recursion issues.
"""

import click
import os
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import uuid
import re
from dataclasses import dataclass, asdict
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CronJob:
    """Represents a scheduled cron job"""
    id: str
    name: str
    command_name: str
    command_args: List[str]
    schedule: str  # cron expression (e.g., "0 2 * * *")
    description: str
    enabled: bool = True
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class CronManager:
    """Cron job manager for MCLI commands"""
    
    def __init__(self):
        self.cron_dir = Path.home() / ".local" / "mcli" / "cron"
        self.cron_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_file = self.cron_dir / "jobs.json"
        self.jobs = self._load_jobs()
        
    def _load_jobs(self) -> Dict[str, CronJob]:
        """Load cron jobs from JSON file"""
        if not self.jobs_file.exists():
            return {}
        
        try:
            with open(self.jobs_file, 'r') as f:
                data = json.load(f)
            
            jobs = {}
            for job_id, job_data in data.items():
                job_data['created_at'] = datetime.fromisoformat(job_data['created_at'])
                jobs[job_id] = CronJob(**job_data)
            
            return jobs
        except Exception as e:
            logger.error(f"Error loading cron jobs: {e}")
            return {}
    
    def _save_jobs(self):
        """Save cron jobs to JSON file"""
        try:
            data = {}
            for job_id, job in self.jobs.items():
                job_data = asdict(job)
                job_data['created_at'] = job.created_at.isoformat()
                data[job_id] = job_data
            
            with open(self.jobs_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cron jobs: {e}")
    
    def add_job(self, name: str, command_name: str, schedule: str, 
                command_args: List[str] = None, description: str = None) -> str:
        """Add a new cron job"""
        job_id = str(uuid.uuid4())
        
        job = CronJob(
            id=job_id,
            name=name,
            command_name=command_name,
            command_args=command_args or [],
            schedule=schedule,
            description=description or f"Scheduled job for {command_name}"
        )
        
        self.jobs[job_id] = job
        self._save_jobs()
        
        # Create wrapper script
        self._create_wrapper_script(job)
        
        logger.info(f"Added cron job '{name}' with ID {job_id}")
        return job_id
    
    def remove_job(self, job_id: str) -> bool:
        """Remove a cron job"""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        
        # Remove wrapper script
        script_path = self.cron_dir / f"job_{job_id}.sh"
        if script_path.exists():
            script_path.unlink()
        
        # Remove from jobs
        del self.jobs[job_id]
        self._save_jobs()
        
        logger.info(f"Removed cron job '{job.name}' with ID {job_id}")
        return True
    
    def list_jobs(self) -> List[CronJob]:
        """List all cron jobs"""
        return list(self.jobs.values())
    
    def get_job(self, job_id: str) -> Optional[CronJob]:
        """Get a specific cron job"""
        return self.jobs.get(job_id)
    
    def _create_wrapper_script(self, job: CronJob):
        """Create a wrapper script for the cron job"""
        script_path = self.cron_dir / f"job_{job.id}.sh"
        
        # Create the script content
        script_content = f"""#!/bin/bash
# MCLI Cron Job: {job.name}
# Job ID: {job.id}
# Command: {job.command_name}
# Created: {job.created_at.isoformat()}

# Set environment
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
export HOME="{Path.home()}"
export MCLI_DAEMON_ROUTING=true

# Log start
echo "[$(date)] Starting cron job: {job.name}"

# Execute command via daemon
python -m mcli workflow api-daemon execute --command-name {job.command_name} {' '.join(job.command_args)}

# Log completion
echo "[$(date)] Completed cron job: {job.name}"
"""
        
        # Write script
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make executable
        script_path.chmod(0o755)
        
        return str(script_path)
    
    def validate_schedule(self, schedule: str) -> bool:
        """Validate a cron schedule expression"""
        # Basic cron expression validation
        parts = schedule.split()
        if len(parts) != 5:
            return False
        
        # Validate each part
        patterns = [
            r'^(\*|[0-5]?[0-9](-[0-5]?[0-9])?(,\d+)*|\*/\d+)$',  # minute
            r'^(\*|1?[0-9]|2[0-3](-1?[0-9]|2[0-3])?(,\d+)*|\*/\d+)$',  # hour
            r'^(\*|[1-9]|[12][0-9]|3[01](-[1-9]|[12][0-9]|3[01])?(,\d+)*|\*/\d+)$',  # day
            r'^(\*|[1-9]|1[0-2](-[1-9]|1[0-2])?(,\d+)*|\*/\d+)$',  # month
            r'^(\*|[0-6](-[0-6])?(,\d+)*|\*/\d+)$'  # weekday
        ]
        
        for i, part in enumerate(parts):
            if not re.match(patterns[i], part):
                return False
        
        return True

# Global cron manager instance
cron_manager = CronManager()

@click.group()
def cli():
    """MCLI Cron Manager - Schedule MCLI commands to run automatically"""
    pass

@cli.command()
@click.argument('name')
@click.argument('command_name')
@click.argument('schedule')
@click.option('--args', '-a', multiple=True, help='Command arguments')
@click.option('--description', '-d', help='Job description')
def add(name: str, command_name: str, schedule: str, args: tuple, description: str):
    """Add a new cron job"""
    # Validate schedule
    if not cron_manager.validate_schedule(schedule):
        click.echo(f"❌ Invalid cron schedule: {schedule}", err=True)
        click.echo("Schedule format: minute hour day month weekday")
        click.echo("Examples:")
        click.echo("  0 2 * * *     # Daily at 2 AM")
        click.echo("  */15 * * * *  # Every 15 minutes")
        click.echo("  0 9 * * 1-5   # Weekdays at 9 AM")
        return
    
    # Add the job
    job_id = cron_manager.add_job(
        name=name,
        command_name=command_name,
        schedule=schedule,
        command_args=list(args),
        description=description
    )
    
    click.echo(f"✅ Added cron job '{name}' with ID {job_id}")
    click.echo(f"Schedule: {schedule}")
    click.echo(f"Command: {command_name} {' '.join(args)}")
    click.echo(f"Wrapper script: {cron_manager.cron_dir}/job_{job_id}.sh")
    click.echo(f"To install in crontab, run:")
    click.echo(f"  echo '{schedule} {cron_manager.cron_dir}/job_{job_id}.sh >> /tmp/mcli_cron.log 2>&1' | crontab -")

@cli.command()
@click.argument('job_id')
def remove(job_id: str):
    """Remove a cron job"""
    if cron_manager.remove_job(job_id):
        click.echo(f"✅ Removed cron job {job_id}")
    else:
        click.echo(f"❌ Job {job_id} not found", err=True)

@cli.command()
def list_jobs():
    """List all cron jobs"""
    jobs = cron_manager.list_jobs()
    
    if not jobs:
        click.echo("No cron jobs found")
        return
    
    click.echo(f"Found {len(jobs)} cron job(s):")
    click.echo()
    
    for job in jobs:
        status = "✅ Enabled" if job.enabled else "❌ Disabled"
        click.echo(f"ID: {job.id}")
        click.echo(f"Name: {job.name}")
        click.echo(f"Command: {job.command_name} {' '.join(job.command_args)}")
        click.echo(f"Schedule: {job.schedule}")
        click.echo(f"Status: {status}")
        click.echo(f"Created: {job.created_at}")
        click.echo(f"Wrapper: {cron_manager.cron_dir}/job_{job.id}.sh")
        click.echo()

@cli.command()
@click.argument('job_id')
def show(job_id: str):
    """Show details of a specific cron job"""
    job = cron_manager.get_job(job_id)
    
    if not job:
        click.echo(f"❌ Job {job_id} not found", err=True)
        return
    
    click.echo(f"Job Details for {job_id}:")
    click.echo(f"  Name: {job.name}")
    click.echo(f"  Description: {job.description}")
    click.echo(f"  Command: {job.command_name} {' '.join(job.command_args)}")
    click.echo(f"  Schedule: {job.schedule}")
    click.echo(f"  Status: {'Enabled' if job.enabled else 'Disabled'}")
    click.echo(f"  Created: {job.created_at}")
    click.echo(f"  Wrapper Script: {cron_manager.cron_dir}/job_{job_id}.sh")

@cli.command()
@click.argument('schedule')
def validate(schedule: str):
    """Validate a cron schedule expression"""
    if cron_manager.validate_schedule(schedule):
        click.echo(f"✅ Valid cron schedule: {schedule}")
    else:
        click.echo(f"❌ Invalid cron schedule: {schedule}", err=True)
        click.echo("Schedule format: minute hour day month weekday")
        click.echo("Examples:")
        click.echo("  0 2 * * *     # Daily at 2 AM")
        click.echo("  */15 * * * *  # Every 15 minutes")
        click.echo("  0 9 * * 1-5   # Weekdays at 9 AM")

@cli.command()
def examples():
    """Show cron schedule examples"""
    click.echo("Cron Schedule Examples:")
    click.echo()
    click.echo("Common Patterns:")
    click.echo("  */5 * * * *     # Every 5 minutes")
    click.echo("  0 */2 * * *     # Every 2 hours")
    click.echo("  0 2 * * *       # Daily at 2 AM")
    click.echo("  0 9 * * 1-5     # Weekdays at 9 AM")
    click.echo("  0 0 1 * *       # Monthly on the 1st")
    click.echo("  0 0 * * 0       # Weekly on Sunday")
    click.echo()
    click.echo("Specific Times:")
    click.echo("  30 14 * * *     # Daily at 2:30 PM")
    click.echo("  0 8,12,18 * * * # Daily at 8 AM, 12 PM, 6 PM")
    click.echo("  0 9 * * 1       # Mondays at 9 AM")
    click.echo()
    click.echo("Complex Patterns:")
    click.echo("  0 9-17 * * 1-5  # Weekdays, 9 AM to 5 PM")
    click.echo("  0 0 1,15 * *    # 1st and 15th of each month")
    click.echo("  */30 9-17 * * 1-5 # Every 30 minutes, weekdays 9-5")

@cli.command()
def install():
    """Install all cron jobs to the system crontab"""
    jobs = cron_manager.list_jobs()
    
    if not jobs:
        click.echo("No cron jobs to install")
        return
    
    try:
        # Get current crontab
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        current_crontab = result.stdout if result.returncode == 0 else ""
        
        # Add new lines for each job
        new_lines = []
        for job in jobs:
            if job.enabled:
                script_path = f"{cron_manager.cron_dir}/job_{job.id}.sh"
                cron_line = f"{job.schedule} {script_path} >> /tmp/mcli_cron.log 2>&1"
                new_lines.append(cron_line)
        
        # Combine current and new crontab
        new_crontab = current_crontab + "\n".join(new_lines) + "\n"
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(new_crontab)
            temp_file = f.name
        
        # Install new crontab
        subprocess.run(['crontab', temp_file], check=True)
        
        # Clean up
        os.unlink(temp_file)
        
        click.echo(f"✅ Installed {len(new_lines)} cron jobs to system crontab")
        
    except Exception as e:
        click.echo(f"❌ Error installing cron jobs: {e}", err=True)

if __name__ == '__main__':
    cli() 