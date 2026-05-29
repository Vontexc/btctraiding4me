"""
Rich terminal reports for A/B tests and optimizer results.
"""

from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich import box

from backtest.engine import BacktestResult
from backtest.metrics import Metrics

console = Console()


def _pnl_style(val: float) -> str:
    return "bold green" if val > 0 else ("bold red" if val < 0 else "white")


def _rank_medal(rank: int) -> str:
    return {1: "🥇 ", 2: "🥈 ", 3: "🥉 "}.get(rank, f"  {rank}. ")


def print_ab_report(
    results: list[tuple[BacktestResult, Metrics]],
    title: str = "A/B Test Results",
) -> None:
    table = Table(
        title=title,
        box=box.ROUNDED,
        show_lines=True,
        highlight=True,
    )

    table.add_column("Rank", justify="center", style="bold", width=4)
    table.add_column("Configuration", min_width=40)
    table.add_column("P&L", justify="right", min_width=10)
    table.add_column("Return", justify="right", min_width=8)
    table.add_column("Trades", justify="right", min_width=7)
    table.add_column("Win%", justify="right", min_width=6)
    table.add_column("PF", justify="right", min_width=5)
    table.add_column("Sharpe", justify="right", min_width=7)
    table.add_column("MaxDD", justify="right", min_width=8)
    table.add_column("Avg Win", justify="right", min_width=8)
    table.add_column("Avg Loss", justify="right", min_width=9)

    for rank, (result, m) in enumerate(results, 1):
        pnl_s = _pnl_style(m.total_pnl)
        pf_str = f"{m.profit_factor:.2f}" if m.profit_factor != float("inf") else "∞"
        table.add_row(
            _rank_medal(rank),
            result.config.label,
            f"[{pnl_s}]${m.total_pnl:+.2f}[/]",
            f"[{pnl_s}]{m.total_return_pct:+.1f}%[/]",
            str(m.num_trades),
            f"{m.win_rate:.1f}%",
            pf_str,
            f"{m.sharpe:.2f}",
            f"[red]${m.max_drawdown:.2f}[/]",
            f"[green]${m.avg_win:.2f}[/]",
            f"[red]${m.avg_loss:.2f}[/]",
        )

    console.print()
    console.print(table)
    console.print()


def print_optimizer_report(
    results: list[tuple[BacktestResult, Metrics]],
    total_configs: int,
) -> None:
    console.print(f"\n[bold cyan]Grid Search complete.[/] "
                  f"Evaluated [bold]{total_configs}[/] configs, showing top [bold]{len(results)}[/].\n")
    print_ab_report(results, title="Optimizer – Top Configurations (ranked by Sharpe × PF)")
