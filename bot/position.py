from dataclasses import dataclass, field
from typing import Optional
from bot.signal import Signal


@dataclass
class Position:
    side: Signal
    entry_price: float
    size_btc: float
    entry_time: str = ""
    peak_pnl: float = 0.0
    unrealised_pnl: float = 0.0

    def update(self, current_price: float) -> None:
        if self.side == Signal.LONG:
            self.unrealised_pnl = (current_price - self.entry_price) * self.size_btc
        else:
            self.unrealised_pnl = (self.entry_price - current_price) * self.size_btc

        if self.unrealised_pnl > self.peak_pnl:
            self.peak_pnl = self.unrealised_pnl

    @property
    def pnl_pct(self) -> float:
        notional = self.entry_price * self.size_btc
        if notional == 0:
            return 0.0
        return (self.unrealised_pnl / notional) * 100


class PositionTracker:
    def __init__(self) -> None:
        self.position: Optional[Position] = None
        self.session_pnl: float = 0.0
        self.wins: int = 0
        self.losses: int = 0

    @property
    def is_open(self) -> bool:
        return self.position is not None

    def open(self, side: Signal, entry_price: float, size_btc: float, entry_time: str = "") -> None:
        self.position = Position(
            side=side,
            entry_price=entry_price,
            size_btc=size_btc,
            entry_time=entry_time,
        )

    def close(self, realised_pnl: float) -> None:
        self.session_pnl += realised_pnl
        if realised_pnl >= 0:
            self.wins += 1
        else:
            self.losses += 1
        self.position = None

    @property
    def win_rate(self) -> float:
        total = self.wins + self.losses
        return (self.wins / total * 100) if total > 0 else 0.0

    def update(self, price: float) -> None:
        if self.position:
            self.position.update(price)
