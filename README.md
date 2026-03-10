# GB Battery Dispatch Prototype (Modo Take-Home)

A Python-based prototype that answers a practical market question:

> **Given GB demand, wind, and solar conditions, when should a battery charge/discharge to maximise day-ahead arbitrage revenue under power, capacity, and cycle constraints?**

This repository demonstrates a complete (but intentionally simplified) workflow:

1. Pull historic GB fundamentals and prices from BMRS.
2. Build a simple statistical relationship between residual load and price.
3. Use day-ahead fundamentals to estimate next-day prices.
4. Optimise battery dispatch against those estimated prices.
5. Explore scenarios interactively in a Streamlit dashboard.

---

## 1) Problem statement and scope

### The question we chose

Electricity prices are strongly influenced by the supply-demand balance. Wind and solar are low-marginal-cost but intermittent, so residual demand (demand minus renewables) can drive pricing pressure. We use that idea to ask:

- How does historic **residual load** relate to **market index price**?
- If we forecast residual load for tomorrow, what price shape does that imply?
- For a battery with chosen technical limits, what dispatch schedule maximises revenue?

### Why this is a good fit for the brief

The take-home is open-ended and asks for a tangible, scoped, market-relevant tool. This project is:

- **Market-relevant**: directly tied to storage trading/dispatch decisions.
- **Tangible**: delivers an interactive dashboard and optimisation outputs.
- **Scoped**: intentionally simple assumptions to fit the timebox.
- **Python-first**: aligns with the role's emphasis on Python modelling.

---

## 2) What the model does (end-to-end)

### Data (BMRS / Elexon)

The code pulls:

- Historic demand outturn
- Historic wind and solar outturn
- Historic market index prices
- Day-ahead wind+solar forecast
- Day-ahead demand forecast

These are fetched in `bmrs_data_wrapper.py` and merged by settlement period.

### Feature engineering

For each settlement period:

- `residual_load_MW = demand_MW - wind_MW - solar_MW`

### Price-shape model (simplified)

Using a lookback window (default 30 days), the project fits a polynomial:

- `market_index_price ~ f(residual_load_MW)`

Then day-ahead residual load forecasts are mapped through the fitted curve to create:

- `curvefitted_price` (proxy day-ahead price signal)

### Battery optimisation

`battery_optimiser.py` solves a linear optimisation problem that maximises arbitrage revenue over half-hourly periods with constraints on:

- Power limit (MW)
- Energy capacity (MWh)
- Total cycle throughput
- State-of-energy dynamics and bounds

### Dashboard workflow

`app.py` lets the user choose scenario inputs (power, capacity, cycles) and visualises:

- Charge/discharge plan
- State of energy trajectory
- Historic price vs residual-load fit
- Day-ahead residual-load and curve-fitted price

---

## 3) Key simplifying assumptions

This is a prototype for rapid insight, not a production trading model. Important simplifications include:

1. Price is modelled as a univariate function of residual load.
2. Polynomial fit is static over the chosen lookback period.
3. Perfect foresight on the day-ahead residual-load forecast used by the optimiser.
4. No explicit battery degradation cost, efficiency losses, or bid/offer spreads.
5. No imbalance risk, constraint/basis risk, or market liquidity impacts.

These assumptions are deliberate to keep the model interpretable and implementable within a short take-home timeframe.

---

## 4) Repository structure

- `app.py` — Streamlit dashboard and interactive scenario controls.
- `bmrs_data_wrapper.py` — BMRS data access + residual load calculations.
- `battery_optimiser.py` — LP-based battery dispatch optimisation.
- `main.py` — non-dashboard script path that runs the same core workflow.
- `historic_actuals.csv` — example output from historical data pull.
- `all_batteries.csv` — example output from batched optimisation runs.
- `take_home_task_open_tech_(2).md` — original brief text.

---

## 5) How to run locally

### Prerequisites

- Python 3.11+ recommended
- A virtual environment (`.venv`)

### Install

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If `requirements.txt` encoding causes issues on your machine, install core packages directly:

```bash
python -m pip install streamlit pandas numpy plotly requests matplotlib pulp
```

### Run dashboard

```bash
source .venv/bin/activate
python -m streamlit run app.py
```

---

## 6) How to interpret outputs

### Charge/discharge plan

- Positive discharge periods indicate selling energy.
- Charge periods indicate buying energy.
- Pattern reflects the optimiser's response to forecasted price shape and constraints.

### SOE plot

- Shows if the schedule respects battery limits.
- Helps diagnose whether capacity or cycle limits are binding.

### Historic fit chart

- Visual check of whether residual load explains historic price variation.
- R² is directional, not a guarantee of predictive quality.

### Forecast chart

- Shows the residual-load forecast and implied curve-fitted price shape.
- This is the immediate input to optimisation decisions.

---

## 7) Evaluation checklist (explicitly addressed)

### Why did you pick this problem?
Because battery dispatch under variable renewables is a core commercial problem in modern power markets and can be scoped meaningfully in a short project.

### What were you trying to find out?
Whether a lightweight residual-load-to-price model can produce useful day-ahead price signals for constrained battery scheduling.

### Did you make smart scoping choices?
Yes: used public BMRS data, a transparent polynomial model, and LP optimisation to deliver an end-to-end prototype quickly.

### Is the output defensible and clearly communicated?
The model is intentionally simple and the README/dashboard state assumptions, data flow, and limitations clearly.

### Does it reflect energy-market awareness?
Yes: it incorporates demand/renewables balance, day-ahead views, settlement-period dispatch, and operational battery constraints.

---

## 8) AI usage disclosure

AI tools were used extensively to speed up implementation and iteration (including Codex, AmpCode, and ChatGPT). The final repository structure, assumptions, and modelling choices were curated and adapted for this specific task.

---

## 9) Dashboard screenshot

Dashboard preview:

![Dashboard screenshot](dashboard.png)

> If `docs/dashboard.png` is missing, launch the app locally and save a screenshot at that path.

---

## 10) Git pull / merge fix (VS Code)

If you see:

```text
fatal: Need to specify how to reconcile divergent branches.
```

Set a repo-level default strategy once:

```bash
git config pull.rebase false
git config pull.ff false
```

Then pull with:

```bash
git pull --no-rebase
```

Helper script:

```bash
./scripts/setup_git_pull_strategy.sh
```
