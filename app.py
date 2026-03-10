import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ------------------------------------------------------------
# Page setup
# ------------------------------------------------------------
st.set_page_config(
    page_title="Battery Dispatch Dashboard",
    page_icon="🔋",
    layout="wide"
)

st.title("🔋 Battery Dispatch Dashboard")
st.markdown("Synthetic Streamlit demo for battery charging/discharging, state of energy, regression, and price forecast.")

# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------
DURATION_OPTIONS = {
    "30 minutes": 0.5,
    "1 hour": 1.0,
    "2 hours": 2.0,
    "4 hours": 4.0,
    "8 hours": 8.0
}

BASE_SETTLEMENT_HOURS = 0.5
N_BASE_PERIODS = 48
BATTERY_POWER_MW = 1.0          # assumed fixed rated power
ROUND_TRIP_EFFICIENCY = 0.90    # fake but reasonable
CHARGE_EFF = np.sqrt(ROUND_TRIP_EFFICIENCY)
DISCHARGE_EFF = np.sqrt(ROUND_TRIP_EFFICIENCY)


# ------------------------------------------------------------
# Fake base data
# ------------------------------------------------------------
@st.cache_data
def make_base_market_dataframe():
    """
    Creates a fake 48-settlement-period dataframe for one day.
    Columns:
      - settlement_period
      - timestamp
      - price_forecast
      - residual_load
    """
    np.random.seed(42)

    timestamps = pd.date_range("2026-03-10 00:00:00", periods=N_BASE_PERIODS, freq="30min")
    sp = np.arange(1, N_BASE_PERIODS + 1)

    # synthetic residual load shape
    residual_load = (
        25000
        + 3500 * np.sin(np.linspace(-1.2, 2.4 * np.pi - 1.2, N_BASE_PERIODS))
        + 1200 * np.sin(np.linspace(0, 6 * np.pi, N_BASE_PERIODS))
        + np.random.normal(0, 450, N_BASE_PERIODS)
    )

    # synthetic price related to residual load
    price_forecast = (
        55
        + 0.0032 * (residual_load - residual_load.mean())
        + 10 * np.sin(np.linspace(0, 2 * np.pi, N_BASE_PERIODS) + 0.6)
        + np.random.normal(0, 2.5, N_BASE_PERIODS)
    )

    df = pd.DataFrame({
        "settlement_period": sp,
        "timestamp": timestamps,
        "price_forecast": price_forecast,
        "residual_load": residual_load
    })

    return df


@st.cache_data
def make_scatter_dataframe():
    """
    Fake dataframe for scatter/regression plot.
    Example relationship: daily spread vs revenue
    """
    np.random.seed(7)

    x = np.linspace(15, 120, 35)
    y = 0.82 * x + 8 + np.random.normal(0, 10, len(x))

    return pd.DataFrame({
        "x_metric": x,
        "y_metric": y
    })


