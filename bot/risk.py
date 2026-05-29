from bot.position import Position
from bot.signal import Signal
from bot.macd import MACDResult
from config import config


class CloseReason:
    TP = "TP"
    SL = "SL"
    SIGNAL_FLIP = "SIGNAL_FLIP"


def check_exit(position: Position, current_price: float, macd: MACDResult) -> tuple[bool, str]:
    """
    Returns (should_close, reason).
    Priority: Hard Cap > SL > TP > Deep-Swing signal flip.
    """
    pnl = position.unrealised_pnl
    notional = position.entry_price * position.size_btc

    # Hard cap: close if PnL exceeds TP * hard-cap multiplier
    if position.side == Signal.LONG:
        tp_usd = (config.TP_LONG / 100) * notional
        hard_cap_usd = tp_usd * config.HARD_CAP_MULTIPLIER
        sl_usd = -(config.STOP_LOSS_PCT / 100) * notional

        if pnl >= hard_cap_usd:
            return True, CloseReason.TP
        if pnl <= sl_usd:
            return True, CloseReason.SL

        if config.DEEP_SWING:
            # Stay in trade unless histogram crosses back negative
            if pnl >= tp_usd and macd.histogram < 0:
                return True, CloseReason.TP
        else:
            if pnl >= tp_usd:
                return True, CloseReason.TP

    else:  # SHORT
        tp_usd = abs((config.TP_SHORT / 100) * notional)
        hard_cap_usd = tp_usd * config.HARD_CAP_MULTIPLIER
        sl_usd = -(config.STOP_LOSS_PCT / 100) * notional

        if pnl >= hard_cap_usd:
            return True, CloseReason.TP
        if pnl <= sl_usd:
            return True, CloseReason.SL

        if config.DEEP_SWING:
            if pnl >= tp_usd and macd.histogram > 0:
                return True, CloseReason.TP
        else:
            if pnl >= tp_usd:
                return True, CloseReason.TP

    return False, ""
