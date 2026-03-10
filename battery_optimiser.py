import pulp
import pandas as pd


def optimise_battery(prices: list[float], power_mw: float, capacity_mwh: float, cycles: float) -> pd.DataFrame:
    """Optimise a battery against half-hourly prices.

    Parameters
    ----------
    prices : list of floats
        Curvefitted price (£/MWh) for each settlement period.
    power_mw : float
        Charge / discharge power rating (MW).
    capacity_mwh : float
        State of energy capacity (MWh).
    cycles : float
        Max number of full cycles. Total charge energy <= cycles * power_mw,
        total discharge energy <= cycles * power_mw.

    Returns
    -------
    pd.DataFrame with columns:
        settlement_period, price, charge_MW, discharge_MW, soe_MWh, revenue
    """
    N = len(prices)
    PERIOD_HOURS = 0.5

    model = pulp.LpProblem("battery_optimiser", pulp.LpMaximize)

    charge = [pulp.LpVariable(f"charge_{t}", 0, power_mw) for t in range(N)]
    discharge = [pulp.LpVariable(f"discharge_{t}", 0, power_mw) for t in range(N)]
    soe = [pulp.LpVariable(f"soe_{t}", 0, capacity_mwh) for t in range(N)]

    # Maximise revenue: discharge sells at price, charge buys at price
    model += pulp.lpSum(
        (discharge[t] - charge[t]) * prices[t] * PERIOD_HOURS for t in range(N)
    )

    # State of energy constraints
    for t in range(N):
        if t == 0:
            model += soe[t] == charge[t] * PERIOD_HOURS - discharge[t] * PERIOD_HOURS
        else:
            model += soe[t] == soe[t - 1] + charge[t] * PERIOD_HOURS - discharge[t] * PERIOD_HOURS

    # Cycle constraints
    max_energy = cycles * capacity_mwh
    model += pulp.lpSum(charge[t] * PERIOD_HOURS for t in range(N)) <= max_energy
    model += pulp.lpSum(discharge[t] * PERIOD_HOURS for t in range(N)) <= max_energy

    model.solve(pulp.PULP_CBC_CMD(msg=0))

    results = []
    for t in range(N):
        c = charge[t].varValue
        d = discharge[t].varValue
        s = soe[t].varValue
        rev = (d - c) * prices[t] * PERIOD_HOURS
        results.append({
            "settlement_period": t + 1,
            "price": prices[t],
            "charge_MW": c,
            "discharge_MW": d,
            "soe_MWh": s,
            "revenue": rev,
        })

    return pd.DataFrame(results)


if __name__ == "__main__":
    import random
    random_values = [random.randint(20, 150) for _ in range(48)]
    df = optimise_battery(prices=random_values, power_mw=1.0, capacity_mwh=2.0, cycles=8)
    print(df[['charge_MW','discharge_MW','revenue']].sum())

