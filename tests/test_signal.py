"""
Unit tests for signal crossover detection.
"""
import pytest
from bot.macd import MACDResult
from bot.signal import Signal, evaluate_signal


def _macd(prev_hist, curr_hist):
    return MACDResult(
        dif=curr_hist + 1, dea=1.0, histogram=curr_hist,
        prev_dif=prev_hist + 1, prev_dea=1.0, prev_histogram=prev_hist,
    )


def test_long_on_crossover_up():
    assert evaluate_signal(_macd(-0.5, 0.1)) == Signal.LONG


def test_short_on_crossover_down():
    assert evaluate_signal(_macd(0.5, -0.1)) == Signal.SHORT


def test_no_signal_both_positive():
    assert evaluate_signal(_macd(0.3, 0.5)) == Signal.NONE


def test_no_signal_both_negative():
    assert evaluate_signal(_macd(-0.3, -0.1)) == Signal.NONE


def test_no_signal_zero_to_zero():
    assert evaluate_signal(_macd(0.0, 0.0)) == Signal.NONE


def test_crossover_exactly_at_zero_prev_zero():
    """prev_histogram == 0 counts as non-positive → Long on move above zero."""
    assert evaluate_signal(_macd(0.0, 0.01)) == Signal.LONG


def test_short_crossover_exactly_at_zero_prev_zero():
    """prev_histogram == 0 counts as non-negative → Short on move below zero."""
    assert evaluate_signal(_macd(0.0, -0.01)) == Signal.SHORT
