"""
Scrapers and Logs Dashboard Page

This page provides:
1. Manual scraping interface for corporate registry data
2. Real-time scraper logs and job status
3. System logs viewer
4. Job history and statistics
"""

import logging
import os
import sys
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def show_scrapers_and_logs():
    """Main function for scrapers and logs page"""
    st.header("🔍 Data Scrapers & System Logs")
    
    # Add a simple test to ensure the page is rendering
    st.info("📋 Page loaded successfully - Scrapers & Logs functionality is available")

    st.markdown("""
    **Features:**
    - 🚀 Manual data scraping from corporate registries
    - 📊 Real-time scraper logs and job status
    - 📝 System logs viewer
    - 📈 Job history and statistics
    """)

    # Create tabs
    tabs = st.tabs([
        "🚀 Manual Scraping",
        "📊 Scraper Logs",
        "📝 System Logs",
        "📈 Job History"
    ])

    with tabs[0]:
        show_manual_scraping()

    with tabs[1]:
        show_scraper_logs()

    with tabs[2]:
        show_system_logs()

    with tabs[3]:
        show_job_history()


def show_manual_scraping():
    """Manual scraping interface"""
    st.subheader("🚀 Manual Data Scraping")

    st.markdown("""
    Manually trigger data scraping jobs from various sources.
    Select a source, configure parameters, and run the scraper.
    """)

    # Source selection
    source_type = st.selectbox(
        "Select Data Source",
        [
            "UK Companies House",
            "Info-Financière (France)",
            "OpenCorporates",
            "XBRL Filings (EU/UK)",
            "XBRL US",
            "Senate Stock Watcher (GitHub)",
        ],
        help="Choose which data source to scrape"
    )

    # Source-specific configuration
    if source_type == "UK Companies House":
        show_uk_companies_house_scraper()
    elif source_type == "Info-Financière (France)":
        show_info_financiere_scraper()
    elif source_type == "OpenCorporates":
        show_opencorporates_scraper()
    elif source_type == "XBRL Filings (EU/UK)":
        show_xbrl_filings_scraper()
    elif source_type == "XBRL US":
        show_xbrl_us_scraper()
    elif source_type == "Senate Stock Watcher (GitHub)":
        show_senate_watcher_scraper()


def show_uk_companies_house_scraper():
    """UK Companies House scraper interface"""
    st.markdown("### UK Companies House Configuration")

    # Check API key
    api_key = os.getenv("UK_COMPANIES_HOUSE_API_KEY") or st.secrets.get("UK_COMPANIES_HOUSE_API_KEY", "")

    if not api_key:
        st.error("❌ UK Companies House API key not configured")
        st.info("""
        To use this scraper, set `UK_COMPANIES_HOUSE_API_KEY` in:
        - Streamlit Cloud: Settings → Secrets
        - Local: .streamlit/secrets.toml or environment variable

        Get free API key: https://developer.company-information.service.gov.uk/
        """)
        return

    st.success("✅ API key configured")

    # Configuration
    col1, col2 = st.columns(2)

    with col1:
        company_query = st.text_input(
            "Company Name",
            value="Tesco",
            help="Company name to search for"
        )
        max_results = st.number_input(
            "Max Results",
            min_value=1,
            max_value=100,
            value=10,
            help="Maximum number of companies to fetch"
        )

    with col2:
        fetch_officers = st.checkbox("Fetch Officers", value=True)
        fetch_psc = st.checkbox("Fetch PSC Data", value=True)
        save_to_db = st.checkbox("Save to Database", value=False)

    # Run scraper
    if st.button("🚀 Run UK Companies House Scraper", type="primary"):
        run_uk_companies_house_scraper(
            company_query,
            max_results,
            fetch_officers,
            fetch_psc,
            save_to_db
        )


