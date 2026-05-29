import csv
import logging
import os
from datetime import datetime

LOG_PATH = os.path.join(os.path.dirname(__file__), "trades_15m.csv")
_FIELDS = ["timestamp", "symbol", "side", "entry_price", "exit_price", "size_btc", "pnl_usd", "reason"]

logger = logging.getLogger(__name__)


def _ensure_header() -> None:
    if not os.path.exists(LOG_PATH) or os.path.getsize(LOG_PATH) == 0:
        with open(LOG_PATH, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=_FIELDS).writeheader()


def log_trade(
    symbol: str,
    side: str,
    entry_price: float,
    exit_price: float,
    size_btc: float,
    pnl_usd: float,
    reason: str,
) -> None:
    _ensure_header()
    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "symbol": symbol,
        "side": side,
        "entry_price": round(entry_price, 2),
        "exit_price": round(exit_price, 2),
        "size_btc": size_btc,
        "pnl_usd": round(pnl_usd, 4),
        "reason": reason,
    }
    with open(LOG_PATH, "a", newline="") as f:
        csv.DictWriter(f, fieldnames=_FIELDS).writerow(row)
    logger.info("Trade logged: %s", row)
