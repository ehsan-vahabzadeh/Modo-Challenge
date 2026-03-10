
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"

pd.set_option('display.max_rows', 5000)
pd.set_option('display.max_columns', 5000)
pd.set_option('display.width', 5000)

def fetch_demand_outturn(date: str) -> pd.DataFrame:
    """Fetch half-hourly national demand outturn (INDO) for a given settlement date."""
    url = f"{BASE_URL}/demand/outturn"
    params = {
        "settlementDateFrom": date,
        "settlementDateTo": date,
        "format": "json",
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    records = resp.json()["data"]
    df = pd.DataFrame(records)
    if df.empty:
        return df
    df = df.rename(columns={
        "settlementPeriod": "settlement_period",
        "startTime": "start_time",
        "initialDemandOutturn": "demand_MW",
    })
    df["settlement_date"] = date
    return df[["settlement_date", "settlement_period", "start_time", "demand_MW"]]


def fetch_wind_generation(date: str) -> pd.DataFrame:
    """Fetch half-hourly solar generation outturn (AGWS/B1630) for a given settlement date."""
    start = f"{date}T00:00Z"
    end_dt = datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)
    end = end_dt.strftime("%Y-%m-%dT00:00Z")
    url = f"{BASE_URL}/generation/actual/per-type/wind-and-solar"
    params = {
        "from": start,
        "to": end,
        "format": "json",
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    records = resp.json()["data"]
    df = pd.DataFrame(records)
    if df.empty:
        return df
    df = df[df["psrType"] != "Solar"]

    df = df.rename(columns={
        "settlementPeriod": "settlement_period",
        "startTime": "start_time",
        "quantity": "wind_MW",
    })

    # I HAVE AMENDED THE CODE PRODUCED BY AMP HERE. UNLIKE SOLAR FORECAST, WIND FORECSAT COMES IN ONSHORE AND OFFSHORE.
    # I AM ONLY INTERESTED IN WIND FORECAST AS A WHOLE THEREFORE FOR EVERY SETTLEMENT PERIOD (1-48) I CALCULATED THE TOTAL
    # WIND GENERATION BY SUMMING ONSHORE AND OFFSHORE WIND GENERATION.
    pvt = df.groupby(['settlement_period'])['wind_MW'].sum().reset_index()
    pvt["settlement_date"] = date
    pvt = pd.merge(pvt, df.loc[:,['settlement_period', 'start_time']], how='left', on='settlement_period')
    pvt = pvt.drop_duplicates(subset=["settlement_date", "settlement_period"])

    return pvt[["settlement_date", "settlement_period", "start_time", "wind_MW"]]

def fetch_solar_generation(date: str) -> pd.DataFrame:
    """Fetch half-hourly solar generation outturn (AGWS/B1630) for a given settlement date."""
    start = f"{date}T00:00Z"
    end_dt = datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)
    end = end_dt.strftime("%Y-%m-%dT00:00Z")
    url = f"{BASE_URL}/generation/actual/per-type/wind-and-solar"
    params = {
        "from": start,
        "to": end,
        "format": "json",
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    records = resp.json()["data"]
    df = pd.DataFrame(records)
    if df.empty:
        return df
    df = df[df["psrType"] == "Solar"]
    df = df.rename(columns={
        "settlementPeriod": "settlement_period",
        "startTime": "start_time",
        "quantity": "solar_MW",
    })
    df["settlement_date"] = date
    df = df.drop_duplicates(subset=["settlement_date", "settlement_period"])
    return df[["settlement_date", "settlement_period", "start_time", "solar_MW"]]


def fetch_market_index_prices(date: str) -> pd.DataFrame:
    """Fetch half-hourly market index prices (MID) for a given settlement date."""
    start = f"{date}T00:00Z"
    end_dt = datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)
    end = end_dt.strftime("%Y-%m-%dT00:00Z")
    url = f"{BASE_URL}/balancing/pricing/market-index"
    params = {
        "from": start,
        "to": end,
        "format": "json",
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    records = resp.json()["data"]
    df = pd.DataFrame(records)
    if df.empty:
        return df
    df = df[df["dataProvider"] == "APXMIDP"]
    df = df.rename(columns={
        "settlementPeriod": "settlement_period",
        "startTime": "start_time",
        "price": "market_index_price",
        "volume": "market_index_volume",
    })
    df["settlement_date"] = date
    df = df.drop_duplicates(subset=["settlement_date", "settlement_period"])
    return df[["settlement_date", "settlement_period", "start_time", "market_index_price", "market_index_volume"]]


def fetch_day_actual_data(date: str) -> pd.DataFrame:
    """Fetch and merge demand, wind, and solar outturn for a single date."""
    demand = fetch_demand_outturn(date)
    wind = fetch_wind_generation(date)
    solar = fetch_solar_generation(date)
    mid = fetch_market_index_prices(date)

    merge_keys = ["settlement_date", "settlement_period"]
    df = demand.merge(wind, on=merge_keys, how="outer", suffixes=("", "_wind"))
    df = df.merge(solar, on=merge_keys, how="outer", suffixes=("", "_solar"))
    df = df.merge(mid, on=merge_keys, how="outer", suffixes=("", "_mid"))

    # Consolidate start_time columns
    if "start_time_wind" in df.columns:
        df["start_time"] = df["start_time"].fillna(df["start_time_wind"])
        df.drop(columns=["start_time_wind"], inplace=True)
    if "start_time_solar" in df.columns:
        df["start_time"] = df["start_time"].fillna(df["start_time_solar"])
        df.drop(columns=["start_time_solar"], inplace=True)
    if "start_time_mid" in df.columns:
        df["start_time"] = df["start_time"].fillna(df["start_time_mid"])
        df.drop(columns=["start_time_mid"], inplace=True)

    df.sort_values("settlement_period", inplace=True)
    return df.reset_index(drop=True)

def fetch_da_wind_solar_forecast(date: str) -> pd.DataFrame:
    """Fetch day-ahead wind and solar generation forecast (DGWS/B1440) for a given settlement date.

    The DA forecast for a given date is published the day before, so we query
    publishDateTimeFrom/To for the day prior.
    """
    target_dt = datetime.strptime(date, "%Y-%m-%d")
    pub_from = (target_dt - timedelta(days=1)).strftime("%Y-%m-%dT00:00Z")
    pub_to = target_dt.strftime("%Y-%m-%dT00:00Z")
    url = f"{BASE_URL}/datasets/DGWS"
    params = {
        "publishDateTimeFrom": pub_from,
        "publishDateTimeTo": pub_to,
        "format": "json",
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    records = resp.json()["data"]
    df = pd.DataFrame(records)
    df = df[df['processType'] == 'Day ahead']
    pvt = df.groupby('settlementPeriod')['quantity'].sum().reset_index()
    pvt.rename(columns={"quantity": "da_forecast_wind_and_solar_MW"}, inplace=True)

    return pvt


def fetch_da_demand_forecast(date: str) -> pd.DataFrame:
    """Fetch the latest day-ahead national demand forecast (NDF) for a given settlement date."""
    start = f"{date}T00:00Z"
    end_dt = datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)
    end = end_dt.strftime("%Y-%m-%dT00:00Z")
    url = f"{BASE_URL}/forecast/demand/day-ahead/latest"
    params = {
        "from": start,
        "to": end,
        "format": "json",
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    records = resp.json()["data"]
    df = pd.DataFrame(records)
    if df.empty:
        return df
    df = df.rename(columns={
        "settlementPeriod": "settlement_period",
        "nationalDemand": "da_demand_forecast_MW",
    })
    df["settlement_date"] = date
    df = df.drop_duplicates(subset=["settlement_date", "settlement_period"])
    df['da_demand_forecast_MW'] = df['da_demand_forecast_MW'].astype(float).ffill()
    return df[["settlement_date", "settlement_period", "da_demand_forecast_MW"]]


def calculate_day_ahead_residual_load_forecast(date: str) -> pd.DataFrame:
    """Fetch and merge day-ahead wind, solar, and demand forecasts for a single date."""
    wind_solar_sum = fetch_da_wind_solar_forecast(date)
    demand = fetch_da_demand_forecast(date)
    dfr = pd.DataFrame(range(1, 49), columns=['settlement_period'])
    dfr['residual_load_forecast_MW'] = demand['da_demand_forecast_MW'] - wind_solar_sum['da_forecast_wind_and_solar_MW']
    return dfr


def get_historic_actual_residual_load_and_day_ahead_prices(number_of_lookback_days: int) -> pd.DataFrame:
    yesterday = datetime.today().date() - pd.to_timedelta(1, unit="d")
    start_date = yesterday - timedelta(days=number_of_lookback_days)

    lst_actual_frames = []
    current = start_date
    while current <= yesterday:
        date_str = current.strftime("%Y-%m-%d")
        print(f"Fetching {date_str} ...")
        try:
            df = fetch_day_actual_data(date_str)
            lst_actual_frames.append(df)
        except Exception as e:
            print(f"  Error on {date_str}: {e}")
        current += timedelta(days=1)
        time.sleep(0.5)

    dfr = pd.DataFrame()
    for i in range(len(lst_actual_frames)):
        i_df = lst_actual_frames[i]
        dfr = pd.concat([dfr, i_df], ignore_index=True)

    dfr['residual_load_MW'] = dfr['demand_MW'] - dfr['wind_MW'] - dfr['solar_MW']

    return dfr

if __name__ == "__main__":
    df_actuals = get_historic_actual_residual_load_and_day_ahead_prices(number_of_lookback_days=3)
    today_str = pd.to_datetime('today').normalize().strftime('%Y-%m-%d')
    df_forecasts = calculate_day_ahead_residual_load_forecast(today_str)
    asd = 1
