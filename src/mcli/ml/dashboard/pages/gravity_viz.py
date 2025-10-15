"""
Gravity Anomaly Visualization Dashboard
Correlates gravitational measurements with politician locations and trading activity
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from supabase import Client, create_client

# Configure page
st.set_page_config(
    page_title="Gravity Anomaly Monitor",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .alert-high {
        color: #d32f2f;
        font-weight: 600;
    }
    .alert-medium {
        color: #f57c00;
        font-weight: 600;
    }
    .alert-low {
        color: #388e3c;
        font-weight: 600;
    }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def get_supabase_client() -> Optional[Client]:
    """Get Supabase client with Streamlit Cloud secrets support"""
    try:
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "") or st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")
    except (AttributeError, FileNotFoundError):
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    if not url or not key:
        return None

    try:
        return create_client(url, key)
    except Exception:
        return None


class GravityData:
    """Simulates gravity measurement data (in production, would fetch from real sensors/APIs)"""

    @staticmethod
    def generate_gravity_anomalies(lat: float, lon: float, radius_km: float = 50) -> pd.DataFrame:
        """
        Generate simulated gravity measurements near a location
        In production: fetch from GRACE satellite data, ground sensors, or geological surveys
        """
        num_points = np.random.randint(20, 50)

        # Generate points within radius
        angles = np.random.uniform(0, 2 * np.pi, num_points)
        distances = np.random.uniform(0, radius_km, num_points)

        # Convert to lat/lon offsets (approximate)
        lat_offsets = (distances / 111) * np.cos(angles)  # 111 km per degree latitude
        lon_offsets = (distances / (111 * np.cos(np.radians(lat)))) * np.sin(angles)

        # Generate gravity anomalies (mGal - milligals)
        # Normal Earth gravity ~9.8 m/s^2, anomalies typically +/- 100 mGal
        base_gravity = 980000  # mGal
        anomalies = np.random.normal(0, 30, num_points)  # +/- 30 mGal typical range

        # Add some interesting features
        if np.random.random() > 0.7:  # 30% chance of significant anomaly
            spike_idx = np.random.randint(0, num_points)
            anomalies[spike_idx] += np.random.uniform(50, 100)

        timestamps = [
            datetime.now() - timedelta(hours=np.random.randint(0, 168))  # Last week
            for _ in range(num_points)
        ]

        return pd.DataFrame(
            {
                "latitude": lat + lat_offsets,
                "longitude": lon + lon_offsets,
                "gravity_anomaly_mgal": anomalies,
                "absolute_gravity_mgal": base_gravity + anomalies,
                "measurement_time": timestamps,
                "distance_km": distances,
                "quality": np.random.choice(
                    ["high", "medium", "low"], num_points, p=[0.6, 0.3, 0.1]
                ),
            }
        )


class PoliticianLocations:
    """Manages politician location and trading data"""

    # Approximate coordinates for major cities (used as fallback)
    STATE_CAPITALS = {
        # US States (capital cities)
        "Alabama": (32.3668, -86.3000),
        "California": (38.5816, -121.4944),
        "Texas": (30.2672, -97.7431),
        "New Jersey": (40.2206, -74.7597),
        "Florida": (30.4383, -84.2807),
        "New York": (42.6526, -73.7562),
        "Pennsylvania": (40.2732, -76.8867),
        "Illinois": (39.7817, -89.6501),
        "Ohio": (39.9612, -82.9988),
        "Georgia": (33.7490, -84.3880),
        "Michigan": (42.7325, -84.5555),
        "North Carolina": (35.7796, -78.6382),
        "Virginia": (37.5407, -77.4360),
        "Washington": (47.0379, -122.9007),
        "Massachusetts": (42.3601, -71.0589),
        # UK
        "United Kingdom": (51.5074, -0.1278),  # London
        "UK": (51.5074, -0.1278),
        # EU Countries (capitals)
        "France": (48.8566, 2.3522),  # Paris
        "Germany": (52.5200, 13.4050),  # Berlin
        "Italy": (41.9028, 12.4964),  # Rome
        "Spain": (40.4168, -3.7038),  # Madrid
        "Poland": (52.2297, 21.0122),  # Warsaw
        "Netherlands": (52.3676, 4.9041),  # Amsterdam
        "Belgium": (50.8503, 4.3517),  # Brussels
        "Sweden": (59.3293, 18.0686),  # Stockholm
        "Austria": (48.2082, 16.3738),  # Vienna
        "Denmark": (55.6761, 12.5683),  # Copenhagen
        "Finland": (60.1699, 24.9384),  # Helsinki
    }

    # Major city coordinates for district approximations
    MAJOR_CITIES = {
        # California
        "San Francisco": (37.7749, -122.4194),
        "Los Angeles": (34.0522, -118.2437),
        "San Diego": (32.7157, -117.1611),
        "Sacramento": (38.5816, -121.4944),
        "San Jose": (37.3382, -121.8863),
        # Texas
        "Houston": (29.7604, -97.7431),
        "Dallas": (32.7767, -96.7970),
        "Austin": (30.2672, -97.7431),
        "San Antonio": (29.4241, -98.4936),
        # New York
        "New York City": (40.7128, -74.0060),
        "Buffalo": (42.8864, -78.8784),
        "Rochester": (43.1566, -77.6088),
        "Albany": (42.6526, -73.7562),
        # Florida
        "Miami": (25.7617, -80.1918),
        "Tampa": (27.9506, -82.4572),
        "Orlando": (28.5383, -81.3792),
        "Jacksonville": (30.3322, -81.6557),
        "Tallahassee": (30.4383, -84.2807),
        # Pennsylvania
        "Philadelphia": (39.9526, -75.1652),
        "Pittsburgh": (40.4406, -79.9959),
        "Harrisburg": (40.2732, -76.8867),
        # Illinois
        "Chicago": (41.8781, -87.6298),
        "Springfield": (39.7817, -89.6501),
        # New Jersey
        "Newark": (40.7357, -74.1724),
        "Jersey City": (40.7178, -74.0431),
        "Trenton": (40.2206, -74.7597),
        # And more major cities as needed...
    }

    @staticmethod
    def get_location_for_politician(
        state_or_country: str, district: str, role: str
    ) -> Tuple[float, float]:
        """
        Get lat/lon for a politician based on their state/district/role
        Returns: (latitude, longitude)
        """
        # For US Congress members with districts, try to use district-specific locations
        if district and state_or_country in [
            "California",
            "Texas",
            "New York",
            "Florida",
            "Pennsylvania",
            "Illinois",
            "New Jersey",
        ]:
            # Parse district like "CA-11" or "TX-02"
            if "-" in str(district):
                district_num = district.split("-")[-1]

                # District-specific mapping (approximate major city in district)
                # This is a simplified approach - in production, use actual district boundaries
                district_locations = {
                    # California districts (examples)
                    "California": {
                        "11": (37.7749, -122.4194),  # SF Bay Area
                        "12": (37.7749, -122.4194),  # SF
                        "13": (37.3382, -121.8863),  # Oakland/East Bay
                        "17": (37.3382, -121.8863),  # San Jose area
                        "28": (34.0522, -118.2437),  # LA
                        "43": (33.7701, -118.1937),  # Long Beach
                    },
                    # Texas districts
                    "Texas": {
                        "02": (29.7604, -97.7431),  # Houston
                        "07": (29.7604, -97.7431),  # Houston
                        "24": (32.7767, -96.7970),  # Dallas
                        "21": (29.4241, -98.4936),  # San Antonio
                    },
                    # New York districts
                    "New York": {
                        "12": (40.7128, -74.0060),  # NYC Manhattan
                        "14": (40.7128, -74.0060),  # NYC Bronx/Queens
                        "26": (42.8864, -78.8784),  # Buffalo
                    },
                    # Add more as needed
                }

                if (
                    state_or_country in district_locations
                    and district_num in district_locations[state_or_country]
                ):
                    # Add small random offset to prevent exact overlap
                    base_lat, base_lon = district_locations[state_or_country][district_num]
                    import random

                    offset_lat = random.uniform(-0.1, 0.1)
                    offset_lon = random.uniform(-0.1, 0.1)
                    return (base_lat + offset_lat, base_lon + offset_lon)

        # For senators or politicians without district mapping, use state capital with small offset
        base_coords = PoliticianLocations.STATE_CAPITALS.get(state_or_country, (38.9072, -77.0369))

        # Add small random offset to prevent exact overlap for multiple politicians from same location
        import random

        offset_lat = random.uniform(-0.2, 0.2)
        offset_lon = random.uniform(-0.2, 0.2)

        return (base_coords[0] + offset_lat, base_coords[1] + offset_lon)

    @staticmethod
    @st.cache_data(ttl=60)
    def get_politicians_from_db() -> pd.DataFrame:
        """Fetch politicians with trading data from database"""
        client = get_supabase_client()
        if not client:
            return PoliticianLocations.get_fallback_politicians()

        try:
            # Fetch politicians
            politicians_response = client.table("politicians").select("*").execute()
            if not politicians_response.data:
                return PoliticianLocations.get_fallback_politicians()

            politicians_df = pd.DataFrame(politicians_response.data)

            # Fetch trading disclosures to calculate volumes
            disclosures_response = client.table("trading_disclosures").select("*").execute()
            disclosures_df = (
                pd.DataFrame(disclosures_response.data)
                if disclosures_response.data
                else pd.DataFrame()
            )

            # Calculate trading metrics per politician
            result_data = []
            for _, pol in politicians_df.iterrows():
                pol_id = pol.get("id")
                pol_disclosures = (
                    disclosures_df[disclosures_df["politician_id"] == pol_id]
                    if not disclosures_df.empty
                    else pd.DataFrame()
                )

                # Calculate metrics
                recent_trades = len(pol_disclosures)
                total_volume = 0
                last_trade_date = None

                if not pol_disclosures.empty:
                    # Estimate volume from range midpoints
                    for _, d in pol_disclosures.iterrows():
                        min_amt = d.get("amount_range_min", 0) or 0
                        max_amt = d.get("amount_range_max", 0) or 0
                        if min_amt and max_amt:
                            total_volume += (min_amt + max_amt) / 2
                        elif d.get("amount_exact"):
                            total_volume += d["amount_exact"]

                    # Get last trade date
                    transaction_dates = pd.to_datetime(
                        pol_disclosures["transaction_date"], errors="coerce"
                    )
                    last_trade_date = transaction_dates.max()

                # Get location based on state/district/role
                state_or_country = pol.get("state_or_country", "")
                district = pol.get("district", "")
                role = pol.get("role", "")
                lat, lon = PoliticianLocations.get_location_for_politician(
                    state_or_country, district, role
                )

                # Build politician record - prefer first+last name over full_name if available
                first_name = pol.get("first_name", "").strip()
                last_name = pol.get("last_name", "").strip()
                full_name = pol.get("full_name", "").strip()

                # Use first_name + last_name if both available, otherwise use full_name
                if first_name and last_name:
                    display_name = f"{first_name} {last_name}"
                elif full_name:
                    display_name = full_name
                elif first_name:
                    display_name = first_name
                elif last_name:
                    display_name = last_name
                else:
                    display_name = f"Politician {pol_id[:8]}"  # Fallback to ID

                result_data.append(
                    {
                        "name": display_name,
                        "role": pol.get("role", "Unknown"),
                        "state": state_or_country,
                        "district": pol.get("district"),
                        "party": pol.get("party", "Unknown"),
                        "lat": lat,
                        "lon": lon,
                        "recent_trades": recent_trades,
                        "total_trade_volume": total_volume,
                        "last_trade_date": (
                            last_trade_date if pd.notna(last_trade_date) else datetime(2025, 1, 1)
                        ),
                    }
                )

            result_df = pd.DataFrame(result_data)
            # Filter out politicians with no trading data
            result_df = result_df[result_df["recent_trades"] > 0]

            if result_df.empty:
                return PoliticianLocations.get_fallback_politicians()

            return result_df

        except Exception as e:
            st.warning(f"Could not fetch politicians from database: {e}")
            return PoliticianLocations.get_fallback_politicians()

    @staticmethod
    def get_fallback_politicians() -> pd.DataFrame:
        """Fallback sample data if database is unavailable"""
        politicians = [
            {
                "name": "Nancy Pelosi",
                "role": "US House Representative",
                "state": "California",
                "district": "CA-11",
                "party": "Democrat",
                "lat": 37.7749,
                "lon": -122.4194,
                "recent_trades": 15,
                "total_trade_volume": 5_000_000,
                "last_trade_date": datetime(2025, 10, 5),
            },
            {
                "name": "Tommy Tuberville",
                "role": "US Senator",
                "state": "Alabama",
                "district": None,
                "party": "Republican",
                "lat": 32.3668,
                "lon": -86.3000,
                "recent_trades": 23,
                "total_trade_volume": 3_200_000,
                "last_trade_date": datetime(2025, 10, 3),
            },
        ]
        return pd.DataFrame(politicians)


def create_gravity_map(
    politicians_df: pd.DataFrame, selected_politician: Optional[str] = None
) -> go.Figure:
    """Create interactive map showing politician locations and gravity anomalies"""

    fig = go.Figure()

    # Add politician markers
    for _, pol in politicians_df.iterrows():
        is_selected = pol["name"] == selected_politician

        fig.add_trace(
            go.Scattergeo(
                lon=[pol["lon"]],
                lat=[pol["lat"]],
                mode="markers+text",
                marker=dict(
                    size=20 if is_selected else 12,
                    color="red" if is_selected else "blue",
                    symbol="star",
                    line=dict(width=2, color="white"),
                ),
                text=pol["name"],
                textposition="top center",
                name=pol["name"],
                hovertemplate=(
                    f"<b>{pol['name']}</b><br>"
                    f"Role: {pol['role']}<br>"
                    f"State: {pol['state']}<br>"
                    f"Recent Trades: {pol['recent_trades']}<br>"
                    f"Trade Volume: ${pol['total_trade_volume']:,.0f}<br>"
                    "<extra></extra>"
                ),
            )
        )

        # Add gravity measurement points if politician is selected
        if is_selected:
            gravity_data = GravityData.generate_gravity_anomalies(pol["lat"], pol["lon"])

            # Color by anomaly strength
            colors = gravity_data["gravity_anomaly_mgal"]

            fig.add_trace(
                go.Scattergeo(
                    lon=gravity_data["longitude"],
                    lat=gravity_data["latitude"],
                    mode="markers",
                    marker=dict(
                        size=8,
                        color=colors,
                        colorscale="RdYlGn_r",
                        cmin=-50,
                        cmax=50,
                        colorbar=dict(title="Gravity<br>Anomaly<br>(mGal)", x=1.1),
                        showscale=True,
                    ),
                    name="Gravity Measurements",
                    hovertemplate=(
                        "Anomaly: %{marker.color:.2f} mGal<br>"
                        "Distance: %{customdata[0]:.1f} km<br>"
                        "Time: %{customdata[1]}<br>"
                        "<extra></extra>"
                    ),
                    customdata=gravity_data[["distance_km", "measurement_time"]].values,
                )
            )

    # Update layout
    fig.update_geos(
        projection_type="natural earth",
        showcountries=True,
        countrycolor="lightgray",
        showland=True,
        landcolor="white",
        showocean=True,
        oceancolor="lightblue",
        coastlinewidth=1,
    )

    fig.update_layout(
        title="Politician Locations & Gravity Anomalies",
        height=600,
        showlegend=False,
        margin=dict(l=0, r=0, t=40, b=0),
    )

    return fig


def create_gravity_heatmap(gravity_df: pd.DataFrame) -> go.Figure:
    """Create heatmap of gravity measurements over time"""

    fig = go.Figure(
        data=go.Densitymapbox(
            lat=gravity_df["latitude"],
            lon=gravity_df["longitude"],
            z=gravity_df["gravity_anomaly_mgal"],
            radius=20,
            colorscale="RdYlGn_r",
            zmin=-50,
            zmax=50,
            hovertemplate="Anomaly: %{z:.2f} mGal<extra></extra>",
        )
    )

    # Calculate center point
    center_lat = gravity_df["latitude"].mean()
    center_lon = gravity_df["longitude"].mean()

    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox=dict(center=dict(lat=center_lat, lon=center_lon), zoom=8),
        margin=dict(l=0, r=0, t=0, b=0),
        height=400,
    )

    return fig


def create_correlation_chart(politician_df: pd.DataFrame, gravity_df: pd.DataFrame) -> go.Figure:
    """Create scatter plot correlating gravity anomalies with trading activity"""

    # Aggregate gravity data by time period
    gravity_stats = {
        "max_anomaly": gravity_df["gravity_anomaly_mgal"].max(),
        "mean_anomaly": gravity_df["gravity_anomaly_mgal"].mean(),
        "std_anomaly": gravity_df["gravity_anomaly_mgal"].std(),
        "num_measurements": len(gravity_df),
    }

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=["Max Anomaly", "Mean Anomaly", "Std Dev", "Measurements"],
            y=[
                gravity_stats["max_anomaly"],
                gravity_stats["mean_anomaly"],
                gravity_stats["std_anomaly"],
                gravity_stats["num_measurements"] / 10,  # Scale for visibility
            ],
            marker_color=["red", "orange", "yellow", "green"],
            text=[
                f"{v:.2f}"
                for v in [
                    gravity_stats["max_anomaly"],
                    gravity_stats["mean_anomaly"],
                    gravity_stats["std_anomaly"],
                    gravity_stats["num_measurements"] / 10,
                ]
            ],
            textposition="auto",
        )
    )

    fig.update_layout(
        title="Gravity Anomaly Statistics",
        xaxis_title="Metric",
        yaxis_title="Value",
        height=300,
        showlegend=False,
    )

    return fig


def create_timeline_chart(gravity_df: pd.DataFrame, politician_name: str) -> go.Figure:
    """Create timeline showing gravity measurements over time"""

    # Sort by time
    gravity_df = gravity_df.sort_values("measurement_time")

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=gravity_df["measurement_time"],
            y=gravity_df["gravity_anomaly_mgal"],
            mode="markers+lines",
            marker=dict(
                size=8,
                color=gravity_df["gravity_anomaly_mgal"],
                colorscale="RdYlGn_r",
                showscale=False,
                line=dict(width=1, color="white"),
            ),
            line=dict(width=1, color="gray", dash="dot"),
            name="Gravity Anomaly",
            hovertemplate=("Time: %{x}<br>" "Anomaly: %{y:.2f} mGal<br>" "<extra></extra>"),
        )
    )

    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

    fig.update_layout(
        title=f"Gravity Measurements Over Time - {politician_name}",
        xaxis_title="Time",
        yaxis_title="Gravity Anomaly (mGal)",
        height=350,
        showlegend=False,
        hovermode="closest",
    )

    return fig


def main():
    """Main application"""

    # Header
    st.markdown('<h1 class="main-header">🌍 Gravity Anomaly Monitor</h1>', unsafe_allow_html=True)
    st.markdown(
        """
    Monitor gravitational anomalies near politician locations and correlate with trading activity.
    Data sources: GRACE satellites, ground-based gravimeters, and geological surveys.
    """
    )

    # Sidebar
    st.sidebar.header("⚙️ Configuration")

    # Load politician data from database
    politicians_df = PoliticianLocations.get_politicians_from_db()

    # Show data info
    st.sidebar.info(f"📊 Loaded {len(politicians_df)} politicians with trading data")

    # Politician selection
    selected_politician = st.sidebar.selectbox(
        "Select Politician", options=["All"] + politicians_df["name"].tolist(), index=0
    )

    # Filters
    st.sidebar.subheader("📊 Filters")

    date_range = st.sidebar.slider(
        "Data Range (days)",
        min_value=1,
        max_value=30,
        value=7,
        help="Number of days of historical data to display",
    )

    min_trade_volume = st.sidebar.number_input(
        "Minimum Trade Volume ($)",
        min_value=0,
        max_value=10_000_000,
        value=0,  # Changed from 1,000,000 to 0 to show all politicians by default
        step=100_000,
        format="%d",
        help="Filter politicians by minimum trade volume. Set to 0 to see all.",
    )

    # Filter politicians by trade volume
    filtered_politicians = politicians_df[politicians_df["total_trade_volume"] >= min_trade_volume]

    # Show filter results
    if len(filtered_politicians) < len(politicians_df):
        st.sidebar.warning(
            f"⚠️ Filter reduced to {len(filtered_politicians)} politicians (from {len(politicians_df)})"
        )
    else:
        st.sidebar.success(f"✅ Showing all {len(filtered_politicians)} politicians")

    # Main content
    if selected_politician != "All":
        # Single politician view
        pol = politicians_df[politicians_df["name"] == selected_politician].iloc[0]

        # Metrics row
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                label="Recent Trades",
                value=pol["recent_trades"],
                delta=f"Last: {(datetime.now() - pol['last_trade_date']).days}d ago",
            )

        with col2:
            st.metric(label="Trade Volume", value=f"${pol['total_trade_volume']:,.0f}", delta=None)

        with col3:
            gravity_data = GravityData.generate_gravity_anomalies(pol["lat"], pol["lon"])
            max_anomaly = gravity_data["gravity_anomaly_mgal"].max()
            alert_class = (
                "alert-high"
                if max_anomaly > 40
                else "alert-medium" if max_anomaly > 20 else "alert-low"
            )
            st.metric(
                label="Max Gravity Anomaly",
                value=f"{max_anomaly:.2f} mGal",
                help="Unusually high anomalies may indicate geological features or data quality issues",
            )

        with col4:
            st.metric(
                label="Measurements",
                value=len(gravity_data),
                delta=f"{len(gravity_data[gravity_data['quality'] == 'high'])} high quality",
            )

        # Tabs for different visualizations
        tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Map", "🔥 Heatmap", "📈 Timeline", "📊 Statistics"])

        with tab1:
            st.plotly_chart(
                create_gravity_map(filtered_politicians, selected_politician),
                config={"displayModeBar": True},
                use_container_width=True,
            )

        with tab2:
            st.plotly_chart(
                create_gravity_heatmap(gravity_data),
                config={"displayModeBar": True},
                use_container_width=True,
            )

            # Data table
            st.subheader("Measurement Data")
            st.dataframe(
                gravity_data[
                    [
                        "latitude",
                        "longitude",
                        "gravity_anomaly_mgal",
                        "distance_km",
                        "quality",
                        "measurement_time",
                    ]
                ]
                .sort_values("gravity_anomaly_mgal", ascending=False)
                .head(10),
                use_container_width=True,
            )

        with tab3:
            st.plotly_chart(
                create_timeline_chart(gravity_data, selected_politician),
                config={"displayModeBar": True},
                use_container_width=True,
            )

        with tab4:
            st.plotly_chart(
                create_correlation_chart(filtered_politicians, gravity_data),
                config={"displayModeBar": True},
                use_container_width=True,
            )

            # Additional stats
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Gravity Statistics")
                st.write(
                    f"**Mean Anomaly:** {gravity_data['gravity_anomaly_mgal'].mean():.2f} mGal"
                )
                st.write(f"**Std Dev:** {gravity_data['gravity_anomaly_mgal'].std():.2f} mGal")
                st.write(f"**Min:** {gravity_data['gravity_anomaly_mgal'].min():.2f} mGal")
                st.write(f"**Max:** {gravity_data['gravity_anomaly_mgal'].max():.2f} mGal")

            with col2:
                st.subheader("Data Quality")
                quality_counts = gravity_data["quality"].value_counts()
                st.bar_chart(quality_counts)

    else:
        # Overview of all politicians
        st.subheader("📍 All Politicians Overview")

        st.plotly_chart(
            create_gravity_map(filtered_politicians),
            config={"displayModeBar": True},
            use_container_width=True,
        )

        # Summary table
        st.subheader("Trading Activity Summary")
        summary_df = filtered_politicians[
            [
                "name",
                "role",
                "state",
                "party",
                "recent_trades",
                "total_trade_volume",
                "last_trade_date",
            ]
        ].sort_values("total_trade_volume", ascending=False)

        st.dataframe(summary_df, use_container_width=True)

        # Trading volume chart
        st.subheader("Trade Volume Comparison")
        fig = px.bar(
            filtered_politicians.sort_values("total_trade_volume", ascending=True),
            x="total_trade_volume",
            y="name",
            orientation="h",
            color="party",
            color_discrete_map={"Democrat": "blue", "Republican": "red"},
            labels={"total_trade_volume": "Total Trade Volume ($)", "name": "Politician"},
            title="Trade Volume by Politician",
        )
        st.plotly_chart(fig, config={"displayModeBar": True}, use_container_width=True)

    # Footer
    st.markdown("---")
    st.markdown(
        """
    **Data Sources:**
    - Gravity: GRACE satellites, ground gravimeters, geological surveys
    - Trading: mcli politician trading database
    - Locations: Official government records

    **Note:** This is a demonstration. In production, integrate with real-time data sources.
    """
    )


if __name__ == "__main__":
    main()
