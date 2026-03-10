import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="Modo Trial Dashboard",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Modo Trial Dashboard")
st.markdown("A simple Streamlit demo using synthetic electricity market data.")

# -----------------------------
# Generate fake market data
# -----------------------------
@st.cache_data
def make_data():
    np.random.seed(42)

    dates = pd.date_range("2026-01-01", periods=24 * 30, freq="H")
    zones = ["North", "South", "East", "West"]

    rows = []
    for zone in zones:
        base_price = {
            "North": 55,
            "South": 65,
            "East": 60,
            "West": 50
        }[zone]

        for dt in dates:
            hour = dt.hour
            demand = 900 + 200 * np.sin((hour / 24) * 2 * np.pi) + np.random.normal(0, 40)
            renewable = 300 + 120 * np.cos((hour / 24) * 2 * np.pi) + np.random.normal(0, 30)
            price = base_price + 0.03 * demand - 0.04 * renewable + np.random.normal(0, 5)

            rows.append({
                "timestamp": dt,
                "zone": zone,
                "hour": hour,
                "demand_mw": max(demand, 0),
                "renewable_mw": max(renewable, 0),
                "price_gbp_mwh": max(price, 0)
            })

    df = pd.DataFrame(rows)
    df["date"] = df["timestamp"].dt.date
    return df

df = make_data()

# -----------------------------
# Sidebar filters
# -----------------------------
st.sidebar.header("Filters")

selected_zones = st.sidebar.multiselect(
    "Select zone(s)",
    options=sorted(df["zone"].unique()),
    default=sorted(df["zone"].unique())
)

min_date = df["timestamp"].min().date()
max_date = df["timestamp"].max().date()

date_range = st.sidebar.date_input(
    "Select date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if len(date_range) != 2:
    st.warning("Please select both a start and end date.")
    st.stop()

start_date, end_date = date_range

filtered = df[
    (df["zone"].isin(selected_zones)) &
    (df["date"] >= start_date) &
    (df["date"] <= end_date)
].copy()

if filtered.empty:
    st.error("No data available for the selected filters.")
    st.stop()

# -----------------------------
# KPIs
# -----------------------------
col1, col2, col3 = st.columns(3)

col1.metric("Average Price (£/MWh)", f"{filtered['price_gbp_mwh'].mean():.1f}")
col2.metric("Average Demand (MW)", f"{filtered['demand_mw'].mean():.0f}")
col3.metric("Average Renewable Output (MW)", f"{filtered['renewable_mw'].mean():.0f}")

# -----------------------------
# Line chart: price over time
# -----------------------------
st.subheader("Price over time")

fig_price = px.line(
    filtered,
    x="timestamp",
    y="price_gbp_mwh",
    color="zone",
    title="Electricity Price by Zone"
)
st.plotly_chart(fig_price, use_container_width=True)

# -----------------------------
# Scatter: demand vs price
# -----------------------------
st.subheader("Demand vs Price")

fig_scatter = px.scatter(
    filtered,
    x="demand_mw",
    y="price_gbp_mwh",
    color="zone",
    hover_data=["timestamp", "renewable_mw"],
    title="Demand vs Price Relationship"
)
st.plotly_chart(fig_scatter, use_container_width=True)

# -----------------------------
# Hourly average profile
# -----------------------------
st.subheader("Average hourly price profile")

hourly = (
    filtered.groupby(["zone", "hour"], as_index=False)["price_gbp_mwh"]
    .mean()
)

fig_hourly = px.line(
    hourly,
    x="hour",
    y="price_gbp_mwh",
    color="zone",
    markers=True,
    title="Average Hourly Price"
)
st.plotly_chart(fig_hourly, use_container_width=True)

# -----------------------------
# Raw data table
# -----------------------------
st.subheader("Raw data")
st.dataframe(filtered, use_container_width=True)