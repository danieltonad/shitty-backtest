from enum import Enum
import asyncio

from capital_com.simulator import new_order



import asyncio
from .simulator import new_order, SignalType
from .memory import memory
from datetime import datetime, time




def is_trading_session() -> bool:
    now_utc = datetime.utcnow().time()
    windows = [
        (time(7, 0), time(16, 0)),   # London–NY overlap
        (time(12, 0), time(17, 0)),  # optional NY volatility window
    ]
    return any(start <= now_utc <= end for start, end in windows)




def get_latest_signal(epic: str, lookback_bars: int = 40):
    """Analyze recent bars to generate trading signals."""
    # trade only during active sessions
    if not is_trading_session():
        return None

    bars = memory.bars[epic]
    if len(bars) < lookback_bars + 2:
        return None

    bars_list = list(bars)
    recent = bars_list[-lookback_bars:]
    current = bars_list[-1]
    prev = bars_list[-2]

    avg_spread = sum(b["avg_spread"] for b in recent) / len(recent)
    avg_range = sum(b["high"] - b["low"] for b in recent) / len(recent)

    # Optional: ignore low-volatility candles (when range is too small)
    if avg_range < avg_spread * 3:
        return None

    # Filter out candles with abnormally wide spread (unstable quotes)
    if current["avg_spread"] > avg_spread * 1.5:
        return None

    signal = None
    entry_price = current["close"]

    # Adaptive TP/SL based on volatility
    tp_mult = 6
    sl_mult = 1.5

    if current["close"] > prev["high"]:
        signal = SignalType.BUY
        # Offset entry slightly for realistic fill
        entry_price += avg_spread
        stop_loss = current["low"] - avg_range * sl_mult
        take_profit = entry_price + avg_range * tp_mult

    elif current["close"] < prev["low"]:
        signal = SignalType.SELL
        entry_price -= avg_spread
        stop_loss = current["high"] + avg_range * sl_mult
        take_profit = entry_price - avg_range * tp_mult

    if signal:
        asyncio.create_task(new_order(epic, signal, entry_price, take_profit, stop_loss))

    return signal
