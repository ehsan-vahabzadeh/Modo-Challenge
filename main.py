import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from bmrs_data_wrapper import get_historic_actual_residual_load_and_day_ahead_prices
from bmrs_data_wrapper import calculate_day_ahead_residual_load_forecast
from battery_optimiser import optimise_battery

LOOKBACK_DAYS = 30
CURVEFITTING_POLYNOMIAL_DEGREE = 3
def curvefit_price_and_residual_load(df, order=1, plot_results=False):
    """
    Fit a polynomial of given order to market price vs residual load.

    Parameters:
        df (DataFrame): Must contain 'residual_load_MW' and 'market_index_price'.
        order (int): Degree of the polynomial fit (default is 1, linear).

    Returns:
        coeffs (np.ndarray): Polynomial coefficients, highest degree first.
        r_squared (float): Coefficient of determination.
        :param plot_results: whether to plot the results or not.

    """
    x = df["residual_load_MW"].values
    y = df["market_index_price"].values

    # Filter out NaNs or infinities
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]

    # Fit polynomial
    coeffs = np.polyfit(x, y, order)

    # Evaluate polynomial for plotting
    x_sorted = np.sort(x)
    y_fit = np.polyval(coeffs, x_sorted)

    # Calculate R²
    y_pred = np.polyval(coeffs, x)
    r_squared = 1 - np.sum((y - y_pred) ** 2) / np.sum((y - np.mean(y)) ** 2)

    # ---- Create readable polynomial equation ----
    terms = []
    for i, c in enumerate(coeffs):
        power = order - i
        if power > 1:
            terms.append(f"{c:.3f}x^{power}")
        elif power == 1:
            terms.append(f"{c:.3f}x")
        else:
            terms.append(f"{c:.3f}")

    equation = " + ".join(terms).replace("+ -", "- ")

    if plot_results:
        plt.figure(figsize=(10, 6))
        plt.scatter(x, y, alpha=0.4, s=10, label="Actual")

        plt.plot(
            x_sorted,
            y_fit,
            linewidth=2,
            label=f"{equation}\nR² = {r_squared:.3f}"
        )

        plt.xlabel("Residual Load (MW)")
        plt.ylabel("Market Index Price (£/MWh)")
        plt.title("Market Index Price vs Residual Load")
        plt.legend()
        plt.tight_layout()
        plt.show()

    return coeffs, r_squared

def main_calculations():
    df_actuals = get_historic_actual_residual_load_and_day_ahead_prices(number_of_lookback_days=LOOKBACK_DAYS)
    curvefit_coeffs = curvefit_price_and_residual_load(df_actuals, order= CURVEFITTING_POLYNOMIAL_DEGREE, plot_results=True)

    today_str = pd.to_datetime('today').normalize().strftime('%Y-%m-%d')
    df_forecasts = calculate_day_ahead_residual_load_forecast(today_str)

    df_forecasts['curvefitted_price'] = (
            df_forecasts['residual_load_forecast_MW']*curvefit_coeffs[0][0]**3 +
            df_forecasts['residual_load_forecast_MW'] * curvefit_coeffs[0][0] ** 3 +
            df_forecasts['residual_load_forecast_MW'] * curvefit_coeffs[0][1] ** 2 +
            df_forecasts['residual_load_forecast_MW'] * curvefit_coeffs[0][2] ** 1 +
            curvefit_coeffs[0][3]
    )

    all_batteries = pd.DataFrame()
    for i_cycle in [1, 2]:
        for i_duration in [0.5, 1, 2, 4, 8]:
            df = optimise_battery(prices=df_forecasts['curvefitted_price'].to_list(), power_mw=10, batt_duration=i_duration, cycles=i_cycle)
            df['cycle'] = i_cycle
            df['duration'] = i_duration
            all_batteries = pd.concat([all_batteries, df], ignore_index=True)
 

if __name__ == "__main__":
    main_calculations()