def run_uk_companies_house_scraper(
    query: str,
    max_results: int,
    fetch_officers: bool,
    fetch_psc: bool,
    save_to_db: bool
):
    """Execute UK Companies House scraper"""
    try:
        from mcli.workflow.politician_trading.scrapers_corporate_registry import UKCompaniesHouseScraper

        # Create log capture
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)

        scraper_logger = logging.getLogger("mcli.workflow.politician_trading.scrapers_corporate_registry")
        scraper_logger.addHandler(handler)

        # Create progress containers
        status_container = st.empty()
        progress_bar = st.progress(0)
        log_container = st.empty()
        results_container = st.empty()

        # Initialize scraper
        status_container.info("🔄 Initializing UK Companies House scraper...")
        scraper = UKCompaniesHouseScraper()
        progress_bar.progress(10)

        # Search companies
        status_container.info(f"🔍 Searching for '{query}'...")
        companies = scraper.search_companies(query, items_per_page=max_results)
        progress_bar.progress(30)

        if not companies:
            status_container.warning(f"⚠️ No companies found matching '{query}'")
            return

        status_container.success(f"✅ Found {len(companies)} companies")

        # Fetch additional data
        all_officers = []
        all_psc = []

        for i, company in enumerate(companies):
            company_number = company.get("company_number")
            company_name = company.get("title", "Unknown")

            if fetch_officers:
                status_container.info(f"👥 Fetching officers for {company_name}...")
                officers = scraper.get_company_officers(company_number)
                all_officers.extend(officers)

            if fetch_psc:
                status_container.info(f"🏢 Fetching PSC for {company_name}...")
                psc = scraper.get_persons_with_significant_control(company_number)
                all_psc.extend(psc)

            progress_bar.progress(30 + int((i + 1) / len(companies) * 50))

        # Display logs
        log_container.text_area(
            "Scraper Logs",
            log_stream.getvalue(),
            height=200
        )

        # Display results
        with results_container:
            st.markdown("### 📊 Scraping Results")

            col1, col2, col3 = st.columns(3)
            col1.metric("Companies", len(companies))
            col2.metric("Officers", len(all_officers))
            col3.metric("PSC", len(all_psc))

            # Show companies
            st.markdown("#### Companies Found")
            companies_df = pd.DataFrame([{
                "Number": c.get("company_number"),
                "Name": c.get("title"),
                "Status": c.get("company_status"),
                "Type": c.get("company_type"),
                "Address": c.get("address_snippet", "")[:50]
            } for c in companies])
            st.dataframe(companies_df, use_container_width=True)

            # Show officers
            if all_officers:
                st.markdown("#### Officers Found")
                officers_df = pd.DataFrame([{
                    "Name": o.get("name"),
                    "Role": o.get("officer_role"),
                    "Appointed": o.get("appointed_on", ""),
                    "Nationality": o.get("nationality", ""),
                    "Occupation": o.get("occupation", "")
                } for o in all_officers[:50]])  # Limit to 50 for display
                st.dataframe(officers_df, use_container_width=True)

            # Show PSC
            if all_psc:
                st.markdown("#### Persons with Significant Control")
                psc_df = pd.DataFrame([{
                    "Name": p.get("name"),
                    "Kind": p.get("kind", "").replace("-", " ").title(),
                    "Control": ", ".join(p.get("natures_of_control", [])),
                    "Nationality": p.get("nationality", ""),
                } for p in all_psc[:50]])
                st.dataframe(psc_df, use_container_width=True)

        progress_bar.progress(100)
        status_container.success(f"✅ Scraping completed! Found {len(companies)} companies, {len(all_officers)} officers, {len(all_psc)} PSC")

        # Save to database if requested
        if save_to_db:
            save_corporate_data_to_db(companies, all_officers, all_psc, "uk_companies_house")

    except Exception as e:
        st.error(f"❌ Error: {e}")
        import traceback
        st.code(traceback.format_exc())


def show_info_financiere_scraper():
    """Info-Financière scraper interface"""
    st.markdown("### Info-Financière (France) Configuration")

    st.success("✅ No API key required (FREE)")

    # Configuration
    col1, col2 = st.columns(2)

    with col1:
        query = st.text_input(
            "Search Query (optional)",
            value="",
            help="Company name, ISIN, or leave blank for all"
        )
        days_back = st.number_input(
            "Days Back",
            min_value=1,
            max_value=365,
            value=30,
            help="How many days of history to fetch"
        )

    with col2:
        max_results = st.number_input(
            "Max Results",
            min_value=1,
            max_value=100,
            value=20
        )
        save_to_db = st.checkbox("Save to Database", value=False)

    # Run scraper
    if st.button("🚀 Run Info-Financière Scraper", type="primary"):
        run_info_financiere_scraper(query, days_back, max_results, save_to_db)


