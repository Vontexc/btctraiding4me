from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.live import Live
from rich.layout import Layout
from bot.macd import MACDResult
from bot.position import PositionTracker
from bot.signal import Signal
from config import config

console = Console()


def _colour_val(val: float, inverse: bool = False) -> str:
    if val > 0:
        colour = "red" if inverse else "green"
    elif val < 0:
        colour = "green" if inverse else "red"
    else:
        colour = "white"
    return colour


def build_display(
    price: float,
    macd: MACDResult,
    tracker: PositionTracker,
    bank: float,
    status: str,
) -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=3),
    )
    layout["main"].split_row(
        Layout(name="left"),
        Layout(name="right"),
    )

    # ── Header ──────────────────────────────────────────────────────────────
    status_colour = {"WATCHING": "yellow", "LONG": "green", "SHORT": "red"}.get(status, "white")
    header_text = Text(justify="center")
    header_text.append("BTC MACD Trading Bot", style="bold cyan")
    header_text.append(f"  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim")
    header_text.append(f"  |  Mode: {config.MODE.upper()}", style="bold magenta")
    layout["header"].update(Panel(header_text, style="bold"))

    # ── Left panel: Market & MACD ────────────────────────────────────────────
    market_table = Table(show_header=False, box=None, padding=(0, 1))
    market_table.add_column("Key", style="bold cyan", width=22)
    market_table.add_column("Value", justify="right", width=20)

    price_col = "green" if price >= 0 else "red"
    market_table.add_row("BTC Price", f"[{price_col}]${price:,.2f}[/]")
    market_table.add_row("Symbol", config.SYMBOL)
    market_table.add_row("Timeframe", config.TIMEFRAME)
    market_table.add_row("", "")

    dif_col = _colour_val(macd.dif)
    dea_col = _colour_val(macd.dea)
    hist_col = _colour_val(macd.histogram)
    prev_hist_col = _colour_val(macd.prev_histogram)

    market_table.add_row("DIF (current)", f"[{dif_col}]{macd.dif:.4f}[/]")
    market_table.add_row("DEA (current)", f"[{dea_col}]{macd.dea:.4f}[/]")
    market_table.add_row("Histogram", f"[{hist_col}]{macd.histogram:.4f}[/]")
    market_table.add_row("Histogram (prev)", f"[{prev_hist_col}]{macd.prev_histogram:.4f}[/]")

    layout["left"].update(Panel(market_table, title="[bold]Market & MACD[/bold]"))

    # ── Right panel: Position & Account ─────────────────────────────────────
    pos_table = Table(show_header=False, box=None, padding=(0, 1))
    pos_table.add_column("Key", style="bold cyan", width=22)
    pos_table.add_column("Value", justify="right", width=20)

    pos_table.add_row("Status", f"[bold {status_colour}]{status}[/bold {status_colour}]")
    pos_table.add_row("Bank (USD)", f"${bank:,.2f}")
    pos_table.add_row("Trade Size (BTC)", f"{config.TRADE_SIZE_BTC:.4f}")
    pos_table.add_row("", "")

    if tracker.is_open and tracker.position:
        pos = tracker.position
        pnl_col = _colour_val(pos.unrealised_pnl)
        peak_col = _colour_val(pos.peak_pnl)
        pos_table.add_row("Entry Price", f"${pos.entry_price:,.2f}")
        pos_table.add_row("Unrealised P&L", f"[{pnl_col}]${pos.unrealised_pnl:,.2f} ({pos.pnl_pct:.2f}%)[/]")
        pos_table.add_row("Peak P&L", f"[{peak_col}]${pos.peak_pnl:,.2f}[/]")
    else:
        pos_table.add_row("Entry Price", "—")
        pos_table.add_row("Unrealised P&L", "—")
        pos_table.add_row("Peak P&L", "—")

    pos_table.add_row("", "")
    sess_col = _colour_val(tracker.session_pnl)
    pos_table.add_row("Session P&L", f"[{sess_col}]${tracker.session_pnl:,.2f}[/]")
    pos_table.add_row("Wins / Losses", f"[green]{tracker.wins}[/] / [red]{tracker.losses}[/]")
    pos_table.add_row("Win Rate", f"{tracker.win_rate:.1f}%")

    layout["right"].update(Panel(pos_table, title="[bold]Position & Account[/bold]"))

    # ── Footer ───────────────────────────────────────────────────────────────
    layout["footer"].update(
        Panel(
            Text("Press Ctrl+C to stop  |  TP Long: ${:.0f}  |  TP Short: -${:.0f}  |  SL: {:.1f}%  |  Deep Swing: {}".format(
                config.TP_LONG, abs(config.TP_SHORT), config.STOP_LOSS_PCT, "ON" if config.DEEP_SWING else "OFF"
            ), justify="center", style="dim"),
        )
    )

    return layout
