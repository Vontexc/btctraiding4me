import time as _time

import ccxt
import pandas as pd

from config import config

_TF_MS: dict[str, int] = {
    "1m": 60_000, "5m": 300_000, "15m": 900_000,
    "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000,
}


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

    def fetch_historical(self, days: int = 180) -> pd.DataFrame:
        """
        Fetch up to `days` of OHLCV history via paginated requests.
        Paginates forward from (now - days) until the exchange returns fewer
        than the page-size, respecting the exchange rate limit between calls.
        """
        tf_ms = _TF_MS.get(config.TIMEFRAME, 900_000)
        since_ms = int((_time.time() - days * 86_400) * 1_000)
        page_size = 1_000
        rows: list[list] = []

        while True:
            batch = self.exchange.fetch_ohlcv(
                config.SYMBOL,
                timeframe=config.TIMEFRAME,
                since=since_ms,
                limit=page_size,
            )
            if not batch:
                break
            rows.extend(batch)
            if len(batch) < page_size:
                break
            since_ms = batch[-1][0] + tf_ms
            _time.sleep(self.exchange.rateLimit / 1_000)

        df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.set_index("timestamp")
        df = df[~df.index.duplicated(keep="last")].sort_index()
        return df

    @property
    def last_price(self) -> float:
        return self._last_price
