import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    API_KEY: str = os.getenv("API_KEY", "")
    API_SECRET: str = os.getenv("API_SECRET", "")
    SYMBOL: str = os.getenv("SYMBOL", "BTC/USDT:USDT")
    TIMEFRAME: str = os.getenv("TIMEFRAME", "15m")
    TRADE_SIZE_BTC: float = float(os.getenv("TRADE_SIZE_BTC", "0.01"))
    TP_LONG: float = float(os.getenv("TP_LONG", "40"))
    TP_SHORT: float = float(os.getenv("TP_SHORT", "-50"))
    HARD_CAP_MULTIPLIER: float = float(os.getenv("HARD_CAP_MULTIPLIER", "1.85"))
    DEEP_SWING: bool = os.getenv("DEEP_SWING", "true").lower() == "true"
    MODE: str = os.getenv("MODE", "paper").lower()

    EMA_FAST: int = 12
    EMA_SLOW: int = 26
    EMA_SIGNAL: int = 9
    OHLCV_LIMIT: int = 200
    STOP_LOSS_PCT: float = float(os.getenv("STOP_LOSS_PCT", "2.0"))
    INITIAL_BANK: float = float(os.getenv("INITIAL_BANK", "1000.0"))

    @classmethod
    def is_live(cls) -> bool:
        return cls.MODE == "live"

    @classmethod
    def validate(cls) -> None:
        if cls.is_live() and (not cls.API_KEY or not cls.API_SECRET):
            raise ValueError("API_KEY and API_SECRET are required in LIVE mode")


config = Config()
