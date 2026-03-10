import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from battery_optimiser import optimise_battery
from bmrs_data_wrapper import (
    calculate_day_ahead_residual_load_forecast,
    get_historic_actual_residual_load_and_day_ahead_prices,
)

st.set_page_config(page_title="Battery Dispatch Dashboard", page_icon="🔋", layout="wide")

LOOKBACK_OPTIONS = [7, 14, 30, 60]
<<<<<<< ours
lookback_days = 30
# POLY_DEGREE_OPTIONS = [1, 2, 3, 4]
poly_degree = 3
POWER_OPTIONS_MW = [0.5, 1.0, 2.0, 4.0]
CAPACITY_OPTIONS_MWH = [0.5, 1.0, 2.0, 4.0, 8.0]
CYCLE_OPTIONS = [1, 2, 3, 5, 10]
=======
POLY_DEGREE_OPTIONS = [1, 2, 3, 4]
POWER_OPTIONS_MW = [0.5, 1.0, 2.0, 4.0]
CAPACITY_OPTIONS_MWH = [0.5, 1.0, 2.0, 4.0, 8.0]
CYCLE_OPTIONS = [0.5, 1.0, 2.0, 3.0]
>>>>>>> theirs


def fit_price_curve(df: pd.DataFrame, degree: int) -> tuple[np.ndarray, float]:
    """Fit polynomial curve of market index price versus residual load."""
    x = df["residual_load_MW"].to_numpy(dtype=float)
    y = df["market_index_price"].to_numpy(dtype=float)
    valid = np.isfinite(x) & np.isfinite(y)
    x = x[valid]
    y = y[valid]

    coeffs = np.polyfit(x, y, degree)
    y_hat = np.polyval(coeffs, x)
    r_squared = 1 - np.sum((y - y_hat) ** 2) / np.sum((y - np.mean(y)) ** 2)
    return coeffs, float(r_squared)


@st.cache_data(show_spinner=True)
def build_input_data(lookback_days: int, polynomial_degree: int):
    """Load historical actuals, fit price curve, and build day-ahead forecasts."""
    historical = get_historic_actual_residual_load_and_day_ahead_prices(lookback_days)
    coeffs, r_squared = fit_price_curve(historical, polynomial_degree)

    today_str = pd.Timestamp.today().normalize().strftime("%Y-%m-%d")
    forecast = calculate_day_ahead_residual_load_forecast(today_str)
    forecast["curvefitted_price"] = np.polyval(coeffs, forecast["residual_load_forecast_MW"])
    return historical, forecast, coeffs, r_squared


def build_dispatch(prices: list[float], power_mw: float, capacity_mwh: float, cycles: float) -> pd.DataFrame:
    dispatch = optimise_battery(
        prices=prices,
        power_mw=power_mw,
        capacity_mwh=capacity_mwh,
        cycles=cycles,
    )
    dispatch["cumulative_revenue"] = dispatch["revenue"].cumsum()
    return dispatch


