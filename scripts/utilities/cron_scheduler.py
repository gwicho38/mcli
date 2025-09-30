#!/usr/bin/env python3
"""
Politician Trading Cron Scheduler

This script sets up automated data collection jobs that can be run via cron
and provides easy database read access for the collected data.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcli.workflow.politician_trading.workflow import PoliticianTradingWorkflow, run_politician_trading_collection
from mcli.workflow.politician_trading.database import PoliticianTradingDB
from mcli.workflow.politician_trading.config import WorkflowConfig

# Set up logging for cron jobs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/politician_trading_cron.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PoliticianTradingCronManager:
    """Manages cron-triggered data collection and database operations"""
    
    def __init__(self):
        self.config = WorkflowConfig.default()
        self.db = PoliticianTradingDB(self.config)
        self.workflow = PoliticianTradingWorkflow(self.config)
    
    async def run_scheduled_collection(self, collection_type: str = "full") -> Dict[str, Any]:
        """
        Run a scheduled data collection job
        
        Args:
            collection_type: "full", "us_only", "eu_only", or "quick"
        """
        logger.info(f"Starting scheduled collection: {collection_type}")
        
        try:
            if collection_type == "full":
                results = await run_politician_trading_collection()
            elif collection_type == "us_only":
                results = await self._run_us_only_collection()
            elif collection_type == "eu_only":
                results = await self._run_eu_only_collection()
            elif collection_type == "quick":
                results = await self._run_quick_collection()
            else:
                raise ValueError(f"Unknown collection type: {collection_type}")
            
            # Log results
            summary = results.get('summary', {})
            logger.info(f"Collection completed - New: {summary.get('total_new_disclosures', 0)}, "
                       f"Updated: {summary.get('total_updated_disclosures', 0)}")
            
            return results
            
        except Exception as e:
            logger.error(f"Scheduled collection failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def _run_us_only_collection(self) -> Dict[str, Any]:
        """Run collection for US sources only"""
        us_results = await self.workflow._collect_us_congress_data()
        ca_results = await self.workflow._collect_california_data()
        us_states_results = await self.workflow._collect_us_states_data()
        
        return {
            "status": "completed",
            "jobs": {
                "us_congress": us_results,
                "california": ca_results,
                "us_states": us_states_results
            },
            "summary": {
                "total_new_disclosures": sum([
                    us_results.get("new_disclosures", 0),
                    ca_results.get("new_disclosures", 0),
                    us_states_results.get("new_disclosures", 0)
                ]),
                "total_updated_disclosures": sum([
                    us_results.get("updated_disclosures", 0),
                    ca_results.get("updated_disclosures", 0),
                    us_states_results.get("updated_disclosures", 0)
                ])
            }
        }
    
    async def _run_eu_only_collection(self) -> Dict[str, Any]:
        """Run collection for EU sources only"""
        eu_results = await self.workflow._collect_eu_parliament_data()
        eu_states_results = await self.workflow._collect_eu_member_states_data()
        uk_results = await self.workflow._collect_uk_parliament_data()
        
        return {
            "status": "completed",
            "jobs": {
                "eu_parliament": eu_results,
                "eu_member_states": eu_states_results,
                "uk_parliament": uk_results
            },
            "summary": {
                "total_new_disclosures": sum([
                    eu_results.get("new_disclosures", 0),
                    eu_states_results.get("new_disclosures", 0),
                    uk_results.get("new_disclosures", 0)
                ]),
                "total_updated_disclosures": sum([
                    eu_results.get("updated_disclosures", 0),
                    eu_states_results.get("updated_disclosures", 0),
                    uk_results.get("updated_disclosures", 0)
                ])
            }
        }
    
    async def _run_quick_collection(self) -> Dict[str, Any]:
        """Run a quick status check and minimal collection"""
        status = await self.workflow.run_quick_check()
        return {
            "status": "completed",
            "type": "quick_check",
            "results": status,
            "summary": {"total_new_disclosures": 0, "total_updated_disclosures": 0}
        }


class DatabaseReader:
    """Easy interface for reading collected data from the database"""
    
    def __init__(self):
        self.config = WorkflowConfig.default()
        self.db = PoliticianTradingDB(self.config)
    
    async def get_recent_disclosures(self, limit: int = 50, days_back: int = 30) -> List[Dict[str, Any]]:
        """Get recent trading disclosures"""
        try:
            # This would implement actual database queries
            # For now, showing the structure
            logger.info(f"Fetching {limit} recent disclosures from last {days_back} days")
            
            # In a real implementation, this would query the database
            # Example query structure:
            # SELECT * FROM trading_disclosures 
            # WHERE transaction_date >= NOW() - INTERVAL '{days_back} days'
            # ORDER BY transaction_date DESC 
            # LIMIT {limit}
            
            return []  # Would return actual data
            
        except Exception as e:
            logger.error(f"Failed to get recent disclosures: {e}")
            return []
    
    async def get_politician_summary(self) -> Dict[str, Any]:
        """Get summary of politicians in database"""
        try:
            # Query politician counts by role and jurisdiction
            return {
                "total_politicians": 0,
                "by_role": {},
                "by_jurisdiction": {},
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get politician summary: {e}")
            return {"error": str(e)}
    
    async def get_job_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent job execution history"""
        try:
            job_status = await self.db.get_job_status()
            recent_jobs = job_status.get('recent_jobs', [])
            return recent_jobs[:limit]
        except Exception as e:
            logger.error(f"Failed to get job history: {e}")
            return []
    
    async def get_data_freshness(self) -> Dict[str, Any]:
        """Get information about data freshness by source"""
        try:
            job_history = await self.get_job_history()
            
            freshness = {}
            for job in job_history:
                job_type = job.get('job_type', 'unknown')
                if job.get('status') == 'completed':
                    completed_at = job.get('completed_at')
                    if job_type not in freshness or completed_at > freshness[job_type]['last_success']:
                        freshness[job_type] = {
                            'last_success': completed_at,
                            'records_collected': job.get('records_new', 0),
                            'status': 'fresh' if self._is_recent(completed_at) else 'stale'
                        }
            
            return freshness
            
        except Exception as e:
            logger.error(f"Failed to get data freshness: {e}")
            return {}
    
    def _is_recent(self, timestamp_str: str, hours_threshold: int = 24) -> bool:
        """Check if a timestamp is recent"""
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return (datetime.now() - timestamp.replace(tzinfo=None)) < timedelta(hours=hours_threshold)
        except:
            return False


