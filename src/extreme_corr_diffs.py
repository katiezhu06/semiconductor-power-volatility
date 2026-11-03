"""List extreme day-to-day moves in the 60-day rolling correlation.

Uses the Phase 2 primary series (correlation_60). A day is extreme when the
absolute successive difference |ρ_t − ρ_{t−1}| exceeds the 99th percentile
threshold of 0.1671 from the difference histogram step.

This is a screening helper for news checks. It does not imply causality.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

DEFAULT_CORR = Path("data/processed/rolling_correlation.csv")
# 99th percentile of |Δρ_t| from the exploratory histogram step.
THRESHOLD = 0.1671


def extreme_moves(corr_path: Path, threshold: float) -> pd.DataFrame:
    corr = pd.read_csv(corr_path, index_col="Date", parse_dates=True)
    if "correlation_60" not in corr.columns:
        raise RuntimeError(f"{corr_path} is missing correlation_60")

    series = corr["correlation_60"].dropna()
    table = pd.DataFrame(
        {
            "Date": series.index,
            "correlation_60": series.to_numpy(),
        }
    ).set_index("Date")
    table["corr_diff"] = table["correlation_60"].diff()
    table["abs_diff"] = table["corr_diff"].abs()
    extreme = table.dropna(subset=["corr_diff"]).loc[table["abs_diff"] > threshold]
    return extreme.sort_values("abs_diff", ascending=False)


def format_table(extreme: pd.DataFrame) -> str:
    display = extreme.reset_index()
    display["Date"] = display["Date"].dt.strftime("%Y-%m-%d")
    display["correlation_60"] = display["correlation_60"].map(lambda x: f"{x: .6f}")
    display["corr_diff"] = display["corr_diff"].map(lambda x: f"{x: .6f}")
    display["abs_diff"] = display["abs_diff"].map(lambda x: f"{x:.6f}")
    return display.to_string(index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--correlation",
        type=Path,
        default=DEFAULT_CORR,
        help="Phase 2 rolling-correlation CSV",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=THRESHOLD,
        help="Absolute successive-difference cutoff (default: 0.1671)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    extreme = extreme_moves(args.correlation, args.threshold)
    print(
        "Extreme successive differences in 60-day rolling correlation\n"
        f"Source: {args.correlation}\n"
        f"Rule: |corr_diff| > {args.threshold}\n"
        f"Extreme dates: {len(extreme)}\n"
    )
    if extreme.empty:
        print("No dates exceed this threshold.")
        return
    print(format_table(extreme))
    print("\nDates only (for Finviz / news search):")
    for date in extreme.index.sort_values():
        print(date.strftime("%Y-%m-%d"))


if __name__ == "__main__":
    main()