def plot_charge_discharge(dispatch_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(
        x=dispatch_df["settlement_period"],
        y=dispatch_df["discharge_MW"],
        name="Discharge (MW)",
        marker_color="royalblue",
    )
    fig.add_bar(
        x=dispatch_df["settlement_period"],
        y=-dispatch_df["charge_MW"],
        name="Charge (MW)",
        marker_color="indianred",
    )
    fig.update_layout(
        title="Charge / Discharge Schedule",
        xaxis_title="Settlement Period",
        yaxis_title="Power (MW)",
        barmode="relative",
        height=400,
    )
    return fig


def plot_soe(dispatch_df: pd.DataFrame, capacity_mwh: float) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(
        x=dispatch_df["settlement_period"],
        y=dispatch_df["soe_MWh"],
        mode="lines+markers",
        name="SOE",
    )
    fig.add_hline(y=capacity_mwh, line_dash="dash", annotation_text="Capacity")
    fig.update_layout(
        title="State of Energy",
        xaxis_title="Settlement Period",
        yaxis_title="SOE (MWh)",
        height=400,
    )
    return fig


def plot_price_residual_forecast(forecast_df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_scatter(
        x=forecast_df["settlement_period"],
        y=forecast_df["curvefitted_price"],
        mode="lines+markers",
        name="Curvefitted Price",
        secondary_y=False,
    )
    fig.add_scatter(
        x=forecast_df["settlement_period"],
        y=forecast_df["residual_load_forecast_MW"],
        mode="lines",
        name="Residual Load Forecast",
        secondary_y=True,
    )
    fig.update_layout(title="Day-ahead Forecast Inputs", xaxis_title="Settlement Period", height=420)
    fig.update_yaxes(title_text="Price (£/MWh)", secondary_y=False)
    fig.update_yaxes(title_text="Residual Load (MW)", secondary_y=True)
    return fig


def plot_historic_scatter_with_fit(historical_df: pd.DataFrame, coeffs: np.ndarray, r_squared: float) -> go.Figure:
    x = historical_df["residual_load_MW"].to_numpy(dtype=float)
    y = historical_df["market_index_price"].to_numpy(dtype=float)
    valid = np.isfinite(x) & np.isfinite(y)
    x = x[valid]
    y = y[valid]

    x_line = np.linspace(x.min(), x.max(), 300)
    y_line = np.polyval(coeffs, x_line)

    fig = go.Figure()
    fig.add_scatter(x=x, y=y, mode="markers", name="Historical points", marker=dict(size=5, opacity=0.4))
    fig.add_scatter(x=x_line, y=y_line, mode="lines", name="Polynomial fit", line=dict(width=3))
    fig.update_layout(
        title=f"Historical Price vs Residual Load (R² = {r_squared:.3f})",
        xaxis_title="Residual Load (MW)",
        yaxis_title="Market Index Price (£/MWh)",
        height=420,
    )
    return fig


st.title("🔋 GB Battery Dispatch Dashboard")
st.markdown(
    "Interactive view of BMRS-based curve-fitted prices and battery optimization. "
    "Choose **power (MW)**, **capacity (MWh)**, and **cycles** in the sidebar."
)

st.sidebar.header("Model Inputs")
<<<<<<< ours
# lookback_days = st.sidebar.selectbox("Historic lookback window (days)", LOOKBACK_OPTIONS, index=2)
# poly_degree = st.sidebar.selectbox("Polynomial degree", POLY_DEGREE_OPTIONS, index=2)
=======
lookback_days = st.sidebar.selectbox("Historic lookback window (days)", LOOKBACK_OPTIONS, index=2)
poly_degree = st.sidebar.selectbox("Polynomial degree", POLY_DEGREE_OPTIONS, index=2)
>>>>>>> theirs
power_mw = st.sidebar.selectbox("Battery power (MW)", POWER_OPTIONS_MW, index=1)
capacity_mwh = st.sidebar.selectbox("Battery capacity (MWh)", CAPACITY_OPTIONS_MWH, index=2)
cycles = st.sidebar.selectbox("Max cycles", CYCLE_OPTIONS, index=1)

if capacity_mwh < power_mw * 0.5:
    st.sidebar.warning("Capacity is very small relative to power for 30-minute settlement periods.")

try:
    historical_df, forecast_df, coeffs, r_squared = build_input_data(lookback_days, poly_degree)
except Exception as exc:
    st.error(f"Data preparation failed: {exc}")
    st.stop()

if forecast_df.empty:
    st.warning("Forecast dataset is empty; cannot run optimizer.")
    st.stop()

prices = forecast_df["curvefitted_price"].astype(float).tolist()
dispatch_df = build_dispatch(prices, power_mw, capacity_mwh, cycles)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Power (MW)", f"{power_mw:.1f}")
c2.metric("Capacity (MWh)", f"{capacity_mwh:.1f}")
c3.metric("Cycles", f"{cycles:.1f}")
c4.metric("Optimized Revenue (£)", f"{dispatch_df['revenue'].sum():,.0f}")

row1_col1, row1_col2 = st.columns(2)
with row1_col1:
    st.plotly_chart(plot_charge_discharge(dispatch_df), use_container_width=True)
with row1_col2:
    st.plotly_chart(plot_soe(dispatch_df, capacity_mwh), use_container_width=True)

row2_col1, row2_col2 = st.columns(2)
with row2_col1:
    st.plotly_chart(plot_historic_scatter_with_fit(historical_df, coeffs, r_squared), use_container_width=True)
with row2_col2:
    st.plotly_chart(plot_price_residual_forecast(forecast_df), use_container_width=True)

st.subheader("Optimization Output")
st.dataframe(dispatch_df, use_container_width=True)

with st.expander("Show source dataframes"):
    st.write("Historical actuals used for curve-fitting")
    st.dataframe(historical_df, use_container_width=True)

    st.write("Day-ahead forecast inputs")
    st.dataframe(forecast_df, use_container_width=True)
