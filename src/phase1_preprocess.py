"""Phase 1: collect prices and build return and volatility series.

Downloads daily adjusted closes for SOXX, CEG, VST, and NRG, keeps the dates
shared by all four, computes daily log returns, forms an equal-weight
power-producer portfolio from CEG, VST, and NRG, and computes 20-day rolling
volatility for SOXX and that portfolio.

This script does not estimate a VAR, compute forecast-error variance
decompositions, measure correlation, or build network graphs.
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yfinance as yf

TICKERS = ["SOXX", "CEG", "VST", "NRG"]
POWER_TICKERS = ["CEG", "VST", "NRG"]
DEFAULT_START = "2022-11-01"
DEFAULT_WINDOW = 20
TRADING_DAYS_PER_YEAR = 252
# Gaps longer than a long weekend are reported as possible missing sessions.
MAX_ORDINARY_GAP_DAYS = 4


def fetch_adjusted_close(ticker: str, start: str, attempts: int = 3) -> pd.Series:
    """Download one ticker's dividend- and split-adjusted daily close."""
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            history = yf.download(
                ticker,
                start=start,
                auto_adjust=True,
                progress=False,
                actions=False,
            )
            if history.empty:
                raise RuntimeError(f"No price data returned for {ticker}")

            close = history["Close"]
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            close = pd.to_numeric(close, errors="coerce")
            close.index = pd.to_datetime(close.index).tz_localize(None).normalize()
            close = close[~close.index.duplicated(keep="last")].sort_index()
            close.name = ticker
            return close
        except Exception as exc:  # retry transient Yahoo / network failures
            last_error = exc
            if attempt < attempts:
                time.sleep(attempt)
    raise RuntimeError(f"Failed to download {ticker} after {attempts} attempts") from last_error


def drop_incomplete_session(prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.Timestamp | None]:
    """Drop today's bar until 16:05 US Eastern, when the regular close is in."""
    if prices.empty:
        return prices, None
    now = datetime.now(ZoneInfo("America/New_York"))
    last = prices.index.max()
    before_close = (now.hour, now.minute) < (16, 5)
    if last.date() == now.date() and before_close:
        return prices.iloc[:-1], last
    return prices, None


def calendar_gaps(index: pd.DatetimeIndex, max_days: int) -> pd.DataFrame:
    """Return consecutive observations separated by more than max_days."""
    if len(index) < 2:
        return pd.DataFrame(columns=["previous_date", "date", "calendar_days"])
    previous = pd.Series(index[:-1], index=index[1:])
    gap_days = (index[1:] - index[:-1]).days
    unusual_mask = gap_days > max_days
    unusual_index = index[1:][unusual_mask]
    return pd.DataFrame(
        {
            "previous_date": previous.loc[unusual_index].dt.date.to_numpy(),
            "date": unusual_index.date,
            "calendar_days": gap_days[unusual_mask].astype(int),
        }
    )


def build_panel(start: str) -> tuple[pd.DataFrame, dict[str, pd.Series], pd.Timestamp | None]:
    raw = {ticker: fetch_adjusted_close(ticker, start) for ticker in TICKERS}
    prices = pd.concat(raw.values(), axis=1, join="outer").reindex(columns=TICKERS)
    prices.index.name = "Date"
    prices, dropped_session = drop_incomplete_session(prices)
    if dropped_session is not None:
        raw = {ticker: series.loc[series.index < dropped_session] for ticker, series in raw.items()}
    return prices, raw, dropped_session


def shared_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """Keep rows where every asset has an adjusted close."""
    complete = prices.dropna(how="any")
    if complete.empty:
        raise RuntimeError("No dates are shared by all four assets")
    return complete


def log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    returns = np.log(prices / prices.shift(1))
    returns = returns.dropna(how="any")
    returns.index.name = "Date"
    return returns


def add_power_portfolio(returns: pd.DataFrame) -> pd.DataFrame:
    """Equal-weight average of the power producers' log returns."""
    out = returns.copy()
    out["power_portfolio"] = out[POWER_TICKERS].mean(axis=1)
    return out


def rolling_volatility(returns: pd.DataFrame, window: int) -> pd.DataFrame:
    """Annualized sample standard deviation of the trailing window of log returns."""
    scale = np.sqrt(TRADING_DAYS_PER_YEAR)
    volatility = pd.DataFrame(
        {
            "SOXX": returns["SOXX"].rolling(window).std() * scale,
            "power_portfolio": returns["power_portfolio"].rolling(window).std() * scale,
        },
        index=returns.index,
    )
    volatility.index.name = "Date"
    return volatility


