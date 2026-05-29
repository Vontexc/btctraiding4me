from enum import Enum
from bot.macd import MACDResult


class Signal(Enum):
    NONE = "WATCHING"
    LONG = "LONG"
    SHORT = "SHORT"


def evaluate_signal(macd: MACDResult) -> Signal:
    """
    Long  when histogram crosses from negative to positive.
    Short when histogram crosses from positive to negative.
    """
    crossed_up = macd.prev_histogram <= 0 < macd.histogram
    crossed_down = macd.prev_histogram >= 0 > macd.histogram

    if crossed_up:
        return Signal.LONG
    if crossed_down:
        return Signal.SHORT
    return Signal.NONE
