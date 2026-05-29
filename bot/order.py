import ccxt
import logging
from bot.signal import Signal
from config import config

logger = logging.getLogger(__name__)


class OrderManager:
    def __init__(self, exchange: ccxt.Exchange | None = None) -> None:
        self.exchange = exchange

    def place_order(self, side: Signal, price: float, size_btc: float) -> dict:
        if config.MODE == "paper":
            return self._paper_order(side, price, size_btc)
        return self._live_order(side, price, size_btc)

    def close_order(self, side: Signal, price: float, size_btc: float) -> dict:
        close_side = Signal.SHORT if side == Signal.LONG else Signal.LONG
        if config.MODE == "paper":
            return self._paper_order(close_side, price, size_btc)
        return self._live_order(close_side, price, size_btc)

    def _paper_order(self, side: Signal, price: float, size_btc: float) -> dict:
        direction = "buy" if side == Signal.LONG else "sell"
        logger.info("[PAPER] %s %.4f BTC @ %.2f", direction.upper(), size_btc, price)
        return {"side": direction, "price": price, "amount": size_btc, "status": "filled"}

    def _live_order(self, side: Signal, price: float, size_btc: float) -> dict:
        if self.exchange is None:
            raise RuntimeError("Exchange not initialised for live trading")
        direction = "buy" if side == Signal.LONG else "sell"
        try:
            order = self.exchange.create_market_order(
                config.SYMBOL,
                direction,
                size_btc,
            )
            logger.info("[LIVE] %s order placed: %s", direction.upper(), order)
            return order
        except ccxt.BaseError as exc:
            logger.error("Order failed: %s", exc)
            raise
