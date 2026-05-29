"""
Unit tests for the metrics module.
"""
import pytest
from backtest.engine import BacktestConfig, BacktestResult, TradeRecord
from backtest.metrics import compute_metrics


def _cfg():
    return BacktestConfig(label="test", initial_bank=1000.0)


def _trade(pnl, side="LONG", reason="TP", bars=10):
    entry = 30000.0
    return TradeRecord(
        side=side, entry_price=entry, exit_price=entry + 100,
        size_btc=0.01, pnl_usd=pnl,
        entry_bar=0, exit_bar=bars, reason=reason,
    )


def _result(pnls, initial=1000.0):
    cfg = BacktestConfig(label="test", initial_bank=initial)
    bank = initial
    equity = [bank]
    trades = []
    for pnl in pnls:
        trades.append(_trade(pnl))
        bank += pnl
        equity.append(bank)
    r = BacktestResult(config=cfg, trades=trades, equity_curve=equity)
    return r


# ── Empty result ──────────────────────────────────────────────────────────────

def test_empty_result_all_zeros():
    r = BacktestResult(config=_cfg(), trades=[], equity_curve=[1000.0])
    m = compute_metrics(r)
    assert m.num_trades == 0
    assert m.total_pnl == 0
    assert m.sharpe == 0.0
    assert m.max_drawdown == 0.0


# ── Win rate ──────────────────────────────────────────────────────────────────

def test_win_rate_all_wins():
    m = compute_metrics(_result([10, 20, 30]))
    assert abs(m.win_rate - 100.0) < 1e-6


def test_win_rate_all_losses():
    m = compute_metrics(_result([-5, -3, -7]))
    assert abs(m.win_rate - 0.0) < 1e-6


def test_win_rate_mixed():
    m = compute_metrics(_result([10, 10, 10, -5]))  # 3 wins, 1 loss → 75%
    assert abs(m.win_rate - 75.0) < 1e-6


# ── Profit factor ─────────────────────────────────────────────────────────────

def test_profit_factor_three_to_one():
    # $30 gross profit, $10 gross loss → PF = 3.0
    m = compute_metrics(_result([10, 20, -10]))
    assert abs(m.profit_factor - 3.0) < 1e-6


def test_profit_factor_no_losses_is_inf():
    m = compute_metrics(_result([10, 20, 30]))
    assert m.profit_factor == float("inf")


def test_profit_factor_no_wins_is_zero():
    m = compute_metrics(_result([-5, -3]))
    assert m.profit_factor == 0.0


# ── Total P&L and return ──────────────────────────────────────────────────────

def test_total_pnl():
    m = compute_metrics(_result([10, -3, 7]))
    assert abs(m.total_pnl - 14.0) < 1e-6


def test_total_return_pct():
    m = compute_metrics(_result([100], initial=1000.0))
    assert abs(m.total_return_pct - 10.0) < 1e-6


# ── Max drawdown ──────────────────────────────────────────────────────────────

def test_max_drawdown_simple():
    # equity: [1000, 1020, 1010, 990] → peak=1020 → DD=30
    m = compute_metrics(_result([20, -10, -20]))
    assert abs(m.max_drawdown - 30.0) < 1e-6


def test_max_drawdown_zero_when_only_wins():
    m = compute_metrics(_result([10, 20, 30]))
    assert m.max_drawdown == 0.0


# ── Avg win / avg loss ────────────────────────────────────────────────────────

def test_avg_win():
    m = compute_metrics(_result([10, 30, -5]))  # wins: 10, 30 → avg=20
    assert abs(m.avg_win - 20.0) < 1e-6


def test_avg_loss():
    m = compute_metrics(_result([10, -6, -4]))  # losses: 6, 4 → avg=5
    assert abs(m.avg_loss - 5.0) < 1e-6
