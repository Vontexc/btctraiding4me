"""
Unit tests for position tracking and P&L calculation.
"""
import pytest
from bot.position import Position, PositionTracker
from bot.signal import Signal


def test_long_pnl_positive():
    pos = Position(side=Signal.LONG, entry_price=30000.0, size_btc=0.01)
    pos.update(31000.0)
    assert abs(pos.unrealised_pnl - 10.0) < 1e-6


def test_long_pnl_negative():
    pos = Position(side=Signal.LONG, entry_price=30000.0, size_btc=0.01)
    pos.update(29000.0)
    assert abs(pos.unrealised_pnl - (-10.0)) < 1e-6


def test_short_pnl_positive():
    pos = Position(side=Signal.SHORT, entry_price=30000.0, size_btc=0.01)
    pos.update(29000.0)
    assert abs(pos.unrealised_pnl - 10.0) < 1e-6


def test_short_pnl_negative():
    pos = Position(side=Signal.SHORT, entry_price=30000.0, size_btc=0.01)
    pos.update(31000.0)
    assert abs(pos.unrealised_pnl - (-10.0)) < 1e-6


def test_peak_pnl_only_rises():
    pos = Position(side=Signal.LONG, entry_price=30000.0, size_btc=0.01)
    pos.update(31000.0)  # peak = 10
    pos.update(30500.0)  # unrealised = 5, peak stays 10
    assert abs(pos.peak_pnl - 10.0) < 1e-6
    assert abs(pos.unrealised_pnl - 5.0) < 1e-6


def test_pnl_pct_calculation():
    pos = Position(side=Signal.LONG, entry_price=30000.0, size_btc=0.01)
    pos.update(33000.0)  # +$30 on $300 notional = +10%
    assert abs(pos.pnl_pct - 10.0) < 1e-4


def test_tracker_session_pnl():
    tracker = PositionTracker()
    tracker.open(Signal.LONG, 30000.0, 0.01)
    tracker.close(25.0)
    tracker.open(Signal.SHORT, 31000.0, 0.01)
    tracker.close(-5.0)
    assert abs(tracker.session_pnl - 20.0) < 1e-6


def test_tracker_win_loss_count():
    tracker = PositionTracker()
    for pnl in [10.0, 20.0, -5.0]:
        tracker.open(Signal.LONG, 30000.0, 0.01)
        tracker.close(pnl)
    assert tracker.wins == 2
    assert tracker.losses == 1


def test_tracker_win_rate():
    tracker = PositionTracker()
    for pnl in [10.0, 10.0, 10.0, -5.0]:
        tracker.open(Signal.LONG, 30000.0, 0.01)
        tracker.close(pnl)
    assert abs(tracker.win_rate - 75.0) < 1e-6


def test_tracker_is_open_flag():
    tracker = PositionTracker()
    assert not tracker.is_open
    tracker.open(Signal.LONG, 30000.0, 0.01)
    assert tracker.is_open
    tracker.close(5.0)
    assert not tracker.is_open
