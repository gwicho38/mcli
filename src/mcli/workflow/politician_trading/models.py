"""
Data models for politician trading information
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from decimal import Decimal


class PoliticianRole(Enum):
    """Political roles"""

    US_HOUSE_REP = "us_house_representative"
    US_SENATOR = "us_senator"
    UK_MP = "uk_member_of_parliament"
    EU_MEP = "eu_parliament_member"
    EU_COMMISSIONER = "eu_commissioner"
    EU_COUNCIL_MEMBER = "eu_council_member"
    
    # EU Member State Roles
    GERMAN_BUNDESTAG = "german_bundestag_member"
    FRENCH_DEPUTY = "french_national_assembly_deputy"
    ITALIAN_DEPUTY = "italian_chamber_deputy"
    ITALIAN_SENATOR = "italian_senate_member"
    SPANISH_DEPUTY = "spanish_congress_deputy" 
    DUTCH_MP = "dutch_tweede_kamer_member"
    
    # US State Roles
    TEXAS_STATE_OFFICIAL = "texas_state_official"
    NEW_YORK_STATE_OFFICIAL = "new_york_state_official"
    FLORIDA_STATE_OFFICIAL = "florida_state_official"
    ILLINOIS_STATE_OFFICIAL = "illinois_state_official"
    PENNSYLVANIA_STATE_OFFICIAL = "pennsylvania_state_official"
    MASSACHUSETTS_STATE_OFFICIAL = "massachusetts_state_official"
    CALIFORNIA_STATE_OFFICIAL = "california_state_official"


class TransactionType(Enum):
    """Types of financial transactions"""

    PURCHASE = "purchase"
    SALE = "sale"
    EXCHANGE = "exchange"
    OPTION_PURCHASE = "option_purchase"
    OPTION_SALE = "option_sale"


class DisclosureStatus(Enum):
    """Status of disclosure processing"""

    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"
    DUPLICATE = "duplicate"


@dataclass
class Politician:
    """Politician information"""

    id: Optional[str] = None
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    role: PoliticianRole = PoliticianRole.US_HOUSE_REP
    party: str = ""
    state_or_country: str = ""
    district: Optional[str] = None
    term_start: Optional[datetime] = None
    term_end: Optional[datetime] = None

    # External identifiers
    bioguide_id: Optional[str] = None  # US Congress bioguide ID
    eu_id: Optional[str] = None  # EU Parliament ID

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TradingDisclosure:
    """Individual trading disclosure"""

    id: Optional[str] = None
    politician_id: str = ""

    # Transaction details
    transaction_date: datetime = field(default_factory=datetime.utcnow)
    disclosure_date: datetime = field(default_factory=datetime.utcnow)
    transaction_type: TransactionType = TransactionType.PURCHASE

    # Asset information
    asset_name: str = ""
    asset_ticker: Optional[str] = None
    asset_type: str = ""  # stock, bond, option, etc.

    # Financial details
    amount_range_min: Optional[Decimal] = None
    amount_range_max: Optional[Decimal] = None
    amount_exact: Optional[Decimal] = None

    # Source information
    source_url: str = ""
    source_document_id: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    # Processing status
    status: DisclosureStatus = DisclosureStatus.PENDING
    processing_notes: str = ""

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DataPullJob:
    """Information about data pull jobs"""

    id: Optional[str] = None
    job_type: str = ""  # "us_congress", "eu_parliament", etc.
    status: str = "pending"  # pending, running, completed, failed

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    records_found: int = 0
    records_processed: int = 0
    records_new: int = 0
    records_updated: int = 0
    records_failed: int = 0

    # Error information
    error_message: Optional[str] = None
    error_details: Dict[str, Any] = field(default_factory=dict)

    # Configuration used
    config_snapshot: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DataSource:
    """Information about data sources"""

    id: Optional[str] = None
    name: str = ""
    url: str = ""
    source_type: str = ""  # "official", "aggregator", "api"
    region: str = ""  # "us", "eu"

    # Status tracking
    is_active: bool = True
    last_successful_pull: Optional[datetime] = None
    last_attempt: Optional[datetime] = None
    consecutive_failures: int = 0

    # Configuration
    request_config: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
