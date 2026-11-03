# Extreme Shock Dates in 60-Day Rolling Correlation

Screening report for news verification and Finviz alignment.

**Source:** `data/processed/rolling_correlation.csv`  
**Series:** `correlation_60` (primary Phase 2 window)  
**Rule:** absolute successive difference \(|\rho_t - \rho_{t-1}| > 0.1671\)  
**Threshold origin:** 99th percentile of \(|\Delta\rho_t|\) from the exploratory difference histogram  
**Extreme dates found:** 10

These dates mark unusually large day-to-day moves in the rolling correlation of SOXX and power-producer 20-day volatility. Correlation measures co-movement only. An extreme difference does not by itself show which market caused the other, or the direction of risk transmission.

## Extreme dates (largest \(|\Delta\rho_t|\) first)

| Date | rolling_correlation (`correlation_60`) | successive_difference (`corr_diff`) | absolute_difference (`abs_diff`) |
| --- | ---: | ---: | ---: |
| 2025-01-27 | 0.065207 | 0.504002 | 0.504002 |
| 2023-03-08 | −0.095767 | −0.482431 | 0.482431 |
| 2023-03-07 | 0.386664 | −0.268147 | 0.268147 |
| 2024-12-24 | −0.134645 | −0.212271 | 0.212271 |
| 2025-01-28 | 0.276564 | 0.211357 | 0.211357 |
| 2025-09-04 | −0.299857 | −0.200747 | 0.200747 |
| 2023-09-27 | −0.000240 | −0.194244 | 0.194244 |
| 2023-09-19 | 0.480954 | 0.187957 | 0.187957 |
| 2024-07-31 | 0.183848 | 0.170626 | 0.170626 |
| 2023-09-26 | 0.194004 | −0.168474 | 0.168474 |

## Chronological list (for Finviz / news search)

- 2023-03-07
- 2023-03-08
- 2023-09-19
- 2023-09-26
- 2023-09-27
- 2024-07-31
- 2024-12-24
- 2025-01-27
- 2025-01-28
- 2025-09-04

## Brief summary

Several of the 10 dates form clusters rather than appearing as isolated one-day events: **March 2023** (7–8 Mar), **September 2023** (19, 26–27 Sep), and **January 2025** (27–28 Jan). Standalone extremes also appear on 2024-07-31, 2024-12-24, and 2025-09-04.

The **maximum jump** is on **2025-01-27** (`corr_diff` = +0.504002). The **maximum drop** is on **2023-03-08** (`corr_diff` = −0.482431).

Reproduce the table with:

```bash
python src/extreme_corr_diffs.py
```
