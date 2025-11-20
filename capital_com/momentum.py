from typing import Optional, List
from enum import Enum
from .memory import memory

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    NONE = "NONE"

def compute_ema(prices: List[float], period: int) -> Optional[float]:
    if prices is None or len(prices) < period:
        return None
    k = 2.0 / (period + 1)
    # seed with simple MA of first `period` values
    seed = sum(prices[:period]) / period
    ema = seed
    for p in prices[period:]:
        ema = p * k + ema * (1 - k)
    return ema

def compute_atr(bars: List[dict], period: int = 14) -> Optional[float]:
    if bars is None or len(bars) < period + 1:
        return None
    trs = []
    # need a list of TRs for bars[-period-? .. -1]
    start = len(bars) - (period + 1)
    for i in range(start + 1, len(bars)):
        cur = bars[i]
        prev = bars[i - 1]
        high = cur["high"]
        low = cur["low"]
        prev_close = prev["close"]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    # simple SMA of TRs then smooth into ATR via Wilder's EMA
    if len(trs) < period:
        return None
    # wilder's ATR: first value = sma, subsequent = (prev_atr*(n-1)+tr)/n
    sma = sum(trs[:period]) / period
    atr = sma
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr

def momentum_punch_signal(
    epic: str,
    atr_period: int = 14,
    trend_period: int = 50,
    impulse_atr_mult: float = 1.6,
    min_body_ratio: float = 0.55,
    retrace_max_ratio: float = 0.618
) -> Optional[SignalType]:
    """
    Momentum Punch scalper for XAUUSD-like behavior.
    - Looks for an impulse candle (strong range vs ATR, clean body)
    - Waits for a small retrace
    - Fires on continuation candle beyond impulse high/low
    - Requires slow_trend EMA confirmation (trend_period)
    """
    bars = memory.bars[epic]
    if len(bars) < max(trend_period, atr_period) + 4:
        return None

    # grab last 4 fully closed bars:
    # [-4] = impulse candidate, [-3] = retrace, [-2] = potential setup (extra), [-1] = confirmation (current closed)
    impulse = bars[-4]
    retrace = bars[-3]
    setup = bars[-2]
    confirm = bars[-1]

    closes = [b["close"] for b in bars]
    slow_trend = compute_ema(closes, trend_period)
    atr = compute_atr(list(bars), atr_period)

    if slow_trend is None or atr is None:
        return None

    # Impulse metrics
    imp_high = impulse["high"]
    imp_low = impulse["low"]
    imp_open = impulse["open"]
    imp_close = impulse["close"]
    imp_range = imp_high - imp_low
    if imp_range <= 0:
        return None
    imp_body = abs(imp_close - imp_open)
    body_ratio = imp_body / imp_range if imp_range > 0 else 0.0

    # is impulse strong vs ATR and with large body (clean thrust)
    strong_range = imp_range >= (atr * impulse_atr_mult)
    clean_body = body_ratio >= min_body_ratio

    # Identify bullish vs bearish impulse
    bullish_impulse = (imp_close > imp_open) and clean_body and strong_range and \
                      ((imp_high - imp_close) <= 0.25 * imp_range)  # close near high
    bearish_impulse = (imp_close < imp_open) and clean_body and strong_range and \
                      ((imp_close - imp_low) <= 0.25 * imp_range)   # close near low

    # Retrace: retrace bar must pull price back into a reasonable fraction of impulse
    # For bullish impulse, retrace should retest below impulse high but not below impulse midpoint
    retrace_ok = False
    if bullish_impulse:
        # retrace low should be below or into the impulse high area but not below the block+max retrace
        # i.e. retrace_low between (imp_high - retrace_max_ratio*imp_range) and imp_high
        retrace_low = retrace["low"]
        retrace_ok = (imp_high - retrace_max_ratio * imp_range) <= retrace_low <= imp_high
    elif bearish_impulse:
        retrace_high = retrace["high"]
        retrace_ok = imp_low <= retrace_high <= (imp_low + retrace_max_ratio * imp_range)
    else:
        return None  # no valid impulse

    if not retrace_ok:
        return None

    # Confirmation: confirm closes beyond impulse extreme (price continuation)
    if bullish_impulse:
        # confirmation candle must close above impulse high (clear continuation)
        if confirm["close"] <= imp_high:
            return None
        # trend filter: slow_trend must agree (price above slow_trend)
        if closes[-1] <= slow_trend:
            return None
        return SignalType.BUY

    if bearish_impulse:
        if confirm["close"] >= imp_low:
            return None
        if closes[-1] >= slow_trend:
            return None
        return SignalType.SELL

    return None
