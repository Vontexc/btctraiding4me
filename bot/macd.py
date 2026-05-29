import pandas as pd
from dataclasses import dataclass
from config import config


@dataclass
class MACDResult:
    dif: float
    dea: float
    histogram: float
    prev_dif: float
    prev_dea: float
    prev_histogram: float


def calculate_macd(df: pd.DataFrame) -> MACDResult:
    close = df["close"].astype(float)

    ema_fast = close.ewm(span=config.EMA_FAST, adjust=False).mean()
    ema_slow = close.ewm(span=config.EMA_SLOW, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=config.EMA_SIGNAL, adjust=False).mean()
    histogram = dif - dea

    return MACDResult(
        dif=float(dif.iloc[-1]),
        dea=float(dea.iloc[-1]),
        histogram=float(histogram.iloc[-1]),
        prev_dif=float(dif.iloc[-2]),
        prev_dea=float(dea.iloc[-2]),
        prev_histogram=float(histogram.iloc[-2]),
    )
