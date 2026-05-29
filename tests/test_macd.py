"""
Unit tests for MACD calculation.
"""
import numpy as np
import pandas as pd
import pytest
from bot.macd import calculate_macd, MACDResult


def _make_df(close_values):
    df = pd.DataFrame(
        {"open": close_values, "high": close_values, "low": close_values,
         "close": close_values, "volume": np.ones(len(close_values))},
        index=pd.date_range("2024-01-01", periods=len(close_values), freq="15min"),
    )
    return df


def test_macd_returns_macd_result():
    close = np.linspace(30000, 31000, 100)
    result = calculate_macd(_make_df(close))
    assert isinstance(result, MACDResult)


def test_macd_uptrend_dif_positive():
    """Steady uptrend → fast EMA > slow EMA → DIF positive."""
    close = np.linspace(25000, 40000, 200)
    result = calculate_macd(_make_df(close))
    assert result.dif > 0, f"Expected DIF > 0 in uptrend, got {result.dif}"


def test_macd_downtrend_dif_negative():
    """Steady downtrend → fast EMA < slow EMA → DIF negative."""
    close = np.linspace(40000, 25000, 200)
    result = calculate_macd(_make_df(close))
    assert result.dif < 0, f"Expected DIF < 0 in downtrend, got {result.dif}"


def test_macd_prev_values_differ():
    """prev_* fields should differ from current fields in non-flat series."""
    close = 30000 + np.cumsum(np.random.default_rng(0).normal(0, 100, 150))
    result = calculate_macd(_make_df(close))
    assert result.dif != result.prev_dif or result.histogram != result.prev_histogram


def test_histogram_equals_dif_minus_dea():
    close = np.linspace(30000, 35000, 150)
    r = calculate_macd(_make_df(close))
    assert abs(r.histogram - (r.dif - r.dea)) < 1e-9
    assert abs(r.prev_histogram - (r.prev_dif - r.prev_dea)) < 1e-9
