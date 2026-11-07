"""Plot 60-day rolling correlation with extreme shock dates highlighted.

Loads the Phase 2 correlation file, marks days where the absolute successive
difference of correlation_60 exceeds the 99th-percentile threshold of 0.1671,
and saves a figure for visual verification.

Vertical dashed lines and scatter markers show the shock dates. Correlation
measures co-movement only; the markers do not imply causality.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import extreme_corr_diffs

DEFAULT_CORR = Path("data/processed/rolling_correlation.csv")
DEFAULT_FIGURE = Path("figures/rolling_correlation_shocks.png")
THRESHOLD = extreme_corr_diffs.THRESHOLD


def load_correlation_60(path: Path) -> pd.Series:
    """Return the primary 60-day correlation series with blank warmup rows dropped."""
    if not path.exists():
        raise RuntimeError(
            f"Could not find {path}. Run src/phase2_correlation.py "
            "(or src/run_pipeline.py) first."
        )
    corr = pd.read_csv(path, index_col="Date", parse_dates=True)
    if "correlation_60" not in corr.columns:
        raise RuntimeError(f"{path} is missing correlation_60")
    series = corr["correlation_60"].dropna().sort_index()
    series.name = "correlation_60"
    if series.empty:
        raise RuntimeError(f"No complete correlation_60 values in {path}")
    return series


def plot_shocks(
    series: pd.Series,
    shocks: pd.DataFrame,
    figure_path: Path,
    threshold: float,
) -> None:
    """Draw the correlation path with shock dates as dashed lines and points."""
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(
        series.index,
        series.to_numpy(),
        color="#1F4E79",
        linewidth=1.8,
        label="60-day rolling correlation",
        zorder=2,
    )
    ax.axhline(0, color="#666666", linewidth=0.8, linestyle="--", label="Zero correlation")

    # One legend entry for all shock markers.
    first = True
    for date, row in shocks.sort_index().iterrows():
        ax.axvline(
            date,
            color="#C45C26",
            linewidth=0.9,
            linestyle="--",
            alpha=0.75,
            label="Extreme shock date (|Δρ| > 0.1671)" if first else None,
            zorder=1,
        )
        ax.scatter(
            [date],
            [row["correlation_60"]],
            color="#C45C26",
            s=42,
            zorder=3,
            edgecolors="white",
            linewidths=0.6,
        )
        first = False

    ax.set_ylim(-1, 1)
    ax.set_title(
        "60-day rolling correlation with extreme shock dates\n"
        "SOXX and equal-weight power-producer 20-day volatility"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Pearson correlation")
    ax.grid(True, axis="y", color="#E6E6E6")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2)
    fig.text(
        0.5,
        0.02,
        f"Shock dates: |ρ_t − ρ_{{t−1}}| > {threshold:.4f} "
        "(99th percentile of absolute successive differences). "
        "Markers show co-movement jumps, not causality.",
        ha="center",
        fontsize=8,
        color="#444444",
    )
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(figure_path, dpi=150)
    plt.close(fig)


def run(corr_path: Path, figure_path: Path, threshold: float) -> str:
    series = load_correlation_60(corr_path)
    shocks = extreme_corr_diffs.extreme_moves(corr_path, threshold)
    if shocks.empty:
        raise RuntimeError(f"No shock dates exceed |corr_diff| > {threshold}")
    missing = [date for date in shocks.index if date not in series.index]
    if missing:
        raise RuntimeError(f"Shock dates missing from correlation series: {missing}")

    plot_shocks(series, shocks, figure_path, threshold)
    lines = [
        "Rolling correlation shock plot",
        f"Source: {corr_path}",
        f"Complete correlation_60 observations: {len(series)} "
        f"({series.index.min().date()} to {series.index.max().date()})",
        f"Threshold: |corr_diff| > {threshold}",
        f"Shock dates plotted: {len(shocks)}",
    ]
    for date in shocks.sort_index().index:
        value = series.loc[date]
        lines.append(f"  {date.date()}: correlation_60={value:.6f}")
    lines.append(f"Saved figure to {figure_path}")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--correlation",
        type=Path,
        default=DEFAULT_CORR,
        help="Phase 2 rolling-correlation CSV (default: data/processed/rolling_correlation.csv)",
    )
    parser.add_argument(
        "--figure",
        type=Path,
        default=DEFAULT_FIGURE,
        help="Output PNG path (default: figures/rolling_correlation_shocks.png)",
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
    print(run(args.correlation, args.figure, args.threshold))


if __name__ == "__main__":
    main()
