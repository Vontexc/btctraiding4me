"""
BTC MACD Trading Bot – entry point.

Usage:
    python main.py            # uses MODE from .env (default: paper)
    MODE=live python main.py  # live trading (requires valid API keys)
"""

import logging
import sys
import time
from datetime import datetime

from rich.live import Live

from bot.macd import calculate_macd
from bot.order import OrderManager
from bot.position import PositionTracker
from bot.risk import check_exit
from bot.signal import Signal, evaluate_signal
from config import config
from data.fetcher import DataFetcher
from display.console import build_display
from logs.trade_logger import log_trade

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler("logs/bot.log"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

TICK_INTERVAL = 5   # seconds between price refreshes
CANDLE_CHECK  = 60  # seconds between new-candle MACD checks (not a full wait – tracks last candle ts)


def main() -> None:
    try:
        config.validate()
    except ValueError as exc:
        logger.error("Config error: %s", exc)
        sys.exit(1)

    logger.info("Starting BTC MACD Bot in %s mode – %s %s", config.MODE.upper(), config.SYMBOL, config.TIMEFRAME)

    fetcher = DataFetcher()
    order_mgr = OrderManager()
    tracker = PositionTracker()
    bank = config.INITIAL_BANK

    last_candle_ts = None

    with Live(auto_refresh=False, screen=True) as live:
        while True:
            try:
                # ── Fetch live price ──────────────────────────────────────────
                ticker = fetcher.fetch_ticker()
                price = fetcher.last_price

                # ── Fetch OHLCV + MACD (once per new candle) ─────────────────
                df = fetcher.fetch_ohlcv()
                current_candle_ts = df.index[-1]

                if current_candle_ts != last_candle_ts:
                    last_candle_ts = current_candle_ts
                    macd = calculate_macd(df)

                    if not tracker.is_open:
                        signal = evaluate_signal(macd)

                        if signal != Signal.NONE:
                            entry_time = datetime.utcnow().isoformat()
                            order_mgr.place_order(signal, price, config.TRADE_SIZE_BTC)
                            tracker.open(signal, price, config.TRADE_SIZE_BTC, entry_time)
                            logger.info("Opened %s @ %.2f", signal.value, price)

                else:
                    # Recompute MACD from existing df for risk checks
                    macd = calculate_macd(df)

                # ── Update position P&L ───────────────────────────────────────
                tracker.update(price)

                # ── Exit logic ────────────────────────────────────────────────
                if tracker.is_open and tracker.position:
                    should_close, reason = check_exit(tracker.position, price, macd)

                    if should_close:
                        pos = tracker.position
                        realised = pos.unrealised_pnl
                        order_mgr.close_order(pos.side, price, pos.size_btc)
                        log_trade(
                            symbol=config.SYMBOL,
                            side=pos.side.value,
                            entry_price=pos.entry_price,
                            exit_price=price,
                            size_btc=pos.size_btc,
                            pnl_usd=realised,
                            reason=reason,
                        )
                        bank += realised
                        tracker.close(realised)
                        logger.info("Closed position – reason: %s, PnL: $%.2f", reason, realised)

                # ── Render terminal UI ────────────────────────────────────────
                status = tracker.position.side.value if tracker.is_open else Signal.NONE.value
                layout = build_display(price, macd, tracker, bank, status)
                live.update(layout, refresh=True)

            except KeyboardInterrupt:
                logger.info("Bot stopped by user.")
                break
            except Exception as exc:
                logger.exception("Unexpected error: %s", exc)

            time.sleep(TICK_INTERVAL)


if __name__ == "__main__":
    main()
