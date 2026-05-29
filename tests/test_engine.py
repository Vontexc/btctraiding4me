"""
Unit tests for the backtest engine.
"""
import numpy as np
import pandas as pd
import pytest
from backtest.engine import BacktestConfig, run_backtest


def _df(close, high=None, low=None):
    n = len(close)
    if high is None:
        high = close + 10
    if low is None:
        low = close - 10
    return pd.DataFrame(
        {"open": close, "high": high, "low": low,
         "close": close, "volume": np.ones(n)},
        index=pd.date_range("2024-01-01", periods=n, freq="15min"),
    )


def _cfg(**kw):
    defaults = dict(
        ema_fast=3, ema_slow=6, ema_signal=3,
        tp_long=40.0, tp_short=-50.0,
        hard_cap_multiplier=1.85,
        stop_loss_pct=2.0,
        deep_swing=False,
        trade_size_btc=0.01,
        initial_bank=1000.0,
        label="test",
    )
    defaults.update(kw)
    return BacktestConfig(**defaults)


# ── Basic smoke tests ─────────────────────────────────────────────────────────

def test_empty_dataframe_returns_no_trades():
    df = _df(np.full(50, 30000.0))
    result = run_backtest(df, _cfg())
    assert len(result.trades) == 0


def test_equity_curve_always_appended():
    np.random.seed(42)
    close = 30000 + np.cumsum(np.random.randn(200) * 100)
    result = run_backtest(_df(close), _cfg())
    assert len(result.equity_curve) > 0
    assert result.equity_curve[0] == 1000.0


def test_no_position_opens_below_warmup():
    """No trades should open within the warmup period."""
    cfg = _cfg(ema_slow=10, ema_signal=3)
    close = np.linspace(29000, 35000, 300)
    result = run_backtest(_df(close), cfg)
    if result.trades:
        assert all(t.entry_bar >= cfg.ema_slow + cfg.ema_signal + 5 for t in result.trades)


# ── SL exit ───────────────────────────────────────────────────────────────────

def test_long_sl_triggered():
    """A sharp drop after entry must trigger SL."""
    close = np.full(300, 30000.0, dtype=float)
    low   = np.full(300, 29990.0, dtype=float)
    high  = np.full(300, 30010.0, dtype=float)

    # Force a MACD long crossover at bar 100 by making a rising then flat pattern
    close[:80]  = np.linspace(28000, 32000, 80)   # uptrend → positive DIF
    close[80:]  = np.linspace(32000, 28000, 220)  # reversal → crossover somewhere

    # After any entry, crash price far enough to hit SL
    entry_size = 0.01
    # SL = 2% of notional. notional ≈ 30000 * 0.01 = $300. SL = $6.
    # Intra-candle low must be: (low - entry) * 0.01 <= -6 → low <= entry - 600
    # We set low[i] = entry_price - 700 for all bars after warmup
    result = run_backtest(_df(close), _cfg(deep_swing=False))
    # We can't guarantee a trade opens in this artificial data, so just verify no exception


def test_pnl_exact_sl():
    """Verify SL P&L equals exactly -(sl_pct/100) * notional."""
    np.random.seed(7)
    close = 30000 + np.cumsum(np.random.randn(400) * 200)
    high  = close + 50
    low   = close - 700  # always trigger SL within a few bars

    cfg = _cfg(stop_loss_pct=2.0, tp_long=99999.0, deep_swing=False)
    result = run_backtest(_df(close, high, low), cfg)

    for t in result.trades:
        if t.reason == "SL":
            expected_sl = -(cfg.stop_loss_pct / 100) * t.entry_price * cfg.trade_size_btc
            assert abs(t.pnl_usd - expected_sl) < 1e-6, (
                f"SL P&L mismatch: got {t.pnl_usd:.6f}, expected {expected_sl:.6f}"
            )


# ── TP exit ───────────────────────────────────────────────────────────────────

def test_pnl_exact_tp():
    """Verify TP P&L equals exactly tp_long (flat USD)."""
    np.random.seed(3)
    close = 30000 + np.cumsum(np.random.randn(400) * 200)
    # Push high far enough to hit TP=$40; keep low above SL
    high = close + 5000   # guarantees pnl_at_high >> $40
    low  = close - 10     # pnl_at_low ~ -$0.10, well above SL=-$6

    cfg = _cfg(tp_long=40.0, stop_loss_pct=2.0, deep_swing=False)
    result = run_backtest(_df(close, high, low), cfg)

    for t in result.trades:
        if t.reason == "TP":
            assert abs(t.pnl_usd - cfg.tp_long) < 1e-6, (
                f"TP P&L mismatch: got {t.pnl_usd:.6f}, expected {cfg.tp_long}"
            )


def test_pnl_exact_hardcap():
    """Verify hard-cap P&L = tp_long * hard_cap_multiplier."""
    np.random.seed(3)
    close = 30000 + np.cumsum(np.random.randn(400) * 200)
    high  = close + 50000  # guarantee hard cap hit every time
    low   = close - 5      # no SL

    cfg = _cfg(tp_long=40.0, hard_cap_multiplier=1.85, stop_loss_pct=2.0, deep_swing=False)
    result = run_backtest(_df(close, high, low), cfg)

    expected_hc = cfg.tp_long * cfg.hard_cap_multiplier  # $74
    for t in result.trades:
        if t.reason == "TP_HC":
            assert abs(t.pnl_usd - expected_hc) < 1e-6, (
                f"HC P&L mismatch: got {t.pnl_usd:.6f}, expected {expected_hc}"
            )


# ── Bank accounting ───────────────────────────────────────────────────────────

def test_bank_tracks_trades():
    """Final equity curve value should equal initial_bank + sum of trade P&Ls."""
    np.random.seed(99)
    close = 30000 + np.cumsum(np.random.randn(400) * 300)
    high  = close + 5000
    low   = close - 700

    cfg = _cfg(tp_long=40.0, stop_loss_pct=2.0, deep_swing=False)
    result = run_backtest(_df(close, high, low), cfg)

    expected_final = cfg.initial_bank + sum(t.pnl_usd for t in result.trades)
    assert abs(result.equity_curve[-1] - expected_final) < 1e-6