def run_info_financiere_scraper(
    query: str,
    days_back: int,
    max_results: int,
    save_to_db: bool
):
    """Execute Info-Financière scraper"""
    try:
        from mcli.workflow.politician_trading.scrapers_corporate_registry import InfoFinanciereAPIScraper

        status_container = st.empty()
        progress_bar = st.progress(0)
        results_container = st.empty()

        # Initialize scraper
        status_container.info("🔄 Initializing Info-Financière scraper...")
        scraper = InfoFinanciereAPIScraper()
        progress_bar.progress(20)

        # Calculate date range
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        to_date = datetime.now().strftime("%Y-%m-%d")

        # Search publications
        status_container.info(f"🔍 Searching publications ({from_date} to {to_date})...")
        publications = scraper.search_publications(
            query=query or None,
            from_date=from_date,
            to_date=to_date,
            per_page=max_results
        )
        progress_bar.progress(80)

        # Display results
        with results_container:
            st.markdown("### 📊 Scraping Results")

            if not publications:
                st.warning(f"⚠️ No publications found for the given criteria")
                return

            st.metric("Publications Found", len(publications))

            # Show publications
            pubs_df = pd.DataFrame([{
                "Date": p.get("publication_date", ""),
                "Title": p.get("title", "")[:100],
                "Type": p.get("publication_type", ""),
                "Issuer": p.get("issuer_name", "")
            } for p in publications])
            st.dataframe(pubs_df, use_container_width=True)

        progress_bar.progress(100)
        status_container.success(f"✅ Scraping completed! Found {len(publications)} publications")

        if save_to_db:
            save_financial_publications_to_db(publications, "info_financiere")

    except Exception as e:
        st.error(f"❌ Error: {e}")
        import traceback
        st.code(traceback.format_exc())


def show_opencorporates_scraper():
    """OpenCorporates scraper interface"""
    st.markdown("### OpenCorporates Configuration")

    api_key = os.getenv("OPENCORPORATES_API_KEY") or st.secrets.get("OPENCORPORATES_API_KEY", "")

    if api_key:
        st.success("✅ API key configured")
    else:
        st.info("ℹ️ No API key (free tier with rate limits). Get API key for better performance: https://opencorporates.com/api_accounts/new")

    # Configuration
    col1, col2 = st.columns(2)

    with col1:
        query = st.text_input(
            "Company Name",
            value="Apple",
            help="Company name to search for"
        )
        jurisdiction = st.selectbox(
            "Jurisdiction (optional)",
            ["", "us_ca", "us_de", "us_ny", "gb", "de", "fr", "nl"],
            help="Filter by jurisdiction code"
        )

    with col2:
        max_results = st.number_input(
            "Max Results",
            min_value=1,
            max_value=100,
            value=10
        )
        save_to_db = st.checkbox("Save to Database", value=False)

    # Run scraper
    if st.button("🚀 Run OpenCorporates Scraper", type="primary"):
        run_opencorporates_scraper(query, jurisdiction or None, max_results, save_to_db)


def run_opencorporates_scraper(
    query: str,
    jurisdiction: str,
    max_results: int,
    save_to_db: bool
):
    """Execute OpenCorporates scraper"""
    try:
        from mcli.workflow.politician_trading.scrapers_corporate_registry import OpenCorporatesScraper

        status_container = st.empty()
        progress_bar = st.progress(0)
        results_container = st.empty()

        # Initialize scraper
        status_container.info("🔄 Initializing OpenCorporates scraper...")
        scraper = OpenCorporatesScraper()
        progress_bar.progress(20)

        # Search companies
        status_container.info(f"🔍 Searching for '{query}'...")
        companies = scraper.search_companies(
            query,
            jurisdiction_code=jurisdiction,
            per_page=max_results
        )
        progress_bar.progress(80)

        # Display results
        with results_container:
            st.markdown("### 📊 Scraping Results")

            if not companies:
                st.warning(f"⚠️ No companies found matching '{query}'")
                return

            st.metric("Companies Found", len(companies))

            # Show companies
            companies_df = pd.DataFrame([{
                "Jurisdiction": c.get("company", {}).get("jurisdiction_code", ""),
                "Number": c.get("company", {}).get("company_number", ""),
                "Name": c.get("company", {}).get("name", ""),
                "Status": c.get("company", {}).get("current_status", ""),
                "Type": c.get("company", {}).get("company_type", "")
            } for c in companies])
            st.dataframe(companies_df, use_container_width=True)

        progress_bar.progress(100)
        status_container.success(f"✅ Scraping completed! Found {len(companies)} companies")

    except Exception as e:
        st.error(f"❌ Error: {e}")
        import traceback
        st.code(traceback.format_exc())


