# Semiconductor–Power Volatility

An undergraduate project exploring volatility connectedness between semiconductor stocks and power producers using Python.

Phase 1 collects prices and builds the return and volatility series used later. It does not estimate a VAR, compute forecast-error variance decompositions, measure correlations, or build network graphs, so it does not yet say whether semiconductor and power-producer volatility have become more synchronized.

## Universe

| Series | Role |
| --- | --- |
| `SOXX` | iShares Semiconductor ETF |
| `CEG` | Constellation Energy |
| `VST` | Vistra |
| `NRG` | NRG Energy |

The sample starts on **1 November 2022** and runs through the latest trading day available when the script is run. `CEG`, `VST`, and `NRG` are combined into one equal-weight power-producer portfolio.

## Phase 1 steps

1. Download each ticker’s daily adjusted close from Yahoo Finance (`auto_adjust=True`, so closes account for splits and dividends). If the script runs before 16:05 US Eastern, it drops the current session so the files contain completed closes only.
2. Report missing values, dates that are not shared by all four assets, and shared-price gaps longer than four calendar days.
3. Keep only dates where `SOXX`, `CEG`, `VST`, and `NRG` all have a price, then compute daily log returns, \(\ln(P_t / P_{t-1})\).
4. Define the power-producer portfolio as the equal-weight average of the `CEG`, `VST`, and `NRG` log returns.
5. Compute 20-day rolling volatility for `SOXX` and the power-producer portfolio. Volatility is the sample standard deviation of the trailing 20 log returns, annualized with \(\sqrt{252}\). The first 19 return dates are blank because the window is not full yet.

## Reproduce

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/phase1_preprocess.py
```

Optional arguments: `--start` (default `2022-11-01`), `--window` (default `20`), and `--output-dir` (default `data`).

## Outputs

The script writes these files under `data/`:

| File | Contents |
| --- | --- |
| `adjusted_close.csv` | Shared-date adjusted closes for `SOXX`, `CEG`, `VST`, and `NRG` |
| `log_returns.csv` | Daily log returns plus the `power_portfolio` column |
| `rolling_volatility.csv` | Annualized 20-day rolling volatility for `SOXX` and `power_portfolio` |
| `phase1_diagnostics.txt` | Missing-data report, sample span, and volatility summary |

Generated data files are listed in `.gitignore` and should stay local. Re-run the script to recreate them.

## Later phases

Later work can use these series for VAR estimation, forecast-error variance decompositions, correlation, and network graphs. None of that is part of Phase 1.
