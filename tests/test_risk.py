"""
Unit tests for risk management (TP / SL / Hard Cap / Deep Swing).
Uses a patched config so tests are independent of .env values.
"""
import os
import pytest
from unittest.mock import patch
from bot.macd import MACDResult
from bot.position import Position
from bot.risk import check_exit, CloseReason
from bot.signal import Signal

# ── Helpers ──────────────────────────────────────────────────────────────────

ENTRY = 30000.0
SIZE  = 0.01
# notional = 30000 * 0.01 = $300
# TP_LONG  = $40 flat   → HC = $74   SL = 2% of $300 = $6
# TP_SHORT = $50 flat   → HC = $92.5


def _pos(side: Signal, pnl_override: float) -> Position:
    """Build a position whose unrealised_pnl equals pnl_override."""
    pos = Position(side=side, entry_price=ENTRY, size_btc=SIZE)
    pos.unrealised_pnl = pnl_override
    return pos


def _macd(hist: float) -> MACDResult:
    return MACDResult(dif=hist, dea=0.0, histogram=hist,
                      prev_dif=0.0, prev_dea=0.0, prev_histogram=0.0)


MOCK_CFG = dict(TP_LONG=40.0, TP_SHORT=-50.0, HARD_CAP_MULTIPLIER=1.85,
                STOP_LOSS_PCT=2.0, DEEP_SWING=True)


def patch_cfg(**overrides):
    cfg = {**MOCK_CFG, **overrides}
    return patch.multiple("bot.risk.config", **cfg)


# ── LONG tests ───────────────────────────────────────────────────────────────

def test_long_tp_exact():
    with patch_cfg():
        close, reason = check_exit(_pos(Signal.LONG, 40.0), ENTRY * 1.133, _macd(-0.1))
    assert close and reason == CloseReason.TP


def test_long_tp_above():
    with patch_cfg():
        close, reason = check_exit(_pos(Signal.LONG, 45.0), ENTRY * 1.15, _macd(-0.1))
    assert close and reason == CloseReason.TP


def test_long_deep_swing_holds_while_histogram_positive():
    with patch_cfg(DEEP_SWING=True):
        close, _ = check_exit(_pos(Signal.LONG, 45.0), ENTRY * 1.15, _macd(0.5))
    assert not close  # histogram still positive → keep holding


def test_long_deep_swing_exits_on_histogram_flip():
    with patch_cfg(DEEP_SWING=True):
        close, reason = check_exit(_pos(Signal.LONG, 45.0), ENTRY * 1.15, _macd(-0.1))
    assert close and reason == CloseReason.TP


def test_long_no_deep_swing_exits_at_tp():
    with patch_cfg(DEEP_SWING=False):
        close, reason = check_exit(_pos(Signal.LONG, 40.0), ENTRY * 1.133, _macd(0.5))
    assert close and reason == CloseReason.TP


def test_long_hard_cap():
    hc = 40.0 * 1.85  # $74
    with patch_cfg():
        close, reason = check_exit(_pos(Signal.LONG, hc + 1), ENTRY * 1.25, _macd(1.0))
    assert close and reason == CloseReason.TP


def test_long_sl_trigger():
    sl = -(2.0 / 100) * (ENTRY * SIZE)  # -$6
    with patch_cfg():
        close, reason = check_exit(_pos(Signal.LONG, sl - 0.01), ENTRY * 0.98, _macd(0.0))
    assert close and reason == CloseReason.SL


def test_long_below_tp_no_exit():
    with patch_cfg():
        close, _ = check_exit(_pos(Signal.LONG, 15.0), ENTRY * 1.05, _macd(0.3))
    assert not close


def test_long_above_sl_no_exit():
    with patch_cfg():
        close, _ = check_exit(_pos(Signal.LONG, -3.0), ENTRY * 0.99, _macd(0.0))
    assert not close


# ── SHORT tests ──────────────────────────────────────────────────────────────

def test_short_tp_exact():
    with patch_cfg():
        close, reason = check_exit(_pos(Signal.SHORT, 50.0), ENTRY * 0.833, _macd(0.1))
    assert close and reason == CloseReason.TP


def test_short_hard_cap():
    hc = 50.0 * 1.85  # $92.5
    with patch_cfg():
        close, reason = check_exit(_pos(Signal.SHORT, hc + 1), ENTRY * 0.7, _macd(-1.0))
    assert close and reason == CloseReason.TP


def test_short_sl_trigger():
    sl = -(2.0 / 100) * (ENTRY * SIZE)  # -$6
    with patch_cfg():
        close, reason = check_exit(_pos(Signal.SHORT, sl - 0.01), ENTRY * 1.02, _macd(0.0))
    assert close and reason == CloseReason.SL


def test_short_deep_swing_holds_while_histogram_negative():
    with patch_cfg(DEEP_SWING=True):
        close, _ = check_exit(_pos(Signal.SHORT, 55.0), ENTRY * 0.8, _macd(-0.5))
    assert not close


def test_short_deep_swing_exits_on_histogram_flip():
    with patch_cfg(DEEP_SWING=True):
        close, reason = check_exit(_pos(Signal.SHORT, 55.0), ENTRY * 0.8, _macd(0.1))
    assert close and reason == CloseReason.TP
