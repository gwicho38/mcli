#!/usr/bin/env python3
"""
Demo script showing MCLI scheduler capabilities
"""

import time
from datetime import datetime
from src.mcli.workflow.scheduler.scheduler import (
    JobScheduler, 
    create_desktop_cleanup_job, 
    create_temp_cleanup_job
)
from src.mcli.workflow.scheduler.job import ScheduledJob, JobType

def demo_scheduler():
    """Demonstrate the scheduler functionality"""
    print("🤖 MCLI Scheduler Demo")
    print("=" * 50)
    
    # Create scheduler
    scheduler = JobScheduler()
    
    # Add some demo jobs
    print("\n📋 Adding demo jobs...")
    
    # 1. Simple command job
    echo_job = ScheduledJob(
        name="Demo Echo",
        cron_expression="@reboot",  # Run at startup
        job_type=JobType.COMMAND,
        command="echo 'Hello from MCLI Scheduler!'",
        description="Simple echo command for demo"
    )
    scheduler.add_job(echo_job)
    print(f"✓ Added: {echo_job.name}")
    
    # 2. Desktop cleanup job
    desktop_job = create_desktop_cleanup_job(
        name="Desktop Organization",
        cron_expression="*/2 * * * *",  # Every 2 minutes for demo
        enabled=True
    )
    scheduler.add_job(desktop_job)
    print(f"✓ Added: {desktop_job.name}")
    
    # 3. System info job
    sysinfo_job = ScheduledJob(
        name="System Info",
        cron_expression="*/3 * * * *",  # Every 3 minutes
        job_type=JobType.COMMAND,
        command="uname -a && date && df -h",
        description="Collect system information"
    )
    scheduler.add_job(sysinfo_job)
    print(f"✓ Added: {sysinfo_job.name}")
    
    # 4. Python script job
    python_job = ScheduledJob(
        name="Python Demo",
        cron_expression="*/5 * * * *",  # Every 5 minutes
        job_type=JobType.PYTHON,
        command="""
import json
import platform
from datetime import datetime

data = {
    "timestamp": datetime.now().isoformat(),
    "platform": platform.system(),
    "python_version": platform.python_version(),
    "message": "Hello from Python scheduler job!"
}

print(json.dumps(data, indent=2))
""",
        description="Python script execution demo",
        output_format="json"
    )
    scheduler.add_job(python_job)
    print(f"✓ Added: {python_job.name}")
    
    # Show all jobs
    print(f"\n📊 Total jobs added: {len(scheduler.get_all_jobs())}")
    
    # Show scheduler stats
    stats = scheduler.get_scheduler_stats()
    print(f"📈 Scheduler stats:")
    print(f"   Total jobs: {stats['total_jobs']}")
    print(f"   Enabled jobs: {stats['enabled_jobs']}")
    print(f"   Running: {stats['running']}")
    
    # Start scheduler
    print(f"\n🚀 Starting scheduler...")
    scheduler.start()
    
    print(f"✓ Scheduler started!")
    print(f"📁 Storage directory: {scheduler.storage.storage_dir}")
    
    # Show JSON API response
    print(f"\n🔗 JSON API Response:")
    response = scheduler.create_json_response()
    import json
    print(json.dumps(response, indent=2)[:500] + "...")
    
    # Let it run for a bit
    print(f"\n⏱️  Letting scheduler run for 30 seconds...")
    print(f"   Watch for job executions...")
    
    for i in range(30):
        time.sleep(1)
        if i % 5 == 0:
            running_jobs = scheduler.monitor.get_running_jobs()
            if running_jobs:
                print(f"   Currently running: {', '.join(running_jobs)}")
            else:
                print(f"   No jobs currently running (t+{i}s)")
    
    # Show final stats
    print(f"\n📈 Final stats:")
    final_stats = scheduler.get_scheduler_stats()
    print(f"   Running jobs: {final_stats['running_jobs']}")
    
    # Show job history
    print(f"\n📜 Recent job history:")
    for job in scheduler.get_all_jobs():
        history = scheduler.storage.get_job_history(job.id, limit=2)
        if history:
            print(f"   {job.name}: {len(history)} executions")
            for record in history[:1]:  # Show most recent
                status = record.get('status', 'unknown')
                executed_at = record.get('executed_at', 'unknown')
                print(f"      Last: {status} at {executed_at}")
    
    # Stop scheduler
    print(f"\n🛑 Stopping scheduler...")
    scheduler.stop()
    print(f"✓ Demo complete!")

if __name__ == "__main__":
    demo_scheduler()