"""Run Phase 1 and Phase 2 as one pipeline.

Phase 1 downloads prices and builds the return and volatility series. Phase 2
reads that volatility series and calculates rolling correlations. Both stages
write into a new folder, data/phase1/run_N. The next execution uses run_{N+1}
and leaves the earlier folder in place.

Correlation measures co-movement only. This script does not estimate a VAR,
compute forecast-error variance decompositions, or build network graphs.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import phase1_preprocess
import phase2_correlation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--start",
        default=phase1_preprocess.DEFAULT_START,
        help="First download date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=phase1_preprocess.DEFAULT_WINDOW,
        help="Rolling volatility window in trading days",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=phase2_correlation.DEFAULT_DATA_ROOT,
        help="Root directory. Each run is saved in phase1/run_N under this directory",
    )
    parser.add_argument(
        "--windows",
        type=int,
        nargs="+",
        default=list(phase2_correlation.WINDOWS),
        help="Correlation windows in observations (default: 40 60 90)",
    )
    parser.add_argument(
        "--primary",
        type=int,
        default=phase2_correlation.PRIMARY_WINDOW,
        help="Correlation window to treat as the primary estimate",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    windows = list(dict.fromkeys(args.windows))
    if args.window < 2:
        raise SystemExit("--window must be at least 2")
    if not windows or any(window < 2 for window in windows):
        raise SystemExit("Each correlation window must be at least 2 observations")
    if args.primary not in windows:
        raise SystemExit("--primary must be one of --windows")
    print(
        phase2_correlation.run_after_phase1(
            args.start,
            args.window,
            args.data_root,
            windows,
            args.primary,
        )
    )


if __name__ == "__main__":
    main()