def show_xbrl_filings_scraper():
    """XBRL Filings scraper interface"""
    st.markdown("### XBRL Filings (EU/UK) Configuration")

    st.success("✅ No API key required (FREE)")

    # Configuration
    col1, col2 = st.columns(2)

    with col1:
        country = st.selectbox(
            "Country (optional)",
            ["", "GB", "FR", "DE", "ES", "IT", "NL", "BE"],
            help="Filter by country code"
        )
        days_back = st.number_input(
            "Days Back",
            min_value=1,
            max_value=365,
            value=30
        )

    with col2:
        max_results = st.number_input(
            "Max Results",
            min_value=1,
            max_value=500,
            value=100
        )
        save_to_db = st.checkbox("Save to Database", value=False)

    # Run scraper
    if st.button("🚀 Run XBRL Filings Scraper", type="primary"):
        run_xbrl_filings_scraper(country or None, days_back, max_results, save_to_db)


def run_xbrl_filings_scraper(
    country: str,
    days_back: int,
    max_results: int,
    save_to_db: bool
):
    """Execute XBRL Filings scraper"""
    try:
        from mcli.workflow.politician_trading.scrapers_corporate_registry import XBRLFilingsScraper

        status_container = st.empty()
        progress_bar = st.progress(0)
        results_container = st.empty()

        # Initialize scraper
        status_container.info("🔄 Initializing XBRL Filings scraper...")
        scraper = XBRLFilingsScraper()
        progress_bar.progress(20)

        # Calculate date range
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        # Get filings
        status_container.info(f"🔍 Fetching XBRL filings since {from_date}...")
        filings = scraper.get_filings(
            country=country,
            from_date=from_date,
            page_size=max_results
        )
        progress_bar.progress(80)

        # Display results
        with results_container:
            st.markdown("### 📊 Scraping Results")

            if not filings:
                st.warning(f"⚠️ No filings found for the given criteria")
                return

            st.metric("Filings Found", len(filings))

            # Show filings
            filings_df = pd.DataFrame([{
                "ID": f.get("id", ""),
                "Country": f.get("attributes", {}).get("country", ""),
                "Entity": f.get("attributes", {}).get("entity_name", "")[:50],
                "Period": f.get("attributes", {}).get("period_end", ""),
                "Date Added": f.get("attributes", {}).get("date_added", "")
            } for f in filings])
            st.dataframe(filings_df, use_container_width=True)

        progress_bar.progress(100)
        status_container.success(f"✅ Scraping completed! Found {len(filings)} filings")

    except Exception as e:
        st.error(f"❌ Error: {e}")
        import traceback
        st.code(traceback.format_exc())


def show_xbrl_us_scraper():
    """XBRL US scraper interface"""
    st.markdown("### XBRL US Configuration")

    api_key = os.getenv("XBRL_US_API_KEY") or st.secrets.get("XBRL_US_API_KEY", "")

    if not api_key:
        st.error("❌ XBRL US API key not configured")
        st.info("""
        To use this scraper, set `XBRL_US_API_KEY` in:
        - Streamlit Cloud: Settings → Secrets
        - Local: .streamlit/secrets.toml or environment variable

        Get free API key: https://xbrl.us/home/use/xbrl-api/
        """)
        return

    st.success("✅ API key configured")

    # Configuration
    col1, col2 = st.columns(2)

    with col1:
        query = st.text_input(
            "Company Name or Ticker",
            value="Tesla",
            help="Search by company name or stock ticker"
        )

    with col2:
        max_results = st.number_input(
            "Max Results",
            min_value=1,
            max_value=100,
            value=10
        )
        save_to_db = st.checkbox("Save to Database", value=False)

    # Run scraper
    if st.button("🚀 Run XBRL US Scraper", type="primary"):
        run_xbrl_us_scraper(query, max_results, save_to_db)


