from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from backtest.engine import BacktestResult


@dataclass
class Metrics:
    total_pnl: float
    total_return_pct: float
    num_trades: int
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe: float
    avg_duration_bars: float

    @property
    def score(self) -> float:
        """Composite rank score: Sharpe weighted by profit factor."""
        return self.sharpe * min(self.profit_factor, 5.0)


_CANDLES_PER_YEAR_15M = 35_040  # 365 * 24 * 4


def compute_metrics(result: BacktestResult) -> Metrics:
    trades = result.trades
    initial = result.config.initial_bank

    if not trades:
        return Metrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    wins = [t.pnl_usd for t in trades if t.pnl_usd > 0]
    losses = [t.pnl_usd for t in trades if t.pnl_usd <= 0]

    total_pnl = sum(t.pnl_usd for t in trades)
    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0

    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    avg_win = gross_profit / len(wins) if wins else 0.0
    avg_loss = gross_loss / len(losses) if losses else 0.0
    avg_duration = float(np.mean([t.duration_bars for t in trades]))

    # Max drawdown from equity curve
    equity = np.array(result.equity_curve, dtype=float)
    peak = np.maximum.accumulate(equity)
    drawdown = peak - equity
    max_dd = float(drawdown.max())
    max_dd_pct = (max_dd / initial) * 100 if initial > 0 else 0.0

    # Annualised Sharpe on per-trade percentage returns
    rets = np.array([t.return_pct for t in trades])
    if len(rets) > 1 and rets.std() > 0:
        trades_per_year = _CANDLES_PER_YEAR_15M / max(avg_duration, 1)
        sharpe = (rets.mean() / rets.std()) * np.sqrt(trades_per_year)
    else:
        sharpe = 0.0

    return Metrics(
        total_pnl=total_pnl,
        total_return_pct=(total_pnl / initial) * 100,
        num_trades=len(trades),
        win_rate=len(wins) / len(trades) * 100,
        profit_factor=profit_factor,
        avg_win=avg_win,
        avg_loss=avg_loss,
        max_drawdown=max_dd,
        max_drawdown_pct=max_dd_pct,
        sharpe=sharpe,
        avg_duration_bars=avg_duration,
    )
