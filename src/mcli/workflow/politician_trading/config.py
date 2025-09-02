"""
Configuration for politician trading data workflow
"""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class SupabaseConfig:
    """Supabase database configuration"""

    url: str
    key: str
    service_role_key: Optional[str] = None

    @classmethod
    def from_env(cls) -> "SupabaseConfig":
        """Load configuration from environment or use provided values"""
        # Your provided Supabase details
        url = os.getenv("SUPABASE_URL", "https://uljsqvwkomdrlnofmlad.supabase.co")
        key = os.getenv(
            "SUPABASE_ANON_KEY",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVsanNxdndrb21kcmxub2ZtbGFkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4MDIyNDQsImV4cCI6MjA3MjM3ODI0NH0.QCpfcEpxGX_5Wn8ljf_J2KWjJLGdF8zRsV_7OatxmHI",
        )
        service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        return cls(url=url, key=key, service_role_key=service_role_key)


@dataclass
class ScrapingConfig:
    """Web scraping configuration"""

    # Rate limiting
    request_delay: float = 1.0  # seconds between requests
    max_retries: int = 3
    timeout: int = 30

    # User agent for requests
    user_agent: str = "Mozilla/5.0 (compatible; MCLI-PoliticianTracker/1.0)"

    # Data sources
    us_congress_sources: list = None
    eu_sources: list = None

    def __post_init__(self):
        if self.us_congress_sources is None:
            self.us_congress_sources = [
                "https://disclosures-clerk.house.gov/PublicDisclosure/FinancialDisclosure",
                "https://efdsearch.senate.gov/search/",
                # Third-party aggregators as fallback
                "https://api.quiverquant.com/beta/live/congresstrading",  # Example API
            ]

        if self.eu_sources is None:
            self.eu_sources = [
                # EU Parliament disclosure sources
                "https://www.europarl.europa.eu/meps/en/declarations",
                # Individual country sources would be added here
            ]


@dataclass
class WorkflowConfig:
    """Overall workflow configuration"""

    supabase: SupabaseConfig
    scraping: ScrapingConfig

    # Cron schedule (for reference, actual scheduling done in Supabase)
    cron_schedule: str = "0 */6 * * *"  # Every 6 hours

    # Data retention
    retention_days: int = 365  # Keep data for 1 year

    @classmethod
    def default(cls) -> "WorkflowConfig":
        """Create default configuration"""
        return cls(supabase=SupabaseConfig.from_env(), scraping=ScrapingConfig())