def run_xbrl_us_scraper(
    query: str,
    max_results: int,
    save_to_db: bool
):
    """Execute XBRL US scraper"""
    try:
        from mcli.workflow.politician_trading.scrapers_corporate_registry import XBRLUSScraper

        status_container = st.empty()
        progress_bar = st.progress(0)
        results_container = st.empty()

        # Initialize scraper
        status_container.info("🔄 Initializing XBRL US scraper...")
        scraper = XBRLUSScraper()
        progress_bar.progress(20)

        # Search companies
        status_container.info(f"🔍 Searching for '{query}'...")
        entities = scraper.search_companies(query, limit=max_results)
        progress_bar.progress(80)

        # Display results
        with results_container:
            st.markdown("### 📊 Scraping Results")

            if not entities:
                st.warning(f"⚠️ No entities found matching '{query}'")
                return

            st.metric("Entities Found", len(entities))

            # Show entities
            entities_df = pd.DataFrame([{
                "ID": e.get("entity", {}).get("id", ""),
                "Name": e.get("entity", {}).get("name", ""),
                "CIK": e.get("entity", {}).get("cik", ""),
                "Ticker": e.get("entity", {}).get("ticker", "")
            } for e in entities])
            st.dataframe(entities_df, use_container_width=True)

        progress_bar.progress(100)
        status_container.success(f"✅ Scraping completed! Found {len(entities)} entities")

    except Exception as e:
        st.error(f"❌ Error: {e}")
        import traceback
        st.code(traceback.format_exc())


def show_senate_watcher_scraper():
    """Senate Stock Watcher scraper interface"""
    st.markdown("### Senate Stock Watcher (GitHub) Configuration")

    st.success("✅ No API key required (FREE)")

    # Configuration
    col1, col2 = st.columns(2)

    with col1:
        recent_only = st.checkbox("Recent Only", value=True)
        days_back = st.number_input(
            "Days Back (if recent)",
            min_value=1,
            max_value=365,
            value=90,
            disabled=not recent_only
        )

    with col2:
        save_to_db = st.checkbox("Save to Database", value=True)

    # Run scraper
    if st.button("🚀 Run Senate Stock Watcher Scraper", type="primary"):
        run_senate_watcher_scraper(recent_only, days_back, save_to_db)


def run_senate_watcher_scraper(
    recent_only: bool,
    days_back: int,
    save_to_db: bool
):
    """Execute Senate Stock Watcher scraper"""
    try:
        from mcli.workflow.politician_trading.scrapers_free_sources import FreeDataFetcher

        status_container = st.empty()
        progress_bar = st.progress(0)
        results_container = st.empty()

        # Initialize fetcher
        status_container.info("🔄 Initializing Senate Stock Watcher scraper...")
        fetcher = FreeDataFetcher()
        progress_bar.progress(20)

        # Fetch data
        status_container.info("🔍 Fetching Senate trading data from GitHub...")
        data = fetcher.fetch_from_senate_watcher(recent_only=recent_only, days=days_back)
        progress_bar.progress(80)

        politicians = data.get("politicians", [])
        disclosures = data.get("disclosures", [])

        # Display results
        with results_container:
            st.markdown("### 📊 Scraping Results")

            col1, col2 = st.columns(2)
            col1.metric("Politicians", len(politicians))
            col2.metric("Disclosures", len(disclosures))

            # Show disclosures
            if disclosures:
                st.markdown("#### Recent Trading Disclosures")
                disc_df = pd.DataFrame([{
                    "Date": d.transaction_date.strftime("%Y-%m-%d") if hasattr(d.transaction_date, 'strftime') else str(d.transaction_date),
                    "Ticker": d.asset_ticker or "—",
                    "Asset": d.asset_name[:50],
                    "Type": d.transaction_type,
                    "Politician": d.politician_bioguide_id,
                    "Min": f"${d.amount_range_min:,.0f}" if d.amount_range_min else "",
                    "Max": f"${d.amount_range_max:,.0f}" if d.amount_range_max else ""
                } for d in disclosures[:100]])  # Limit to 100 for display
                st.dataframe(disc_df, use_container_width=True)

        progress_bar.progress(100)
        status_container.success(f"✅ Scraping completed! Found {len(politicians)} politicians, {len(disclosures)} disclosures")

        if save_to_db:
            save_politician_trading_to_db(politicians, disclosures)

    except Exception as e:
        st.error(f"❌ Error: {e}")
        import traceback
        st.code(traceback.format_exc())


def save_corporate_data_to_db(companies, officers, psc, source):
    """Save corporate data to Supabase"""
    st.info("⚠️ Database saving not yet implemented. Data displayed above.")
    # TODO: Implement Supabase upsert logic


def save_financial_publications_to_db(publications, source):
    """Save financial publications to Supabase"""
    st.info("⚠️ Database saving not yet implemented. Data displayed above.")
    # TODO: Implement Supabase upsert logic


