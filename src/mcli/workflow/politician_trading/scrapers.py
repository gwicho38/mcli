"""
Web scrapers for politician trading data
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

from .models import Politician, TradingDisclosure, TransactionType, PoliticianRole
from .config import ScrapingConfig

logger = logging.getLogger(__name__)


class BaseScraper:
    """Base class for all scrapers"""

    def __init__(self, config: ScrapingConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            headers={"User-Agent": self.config.user_agent},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def fetch_page(self, url: str, **kwargs) -> Optional[str]:
        """Fetch a web page with error handling and rate limiting"""
        for attempt in range(self.config.max_retries):
            try:
                await asyncio.sleep(self.config.request_delay)

                async with self.session.get(url, **kwargs) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
                        if response.status == 429:  # Rate limited
                            await asyncio.sleep(self.config.request_delay * 2)

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.request_delay * (attempt + 1))

        return None

    def parse_amount_range(
        self, amount_text: str
    ) -> Tuple[Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
        """Parse amount text into range values"""
        if not amount_text:
            return None, None, None

        amount_text = amount_text.replace(",", "").replace("$", "").strip()

        # Look for range patterns like "$1,001 - $15,000"
        range_match = re.search(r"(\d+(?:\.\d{2})?)\s*[-–]\s*(\d+(?:\.\d{2})?)", amount_text)
        if range_match:
            min_val = Decimal(range_match.group(1))
            max_val = Decimal(range_match.group(2))
            return min_val, max_val, None

        # Look for exact amounts
        exact_match = re.search(r"(\d+(?:\.\d{2})?)", amount_text)
        if exact_match:
            exact_val = Decimal(exact_match.group(1))
            return None, None, exact_val

        # Handle standard ranges
        range_mappings = {
            "$1,001 - $15,000": (Decimal("1001"), Decimal("15000")),
            "$15,001 - $50,000": (Decimal("15001"), Decimal("50000")),
            "$50,001 - $100,000": (Decimal("50001"), Decimal("100000")),
            "$100,001 - $250,000": (Decimal("100001"), Decimal("250000")),
            "$250,001 - $500,000": (Decimal("250001"), Decimal("500000")),
            "$500,001 - $1,000,000": (Decimal("500001"), Decimal("1000000")),
            "$1,000,001 - $5,000,000": (Decimal("1000001"), Decimal("5000000")),
            "$5,000,001 - $25,000,000": (Decimal("5000001"), Decimal("25000000")),
            "$25,000,001 - $50,000,000": (Decimal("25000001"), Decimal("50000000")),
            "Over $50,000,000": (Decimal("50000001"), None),
        }

        for pattern, (min_val, max_val) in range_mappings.items():
            if pattern.lower() in amount_text.lower():
                return min_val, max_val, None

        return None, None, None


class CongressTradingScraper(BaseScraper):
    """Scraper for US Congress trading data"""

    async def scrape_house_disclosures(self) -> List[TradingDisclosure]:
        """Scrape House financial disclosures"""
        disclosures = []
        base_url = "https://disclosures-clerk.house.gov"

        try:
            # This is a simplified example - the actual implementation would need
            # to handle the complex forms and search mechanisms on the real sites
            logger.info("Starting House disclosures scrape")

            # For now, return sample data structure
            # In production, you'd navigate the disclosure search forms
            sample_disclosure = TradingDisclosure(
                politician_id="",  # Would be filled after politician lookup
                transaction_date=datetime.now() - timedelta(days=30),
                disclosure_date=datetime.now() - timedelta(days=15),
                transaction_type=TransactionType.PURCHASE,
                asset_name="Apple Inc.",
                asset_ticker="AAPL",
                asset_type="stock",
                amount_range_min=Decimal("15001"),
                amount_range_max=Decimal("50000"),
                source_url=base_url,
                raw_data={"sample": True},
            )
            disclosures.append(sample_disclosure)

        except Exception as e:
            logger.error(f"House disclosures scrape failed: {e}")

        return disclosures

    async def scrape_senate_disclosures(self) -> List[TradingDisclosure]:
        """Scrape Senate financial disclosures"""
        disclosures = []
        base_url = "https://efdsearch.senate.gov"

        try:
            logger.info("Starting Senate disclosures scrape")

            # Similar to House - this would implement the actual scraping logic
            sample_disclosure = TradingDisclosure(
                politician_id="",
                transaction_date=datetime.now() - timedelta(days=45),
                disclosure_date=datetime.now() - timedelta(days=20),
                transaction_type=TransactionType.SALE,
                asset_name="Microsoft Corporation",
                asset_ticker="MSFT",
                asset_type="stock",
                amount_range_min=Decimal("1001"),
                amount_range_max=Decimal("15000"),
                source_url=base_url,
                raw_data={"sample": True},
            )
            disclosures.append(sample_disclosure)

        except Exception as e:
            logger.error(f"Senate disclosures scrape failed: {e}")

        return disclosures


class QuiverQuantScraper(BaseScraper):
    """Scraper for QuiverQuant congress trading data as a backup source"""

    async def scrape_congress_trades(self) -> List[Dict[str, Any]]:
        """Scrape congress trading data from QuiverQuant"""
        trades = []

        try:
            # This would implement scraping from QuiverQuant's public data
            # Note: Respect their robots.txt and terms of service
            logger.info("Starting QuiverQuant scrape")

            url = "https://www.quiverquant.com/congresstrading/"
            html = await self.fetch_page(url)

            if html:
                soup = BeautifulSoup(html, "html.parser")

                # Parse the trading data table (simplified example)
                # In reality, this might require handling JavaScript rendering
                trade_rows = soup.select("table tr")

                for row in trade_rows[1:10]:  # Skip header, limit to 10 for example
                    cells = row.select("td")
                    if len(cells) >= 6:
                        trade_data = {
                            "politician_name": cells[0].get_text(strip=True),
                            "transaction_date": cells[1].get_text(strip=True),
                            "ticker": cells[2].get_text(strip=True),
                            "transaction_type": cells[3].get_text(strip=True),
                            "amount": cells[4].get_text(strip=True),
                            "source": "quiverquant",
                        }
                        trades.append(trade_data)

        except Exception as e:
            logger.error(f"QuiverQuant scrape failed: {e}")

        return trades

    def parse_quiver_trade(self, trade_data: Dict[str, Any]) -> Optional[TradingDisclosure]:
        """Parse QuiverQuant trade data into TradingDisclosure"""
        try:
            # Parse transaction type
            transaction_type_map = {
                "purchase": TransactionType.PURCHASE,
                "sale": TransactionType.SALE,
                "buy": TransactionType.PURCHASE,
                "sell": TransactionType.SALE,
            }

            transaction_type = transaction_type_map.get(
                trade_data.get("transaction_type", "").lower(), TransactionType.PURCHASE
            )

            # Parse date
            date_str = trade_data.get("transaction_date", "")
            transaction_date = (
                datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()
            )

            # Parse amount
            amount_min, amount_max, amount_exact = self.parse_amount_range(
                trade_data.get("amount", "")
            )

            disclosure = TradingDisclosure(
                politician_id="",  # Will be filled after politician matching
                transaction_date=transaction_date,
                disclosure_date=datetime.now(),  # QuiverQuant aggregation date
                transaction_type=transaction_type,
                asset_name=trade_data.get("ticker", ""),
                asset_ticker=trade_data.get("ticker", ""),
                asset_type="stock",
                amount_range_min=amount_min,
                amount_range_max=amount_max,
                amount_exact=amount_exact,
                source_url="https://www.quiverquant.com/congresstrading/",
                raw_data=trade_data,
            )

            return disclosure

        except Exception as e:
            logger.error(f"Failed to parse QuiverQuant trade: {e}")
            return None


class EUParliamentScraper(BaseScraper):
    """Scraper for EU Parliament member declarations"""

    async def scrape_mep_declarations(self) -> List[TradingDisclosure]:
        """Scrape MEP financial declarations"""
        disclosures = []

        try:
            logger.info("Starting EU Parliament declarations scrape")
            base_url = "https://www.europarl.europa.eu/meps/en/declarations"

            # This would implement actual EU Parliament scraping
            # EU disclosure formats are different from US - more about interests than trades

            sample_disclosure = TradingDisclosure(
                politician_id="",
                transaction_date=datetime.now() - timedelta(days=60),
                disclosure_date=datetime.now() - timedelta(days=30),
                transaction_type=TransactionType.PURCHASE,
                asset_name="Investment Fund Shares",
                asset_type="fund",
                amount_range_min=Decimal("10000"),
                amount_range_max=Decimal("50000"),
                source_url=base_url,
                raw_data={"sample": True, "region": "eu"},
            )
            disclosures.append(sample_disclosure)

        except Exception as e:
            logger.error(f"EU Parliament scrape failed: {e}")

        return disclosures


class PoliticianMatcher:
    """Matches scraped names to politician records"""

    def __init__(self, politicians: List[Politician]):
        self.politicians = politicians
        self._build_lookup()

    def _build_lookup(self):
        """Build lookup dictionaries for fast matching"""
        self.name_lookup = {}
        self.bioguide_lookup = {}

        for politician in self.politicians:
            # Full name variations
            full_name = politician.full_name.lower()
            self.name_lookup[full_name] = politician

            # Last, First format
            if politician.first_name and politician.last_name:
                last_first = f"{politician.last_name.lower()}, {politician.first_name.lower()}"
                self.name_lookup[last_first] = politician

                # First Last format
                first_last = f"{politician.first_name.lower()} {politician.last_name.lower()}"
                self.name_lookup[first_last] = politician

            # Bioguide ID lookup
            if politician.bioguide_id:
                self.bioguide_lookup[politician.bioguide_id] = politician

    def find_politician(self, name: str, bioguide_id: str = None) -> Optional[Politician]:
        """Find politician by name or bioguide ID"""
        if bioguide_id and bioguide_id in self.bioguide_lookup:
            return self.bioguide_lookup[bioguide_id]

        if name:
            name_clean = name.lower().strip()

            # Direct match
            if name_clean in self.name_lookup:
                return self.name_lookup[name_clean]

            # Fuzzy matching (simplified)
            for lookup_name, politician in self.name_lookup.items():
                if self._names_similar(name_clean, lookup_name):
                    return politician

        return None

    def _names_similar(self, name1: str, name2: str) -> bool:
        """Simple similarity check for names"""
        # Remove common prefixes/suffixes
        prefixes = ["rep.", "sen.", "senator", "representative", "mr.", "mrs.", "ms."]
        suffixes = ["jr.", "sr.", "ii", "iii", "iv"]

        for prefix in prefixes:
            name1 = name1.replace(prefix, "").strip()
            name2 = name2.replace(prefix, "").strip()

        for suffix in suffixes:
            name1 = name1.replace(suffix, "").strip()
            name2 = name2.replace(suffix, "").strip()

        # Check if one name contains the other
        return name1 in name2 or name2 in name1
