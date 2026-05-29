import ccxt
import pandas as pd
from config import config


class DataFetcher:
    def __init__(self) -> None:
        exchange_params: dict = {"enableRateLimit": True}
        if config.is_live():
            exchange_params["apiKey"] = config.API_KEY
            exchange_params["secret"] = config.API_SECRET

        # Bybit supports unified perpetual futures via ccxt
        self.exchange = ccxt.bybit(exchange_params)
        self._last_price: float = 0.0

    def fetch_ohlcv(self) -> pd.DataFrame:
        raw = self.exchange.fetch_ohlcv(
            config.SYMBOL,
            timeframe=config.TIMEFRAME,
            limit=config.OHLCV_LIMIT,
        )
        df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.set_index("timestamp")
        return df

    def fetch_ticker(self) -> dict:
        ticker = self.exchange.fetch_ticker(config.SYMBOL)
        self._last_price = float(ticker["last"])
        return ticker

    @property
    def last_price(self) -> float:
        return self._last_price
