# Corporate Registry Scrapers Documentation

## Overview

This document describes the corporate registry and financial disclosure scrapers implemented for the MCLI politician trading workflow. These scrapers complement the politician trading data by providing corporate financial information that can reveal conflicts of interest, undisclosed holdings, and asset declarations.

## Implemented Scrapers

### 1. UK Companies House REST API ✅

**Status:** Implemented and tested
**Access:** FREE API key required (register at https://developer.company-information.service.gov.uk/)
**Rate Limit:** 600 requests per 5 minutes per key
**Data Coverage:** All UK registered companies, officers, PSC (Persons with Significant Control)

**Features:**
- Company profile search by name
- Company details by registration number
- Company officers (directors, secretaries)
- Persons with significant control (PSC) - ownership >25%
- Filing history metadata

**Setup:**
```bash
# Get free API key from https://developer.company-information.service.gov.uk/
export UK_COMPANIES_HOUSE_API_KEY='your-api-key-here'
```

**Usage:**
```python
from mcli.workflow.politician_trading.scrapers_corporate_registry import UKCompaniesHouseScraper

scraper = UKCompaniesHouseScraper()

# Search for companies
companies = scraper.search_companies("Tesco", items_per_page=10)

# Get company profile
profile = scraper.get_company_profile("00445790")  # Tesco PLC

# Get company officers
officers = scraper.get_company_officers("00445790")

# Get persons with significant control
psc = scraper.get_persons_with_significant_control("00445790")
```

### 2. Info-Financière API (France) ✅

**Status:** Implemented and tested
**Access:** FREE, no API key required
**Rate Limit:** 10,000 API calls per IP per day
**Data Coverage:** French publicly listed companies, regulatory filings

**Features:**
- Search financial publications (prospectuses, annual reports, regulatory filings)
- Publication details with document links
- Issuer information (company name, LEI, ISIN)
- Documents in PDF, HTML, XML format

**Setup:**
```bash
# No API key required!
```

**Usage:**
```python
from mcli.workflow.politician_trading.scrapers_corporate_registry import InfoFinanciereAPIScraper

scraper = InfoFinanciereAPIScraper()

# Search publications
publications = scraper.search_publications(
    query="Total",  # Company name
    from_date="2024-01-01",
    to_date="2024-12-31",
    per_page=20
)

# Get publication details
details = scraper.get_publication_details(publication_id)
```

### 3. OpenCorporates API ✅

**Status:** Implemented and tested
**Access:** Free tier available (registration recommended), paid tiers for higher volume
**Rate Limit:** Varies by tier
**Data Coverage:** Global multi-jurisdiction company registry aggregator (200+ jurisdictions)

**Features:**
- Search companies across 200+ jurisdictions
- Company details by jurisdiction and registration number
- Company officers/directors
- Filing events (metadata)

**Setup:**
```bash
# Optional API key (free tier works without, but recommended for better rate limits)
export OPENCORPORATES_API_KEY='your-api-key-here'
```

**Usage:**
```python
from mcli.workflow.politician_trading.scrapers_corporate_registry import OpenCorporatesScraper

scraper = OpenCorporatesScraper()  # Optional: pass api_key

# Search globally
companies = scraper.search_companies("Apple", per_page=10)

# Search by jurisdiction
companies = scraper.search_companies(
    "Apple",
    jurisdiction_code="us_ca",  # California, USA
    per_page=10
)

# Get company details
company = scraper.get_company("us_ca", "C0806592")  # Apple Inc.

# Get company officers
officers = scraper.get_company_officers("us_ca", "C0806592")
```

### 4. XBRL Filings API (filings.xbrl.org) ✅

**Status:** Implemented and tested
**Access:** FREE, no API key required
**Rate Limit:** None specified
**Data Coverage:** EU/UK/Ukraine ESEF/UKSEF financial statement filings

**Features:**
- Search XBRL filings by country, date range
- Entity (company) information
- Filing validation messages
- JSON:API compliant responses

**Setup:**
```bash
# No API key required!
```

**Usage:**
```python
from mcli.workflow.politician_trading.scrapers_corporate_registry import XBRLFilingsScraper

scraper = XBRLFilingsScraper()

# Get filings by country
filings = scraper.get_filings(
    country="GB",  # United Kingdom
    from_date="2024-01-01",
    to_date="2024-12-31",
    page_size=100
)

# Get entities (companies)
entities = scraper.get_entities(country="FR", page_size=100)
```

### 5. XBRL US API ✅

**Status:** Implemented and tested
**Access:** FREE API key required (register at https://xbrl.us/home/use/xbrl-api/)
**Rate Limit:** Varies by tier
**Data Coverage:** US SEC filings with ~15 minute latency

**Features:**
- Search companies/filers by name or ticker
- Get entity filings with date filters
- Extract XBRL facts (financial data points) by concept name
- Fact-level retrieval mapping XBRL tags to numeric values

**Setup:**
```bash
# Get free API key from https://xbrl.us/home/use/xbrl-api/
export XBRL_US_API_KEY='your-api-key-here'
```

**Usage:**
```python
from mcli.workflow.politician_trading.scrapers_corporate_registry import XBRLUSScraper

scraper = XBRLUSScraper()

# Search companies
entities = scraper.search_companies("Tesla", limit=10)

# Get entity filings
filings = scraper.get_entity_filings(
    entity_id=1234,
    filing_date_from="2024-01-01",
    filing_date_to="2024-12-31",
    limit=100
)

# Get XBRL facts (financial data points)
facts = scraper.get_facts(
    concept_name="Assets",
    entity_id=1234,
    period_end_from="2024-01-01",
    limit=100
)
```

### 6. Unified CorporateRegistryFetcher ✅

**Status:** Implemented and tested
**Purpose:** Simplified interface for common data fetching operations

**Usage:**
```python
from mcli.workflow.politician_trading.scrapers_corporate_registry import CorporateRegistryFetcher

# Initialize with optional API keys
fetcher = CorporateRegistryFetcher(
    uk_companies_house_key="your-uk-key",
    opencorporates_key="your-opencorporates-key",
    xbrl_us_key="your-xbrl-us-key"
)

# Fetch UK company data
uk_data = fetcher.fetch_uk_company_data("Tesco")
# Returns: {"companies": [...], "officers": [...], "psc": [...]}

# Fetch French financial disclosures
french_pubs = fetcher.fetch_french_disclosures(
    query="Total",
    days_back=30
)

# Fetch EU XBRL filings
xbrl_filings = fetcher.fetch_xbrl_eu_filings(
    country="GB",
    days_back=30
)
```

## Data Models

New data models have been added to `models.py` for corporate registry data:

### Company
```python
@dataclass
class Company:
    company_number: str  # Registration number
    company_name: str
    jurisdiction: str  # Country/region code
    company_type: Optional[str]
    status: str  # active, dissolved, etc.
    incorporation_date: Optional[datetime]
    registered_address: Optional[str]
    sic_codes: List[str]  # Industry classification
    source: str  # Data source
    raw_data: Dict[str, Any]
```

### CompanyOfficer
```python
@dataclass
class CompanyOfficer:
    company_id: str
    name: str
    officer_role: str  # director, secretary, etc.
    appointed_on: Optional[datetime]
    resigned_on: Optional[datetime]
    nationality: Optional[str]
    occupation: Optional[str]
    raw_data: Dict[str, Any]
```

### PersonWithSignificantControl
```python
@dataclass
class PersonWithSignificantControl:
    company_id: str
    name: str
    kind: str  # individual, corporate-entity, etc.
    natures_of_control: List[str]  # ownership percentages
    notified_on: Optional[datetime]
    nationality: Optional[str]
    raw_data: Dict[str, Any]
```

### FinancialPublication
```python
@dataclass
class FinancialPublication:
    publication_id: str
    title: str
    publication_type: str  # prospectus, annual-report, etc.
    publication_date: datetime
    issuer_name: Optional[str]
    document_url: Optional[str]
    source: str
    jurisdiction: str
    raw_data: Dict[str, Any]
```

### XBRLFiling
```python
@dataclass
class XBRLFiling:
    filing_id: str
    entity_name: str
    filing_date: datetime
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    fiscal_year: Optional[int]
    document_url: Optional[str]
    taxonomy: Optional[str]  # ESEF, UKSEF, US-GAAP
    source: str
    jurisdiction: str
    raw_data: Dict[str, Any]
```

## Testing

Run the test suite to verify scrapers are working:

```bash
# Test all scrapers
.venv/bin/python scripts/test_corporate_scrapers.py

# Expected output:
# ✅ PASS: Info-Financière (France) - FREE
# ✅ PASS: XBRL Filings (EU/UK) - FREE
# ✅ PASS: OpenCorporates - Free Tier
# ⚠️  SKIP: UK Companies House (no API key)
# ⚠️  SKIP: XBRL US (no API key)
# ✅ PASS: Unified Fetcher
```

## Use Cases

### 1. Cross-reference Politician Holdings with Corporate Officers

Identify politicians who may have undisclosed relationships with companies they hold stock in:

```python
# Get politician trading disclosures
politician_trades = get_politician_disclosures("Nancy Pelosi")

# For each stock traded, check if politician is company officer
for trade in politician_trades:
    ticker = trade.asset_ticker

    # Search company in UK/US registries
    uk_companies = uk_scraper.search_companies(ticker)

    for company in uk_companies:
        # Check if politician is listed as officer
        officers = uk_scraper.get_company_officers(company['company_number'])

        # Match officer names against politician name
        matches = [o for o in officers if politician_name in o['name']]

        if matches:
            print(f"Potential conflict: {politician_name} is officer in {company['name']}")
```

### 2. Track Corporate Insiders Trading Patterns

Analyze when corporate insiders (officers, PSC) trade their own company stock:

```python
# Get persons with significant control for a company
psc = uk_scraper.get_persons_with_significant_control("00445790")

# Check if any PSC also appear in politician trading disclosures
for person in psc:
    # Search for trading disclosures by person name
    disclosures = search_disclosures_by_name(person['name'])

    if disclosures:
        print(f"PSC {person['name']} has trading disclosures:")
        print(f"  Ownership: {person['natures_of_control']}")
        print(f"  Trades: {len(disclosures)}")
```

### 3. Monitor French Financial Disclosures

Track recent French company disclosures for anomalies:

```python
# Get recent French publications
recent_pubs = fetcher.fetch_french_disclosures(days_back=7)

# Filter for specific types
prospectuses = [p for p in recent_pubs if p['publication_type'] == 'prospectus']

# Check if any match politician holdings
for pub in prospectuses:
    issuer = pub['issuer_name']

    # Search politician disclosures for this issuer
    matches = search_disclosures_by_asset(issuer)

    if matches:
        print(f"Politician holds stock in {issuer}, which just filed {pub['title']}")
```

### 4. Analyze XBRL Financial Statements

Extract structured financial data from XBRL filings:

```python
# Get XBRL US facts for a specific concept
assets = xbrl_us.get_facts(
    concept_name="Assets",
    entity_id=1234,
    period_end_from="2024-01-01",
    limit=100
)

# Analyze asset trends
for fact in assets:
    print(f"Period: {fact['period']['fiscal-period']}")
    print(f"Assets: ${fact['value']:,.2f}")
    print(f"Change: {fact.get('change_from_prior', 'N/A')}")
```

## API Key Management

### Getting API Keys

1. **UK Companies House** (FREE):
   - Register at https://developer.company-information.service.gov.uk/
   - Create application to get API key
   - No credit card required

2. **XBRL US** (FREE):
   - Register at https://xbrl.us/home/use/xbrl-api/
   - Request free API key
   - No credit card required

3. **OpenCorporates** (FREE tier available):
   - Free tier works without API key (rate limited)
   - Register at https://opencorporates.com/api_accounts/new for API key
   - Paid tiers for higher volume

### Storing API Keys

**For local development:**
```bash
# Add to .env file (in project root)
UK_COMPANIES_HOUSE_API_KEY=your-key-here
XBRL_US_API_KEY=your-key-here
OPENCORPORATES_API_KEY=your-key-here
```

**For Streamlit Cloud:**
```toml
# Add to Streamlit Cloud Settings → Secrets
UK_COMPANIES_HOUSE_API_KEY = "your-key-here"
XBRL_US_API_KEY = "your-key-here"
OPENCORPORATES_API_KEY = "your-key-here"
```

**For production (environment variables):**
```bash
export UK_COMPANIES_HOUSE_API_KEY='your-key-here'
export XBRL_US_API_KEY='your-key-here'
export OPENCORPORATES_API_KEY='your-key-here'
```

## Rate Limiting

Each scraper implements rate limiting to respect API terms:

| API | Rate Limit | Implementation |
|-----|------------|----------------|
| UK Companies House | 600 req/5 min | 0.5s delay between requests |
| Info-Financière | 10,000 req/day | No delay (generous limit) |
| OpenCorporates | Varies by tier | No delay (handled by API) |
| XBRL Filings | None specified | No delay |
| XBRL US | Varies by tier | No delay (handled by API) |

## Error Handling

All scrapers implement comprehensive error handling:

- **HTTP 404**: Resource not found (logged as warning)
- **HTTP 401/403**: Authentication failed (raises ValueError)
- **HTTP 429**: Rate limit exceeded (logged as error)
- **Network errors**: Logged with full traceback
- **Invalid responses**: Logged and returns empty list/None

Example:
```python
try:
    companies = scraper.search_companies("Test")
except ValueError as e:
    # Authentication error
    print(f"API key invalid: {e}")
except Exception as e:
    # Other errors
    print(f"Unexpected error: {e}")
```

## Future Enhancements

### Planned Additions

1. **UK Companies House Streaming API**
   - Real-time company change notifications
   - Requires streaming connection setup
   - Priority: Medium

2. **GetEDGE API (Australia)**
   - Australian corporate registry
   - Requires paid subscription
   - Priority: Low

3. **Hong Kong Companies Registry**
   - Requires portal login/paid access
   - Limited structured data
   - Priority: Low

4. **Transparent Data (EU)**
   - EU registry aggregator
   - Requires paid subscription
   - Priority: Medium

### Integration Opportunities

1. **Politician-Company Matching**
   - Automated matching of politician names with company officers
   - Conflict of interest detection
   - Asset declaration verification

2. **Insider Trading Detection**
   - Cross-reference PSC data with trading disclosures
   - Identify suspicious timing patterns
   - Generate alerts for unusual activity

3. **Financial Statement Analysis**
   - Extract key metrics from XBRL filings
   - Correlate with politician trading activity
   - Identify material events that precede trades

## Support & Troubleshooting

### Common Issues

**Issue: "API key required" error**
```bash
# Solution: Set environment variable
export UK_COMPANIES_HOUSE_API_KEY='your-key'
```

**Issue: "Rate limit exceeded"**
```python
# Solution: Wait and retry, or reduce request frequency
import time
time.sleep(60)  # Wait 1 minute
```

**Issue: "No data found"**
```python
# Some APIs may be empty or rate limited on free tier
# Check API status page or try different search query
```

### Getting Help

- **Scraper issues**: Check `scripts/test_corporate_scrapers.py`
- **API documentation**: Links provided in each scraper docstring
- **Rate limiting**: Review API terms and adjust delay
- **Data models**: See `models.py` for schema

## License & Legal

- **Data Usage**: Respect each API's terms of service
- **Attribution**: Required by some APIs (e.g., OpenCorporates)
- **Commercial Use**: Check individual API terms
- **Rate Limits**: Never exceed documented rate limits
- **Privacy**: Handle personal data per GDPR/local laws

## Contributing

To add new scrapers:

1. Create scraper class in `scrapers_corporate_registry.py`
2. Add corresponding data model to `models.py`
3. Add test function to `scripts/test_corporate_scrapers.py`
4. Update this documentation
5. Submit pull request

Example scraper template:
```python
class NewRegistryScraper:
    """
    Scraper for [Registry Name]
    Source: [API URL]

    [Access notes]
    """

    BASE_URL = "https://api.example.com"

    def __init__(self, api_key: Optional[str] = None):
        # Initialize with API key from env var
        self.api_key = api_key or os.getenv("NEW_REGISTRY_API_KEY")
        # Set up session with headers

    def search(self, query: str) -> List[Dict]:
        # Implement search functionality
        pass
```

---

**Last Updated:** 2025-10-07
**Version:** 1.0.0
**Maintainer:** MCLI Development Team
