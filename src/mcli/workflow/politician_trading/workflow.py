"""
Main workflow orchestrator for politician trading data collection
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from .config import WorkflowConfig
from .database import PoliticianTradingDB
from .models import DataPullJob, Politician, TradingDisclosure, PoliticianRole
from .scrapers import (
    CongressTradingScraper,
    QuiverQuantScraper,
    EUParliamentScraper,
    PoliticianMatcher,
)

logger = logging.getLogger(__name__)


class PoliticianTradingWorkflow:
    """Main workflow for collecting politician trading data"""

    def __init__(self, config: WorkflowConfig = None):
        self.config = config or WorkflowConfig.default()
        self.db = PoliticianTradingDB(self.config)
        self.politicians: List[Politician] = []

    async def run_full_collection(self) -> Dict[str, Any]:
        """Run complete data collection workflow"""
        logger.info("Starting full politician trading data collection")

        results = {
            "started_at": datetime.utcnow().isoformat(),
            "jobs": {},
            "summary": {"total_new_disclosures": 0, "total_updated_disclosures": 0, "errors": []},
        }

        try:
            # Ensure database schema
            schema_ok = await self.db.ensure_schema()
            if not schema_ok:
                raise Exception("Database schema verification failed")

            # Load existing politicians for matching
            await self._load_politicians()

            # Run US Congress collection
            us_results = await self._collect_us_congress_data()
            results["jobs"]["us_congress"] = us_results
            results["summary"]["total_new_disclosures"] += us_results.get("new_disclosures", 0)
            results["summary"]["total_updated_disclosures"] += us_results.get(
                "updated_disclosures", 0
            )

            # Run EU Parliament collection
            eu_results = await self._collect_eu_parliament_data()
            results["jobs"]["eu_parliament"] = eu_results
            results["summary"]["total_new_disclosures"] += eu_results.get("new_disclosures", 0)
            results["summary"]["total_updated_disclosures"] += eu_results.get(
                "updated_disclosures", 0
            )

            results["completed_at"] = datetime.utcnow().isoformat()
            results["status"] = "completed"

        except Exception as e:
            logger.error(f"Full collection workflow failed: {e}")
            results["error"] = str(e)
            results["status"] = "failed"
            results["summary"]["errors"].append(str(e))

        logger.info(f"Workflow completed: {results['summary']}")
        return results

    async def _load_politicians(self):
        """Load politicians from database for matching"""
        try:
            # For now, create some sample politicians
            # In production, you'd load from a politicians API or database
            sample_politicians = [
                Politician(
                    id="pol_1",
                    first_name="Nancy",
                    last_name="Pelosi",
                    full_name="Nancy Pelosi",
                    role=PoliticianRole.US_HOUSE_REP,
                    party="Democratic",
                    state_or_country="CA",
                    district="5",
                    bioguide_id="P000197",
                ),
                Politician(
                    id="pol_2",
                    first_name="Ted",
                    last_name="Cruz",
                    full_name="Ted Cruz",
                    role=PoliticianRole.US_SENATOR,
                    party="Republican",
                    state_or_country="TX",
                    bioguide_id="C001098",
                ),
            ]

            # Store politicians in database
            for politician in sample_politicians:
                politician_id = await self.db.upsert_politician(politician)
                politician.id = politician_id
                self.politicians.append(politician)

            logger.info(f"Loaded {len(self.politicians)} politicians for matching")

        except Exception as e:
            logger.error(f"Failed to load politicians: {e}")
            self.politicians = []

    async def _collect_us_congress_data(self) -> Dict[str, Any]:
        """Collect US Congress trading data"""
        job_id = await self.db.create_data_pull_job("us_congress", self.config.__dict__)

        job_result = {
            "job_id": job_id,
            "status": "running",
            "new_disclosures": 0,
            "updated_disclosures": 0,
            "errors": [],
        }

        job = DataPullJob(
            id=job_id, job_type="us_congress", status="running", started_at=datetime.utcnow()
        )

        try:
            logger.info("Starting US Congress data collection")

            # Initialize scrapers
            congress_scraper = CongressTradingScraper(self.config.scraping)
            quiver_scraper = QuiverQuantScraper(self.config.scraping)

            all_disclosures = []

            # Scrape official sources
            async with congress_scraper:
                house_disclosures = await congress_scraper.scrape_house_disclosures()
                senate_disclosures = await congress_scraper.scrape_senate_disclosures()
                all_disclosures.extend(house_disclosures)
                all_disclosures.extend(senate_disclosures)

            # Scrape backup sources
            async with quiver_scraper:
                quiver_trades = await quiver_scraper.scrape_congress_trades()
                for trade_data in quiver_trades:
                    disclosure = quiver_scraper.parse_quiver_trade(trade_data)
                    if disclosure:
                        all_disclosures.append(disclosure)

            job.records_found = len(all_disclosures)

            # Process disclosures
            matcher = PoliticianMatcher(self.politicians)

            for disclosure in all_disclosures:
                try:
                    # Find matching politician
                    politician_name = disclosure.raw_data.get("politician_name", "")
                    politician = matcher.find_politician(politician_name)

                    if not politician:
                        logger.warning(f"No politician match for: {politician_name}")
                        job.records_failed += 1
                        continue

                    disclosure.politician_id = politician.id

                    # Check if disclosure already exists
                    existing = await self.db.find_disclosure_by_transaction(
                        disclosure.politician_id,
                        disclosure.transaction_date,
                        disclosure.asset_name,
                        disclosure.transaction_type.value,
                    )

                    if existing:
                        # Update existing record
                        disclosure.id = existing.id
                        if await self.db.update_disclosure(disclosure):
                            job.records_updated += 1
                            job_result["updated_disclosures"] += 1
                        else:
                            job.records_failed += 1
                    else:
                        # Insert new record
                        disclosure_id = await self.db.insert_disclosure(disclosure)
                        if disclosure_id:
                            job.records_new += 1
                            job_result["new_disclosures"] += 1
                        else:
                            job.records_failed += 1

                    job.records_processed += 1

                except Exception as e:
                    logger.error(f"Failed to process disclosure: {e}")
                    job.records_failed += 1
                    job_result["errors"].append(str(e))

            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job_result["status"] = "completed"

        except Exception as e:
            logger.error(f"US Congress collection failed: {e}")
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            job_result["status"] = "failed"
            job_result["errors"].append(str(e))

        # Update job status
        await self.db.update_data_pull_job(job)

        return job_result

    async def _collect_eu_parliament_data(self) -> Dict[str, Any]:
        """Collect EU Parliament trading/financial data"""
        job_id = await self.db.create_data_pull_job("eu_parliament", self.config.__dict__)

        job_result = {
            "job_id": job_id,
            "status": "running",
            "new_disclosures": 0,
            "updated_disclosures": 0,
            "errors": [],
        }

        job = DataPullJob(
            id=job_id, job_type="eu_parliament", status="running", started_at=datetime.utcnow()
        )

        try:
            logger.info("Starting EU Parliament data collection")

            scraper = EUParliamentScraper(self.config.scraping)

            async with scraper:
                disclosures = await scraper.scrape_mep_declarations()

            job.records_found = len(disclosures)

            # Process EU disclosures (similar to US processing)
            for disclosure in disclosures:
                try:
                    # For EU, we'd need a different politician matching strategy
                    # For now, create a sample politician
                    if not disclosure.politician_id:
                        # Create placeholder politician
                        eu_politician = Politician(
                            first_name="Sample",
                            last_name="MEP",
                            full_name="Sample MEP",
                            role=PoliticianRole.EU_MEP,
                            state_or_country="EU",
                        )
                        politician_id = await self.db.upsert_politician(eu_politician)
                        disclosure.politician_id = politician_id

                    # Insert disclosure
                    disclosure_id = await self.db.insert_disclosure(disclosure)
                    if disclosure_id:
                        job.records_new += 1
                        job_result["new_disclosures"] += 1
                    else:
                        job.records_failed += 1

                    job.records_processed += 1

                except Exception as e:
                    logger.error(f"Failed to process EU disclosure: {e}")
                    job.records_failed += 1
                    job_result["errors"].append(str(e))

            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job_result["status"] = "completed"

        except Exception as e:
            logger.error(f"EU Parliament collection failed: {e}")
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            job_result["status"] = "failed"
            job_result["errors"].append(str(e))

        # Update job status
        await self.db.update_data_pull_job(job)

        return job_result

    async def get_status(self) -> Dict[str, Any]:
        """Get current workflow status"""
        try:
            return await self.db.get_job_status()
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {"error": str(e)}

    async def run_quick_check(self) -> Dict[str, Any]:
        """Run a quick status check without full data collection"""
        try:
            status = await self.get_status()

            # Add some additional quick checks
            status["database_connection"] = "ok" if self.db.client else "failed"
            status["config_loaded"] = "ok" if self.config else "failed"
            status["timestamp"] = datetime.utcnow().isoformat()

            return status

        except Exception as e:
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat(), "status": "failed"}


# Standalone functions for cron job usage
async def run_politician_trading_collection() -> Dict[str, Any]:
    """Standalone function for cron job execution"""
    workflow = PoliticianTradingWorkflow()
    return await workflow.run_full_collection()


async def check_politician_trading_status() -> Dict[str, Any]:
    """Standalone function for status checking"""
    workflow = PoliticianTradingWorkflow()
    return await workflow.run_quick_check()