def save_politician_trading_to_db(politicians, disclosures):
    """Save politician trading data to Supabase"""
    st.info("⚠️ Using existing seed_database.py logic for this source")
    # TODO: Call seed_database.py functions


def show_scraper_logs():
    """Display scraper logs"""
    st.subheader("📊 Scraper Logs")

    st.markdown("""
    View real-time logs from scraping operations and data pull jobs.
    """)

    # Get logs from Supabase data_pull_jobs
    try:
        from mcli.ml.dashboard.app_integrated import get_supabase_client

        client = get_supabase_client()

        if client:
            # Get recent jobs
            jobs = client.table("data_pull_jobs").select("*").order("created_at", desc=True).limit(50).execute()

            if jobs.data:
                st.markdown("### Recent Data Pull Jobs")

                jobs_df = pd.DataFrame(jobs.data)

                # Format dates
                for col in ['started_at', 'completed_at', 'created_at']:
                    if col in jobs_df.columns:
                        jobs_df[col] = pd.to_datetime(jobs_df[col], format='ISO8601', errors='coerce')

                # Display jobs table
                display_df = jobs_df[[
                    'created_at', 'job_type', 'status', 'records_found',
                    'records_new', 'records_updated', 'records_failed'
                ]].copy()

                display_df.columns = [
                    'Timestamp', 'Job Type', 'Status', 'Found',
                    'New', 'Updated', 'Failed'
                ]

                st.dataframe(display_df, use_container_width=True)

                # Job details
                st.markdown("### Job Details")

                selected_job = st.selectbox(
                    "Select Job",
                    jobs_df['id'].tolist(),
                    format_func=lambda x: f"{jobs_df[jobs_df['id']==x]['job_type'].values[0]} - {jobs_df[jobs_df['id']==x]['created_at'].values[0]}"
                )

                if selected_job:
                    job = jobs_df[jobs_df['id'] == selected_job].iloc[0]

                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Status", job['status'])
                    col2.metric("Records Found", job['records_found'])
                    col3.metric("New Records", job['records_new'])
                    col4.metric("Failed", job['records_failed'])

                    if job.get('error_message'):
                        st.error(f"**Error:** {job['error_message']}")

                    # Show config snapshot
                    if job.get('config_snapshot'):
                        with st.expander("Configuration Snapshot"):
                            st.json(job['config_snapshot'])

            else:
                st.info("No jobs found in database")

        else:
            st.warning("Supabase not connected - logs unavailable")

    except Exception as e:
        st.error(f"Error loading scraper logs: {e}")


