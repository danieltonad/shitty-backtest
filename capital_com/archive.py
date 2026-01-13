from enum import Enum
from typing import Optional
import asyncio
from datetime import datetime, time
import pandas as pd
from .hook import send_hook

# --- External imports (you already have these) ---
from .simulator import new_order, SignalType
from .memory import memory


class TrendBias(str, Enum):
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    NEUTRAL = "neutral"


def is_trading_session() -> bool:
    """Only trade during high-liquidity windows (UTC)."""
    now = datetime.utcnow().time()
    # Primary: London–NY overlap
    return time(12, 0) <= now <= time(16, 30)


def get_trend_bias(bars_list: list) -> TrendBias:
    """Simple EMA(8) vs EMA(20) trend filter on 30-sec closes."""
    if len(bars_list) < 20:
        return TrendBias.NEUTRAL

    closes = [b["close"] for b in bars_list[-40:]]
    ema8 = pd.Series(closes).ewm(span=8, adjust=False).mean().iloc[-1]
    ema20 = pd.Series(closes).ewm(span=20, adjust=False).mean().iloc[-1]

    if ema8 > ema20 * 1.001:
        return TrendBias.UPTREND
    elif ema8 < ema20 * 0.999:
        return TrendBias.DOWNTREND
    else:
        return TrendBias.NEUTRAL


def atr_14(bars_list: list) -> float:
    """Compute 14-period Average True Range from 30-sec bars."""
    if len(bars_list) < 15:
        # Fallback: use recent average range
        recent = bars_list[-5:] if bars_list else [{"high": 1, "low": 1}]
        return max(b["high"] - b["low"] for b in recent)

    trs = []
    for i in range(1, len(bars_list)):
        h, l, c_prev = bars_list[i]["high"], bars_list[i]["low"], bars_list[i-1]["close"]
        tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
        trs.append(tr)

    return sum(trs[-14:]) / 14




async def get_latest_signal(epic: str, lookback_bars: int = 40) -> Optional[SignalType]:
    """
    Micro-breakout strategy with trend + volatility filtering.
    Designed for Capital.com's tick-based 30-sec bars.
    """
    # Session filter (critical on Capital.com)
    # if not is_trading_session():
    #     return None

    bars = memory.bars[epic]
    if len(bars) < lookback_bars + 3:  # need bars[-3], [-2], [-1]
        return None

    bars_list = list(bars)
    recent = bars_list[-lookback_bars:]
    current = bars_list[-1]
    prev = bars_list[-2]
    prev2 = bars_list[-3]  # for confirmation logic

    # Compute stats
    avg_spread = sum(b["avg_spread"] for b in recent) / len(recent)
    atr = atr_14(bars_list)

    # Spread filter: avoid unstable quotes
    if current["avg_spread"] > avg_spread * 1.5:
        return None

    # Volatility filter: skip ultra-chop
    if atr < avg_spread * 2.5:
        return None

    # 📈 Trend filter (AVOID counter-trend trades — biggest loss source)
    trend = get_trend_bias(bars_list)

    signal = None
    entry_price = None
    stop_loss = None
    take_profit = None

    # 🔺 LONG logic: breakout + retest confirmation
    breakout_up = current["close"] > prev["high"]
    retest_hold = current["low"] >= prev["high"] * 0.9995  # holds breakout level
    in_uptrend = trend in (TrendBias.UPTREND, TrendBias.NEUTRAL)

    if breakout_up and retest_hold and in_uptrend:
        signal = SignalType.BUY
        # Enter on *breakout level*, not chase current price
        entry_price = prev["high"] + 0.1 * avg_spread  # slight aggressiveness
        sl_dist = max(avg_spread * 2, atr * 0.8)      # minimum SL buffer
        tp_dist = atr * 2.2                            # realistic ~2:1 RR
        stop_loss = entry_price - sl_dist
        take_profit = entry_price + tp_dist

    # 🔻 SHORT logic: breakdown + retest
    breakdown = current["close"] < prev["low"]
    retest_resist = current["high"] <= prev["low"] * 1.0005
    in_downtrend = trend in (TrendBias.DOWNTREND, TrendBias.NEUTRAL)

    if breakdown and retest_resist and in_downtrend:
        signal = SignalType.SELL
        entry_price = prev["low"] - 0.1 * avg_spread
        sl_dist = max(avg_spread * 2, atr * 0.8)
        tp_dist = atr * 2.2
        stop_loss = entry_price + sl_dist
        take_profit = entry_price - tp_dist

    # 🚀 Fire signal
    if signal and entry_price and stop_loss and take_profit:
        # Guard against degenerate prices
        if stop_loss == entry_price or take_profit == entry_price:
            return None
        if (signal == SignalType.BUY and stop_loss >= entry_price) or \
           (signal == SignalType.SELL and stop_loss <= entry_price):
            return None

        # asyncio.create_task(
        #     new_order(epic, signal, entry_price, take_profit, stop_loss)
        # )
        await send_hook(ticker=epic, hook_name="STRATEGY", direction=signal, amount=50, profit=250, loss=250, trail_sl=200, recalibrate=True, mkt_closed=True, strategy=True)
        print(f"Archive Signal | {epic}: {signal.value} @ {entry_price:.4f} | TP: {take_profit:.4f} | SL: {stop_loss:.4f}")
        return signal

    return None