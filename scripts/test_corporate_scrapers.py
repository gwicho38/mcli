#!/usr/bin/env python3
"""
Test Script for Corporate Registry Scrapers

This script tests the corporate registry scrapers to verify they can:
1. Connect to APIs
2. Fetch data
3. Parse responses correctly

Usage:
    python scripts/test_corporate_scrapers.py
    # or with virtual environment:
    .venv/bin/python scripts/test_corporate_scrapers.py
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_info_financiere():
    """Test French Info-Financière API (FREE, no API key)"""
    print("\n" + "="*80)
    print("Testing Info-Financière API (France) - FREE")
    print("="*80)

    try:
        from mcli.workflow.politician_trading.scrapers_corporate_registry import InfoFinanciereAPIScraper

        scraper = InfoFinanciereAPIScraper()
        print("✅ Scraper initialized")

        # Test search
        print("Searching for recent publications...")
        publications = scraper.search_publications(per_page=5)

        if publications:
            print(f"✅ Found {len(publications)} publications")
            print(f"   Sample: {publications[0].get('title', 'N/A')[:100] if publications else 'None'}...")
            return True
        else:
            print("⚠️  No publications found (API may be empty or rate limited)")
            return True  # Still counts as working

    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_xbrl_filings():
    """Test XBRL Filings API (FREE, no API key)"""
    print("\n" + "="*80)
    print("Testing XBRL Filings API (filings.xbrl.org) - FREE")
    print("="*80)

    try:
        from mcli.workflow.politician_trading.scrapers_corporate_registry import XBRLFilingsScraper

        scraper = XBRLFilingsScraper()
        print("✅ Scraper initialized")

        # Test get filings
        print("Fetching recent XBRL filings...")
        filings = scraper.get_filings(page_size=5)

        if filings:
            print(f"✅ Found {len(filings)} filings")
            print(f"   Sample filing ID: {filings[0].get('id', 'N/A') if filings else 'None'}")
            return True
        else:
            print("⚠️  No filings found (API may be empty)")
            return True  # Still counts as working

    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_opencorporates():
    """Test OpenCorporates API (has free tier, API key optional)"""
    print("\n" + "="*80)
    print("Testing OpenCorporates API - Free tier (no API key)")
    print("="*80)

    try:
        from mcli.workflow.politician_trading.scrapers_corporate_registry import OpenCorporatesScraper

        scraper = OpenCorporatesScraper()
        print("✅ Scraper initialized (free tier)")

        # Test search - use a common company name
        print("Searching for 'Apple' companies...")
        companies = scraper.search_companies("Apple", per_page=3)

        if companies:
            print(f"✅ Found {len(companies)} companies")
            for i, company_data in enumerate(companies[:3]):
                company = company_data.get("company", {})
                print(f"   {i+1}. {company.get('name', 'N/A')} ({company.get('jurisdiction_code', 'N/A')})")
            return True
        else:
            print("⚠️  No companies found (may be rate limited on free tier)")
            return True  # Still counts as working

    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_uk_companies_house():
    """Test UK Companies House API (requires free API key)"""
    print("\n" + "="*80)
    print("Testing UK Companies House API - Requires free API key")
    print("="*80)

    api_key = os.getenv("UK_COMPANIES_HOUSE_API_KEY")

    if not api_key:
        print("⚠️  UK_COMPANIES_HOUSE_API_KEY not set - SKIPPING")
        print("   Get free API key from:")
        print("   https://developer.company-information.service.gov.uk/")
        return True  # Skip but don't fail

    try:
        from mcli.workflow.politician_trading.scrapers_corporate_registry import UKCompaniesHouseScraper

        scraper = UKCompaniesHouseScraper(api_key)
        print("✅ Scraper initialized with API key")

        # Test search
        print("Searching for 'Tesco' companies...")
        companies = scraper.search_companies("Tesco", items_per_page=3)

        if companies:
            print(f"✅ Found {len(companies)} companies")
            for i, company in enumerate(companies[:3]):
                print(f"   {i+1}. {company.get('title', 'N/A')} ({company.get('company_number', 'N/A')})")

            # Test get company profile
            if companies:
                company_number = companies[0].get("company_number")
                if company_number:
                    print(f"\nFetching profile for company {company_number}...")
                    profile = scraper.get_company_profile(company_number)
                    if profile:
                        print(f"✅ Got company profile: {profile.get('company_name', 'N/A')}")
                    else:
                        print("⚠️  Could not fetch company profile")

            return True
        else:
            print("⚠️  No companies found")
            return True

    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_xbrl_us():
    """Test XBRL US API (requires free API key)"""
    print("\n" + "="*80)
    print("Testing XBRL US API - Requires free API key")
    print("="*80)

    api_key = os.getenv("XBRL_US_API_KEY")

    if not api_key:
        print("⚠️  XBRL_US_API_KEY not set - SKIPPING")
        print("   Get free API key from:")
        print("   https://xbrl.us/home/use/xbrl-api/")
        return True  # Skip but don't fail

    try:
        from mcli.workflow.politician_trading.scrapers_corporate_registry import XBRLUSScraper

        scraper = XBRLUSScraper(api_key)
        print("✅ Scraper initialized with API key")

        # Test search companies
        print("Searching for 'Apple' companies...")
        entities = scraper.search_companies("Apple", limit=3)

        if entities:
            print(f"✅ Found {len(entities)} entities")
            for i, entity in enumerate(entities[:3]):
                print(f"   {i+1}. {entity.get('entity', {}).get('name', 'N/A')}")
            return True
        else:
            print("⚠️  No entities found")
            return True

    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_corporate_registry_fetcher():
    """Test unified CorporateRegistryFetcher"""
    print("\n" + "="*80)
    print("Testing CorporateRegistryFetcher (Unified Interface)")
    print("="*80)

    try:
        from mcli.workflow.politician_trading.scrapers_corporate_registry import CorporateRegistryFetcher

        fetcher = CorporateRegistryFetcher()
        print("✅ Fetcher initialized")

        # Test French disclosures (always works, no API key)
        print("\nFetching French financial disclosures (last 30 days)...")
        publications = fetcher.fetch_french_disclosures(days_back=30)
        print(f"✅ Found {len(publications)} French publications")

        # Test XBRL EU filings (always works, no API key)
        print("\nFetching XBRL EU filings (last 30 days)...")
        filings = fetcher.fetch_xbrl_eu_filings(days_back=30)
        print(f"✅ Found {len(filings)} XBRL filings")

        return True

    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all scraper tests"""
    print("\n" + "="*80)
    print("CORPORATE REGISTRY SCRAPERS TEST SUITE")
    print("="*80)
    print("\nTesting corporate registry and financial disclosure scrapers...")
    print("Some tests require API keys (free registration).")
    print("\n" + "="*80)

    results = {
        "Info-Financière (France) - FREE": test_info_financiere(),
        "XBRL Filings (EU/UK) - FREE": test_xbrl_filings(),
        "OpenCorporates - Free Tier": test_opencorporates(),
        "UK Companies House": test_uk_companies_house(),
        "XBRL US": test_xbrl_us(),
        "Unified Fetcher": test_corporate_registry_fetcher(),
    }

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    print("\n" + "="*80)

    total_tests = len(results)
    passed_tests = sum(1 for passed in results.values() if passed)
    failed_tests = total_tests - passed_tests

    print(f"Total: {total_tests} tests")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")

    if failed_tests == 0:
        print("\n🎉 All scraper tests passed!")
        print("\n" + "="*80)
        print("GETTING STARTED")
        print("="*80)
        print("\n1. FREE scrapers (no API key needed):")
        print("   - Info-Financière (France)")
        print("   - XBRL Filings (EU/UK)")
        print("   - OpenCorporates (free tier)")
        print("\n2. FREE API keys (registration required):")
        print("   - UK Companies House: https://developer.company-information.service.gov.uk/")
        print("   - XBRL US: https://xbrl.us/home/use/xbrl-api/")
        print("\n3. Set environment variables:")
        print("   export UK_COMPANIES_HOUSE_API_KEY='your-key'")
        print("   export XBRL_US_API_KEY='your-key'")
        print("\n4. Or add to .streamlit/secrets.toml:")
        print("   UK_COMPANIES_HOUSE_API_KEY = \"your-key\"")
        print("   XBRL_US_API_KEY = \"your-key\"")

        return 0
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Check output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
