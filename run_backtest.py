"""
Backtesting / A-B test / Optimizer CLI.

Usage examples
--------------
Single run with current .env config:
    python run_backtest.py --mode single --days 90

A/B test (8 predefined strategy variants):
    python run_backtest.py --mode ab --days 180

Grid-search optimizer (top 10 by Sharpe × PF):
    python run_backtest.py --mode optimize --days 180 --top 10
"""

from __future__ import annotations

import argparse
import sys

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

console = Console()


def _fetch_data(days: int):
    from data.fetcher import DataFetcher
    console.print(f"[cyan]Fetching {days} days of {_config().TIMEFRAME} OHLCV data for {_config().SYMBOL}…[/]")
    fetcher = DataFetcher()
    df = fetcher.fetch_historical(days=days)
    console.print(f"[green]  {len(df):,} candles loaded ({df.index[0].date()} → {df.index[-1].date()})[/]\n")
    return df


def _config():
    from config import config
    return config


def _run_single(days: int) -> None:
    from backtest.engine import BacktestConfig, run_backtest
    from backtest.metrics import compute_metrics
    from backtest.report import print_ab_report
    from config import config

    df = _fetch_data(days)
    cfg = BacktestConfig(
        label="Current .env config",
        ema_fast=config.EMA_FAST,
        ema_slow=config.EMA_SLOW,
        ema_signal=config.EMA_SIGNAL,
        tp_long=config.TP_LONG,
        tp_short=config.TP_SHORT,
        hard_cap_multiplier=config.HARD_CAP_MULTIPLIER,
        stop_loss_pct=config.STOP_LOSS_PCT,
        deep_swing=config.DEEP_SWING,
        trade_size_btc=config.TRADE_SIZE_BTC,
        initial_bank=config.INITIAL_BANK,
    )
    result = run_backtest(df, cfg)
    m = compute_metrics(result)
    print_ab_report([(result, m)], title="Single Backtest – Current Config")

    # Detailed trade breakdown
    if result.trades:
        console.print(f"[bold]Trade breakdown:[/] {len(result.trades)} trades")
        reasons: dict[str, int] = {}
        for t in result.trades:
            reasons[t.reason] = reasons.get(t.reason, 0) + 1
        for reason, count in sorted(reasons.items()):
            console.print(f"  {reason:12s}: {count}")


def _run_ab(days: int) -> None:
    from backtest.ab_test import AB_CONFIGS
    from backtest.engine import run_backtest
    from backtest.metrics import compute_metrics
    from backtest.report import print_ab_report

    df = _fetch_data(days)

    results = []
    with Progress(SpinnerColumn(), "[progress.description]{task.description}", BarColumn(),
                  TaskProgressColumn(), TimeElapsedColumn(), console=console) as prog:
        task = prog.add_task("Running A/B configs…", total=len(AB_CONFIGS))
        for cfg in AB_CONFIGS:
            r = run_backtest(df, cfg)
            results.append((r, compute_metrics(r)))
            prog.advance(task)

    results.sort(key=lambda x: x[1].score, reverse=True)
    print_ab_report(results, title=f"A/B Test – {days}-Day Backtest")


def _run_optimize(days: int, top_n: int) -> None:
    from backtest.optimizer import generate_configs, run_optimizer
    from backtest.report import print_optimizer_report

    df = _fetch_data(days)
    configs = generate_configs()
    total = len(configs)
    console.print(f"[cyan]Grid search: {total} valid configurations, running in parallel…[/]\n")

    completed = [0]

    with Progress(SpinnerColumn(), "[progress.description]{task.description}", BarColumn(),
                  TaskProgressColumn(), TimeElapsedColumn(), console=console) as prog:
        task = prog.add_task("Optimizing…", total=total)

        def on_progress(done: int, _total: int) -> None:
            prog.update(task, completed=done)

        top = run_optimizer(df, configs=configs, top_n=top_n, progress_cb=on_progress)

    print_optimizer_report(top, total_configs=total)


def main() -> None:
    parser = argparse.ArgumentParser(description="BTC MACD Bot – Backtester / A-B / Optimizer")
    parser.add_argument("--mode", choices=["single", "ab", "optimize"], default="ab",
                        help="single: one run with .env config | ab: compare presets | optimize: grid search")
    parser.add_argument("--days", type=int, default=180,
                        help="Days of historical data to fetch (default: 180)")
    parser.add_argument("--top", type=int, default=10,
                        help="Top N configs to display in optimizer mode (default: 10)")
    args = parser.parse_args()

    if args.mode == "single":
        _run_single(args.days)
    elif args.mode == "ab":
        _run_ab(args.days)
    else:
        _run_optimize(args.days, args.top)


if __name__ == "__main__":
    main()
