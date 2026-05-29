"""
Self-contained backtest engine.

Replays OHLCV candles bar-by-bar applying MACD signals and risk rules.
Intra-candle TP/SL uses the candle's high/low range for realism.
When both SL and TP are hit inside the same candle the SL is assumed first
(conservative bias).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class BacktestConfig:
    ema_fast: int = 12
    ema_slow: int = 26
    ema_signal: int = 9
    tp_long: float = 40.0
    tp_short: float = -50.0
    hard_cap_multiplier: float = 1.85
    stop_loss_pct: float = 2.0
    deep_swing: bool = True
    trade_size_btc: float = 0.01
    initial_bank: float = 1000.0
    label: str = ""

    def __post_init__(self) -> None:
        if not self.label:
            ds = "DS" if self.deep_swing else "NoDS"
            self.label = (
                f"EMA{self.ema_fast}/{self.ema_slow}/{self.ema_signal} "
                f"TP{self.tp_long}/{self.tp_short} "
                f"SL{self.stop_loss_pct}% HC{self.hard_cap_multiplier} {ds}"
            )


@dataclass
class TradeRecord:
    side: str
    entry_price: float
    exit_price: float
    size_btc: float
    pnl_usd: float
    entry_bar: int
    exit_bar: int
    reason: str

    @property
    def duration_bars(self) -> int:
        return max(self.exit_bar - self.entry_bar, 1)

    @property
    def return_pct(self) -> float:
        notional = self.entry_price * self.size_btc
        return (self.pnl_usd / notional) * 100 if notional > 0 else 0.0


@dataclass
class BacktestResult:
    config: BacktestConfig
    trades: list[TradeRecord] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)


def _calc_macd(close: np.ndarray, fast: int, slow: int, signal: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    s = pd.Series(close)
    dif = s.ewm(span=fast, adjust=False).mean() - s.ewm(span=slow, adjust=False).mean()
    dea = dif.ewm(span=signal, adjust=False).mean()
    hist = dif - dea
    return dif.values, dea.values, hist.values


def run_backtest(df: pd.DataFrame, cfg: BacktestConfig) -> BacktestResult:
    close = df["close"].astype(float).values
    high = df["high"].astype(float).values
    low = df["low"].astype(float).values
    n = len(close)

    _, _, hist = _calc_macd(close, cfg.ema_fast, cfg.ema_slow, cfg.ema_signal)

    # Warm-up bars needed before signals are reliable
    min_bar = cfg.ema_slow + cfg.ema_signal + 5

    result = BacktestResult(config=cfg)
    bank = cfg.initial_bank
    result.equity_curve.append(bank)

    side: str | None = None
    entry_price = 0.0
    entry_bar = 0

    for i in range(min_bar, n):
        price = close[i]

        if side is None:
            # Entry on histogram crossover (confirmed at bar close)
            if hist[i - 1] <= 0 < hist[i]:
                side, entry_price, entry_bar = "LONG", price, i
            elif hist[i - 1] >= 0 > hist[i]:
                side, entry_price, entry_bar = "SHORT", price, i
        else:
            notional = entry_price * cfg.trade_size_btc

            if side == "LONG":
                tp_usd = (cfg.tp_long / 100) * notional
                hc_usd = tp_usd * cfg.hard_cap_multiplier
                sl_usd = -(cfg.stop_loss_pct / 100) * notional

                pnl_at_high = (high[i] - entry_price) * cfg.trade_size_btc
                pnl_at_low = (low[i] - entry_price) * cfg.trade_size_btc
                pnl_at_close = (close[i] - entry_price) * cfg.trade_size_btc

                exit_pnl: float | None = None
                reason = ""

                # SL checked first (conservative)
                if pnl_at_low <= sl_usd:
                    exit_pnl, reason = sl_usd, "SL"
                elif pnl_at_high >= hc_usd:
                    exit_pnl, reason = hc_usd, "TP_HC"
                elif cfg.deep_swing:
                    if pnl_at_close >= tp_usd and hist[i] < 0:
                        exit_pnl, reason = pnl_at_close, "TP_DS"
                elif pnl_at_high >= tp_usd:
                    exit_pnl, reason = tp_usd, "TP"

            else:  # SHORT
                tp_usd = abs(cfg.tp_short / 100) * notional
                hc_usd = tp_usd * cfg.hard_cap_multiplier
                sl_usd = -(cfg.stop_loss_pct / 100) * notional

                pnl_at_low = (entry_price - low[i]) * cfg.trade_size_btc   # profit
                pnl_at_high = (entry_price - high[i]) * cfg.trade_size_btc  # loss when price rises
                pnl_at_close = (entry_price - close[i]) * cfg.trade_size_btc

                exit_pnl = None
                reason = ""

                if pnl_at_high <= sl_usd:
                    exit_pnl, reason = sl_usd, "SL"
                elif pnl_at_low >= hc_usd:
                    exit_pnl, reason = hc_usd, "TP_HC"
                elif cfg.deep_swing:
                    if pnl_at_close >= tp_usd and hist[i] > 0:
                        exit_pnl, reason = pnl_at_close, "TP_DS"
                elif pnl_at_low >= tp_usd:
                    exit_pnl, reason = tp_usd, "TP"

            if exit_pnl is not None:
                result.trades.append(
                    TradeRecord(
                        side=side,
                        entry_price=entry_price,
                        exit_price=price,
                        size_btc=cfg.trade_size_btc,
                        pnl_usd=exit_pnl,
                        entry_bar=entry_bar,
                        exit_bar=i,
                        reason=reason,
                    )
                )
                bank += exit_pnl
                side = None

        result.equity_curve.append(bank)

    return result
