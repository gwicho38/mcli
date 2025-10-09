"""Utility functions using streamlit-extras for enhanced dashboard UI"""

import streamlit as st

# Try to import streamlit-extras components
HAS_EXTRAS = True
try:
    from streamlit_extras.metric_cards import style_metric_cards
    from streamlit_extras.badges import badge
    from streamlit_extras.colored_header import colored_header
    from streamlit_extras.card import card
    from streamlit_extras.stoggle import stoggle
    from streamlit_extras.grid import grid
    from streamlit_extras.add_vertical_space import add_vertical_space
    from streamlit_extras.stylable_container import stylable_container
except ImportError:
    HAS_EXTRAS = False
    style_metric_cards = None
    badge = None
    colored_header = None
    card = None
    stoggle = None
    grid = None
    add_vertical_space = None
    stylable_container = None


def enhanced_metrics(metrics_data: list, use_container_width: bool = True):
    """
    Display enhanced metric cards with styling from streamlit-extras

    Args:
        metrics_data: List of dicts with keys: label, value, delta (optional)
        use_container_width: Whether to use full container width

    Example:
        enhanced_metrics([
            {"label": "Total Transactions", "value": "1,234", "delta": "+12%"},
            {"label": "Portfolio Value", "value": "$50,000", "delta": "-2.3%"},
        ])
    """
    if not HAS_EXTRAS:
        # Fallback to standard metrics
        cols = st.columns(len(metrics_data))
        for i, metric in enumerate(metrics_data):
            with cols[i]:
                st.metric(
                    label=metric["label"],
                    value=metric["value"],
                    delta=metric.get("delta")
                )
        return

    # Use streamlit-extras styled metrics
    cols = st.columns(len(metrics_data))
    for i, metric in enumerate(metrics_data):
        with cols[i]:
            st.metric(
                label=metric["label"],
                value=metric["value"],
                delta=metric.get("delta")
            )
    style_metric_cards()


def status_badge(label: str, url: str = None):
    """
    Display a status badge

    Args:
        label: Badge text (e.g., "Live", "Production", "Beta")
        url: Optional URL to link to
    """
    if not HAS_EXTRAS:
        st.markdown(f"**{label}**")
        return

    badge(type="success", name=label, url=url)


def section_header(label: str, description: str = None, divider: str = "rainbow"):
    """
    Display a colored section header with optional description

    Args:
        label: Header text
        description: Optional description text
        divider: Color of divider line
    """
    if not HAS_EXTRAS:
        st.header(label)
        if description:
            st.markdown(description)
        st.divider()
        return

    colored_header(
        label=label,
        description=description or "",
        color_name=divider
    )


def info_card(title: str, text: str, image: str = None, url: str = None,
              has_button: bool = False, button_text: str = "Learn More"):
    """
    Display an information card

    Args:
        title: Card title
        text: Card content
        image: Optional image URL
        url: Optional URL to link to
        has_button: Whether to show a button
        button_text: Button text if has_button is True
    """
    if not HAS_EXTRAS:
        with st.container():
            st.subheader(title)
            if image:
                st.image(image)
            st.markdown(text)
            if url and has_button:
                st.link_button(button_text, url)
        return

    kwargs = {
        "title": title,
        "text": text,
    }
    if image:
        kwargs["image"] = image
    if url:
        kwargs["url"] = url

    card(**kwargs)


def collapsible_section(label: str, content_fn, default_open: bool = False):
    """
    Create a collapsible toggle section

    Args:
        label: Section label
        content_fn: Function to call to render content
        default_open: Whether section starts open
    """
    if not HAS_EXTRAS:
        with st.expander(label, expanded=default_open):
            content_fn()
        return

    stoggle(label, content_fn)


def dashboard_grid(num_cols: int = 3, gap: str = "medium"):
    """
    Create a responsive grid layout

    Args:
        num_cols: Number of columns
        gap: Gap size between columns

    Returns:
        Grid object for use in with statement
    """
    if not HAS_EXTRAS:
        return st.columns(num_cols)

    return grid(num_cols, gap=gap)


def vertical_space(lines: int = 1):
    """
    Add vertical spacing

    Args:
        lines: Number of lines to add
    """
    if not HAS_EXTRAS:
        for _ in range(lines):
            st.write("")
        return

    add_vertical_space(lines)


def styled_container(key: str, css_styles: str):
    """
    Create a container with custom CSS styling

    Args:
        key: Unique key for the container
        css_styles: CSS styles to apply

    Returns:
        Context manager for styled container
    """
    if not HAS_EXTRAS:
        return st.container()

    return stylable_container(
        key=key,
        css_styles=css_styles
    )


def trading_status_card(status: str, portfolio_value: float, daily_pnl: float,
                       positions: int, cash: float):
    """
    Display a trading status summary card

    Args:
        status: Trading status (e.g., "Active", "Paused")
        portfolio_value: Current portfolio value
        daily_pnl: Daily profit/loss
        positions: Number of open positions
        cash: Available cash
    """
    status_color = "🟢" if status == "Active" else "🔴"
    pnl_emoji = "📈" if daily_pnl >= 0 else "📉"
    pnl_sign = "+" if daily_pnl >= 0 else ""

    section_header(
        f"{status_color} Trading Status: {status}",
        f"Real-time portfolio monitoring and execution",
        divider="blue"
    )

    enhanced_metrics([
        {
            "label": "Portfolio Value",
            "value": f"${portfolio_value:,.2f}",
            "delta": f"{pnl_sign}${daily_pnl:,.2f}"
        },
        {
            "label": "Open Positions",
            "value": str(positions),
        },
        {
            "label": "Available Cash",
            "value": f"${cash:,.2f}",
        },
    ])


def data_quality_indicators(total_records: int, clean_records: int,
                            errors: int, last_update: str):
    """
    Display data quality indicators

    Args:
        total_records: Total number of records
        clean_records: Number of clean records
        errors: Number of errors
        last_update: Last update timestamp
    """
    quality_pct = (clean_records / total_records * 100) if total_records > 0 else 0

    section_header(
        "📊 Data Quality Metrics",
        f"Last updated: {last_update}",
        divider="green"
    )

    enhanced_metrics([
        {
            "label": "Total Records",
            "value": f"{total_records:,}",
        },
        {
            "label": "Data Quality",
            "value": f"{quality_pct:.1f}%",
            "delta": f"{clean_records:,} clean"
        },
        {
            "label": "Errors",
            "value": str(errors),
            "delta": f"{(errors/total_records*100):.2f}%" if total_records > 0 else "0%"
        },
    ])


# Export available components
__all__ = [
    'HAS_EXTRAS',
    'enhanced_metrics',
    'status_badge',
    'section_header',
    'info_card',
    'collapsible_section',
    'dashboard_grid',
    'vertical_space',
    'styled_container',
    'trading_status_card',
    'data_quality_indicators',
]
