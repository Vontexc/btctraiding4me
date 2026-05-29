"""
Pre-defined A/B test configurations.

Each entry represents a distinct strategy variant to compare head-to-head
on the same historical dataset.
"""

from backtest.engine import BacktestConfig

AB_CONFIGS: list[BacktestConfig] = [
    BacktestConfig(
        label="Default  (12/26/9 · TP40/-50 · SL2% · DS)",
        ema_fast=12, ema_slow=26, ema_signal=9,
        tp_long=40, tp_short=-50,
        stop_loss_pct=2.0, hard_cap_multiplier=1.85, deep_swing=True,
    ),
    BacktestConfig(
        label="Conservative (12/26/9 · TP30/-40 · SL1.5% · NoDS)",
        ema_fast=12, ema_slow=26, ema_signal=9,
        tp_long=30, tp_short=-40,
        stop_loss_pct=1.5, hard_cap_multiplier=1.5, deep_swing=False,
    ),
    BacktestConfig(
        label="Aggressive   (12/26/9 · TP60/-70 · SL3% · DS)",
        ema_fast=12, ema_slow=26, ema_signal=9,
        tp_long=60, tp_short=-70,
        stop_loss_pct=3.0, hard_cap_multiplier=2.0, deep_swing=True,
    ),
    BacktestConfig(
        label="Fast MACD    (8/21/9  · TP40/-50 · SL2% · DS)",
        ema_fast=8, ema_slow=21, ema_signal=9,
        tp_long=40, tp_short=-50,
        stop_loss_pct=2.0, hard_cap_multiplier=1.85, deep_swing=True,
    ),
    BacktestConfig(
        label="Slow MACD    (14/30/11· TP40/-50 · SL2% · DS)",
        ema_fast=14, ema_slow=30, ema_signal=11,
        tp_long=40, tp_short=-50,
        stop_loss_pct=2.0, hard_cap_multiplier=1.85, deep_swing=True,
    ),
    BacktestConfig(
        label="No DeepSwing (12/26/9 · TP40/-50 · SL2% · NoDS)",
        ema_fast=12, ema_slow=26, ema_signal=9,
        tp_long=40, tp_short=-50,
        stop_loss_pct=2.0, hard_cap_multiplier=1.85, deep_swing=False,
    ),
    BacktestConfig(
        label="Tight SL     (12/26/9 · TP40/-50 · SL1% · DS)",
        ema_fast=12, ema_slow=26, ema_signal=9,
        tp_long=40, tp_short=-50,
        stop_loss_pct=1.0, hard_cap_multiplier=1.85, deep_swing=True,
    ),
    BacktestConfig(
        label="Wide SL      (12/26/9 · TP40/-50 · SL3% · DS)",
        ema_fast=12, ema_slow=26, ema_signal=9,
        tp_long=40, tp_short=-50,
        stop_loss_pct=3.0, hard_cap_multiplier=1.85, deep_swing=True,
    ),
]
