"""Reusable chart components for Streamlit dashboards"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import streamlit as st
from typing import Optional, Dict, List, Any


def create_timeline_chart(
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str = "Timeline",
    color_col: Optional[str] = None,
    height: int = 400
) -> go.Figure:
    """Create a timeline chart with Plotly"""

    fig = px.line(
        data,
        x=x_col,
        y=y_col,
        color=color_col,
        title=title,
        markers=True
    )

    fig.update_layout(
        height=height,
        hovermode='x unified',
        showlegend=True if color_col else False
    )

    return fig


def create_status_pie_chart(
    data: pd.DataFrame,
    status_col: str,
    title: str = "Status Distribution",
    color_map: Optional[Dict[str, str]] = None
) -> go.Figure:
    """Create a pie chart for status distribution"""

    status_counts = data[status_col].value_counts()

    if color_map is None:
        color_map = {
            'completed': '#10b981',
            'running': '#3b82f6',
            'pending': '#f59e0b',
            'failed': '#ef4444',
            'cancelled': '#6b7280'
        }

    colors = [color_map.get(status.lower(), '#6b7280') for status in status_counts.index]

    fig = go.Figure(data=[go.Pie(
        labels=status_counts.index,
        values=status_counts.values,
        marker=dict(colors=colors),
        hole=0.4
    )])

    fig.update_layout(
        title=title,
        height=350,
        showlegend=True
    )

    return fig


def create_metric_trend_chart(
    data: pd.DataFrame,
    time_col: str,
    metric_col: str,
    title: str,
    target_value: Optional[float] = None
) -> go.Figure:
    """Create a metric trend chart with optional target line"""

    fig = go.Figure()

    # Add metric line
    fig.add_trace(go.Scatter(
        x=data[time_col],
        y=data[metric_col],
        mode='lines+markers',
        name=metric_col,
        line=dict(width=3),
        marker=dict(size=8)
    ))

    # Add target line if specified
    if target_value is not None:
        fig.add_hline(
            y=target_value,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Target: {target_value}"
        )

    fig.update_layout(
        title=title,
        xaxis_title=time_col,
        yaxis_title=metric_col,
        height=400,
        hovermode='x unified'
    )

    return fig


def create_heatmap(
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    value_col: str,
    title: str = "Heatmap",
    color_scale: str = "Blues"
) -> go.Figure:
    """Create a heatmap visualization"""

    pivot_data = data.pivot_table(
        index=y_col,
        columns=x_col,
        values=value_col,
        aggfunc='mean'
    )

    fig = px.imshow(
        pivot_data,
        color_continuous_scale=color_scale,
        title=title,
        aspect="auto"
    )

    fig.update_layout(height=400)

    return fig


def create_gantt_chart(
    data: pd.DataFrame,
    task_col: str,
    start_col: str,
    end_col: str,
    status_col: Optional[str] = None,
    title: str = "Timeline"
) -> go.Figure:
    """Create a Gantt chart for job/task scheduling"""

    fig = px.timeline(
        data,
        x_start=start_col,
        x_end=end_col,
        y=task_col,
        color=status_col,
        title=title
    )

    fig.update_yaxes(categoryorder="total ascending")
    fig.update_layout(height=max(400, len(data) * 30))

    return fig


def create_multi_metric_gauge(
    values: Dict[str, float],
    max_values: Dict[str, float],
    title: str = "Metrics"
) -> go.Figure:
    """Create multiple gauge charts in a grid"""

    from plotly.subplots import make_subplots

    n_metrics = len(values)
    cols = min(3, n_metrics)
    rows = (n_metrics + cols - 1) // cols

    fig = make_subplots(
        rows=rows,
        cols=cols,
        specs=[[{'type': 'indicator'}] * cols] * rows,
        subplot_titles=list(values.keys())
    )

    for idx, (metric, value) in enumerate(values.items()):
        row = idx // cols + 1
        col = idx % cols + 1
        max_val = max_values.get(metric, 100)

        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=value,
                title={'text': metric},
                gauge={
                    'axis': {'range': [None, max_val]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, max_val * 0.5], 'color': "lightgray"},
                        {'range': [max_val * 0.5, max_val * 0.8], 'color': "gray"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': max_val * 0.9
                    }
                }
            ),
            row=row,
            col=col
        )

    fig.update_layout(
        title=title,
        height=300 * rows
    )

    return fig


def create_waterfall_chart(
    categories: List[str],
    values: List[float],
    title: str = "Waterfall Chart"
) -> go.Figure:
    """Create a waterfall chart for step-by-step changes"""

    fig = go.Figure(go.Waterfall(
        name="",
        orientation="v",
        measure=["relative"] * (len(values) - 1) + ["total"],
        x=categories,
        y=values,
        connector={"line": {"color": "rgb(63, 63, 63)"}},
    ))

    fig.update_layout(
        title=title,
        showlegend=False,
        height=400
    )

    return fig


def render_chart(fig: go.Figure, key: Optional[str] = None):
    """Helper to render Plotly chart with consistent configuration"""
    st.plotly_chart(
        fig,
        width="stretch",
        config={"responsive": True},
        key=key
    )
