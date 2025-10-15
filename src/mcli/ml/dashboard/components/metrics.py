"""Reusable metric display components"""

from typing import Optional, Union

import streamlit as st


def display_metric_card(
    label: str,
    value: Union[int, float, str],
    delta: Optional[Union[int, float, str]] = None,
    delta_color: str = "normal",
    help_text: Optional[str] = None,
    icon: Optional[str] = None,
):
    """Display a metric card with optional delta and icon"""

    if icon:
        label = f"{icon} {label}"

    st.metric(label=label, value=value, delta=delta, delta_color=delta_color, help=help_text)


def display_status_badge(status: str, size: str = "medium") -> str:
    """Return a colored status badge"""

    status_colors = {
        "completed": "🟢",
        "success": "🟢",
        "running": "🔵",
        "in_progress": "🔵",
        "pending": "🟡",
        "waiting": "🟡",
        "failed": "🔴",
        "error": "🔴",
        "cancelled": "⚪",
        "unknown": "⚫",
    }

    icon = status_colors.get(status.lower(), "⚫")

    if size == "small":
        return f"{icon} {status}"
    elif size == "large":
        return f"## {icon} {status}"
    else:  # medium
        return f"### {icon} {status}"


def display_kpi_row(metrics: dict, columns: Optional[int] = None):
    """Display a row of KPIs in columns"""

    if columns is None:
        columns = len(metrics)

    cols = st.columns(columns)

    for idx, (label, value) in enumerate(metrics.items()):
        with cols[idx % columns]:
            if isinstance(value, dict):
                display_metric_card(
                    label=label,
                    value=value.get("value", "-"),
                    delta=value.get("delta"),
                    delta_color=value.get("delta_color", "normal"),
                    help_text=value.get("help"),
                    icon=value.get("icon"),
                )
            else:
                st.metric(label=label, value=value)


def display_progress_bar(label: str, progress: float, show_percentage: bool = True):
    """Display a progress bar with label"""

    st.text(label)
    st.progress(min(1.0, max(0.0, progress)))

    if show_percentage:
        st.caption(f"{progress * 100:.1f}%")


def display_health_indicator(component: str, is_healthy: bool, details: Optional[str] = None):
    """Display a health status indicator"""

    if is_healthy:
        st.success(f"✅ {component}: Healthy" + (f" ({details})" if details else ""))
    else:
        st.error(f"❌ {component}: Unhealthy" + (f" ({details})" if details else ""))


def display_alert(message: str, alert_type: str = "info", icon: Optional[str] = None):
    """Display an alert message"""

    if icon:
        message = f"{icon} {message}"

    if alert_type == "success":
        st.success(message)
    elif alert_type == "warning":
        st.warning(message)
    elif alert_type == "error":
        st.error(message)
    else:  # info
        st.info(message)