async def cron_full_collection():
    """Function to be called by cron for full data collection"""
    manager = PoliticianTradingCronManager()
    results = await manager.run_scheduled_collection("full")
    print(f"Cron job completed: {results.get('status', 'unknown')}")
    return results


async def cron_us_collection():
    """Function to be called by cron for US-only collection"""
    manager = PoliticianTradingCronManager()
    results = await manager.run_scheduled_collection("us_only")
    print(f"US collection completed: {results.get('status', 'unknown')}")
    return results


async def cron_eu_collection():
    """Function to be called by cron for EU-only collection"""
    manager = PoliticianTradingCronManager()
    results = await manager.run_scheduled_collection("eu_only")
    print(f"EU collection completed: {results.get('status', 'unknown')}")
    return results


async def read_recent_data():
    """Function to easily read recent data"""
    reader = DatabaseReader()
    
    print("📊 RECENT DATA SUMMARY")
    print("=" * 40)
    
    # Get job history
    jobs = await reader.get_job_history(10)
    print(f"\n📋 Recent Jobs: {len(jobs)}")
    for job in jobs[:5]:
        status_icon = {'completed': '✅', 'running': '🔄', 'failed': '❌', 'pending': '⏳'}.get(job.get('status'), '❓')
        print(f"{status_icon} {job.get('job_type', 'unknown').replace('_', ' ').title()}: {job.get('started_at', 'N/A')[:19]}")
    
    # Get data freshness
    freshness = await reader.get_data_freshness()
    print(f"\n🕐 Data Freshness:")
    for source, info in freshness.items():
        status_icon = '🟢' if info['status'] == 'fresh' else '🟡'
        print(f"{status_icon} {source.replace('_', ' ').title()}: {info['last_success'][:19] if info['last_success'] else 'Never'}")
    
    # Get politician summary
    pol_summary = await reader.get_politician_summary()
    print(f"\n👥 Politicians: {pol_summary.get('total_politicians', 'Unknown')}")
    
    # Get recent disclosures
    disclosures = await reader.get_recent_disclosures(10)
    print(f"📈 Recent Disclosures: {len(disclosures)}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "full":
            asyncio.run(cron_full_collection())
        elif command == "us":
            asyncio.run(cron_us_collection())
        elif command == "eu":
            asyncio.run(cron_eu_collection())
        elif command == "read":
            asyncio.run(read_recent_data())
        elif command == "install-cron":
            print("🕐 CRON INSTALLATION INSTRUCTIONS")
            print("=" * 50)
            print("Add these lines to your crontab (crontab -e):")
            print()
            print("# Full collection every 6 hours")
            print("0 */6 * * * cd /Users/lefv/repos/mcli && source .venv/bin/activate && python cron_scheduler.py full >> /tmp/politician_cron.log 2>&1")
            print()
            print("# US collection every 4 hours")
            print("0 */4 * * * cd /Users/lefv/repos/mcli && source .venv/bin/activate && python cron_scheduler.py us >> /tmp/politician_cron.log 2>&1")
            print()
            print("# EU collection every 8 hours")
            print("0 */8 * * * cd /Users/lefv/repos/mcli && source .venv/bin/activate && python cron_scheduler.py eu >> /tmp/politician_cron.log 2>&1")
            print()
            print("# Read data summary daily")
            print("0 9 * * * cd /Users/lefv/repos/mcli && source .venv/bin/activate && python cron_scheduler.py read >> /tmp/politician_cron.log 2>&1")
        else:
            print(f"Unknown command: {command}")
    else:
        print("🤖 POLITICIAN TRADING CRON SCHEDULER")
        print("=" * 50)
        print("Usage:")
        print("  python cron_scheduler.py full        # Run full collection")
        print("  python cron_scheduler.py us          # Run US-only collection")
        print("  python cron_scheduler.py eu          # Run EU-only collection") 
        print("  python cron_scheduler.py read        # Read recent data")
        print("  python cron_scheduler.py install-cron # Show cron setup instructions")