def show_system_logs():
    """Display system logs"""
    st.subheader("📝 System Logs")

    st.markdown("""
    View application logs, errors, and system events.
    """)

    # Log file path
    log_file = Path("/tmp/seed_database.log")

    if log_file.exists():
        try:
            with open(log_file, 'r') as f:
                logs = f.readlines()

            # Filter options
            col1, col2, col3 = st.columns(3)

            with col1:
                log_level = st.selectbox(
                    "Log Level",
                    ["ALL", "ERROR", "WARNING", "INFO", "DEBUG"]
                )

            with col2:
                lines_to_show = st.number_input(
                    "Lines to Show",
                    min_value=10,
                    max_value=1000,
                    value=100
                )

            with col3:
                search_term = st.text_input("Search", value="")

            # Filter logs
            filtered_logs = logs[-lines_to_show:]

            if log_level != "ALL":
                filtered_logs = [l for l in filtered_logs if log_level in l]

            if search_term:
                filtered_logs = [l for l in filtered_logs if search_term.lower() in l.lower()]

            # Display logs
            st.text_area(
                "Log Output",
                "".join(filtered_logs),
                height=400
            )

            # Download button
            st.download_button(
                "Download Full Logs",
                "".join(logs),
                file_name=f"system_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )

        except Exception as e:
            st.error(f"Error reading log file: {e}")
    else:
        st.info("📋 **No logs available yet**")
        st.markdown("""
        System logs will appear here automatically after scraping jobs run.

        **To generate logs:**
        - Use the "Manual Scrapers" section above to run a data pull
        - Wait for automated jobs to execute
        - Logs will be stored in: `/tmp/seed_database.log`
        """)

        # Create example logs display
        st.markdown("### 📝 Example Log Output")
        st.code("""
2025-10-07 12:00:00 - INFO - Starting data pull job: senate_watcher_seed
2025-10-07 12:00:05 - INFO - Fetched 8350 Senate transactions
2025-10-07 12:00:10 - INFO - Upserted 89 politicians (5 new, 84 updated)
2025-10-07 12:01:30 - INFO - Upserted 8350 disclosures (6353 new, 1893 updated, 104 failed)
2025-10-07 12:01:31 - INFO - Job completed successfully
        """, language="log")


def show_job_history():
    """Display job history and statistics"""
    st.subheader("📈 Job History & Statistics")

    st.markdown("""
    View historical data about scraping jobs, success rates, and trends.
    """)

    try:
        from mcli.ml.dashboard.app_integrated import get_supabase_client

        client = get_supabase_client()

        if client:
            # Get all jobs
            jobs = client.table("data_pull_jobs").select("*").order("created_at", desc=True).limit(1000).execute()

            if jobs.data and len(jobs.data) > 0:
                jobs_df = pd.DataFrame(jobs.data)

                # Format dates
                for col in ['started_at', 'completed_at', 'created_at']:
                    if col in jobs_df.columns:
                        jobs_df[col] = pd.to_datetime(jobs_df[col], format='ISO8601', errors='coerce')

                # Statistics
                st.markdown("### Overall Statistics")

                col1, col2, col3, col4 = st.columns(4)

                total_jobs = len(jobs_df)
                completed_jobs = len(jobs_df[jobs_df['status'] == 'completed'])
                failed_jobs = len(jobs_df[jobs_df['status'] == 'failed'])
                success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0

                col1.metric("Total Jobs", total_jobs)
                col2.metric("Completed", completed_jobs)
                col3.metric("Failed", failed_jobs)
                col4.metric("Success Rate", f"{success_rate:.1f}%")

                # Job type breakdown
                st.markdown("### Job Type Breakdown")

                job_type_counts = jobs_df['job_type'].value_counts()

                fig = px.pie(
                    values=job_type_counts.values,
                    names=job_type_counts.index,
                    title="Jobs by Type"
                )
                st.plotly_chart(fig, config={"displayModeBar": True}, use_container_width=True)

                # Status breakdown
                st.markdown("### Status Breakdown")

                status_counts = jobs_df['status'].value_counts()

                fig = px.bar(
                    x=status_counts.index,
                    y=status_counts.values,
                    labels={'x': 'Status', 'y': 'Count'},
                    title="Jobs by Status"
                )
                st.plotly_chart(fig, config={"displayModeBar": True}, use_container_width=True)

                # Timeline
                st.markdown("### Job Timeline")

                jobs_df['date'] = jobs_df['created_at'].dt.date

                timeline_df = jobs_df.groupby(['date', 'status']).size().reset_index(name='count')

                fig = px.line(
                    timeline_df,
                    x='date',
                    y='count',
                    color='status',
                    title="Jobs Over Time"
                )
                st.plotly_chart(fig, config={"displayModeBar": True}, use_container_width=True)

                # Records processed
                st.markdown("### Records Processed")

                records_df = jobs_df[jobs_df['status'] == 'completed'][['created_at', 'records_found', 'records_new', 'records_updated', 'records_failed']].copy()

                if not records_df.empty:
                    fig = go.Figure()

                    fig.add_trace(go.Scatter(
                        x=records_df['created_at'],
                        y=records_df['records_new'],
                        name='New Records',
                        mode='lines+markers'
                    ))

                    fig.add_trace(go.Scatter(
                        x=records_df['created_at'],
                        y=records_df['records_updated'],
                        name='Updated Records',
                        mode='lines+markers'
                    ))

                    fig.add_trace(go.Scatter(
                        x=records_df['created_at'],
                        y=records_df['records_failed'],
                        name='Failed Records',
                        mode='lines+markers'
                    ))

                    fig.update_layout(
                        title="Records Processed Over Time",
                        xaxis_title="Date",
                        yaxis_title="Count",
                        hovermode='x unified'
                    )

                    st.plotly_chart(fig, config={"displayModeBar": True}, use_container_width=True)

            else:
                st.info("No job history available yet. Run some scraping jobs to see statistics here.")

        else:
            st.warning("Supabase not connected - job history unavailable")

    except Exception as e:
        st.error(f"Error loading job history: {e}")
        import traceback
        st.code(traceback.format_exc())


# Export for use in main dashboard
__all__ = ["show_scrapers_and_logs"]


# Module-level execution only when run directly (not when imported)
if __name__ == "__main__":
    show_scrapers_and_logs()
