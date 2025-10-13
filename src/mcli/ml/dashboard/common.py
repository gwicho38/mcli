"""
Common utilities for MCLI ML Dashboards.

This module provides shared functionality across all dashboard variants to avoid code duplication.
"""

import os
import warnings
from pathlib import Path
from typing import Optional

import streamlit as st
from dotenv import load_dotenv


def suppress_streamlit_warnings():
    """
    Suppress common Streamlit, Plotly, and media file warnings.

    Call this at the top of your dashboard file before importing other modules.
    """
    # Suppress Streamlit warnings when used outside runtime context
    warnings.filterwarnings("ignore", message=".*missing ScriptRunContext.*")
    warnings.filterwarnings("ignore", message=".*No runtime found.*")
    warnings.filterwarnings("ignore", message=".*Session state does not function.*")
    warnings.filterwarnings("ignore", message=".*to view this Streamlit app.*")

    # Suppress Plotly deprecation warnings
    warnings.filterwarnings("ignore", message=".*keyword arguments have been deprecated.*")
    warnings.filterwarnings("ignore", message=".*Use `config` instead.*")

    # Suppress media file errors
    warnings.filterwarnings("ignore", message=".*MediaFileHandler.*")
    warnings.filterwarnings("ignore", message=".*Missing file.*")
    warnings.filterwarnings("ignore", message=".*Bad filename.*")

    # Suppress general warnings
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)

    # Suppress specific Streamlit media file errors in logging
    import logging

    logging.getLogger("streamlit.runtime.media_file_storage").setLevel(logging.ERROR)
    logging.getLogger("streamlit.web.server.media_file_handler").setLevel(logging.ERROR)


def setup_page_config(
    page_title: str = "MCLI ML Dashboard",
    page_icon: str = "📊",
    layout: str = "wide",
    initial_sidebar_state: str = "expanded",
):
    """
    Configure Streamlit page with standard settings.

    IMPORTANT: This must be called before any other Streamlit commands.

    Args:
        page_title: Title shown in browser tab
        page_icon: Emoji or image icon
        layout: "wide" or "centered"
        initial_sidebar_state: "expanded" or "collapsed"

    Example:
        from mcli.ml.dashboard.common import setup_page_config

        setup_page_config(page_title="ML Training Dashboard")
    """
    st.set_page_config(
        page_title=page_title,
        page_icon=page_icon,
        layout=layout,
        initial_sidebar_state=initial_sidebar_state,
    )


@st.cache_resource
def get_supabase_client():
    """
    Get cached Supabase client with automatic credential detection.

    Tries multiple sources in order:
    1. Streamlit Cloud secrets (for deployed apps)
    2. Environment variables (for local development)
    3. .env.local file in supabase directory

    Returns:
        Supabase Client instance or None if credentials not found

    Example:
        from mcli.ml.dashboard.common import get_supabase_client

        client = get_supabase_client()
        if client:
            data = client.table('politicians').select('*').execute()
    """
    from supabase import Client, create_client

    # Try Streamlit secrets first (for Streamlit Cloud)
    url = ""
    key = ""

    try:
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "") or st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")
    except (AttributeError, FileNotFoundError, KeyError):
        pass

    # Fall back to environment variables (for local dev)
    if not url or not key:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    # Try loading from .env.local in supabase directory
    if not url or not key:
        env_path = Path(__file__).parent.parent.parent.parent.parent / "supabase" / ".env.local"
        if env_path.exists():
            load_dotenv(env_path)
            url = os.getenv("SUPABASE_URL", "")
            key = os.getenv("SUPABASE_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    if not url or not key:
        st.warning(
            "⚠️ Supabase credentials not found. Configure SUPABASE_URL and SUPABASE_KEY "
            "in Streamlit Cloud secrets or environment variables."
        )
        return None

    try:
        client = create_client(url, key)

        # Test connection with a simple query
        try:
            # Try politicians table first (most common)
            client.table("politicians").select("id").limit(1).execute()
        except Exception:
            # If politicians table doesn't exist, try another table
            pass

        return client
    except Exception as e:
        st.error(f"❌ Failed to create Supabase client: {e}")
        return None


def load_environment_variables():
    """
    Load environment variables from various sources.

    Tries loading from:
    1. Current directory .env file
    2. Parent supabase/.env.local file

    Example:
        from mcli.ml.dashboard.common import load_environment_variables

        load_environment_variables()
        api_key = os.getenv("API_KEY")
    """
    # Try current directory
    load_dotenv()

    # Try supabase directory
    env_path = Path(__file__).parent.parent.parent.parent.parent / "supabase" / ".env.local"
    if env_path.exists():
        load_dotenv(env_path)
