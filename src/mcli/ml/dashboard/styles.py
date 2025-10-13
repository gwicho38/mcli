"""
Shared CSS styles for MCLI ML Dashboards.

This module centralizes all CSS styling to avoid duplication across dashboard files.
"""

# Standard dashboard CSS used across all dashboard variants
DASHBOARD_CSS = """
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .alert-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 0.75rem;
        border-radius: 0.25rem;
    }
    .alert-warning {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 0.75rem;
        border-radius: 0.25rem;
    }
    .alert-danger {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 0.75rem;
        border-radius: 0.25rem;
    }
</style>
"""


def apply_dashboard_styles():
    """
    Apply standard dashboard CSS styles.

    Call this function once in your dashboard to apply the standard styling.

    Example:
        import streamlit as st
        from mcli.ml.dashboard.styles import apply_dashboard_styles

        apply_dashboard_styles()
    """
    import streamlit as st

    st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)