def format_diagnostics(
    raw: dict[str, pd.Series],
    prices: pd.DataFrame,
    complete: pd.DataFrame,
    returns: pd.DataFrame,
    volatility: pd.DataFrame,
    start: str,
    window: int,
    dropped_session: pd.Timestamp | None,
) -> str:
    missing_counts = prices.isna().sum()
    incomplete_dates = prices.index.difference(complete.index)
    gaps = calendar_gaps(complete.index, MAX_ORDINARY_GAP_DAYS)
    valid_vol = volatility.dropna(how="any")
    lines = [
        "Phase 1 diagnostics",
        f"Generated (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
        f"yfinance: {yf.__version__}",
        f"Requested start: {start}",
        "Adjustment: Yahoo Finance adjusted close (auto_adjust=True)",
        (
            f"Dropped in-progress session: {dropped_session.date()}"
            if dropped_session is not None
            else "Dropped in-progress session: none"
        ),
        "",
        "Download after any in-progress session is removed, before alignment",
    ]
    for ticker in TICKERS:
        series = raw[ticker]
        lines.append(
            f"  {ticker}: {len(series)} observations, "
            f"{series.index.min().date()} to {series.index.max().date()}, "
            f"{int(series.isna().sum())} missing values inside the series"
        )

    lines.extend(
        [
            "",
            f"Outer-joined price rows: {len(prices)}",
            "Missing adjusted closes on the outer join:",
        ]
    )
    for ticker in TICKERS:
        lines.append(f"  {ticker}: {int(missing_counts[ticker])}")
    lines.append(f"Dates not shared by all four assets: {len(incomplete_dates)}")
    if len(incomplete_dates):
        sample = ", ".join(date.strftime("%Y-%m-%d") for date in incomplete_dates[:15])
        suffix = " ..." if len(incomplete_dates) > 15 else ""
        lines.append(f"  First incomplete dates: {sample}{suffix}")

    lines.extend(
        [
            "",
            f"Shared price dates: {len(complete)} "
            f"({complete.index.min().date()} to {complete.index.max().date()})",
            f"Daily log-return observations: {len(returns)} "
            f"({returns.index.min().date()} to {returns.index.max().date()})",
            "Power portfolio: equal-weight average of CEG, VST, and NRG log returns",
            f"Shared-price gaps longer than {MAX_ORDINARY_GAP_DAYS} calendar days: {len(gaps)}",
        ]
    )
    if not gaps.empty:
        for row in gaps.itertuples(index=False):
            lines.append(
                f"  {row.previous_date} -> {row.date} ({row.calendar_days} calendar days)"
            )

    lines.extend(
        [
            "",
            f"Rolling volatility window: {window} trading days",
            "Estimator: sample standard deviation (ddof=1), annualized by sqrt(252)",
            f"Volatility observations with a full window: {len(valid_vol)} "
            f"({valid_vol.index.min().date()} to {valid_vol.index.max().date()})",
            f"Leading volatility rows left blank while the window fills: {window - 1}",
            "",
            "Annualized 20-day volatility summary",
        ]
    )
    summary = valid_vol.agg(["mean", "std", "min", "max"])
    for column in valid_vol.columns:
        stats = summary[column]
        lines.append(
            f"  {column}: mean={stats['mean']:.4f}, std={stats['std']:.4f}, "
            f"min={stats['min']:.4f}, max={stats['max']:.4f}"
        )
    lines.append("")
    return "\n".join(lines)


def save_outputs(
    output_dir: Path,
    complete: pd.DataFrame,
    returns: pd.DataFrame,
    volatility: pd.DataFrame,
    diagnostics: str,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    complete.to_csv(output_dir / "adjusted_close.csv", float_format="%.6f")
    returns.to_csv(output_dir / "log_returns.csv", float_format="%.8f")
    volatility.to_csv(output_dir / "rolling_volatility.csv", float_format="%.8f")
    (output_dir / "phase1_diagnostics.txt").write_text(diagnostics, encoding="utf-8")


def run(start: str, window: int, output_dir: Path) -> str:
    prices, raw, dropped_session = build_panel(start)
    complete = shared_prices(prices)
    returns = add_power_portfolio(log_returns(complete))
    volatility = rolling_volatility(returns, window)

    if complete.isna().any().any():
        raise RuntimeError("Shared price panel still contains missing values")
    if returns.isna().any().any():
        raise RuntimeError("Return panel contains missing values")
    portfolio_error = (
        returns[POWER_TICKERS].mean(axis=1) - returns["power_portfolio"]
    ).abs().max()
    if portfolio_error > 1e-12:
        raise RuntimeError("Power portfolio is not the average of CEG, VST, and NRG")
    if volatility.iloc[window - 1 :].isna().any().any():
        raise RuntimeError("Rolling volatility is missing after the warmup window")

    diagnostics = format_diagnostics(
        raw, prices, complete, returns, volatility, start, window, dropped_session
    )
    save_outputs(output_dir, complete, returns, volatility, diagnostics)
    return diagnostics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default=DEFAULT_START, help="First download date (YYYY-MM-DD)")
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW, help="Rolling window in trading days")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Directory for CSV outputs and the diagnostics report",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.window < 2:
        raise SystemExit("--window must be at least 2")
    print(run(args.start, args.window, args.output_dir))


if __name__ == "__main__":
    main()
