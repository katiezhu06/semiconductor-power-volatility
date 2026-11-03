# Semiconductor–Power Volatility

An undergraduate project exploring volatility connectedness between semiconductor stocks and power producers using Python.

Phase 1 collects prices and builds the return and volatility series. Phase 2 measures how those volatility series move together, using rolling correlation. Correlation describes co-movement. It does not show causality or the direction of risk transmission. The project does not estimate a VAR, compute forecast-error variance decompositions, or build network graphs.

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
4. Define the power-producer portfolio return from the equal-weight average of the `CEG`, `VST`, and `NRG` simple returns, as in Methodology & Equations.
5. Compute 20-day rolling volatility for `SOXX` and the power-producer portfolio. Volatility is the sample standard deviation of the trailing 20 log returns, annualized with \(\sqrt{252}\). The first 19 return dates are blank because the window is not full yet.

## Phase 2 steps

Phase 2 reads `rolling_volatility.csv` from the Phase 1 run that the pipeline just wrote. It does not download prices again.

1. Load the 20-day rolling volatility of `SOXX` and of the power-producer portfolio.
2. Align the two series on the date and drop any row where either value is missing. Those missing values are the opening dates, while the 20-day volatility window is still filling.
3. On each remaining date, compute the Pearson correlation of the two volatility series over a trailing window:
   - **60 observations** is the primary window.
   - **40 and 90 observations** are sensitivity checks.
   The correlation for a window of length \(W\) is blank until that date has \(W\) volatility readings.
4. Save the three correlation series and plot them against time.

Pearson correlation is a number from \(-1\) to \(1\). Inside one window, a value near \(1\) means the two volatilities were high on the same days and low on the same days. A value near \(0\) means little straight-line co-movement. A value near \(-1\) means one series tended to be high when the other was low.

That number is only a description of co-movement. A high correlation does not show that semiconductor volatility causes power-producer volatility, or the reverse, and it does not identify the direction of risk transmission.

Adjacent points on the plot share most of the same volatility readings, because the window moves forward by only one trading day. Each volatility reading itself already uses 20 returns. The correlation line is therefore expected to change gradually.

## Methodology & Equations

### 1. Daily Log Returns

For each individual asset $i \in \{\text{SOXX}, \text{CEG}, \text{VST}, \text{NRG}\}$, daily log returns are computed from adjusted closing prices $P_{i,t}$:

$$r_{i,t} = \ln\left(\frac{P_{i,t}}{P_{i,t-1}}\right)$$

The power-producer portfolio return $r_{\text{power},t}$ is derived from the equal-weight average of the underlying simple returns:

$$R_{\text{power},t} = \frac{1}{3} \sum_{i \in \{\text{CEG}, \text{VST}, \text{NRG}\}} (\exp(r_{i,t}) - 1)$$

$$r_{\text{power},t} = \ln(1 + R_{\text{power},t})$$

### 2. Rolling Volatility

Historical volatility is estimated using a 20-trading-day rolling window ($N = 20$). The annualized sample standard deviation $\sigma_{i,t}^{\text{ann}}$ is calculated as:

$$\hat{\sigma}_{i,t} = \sqrt{\frac{1}{N - 1} \sum_{k=0}^{N-1} \left( r_{i,t-k} - \bar{r}_{i,t} \right)^2}$$

$$\sigma_{i,t}^{\text{ann}} = \hat{\sigma}_{i,t} \times \sqrt{252}$$

The first 19 return dates are left blank while the window fills.

### 3. Rolling Correlation

The degree of co-movement between $\sigma_{\text{SOXX},t}^{\text{ann}}$ and $\sigma_{\text{power},t}^{\text{ann}}$ is measured via a rolling Pearson correlation coefficient over an $M$-day window:

$$\rho_{t}^{(M)} = \frac{\sum_{k=0}^{M-1} (\sigma_{\text{SOXX},t-k}^{\text{ann}} - \bar{\sigma}_{\text{SOXX},t}^{(M)})(\sigma_{\text{power},t-k}^{\text{ann}} - \bar{\sigma}_{\text{power},t}^{(M)})}{\sqrt{\sum_{k=0}^{M-1} (\sigma_{\text{SOXX},t-k}^{\text{ann}} - \bar{\sigma}_{\text{SOXX},t}^{(M)})^2} \sqrt{\sum_{k=0}^{M-1} (\sigma_{\text{power},t-k}^{\text{ann}} - \bar{\sigma}_{\text{power},t}^{(M)})^2}}$$

## Reproduce

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/run_pipeline.py
```

That one command runs Phase 1 and then Phase 2. Phase 2 imports Phase 1 and calls it, so the volatility file does not have to be passed from one script to the next by hand.

Each execution creates a new folder and leaves earlier folders unchanged:

```text
data/phase1/run_1/
data/phase1/run_2/
```

Optional arguments: `--start` (default `2022-11-01`), `--window` (default `20`), `--data-root` (default `data`), `--windows` (default `40 60 90`), and `--primary` (default `60`).

`python src/phase1_preprocess.py` only builds the next Phase 1 folder. `python src/phase2_correlation.py` reads the latest folder’s volatility file and, if no run exists yet, runs Phase 1 first.

## Outputs

Every pipeline run writes these files inside its own `data/phase1/run_N/` folder:

| File | Contents |
| --- | --- |
| `adjusted_close.csv` | Shared-date adjusted closes for `SOXX`, `CEG`, `VST`, and `NRG` |
| `log_returns.csv` | Daily log returns plus the `power_portfolio` column |
| `rolling_volatility.csv` | Annualized 20-day rolling volatility for `SOXX` and `power_portfolio` |
| `phase1_diagnostics.txt` | Missing-data report, sample span, and volatility summary |
| `rolling_correlation.csv` | Rolling correlations for windows of 40, 60, and 90 observations |
| `rolling_correlation.png` | Time plot of those three correlation series |

Generated files under `data/` are listed in `.gitignore` and should stay local. Run the pipeline again to create the next numbered folder.

## Later phases

Later work can estimate a VAR, compute forecast-error variance decompositions, or build network graphs. None of that is part of Phase 1 or Phase 2.