# ------------------------------------------------------------
# Battery dispatch builder
# ------------------------------------------------------------
def build_dispatch_dataframe(base_df: pd.DataFrame, duration_h: float) -> pd.DataFrame:
    """
    Build charging/discharging and SOE profile for a chosen battery duration.

    Assumptions:
      - base data are 48 half-hour periods
      - periods are aggregated according to duration
      - battery power is fixed at BATTERY_POWER_MW
      - energy capacity = BATTERY_POWER_MW * duration_h
      - simple heuristic:
          charge in cheapest blocks
          discharge in most expensive blocks
          idle elsewhere
    """
    block_size = int(duration_h / BASE_SETTLEMENT_HOURS)  # 1,2,4,8,16
    n_blocks = N_BASE_PERIODS // block_size

    df = base_df.copy()
    df["block"] = np.repeat(np.arange(1, n_blocks + 1), block_size)

    agg = (
        df.groupby("block", as_index=False)
        .agg(
            timestamp=("timestamp", "first"),
            price_forecast=("price_forecast", "mean"),
            residual_load=("residual_load", "mean")
        )
    )

    # Decide dispatch based on price ranking
    n_charge = max(1, n_blocks // 3)
    n_discharge = max(1, n_blocks // 3)

    sorted_idx = agg["price_forecast"].sort_values().index
    charge_idx = sorted_idx[:n_charge]
    discharge_idx = sorted_idx[-n_discharge:]

    agg["dispatch_mwh"] = 0.0

    # energy moved in each aggregated block = power * duration
    block_energy = BATTERY_POWER_MW * duration_h

    agg.loc[charge_idx, "dispatch_mwh"] = -block_energy   # charging
    agg.loc[discharge_idx, "dispatch_mwh"] = block_energy # discharging

    # Battery capacity
    energy_capacity_mwh = BATTERY_POWER_MW * duration_h
    soe = 0.5 * energy_capacity_mwh  # initial SOE at 50%

    soe_list = []
    for dispatch in agg["dispatch_mwh"]:
        if dispatch < 0:
            # charging
            energy_in = -dispatch
            soe += energy_in * CHARGE_EFF
        elif dispatch > 0:
            # discharging
            energy_out = dispatch
            soe -= energy_out / DISCHARGE_EFF

        soe = np.clip(soe, 0, energy_capacity_mwh)
        soe_list.append(soe)

    agg["soe_mwh"] = soe_list
    agg["period_label"] = np.arange(1, len(agg) + 1)
    agg["duration_h"] = duration_h
    agg["energy_capacity_mwh"] = energy_capacity_mwh

    return agg


# ------------------------------------------------------------
# Plot functions
# ------------------------------------------------------------
def plot_charge_discharge(dispatch_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    # positive = discharge
    discharge = dispatch_df["dispatch_mwh"].clip(lower=0)
    charge = dispatch_df["dispatch_mwh"].clip(upper=0)

    fig.add_trace(go.Bar(
        x=dispatch_df["period_label"],
        y=discharge,
        name="Discharging",
        marker_color="royalblue",
        hovertemplate="Period %{x}<br>Discharge: %{y:.2f} MWh<extra></extra>"
    ))

    fig.add_trace(go.Bar(
        x=dispatch_df["period_label"],
        y=charge,
        name="Charging",
        marker_color="red",
        hovertemplate="Period %{x}<br>Charge: %{y:.2f} MWh<extra></extra>"
    ))

    fig.update_layout(
        title="Charging and Discharging",
        xaxis_title="Settlement Period",
        yaxis_title="Energy (MWh)",
        barmode="relative",
        height=420,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig


def plot_soe(dispatch_df: pd.DataFrame) -> go.Figure:
    cap = dispatch_df["energy_capacity_mwh"].iloc[0]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dispatch_df["period_label"],
        y=dispatch_df["soe_mwh"],
        mode="lines+markers",
        name="State of Energy",
        hovertemplate="Period %{x}<br>SOE: %{y:.2f} MWh<extra></extra>"
    ))

    fig.add_hline(
        y=cap,
        line_dash="dash",
        annotation_text="Capacity",
        annotation_position="top left"
    )

    fig.update_layout(
        title="State of Energy",
        xaxis_title="Settlement Period",
        yaxis_title="State of Energy (MWh)",
        height=420
    )

    return fig


def plot_scatter_with_fit(scatter_df: pd.DataFrame) -> go.Figure:
    x = scatter_df["x_metric"].values
    y = scatter_df["y_metric"].values

    # linear regression
    coeffs = np.polyfit(x, y, 1)
    slope, intercept = coeffs
    y_fit = slope * x + intercept

    # R^2
    ss_res = np.sum((y - y_fit) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot

    x_line = np.linspace(x.min(), x.max(), 200)
    y_line = slope * x_line + intercept

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x,
        y=y,
        mode="markers",
        name="Data points",
        marker=dict(size=9),
        hovertemplate="x: %{x:.2f}<br>y: %{y:.2f}<extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=x_line,
        y=y_line,
        mode="lines",
        name="Linear fit",
        line=dict(width=3)
    ))

    fig.update_layout(
        title=f"Scatter Plot with Linear Fit<br><sup>y = {slope:.3f}x + {intercept:.3f}, R² = {r2:.3f}</sup>",
        xaxis_title="X metric",
        yaxis_title="Y metric",
        height=420
    )

    return fig


def plot_price_and_residual_load(base_df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=base_df["settlement_period"],
            y=base_df["price_forecast"],
            mode="lines+markers",
            name="Price Forecast",
            hovertemplate="SP %{x}<br>Price: %{y:.2f}<extra></extra>"
        ),
        secondary_y=False
    )

    fig.add_trace(
        go.Scatter(
            x=base_df["settlement_period"],
            y=base_df["residual_load"],
            mode="lines",
            name="Residual Load",
            hovertemplate="SP %{x}<br>Residual load: %{y:.0f}<extra></extra>"
        ),
        secondary_y=True
    )

    fig.update_layout(
        title="Price Forecast and Residual Load",
        xaxis_title="Settlement Period",
        height=450,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    fig.update_yaxes(title_text="Price", secondary_y=False)
    fig.update_yaxes(title_text="Residual Load", secondary_y=True)

    return fig


# ------------------------------------------------------------
# Data creation
# ------------------------------------------------------------
base_market_df = make_base_market_dataframe()
scatter_df = make_scatter_dataframe()

# ------------------------------------------------------------
# Sidebar controls
# ------------------------------------------------------------
st.sidebar.header("Controls")

duration_label = st.sidebar.selectbox(
    "Battery duration",
    list(DURATION_OPTIONS.keys()),
    index=1
)

duration_h = DURATION_OPTIONS[duration_label]
dispatch_df = build_dispatch_dataframe(base_market_df, duration_h)

st.sidebar.markdown("### Assumptions")
st.sidebar.write(f"- Rated power: {BATTERY_POWER_MW:.1f} MW")
st.sidebar.write(f"- Duration: {duration_h:.1f} h")
st.sidebar.write(f"- Energy capacity: {BATTERY_POWER_MW * duration_h:.1f} MWh")
st.sidebar.write(f"- Number of settlement points shown: {len(dispatch_df)}")

# ------------------------------------------------------------
# KPI row
# ------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)

c1.metric("Battery Duration", duration_label)
c2.metric("Points on Interactive Plots", f"{len(dispatch_df)}")
c3.metric("Average Price", f"{base_market_df['price_forecast'].mean():.1f}")
c4.metric("Average Residual Load", f"{base_market_df['residual_load'].mean():.0f}")

# ------------------------------------------------------------
# Plot row 1
# ------------------------------------------------------------
row1_col1, row1_col2 = st.columns(2)

with row1_col1:
    st.plotly_chart(plot_charge_discharge(dispatch_df), use_container_width=True)

with row1_col2:
    st.plotly_chart(plot_soe(dispatch_df), use_container_width=True)

# ------------------------------------------------------------
# Plot row 2
# ------------------------------------------------------------
row2_col1, row2_col2 = st.columns(2)

with row2_col1:
    st.plotly_chart(plot_scatter_with_fit(scatter_df), use_container_width=True)

with row2_col2:
    st.plotly_chart(plot_price_and_residual_load(base_market_df), use_container_width=True)

# ------------------------------------------------------------
# Optional raw data display
# ------------------------------------------------------------
with st.expander("Show fake input dataframes"):
    st.subheader("Base market dataframe")
    st.dataframe(base_market_df, use_container_width=True)

    st.subheader("Interactive dispatch dataframe")
    st.dataframe(dispatch_df, use_container_width=True)

    st.subheader("Scatter dataframe")
    st.dataframe(scatter_df, use_container_width=True)