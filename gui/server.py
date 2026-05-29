"""
Web GUI server – serves the dashboard and runs the bot in a background thread.

    python run_gui.py          # opens http://localhost:8080
"""

from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from bot.macd import calculate_macd
from bot.order import OrderManager
from bot.position import PositionTracker
from bot.risk import check_exit
from bot.signal import Signal, evaluate_signal
from config import config
from data.fetcher import DataFetcher
from logs.trade_logger import log_trade

logger = logging.getLogger(__name__)

CHART_WINDOW = 80
TICK_SECONDS = 5


# ── Shared state ──────────────────────────────────────────────────────────────

@dataclass
class BotState:
    price: float = 0.0
    dif: float = 0.0
    dea: float = 0.0
    histogram: float = 0.0
    prev_histogram: float = 0.0
    status: str = "STOPPED"
    side: str = ""
    entry_price: float = 0.0
    unrealised_pnl: float = 0.0
    peak_pnl: float = 0.0
    pnl_pct: float = 0.0
    bank: float = config.INITIAL_BANK
    session_pnl: float = 0.0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    mode: str = config.MODE.upper()
    running: bool = False
    error: str = ""
    last_update: str = ""
    # Rolling chart series
    chart_labels: list = field(default_factory=list)
    chart_close: list = field(default_factory=list)
    chart_histogram: list = field(default_factory=list)
    chart_dif: list = field(default_factory=list)
    chart_dea: list = field(default_factory=list)
    # Last 50 closed trades
    trades: list = field(default_factory=list)


_state = BotState()
_lock = threading.Lock()
_stop_event = threading.Event()
_bot_thread: Optional[threading.Thread] = None


def _trim_chart() -> None:
    """Drop oldest chart points beyond CHART_WINDOW (call while holding _lock)."""
    while len(_state.chart_labels) > CHART_WINDOW:
        for lst in (_state.chart_labels, _state.chart_close,
                    _state.chart_histogram, _state.chart_dif, _state.chart_dea):
            lst.pop(0)


# ── Bot loop (runs in background thread) ─────────────────────────────────────

def _run_bot() -> None:
    fetcher = DataFetcher()
    order_mgr = OrderManager()
    tracker = PositionTracker()
    last_candle_ts = None

    with _lock:
        _state.running = True
        _state.status = "WATCHING"
        _state.bank = config.INITIAL_BANK
        _state.session_pnl = 0.0
        _state.wins = 0
        _state.losses = 0
        _state.win_rate = 0.0
        _state.error = ""

    while not _stop_event.is_set():
        try:
            fetcher.fetch_ticker()
            price = fetcher.last_price

            df = fetcher.fetch_ohlcv()
            current_candle_ts = df.index[-1]
            macd = calculate_macd(df)

            # ── New candle: update chart + check entry ────────────────────────
            if current_candle_ts != last_candle_ts:
                last_candle_ts = current_candle_ts
                with _lock:
                    _state.chart_labels.append(current_candle_ts.strftime("%H:%M"))
                    _state.chart_close.append(round(float(df["close"].iloc[-1]), 2))
                    _state.chart_histogram.append(round(macd.histogram, 6))
                    _state.chart_dif.append(round(macd.dif, 6))
                    _state.chart_dea.append(round(macd.dea, 6))
                    _trim_chart()

                if not tracker.is_open:
                    signal = evaluate_signal(macd)
                    if signal != Signal.NONE:
                        order_mgr.place_order(signal, price, config.TRADE_SIZE_BTC)
                        tracker.open(signal, price, config.TRADE_SIZE_BTC,
                                     datetime.utcnow().isoformat())
                        logger.info("Opened %s @ %.2f", signal.value, price)

            # ── Update P&L + check exit ───────────────────────────────────────
            tracker.update(price)

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
                    with _lock:
                        _state.bank += realised
                        _state.trades.insert(0, {
                            "time": datetime.utcnow().strftime("%H:%M:%S"),
                            "side": pos.side.value,
                            "entry": round(pos.entry_price, 2),
                            "exit_price": round(price, 2),
                            "pnl": round(realised, 4),
                            "reason": reason,
                        })
                        if len(_state.trades) > 50:
                            _state.trades.pop()
                    tracker.close(realised)
                    logger.info("Closed %s | P&L: $%.4f | %s", pos.side.value, realised, reason)

            # ── Sync state ────────────────────────────────────────────────────
            pos = tracker.position
            with _lock:
                _state.price = round(price, 2)
                _state.dif = round(macd.dif, 4)
                _state.dea = round(macd.dea, 4)
                _state.histogram = round(macd.histogram, 4)
                _state.prev_histogram = round(macd.prev_histogram, 4)
                _state.session_pnl = round(tracker.session_pnl, 4)
                _state.wins = tracker.wins
                _state.losses = tracker.losses
                _state.win_rate = round(tracker.win_rate, 1)
                _state.last_update = datetime.utcnow().strftime("%H:%M:%S")
                _state.error = ""
                if pos:
                    _state.status = pos.side.value
                    _state.side = pos.side.value
                    _state.entry_price = round(pos.entry_price, 2)
                    _state.unrealised_pnl = round(pos.unrealised_pnl, 4)
                    _state.peak_pnl = round(pos.peak_pnl, 4)
                    _state.pnl_pct = round(pos.pnl_pct, 2)
                else:
                    _state.status = "WATCHING"
                    _state.side = ""
                    _state.entry_price = 0.0
                    _state.unrealised_pnl = 0.0
                    _state.peak_pnl = 0.0
                    _state.pnl_pct = 0.0

        except Exception as exc:
            logger.exception("Bot error: %s", exc)
            with _lock:
                _state.error = str(exc)

        _stop_event.wait(TICK_SECONDS)

    with _lock:
        _state.running = False
        _state.status = "STOPPED"


# ── FastAPI ───────────────────────────────────────────────────────────────────

app = FastAPI(title="BTC MACD Bot")
_HTML = (Path(__file__).parent / "templates" / "index.html").read_text


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return _HTML()


@app.post("/api/start")
def api_start():
    global _bot_thread
    if _state.running:
        return {"ok": False, "msg": "already running"}
    _stop_event.clear()
    _bot_thread = threading.Thread(target=_run_bot, daemon=True)
    _bot_thread.start()
    return {"ok": True}


@app.post("/api/stop")
def api_stop():
    _stop_event.set()
    return {"ok": True}


@app.get("/api/config")
def api_config():
    return {
        "symbol":            config.SYMBOL,
        "timeframe":         config.TIMEFRAME,
        "trade_size_btc":    config.TRADE_SIZE_BTC,
        "tp_long":           config.TP_LONG,
        "tp_short":          config.TP_SHORT,
        "stop_loss_pct":     config.STOP_LOSS_PCT,
        "hard_cap_multiplier": config.HARD_CAP_MULTIPLIER,
        "deep_swing":        config.DEEP_SWING,
        "mode":              config.MODE,
    }


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            with _lock:
                snapshot = asdict(_state)
            await ws.send_json(snapshot)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
