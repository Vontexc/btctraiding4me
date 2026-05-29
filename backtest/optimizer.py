"""
Grid-search optimizer.

Generates all BacktestConfig combinations from GRID, runs them in parallel
using ProcessPoolExecutor, and returns results ranked by Sharpe × profit_factor.
"""

from __future__ import annotations

import itertools
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Iterator

import pandas as pd

from backtest.engine import BacktestConfig, BacktestResult, run_backtest
from backtest.metrics import Metrics, compute_metrics

# Grid definition — extend or shrink to trade coverage vs. runtime
GRID: dict[str, list] = {
    "ema_fast":           [8, 12, 14],
    "ema_slow":           [21, 26, 30],
    "ema_signal":         [7, 9],
    "tp_long":            [30, 40, 55],
    "stop_loss_pct":      [1.5, 2.0, 2.5],
    "deep_swing":         [True, False],
}

# Parameters held constant during grid search
FIXED: dict = {
    "tp_short":           -50.0,
    "hard_cap_multiplier": 1.85,
    "trade_size_btc":      0.01,
    "initial_bank":        1000.0,
}


def _is_valid(cfg: dict) -> bool:
    """Skip configurations where EMA fast >= slow."""
    return cfg["ema_fast"] < cfg["ema_slow"]


def generate_configs() -> list[BacktestConfig]:
    keys = list(GRID.keys())
    combos = itertools.product(*GRID.values())
    configs = []
    for values in combos:
        params = dict(zip(keys, values))
        if not _is_valid(params):
            continue
        params.update(FIXED)
        configs.append(BacktestConfig(**params))
    return configs


def _worker(args: tuple[BacktestConfig, pd.DataFrame]) -> tuple[BacktestResult, Metrics]:
    cfg, df = args
    result = run_backtest(df, cfg)
    return result, compute_metrics(result)


def run_optimizer(
    df: pd.DataFrame,
    configs: list[BacktestConfig] | None = None,
    top_n: int = 10,
    progress_cb: callable | None = None,
) -> list[tuple[BacktestResult, Metrics]]:
    """
    Run all configs against df in parallel.
    Returns the top_n results sorted by Metrics.score (Sharpe × PF).
    """
    if configs is None:
        configs = generate_configs()

    workers = min(os.cpu_count() or 4, len(configs))
    results: list[tuple[BacktestResult, Metrics]] = []

    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_worker, (cfg, df)): cfg for cfg in configs}
        done = 0
        for future in as_completed(futures):
            done += 1
            if progress_cb:
                progress_cb(done, len(configs))
            try:
                results.append(future.result())
            except Exception:
                pass

    results.sort(key=lambda x: x[1].score, reverse=True)
    return results[:top_n]
