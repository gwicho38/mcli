"""
Comprehensive Data Sources Configuration for Politician Trading/Financial Disclosure Data

This file contains the definitive mapping of all publicly accessible politician
trading and financial disclosure sources across US federal, state, EU, and national levels.

Based on 2025 research of available public databases and APIs.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal
from enum import Enum

class DisclosureType(Enum):
    """Types of financial disclosures available"""
    STOCK_TRANSACTIONS = "stock_transactions"      # Individual buy/sell transactions
    FINANCIAL_INTERESTS = "financial_interests"    # General financial interests/assets
    ASSET_DECLARATIONS = "asset_declarations"      # Property, investments, etc.
    INCOME_SOURCES = "income_sources"             # Outside income sources
    CONFLICT_INTERESTS = "conflict_interests"      # Potential conflicts of interest

class AccessMethod(Enum):
    """How data can be accessed"""
    WEB_SCRAPING = "web_scraping"        # HTML scraping required
    API = "api"                          # JSON/XML API available
    PDF_PARSING = "pdf_parsing"          # PDF documents to parse
    MANUAL_DOWNLOAD = "manual_download"  # Manual download required
    DATABASE_QUERY = "database_query"   # Direct database access

@dataclass
class DataSource:
    """Configuration for a single data source"""
    name: str
    jurisdiction: str                              # e.g., "US-Federal", "US-CA", "EU", "DE"
    institution: str                               # e.g., "House", "Senate", "Bundestag"
    url: str
    disclosure_types: List[DisclosureType]
    access_method: AccessMethod
    update_frequency: str                          # e.g., "daily", "weekly", "monthly"
    threshold_amount: Optional[int] = None         # Minimum disclosure amount in USD
    data_format: str = "html"                      # html, json, xml, pdf
    api_key_required: bool = False
    rate_limits: Optional[str] = None
    historical_data_available: bool = True
    notes: Optional[str] = None
    status: Literal["active", "inactive", "testing", "planned"] = "active"

# =============================================================================
# US FEDERAL SOURCES
# =============================================================================

US_FEDERAL_SOURCES = [
    DataSource(
        name="US House Financial Disclosures",
        jurisdiction="US-Federal",
        institution="House of Representatives",
        url="https://disclosures-clerk.house.gov/FinancialDisclosure",
        disclosure_types=[DisclosureType.STOCK_TRANSACTIONS, DisclosureType.ASSET_DECLARATIONS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Real-time (within 30 days of filing)",
        threshold_amount=1000,  # $1,000+ transactions must be reported
        data_format="html",
        historical_data_available=True,
        notes="STOCK Act requires prompt disclosure of transactions >$1,000. 8-year archive available.",
        status="active"
    ),
    
    DataSource(
        name="US Senate Financial Disclosures",
        jurisdiction="US-Federal", 
        institution="Senate",
        url="https://efd.senate.gov",
        disclosure_types=[DisclosureType.STOCK_TRANSACTIONS, DisclosureType.ASSET_DECLARATIONS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Real-time (within 30 days of filing)",
        threshold_amount=1000,  # $1,000+ transactions must be reported
        data_format="html",
        historical_data_available=True,
        notes="Filing threshold $150,160 for 2025. 6-year retention after leaving office.",
        status="active"
    ),
    
    DataSource(
        name="Office of Government Ethics",
        jurisdiction="US-Federal",
        institution="Executive Branch",
        url="https://www.oge.gov/web/OGE.nsf/Officials Individual Disclosures Search Collection",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.ASSET_DECLARATIONS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Annually",
        data_format="pdf",
        historical_data_available=True,
        notes="Executive branch officials, judges, and senior staff disclosures",
        status="active"
    )
]

# =============================================================================
# US STATE SOURCES (Selected Major States)
# =============================================================================

US_STATE_SOURCES = [
    # California
    DataSource(
        name="California FPPC Form 700",
        jurisdiction="US-CA",
        institution="State Legislature",
        url="https://netfile.com/Connect2/api/public/list/ANC",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.INCOME_SOURCES],
        access_method=AccessMethod.API,
        update_frequency="Annually (April deadline)",
        threshold_amount=2000,
        data_format="json",
        api_key_required=False,
        notes="Fair Political Practices Commission Form 700. NetFile API available.",
        status="active"
    ),
    
    # New York
    DataSource(
        name="New York State Financial Disclosure",
        jurisdiction="US-NY",
        institution="State Legislature", 
        url="https://ethics.ny.gov/financial-disclosure-statements-elected-officials",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.INCOME_SOURCES],
        access_method=AccessMethod.PDF_PARSING,
        update_frequency="Annually (May 15 deadline)",
        data_format="pdf",
        notes="Commission on Ethics and Lobbying in Government",
        status="active"
    ),
    
    # Florida
    DataSource(
        name="Florida Financial Disclosure",
        jurisdiction="US-FL",
        institution="State Legislature",
        url="https://ethics.state.fl.us/FinancialDisclosure/",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.ASSET_DECLARATIONS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Annually (July 1 deadline, grace period until Sept 1)",
        data_format="html",
        notes="All elected state and local public officers required to file",
        status="active"
    ),
    
    # Texas
    DataSource(
        name="Texas Ethics Commission",
        jurisdiction="US-TX", 
        institution="State Legislature",
        url="https://www.ethics.state.tx.us/search/cf/",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Annually",
        data_format="html",
        status="active"
    ),
    
    # Michigan
    DataSource(
        name="Michigan Personal Financial Disclosure",
        jurisdiction="US-MI",
        institution="State Legislature",
        url="https://www.michigan.gov/sos/elections/disclosure/personal-financial-disclosure",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Annually",
        data_format="html", 
        notes="Candidates for Governor, Lt. Gov, SoS, AG, and Legislature required",
        status="active"
    )
]

# =============================================================================
# EU PARLIAMENT SOURCES
# =============================================================================

EU_PARLIAMENT_SOURCES = [
    DataSource(
        name="MEP Financial Interest Declarations",
        jurisdiction="EU",
        institution="European Parliament",
        url="https://www.europarl.europa.eu/meps/en/home",
        disclosure_types=[DisclosureType.INCOME_SOURCES, DisclosureType.CONFLICT_INTERESTS],
        access_method=AccessMethod.PDF_PARSING,
        update_frequency="Per legislative term (5 years)",
        threshold_amount=5000,  # €5,000+ outside income must be declared
        data_format="pdf",
        notes="Individual MEP pages have declarations. Third-party aggregation by EU Integrity Watch.",
        status="active"
    ),
    
    DataSource(
        name="EU Integrity Watch",
        jurisdiction="EU",
        institution="Third-party aggregator",
        url="https://www.integritywatch.eu/mepincomes",
        disclosure_types=[DisclosureType.INCOME_SOURCES, DisclosureType.CONFLICT_INTERESTS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Updated after MEP declarations",
        data_format="html",
        notes="Automated extraction from Parliament PDFs. Interactive database available.",
        status="active"
    )
]

# =============================================================================
# EUROPEAN NATIONAL SOURCES
# =============================================================================

EU_NATIONAL_SOURCES = [
    # Germany
    DataSource(
        name="German Bundestag Member Interests",
        jurisdiction="DE",
        institution="Bundestag",
        url="https://www.bundestag.de/abgeordnete",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.INCOME_SOURCES],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Updated as required",
        threshold_amount=None,  # 5% company ownership threshold (down from 25% in 2021)
        data_format="html",
        notes="Transparency Act 2021. Company ownership >5%, tougher bribery laws (1-10 years prison).",
        status="active"
    ),
    
    # France
    DataSource(
        name="French Parliament Financial Declarations",
        jurisdiction="FR", 
        institution="National Assembly & Senate",
        url="https://www.hatvp.fr/",  # High Authority for Transparency in Public Life
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.ASSET_DECLARATIONS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Annually",
        data_format="html",
        notes="HATVP publishes declarations. Asset declarations for MEPs since 2019. Penalties: 3 years prison + €45,000 fine.",
        status="active"
    ),
    
    # United Kingdom
    DataSource(
        name="UK Parliament Register of Members' Financial Interests", 
        jurisdiction="UK",
        institution="House of Commons",
        url="https://www.parliament.uk/mps-lords-and-offices/standards-and-financial-interests/parliamentary-commissioner-for-standards/registers-of-interests/register-of-members-financial-interests/",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.INCOME_SOURCES],
        access_method=AccessMethod.API,
        update_frequency="Updated every 2 weeks during sitting periods",
        threshold_amount=70000,  # £70,000+ shareholdings (or >15% company ownership)
        data_format="json",
        api_key_required=False,
        notes="Open Parliament Licence API available. Register updated bi-weekly.",
        status="active"
    ),
    
    DataSource(
        name="UK House of Lords Register of Interests",
        jurisdiction="UK",
        institution="House of Lords", 
        url="https://members.parliament.uk/members/lords/interests/register-of-lords-interests",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.INCOME_SOURCES],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Updated regularly",
        data_format="html",
        notes="More detailed shareholding disclosure than Commons. Searchable database.",
        status="active"
    ),
    
    # Spain
    DataSource(
        name="Spanish Parliament Transparency Portal",
        jurisdiction="ES",
        institution="Congress of Deputies & Senate",
        url="https://www.congreso.es/transparencia",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Updated as required",
        data_format="html",
        notes="Deputies and senators publish institutional agendas with interest representatives. No lobbyist register.",
        status="active"
    ),
    
    # Italy
    DataSource(
        name="Italian Parliament Financial Declarations",
        jurisdiction="IT",
        institution="Camera dei Deputati & Senato",
        url="https://www.camera.it/leg19/1",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Per legislative term",
        data_format="html",
        notes="Individual member pages contain declarations. Limited standardization.",
        status="testing"
    )
]

# =============================================================================
# THIRD-PARTY AGGREGATORS AND APIS
# =============================================================================

THIRD_PARTY_SOURCES = [
    DataSource(
        name="OpenSecrets Personal Finances",
        jurisdiction="US-Federal",
        institution="Third-party aggregator",
        url="https://www.opensecrets.org/personal-finances",
        disclosure_types=[DisclosureType.ASSET_DECLARATIONS, DisclosureType.STOCK_TRANSACTIONS],
        access_method=AccessMethod.API,
        update_frequency="Updated from federal filings",
        data_format="json",
        api_key_required=True,
        rate_limits="1000 requests/day",
        notes="Center for Responsive Politics aggregation of federal disclosures.",
        status="active"
    ),
    
    DataSource(
        name="LegiStorm Financial Disclosures",
        jurisdiction="US-Federal", 
        institution="Third-party aggregator",
        url="https://www.legistorm.com/financial_disclosure.html",
        disclosure_types=[DisclosureType.FINANCIAL_INTERESTS, DisclosureType.STOCK_TRANSACTIONS],
        access_method=AccessMethod.WEB_SCRAPING,
        update_frequency="Real-time from government sources",
        data_format="html",
        notes="Subscription service with enhanced search and analysis tools.",
        status="active"
    ),
    
    DataSource(
        name="QuiverQuant Congressional Trading",
        jurisdiction="US-Federal",
        institution="Third-party aggregator", 
        url="https://api.quiverquant.com/beta/live/congresstrading",
        disclosure_types=[DisclosureType.STOCK_TRANSACTIONS],
        access_method=AccessMethod.API,
        update_frequency="Real-time",
        data_format="json",
        api_key_required=True,
        rate_limits="Varies by subscription",
        notes="Financial data company focusing on congressional stock trades.",
        status="active"
    )
]

# =============================================================================
# CONSOLIDATED SOURCE MAPPING
# =============================================================================

ALL_DATA_SOURCES = {
    "us_federal": US_FEDERAL_SOURCES,
    "us_states": US_STATE_SOURCES, 
    "eu_parliament": EU_PARLIAMENT_SOURCES,
    "eu_national": EU_NATIONAL_SOURCES,
    "third_party": THIRD_PARTY_SOURCES
}

# Summary statistics
TOTAL_SOURCES = sum(len(sources) for sources in ALL_DATA_SOURCES.values())
ACTIVE_SOURCES = sum(
    len([s for s in sources if s.status == "active"]) 
    for sources in ALL_DATA_SOURCES.values()
)

def get_sources_by_jurisdiction(jurisdiction: str) -> List[DataSource]:
    """Get all sources for a specific jurisdiction (e.g., 'US-CA', 'DE', 'EU')"""
    all_sources = []
    for source_group in ALL_DATA_SOURCES.values():
        all_sources.extend([s for s in source_group if s.jurisdiction == jurisdiction])
    return all_sources

def get_sources_by_type(disclosure_type: DisclosureType) -> List[DataSource]:
    """Get all sources that provide a specific type of disclosure"""
    all_sources = []
    for source_group in ALL_DATA_SOURCES.values():
        all_sources.extend([s for s in source_group if disclosure_type in s.disclosure_types])
    return all_sources

def get_api_sources() -> List[DataSource]:
    """Get all sources that provide API access"""
    all_sources = []
    for source_group in ALL_DATA_SOURCES.values():
        all_sources.extend([s for s in source_group if s.access_method == AccessMethod.API])
    return all_sources

# Export for use in workflow configuration
__all__ = [
    'DataSource', 'DisclosureType', 'AccessMethod',
    'ALL_DATA_SOURCES', 'get_sources_by_jurisdiction', 
    'get_sources_by_type', 'get_api_sources',
    'TOTAL_SOURCES', 'ACTIVE_SOURCES'
]