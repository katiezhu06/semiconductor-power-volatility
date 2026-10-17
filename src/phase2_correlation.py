"""Phase 2: rolling correlation of SOXX and power-producer volatility.

Loads the 20-day rolling volatility series from Phase 1, keeps dates where
both series are observed, and computes rolling Pearson correlations. The
primary window is 60 trading days. Windows of 40 and 90 trading days are
sensitivity checks.

On each date, the correlation uses the two volatility readings from that date
and the previous dates in the window. A value near 1 means the two volatilities
were high together and low together. A value near 0 means little linear
co-movement, and a value near -1 means they moved in opposite directions.

Correlation measures co-movement only. It does not show which series causes
the other, or the direction of risk transmission.

This script does not estimate a VAR, compute forecast-error variance
decompositions, or build network graphs.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

VOLATILITY_COLUMNS = ["SOXX", "power_portfolio"]
WINDOWS = (40, 60, 90)
PRIMARY_WINDOW = 60
DEFAULT_VOLATILITY = Path("data/rolling_volatility.csv")
DEFAULT_OUTPUT = Path("data/processed/rolling_correlation.csv")
DEFAULT_FIGURE = Path("figures/rolling_correlation.png")


def load_volatility(path: Path) -> pd.DataFrame:
    """Read the Phase 1 volatility file and keep the two series used here."""
    if not path.exists():
        raise RuntimeError(
            f"Could not find {path}. Run src/phase1_preprocess.py first."
        )
    volatility = pd.read_csv(path, index_col="Date", parse_dates=True)
    missing = [column for column in VOLATILITY_COLUMNS if column not in volatility.columns]
    if missing:
        raise RuntimeError(f"Volatility file is missing columns: {missing}")
    panel = volatility[VOLATILITY_COLUMNS].sort_index()
    panel = panel[~panel.index.duplicated(keep="last")]
    panel.index.name = "Date"
    return panel


def align_volatility(volatility: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Keep dates where both volatility series are present."""
    dropped = int(volatility.isna().any(axis=1).sum())
    aligned = volatility.dropna(how="any")
    if aligned.empty:
        raise RuntimeError("No dates have both SOXX and power-portfolio volatility")
    return aligned, dropped


def rolling_correlation(volatility: pd.DataFrame, window: int) -> pd.Series:
    """Pearson correlation of the two volatilities over the last `window` dates.

    Dates before the window is full are left blank. Pandas computes the ordinary
    correlation of the paired SOXX and power-portfolio values inside the window.
    """
    series = volatility["SOXX"].rolling(window).corr(volatility["power_portfolio"])
    series.name = f"correlation_{window}"
    return series


def correlation_table(volatility: pd.DataFrame, windows: list[int]) -> pd.DataFrame:
    """One column per window, indexed by the same dates as the aligned volatility."""
    columns = [rolling_correlation(volatility, window) for window in windows]
    table = pd.concat(columns, axis=1)
    table.index.name = "Date"
    return table


def format_summary(
    aligned: pd.DataFrame,
    correlations: pd.DataFrame,
    dropped: int,
    primary_window: int,
) -> str:
    """Plain-text description of the sample and each correlation series."""
    lines = [
        "Phase 2 rolling correlation",
        f"Aligned volatility observations: {len(aligned)} "
        f"({aligned.index.min().date()} to {aligned.index.max().date()})",
        f"Rows dropped because SOXX or power-portfolio volatility was missing: {dropped}",
        "Correlation: Pearson correlation of the paired volatility observations",
        f"Primary window: {primary_window} observations",
        "",
    ]
    for column in correlations.columns:
        window = int(column.removeprefix("correlation_"))
        series = correlations[column].dropna()
        role = "primary" if window == primary_window else "sensitivity"
        if series.empty:
            lines.append(f"{column} ({role}): no complete windows")
            continue
        lines.extend(
            [
                f"{column} ({role})",
                f"  Complete windows: {len(series)} "
                f"({series.index.min().date()} to {series.index.max().date()})",
                f"  Blank while the window fills: {window - 1}",
                f"  Mean: {series.mean():.3f}",
                f"  Min: {series.min():.3f} on {series.idxmin().date()}",
                f"  Max: {series.max():.3f} on {series.idxmax().date()}",
                f"  Share above zero: {(series > 0).mean():.1%}",
            ]
        )
        if len(series) >= 2 * 252:
            early = series.iloc[:252]
            late = series.iloc[-252:]
            lines.append(
                f"  Mean of earliest 252 complete windows: {early.mean():.3f} "
                f"({early.index.min().date()} to {early.index.max().date()})"
            )
            lines.append(
                f"  Mean of latest 252 complete windows: {late.mean():.3f} "
                f"({late.index.min().date()} to {late.index.max().date()})"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def plot_correlations(
    correlations: pd.DataFrame,
    figure_path: Path,
    primary_window: int,
) -> None:
    """Save a time plot with the primary window drawn over the sensitivity checks."""
    styles = {
        "correlation_40": {
            "label": "40 trading days (sensitivity)",
            "color": "#5B8FA8",
            "linewidth": 1.15,
        },
        "correlation_90": {
            "label": "90 trading days (sensitivity)",
            "color": "#C47B2B",
            "linewidth": 1.15,
        },
        "correlation_60": {
            "label": "60 trading days (primary)",
            "color": "#1F4E79",
            "linewidth": 2.2,
        },
    }
    primary_column = f"correlation_{primary_window}"
    # Draw the primary series last so its line sits on top of the sensitivity checks.
    columns = [column for column in correlations.columns if column != primary_column]
    if primary_column in correlations.columns:
        columns.append(primary_column)

    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    for column in columns:
        series = correlations[column].dropna()
        window = column.removeprefix("correlation_")
        style = styles.get(
            column,
            {"label": f"{window} trading days", "color": "#444444", "linewidth": 1.2},
        )
        ax.plot(series.index, series.to_numpy(), **style)

    ax.axhline(0, color="#666666", linewidth=0.8, linestyle="--", label="Zero correlation")
    ax.set_ylim(-1, 1)
    ax.set_title(
        "Rolling correlation of 20-day volatility\n"
        "SOXX and the equal-weight power-producer portfolio"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Pearson correlation")
    ax.grid(True, axis="y", color="#E6E6E6")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2)
    fig.text(
        0.5,
        0.02,
        "Each point uses the trailing window of volatility observations. "
        "Correlation measures co-movement, not causality or the direction of risk transmission.",
        ha="center",
        fontsize=8,
        color="#444444",
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(figure_path, dpi=150)
    plt.close(fig)


def check_results(aligned: pd.DataFrame, correlations: pd.DataFrame, windows: list[int]) -> None:
    """Stop if a complete window is outside the correlation bounds or is missing."""
    if len(aligned) < max(windows):
        raise RuntimeError(
            f"Need at least {max(windows)} aligned observations; found {len(aligned)}"
        )
    for window in windows:
        column = f"correlation_{window}"
        series = correlations[column]
        if series.iloc[: window - 1].notna().any():
            raise RuntimeError(f"{column} is filled before the window has {window} observations")
        complete = series.iloc[window - 1 :]
        if complete.isna().any():
            raise RuntimeError(f"{column} is missing after the window is full")
        if ((complete < -1.0000001) | (complete > 1.0000001)).any():
            raise RuntimeError(f"{column} has a value outside [-1, 1]")


def save_correlations(correlations: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    correlations.to_csv(path, float_format="%.6f")


def run(
    volatility_path: Path,
    output_path: Path,
    figure_path: Path,
    windows: list[int],
    primary_window: int,
) -> str:
    aligned, dropped = align_volatility(load_volatility(volatility_path))
    correlations = correlation_table(aligned, windows)
    check_results(aligned, correlations, windows)
    save_correlations(correlations, output_path)
    plot_correlations(correlations, figure_path, primary_window)
    summary = format_summary(aligned, correlations, dropped, primary_window)
    summary += f"\nSaved correlations to {output_path}\nSaved figure to {figure_path}\n"
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--volatility",
        type=Path,
        default=DEFAULT_VOLATILITY,
        help="Phase 1 rolling-volatility CSV",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="CSV path for the rolling correlations",
    )
    parser.add_argument(
        "--figure",
        type=Path,
        default=DEFAULT_FIGURE,
        help="PNG path for the correlation plot",
    )
    parser.add_argument(
        "--windows",
        type=int,
        nargs="+",
        default=list(WINDOWS),
        help="Trailing windows in observations (default: 40 60 90)",
    )
    parser.add_argument(
        "--primary",
        type=int,
        default=PRIMARY_WINDOW,
        help="Window to treat as the primary estimate in the summary and plot",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    windows = list(dict.fromkeys(args.windows))
    if not windows or any(window < 2 for window in windows):
        raise SystemExit("Each window must be at least 2 observations")
    if args.primary not in windows:
        raise SystemExit("--primary must be one of the windows")
    print(run(args.volatility, args.output, args.figure, windows, args.primary))


if __name__ == "__main__":
    main()
